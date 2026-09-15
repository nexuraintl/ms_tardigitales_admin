from datetime import datetime
from typing import Optional

_FORMATOS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d")


def parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """Parsea una fecha proveniente de la API de la JCC."""
    if not date_str:
        return None

    for fmt in _FORMATOS:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    print(f"[datetime_utils] Error parseando fecha: {date_str}")
    return None