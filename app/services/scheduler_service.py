import os
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from app.integrations.jcc_client import JccClient
from app.repositories.tarjetas_repository import TarjetasRepository
from app.services.emision_engine_service import EmisionEngineService

logger = logging.getLogger("scheduler_service")

class SchedulerService:
    def __init__(self):
        self.jcc_client = JccClient()
        self.repository = TarjetasRepository()
        self.engine = EmisionEngineService(self.repository, self.jcc_client)
        self.ejecutando_ahora: bool = False
        self.ultima_ejecucion: Optional[str] = None
        self.ultimo_resultado: Optional[Dict[str, Any]] = None
        self.proxima_ejecucion: Optional[str] = None

    def get_status(self) -> Dict[str, Any]:
        from app.config.queue_config import queue_config
        return {
            "habilitado": queue_config.SCHEDULER_ENABLED,
            "ejecutando_ahora": self.ejecutando_ahora,
            "intervalo_minutos": max(1, queue_config.SCHEDULER_INTERVAL_SECONDS // 60),
            "ultima_ejecucion": self.ultima_ejecucion,
            "ultimo_resultado": self.ultimo_resultado,
            "proxima_ejecucion": self.proxima_ejecucion
        }

    async def ejecutar_emision_recurrente(
        self, 
        client_id: Optional[int] = None,
        origen: str = "PROGRAMADO"
    ) -> Dict[str, Any]:
        """
        HU-JCC-005: Emisión credencial digital RECURRENTE / MANUAL.
        Reutiliza el motor unificado de emisión (EmisionEngineService) y persiste
        el resultado en la tabla física de auditoría tn_tarjetavirtual_sincronizacion_logs.
        """
        self.ejecutando_ahora = True
        start_time = time.perf_counter()
        fecha_inicio = datetime.now()

        resumen = {
            "fecha_ejecucion": fecha_inicio.isoformat(),
            "origen": origen,
            "procesados_contadores": 0,
            "procesados_sociedades": 0,
            "creados": 0,
            "omitidos_duplicados": 0,
            "errores": 0,
            "detalles": [],
            "errores_detalle": []
        }

        try:
            tipos_contadores = ["primeraVez", "duplicado", "sustitucion"]
            tipos_sociedades = ["primeraVez", "modificacion", "duplicado"]
            cid = client_id or int(os.getenv("CLIENT_ID", "20001"))

            logger.info(f"[SchedulerService] Iniciando ciclo de emisión recurrente (client_id={cid})...")

            from app.config.queue_config import queue_config

            # ---------------------------------------------------------------------
            # PROCESO RECURRENTE DE CONTADORES
            # ---------------------------------------------------------------------
            for tipo in tipos_contadores:
                try:
                    consulta = await self.jcc_client.consultar_registro(
                        documento="", 
                        tipo_tarjeta="contadores", 
                        tipo=tipo, 
                        client_id=cid
                    )
                    
                    if consulta.get("error"):
                        err_msg = consulta.get("error")
                        logger.warning(f"[SchedulerService] Error reportado por JCC en contadores ({tipo}): {err_msg}")
                        resumen["errores"] += 1
                        resumen["errores_detalle"].append(f"Contadores ({tipo}): {err_msg}")
                        resumen["detalles"].append({
                            "tipo": tipo,
                            "tipo_tarjeta": "contadores",
                            "estado": "ERROR",
                            "error": err_msg
                        })
                        continue

                    disponibles = consulta.get("disponibles", [])
                    if not disponibles or not consulta.get("encontrado"):
                        continue

                    docs = [str(item.get("no_documento", "")).strip() for item in disponibles if item.get("no_documento")]
                    if not docs:
                        continue

                    if queue_config.SCHEDULER_AUTO_ENQUEUE:
                        lote_id = await self.repository.create_emision_lote(
                            client_id=cid,
                            tipo_tarjeta="contadores",
                            tipo_tramite=tipo,
                            total_registros=len(docs),
                            archivo_nombre=f"SCHEDULER_CONTADORES_{tipo.upper()}",
                            creado_por="Sistema Programado"
                        )
                        await self.repository.insert_emision_lote_items(lote_id=lote_id, documentos=docs, client_id=cid)
                        resumen["procesados_contadores"] += len(docs)
                        resumen["detalles"].append({
                            "tipo": tipo,
                            "tipo_tarjeta": "contadores",
                            "lote_id": lote_id,
                            "total_encolados": len(docs),
                            "estado": "EN_COLA"
                        })
                        logger.info(f"[SchedulerService] Lote #{lote_id} con {len(docs)} contadores ({tipo}) encolado para el Worker.")
                    else:
                        precargados = {str(item.get("no_documento", "")).strip(): item for item in disponibles if item.get("no_documento")}
                        sub_resumen = await self.engine.procesar_lote_emision(
                            identificaciones=docs,
                            tipo_tarjeta="contadores",
                            tipo_tramite=tipo,
                            client_id=cid,
                            items_precargados_map=precargados
                        )
                        resumen["procesados_contadores"] += sub_resumen["procesados"]
                        resumen["creados"] += sub_resumen["creados"]
                        resumen["omitidos_duplicados"] += sub_resumen["omitidos_duplicados"]
                        resumen["errores"] += (sub_resumen["no_aptos"] + sub_resumen["errores"])
                        resumen["detalles"].append(sub_resumen)

                except Exception as e:
                    err_str = str(e)
                    logger.error(f"[SchedulerService] Excepción en contadores tipo {tipo}: {err_str}", exc_info=True)
                    resumen["errores"] += 1
                    resumen["errores_detalle"].append(f"Contadores ({tipo}): {err_str}")
                    resumen["detalles"].append({
                        "tipo": tipo,
                        "tipo_tarjeta": "contadores",
                        "estado": "ERROR",
                        "error": err_str
                    })

            # ---------------------------------------------------------------------
            # PROCESO RECURRENTE DE SOCIEDADES
            # ---------------------------------------------------------------------
            for tipo in tipos_sociedades:
                try:
                    consulta = await self.jcc_client.consultar_registro(
                        documento="", 
                        tipo_tarjeta="sociedades", 
                        tipo=tipo, 
                        client_id=cid
                    )

                    if consulta.get("error"):
                        err_msg = consulta.get("error")
                        logger.warning(f"[SchedulerService] Error reportado por JCC en sociedades ({tipo}): {err_msg}")
                        resumen["errores"] += 1
                        resumen["errores_detalle"].append(f"Sociedades ({tipo}): {err_msg}")
                        resumen["detalles"].append({
                            "tipo": tipo,
                            "tipo_tarjeta": "sociedades",
                            "estado": "ERROR",
                            "error": err_msg
                        })
                        continue

                    disponibles = consulta.get("disponibles", [])
                    if not disponibles or not consulta.get("encontrado"):
                        continue

                    nits = [str(item.get("nit", "")).strip() for item in disponibles if item.get("nit")]
                    if not nits:
                        continue

                    if queue_config.SCHEDULER_AUTO_ENQUEUE:
                        lote_id = await self.repository.create_emision_lote(
                            client_id=cid,
                            tipo_tarjeta="sociedades",
                            tipo_tramite=tipo,
                            total_registros=len(nits),
                            archivo_nombre=f"SCHEDULER_SOCIEDADES_{tipo.upper()}",
                            creado_por="Sistema Programado"
                        )
                        await self.repository.insert_emision_lote_items(lote_id=lote_id, documentos=nits, client_id=cid)
                        resumen["procesados_sociedades"] += len(nits)
                        resumen["detalles"].append({
                            "tipo": tipo,
                            "tipo_tarjeta": "sociedades",
                            "lote_id": lote_id,
                            "total_encolados": len(nits),
                            "estado": "EN_COLA"
                        })
                        logger.info(f"[SchedulerService] Lote #{lote_id} con {len(nits)} sociedades ({tipo}) encolado para el Worker.")
                    else:
                        precargados = {str(item.get("nit", "")).strip(): item for item in disponibles if item.get("nit")}
                        sub_resumen = await self.engine.procesar_lote_emision(
                            identificaciones=nits,
                            tipo_tarjeta="sociedades",
                            tipo_tramite=tipo,
                            client_id=cid,
                            items_precargados_map=precargados
                        )
                        resumen["procesados_sociedades"] += sub_resumen["procesados"]
                        resumen["creados"] += sub_resumen["creados"]
                        resumen["omitidos_duplicados"] += sub_resumen["omitidos_duplicados"]
                        resumen["errores"] += (sub_resumen["no_aptos"] + sub_resumen["errores"])
                        resumen["detalles"].append(sub_resumen)

                except Exception as e:
                    err_str = str(e)
                    logger.error(f"[SchedulerService] Excepción en sociedades tipo {tipo}: {err_str}", exc_info=True)
                    resumen["errores"] += 1
                    resumen["errores_detalle"].append(f"Sociedades ({tipo}): {err_str}")
                    resumen["detalles"].append({
                        "tipo": tipo,
                        "tipo_tarjeta": "sociedades",
                        "estado": "ERROR",
                        "error": err_str
                    })

            self.ultima_ejecucion = datetime.now().isoformat()
            total_enc = resumen["procesados_contadores"] + resumen["procesados_sociedades"]
            errores_detalle_list = resumen.get("errores_detalle", [])
            
            # Deduplicación y consolidación de errores limpia
            if errores_detalle_list:
                mensajes_puros = set()
                for e in errores_detalle_list:
                    if ": " in e:
                        mensajes_puros.add(e.split(": ", 1)[1].strip())
                    else:
                        mensajes_puros.add(e.strip())

                if len(mensajes_puros) == 1:
                    msg_comun = list(mensajes_puros)[0]
                    ultimo_error_str = f"Fallo de conexión con la API JCC: {msg_comun} (Afectó a todos los trámites consultados)"
                else:
                    # Si hay diferentes motivos de error, unificarlos sin repeticiones exactas
                    ultimo_error_str = " | ".join(list(dict.fromkeys(errores_detalle_list)))
            else:
                ultimo_error_str = None

            duracion_ms = int((time.perf_counter() - start_time) * 1000)
            fecha_fin = datetime.now()

            if total_enc > 0 and resumen["errores"] == 0:
                estado = "EXITOSO"
            elif total_enc > 0 and resumen["errores"] > 0:
                estado = "PARCIAL"
            elif total_enc == 0 and resumen["errores"] > 0:
                estado = "FALLIDO"
            else:
                estado = "SIN_NOVEDAD"

            resumen["total_encolados"] = total_enc
            resumen["ultimo_error"] = ultimo_error_str
            resumen["duracion_ms"] = duracion_ms
            resumen["estado"] = estado

            # Persistencia formal en base de datos (Auditoría Enterprise sin memoria volátil)
            detalle_log = ultimo_error_str if ultimo_error_str else (
                f"Sincronizados {total_enc} trámites ({resumen['procesados_contadores']} contadores, {resumen['procesados_sociedades']} sociedades)." if total_enc > 0 else "Sin nuevos trámites aprobados pendientes en JCC."
            )
            try:
                await self.repository.create_sincronizacion_log({
                    "origen": origen,
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "duracion_ms": duracion_ms,
                    "estado": estado,
                    "total_encolados": total_enc,
                    "contadores_encolados": resumen["procesados_contadores"],
                    "sociedades_encoladas": resumen["procesados_sociedades"],
                    "errores_count": resumen["errores"],
                    "detalle": detalle_log
                }, client_id=cid)
            except Exception as log_err:
                logger.error(f"[SchedulerService] Error al guardar log en BD: {log_err}")

            self.ultimo_resultado = {
                "contadores_encolados": resumen["procesados_contadores"],
                "sociedades_encoladas": resumen["procesados_sociedades"],
                "total_encolados": total_enc,
                "errores": resumen["errores"],
                "ultimo_error": ultimo_error_str,
                "duracion_ms": duracion_ms,
                "origen": origen,
                "estado": estado
            }

            from app.config.queue_config import queue_config
            from datetime import timedelta
            self.proxima_ejecucion = (datetime.now() + timedelta(seconds=queue_config.SCHEDULER_INTERVAL_SECONDS)).isoformat()

            logger.info(f"[SchedulerService] Ciclo recurrente finalizado. Estado: {estado}, Total encolados: {total_enc}, Duración: {duracion_ms}ms")
            return resumen

        finally:
            self.ejecutando_ahora = False

# Instancia singleton para acceso y telemetría global
scheduler_service = SchedulerService()
