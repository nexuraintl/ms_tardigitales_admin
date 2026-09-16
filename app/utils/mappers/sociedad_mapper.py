import os
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
                if foto.startswith("data:") or len(foto) > 200:
                    foto_procesada = ImageUtils.normalizar_base64(foto)
                else:
                    extension = os.path.splitext(foto)[1].lower()
                    if extension in ['.jpg', '.jpeg', '.png', '.svg']:
                        foto_procesada = ImageUtils.normalizar_base64(foto)
                    else:
                        print(f"[Mapper] La ruta de foto no tiene una extensión válida: {foto}")
        
        expd_raw = item.get("NO_EXPD") or item.get("no_expd") or 0
        try:
            expd_val = int(expd_raw)
        except Exception:
            expd_val = 0

        insc_raw = item.get("INSCRIPCION") or item.get("inscripcion")
        insc_val = None
        if insc_raw is not None and str(insc_raw).strip() != "":
            try:
                insc_val = int(insc_raw)
            except Exception:
                insc_val = None

        razon_social = item.get("RAZON_SOCIAL") or item.get("razon_social") or "Sin Razón Social"
        nit = item.get("NIT") or item.get("nit") or ""
        tipo_sociedad = item.get("TIPO_SOCIEDAD") or item.get("tipo_sociedad") or "SOCIEDAD DE CONTADORES"
        acta = item.get("ACTA_JCC") or item.get("acta_jcc")

        return SociedadCreateSchema(
            no_expd=expd_val,
            razon_social=str(razon_social),
            nit=str(nit),
            tipo_sociedad=str(tipo_sociedad),
            inscripcion=insc_val,
            fecha_radicacion=parse_datetime(item.get("FECHA_RADICACION") or item.get("fecha_radicacion")),
            estado_sociedad=item.get("ESTADO_SOCIEDAD") or item.get("estado_sociedad") or "ACTIVO",
            resolucion=item.get("RESOLUCION") or item.get("resolucion"),
            fecha_resolucion=parse_datetime(item.get("FECH_RESOLU") or item.get("fecha_resolucion")),
            acta_jcc=str(acta) if acta is not None else None,
            estado_solicitud=item.get("ESTADO_SOLICITUD") or item.get("estado_solicitud"),
            tipo_solicitud=item.get("TIPO_SOLICITUD") or item.get("tipo_solicitud"),
            fecha_emision=fecha_emision or datetime.now(),
            tipo_asociado_id=tipo_asociado_id or 1,
            estado_tarjeta_id=estado_tarjeta_id or 1,
            foto=foto_procesada,
        )