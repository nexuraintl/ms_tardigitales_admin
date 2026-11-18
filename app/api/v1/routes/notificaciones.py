from fastapi import APIRouter, Depends, Query, Path, Body, status
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
