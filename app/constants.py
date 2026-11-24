import os
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
# ENTORNO Y CONFIGURACIÓN DEL PUENTE PHP JCC / PREPRODUCCIÓN:
# - APP_ENV = "local"                         -> Laragon local (host.docker.internal)
# - APP_ENV = "development" | "preproduccion" -> Servidor Preproducción 9
# - Si se define PREPROD_PHP_BRIDGE_URL en .env, esta tiene máxima prioridad.
# =============================================================================
USE_PHP_VPN_BRIDGE: bool = True

APP_ENV: str = os.getenv("APP_ENV", "development").lower().strip()

DEFAULT_BRIDGE_URL = (
    "http://host.docker.internal/api/TarjetasDigitales"
    if APP_ENV == "local"
    else "https://preproduccion9-jcc.nexura.com.co/api/TarjetasDigitales"
)

PREPROD_PHP_BRIDGE_URL: str = os.getenv("PREPROD_PHP_BRIDGE_URL", DEFAULT_BRIDGE_URL).rstrip("/")
OFFICIAL_JCC_API_URL: str = "https://apitarjetas.jcc.gov.co"

# =============================================================================
# INTEGRACIÓN SERVICIO OTP FIRMA ELECTRÓNICA (NEXURA)
# =============================================================================
OTP_BASE_URL: str = os.getenv("OTP_BASE_URL", "https://preproduccion-microservicios.nexura.com").rstrip("/")
OTP_AUTH_NAME: str = os.getenv("OTP_AUTH_NAME", "otpjcc")
OTP_AUTH_PASSWORD: str = os.getenv("OTP_AUTH_PASSWORD", "Nexura@2024")
OTP_STATIC_BEARER_TOKEN: str = os.getenv("OTP_STATIC_BEARER_TOKEN", "")
OTP_TIME_VALIDATE: int = int(os.getenv("OTP_TIME_VALIDATE", "5"))
OTP_BLOCKING_ATTEMPTS: int = int(os.getenv("OTP_BLOCKING_ATTEMPTS", "10"))
OTP_DEFAULT_CELLPHONE: str = os.getenv("OTP_DEFAULT_CELLPHONE", "3000000000")
OTP_SIMULATION_MODE: bool = os.getenv("OTP_SIMULATION_MODE", "false").lower() in ("true", "1", "yes")

# =============================================================================
# SEGURIDAD CRIPTOGRÁFICA Y GENERACIÓN DE HASHES (UAE JCC)
# Semilla estática fija (no depende de .env ni se pierde en CI/CD)
# =============================================================================
CARD_SECURITY_SALT: str = "JCC_TARDIGITALES_SECURE_SALT_KEY_2026_NEXURA"

# =============================================================================
# AUTENTICACIÓN DE SESIÓN Y PERMISOS GRANULARES (NEXURA CORE AUTH)
# =============================================================================
AUTH_CORE_BASE_URL: str = os.getenv(
    "AUTH_CORE_BASE_URL", "https://preproduccion9-jcc.nexura.com.co"
).rstrip("/")
AUTH_CLIENT_ID: int = int(os.getenv("AUTH_CLIENT_ID", "20060"))
AUTH_MODULE_NAME: str = os.getenv("AUTH_MODULE_NAME", "TarjetasDigitales")
AUTH_CACHE_TTL_SECONDS: int = int(os.getenv("AUTH_CACHE_TTL_SECONDS", "60"))

# =============================================================================
# INTEGRACIÓN FIRMA DIGITAL DESATENDIDA CAMERCLOUD (VIAFIRMA FORTRESS)
# =============================================================================
CAMERCLOUD_ENABLED: bool = os.getenv("CAMERCLOUD_ENABLED", "true").lower() in ("true", "1", "yes")
CAMERCLOUD_BASE_URL: str = os.getenv(
    "CAMERCLOUD_BASE_URL", "https://camercloud.camerfirma.com/fortress"
).rstrip("/")
CAMERCLOUD_CLIENT_ID: str = os.getenv("CAMERCLOUD_CLIENT_ID", "CAMERFIRMACOLOMBIACAMERCLOUD")
CAMERCLOUD_CLIENT_SECRET: str = os.getenv(
    "CAMERCLOUD_CLIENT_SECRET", "dad1e8a184d445ac84c17459ceef22dd"
)
CAMERCLOUD_REDIRECT_URI: str = os.getenv("CAMERCLOUD_REDIRECT_URI", "*")
CAMERCLOUD_CERTIFICATE_CODE: str = os.getenv("CAMERCLOUD_CERTIFICATE_CODE", "").strip()
CAMERCLOUD_CERTIFICATE_PASSWORD: str = os.getenv("CAMERCLOUD_CERTIFICATE_PASSWORD", "").strip()
CAMERCLOUD_TIMEOUT_SECONDS: int = int(os.getenv("CAMERCLOUD_TIMEOUT_SECONDS", "30"))
CAMERCLOUD_FALLBACK_UNSIGNED: bool = os.getenv("CAMERCLOUD_FALLBACK_UNSIGNED", "true").lower() in ("true", "1", "yes")








