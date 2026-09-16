from datetime import datetime
from typing import Optional

_FORMATOS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S")


def parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """Parsea una fecha proveniente de la API de la JCC."""
    if not date_str:
        return None

    if isinstance(date_str, datetime):
        return date_str

    for fmt in _FORMATOS:
        try:
            return datetime.strptime(str(date_str), fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(str(date_str))
    except Exception:
        pass

    print(f"[datetime_utils] Error parseando fecha: {date_str}")
    return None