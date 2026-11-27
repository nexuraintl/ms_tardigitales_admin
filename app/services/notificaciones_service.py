import asyncio
import calendar
import logging
import os
from datetime import datetime, time, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from fastapi import status
from app.repositories.notificaciones_repository import NotificacionesRepository
from app.schemas.notificaciones_schema import NotificacionCreateSchema
from app.core.exceptions import PipelineException
from app.constants import DEFAULT_CLIENT_ID
from app.services.fcm_push_service import FcmPushService

logger = logging.getLogger("notificaciones_service")

BOGOTA_TZ = timezone(timedelta(hours=-5))


def _now_bogota() -> datetime:
    """Retorna la fecha/hora actual de Colombia (UTC-5) como datetime naive para MySQL."""
    return datetime.now(BOGOTA_TZ).replace(tzinfo=None, microsecond=0)


def _parse_hhmm(val: Optional[str], default: time) -> time:
    if not val:
        return default
    try:
        parts = str(val).strip().split(":")
        return time(int(parts[0]), int(parts[1]))
    except Exception:
        return default


def _parse_fecha_programada(fecha_str: Optional[str], fallback: datetime) -> datetime:
    """Parsea los formatos de fecha enviados por el MFE Admin (DD/MM/YYYY HH:MM, ISO, etc.)."""
    raw = (fecha_str or "").strip()
    if not raw:
        return fallback
    for fmt in (
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%d-%m-%Y %H:%M",
    ):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return fallback


