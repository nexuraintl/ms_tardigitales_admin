import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, Query, Path, Body, HTTPException

from datetime import datetime, timedelta
from app.repositories.tarjetas_repository import TarjetasRepository
from app.services.scheduler_service import scheduler_service
from app.services.queue_worker_service import queue_worker
from app.config.queue_config import queue_config

router = APIRouter(prefix="/colas", tags=["Admin - Colas y Procesos"])
repo = TarjetasRepository()

# -----------------------------------------------------------------------------
# 1. Monitoreo y Métricas Globales de Colas
# -----------------------------------------------------------------------------
@router.get("/metricas")
async def get_metricas_colas(
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    """
    Retorna métricas consolidadas del sistema de colas:
    telemetría del worker en segundo plano, estado del circuit breaker,
    scheduler y conteos de registros y lotes.
    """
    cid = client_id or int(os.getenv("CLIENT_ID", "20001"))
    metricas_raw = await repo.get_queue_metrics(cid)
    worker_status = queue_worker.get_status()
    scheduler_status = scheduler_service.get_status()

    # Si en memoria RAM no hay última ejecución (ej. reinicio del contenedor),
    # hidratar desde la tabla física tn_tarjetavirtual_sincronizacion_logs
    if not scheduler_status.get("ultimo_resultado"):
        ultimo_log = await repo.get_ultima_sincronizacion_log(cid)
        if ultimo_log:
            scheduler_status["ultima_ejecucion"] = ultimo_log.get("fecha_inicio")
            scheduler_status["ultimo_resultado"] = {
                "contadores_encolados": ultimo_log.get("contadores_encolados", 0),
                "sociedades_encoladas": ultimo_log.get("sociedades_encoladas", 0),
                "total_encolados": ultimo_log.get("total_encolados", 0),
                "errores": ultimo_log.get("errores_count", 0),
                "ultimo_error": ultimo_log.get("detalle") if ultimo_log.get("estado") in ("FALLIDO", "PARCIAL") else None,
                "duracion_ms": ultimo_log.get("duracion_ms", 0),
                "origen": ultimo_log.get("origen", "PROGRAMADO"),
                "estado": ultimo_log.get("estado")
            }

    return {
        "status": "success",
        "data": {
            "worker_activo": worker_status["activo"],
            "worker_estado": worker_status["estado"],
            "circuit_breaker": {
                "estado": worker_status["circuit_breaker_estado"],
                "fallos_consecutivos": worker_status["fallos_consecutivos"],
                "max_fallos": queue_config.CIRCUIT_BREAKER_FAIL_THRESHOLD,
                "cooldown_segundos": queue_config.CIRCUIT_BREAKER_COOLDOWN_SECONDS
            },
            "scheduler": scheduler_status,
            "metricas_items": {
                "total": metricas_raw.get("total_historico_registros", 0),
                "pendientes": metricas_raw.get("items_pendientes_en_cola", 0),
                "procesando": metricas_raw.get("lotes_activos", 0),
                "exitosos": metricas_raw.get("total_exitosos", 0),
                "fallidos": metricas_raw.get("total_fallidos", 0)
            },
            "metricas_lotes": {
                "total_lotes": metricas_raw.get("total_lotes", 0),
                "completados": metricas_raw.get("lotes_completados", 0),
                "en_proceso": metricas_raw.get("lotes_activos", 0),
                "pendientes": 1 if metricas_raw.get("items_pendientes_en_cola", 0) > 0 else 0
            }
        }
    }

# -----------------------------------------------------------------------------
# 2. Listado Paginado de Lotes de Emisión
# -----------------------------------------------------------------------------
@router.get("/lotes")
async def get_lotes(
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
    page: Optional[int] = Query(None, description="Número de página"),
    page_size: Optional[int] = Query(None, description="Registros por página"),
    limit: Optional[int] = Query(None, description="Alias para page_size"),
    offset: Optional[int] = Query(None, description="Offset de registros"),
    estado: Optional[str] = Query(None, description="Filtrar por estado (EN_COLA, PROCESANDO, FINALIZADO, FALLIDO)"),
    tipo_tarjeta: Optional[str] = Query(None, description="Filtrar por tipo (contadores, sociedades)")
):
    """
    Lista todos los lotes de emisión masiva y tareas automáticas con paginación y filtros.
    """
    cid = client_id or int(os.getenv("CLIENT_ID", "20001"))
    ps = page_size or limit or 10
    if page is not None:
        p = max(1, page)
    elif offset is not None:
        p = max(1, (offset // ps) + 1)
    else:
        p = 1

    res = await repo.get_emision_lotes_list(
        client_id=cid,
        page=p,
        page_size=ps,
        estado=estado,
        tipo_tarjeta=tipo_tarjeta
    )
    return {
        "status": "success",
        "data": res
    }

# -----------------------------------------------------------------------------
# 3. Detalle de Ítems de un Lote Específico
# -----------------------------------------------------------------------------
@router.get("/lote/{lote_id}")
async def get_lote_detalle(
    lote_id: int = Path(..., description="ID del lote a inspeccionar"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
    limit: int = Query(200, ge=1, le=1000, description="Límite de ítems a retornar")
):
    """
    Retorna la cabecera y el detalle individual de cada registro del lote con su estado y mensajes.
    """
    cid = client_id or int(os.getenv("CLIENT_ID", "20001"))
    lote = await repo.get_emision_lote(lote_id, cid)
    if not lote:
        raise HTTPException(status_code=404, detail=f"Lote #{lote_id} no encontrado.")

    items = await repo.get_emision_lote_items(lote_id, cid, limit=limit)
    return {
        "status": "success",
        "data": {
            "lote": lote,
            "items": items
        },
        "lote": lote,
        "items": items
    }

# -----------------------------------------------------------------------------
# 4. Parametrización y Configuración Dinámica de Colas y Tareas
# -----------------------------------------------------------------------------
@router.get("/configuracion")
async def get_configuracion(
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    """
    Retorna la configuración activa en base de datos para el worker y la tarea periódica.
    """
    cid = client_id or int(os.getenv("CLIENT_ID", "20001"))
    config_db = await repo.get_queue_config(cid)
    if not config_db:
        # Fallback a los valores predeterminados de queue_config
        config_db = queue_config.to_dict()
    return {
        "status": "success",
        "data": config_db
    }

@router.put("/configuracion")
async def update_configuracion(
    config_data: Dict[str, Any] = Body(..., description="Nuevos parámetros de colas y worker"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    """
    Actualiza dinámicamente en MySQL los parámetros de colas, tandas, tiempos y Circuit Breaker.
    """
    cid = client_id or int(os.getenv("CLIENT_ID", "20001"))
    nueva_config = await repo.save_queue_config(cid, config_data)
    queue_config.load_from_db(nueva_config)
    return {
        "status": "success",
        "message": "Configuración de colas actualizada exitosamente en base de datos.",
        "data": nueva_config
    }

import logging
logger = logging.getLogger("colas_routes")

# -----------------------------------------------------------------------------
# 5. Disparador Manual de la Tarea Automática Recurrente (HU-JCC-005)
# -----------------------------------------------------------------------------
@router.post("/ejecutar-tarea")
async def ejecutar_tarea_manual(
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    """
    Dispara de forma manual e inmediata el barrido de JCC para contadores y sociedades,
    encolando los hallazgos en la tabla de lotes para su procesamiento por el Worker.
    """
    cid = client_id or int(os.getenv("CLIENT_ID", "20001"))
    try:
        resumen = await scheduler_service.ejecutar_emision_recurrente(client_id=cid, origen="MANUAL")
    except Exception as exc:
        logger.error(f"[Colas] Error inesperado en ejecución manual de tarea: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Fallo crítico al ejecutar la tarea de sincronización: {str(exc)}"
        )

    total_enc = resumen.get("total_encolados", 0)
    errores = resumen.get("errores", 0)
    ultimo_error = resumen.get("ultimo_error")

    # Si hubo errores y no se pudo encolar ningún registro
    if errores > 0 and total_enc == 0:
        err_msg = ultimo_error or "Se produjeron errores al consultar los registros en la API externa de la JCC."
        logger.warning(f"[Colas] Sincronización fallida: {err_msg}")
        raise HTTPException(
            status_code=502 if any(k in err_msg.lower() for k in ["conexión", "comunicación", "vpn", "timeout"]) else 400,
            detail=f"Fallo en la sincronización con JCC: {err_msg}"
        )

    # Si hubo éxito parcial (se encolaron algunos pero otros fallaron)
    if errores > 0 and total_enc > 0:
        return {
            "status": "warning",
            "message": f"Sincronización completada con advertencias. Se encolaron {total_enc} registros, pero ocurrieron {errores} errores: {ultimo_error}",
            "data": resumen
        }

    # Si todo se ejecutó sin errores pero no habían registros nuevos
    if total_enc == 0:
        return {
            "status": "success",
            "message": "Sincronización completada exitosamente. No se encontraron nuevos trámites pendientes en la JCC.",
            "data": resumen
        }

    # Éxito total con registros encolados
    return {
        "status": "success",
        "message": f"Ciclo de emisión ejecutado exitosamente. Se encolaron {total_enc} registros para procesamiento en segundo plano.",
        "data": resumen
    }

# -----------------------------------------------------------------------------
# 6. Historial de Disparos de Sincronización (Auditoría Persistente en BD)
# -----------------------------------------------------------------------------
@router.get("/sincronizacion/historial")
async def get_sincronizacion_historial(
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
    limit: int = Query(15, ge=1, le=100, description="Límite de registros a retornar")
):
    """
    Retorna el historial cronológico de ejecuciones de sincronización desde la tabla
    física tn_tarjetavirtual_sincronizacion_logs, sin depender de la memoria volátil.
    """
    cid = client_id or int(os.getenv("CLIENT_ID", "20001"))
    logs = await repo.get_sincronizacion_logs(client_id=cid, limit=limit)
    return {
        "status": "success",
        "data": logs
    }
