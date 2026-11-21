import time
import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Set, Tuple, Literal
import httpx
from fastapi import Depends, Request, status

from app.constants import (
    APP_ENV,
    AUTH_CACHE_TTL_SECONDS,
    AUTH_CLIENT_ID,
    AUTH_CORE_BASE_URL,
    AUTH_MODULE_NAME,
)
from app.core.exceptions import PipelineException


class PERMISSIONS:
    """Catálogo canónico de los 47 permisos granulares de TarjetasDigitales (JCC)."""

    # 1. Tarjeta digital para contadores (Gestión)
    CONT_LISTADO = "contListado"
    CONT_EMISION_MASIVA = "contEmisionMasiva"
    CONT_NUEVA_TARJETA = "contNuevaTarjeta"
    CONT_DETALLES = "contDetalles"
    CONT_VER_TARJETA = "contVerTarjeta"
    CONT_EXPORTAR_TARJETA = "contExportarTarjeta"
    CONT_REGENERAR = "contRegenerar"
    CONT_ACTUALIZAR_DATOS = "contActualizarDatos"
    CONT_HISTORIAL = "contHistorial"

    # 2. Tarjeta digital para sociedades (Gestión)
    SOC_LISTADO = "socListado"
    SOC_EMISION_MASIVA = "socEmisionMasiva"
    SOC_NUEVA_TARJETA = "socNuevaTarjeta"
    SOC_DETALLES = "socDetalles"
    SOC_VER_TARJETA = "socVerTarjeta"
    SOC_EXPORTAR_TARJETA = "socExportarTarjeta"
    SOC_REGENERAR = "socRegenerar"
    SOC_ACTUALIZAR_DATOS = "socActualizarDatos"
    SOC_HISTORIAL = "socHistorial"

    # 3. Notificaciones
    NOTIF_NUEVA = "notifNueva"
    NOTIF_HISTORIAL = "notifHistorial"

    # 4. Reportes — Dashboard general
    REP_DASHBOARD_GEN = "repDashboardGen"

    # 5. Reportes — Contadores
    REP_CONT_LISTADO_CSV = "repContListadoCsv"
    REP_CONT_DETALLES = "repContDetalles"
    REP_CONT_VER_TARJETA = "repContVerTarjeta"
    REP_CONT_EXPORTAR = "repContExportar"
    REP_CONT_REGENERAR = "repContRegenerar"
    REP_CONT_ACTUALIZAR_DATOS = "repContActualizar"
    REP_CONT_HISTORIAL = "repContHistorial"

    # 6. Reportes — Sociedades
    REP_SOC_LISTADO_CSV = "repSocListadoCsv"
    REP_SOC_DETALLES = "repSocDetalles"
    REP_SOC_VER_TARJETA = "repSocVerTarjeta"
    REP_SOC_EXPORTAR = "repSocExportar"
    REP_SOC_REGENERAR = "repSocRegenerar"
    REP_SOC_ACTUALIZAR_DATOS = "repSocActualizar"
    REP_SOC_HISTORIAL = "repSocHistorial"

    # 7. Reportes — Notificaciones
    REP_NOTIFICACIONES = "repNotificaciones"

    # 8. Certificados
    CERT_LISTADO = "certListado"
    CERT_DESCARGAR = "certDescargar"
    CERT_DETALLE = "certDetalle"

    # 9. Branding Contadores
    BRAND_CONT_VER = "brandContVer"
    BRAND_CONT_GUARDAR = "brandContGuardar"
    BRAND_CONT_PUBLICAR = "brandContPublicar"

    # 10. Branding Sociedades
    BRAND_SOC_VER = "brandSocVer"
    BRAND_SOC_GUARDAR = "brandSocGuardar"
    BRAND_SOC_PUBLICAR = "brandSocPublicar"

    # 11. Branding Firma Institucional
    BRAND_FIRMA_VER = "brandFirmaVer"
    BRAND_FIRMA_GUARDAR = "brandFirmaGuardar"
    BRAND_FIRMA_PUBLICAR = "brandFirmaPublicar"

    # 12. Validador QR
    VAL_QR_CONTADORES = "valQrContadores"
    VAL_QR_SOCIEDADES = "valQrSociedades"

    # 13. Auditoría API
    AUDITORIA_API_REG = "auditoriaApiReg"

    # 14. Plantilla de activación
    PLANT_ACT_CONTADORES = "plantActContadores"
    PLANT_ACT_SOCIEDADES = "plantActSociedades"


ALL_MODULE_PERMISSIONS: Set[str] = {
    v for k, v in vars(PERMISSIONS).items() if not k.startswith("_") and isinstance(v, str)
}

# ==============================================================================
# CONFIGURACIÓN MANUAL DE LIMITACIONES Y REGLAS PERSONALIZADAS (FUTURO)
# ==============================================================================
MANUAL_REVOKED_PERMISSIONS: Set[str] = set()
MANUAL_GRANTED_PERMISSIONS: Set[str] = set()
CUSTOM_PERMISSION_EVALUATORS: Dict[str, Callable[["AuthContext"], bool]] = {}