def _format_fecha_display(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y %H:%M")


def _ajustar_a_ventana_horaria(
    dt: datetime,
    hora_inicio_str: Optional[str],
    hora_fin_str: Optional[str],
    respetar_rango: bool,
) -> Tuple[datetime, bool]:
    """
    Si respetar_rango=True y dt cae fuera de [hora_inicio, hora_fin],
    lo ajusta a la próxima apertura de hora_inicio y retorna (dt_ajustado, fue_pospuesto).
    """
    if not respetar_rango:
        return dt, False

    t_ini = _parse_hhmm(hora_inicio_str, time(7, 0))
    t_fin = _parse_hhmm(hora_fin_str, time(17, 0))
    t_cur = dt.time()

    if t_cur < t_ini:
        return dt.replace(hour=t_ini.hour, minute=t_ini.minute, second=0, microsecond=0), True
    if t_cur > t_fin:
        next_day = dt + timedelta(days=1)
        return next_day.replace(hour=t_ini.hour, minute=t_ini.minute, second=0, microsecond=0), True
    return dt, False


def _siguiente_dia_en_ventana(now_dt: datetime, hora_inicio_str: Optional[str]) -> datetime:
    t_ini = _parse_hhmm(hora_inicio_str, time(7, 0))
    next_day = now_dt + timedelta(days=1)
    return next_day.replace(hour=t_ini.hour, minute=t_ini.minute, second=0, microsecond=0)


def _calcular_siguiente_recurrencia(base_dt: datetime, recurrencia: Optional[str]) -> Optional[datetime]:
    rec = (recurrencia or "No repetir").strip().lower()
    if rec in ("no repetir", "ninguna", ""):
        return None
    if rec in ("diariamente", "diario", "diaria"):
        return base_dt + timedelta(days=1)
    if rec in ("semanalmente", "semanal"):
        return base_dt + timedelta(days=7)
    if rec in ("mensualmente", "mensual"):
        year = base_dt.year + (1 if base_dt.month == 12 else 0)
        month = 1 if base_dt.month == 12 else base_dt.month + 1
        last_day = calendar.monthrange(year, month)[1]
        day = min(base_dt.day, last_day)
        return base_dt.replace(year=year, month=month, day=day)
    return None


class NotificacionesService:
    def __init__(
        self,
        repository: Optional[NotificacionesRepository] = None,
        fcm_service: Optional[FcmPushService] = None,
    ):
        self.repository = repository or NotificacionesRepository()
        self.fcm_service = fcm_service or FcmPushService()

    async def _despachar_fcm(
        self,
        notif_id: int,
        canal: str,
        audiencia: str,
        titulo: str,
        mensaje: str,
        tipo: str,
        client_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Ejecuta el envío FCM híbrido (Topic por defecto o multicast de 500 si FCM_USE_TOPICS=false)."""
        if "push" not in (canal or "").strip().lower():
            return None

        use_topics = (os.getenv("FCM_USE_TOPICS") or "true").strip().lower() in ("1", "true", "yes")
        fcm_data = {
            "notificacion_id": str(notif_id),
            "tipo": tipo or "Informativa",
            "audiencia": audiencia or "Todos",
        }
        if use_topics:
            return await asyncio.to_thread(
                self.fcm_service.enviar_a_audiencia,
                audiencia=audiencia or "Todos",
                titulo=titulo,
                mensaje=mensaje,
                data=fcm_data,
            )

        grouped = await self.repository.get_active_fcm_tokens_by_tipo(client_id)
        aud_norm = (audiencia or "Todos").strip().lower()
        target_tokens: List[str] = []
        if aud_norm in ("contadores", "contador", "todos", ""):
            target_tokens.extend(grouped.get("contadores", []))
        if aud_norm in ("sociedades", "sociedad", "todos", ""):
            target_tokens.extend(grouped.get("sociedades", []))

        fcm_result = await asyncio.to_thread(
            self.fcm_service.enviar_a_tokens_lote,
            tokens=target_tokens,
            titulo=titulo,
            mensaje=mensaje,
            data=fcm_data,
        )
        for dead_tok in fcm_result.get("unregistered_tokens") or []:
            await self.repository.mark_fcm_token_inactive(dead_tok, client_id)
        return fcm_result

    async def list_notificaciones(
        self,
        client_id: Optional[int] = None,
        canal: Optional[str] = None,
        estado: Optional[str] = None,
        audiencia: Optional[str] = None,
        texto: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        cid = client_id or DEFAULT_CLIENT_ID
        try:
            return await self.repository.list_notificaciones(
                client_id=cid,
                canal=canal,
                estado=estado,
                audiencia=audiencia,
                texto=texto,
                limit=limit,
                offset=offset
            )
        except Exception as e:
            logger.error(f"[NotificacionesService] Error al listar notificaciones: {e}", exc_info=True)
            raise PipelineException(
                etapa="NOTIFICACIONES_LIST",
                mensaje="No fue posible obtener el listado de notificaciones.",
                detalle_tecnico=str(e),
                cliente_id=cid,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def create_notificacion(
        self,
        payload: NotificacionCreateSchema,
        client_id: Optional[int] = None
    ) -> Dict[str, Any]:
        cid = client_id or payload.client_id or DEFAULT_CLIENT_ID
        try:
            now_dt = _now_bogota()
            data = payload.dict()
            data["client_id"] = cid
            audiencia_val = data.get("audiencia", "Todos")
            destinatarios_reales = await self.repository.count_tarjetas_activas_por_audiencia(
                audiencia=audiencia_val,
                client_id=cid,
            )
            data["destinatarios"] = destinatarios_reales

            estado_norm = (payload.estado or "Programada").strip().lower()
            es_inmediata = estado_norm in ("entregada", "inmediata", "enviada")
            respetar_rango = bool(data.get("respetar_rango", True))
            max_diario = int(data.get("max_diario") or 2)
            pospuesta_motivo: Optional[str] = None

            if es_inmediata:
                # Validar rango horario y tope diario antes de despachar
                dt_ajustado, fuera_rango = _ajustar_a_ventana_horaria(
                    now_dt, data.get("hora_inicio"), data.get("hora_fin"), respetar_rango
                )
                enviadas_hoy = await self.repository.count_entregadas_hoy(
                    canal=payload.canal,
                    audiencia=audiencia_val,
                    hoy_str=now_dt.strftime("%Y-%m-%d"),
                    client_id=cid,
                )
                if fuera_rango:
                    data["estado"] = "Programada"
                    data["proxima_ejecucion"] = dt_ajustado
                    data["ultimo_envio"] = None
                    data["fecha"] = _format_fecha_display(dt_ajustado)
                    pospuesta_motivo = "Fuera del rango horario permitido; programada para la próxima ventana."
                    es_inmediata = False
                elif max_diario > 0 and enviadas_hoy >= max_diario:
                    prox = _siguiente_dia_en_ventana(now_dt, data.get("hora_inicio"))
                    data["estado"] = "Programada"
                    data["proxima_ejecucion"] = prox
                    data["ultimo_envio"] = None
                    data["fecha"] = _format_fecha_display(prox)
                    pospuesta_motivo = f"Se alcanzó el máximo diario ({max_diario}); programada para mañana."
                    es_inmediata = False
                else:
                    data["estado"] = "Entregada"
                    data["proxima_ejecucion"] = None
                    data["ultimo_envio"] = now_dt
            else:
                dt_prog = _parse_fecha_programada(data.get("fecha"), now_dt)
                dt_prog, _ = _ajustar_a_ventana_horaria(
                    dt_prog, data.get("hora_inicio"), data.get("hora_fin"), respetar_rango
                )
                data["estado"] = "Programada"
                data["proxima_ejecucion"] = dt_prog
                data["ultimo_envio"] = None
                data["fecha"] = _format_fecha_display(dt_prog)

            notif_id = await self.repository.create_notificacion(data, cid)

            fcm_result: Optional[Dict[str, Any]] = None
            if es_inmediata:
                fcm_result = await self._despachar_fcm(
                    notif_id=notif_id,
                    canal=payload.canal,
                    audiencia=audiencia_val,
                    titulo=payload.titulo,
                    mensaje=payload.mensaje,
                    tipo=payload.tipo or "Informativa",
                    client_id=cid,
                )

            return {
                "status": "success",
                "message": pospuesta_motivo or "Notificación registrada exitosamente.",
                "data": {
                    "id": notif_id,
                    "titulo": payload.titulo,
                    "canal": payload.canal,
                    "estado": data["estado"],
                    "destinatarios": destinatarios_reales,
                    "proxima_ejecucion": str(data["proxima_ejecucion"]) if data.get("proxima_ejecucion") else None,
                    "fcm": fcm_result,
                }
            }
        except Exception as e:
            logger.error(f"[NotificacionesService] Error al crear notificación: {e}", exc_info=True)
            raise PipelineException(
                etapa="NOTIFICACIONES_CREATE",
                mensaje="No fue posible registrar la notificación.",
                detalle_tecnico=str(e),
                cliente_id=cid,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def procesar_notificaciones_programadas(
        self,
        client_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Procesa notificaciones programadas vencidas (invocado por Cloud Scheduler).
        Respeta ventana horaria (hora_inicio-hora_fin), max_diario y recurrencias.
        """
        cid = client_id or DEFAULT_CLIENT_ID
        now_dt = _now_bogota()
        pendientes = await self.repository.claim_due_notificaciones(now_dt=now_dt, client_id=cid)

        resumen = {
            "status": "success",
            "timestamp_bogota": now_dt.isoformat(),
            "evaluadas": len(pendientes),
            "enviadas": 0,
            "pospuestas": 0,
            "fallidas": 0,
            "detalles": [],
        }

        for notif in pendientes:
            nid = notif["id"]
            canal = notif.get("canal") or ""
            audiencia = notif.get("audiencia") or "Todos"
            respetar_rango = bool(notif.get("respetar_rango"))
            max_diario = int(notif.get("max_diario") or 2)
            recurrencia = notif.get("recurrencia") or "No repetir"

            # 1. Validar ventana horaria
            dt_ventana, fuera_rango = _ajustar_a_ventana_horaria(
                now_dt, notif.get("hora_inicio"), notif.get("hora_fin"), respetar_rango
            )
            if fuera_rango:
                await self.repository.update_notificacion_ejecucion(
                    notif_id=nid,
                    estado="Programada",
                    proxima_ejecucion=dt_ventana,
                    fecha_display=_format_fecha_display(dt_ventana),
                    client_id=cid,
                )
                resumen["pospuestas"] += 1
                resumen["detalles"].append({"id": nid, "accion": "pospuesta_horario", "proxima": str(dt_ventana)})
                continue

            # 2. Validar tope diario
            enviadas_hoy = await self.repository.count_entregadas_hoy(
                canal=canal,
                audiencia=audiencia,
                hoy_str=now_dt.strftime("%Y-%m-%d"),
                client_id=cid,
            )
            if max_diario > 0 and enviadas_hoy >= max_diario:
                prox = _siguiente_dia_en_ventana(now_dt, notif.get("hora_inicio"))
                await self.repository.update_notificacion_ejecucion(
                    notif_id=nid,
                    estado="Programada",
                    proxima_ejecucion=prox,
                    fecha_display=_format_fecha_display(prox),
                    client_id=cid,
                )
                resumen["pospuestas"] += 1
                resumen["detalles"].append({"id": nid, "accion": "pospuesta_max_diario", "proxima": str(prox)})
                continue

            # 3. Recalcular destinatarios reales al momento del envío y despachar
            dest_reales = await self.repository.count_tarjetas_activas_por_audiencia(
                audiencia=audiencia, client_id=cid
            )
            fcm_res = await self._despachar_fcm(
                notif_id=nid,
                canal=canal,
                audiencia=audiencia,
                titulo=notif.get("titulo") or "",
                mensaje=notif.get("mensaje") or "",
                tipo=notif.get("tipo") or "Informativa",
                client_id=cid,
            )

            push_fallo = fcm_res is not None and fcm_res.get("enabled") and not fcm_res.get("sent")
            if push_fallo:
                await self.repository.update_notificacion_ejecucion(
                    notif_id=nid,
                    estado="Fallida",
                    destinatarios=dest_reales,
                    proxima_ejecucion=None,
                    ultimo_envio=now_dt,
                    client_id=cid,
                )
                resumen["fallidas"] += 1
                resumen["detalles"].append({"id": nid, "accion": "fallida", "fcm": fcm_res})
                continue

            # 4. Actualizar estado o reprogramar si es recurrente
            base_rec = notif.get("proxima_ejecucion") or now_dt
            if isinstance(base_rec, str):
                base_rec = _parse_fecha_programada(base_rec, now_dt)
            sig_dt = _calcular_siguiente_recurrencia(base_rec, recurrencia)

            if sig_dt is None:
                await self.repository.update_notificacion_ejecucion(
                    notif_id=nid,
                    estado="Entregada",
                    destinatarios=dest_reales,
                    proxima_ejecucion=None,
                    ultimo_envio=now_dt,
                    fecha_display=_format_fecha_display(now_dt),
                    client_id=cid,
                )
            else:
                # Registrar ejecución actual en historial como Entregada y avanzar la programación padre
                while sig_dt <= now_dt:
                    sig_dt = _calcular_siguiente_recurrencia(sig_dt, recurrencia) or (now_dt + timedelta(days=1))
                sig_dt, _ = _ajustar_a_ventana_horaria(
                    sig_dt, notif.get("hora_inicio"), notif.get("hora_fin"), respetar_rango
                )
                await self.repository.create_notificacion(
                    {
                        "client_id": cid,
                        "titulo": notif.get("titulo"),
                        "mensaje": notif.get("mensaje"),
                        "tipo": notif.get("tipo") or "Informativa",
                        "canal": canal,
                        "audiencia": audiencia,
                        "destinatarios": dest_reales,
                        "fecha": _format_fecha_display(now_dt),
                        "estado": "Entregada",
                        "creadoPor": notif.get("creadoPor") or "Programador automático",
                        "hora_inicio": notif.get("hora_inicio") or "07:00",
                        "hora_fin": notif.get("hora_fin") or "17:00",
                        "max_diario": max_diario,
                        "recurrencia": recurrencia,
                        "respetar_rango": respetar_rango,
                        "proxima_ejecucion": None,
                        "ultimo_envio": now_dt,
                    },
                    cid,
                )
                await self.repository.update_notificacion_ejecucion(
                    notif_id=nid,
                    estado="Programada",
                    destinatarios=dest_reales,
                    proxima_ejecucion=sig_dt,
                    ultimo_envio=now_dt,
                    fecha_display=_format_fecha_display(sig_dt),
                    client_id=cid,
                )

            resumen["enviadas"] += 1
            resumen["detalles"].append(
                {
                    "id": nid,
                    "accion": "enviada",
                    "destinatarios": dest_reales,
                    "proxima_recurrencia": str(sig_dt) if sig_dt else None,
                    "fcm": fcm_res,
                }
            )

        return resumen

    async def get_notificacion(
        self,
        notif_id: int,
        client_id: Optional[int] = None
    ) -> Dict[str, Any]:
        cid = client_id or DEFAULT_CLIENT_ID
        try:
            notif = await self.repository.get_notificacion_by_id(notif_id, cid)
            if not notif:
                raise PipelineException(
                    etapa="NOTIFICACIONES_GET",
                    mensaje=f"Notificación #{notif_id} no encontrada.",
                    cliente_id=cid,
                    status_code=status.HTTP_404_NOT_FOUND
                )
            return {
                "status": "success",
                "data": notif
            }
        except PipelineException:
            raise
        except Exception as e:
            logger.error(f"[NotificacionesService] Error al consultar notificación #{notif_id}: {e}", exc_info=True)
            raise PipelineException(
                etapa="NOTIFICACIONES_GET",
                mensaje="No fue posible obtener el detalle de la notificación.",
                detalle_tecnico=str(e),
                cliente_id=cid,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def sincronizar_topics_dispositivos(
        self,
        client_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Suscribe en lote todos los tokens FCM activos a los topics de su audiencia."""
        cid = client_id or DEFAULT_CLIENT_ID
        grouped = await self.repository.get_active_fcm_tokens_by_tipo(cid)
        res_cont = await asyncio.to_thread(
            self.fcm_service.suscribir_tokens_a_topics,
            grouped.get("contadores", []),
            "contadores",
        )
        res_soc = await asyncio.to_thread(
            self.fcm_service.suscribir_tokens_a_topics,
            grouped.get("sociedades", []),
            "sociedades",
        )
        return {
            "status": "success",
            "contadores": res_cont,
            "sociedades": res_soc,
        }
