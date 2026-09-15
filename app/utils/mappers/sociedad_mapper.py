from datetime import datetime
from typing import Any, Dict, Optional

from app.schemas.tarjetas_schema import SociedadCreateSchema
from app.utils.datetime_utils import parse_datetime
from app.utils.image_utils import ImageUtils


class SociedadMapper:
    """Convierte un item de respuesta JCC a SociedadCreateSchema."""

    @staticmethod
    def from_jcc(
        item: Dict[str, Any],
        tipo_asociado_id: int,
        estado_tarjeta_id: int,
        foto: Optional[str] = None,
        fecha_emision: Optional[datetime] = None,
    ) -> SociedadCreateSchema:

        foto_procesada = None

        if foto and isinstance(foto, str):
            if "Imagen no existe" not in foto and "no registra" not in foto.lower():
                extension = os.path.splitext(foto)[1].lower()
                if extension in ['.jpg', '.jpeg', '.png', '.svg']:
                    foto_procesada = ImageUtils.normalizar_base64(foto)
                else:
                    print(f"[Mapper] La ruta de foto no tiene una extensión válida: {foto}")
        
        return SociedadCreateSchema(
            no_expd=item.get("NO_EXPD"),
            razon_social=item.get("RAZON_SOCIAL"),
            nit=item.get("NIT"),
            tipo_sociedad=item.get("TIPO_SOCIEDAD"),
            inscripcion=item.get("INSCRIPCION"),
            fecha_radicacion=parse_datetime(item.get("FECHA_RADICACION")),
            estado_sociedad=item.get("ESTADO_SOCIEDAD", "ACTIVO"),
            resolucion=item.get("RESOLUCION"),
            fecha_resolucion=parse_datetime(item.get("FECH_RESOLU")),
            acta_jcc=item.get("ACTA_JCC"),
            estado_solicitud=item.get("ESTADO_SOLICITUD"),
            tipo_solicitud=item.get("TIPO_SOLICITUD"),
            fecha_emision=fecha_emision or datetime.now(),
            tipo_asociado_id=tipo_asociado_id,
            estado_tarjeta_id=estado_tarjeta_id,
            foto=foto_procesada,
        )