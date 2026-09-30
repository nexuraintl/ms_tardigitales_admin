from datetime import datetime
from typing import Any, Dict, Optional

def build_auditoria_payload(
    *,
    client_id: Optional[int],
    tipo_tarjeta: str,          # "contadores" | "sociedades"
    tipo: str,                  # "primeraVez" | "duplicado" | ...
    metodo: str,                # "POST" | "GET"
    url: str,
    parametros_peticion: Dict[str, Any],
    cuerpo_respuesta: Dict[str, Any],
    duracion_ms: int,
    codigo_http: int = 200,
) -> Dict[str, Any]:
    """Construye el dict listo para el repositorio."""
    return {
        "client_id": client_id,
        "tipo_tarjeta": tipo_tarjeta,
        "tipo_asociado": tipo,
        "metodo": metodo,
        "url": url,
        "duracion_ms": duracion_ms,
        "codigo_http": codigo_http,
        "parametros_peticion": parametros_peticion,
        "cuerpo_respuesta_peticion": cuerpo_respuesta,
    }