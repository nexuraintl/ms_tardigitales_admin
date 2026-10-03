import os
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from app.integrations.jcc_client import JccClient

COLOMBIA_TZ = timezone(timedelta(hours=-5))
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

                    docs_todos = [str(item.get("no_documento", "")).strip() for item in disponibles if item.get("no_documento")]
                    if not docs_todos:
                        continue

                    # Filtrar contadores que ya cuentan con tarjeta emitida en el sistema
                    docs = await self.repository.filter_unregistered_accountants(docs_todos, cid)
                    if not docs:
                        logger.info(f"[SchedulerService] Contadores ({tipo}): Los {len(docs_todos)} registros reportados por JCC ya cuentan con tarjeta emitida. Omitiendo creación de lote.")
                        continue

                    # Mapeo de datos completos recibidos en la llamada masiva
                    precargados_map = {str(item.get("no_documento", "")).strip(): item for item in disponibles if item.get("no_documento")}

                    # -------------------------------------------------------------
                    # FASE 1: Ingesta Inmediata Garantizada (Fast-Path Persistence)
                    # Persiste las tarjetas inmediatamente en BD con estado Emitida
                    # y los datos oficiales de la JCC (resolución, actas, seccional, etc.)
                    # -------------------------------------------------------------
                    from app.schemas.tarjetas_schema import EstadoTarjetaEnum
                    docs_creados = []
                    for doc in docs:
                        item_data = precargados_map.get(doc, {})
                        contador_data = {
                            "no_tarjeta": item_data.get("no_tarjeta", ""),
                            "nombres": item_data.get("nombres", ""),
                            "primer_apellido": item_data.get("primer_apellido", ""),
                            "segundo_apellido": item_data.get("segundo_apellido", ""),
                            "no_expd": item_data.get("no_expd", 0),
                            "tipo_documento": item_data.get("tipo_documento", "CC"),
                            "no_documento": doc,
                            "universidad": item_data.get("universidad", ""),
                            "estado_contador": item_data.get("estado_contador", "ACTIVO"),
                            "resolucion": item_data.get("resolucion", ""),
                            "fecha_estado": item_data.get("fecha_estado"),
                            "fecha_radicacion": item_data.get("fecha_radicacion"),
                            "fecha_resolucion": item_data.get("fecha_resolucion"),
                            "acta_jcc": item_data.get("acta_jcc"),
                            "fecha_grado": item_data.get("fecha_grado"),
                            "seccional": item_data.get("seccional", ""),
                            "correo": item_data.get("correo", ""),
                            "tipo_asociado": tipo,
                            "estado": EstadoTarjetaEnum.EMITIDA.value,
                            "foto": item_data.get("foto") or item_data.get("pdf") or None
                        }
                        try:
                            await self.repository.create_contadores(contador_data, cid)
                            docs_creados.append(doc)
                        except Exception as create_err:
                            logger.error(f"[SchedulerService] Error persistiendo contador {doc}: {create_err}")
                            resumen["errores"] += 1
                            resumen["errores_detalle"].append(f"Contador {doc}: {str(create_err)}")

                    resumen["procesados_contadores"] += len(docs_creados)
                    resumen["creados"] += len(docs_creados)

                    # -------------------------------------------------------------
                    # FASE 2: Encolar la hidratación asíncrona de fotos en segundo plano
                    # -------------------------------------------------------------
                    if docs_creados and queue_config.SCHEDULER_AUTO_ENQUEUE:
                        lote_id = await self.repository.create_emision_lote(
                            client_id=cid,
                            tipo_tarjeta="contadores",
                            tipo_tramite=tipo,
                            total_registros=len(docs_creados),
                            archivo_nombre=f"SCHEDULER_FOTOS_CONTADORES_{tipo.upper()}",
                            creado_por="Sistema Programado"
                        )
                        await self.repository.insert_emision_lote_items(lote_id=lote_id, documentos=docs_creados, client_id=cid)
                        resumen["detalles"].append({
                            "tipo": tipo,
                            "tipo_tarjeta": "contadores",
                            "lote_id": lote_id,
                            "total_creados": len(docs_creados),
                            "total_encolados_fotos": len(docs_creados),
                            "estado": "EMITIDAS_FOTOS_EN_COLA"
                        })
                        logger.info(f"[SchedulerService] {len(docs_creados)} contadores ({tipo}) persistidos inmediatamente en BD. Lote #{lote_id} encolado para hidratación de fotos.")
                    elif docs_creados:
                        resumen["detalles"].append({
                            "tipo": tipo,
                            "tipo_tarjeta": "contadores",
                            "total_creados": len(docs_creados),
                            "estado": "EMITIDAS_SIN_COLA"
                        })

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

                    # Filtrar sociedades que ya cuentan con tarjeta en el sistema (por raíz de NIT, DV o expediente)
                    pendientes = await self.repository.filter_unregistered_societies(disponibles, cid)
                    if not pendientes:
                        logger.info(f"[SchedulerService] Sociedades ({tipo}): Los {len(disponibles)} registros reportados por JCC ya cuentan con tarjeta emitida. Omitiendo creación de lote.")
                        continue

                    # -------------------------------------------------------------
                    # FASE 1: Ingesta Inmediata Garantizada para Sociedades
                    # (No requieren fotos individuales, se emiten al 100% de manera atómica)
                    # -------------------------------------------------------------
                    from app.schemas.tarjetas_schema import EstadoTarjetaEnum
                    sociedades_creadas = []
                    for item in pendientes:
                        nit_raw = str(item.get("nit") or item.get("NIT", "")).strip()
                        if not nit_raw:
                            continue
                        sociedad_data = {
                            "no_expd": item.get("no_expd") or item.get("NO_EXPD") or 0,
                            "razon_social": item.get("razon_social") or item.get("RAZON_SOCIAL") or "Sin Razón Social",
                            "nit": nit_raw,
                            "tipo_sociedad": item.get("tipo_sociedad") or item.get("TIPO_SOCIEDAD") or "SOCIEDAD DE CONTADORES",
                            "inscripcion": item.get("inscripcion") or item.get("INSCRIPCION"),
                            "fecha_radicacion": item.get("fecha_radicacion") or item.get("FECHA_RADICACION"),
                            "estado_sociedad": item.get("estado_sociedad") or item.get("ESTADO_SOCIEDAD") or "ACTIVO",
                            "resolucion": item.get("resolucion") or item.get("RESOLUCION"),
                            "fecha_resolucion": item.get("fecha_resolucion") or item.get("FECH_RESOLU") or item.get("FECHA_RESOLUCION"),
                            "acta_jcc": item.get("acta_jcc") or item.get("ACTA_JCC"),
                            "estado_solicitud": item.get("estado_solicitud") or item.get("ESTADO_SOLICITUD"),
                            "tipo_solicitud": item.get("tipo_solicitud") or item.get("TIPO_SOLICITUD"),
                            "tipo_asociado": tipo,
                            "estado": EstadoTarjetaEnum.EMITIDA.value,
                            "foto": item.get("foto") or item.get("pdf") or None,
                            "representante_legal": item.get("representante_legal") or item.get("REPRESENTANTE_LEGAL") or ""
                        }
                        try:
                            await self.repository.create_sociedades(sociedad_data, cid)
                            sociedades_creadas.append(nit_raw)
                        except Exception as create_soc_err:
                            logger.error(f"[SchedulerService] Error persistiendo sociedad {nit_raw}: {create_soc_err}")
                            resumen["errores"] += 1
                            resumen["errores_detalle"].append(f"Sociedad {nit_raw}: {str(create_soc_err)}")

                    resumen["procesados_sociedades"] += len(sociedades_creadas)
                    resumen["creados"] += len(sociedades_creadas)

                    # Registrar cabecera de lote finalizado en BD para trazabilidad en auditoría
                    if sociedades_creadas:
                        try:
                            lote_id = await self.repository.create_emision_lote(
                                client_id=cid,
                                tipo_tarjeta="sociedades",
                                tipo_tramite=tipo,
                                total_registros=len(sociedades_creadas),
                                archivo_nombre=f"SCHEDULER_SOCIEDADES_{tipo.upper()}",
                                creado_por="Sistema Programado"
                            )
                            await self.repository.update_emision_lote_progress(
                                lote_id=lote_id,
                                procesados=len(sociedades_creadas),
                                exitosos=len(sociedades_creadas),
                                duplicados=0,
                                fallidos=0,
                                estado="FINALIZADO",
                                mensaje=f"{len(sociedades_creadas)}/{len(sociedades_creadas)} emitidas exitosamente en sincronización masiva.",
                                finalizado=True,
                                client_id=cid
                            )
                        except Exception as lote_soc_err:
                            logger.warning(f"[SchedulerService] No se pudo asentar cabecera de lote para sociedades: {lote_soc_err}")

                        resumen["detalles"].append({
                            "tipo": tipo,
                            "tipo_tarjeta": "sociedades",
                            "total_creadas": len(sociedades_creadas),
                            "estado": "EMITIDAS_EXITOSAMENTE"
                        })
                        logger.info(f"[SchedulerService] {len(sociedades_creadas)} sociedades ({tipo}) persistidas y emitidas inmediatamente en BD.")

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

            self.ultima_ejecucion = datetime.now(COLOMBIA_TZ).isoformat()
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
            self.proxima_ejecucion = (datetime.now(COLOMBIA_TZ) + timedelta(seconds=queue_config.SCHEDULER_INTERVAL_SECONDS)).isoformat()

            logger.info(f"[SchedulerService] Ciclo recurrente finalizado. Estado: {estado}, Total encolados: {total_enc}, Duración: {duracion_ms}ms")
            return resumen

        finally:
            self.ejecutando_ahora = False

# Instancia singleton para acceso y telemetría global
scheduler_service = SchedulerService()
