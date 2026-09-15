from datetime import datetime
from typing import Any, Dict, Optional

from app.schemas.tarjetas_schema import ContadorCreateSchema
from app.utils.datetime_utils import parse_datetime
from app.utils.image_utils import ImageUtils


class ContadorMapper:
    """Convierte un item de respuesta JCC a ContadorCreateSchema."""

    @staticmethod
    def from_jcc(
        item: Dict[str, Any],
        tipo_asociado_id: int,
        estado_tarjeta_id: int,
        foto: Optional[str] = None,
        fecha_emision: Optional[datetime] = None,
    ) -> ContadorCreateSchema:

        foto_procesada = None

        if foto and isinstance(foto, str):
            if "Imagen no existe" not in foto and "no registra" not in foto.lower():
                extension = os.path.splitext(foto)[1].lower()
                if extension in ['.jpg', '.jpeg', '.png', '.svg']:
                    foto_procesada = ImageUtils.normalizar_base64(foto)
                else:
                    print(f"[Mapper] La ruta de foto no tiene una extensión válida: {foto}")
        
        return ContadorCreateSchema(
            no_tarjeta=item.get("NO_TARJETA"),
            nombres=item.get("NOMBRES"),
            primer_apellido=item.get("PRIMER_APELLIDO"),
            segundo_apellido=item.get("SEGUNDO_APELLIDO"),
            no_expd=item.get("NO_EXPD"),
            tipo_documento=item.get("TIPO_DOCUMENTO"),
            no_documento=item.get("NO_DOCUMENTO"),
            universidad=item.get("UNIVERSIDAD"),
            estado_contador=item.get("ESTADO_CONTADOR", "ACTIVO"),
            resolucion=item.get("RESOLUCION"),
            fecha_estado=parse_datetime(item.get("FECHA_ESTADO")),
            fecha_radicacion=parse_datetime(item.get("FECHA_RADICACION")),
            fecha_resolucion=parse_datetime(item.get("FECH_RESOLU")),
            acta_jcc=item.get("ACTA_JCC"),
            fecha_grado=parse_datetime(item.get("FECHA_GRADO")),
            seccional=item.get("SECCIONAL"),
            correo=item.get("EMAIL", "no_registra@example.test"),
            fecha_emision=fecha_emision or datetime.now(),
            tipo_asociado_id=tipo_asociado_id,
            estado_tarjeta_id=estado_tarjeta_id,
            foto=foto_procesada,
        )