import logging
import io
import base64
import socket
import qrcode
import httpx
from typing import Dict, Any
from app.constants import PREPROD_PHP_BRIDGE_URL

logger = logging.getLogger("notificacion_activacion")


def generar_qr_base64(hash_sha256: str) -> str:
    """
    Genera el código QR canónico que codifica el hash SHA-256 de la tarjeta
    y lo retorna en formato Data URL PNG Base64.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2
    )
    qr.add_data(str(hash_sha256).strip())
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def resolver_url_puente_nx9() -> str:
    """
    Resuelve la URL base del puente de TarjetasDigitales en NX9, adaptándose
    tanto dentro de contenedores Docker (host.docker.internal) como en ejecuciones
    locales directas de Windows/Laragon (127.0.0.1).
    """
    bridge_base = PREPROD_PHP_BRIDGE_URL.rstrip("/")
    if "host.docker.internal" in bridge_base:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect(("host.docker.internal", 9090))
            s.close()
        except Exception:
            bridge_base = bridge_base.replace("host.docker.internal:9090", "127.0.0.1").replace("host.docker.internal", "127.0.0.1")

    if not bridge_base.endswith("/api/TarjetasDigitales"):
        bridge_base = f"{bridge_base}/api/TarjetasDigitales"

    return bridge_base


async def despachar_correo_activacion(
    correo: str,
    nombre: str,
    hash_sha256: str
) -> Dict[str, Any]:
    """
    Genera el QR del hash y despacha la petición al endpoint de NX9:
    POST /api/TarjetasDigitales/enviarActivacion
    (El endpoint toma el correo_control directamente de sx_vars del módulo TarjetasDigitales en NX9).
    """
    if not correo or "@" not in correo:
        logger.warning(f"[NotificacionActivacion] Correo inválido '{correo}', se omite despacho.")
        return {"status": "omitted", "reason": "invalid_email"}

    if not hash_sha256:
        logger.warning(f"[NotificacionActivacion] Hash vacío para '{nombre}', se omite despacho.")
        return {"status": "omitted", "reason": "empty_hash"}

    qr_base64 = generar_qr_base64(hash_sha256)
    bridge_base = resolver_url_puente_nx9()
    url_enviar_activacion = f"{bridge_base}/enviarActivacion"

    headers_bridge = {
        "Host": "local-jcc.nexura.com.co",
        "Content-Type": "application/json"
    }

    payload = {
        "correo": correo.strip(),
        "nombre": nombre.strip() if nombre else "Usuario",
        "qr_base64": qr_base64
    }

    try:
        logger.info(f"[NotificacionActivacion] Despachando correo de activación a puente NX9: {url_enviar_activacion} (Destino real: {correo})...")
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url_enviar_activacion, json=payload, headers=headers_bridge)
            if resp.status_code == 200:
                data = resp.json()
                logger.info(
                    f"[NotificacionActivacion] Correo activación despachado con éxito -> Destino: {data.get('destinatario')} "
                    f"(Original: {data.get('correo_original')}, Controlado: {data.get('es_controlado')})"
                )
                return data
            else:
                logger.warning(f"[NotificacionActivacion] NX9 retornó HTTP {resp.status_code}: {resp.text}")
                return {"status": "error", "code": resp.status_code, "text": resp.text}
    except Exception as e:
        logger.error(f"[NotificacionActivacion] Excepción al enviar correo de activación: {e!r}")
        return {"status": "error", "message": repr(e)}
