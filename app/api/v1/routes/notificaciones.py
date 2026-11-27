import os
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Path, Body, status
from typing import List, Dict, Any, Optional
from app.services.notificaciones_service import NotificacionesService
from app.schemas.notificaciones_schema import NotificacionCreateSchema
from app.constants import DEFAULT_CLIENT_ID
from app.core.permissions import PERMISSIONS, require_permission

router = APIRouter()
service = NotificacionesService()

@router.get(
    "/list",
    response_model=List[Dict[str, Any]],
    dependencies=[
        Depends(
            require_permission(
                PERMISSIONS.NOTIF_HISTORIAL,
                PERMISSIONS.REP_NOTIFICACIONES,
            )
        )
    ],
)
async def list_notificaciones(
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
    canal: Optional[str] = Query(None, description="Filtrar por canal: Push, Alerta estándar, Notificación interna"),
    estado: Optional[str] = Query(None, description="Filtrar por estado: Entregada, Programada, Fallida, En proceso"),
    audiencia: Optional[str] = Query(None, description="Filtrar por audiencia: Todos, Contadores, Sociedades"),
    texto: Optional[str] = Query(None, description="Búsqueda por texto en título o mensaje"),
    limit: int = Query(100, ge=1, le=500, description="Cantidad máxima de registros a retornar"),
    offset: int = Query(0, ge=0, description="Desplazamiento / paginación")
):
    """
    Retorna el historial de notificaciones enviadas y programadas (HU-JCC-020).
    """
    cid = client_id or DEFAULT_CLIENT_ID
    return await service.list_notificaciones(
        client_id=cid,
        canal=canal,
        estado=estado,
        audiencia=audiencia,
        texto=texto,
        limit=limit,
        offset=offset
    )

@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(PERMISSIONS.NOTIF_NUEVA))],
)
async def create_notificacion(
    payload: NotificacionCreateSchema = Body(..., description="Datos de la notificación a crear"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    """
    Registra una nueva notificación personalizada (HU-JCC-020).
    Soporta canales Push, Alerta estándar y Notificación interna, así como envíos inmediatos y programados.
    """
    cid = client_id or payload.client_id or DEFAULT_CLIENT_ID
    return await service.create_notificacion(payload, cid)

@router.post(
    "/sincronizar-topics",
    dependencies=[Depends(require_permission(PERMISSIONS.NOTIF_NUEVA))],
)
async def sincronizar_topics_fcm(
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    """
    Sincroniza (backfill) todos los tokens FCM activos en BD hacia los topics
    jcc_todos, jcc_contadores y jcc_sociedades.
    """
    cid = client_id or DEFAULT_CLIENT_ID
    return await service.sincronizar_topics_dispositivos(cid)

@router.post("/procesar-programadas")
async def procesar_notificaciones_programadas(
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
    x_scheduler_secret: Optional[str] = Header(None, alias="X-Scheduler-Secret"),
):
    """
    Endpoint invocado periódicamente por Google Cloud Scheduler para despachar
    notificaciones programadas vencidas respetando rango horario, max_diario y recurrencias.
    """
    expected_secret = (os.getenv("SCHEDULER_SECRET") or "").strip()
    if expected_secret and x_scheduler_secret != expected_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header X-Scheduler-Secret inválido o ausente.",
        )
    cid = client_id or DEFAULT_CLIENT_ID
    return await service.procesar_notificaciones_programadas(cid)

@router.get(
    "/{id}",
    dependencies=[
        Depends(
            require_permission(
                PERMISSIONS.NOTIF_HISTORIAL,
                PERMISSIONS.REP_NOTIFICACIONES,
            )
        )
    ],
)
async def get_notificacion_detalle(
    id: int = Path(..., description="ID único de la notificación"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    """
    Retorna el detalle completo de una notificación por su ID.
    """
    cid = client_id or DEFAULT_CLIENT_ID
    return await service.get_notificacion(id, cid)
