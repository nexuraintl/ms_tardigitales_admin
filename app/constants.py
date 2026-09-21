from enum import StrEnum

class TipoTarjeta(StrEnum):
    CONTADORES = "contadores"
    SOCIEDADES = "sociedades"

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100