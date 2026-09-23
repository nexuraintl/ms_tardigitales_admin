import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.integrations.jcc_client import JccClient
from app.repositories.tarjetas_repository import TarjetasRepository
from app.schemas.tarjetas_schema import EstadoTarjetaEnum

logger = logging.getLogger("emision_engine")

class EmisionEngineService:
    def __init__(self, repository: Optional[TarjetasRepository] = None, jcc_client: Optional[JccClient] = None):
        self.repository = repository or TarjetasRepository()
        self.jcc_client = jcc_client or JccClient()

    async def emitir_contador_individual(
        self,
        documento: str,
        tipo_tramite: str = "primeraVez",
        client_id: Optional[int] = None,
        item_precargado: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Emisión atómica y unificada de tarjeta de Contador (HU-JCC-005, HU-JCC-006, HU-JCC-007).
        """
        doc_limpio = "".join(c for c in str(documento).strip() if c.isalnum())
        if not doc_limpio:
            return {
                "resultado": "error",
                "documento": documento,
                "mensaje": "Número de identificación vacío o inválido."
            }

        cid = client_id

        # 1. Control estricto de duplicados en BD
        existe = await self.repository.exists_accountant(doc_limpio, cid)
        if existe:
            return {
                "resultado": "omitido_duplicado",
                "documento": doc_limpio,
                "mensaje": f"El contador con identificación {doc_limpio} ya cuenta con tarjeta registrada en el sistema."
            }

        # 2. Obtener datos de la JCC (precargados o consulta vía JccClient con auditoría automática)
        item = item_precargado
        if not item:
            consulta = await self.jcc_client.consultar_registro(
                documento=doc_limpio,
                tipo_tarjeta="contadores",
                tipo=tipo_tramite,
                client_id=cid
            )
            # A. Falla técnica / infraestructura (VPN desconectada, timeout, error de red o servidor)
            if consulta and consulta.get("es_error_conexion"):
                return {
                    "resultado": "error_conexion",
                    "documento": doc_limpio,
                    "mensaje": consulta.get("error") or "Fallo de conexión con la API externa de la JCC (Verifique VPN o disponibilidad del servicio)."
                }

            # B. Respuesta de negocio: JCC respondió pero la cédula no existe o no es apta
            if not consulta or not consulta.get("encontrado") or not consulta.get("data"):
                error_msg = consulta.get("error") if consulta else "Registro no encontrado en los servicios de la JCC."
                return {
                    "resultado": "no_encontrado",
                    "documento": doc_limpio,
                    "mensaje": error_msg or "No se encontró registro oficial activo en la JCC."
                }
            item = consulta["data"]

        # 3. Resolución de fotografía Base64 si no vino incluida
        foto_b64 = item.get("pdf") or item.get("foto")
        if not foto_b64:
            try:
                consulta_foto = await self.jcc_client.consultar_registro(
                    documento=doc_limpio,
                    tipo_tarjeta="contadores",
                    tipo=tipo_tramite,
                    client_id=cid
                )
                if consulta_foto and consulta_foto.get("data"):
                    foto_b64 = consulta_foto["data"].get("pdf") or consulta_foto["data"].get("foto")
            except Exception as e:
                logger.warning(f"[EmisionEngine] No fue posible obtener foto complementaria para {doc_limpio}: {e}")

        # 4. Construcción y persistencia con estado inicial 'Emitida'
        contador_data = {
            "no_tarjeta": item.get("no_tarjeta", ""),
            "nombres": item.get("nombres", ""),
            "primer_apellido": item.get("primer_apellido", ""),
            "segundo_apellido": item.get("segundo_apellido", ""),
            "no_expd": item.get("no_expd", 0),
            "tipo_documento": item.get("tipo_documento", "CC"),
            "no_documento": item.get("no_documento", doc_limpio),
            "universidad": item.get("universidad", ""),
            "estado_contador": item.get("estado_contador", "ACTIVO"),
            "resolucion": item.get("resolucion", ""),
            "fecha_estado": item.get("fecha_estado"),
            "fecha_radicacion": item.get("fecha_radicacion"),
            "fecha_resolucion": item.get("fecha_resolucion"),
            "acta_jcc": item.get("acta_jcc"),
            "fecha_grado": item.get("fecha_grado"),
            "seccional": item.get("seccional", ""),
            "correo": item.get("correo", ""),
            "fecha_emision": datetime.now(),
            "tipo_asociado": tipo_tramite,
            "estado": EstadoTarjetaEnum.EMITIDA.value,
            "foto": foto_b64
        }

        try:
            new_id = await self.repository.create_contadores(contador_data, cid)
            return {
                "resultado": "emitido_exitosamente",
                "id": new_id,
                "documento": doc_limpio,
                "estado_inicial": EstadoTarjetaEnum.EMITIDA.value,
                "mensaje": "Tarjeta digital de contador emitida exitosamente."
            }
        except Exception as e:
            logger.error(f"[EmisionEngine] Error al insertar contador {doc_limpio}: {e}")
            return {
                "resultado": "error",
                "documento": doc_limpio,
                "mensaje": f"Error en base de datos al guardar contador: {str(e)}"
            }

    async def emitir_sociedad_individual(
        self,
        nit: str,
        tipo_tramite: str = "primeraVez",
        client_id: Optional[int] = None,
        item_precargado: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Emisión atómica y unificada de tarjeta de Sociedad (HU-JCC-005, HU-JCC-006, HU-JCC-007).
        """
        nit_limpio = "".join(c for c in str(nit).strip() if c.isalnum())
        if not nit_limpio:
            return {
                "resultado": "error",
                "nit": nit,
                "mensaje": "NIT de sociedad vacío o inválido."
            }

        cid = client_id

        # 1. Control estricto de duplicados en BD
        existe = await self.repository.exists_society(nit_limpio, cid)
        if existe:
            return {
                "resultado": "omitido_duplicado",
                "nit": nit_limpio,
                "mensaje": f"La sociedad con NIT {nit_limpio} ya cuenta con tarjeta registrada en el sistema."
            }

        # 2. Obtener datos de la JCC (precargados o consulta vía JccClient con auditoría automática)
        item = item_precargado
        if not item:
            consulta = await self.jcc_client.consultar_registro(
                documento=nit_limpio,
                tipo_tarjeta="sociedades",
                tipo=tipo_tramite,
                client_id=cid
            )
            # A. Falla técnica / infraestructura (VPN desconectada, timeout, error de red o servidor)
            if consulta and consulta.get("es_error_conexion"):
                return {
                    "resultado": "error_conexion",
                    "nit": nit_limpio,
                    "mensaje": consulta.get("error") or "Fallo de conexión con la API externa de la JCC (Verifique VPN o disponibilidad del servicio)."
                }

            # B. Respuesta de negocio: JCC respondió pero la sociedad no existe o no es apta
            if not consulta or not consulta.get("encontrado") or not consulta.get("data"):
                error_msg = consulta.get("error") if consulta else "Sociedad no encontrada en los servicios de la JCC."
                return {
                    "resultado": "no_encontrado",
                    "nit": nit_limpio,
                    "mensaje": error_msg or "No se encontró registro oficial activo de sociedad en la JCC."
                }
            item = consulta["data"]

        # 3. Resolución de fotografía Base64 si no vino incluida
        foto_b64 = item.get("pdf") or item.get("foto")
        if not foto_b64:
            try:
                consulta_foto = await self.jcc_client.consultar_registro(
                    documento=nit_limpio,
                    tipo_tarjeta="sociedades",
                    tipo=tipo_tramite,
                    client_id=cid
                )
                if consulta_foto and consulta_foto.get("data"):
                    foto_b64 = consulta_foto["data"].get("pdf") or consulta_foto["data"].get("foto")
            except Exception as e:
                logger.warning(f"[EmisionEngine] No fue posible obtener foto complementaria para sociedad {nit_limpio}: {e}")

        # 4. Construcción y persistencia con estado inicial 'Emitida'
        sociedad_data = {
            "no_expd": item.get("no_expd", 0),
            "razon_social": item.get("razon_social", ""),
            "nit": item.get("nit", nit_limpio),
            "tipo_sociedad": item.get("tipo_sociedad", "SOCIEDAD DE CONTADORES"),
            "inscripcion": item.get("inscripcion"),
            "fecha_radicacion": item.get("fecha_radicacion"),
            "estado_sociedad": item.get("estado_sociedad", "ACTIVO"),
            "resolucion": item.get("resolucion", ""),
            "fecha_resolucion": item.get("fecha_resolucion"),
            "acta_jcc": str(item.get("acta_jcc")) if item.get("acta_jcc") is not None else None,
            "estado_solicitud": item.get("estado_solicitud"),
            "tipo_solicitud": item.get("tipo_solicitud"),
            "correo": item.get("correo", ""),
            "representante_legal": item.get("representante_legal", ""),
            "fecha_emision": datetime.now(),
            "tipo_asociado": tipo_tramite,
            "estado": EstadoTarjetaEnum.EMITIDA.value,
            "foto": foto_b64
        }

        try:
            new_id = await self.repository.create_sociedades(sociedad_data, cid)
            return {
                "resultado": "emitido_exitosamente",
                "id": new_id,
                "nit": nit_limpio,
                "estado_inicial": EstadoTarjetaEnum.EMITIDA.value,
                "mensaje": "Tarjeta digital de sociedad emitida exitosamente."
            }
        except Exception as e:
            logger.error(f"[EmisionEngine] Error al insertar sociedad {nit_limpio}: {e}")
            return {
                "resultado": "error",
                "nit": nit_limpio,
                "mensaje": f"Error en base de datos al guardar sociedad: {str(e)}"
            }

    async def procesar_lote_emision(
        self,
        identificaciones: List[str],
        tipo_tarjeta: str = "contadores",
        tipo_tramite: str = "primeraVez",
        client_id: Optional[int] = None,
        lote_id: Optional[int] = None,
        items_precargados_map: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Orquesta el procesamiento iterativo de un lote de emisión (HU-JCC-006).
        Si se suministra lote_id, actualiza el progreso en la tabla de lotes.
        """
        cid = client_id
        items_precargados_map = items_precargados_map or {}

        resumen = {
            "lote_id": lote_id,
            "total_recibidos": len(identificaciones),
            "procesados": 0,
            "creados": 0,
            "omitidos_duplicados": 0,
            "no_encontrados": 0,
            "no_aptos": 0,
            "errores_conexion": 0,
            "errores": 0,
            "abortado_por_conexion": False,
            "detalles": []
        }

        consecutive_conn_errors = 0
        CIRCUIT_BREAKER_LIMIT = 3
        abortado = False

        for idx, doc_raw in enumerate(identificaciones):
            doc = str(doc_raw).strip()
            if not doc:
                continue

            item_precargado = items_precargados_map.get(doc)

            if tipo_tarjeta == "sociedades":
                res = await self.emitir_sociedad_individual(
                    nit=doc,
                    tipo_tramite=tipo_tramite,
                    client_id=cid,
                    item_precargado=item_precargado
                )
            else:
                res = await self.emitir_contador_individual(
                    documento=doc,
                    tipo_tramite=tipo_tramite,
                    client_id=cid,
                    item_precargado=item_precargado
                )

            resumen["procesados"] += 1
            resultado_key = res.get("resultado")

            if resultado_key == "emitido_exitosamente":
                resumen["creados"] += 1
                consecutive_conn_errors = 0
            elif resultado_key == "omitido_duplicado":
                resumen["omitidos_duplicados"] += 1
            elif resultado_key in ("no_encontrado", "no_apto"):
                resumen["no_encontrados"] += 1
                resumen["no_aptos"] += 1
                consecutive_conn_errors = 0
            elif resultado_key == "error_conexion":
                resumen["errores_conexion"] += 1
                consecutive_conn_errors += 1
            else:
                resumen["errores"] += 1

            resumen["detalles"].append(res)

            # Actualizar progreso en base de datos si existe lote_id
            if lote_id:
                await self.repository.update_emision_lote_item(
                    lote_id=lote_id,
                    documento=doc,
                    resultado=resultado_key,
                    tarjeta_id=res.get("id"),
                    mensaje_detalle=res.get("mensaje"),
                    client_id=cid
                )

                # Actualizar cabecera del lote cada 10 registros o al final
                if (idx + 1) % 10 == 0 or (idx + 1) == len(identificaciones):
                    fallos_totales = resumen["no_aptos"] + resumen["errores"] + resumen["errores_conexion"]
                    await self.repository.update_emision_lote_progress(
                        lote_id=lote_id,
                        procesados=resumen["procesados"],
                        exitosos=resumen["creados"],
                        duplicados=resumen["omitidos_duplicados"],
                        fallidos=fallos_totales,
                        estado="PROCESANDO" if (idx + 1) < len(identificaciones) else "FINALIZADO",
                        mensaje=f"{resumen['procesados']}/{resumen['total_recibidos']} procesados.",
                        finalizado=(idx + 1) == len(identificaciones),
                        client_id=cid
                    )

            # Circuit breaker: Si se acumulan 3 fallas consecutivas de red/VPN, abortar inmediatamente el lote
            if consecutive_conn_errors >= CIRCUIT_BREAKER_LIMIT:
                logger.error(
                    f"[EmisionEngine] Circuit Breaker activado en Lote #{lote_id}: {consecutive_conn_errors} fallos consecutivos de red con JCC. "
                    f"Abortando procesamiento del lote para evitar esperas y timeouts innecesarios."
                )
                abortado = True
                resumen["abortado_por_conexion"] = True

                # Marcar los registros restantes del lote como abortados
                restantes = identificaciones[idx + 1:]
                for remaining_doc in restantes:
                    rem_doc = str(remaining_doc).strip()
                    if not rem_doc:
                        continue
                    res_abort = {
                        "resultado": "error_conexion",
                        "documento": rem_doc,
                        "mensaje": "Lote abortado: Falla recurrente de conectividad con la API externa de JCC (Verifique VPN o disponibilidad del servicio)."
                    }
                    resumen["detalles"].append(res_abort)
                    resumen["procesados"] += 1
                    resumen["errores_conexion"] += 1
                    if lote_id:
                        await self.repository.update_emision_lote_item(
                            lote_id=lote_id,
                            documento=rem_doc,
                            resultado="error_conexion",
                            tarjeta_id=None,
                            mensaje_detalle=res_abort["mensaje"],
                            client_id=cid
                        )
                break

            # Pausa microscópica para ceder el event loop
            if (idx + 1) % 25 == 0:
                await asyncio.sleep(0.05)

        if lote_id:
            estado_final = "FALLIDO" if abortado else "FINALIZADO"
            msg_final = (
                f"Lote abortado por falla crítica de conexión externa con JCC (VPN desconectada o servicio inalcanzable)."
                if abortado
                else f"Lote finalizado: {resumen['creados']} credenciales emitidas."
            )
            fallos_totales = resumen["no_aptos"] + resumen["errores"] + resumen["errores_conexion"]
            await self.repository.update_emision_lote_progress(
                lote_id=lote_id,
                procesados=resumen["procesados"],
                exitosos=resumen["creados"],
                duplicados=resumen["omitidos_duplicados"],
                fallidos=fallos_totales,
                estado=estado_final,
                mensaje=msg_final,
                finalizado=True,
                client_id=cid
            )

        return resumen
