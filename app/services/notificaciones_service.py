import logging
from typing import List, Dict, Any, Optional
from fastapi import status
from app.repositories.notificaciones_repository import NotificacionesRepository
from app.schemas.notificaciones_schema import NotificacionCreateSchema
from app.core.exceptions import PipelineException
from app.constants import DEFAULT_CLIENT_ID

logger = logging.getLogger("notificaciones_service")

class NotificacionesService:
    def __init__(self, repository: Optional[NotificacionesRepository] = None):
        self.repository = repository or NotificacionesRepository()

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
            data = payload.dict()
            data["client_id"] = cid

            notif_id = await self.repository.create_notificacion(data, cid)
            return {
                "status": "success",
                "message": "Notificación registrada exitosamente.",
                "data": {
                    "id": notif_id,
                    "titulo": payload.titulo,
                    "canal": payload.canal,
                    "estado": payload.estado
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