def revoke_permission_manually(*permissions: str) -> None:
    """Revoca manualmente uno o más permisos en el microservicio."""
    for p in permissions:
        MANUAL_REVOKED_PERMISSIONS.add(p)


def grant_permission_manually(*permissions: str) -> None:
    """Concede manualmente uno o más permisos en el microservicio."""
    for p in permissions:
        MANUAL_GRANTED_PERMISSIONS.add(p)
        MANUAL_REVOKED_PERMISSIONS.discard(p)


def register_custom_evaluator(
    permission: str, evaluator: Callable[["AuthContext"], bool]
) -> None:
    """Registra una función evaluadora personalizada para un permiso."""
    CUSTOM_PERMISSION_EVALUATORS[permission] = evaluator


def clear_manual_overrides() -> None:
    """Limpia todas las limitaciones manuales en memoria."""
    MANUAL_REVOKED_PERMISSIONS.clear()
    MANUAL_GRANTED_PERMISSIONS.clear()
    CUSTOM_PERMISSION_EVALUATORS.clear()


@dataclass
class AuthContext:
    """Contexto de sesión y permisos del usuario autenticado."""

    authenticated: bool
    uid: int
    user: Dict[str, Any] = field(default_factory=dict)
    modules: Dict[str, Any] = field(default_factory=dict)
    raw_permissions: Set[str] = field(default_factory=set)

    @property
    def effective_permissions(self) -> Set[str]:
        perms = (set(self.raw_permissions) | MANUAL_GRANTED_PERMISSIONS) - MANUAL_REVOKED_PERMISSIONS
        return perms

    def has_permission(self, permission: str) -> bool:
        if not permission:
            return True
        if permission not in self.effective_permissions:
            return False
        evaluator = CUSTOM_PERMISSION_EVALUATORS.get(permission)
        if callable(evaluator):
            try:
                return bool(evaluator(self))
            except Exception:
                return False
        return True

    def has_any_permission(self, *permissions: str) -> bool:
        if not permissions:
            return True
        return any(self.has_permission(p) for p in permissions)

    def has_all_permissions(self, *permissions: str) -> bool:
        if not permissions:
            return True
        return all(self.has_permission(p) for p in permissions)

    def ensure_permission(self, permission: str) -> None:
        if not self.has_permission(permission):
            raise PipelineException(
                etapa="PERMISO_DENEGADO",
                mensaje=f"No cuenta con el permiso requerido ('{permission}') para ejecutar esta acción.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

    def ensure_any_permission(self, *permissions: str) -> None:
        if not self.has_any_permission(*permissions):
            perms_str = ", ".join(permissions)
            raise PipelineException(
                etapa="PERMISO_DENEGADO",
                mensaje=f"No cuenta con permisos de autorización ({perms_str}) para ejecutar esta acción.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

    def ensure_all_permissions(self, *permissions: str) -> None:
        if not self.has_all_permissions(*permissions):
            perms_str = ", ".join(permissions)
            raise PipelineException(
                etapa="PERMISO_DENEGADO",
                mensaje=f"Se requieren todos los permisos ({perms_str}) para ejecutar esta acción.",
                status_code=status.HTTP_403_FORBIDDEN,
            )


# Caché en memoria de corto plazo: cache_key -> (expire_ts, AuthContext)
_AUTH_CONTEXT_CACHE: Dict[str, Tuple[float, AuthContext]] = {}


def _extract_nexura_sid(request: Request) -> Optional[str]:
    sid = request.cookies.get("nexuraSID")
    if sid:
        return sid.strip()
    cookie_header = request.headers.get("cookie") or ""
    for part in cookie_header.split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            if k.strip() == "nexuraSID" and v.strip():
                return v.strip()
    return None


def _is_local_unmounted_request(request: Request, nexura_sid: Optional[str]) -> bool:
    """
    Si el entorno es local y no viene cookie nexuraSID (porque /apig/core aún no está
    montado en el gateway local), permite operar con el contexto local de desarrollo.
    """
    if nexura_sid:
        return False
    if APP_ENV == "local":
        return True
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").lower()
    if any(h in host for h in ("localhost", "127.0.0.1", "local-jcc.nexura.com.co", "host.docker.internal")):
        return True
    return False


def _extract_gateway_auth(request: Request) -> str:
    """Prioriza X-Forwarded-Authorization (GCP API Gateway) sobre Authorization."""
    return (
        request.headers.get("x-forwarded-authorization")
        or request.headers.get("authorization")
        or ""
    ).strip()


async def get_auth_context(request: Request) -> AuthContext:
    """
    Dependencia principal de FastAPI que valida la sesión en `/apig/core/auth/session`
    y obtiene los permisos granulares desde `/apig/core/auth/permissions`.
    """
    nexura_sid = _extract_nexura_sid(request)
    auth_header = _extract_gateway_auth(request)

    if _is_local_unmounted_request(request, nexura_sid):
        return AuthContext(
            authenticated=True,
            uid=111,
            user={"id": 111, "nombre": "Fabian Vargas", "login": "fvargas", "email": "fvargas@nexura.com"},
            modules={AUTH_MODULE_NAME: {"display": "Tarjetas Digitales"}},
            raw_permissions=set(ALL_MODULE_PERMISSIONS),
        )

    if not nexura_sid:
        raise PipelineException(
            etapa="SESION_NO_AUTENTICADA",
            mensaje="No se encontró una sesión activa (nexuraSID). Inicie sesión en el portal administrativo.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    cache_key = hashlib.sha256(f"{nexura_sid}:{auth_header}".encode("utf-8")).hexdigest()
    now = time.time()
    cached = _AUTH_CONTEXT_CACHE.get(cache_key)
    if cached and cached[0] > now:
        return cached[1]

    headers: Dict[str, str] = {
        "Accept": "application/json",
        "Cookie": f"nexuraSID={nexura_sid}",
    }
    if auth_header:
        headers["Authorization"] = auth_header

    session_url = f"{AUTH_CORE_BASE_URL}/apig/core/auth/session"
    try:
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            session_resp = await client.get(session_url, headers=headers)
            if session_resp.status_code in (401, 403):
                print(f"[AuthSecurity] /session rechazado ({session_resp.status_code}): {session_resp.text[:300]}")
                raise PipelineException(
                    etapa="SESION_NO_AUTENTICADA",
                    mensaje="La sesión administrativa ha expirado o no es válida.",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
            session_data = session_resp.json() if session_resp.status_code == 200 else {}

            is_authenticated = session_data.get("authenticated") is True
            uid = (
                (session_data.get("session_info") or {}).get("uid")
                or (session_data.get("user") or {}).get("id")
                or session_data.get("uid")
            )

            if not is_authenticated or not uid:
                raise PipelineException(
                    etapa="SESION_NO_AUTENTICADA",
                    mensaje="El usuario no cuenta con una sesión autenticada activa.",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            modules = session_data.get("modules") or {}
            if isinstance(modules, dict) and len(modules) > 0:
                has_module = any(k.lower() == AUTH_MODULE_NAME.lower() for k in modules.keys())
                if not has_module:
                    raise PipelineException(
                        etapa="PERMISO_DENEGADO",
                        mensaje=f"El usuario no tiene acceso autorizado al módulo {AUTH_MODULE_NAME}.",
                        status_code=status.HTTP_403_FORBIDDEN,
                    )

            perms_url = f"{AUTH_CORE_BASE_URL}/apig/core/auth/permissions"
            perms_resp = await client.get(
                perms_url,
                params={
                    "client_id": AUTH_CLIENT_ID,
                    "uid": int(uid),
                    "modulo": AUTH_MODULE_NAME,
                },
                headers=headers,
            )
            perms_list = []
            if perms_resp.status_code == 200:
                perms_json = perms_resp.json()
                if isinstance(perms_json.get("permissions"), list):
                    perms_list = [str(p) for p in perms_json["permissions"]]
            else:
                print(f"[AuthSecurity] /permissions error ({perms_resp.status_code}): {perms_resp.text[:300]}")

            ctx = AuthContext(
                authenticated=True,
                uid=int(uid),
                user=session_data.get("user") or {},
                modules=modules if isinstance(modules, dict) else {},
                raw_permissions=set(perms_list),
            )
            _AUTH_CONTEXT_CACHE[cache_key] = (now + AUTH_CACHE_TTL_SECONDS, ctx)
            return ctx

    except PipelineException:
        raise
    except Exception as exc:
        print(f"[AuthSecurity] Error al verificar sesión/permisos contra Core Auth: {exc}")
        raise PipelineException(
            etapa="SESION_NO_AUTENTICADA",
            mensaje="No fue posible verificar la sesión de autenticación con el servidor Core.",
            detalle_tecnico=str(exc),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


def require_permission(
    *permissions: str, mode: Literal["any", "all"] = "any"
) -> Callable[[AuthContext], AuthContext]:
    """
    Generador de dependencias FastAPI para exigir uno o varios permisos granulares en un endpoint.
    - `mode="any"` (por defecto): autoriza si el usuario posee AL MENOS UNO de los permisos listados.
    - `mode="all"`: autoriza solo si posee TODOS los permisos listados.
    """

    async def _dependency(auth_ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if not permissions:
            return auth_ctx
        if mode == "all":
            auth_ctx.ensure_all_permissions(*permissions)
        else:
            auth_ctx.ensure_any_permission(*permissions)
        return auth_ctx

    return _dependency
