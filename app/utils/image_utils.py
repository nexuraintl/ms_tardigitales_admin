import base64
from typing import Optional
from fastapi import HTTPException, UploadFile

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".svg"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/svg+xml"}
MAX_LOGO_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB

# Firmas base64 -> MIME
_FIRMAS_BASE64 = (
    ("/9j/",        "image/jpeg"),
    ("iVBORw0KGgo", "image/png"),
    ("R0lGOD",      "image/gif"),
    ("UklGR",       "image/webp"),
    ("Qk",          "image/bmp"),
    ("JVBERi0",     "application/pdf"),
    ("PHN2Zy",      "image/svg+xml"),
    ("PD94bWw",     "image/svg+xml"),
)


class ImageUtils:
    """Utilidades para procesar y normalizar imágenes."""

    @staticmethod
    async def upload_to_base64(file: Optional[UploadFile]) -> Optional[str]:
        """Convierte un UploadFile en un data URI base64 validando formato y tamaño."""
        if not file:
            print("[ImageUtils] No se recibió archivo (logo=None)")
            return None

        filename = file.filename or ""
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            print(f"[ImageUtils] Extensión no permitida: {ext}")
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Formato de archivo no permitido ('{ext}'). "
                    f"Formatos válidos: {', '.join(sorted(ALLOWED_EXTENSIONS))} (MS-3851)."
                ),
            )

        content_type = (file.content_type or "").lower()
        if content_type not in ALLOWED_CONTENT_TYPES:
            print(f"[ImageUtils] Content-Type no permitido: {content_type}")
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Tipo de contenido no permitido ('{content_type}'). "
                    f"Debe ser una imagen (MS-3851)."
                ),
            )

        try:
            content = await file.read()
        except Exception as e:
            print(f"[ImageUtils] Error leyendo archivo: {e}")
            raise HTTPException(
                status_code=400,
                detail="No fue posible leer el archivo enviado (MS-3851).",
            )

        if not content:
            print("[ImageUtils] El archivo llegó vacío (0 bytes)")
            raise HTTPException(
                status_code=400,
                detail="El archivo enviado está vacío (MS-3851).",
            )

        if len(content) > MAX_LOGO_SIZE_BYTES:
            print(f"[ImageUtils] Archivo demasiado grande: {len(content)} bytes")
            raise HTTPException(
                status_code=400,
                detail=(
                    f"El archivo excede el tamaño máximo permitido "
                    f"({MAX_LOGO_SIZE_BYTES // (1024 * 1024)} MB) (MS-3851)."
                ),
            )

        try:
            base64_string = base64.b64encode(content).decode("utf-8")
        except Exception as e:
            print(f"[ImageUtils] Error al codificar a base64: {e}")
            raise HTTPException(
                status_code=400,
                detail="No fue posible procesar la imagen del logo (MS-3851).",
            )

        print(f"[ImageUtils] Logo procesado: {len(content)} bytes, tipo {content_type}")
        return f"data:{content_type};base64,{base64_string}"

    @staticmethod
    def normalizar_base64(valor: Optional[str]) -> Optional[str]:
        """
        Normaliza un base64 puro a un data URI.
        - Si ya trae 'data:', lo devuelve tal cual (limpiando saltos de línea).
        - Si es base64 puro, detecta el MIME por firma y le agrega el prefijo.
        - Si no es base64 válido, devuelve None.
        """
        if not valor or not isinstance(valor, str):
            return valor

        valor = valor.strip()

        if valor.startswith("data:"):
            header, _, payload = valor.partition(",")
            payload = "".join(payload.split())
            return f"{header},{payload}"

        limpio = "".join(valor.split())

        mime = next(
            (tipo for firma, tipo in _FIRMAS_BASE64 if limpio.startswith(firma)),
            None,
        )

        if mime is None:
            try:
                base64.b64decode(limpio[:100] + "==", validate=False)
                mime = "image/jpeg"
            except Exception:
                return None

        return f"data:{mime};base64,{limpio}"