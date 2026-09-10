from datetime import datetime
from typing import Any, Dict, Optional
from app.constants import TIPO_TARJETA_MAP, TIPO_ASOCIADO_MAP

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
) -> Dict[str, Any]:
    """Construye el dict listo para el repositorio."""
    return {
        "client_id": client_id,
        "tipo_id": int(TIPO_TARJETA_MAP[tipo_tarjeta]),          # FK a tipos
        "tipo_asociado_id": (
            int(TIPO_ASOCIADO_MAP[tipo]) if tipo in TIPO_ASOCIADO_MAP else None
        ),
        "metodo": metodo,
        "url": url,
        "fecha_creacion": datetime.now(),
        "duracion_ms": duracion_ms,
        "parametros_peticion": parametros_peticion,
        "cuerpo_respuesta_peticion": cuerpo_respuesta,
    }