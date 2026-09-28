from enum import StrEnum

class TipoTarjeta(StrEnum):
    CONTADORES = "contadores"
    SOCIEDADES = "sociedades"

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100

# =============================================================================
# SOLUCIÓN TEMPORAL / MULTI-TENANT FALLBACK:
# En entornos como Preproducción o pipelines CI/CD, las variables de entorno (.env)
# pueden ser sobreescritas o reemplazadas dinámicamente por la infraestructura, provocando
# que CLIENT_ID no esté disponible en procesos en segundo plano (Worker de Colas, Scheduler)
# que no reciben la petición de un usuario por HTTP.
#
# Se define DEFAULT_CLIENT_ID = 20001 (JCC) como constante global de contingencia.
# A futuro, este valor debe dejar de usarse de esta manera y ser reemplazado
# por un mecanismo formal de resolución multi-entidad o registro de tenants activos.
# =============================================================================
DEFAULT_CLIENT_ID: int = 20001
