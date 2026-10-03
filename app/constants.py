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

# =============================================================================
# CONTINGENCIA VPN PREPRODUCCIÓN / PUENTE PHP JCC:
# En preproducción, el microservicio no dispone de acceso directo a la VPN
# de la JCC, mientras que el servidor PHP (nx9) sí cuenta con conexión activa.
# Se habilita el puente hacia el endpoint PHP sin requerir variables en .env.
# =============================================================================
USE_PHP_VPN_BRIDGE: bool = False

# URL Local de desarrollo (utilizada en pruebas locales con Docker Gateway / Nginx):
# PREPROD_PHP_BRIDGE_URL: str = "http://host.docker.internal/api/TarjetasDigitales"

# URL Preproducción:
PREPROD_PHP_BRIDGE_URL: str = "https://preproduccion9-jcc.nexura.com.co/"
OFFICIAL_JCC_API_URL: str = "https://apitarjetas.jcc.gov.co"





