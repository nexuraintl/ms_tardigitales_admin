from fastapi import APIRouter, Request, Response, Query, HTTPException, Path, Body, Form, File, UploadFile, BackgroundTasks, status
from urllib.parse import urlsplit
from typing import List, Dict, Any, Optional
from app.services.tarjetas_service import TarjetasService
from app.utils.image_utils import ImageUtils
from app.schemas.tarjetas_schema import (
    ActivacionMovilRequestSchema,
    RegistroLecturaRequestSchema,
    ConsultaHistorialLecturasResponseSchema,
    TarjetaCreateSchema,
    ValidadorConfigSchema,
    BrandingCredentialsCreateSchema,
    BrandingCredentialsUpdateSchema,
    ConsultaTarjetaSchema,
    EmisionMasivaRequestSchema,
    InstitucionalConfigCreateSchema,
    InstitucionalConfigUpdateSchema
)

router = APIRouter()
service = TarjetasService()

@router.get("/list")
async def list_tarjetas(
    tipo_tarjeta: Optional[str] = Query(None, description="Filtrar por 'contadores' o 'sociedades'"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
    page: int = Query(1, ge=1, description="Número de página a consultar"),
    page_size: int = Query(10, ge=1, le=50000, description="Cantidad de registros por página (máx 50000)"),
    texto: Optional[str] = Query(None, description="Búsqueda general por nombre completo, tarjeta profesional, expediente, documento o correo"),
    filtro_documento: Optional[str] = Query(None, description="Documento (contadores) o NIT (sociedades)"),
    filtro_expediente: Optional[str] = Query(None, description="Número de expediente"),
    filtro_resolucion: Optional[str] = Query(None, description="Número de resolución"),
    filtro_acta_jcc: Optional[str] = Query(None, description="Número de acta JCC"),
    filtro_no_tarjeta: Optional[str] = Query(None, description="Número de tarjeta (solo contadores)"),
    filtro_inscripcion: Optional[str] = Query(None, description="Inscripción (solo sociedades)"),
    filtro_correo: Optional[str] = Query(None, description="Correo electrónico"),
    order_by: Optional[str] = Query(None, description="Campo por el cual ordenar (ej: nombre_completo, fecha_emision)"),
    order_dir: str = Query("DESC", pattern="^(ASC|DESC)$", description="Dirección del ordenamiento: ASC o DESC"),
    fecha_resolucion_desde: Optional[str] = Query(None, description="Fecha de resolución inicial (YYYY-MM-DD)"),
    fecha_resolucion_hasta: Optional[str] = Query(None, description="Fecha de resolución final (YYYY-MM-DD)"),
    fecha_emision_desde: Optional[str] = Query(None, description="Fecha de emisión inicial (YYYY-MM-DD)"),
    fecha_emision_hasta: Optional[str] = Query(None, description="Fecha de emisión final (YYYY-MM-DD)"),
    fecha_radicacion_desde: Optional[str] = Query(None, description="Fecha de radicación inicial (YYYY-MM-DD)"),
    fecha_radicacion_hasta: Optional[str] = Query(None, description="Fecha de radicación final (YYYY-MM-DD)"),
    fecha_estado_desde: Optional[str] = Query(None, description="Fecha de estado inicial (YYYY-MM-DD)"),
    fecha_estado_hasta: Optional[str] = Query(None, description="Fecha de estado final (YYYY-MM-DD)"),
    fecha_grado_desde: Optional[str] = Query(None, description="Fecha de grado inicial (YYYY-MM-DD)"),
    fecha_grado_hasta: Optional[str] = Query(None, description="Fecha de grado final (YYYY-MM-DD)"),
    fecha_activacion_desde: Optional[str] = Query(None, description="Fecha de activación inicial (YYYY-MM-DD)"),
    fecha_activacion_hasta: Optional[str] = Query(None, description="Fecha de activación final (YYYY-MM-DD)"),
    estado_tarjeta: Optional[str] = Query(None, description="Estado de la tarjeta"),
    estado_contador: Optional[str] = Query(None, description="Estado del contador"),
    estado_sociedad: Optional[str] = Query(None, description="Estado de la sociedad"),
    tipo_asociado: Optional[str] = Query(None, description="Tipo de trámite / asociado")
):
    
    filtros = {
        "texto": texto,
        "documento": filtro_documento,
        "expediente": filtro_expediente,
        "resolucion": filtro_resolucion,
        "acta_jcc": filtro_acta_jcc,
        "no_tarjeta": filtro_no_tarjeta,
        "inscripcion": filtro_inscripcion,
        "correo": filtro_correo,
        "fecha_resolucion_desde": fecha_resolucion_desde,
        "fecha_resolucion_hasta": fecha_resolucion_hasta,
        "fecha_emision_desde": fecha_emision_desde,
        "fecha_emision_hasta": fecha_emision_hasta,
        "fecha_radicacion_desde": fecha_radicacion_desde,
        "fecha_radicacion_hasta": fecha_radicacion_hasta,
        "fecha_estado_desde": fecha_estado_desde,
        "fecha_estado_hasta": fecha_estado_hasta,
        "fecha_grado_desde": fecha_grado_desde,
        "fecha_grado_hasta": fecha_grado_hasta,
        "fecha_activacion_desde": fecha_activacion_desde,
        "fecha_activacion_hasta": fecha_activacion_hasta,
        "estado_tarjeta": estado_tarjeta,
        "estado_contador": estado_contador,
        "estado_sociedad": estado_sociedad,
        "tipo_asociado": tipo_asociado
    }
    
    return await service.list_tarjetas(
        tipo_tarjeta=tipo_tarjeta,
        client_id=client_id,
        page=page,
        page_size=page_size,
        filtros=filtros,
        order_by=order_by,
        order_dir=order_dir
    )

@router.get("/consult-registry")
async def consult_registry(
    documento: str = Query(..., min_length=3, description="Número de documento de identidad o NIT a consultar (obligatorio)"),
    tipo_tarjeta: str = Query("contadores", description="Tipo de registro ('contadores' o 'sociedades')"),
    tipo: Optional[str] = Query("", description="Tipo de consulta ('primeraVez', 'modificacion', etc.)"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.consult_registry(documento, tipo_tarjeta, tipo, client_id)


@router.get("/get/{id}")
async def get_tarjeta(
    request: Request,
    id: int = Path(..., description="ID de la tarjeta"),
    tipo_tarjeta: Optional[str] = Query(None, description="Filtrar por 'contadores' o 'sociedades'"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
):
    return await service.get_tarjeta(id, tipo_tarjeta, client_id)


@router.get("/get-by-hash/{hash}")
@router.get("/verificar/{hash}")
async def get_tarjeta_by_hash(
    request: Request,
    hash: str = Path(..., min_length=10, max_length=64, description="Hash SHA-256 canónico de la tarjeta"),
    tipo_tarjeta: Optional[str] = Query(None, description="Filtrar por 'contadores' o 'sociedades'"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
    sanitizar: bool = Query(False, description="Si es True, aplica los filtros de visibilidad del validador QR (por defecto False para App Movil e integraciones)"),
):
    ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else None)
    if ip and "," in ip:
        ip = ip.split(",")[0].strip()
    return await service.get_tarjeta_by_hash(hash, tipo_tarjeta, client_id, sanitizar=sanitizar, ip=ip, auto_log=True)


@router.get("/verificar")
async def verificar_tarjeta_query(
    request: Request,
    token: Optional[str] = Query(None, description="Token / Hash SHA-256 de la tarjeta"),
    hash: Optional[str] = Query(None, description="Hash SHA-256 alternativo de la tarjeta"),
    tipo_tarjeta: Optional[str] = Query(None, description="Filtrar por 'contadores' o 'sociedades'"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
    sanitizar: bool = Query(False, description="Si es True, aplica los filtros de visibilidad del validador QR (por defecto False para App Movil e integraciones)"),
):
    target_hash = token or hash
    if not target_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe suministrar el parámetro 'token' o 'hash' de la tarjeta a verificar."
        )
    ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else None)
    if ip and "," in ip:
        ip = ip.split(",")[0].strip()
    return await service.get_tarjeta_by_hash(target_hash, tipo_tarjeta, client_id, sanitizar=sanitizar, ip=ip, auto_log=True)


@router.get("/pdf/{id}")
@router.get("/get/{id}/pdf")
async def export_tarjeta_pdf(
    request: Request,
    id: int = Path(..., description="ID de la tarjeta"),
    tipo_tarjeta: Optional[str] = Query(None, description="Filtrar por 'contadores' o 'sociedades'"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
    base_url: Optional[str] = Query(None, description="URL base del portal frontend para el código QR"),
    download: bool = Query(True, description="Si es True fuerza la descarga como attachment")
):
    pdf_bytes, filename = await service.generar_pdf_tarjeta(id, tipo_tarjeta, client_id, base_url=base_url or request.headers.get("origin") or request.headers.get("referer"))
    disposition = "attachment" if download else "inline"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@router.get("/verificar/{hash}/pdf")
@router.get("/get-by-hash/{hash}/pdf")
async def export_tarjeta_pdf_by_hash(
    request: Request,
    hash: str = Path(..., min_length=10, max_length=64, description="Hash SHA-256 canónico de la tarjeta"),
    tipo_tarjeta: Optional[str] = Query(None, description="Filtrar por 'contadores' o 'sociedades'"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
    base_url: Optional[str] = Query(None, description="URL base del portal frontend para el código QR"),
    download: bool = Query(True, description="Si es True fuerza la descarga como attachment")
):
    pdf_bytes, filename = await service.generar_pdf_tarjeta_by_hash(hash, tipo_tarjeta, client_id, base_url=base_url or request.headers.get("origin") or request.headers.get("referer"))
    disposition = "attachment" if download else "inline"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@router.post("/create")
async def create_tarjeta(
    data: TarjetaCreateSchema = Body(...),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.create_tarjeta(data, client_id)

@router.get("/historial/{id}")
async def get_historial(
    request: Request,
    id: int = Path(..., description="ID de la tarjeta"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
    tipo: Optional[str] = Query(None, description="Tipo de tarjeta ('contador' o 'sociedad')")
):
    return await service.get_historial(id, client_id, tipo)

@router.get("/validador-qr/get-config")
async def get_validador_config(
    tipo_tarjeta: str = Query("contadores", description="Tipo de tarjeta ('contadores' o 'sociedades')"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.get_validador_config(tipo_tarjeta, client_id)

@router.post("/validador-qr/update-config")
async def update_validador_config(
    data: ValidadorConfigSchema = Body(...),
    tipo_tarjeta: Optional[str] = Query(None, description="Tipo de tarjeta ('contadores' o 'sociedades')"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    tipo = tipo_tarjeta or getattr(data, 'tipo_tarjeta', None) or "contadores"
    return await service.save_validador_config(data, tipo, client_id)

@router.get("/columns-config")
async def get_columns_config(
    tipo_tarjeta: str = Query("contadores", description="Tipo de tarjeta ('contadores' o 'sociedades')"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.get_columns_config(tipo_tarjeta, client_id)


# Branding de credenciales
@router.post("/branding-credentials/create")
async def create_branding_credentials(
    idCliente: Optional[int] = Form(None),
    version_actual: int = Form(1),
    version_publicada: Optional[int] = Form(None),
    logo: Optional[UploadFile] = File(None),
    patron: Optional[UploadFile] = File(None),
    logo_impresion: Optional[UploadFile] = File(None),
    logo_impresion_base64: Optional[str] = Form(None),
    patron_impresion: Optional[UploadFile] = File(None),
    patron_impresion_base64: Optional[str] = Form(None),
    firma_director: Optional[UploadFile] = File(None),
    nombre_director: Optional[str] = Form(None),
    firma_director_base64: Optional[str] = Form(None),
    observacion: Optional[str] = Form(None),
    color_fondo: str = Form(...),
    color_letra: str = Form(...),
    color_letra_impresion: str = Form("#0f172a"),
    usuario_creacion_id: int = Form(...),
    tipo_id: int = Form(...),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
):
    logo_base64 = await ImageUtils.upload_to_base64(logo)
    patron_base64 = await ImageUtils.upload_to_base64(patron)
    logo_imp_b64 = await ImageUtils.upload_to_base64(logo_impresion) if logo_impresion else logo_impresion_base64
    patron_imp_b64 = await ImageUtils.upload_to_base64(patron_impresion) if patron_impresion else patron_impresion_base64
    firma_base64 = await ImageUtils.upload_to_base64(firma_director) if firma_director else firma_director_base64

    data = BrandingCredentialsCreateSchema(
        idCliente=idCliente,
        version_actual=version_actual,
        version_publicada=version_publicada,
        logo=logo_base64,
        patron=patron_base64,
        logo_impresion=logo_imp_b64,
        patron_impresion=patron_imp_b64,
        color_fondo=color_fondo,
        color_letra=color_letra,
        color_letra_impresion=color_letra_impresion,
        nombre_director=nombre_director,
        firma_director=firma_base64,
        observacion=observacion,
        usuario_creacion_id=usuario_creacion_id,
        tipo_id=tipo_id,
    )

    return await service.create_or_update_branding_credentials(data, client_id)

@router.put("/branding-credentials/update/change-version/{id}")
async def update_branding_credentials(
    id: int = Path(..., description="ID único del Branding credentials"),
    data: BrandingCredentialsUpdateSchema = Body(...),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.update_branding_credentials_change_version(id, data, client_id)

@router.get("/branding-credentials/info/{id}")
async def get_branding_credentials(
    id: int = Path(..., description="ID único del Branding credentials"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.get_branding_credentials(id, client_id)

@router.get("/branding-credentials/info-published/{id}")
async def get_branding_credentials(
    id: int = Path(..., description="ID único del Branding credentials"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.get_branding_credentials_publish(id, client_id)

@router.get("/branding-credentials/list-history-versions/{id}")
async def list_history_branding_credentials(
    id: int = Path(..., description="ID Branding credentials"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
    page: int = Query(1, ge=1, description="Número de página a consultar"),
    page_size: int = Query(10, ge=1, le=100, description="Cantidad de registros por página (máx 100)")
):
    return await service.list_history_branding_credentials(id, client_id, page, page_size)

# =============================================================================
# BRANDING INSTITUCIONAL (GLOBAL - DIRECTOR GENERAL Y FIRMA OFICIAL)
# =============================================================================
@router.get("/branding-credentials/institucional/info-published")
@router.get("/branding-institucional/info-published")
async def get_institucional_published(
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.get_institucional_published(client_id)

@router.post("/branding-credentials/institucional/create")
@router.post("/branding-institucional/create")
async def create_institucional_version(
    data: InstitucionalConfigCreateSchema = Body(...),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.create_institucional_version(data, client_id)

@router.get("/branding-credentials/institucional/list-history-versions")
@router.get("/branding-institucional/list-history-versions")
async def list_institucional_history(
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
    page: int = Query(1, ge=1, description="Número de página a consultar"),
    page_size: int = Query(10, ge=1, le=100, description="Cantidad de registros por página (máx 100)")
):
    return await service.list_institucional_history(client_id, page, page_size)

@router.put("/branding-credentials/institucional/update/change-version/{id}")
@router.put("/branding-institucional/update/change-version/{id}")
async def publish_institucional_version(
    id: int = Path(..., description="ID de la versión institucional a publicar"),
    data: Optional[InstitucionalConfigUpdateSchema] = Body(None),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    observacion = data.observacion if data else None
    return await service.publish_institucional_version(id, client_id, observacion=observacion)


# Auditoria API
@router.get("/audit-api/list", response_model=Dict[str, Any])
@router.get("/auditoria-api/list", response_model=Dict[str, Any])
async def list_auditoria_api(
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
    page: int = Query(1, ge=1, description="Número de página a consultar"),
    page_size: int = Query(10, ge=1, le=50000, description="Cantidad de registros por página (máx 50000)"),
    fecha_desde: Optional[str] = Query(None, description="Fecha y hora desde (YYYY-MM-DD HH:MM)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha y hora hasta (YYYY-MM-DD HH:MM)"),
    endpoint: Optional[str] = Query(None, description="Filtro por endpoint (contadores, sociedades)"),
    tipo: Optional[str] = Query(None, description="Filtro por tipo de operación (primeraVez,duplicado,sustitucion,modificacion)"),
    texto: Optional[str] = Query(None, description="Texto a buscar en petición o respuesta"),
    cambiar_estado: Optional[str] = Query(None, description="Filtro por cambiarEstado (true, false)"),
):
    return await service.list_auditoria_api(
        client_id=client_id,
        page=page,
        page_size=page_size,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        endpoint=endpoint,
        tipo=tipo,
        texto=texto,
        cambiar_estado=cambiar_estado,
    )

# Contador creacion
@router.post('/contador/create')
@router.post('/accountant/create')
async def create_tarjeta_contador(
    data: ConsultaTarjetaSchema = Body(...),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.create_tarjeta_contador(
        documento=data.documento,
        tipo=data.tipo,
        client_id=client_id,
    )

# society creacion
@router.post('/sociedad/create')
@router.post('/society/create')
async def create_tarjeta_sociedad(
    data: ConsultaTarjetaSchema = Body(...),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.create_tarjeta_sociedad(
        documento=data.documento,
        tipo=data.tipo,
        client_id=client_id,
    )

# HU-JCC-005: Tarea programada de emision recurrente bajo demanda
@router.post('/emision-recurrente/ejecutar')
async def ejecutar_emision_recurrente(
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    from app.services.scheduler_service import SchedulerService
    scheduler = SchedulerService()
    return await scheduler.ejecutar_emision_recurrente(client_id=client_id)

# HU-JCC-006: Emisión Masiva y Procesamiento de Lotes (Síncrono y Cola Asíncrona)
@router.post("/emision-masiva")
async def emision_masiva(
    payload: EmisionMasivaRequestSchema = Body(...),
    background_tasks: BackgroundTasks = None,
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    from app.services.emision_engine_service import EmisionEngineService
    from app.repositories.tarjetas_repository import TarjetasRepository
    import os

    cid = client_id or int(os.getenv("CLIENT_ID", "20001"))
    docs = [str(d).strip() for d in payload.identificaciones if str(d).strip()]
    if not docs:
        raise HTTPException(status_code=400, detail="La lista de identificaciones no contiene registros válidos.")

    repo = TarjetasRepository()
    engine = EmisionEngineService(repo)

    # 1. Registrar cabecera del lote e ítems en BD
    lote_id = await repo.create_emision_lote(
        client_id=cid,
        tipo_tarjeta=payload.tipo_tarjeta,
        tipo_tramite=payload.tipo_tramite or "primeraVez",
        total_registros=len(docs),
        archivo_nombre=payload.archivo_nombre,
        creado_por=payload.creado_por or "Administrador"
    )
    await repo.insert_emision_lote_items(lote_id=lote_id, documentos=docs, client_id=cid)

    from app.config.queue_config import queue_config

    # 2. Despacho: si el QueueWorker continuo está activo, el lote queda encolado para el Worker
    reg_label = f"{len(docs)} registro" if len(docs) == 1 else f"{len(docs)} registros"
    if queue_config.WORKER_ENABLED:
        from app.services.queue_worker_service import queue_worker
        queue_worker.despertar()
        return {
            "status": "accepted",
            "asincrono": True,
            "lote_id": lote_id,
            "total": len(docs),
            "mensaje": f"Archivo con {reg_label} recibido correctamente. La información será procesada en segundo plano.",
            "configuracion": queue_config.to_dict()
        }
    elif payload.asincrono or len(docs) > 10:
        if background_tasks:
            background_tasks.add_task(
                engine.procesar_lote_emision,
                identificaciones=docs,
                tipo_tarjeta=payload.tipo_tarjeta,
                tipo_tramite=payload.tipo_tramite or "primeraVez",
                client_id=cid,
                lote_id=lote_id
            )
        return {
            "status": "accepted",
            "asincrono": True,
            "lote_id": lote_id,
            "total": len(docs),
            "mensaje": f"Archivo con {reg_label} recibido correctamente. La información será procesada en segundo plano."
        }
    else:
        # Procesamiento síncrono inmediato (solo para pruebas pequeñas cuando el worker está apagado)
        resumen = await engine.procesar_lote_emision(
            identificaciones=docs,
            tipo_tarjeta=payload.tipo_tarjeta,
            tipo_tramite=payload.tipo_tramite or "primeraVez",
            client_id=cid,
            lote_id=lote_id
        )
        return {
            "status": "success",
            "asincrono": False,
            "lote_id": lote_id,
            "resumen": resumen
        }

@router.get("/emision-masiva/configuracion")
async def get_configuracion_colas():
    from app.config.queue_config import queue_config
    return {
        "status": "success",
        "data": queue_config.to_dict()
    }

@router.get("/emision-masiva/lote/{lote_id}")
async def get_estado_lote(
    lote_id: int = Path(..., description="ID del lote"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    from app.repositories.tarjetas_repository import TarjetasRepository
    import os
    cid = client_id or int(os.getenv("CLIENT_ID", "20001"))
    repo = TarjetasRepository()
    lote = await repo.get_emision_lote(lote_id, cid)
    if not lote:
        raise HTTPException(status_code=404, detail=f"Lote #{lote_id} no encontrado.")
    items = await repo.get_emision_lote_items(lote_id, cid, limit=200)
    return {
        "status": "success",
        "lote": lote,
        "items": items
    }


@router.post("/activar-movil", status_code=status.HTTP_200_OK)
async def activar_tarjeta_movil(
    payload: ActivacionMovilRequestSchema = Body(..., description="Parámetros de activación móvil desde el Wallet JCC"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    """
    HU-JCC-014: Activación móvil de credencial digital desde la App Móvil / Wallet.
    - Valida el hash SHA-256 de la tarjeta.
    - Cambia el estado de 'Emitida' a 'Activa'.
    - Registra el dispositivo y token FCM en la tabla satélite tn_tarjetavirtual_dispositivos.
    - Registra la trazabilidad en el historial.
    - Retorna los datos de la credencial y branding para renderizado en la App Móvil.
    """
    if client_id and not payload.client_id:
        payload.client_id = client_id
    return await service.activar_tarjeta_movil(payload)

@router.get("/reportes/dashboard")
async def get_reportes_dashboard(
    fecha_desde: Optional[str] = Query(None, description="Fecha inicial YYYY-MM-DD"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha final YYYY-MM-DD"),
    segmento: str = Query("all", description="all, accountants, companies"),
    tipo_reporte: str = Query("general", description="general, cards, notifications"),
    estado: Optional[str] = Query(None, description="Estado de filtro anidado"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.get_reportes_dashboard(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        segmento=segmento,
        tipo_reporte=tipo_reporte,
        estado=estado,
        client_id=client_id
    )


@router.post("/lecturas/registrar", status_code=status.HTTP_201_CREATED)
async def registrar_lectura(
    request: Request,
    payload: RegistroLecturaRequestSchema = Body(..., description="Datos del evento de lectura QR"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente (opcional)")
):
    """
    Registra un evento de lectura QR (HU: Gestión de Registro y Consulta de Auditoría).
    - Clasifica automáticamente el origen: 'Dispositivo móvil' (QR dinámico 17:34) vs 'Navegador web' (QR estático 17:39).
    - Almacena en tn_tarjetavirtual_lecturas_historial.
    """
    if client_id and not payload.client_id:
        payload.client_id = client_id
    ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else None)
    if ip and "," in ip:
        ip = ip.split(",")[0].strip()
    return await service.registrar_lectura(payload, ip=ip)


@router.get("/lecturas/historial")
async def get_historial_lecturas(
    documento: str = Query(..., min_length=3, description="Cédula o NIT del usuario"),
    filtro: str = Query("me_consultaron", pattern="^(me_consultaron|mis_consultas)$", description="Filtro de consulta: 'me_consultaron' o 'mis_consultas'"),
    limit: int = Query(20, ge=1, le=100, description="Cantidad máxima de registros a retornar"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    """
    Consulta el historial de lecturas QR según número de identificación del usuario (App Móvil 14:09).
    - 'me_consultaron': Quién ha visto el perfil del usuario.
    - 'mis_consultas': Lo que el usuario autenticado ha consultado a otros.
    """
    return await service.get_historial_lecturas(
        documento=documento,
        filtro=filtro,
        limit=limit,
        offset=offset,
        client_id=client_id
    )
