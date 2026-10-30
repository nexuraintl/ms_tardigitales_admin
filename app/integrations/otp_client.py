import logging
import random
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from app.constants import (
    OTP_BASE_URL,
    OTP_AUTH_NAME,
    OTP_AUTH_PASSWORD,
    OTP_STATIC_BEARER_TOKEN,
    OTP_TIME_VALIDATE,
    OTP_BLOCKING_ATTEMPTS,
    OTP_DEFAULT_CELLPHONE,
    OTP_SIMULATION_MODE
)
from app.core.exceptions import PipelineException

logger = logging.getLogger("otp_client")


class OtpClient:
    """
    Cliente HTTP asíncrono para interactuar con la API corporativa de OTP / Firma Electrónica Nexura.
    Endpoints:
      - POST /api/otp/authorization: Generación de token JWT Bearer.
      - POST /api/generar: Generación y emisión de código OTP.
      - POST /api/validar: Validación de código OTP ingresado por el usuario.
    """

    def __init__(self):
        self._cached_token: Optional[str] = OTP_STATIC_BEARER_TOKEN if OTP_STATIC_BEARER_TOKEN else None
        self._token_expires_at: Optional[datetime] = None
        self._timeout = 15.0
        self._simulation_cache: Dict[str, str] = {}

    async def get_authorization_token(self, force_refresh: bool = False) -> str:
        """
        Obtiene el token Bearer activo. Si se configuró un OTP_STATIC_BEARER_TOKEN lo usa;
        de lo contrario, se autentica automáticamente contra el endpoint de autorización.
        """
        if OTP_STATIC_BEARER_TOKEN and not force_refresh:
            return OTP_STATIC_BEARER_TOKEN

        if not force_refresh and self._cached_token and not self._is_token_expired():
            return self._cached_token

        self._cached_token = None
        self._token_expires_at = None

        auth_url = f"{OTP_BASE_URL}/api/otp/authorization"
        payload = {
            "name": OTP_AUTH_NAME,
            "password": OTP_AUTH_PASSWORD
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        logger.info(f"[OtpClient] Solicitando nuevo token de autorización a: {auth_url}")
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(auth_url, json=payload, headers=headers)

            if response.status_code != 200:
                logger.error(f"[OtpClient] Error HTTP al autorizar ({response.status_code}): {response.text}")
                raise PipelineException(
                    etapa="OTP_AUTHORIZATION",
                    mensaje="No fue posible autenticar con el servicio corporativo de OTP.",
                    detalle_tecnico=f"HTTP {response.status_code}: {response.text}",
                    status_code=502
                )

            data = response.json()
            access_token = data.get("access_token")
            if not access_token:
                desc = data.get("respuesta", {}).get("descripcion") or str(data)
                logger.error(f"[OtpClient] Autorización denegada por servicio OTP: {desc}")
                raise PipelineException(
                    etapa="OTP_AUTHORIZATION",
                    mensaje="Acceso denegado al servicio de autenticación OTP.",
                    detalle_tecnico=desc,
                    status_code=502
                )

            self._cached_token = access_token
            expires_at_str = data.get("expires_at")
            if expires_at_str:
                try:
                    self._token_expires_at = datetime.strptime(expires_at_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    self._token_expires_at = None

            logger.info("[OtpClient] Token de autorización obtenido y cacheado exitosamente.")
            return self._cached_token

        except PipelineException:
            raise
        except Exception as e:
            logger.error(f"[OtpClient] Excepción de conexión al autorizar OTP: {e}")
            raise PipelineException(
                etapa="OTP_AUTHORIZATION",
                mensaje="Fallo de red al conectar con el servicio de autorización OTP.",
                detalle_tecnico=str(e),
                status_code=504
            )

    def _is_token_expired(self) -> bool:
        if not self._token_expires_at:
            return False
        return (self._token_expires_at - datetime.now()).total_seconds() < 60

    async def generar_otp(
        self,
        user_identifier: str,
        email: str,
        cellphone: Optional[str] = None,
        type_otp: int = 3,
        time_validate: Optional[int] = None,
        blocking: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Invoca POST /api/generar para crear un nuevo código OTP.
        """
        user_formatted = f"${user_identifier}" if not user_identifier.startswith("$") else user_identifier

        # Modo Simulación para pruebas locales si se activa por entorno
        if OTP_SIMULATION_MODE:
            simulated_code = str(random.randint(100000, 999999))
            self._simulation_cache[user_formatted] = simulated_code
            logger.info(f"[OtpClient] [MODO SIMULACIÓN] Código generado para {user_formatted}: {simulated_code}")
            return {
                "token": simulated_code,
                "respuesta": {
                    "codigo": 0,
                    "descripcion": "Token generado con exito (MODO SIMULACION)"
                }
            }

        token = await self.get_authorization_token()
        url = f"{OTP_BASE_URL}/api/generar"

        payload = {
            "user": user_formatted,
            "cellphone": cellphone or OTP_DEFAULT_CELLPHONE,
            "email": email,
            "type_otp": type_otp,
            "time_validate": time_validate or OTP_TIME_VALIDATE,
            "blocking": blocking or OTP_BLOCKING_ATTEMPTS
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        logger.info(f"[OtpClient] Solicitando generación de OTP para usuario {user_formatted} ({email})")
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload, headers=headers)

                # Si el token caducó o fue invalidado por el servidor, re-autenticar y reintentar 1 vez
                if response.status_code == 401:
                    logger.warning("[OtpClient] Token 401 expirado/inválido en generar_otp. Re-autenticando y reintentando...")
                    token = await self.get_authorization_token(force_refresh=True)
                    headers["Authorization"] = f"Bearer {token}"
                    response = await client.post(url, json=payload, headers=headers)

            if response.status_code != 200:
                logger.error(f"[OtpClient] Error HTTP al generar OTP ({response.status_code}): {response.text}")
                raise PipelineException(
                    etapa="OTP_GENERACION",
                    mensaje="El proveedor de OTP no pudo procesar la solicitud de generación.",
                    detalle_tecnico=f"HTTP {response.status_code}: {response.text}",
                    status_code=502
                )

            data = response.json()
            codigo = data.get("respuesta", {}).get("codigo")
            if str(codigo).strip() != "0":
                desc = data.get("respuesta", {}).get("descripcion") or "Error en proveedor OTP"
                logger.warning(f"[OtpClient] Proveedor retornó código de rechazo ({codigo}): {desc}")
                raise PipelineException(
                    etapa="OTP_GENERACION",
                    mensaje="No fue posible generar el código de verificación OTP.",
                    detalle_tecnico=desc,
                    status_code=400
                )

            logger.info(f"[OtpClient] OTP generado con éxito para {user_formatted}.")
            return data

        except PipelineException:
            raise
        except Exception as e:
            logger.error(f"[OtpClient] Error de comunicación al generar OTP: {e}")
            raise PipelineException(
                etapa="OTP_GENERACION",
                mensaje="Fallo al contactar el servicio de generación de OTP.",
                detalle_tecnico=str(e),
                status_code=504
            )

    async def validar_otp(
        self,
        user_identifier: str,
        otp_code: str,
        type_otp: int = 3,
        aplication: int = 1
    ) -> Dict[str, Any]:
        """
        Invoca POST /api/validar para verificar si el código OTP ingresado es válido y vigente.
        """
        user_formatted = f"${user_identifier}" if not user_identifier.startswith("$") else user_identifier
        code_str = str(otp_code).strip()

        # Modo Simulación para pruebas locales
        if OTP_SIMULATION_MODE:
            expected = self._simulation_cache.get(user_formatted)
            if expected and expected == code_str:
                logger.info(f"[OtpClient] [MODO SIMULACIÓN] Código {code_str} validado con éxito para {user_formatted}.")
                return {
                    "validado": True,
                    "codigo": 0,
                    "mensaje": "Token validado con éxito (SIMULACION)."
                }
            else:
                logger.warning(f"[OtpClient] [MODO SIMULACIÓN] Código incorrecto. Esperado={expected}, Recibido={code_str}")
                return {
                    "validado": False,
                    "codigo": 1,
                    "mensaje": "Código de verificación incorrecto o expirado."
                }

        token = await self.get_authorization_token()
        url = f"{OTP_BASE_URL}/api/validar"

        clean_code = int(code_str) if code_str.isdigit() else code_str

        payload = {
            "user": user_formatted,
            "type_otp": type_otp,
            "aplication": aplication,
            "token": clean_code
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        logger.info(f"[OtpClient] Validando OTP para usuario {user_formatted}")
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload, headers=headers)

                # Si el token caducó o fue invalidado por el servidor, re-autenticar y reintentar 1 vez
                if response.status_code == 401:
                    logger.warning("[OtpClient] Token 401 expirado/inválido en validar_otp. Re-autenticando y reintentando...")
                    token = await self.get_authorization_token(force_refresh=True)
                    headers["Authorization"] = f"Bearer {token}"
                    response = await client.post(url, json=payload, headers=headers)

            if response.status_code != 200:
                logger.error(f"[OtpClient] Error HTTP al validar OTP ({response.status_code}): {response.text}")
                raise PipelineException(
                    etapa="OTP_VALIDACION",
                    mensaje="El proveedor de OTP no pudo procesar la validación.",
                    detalle_tecnico=f"HTTP {response.status_code}: {response.text}",
                    status_code=502
                )

            data = response.json()
            codigo = data.get("respuesta", {}).get("codigo")
            if str(codigo).strip() != "0":
                desc = data.get("respuesta", {}).get("descripcion") or "Código de verificación inválido o expirado."
                logger.warning(f"[OtpClient] Validación fallida para {user_formatted} (código {codigo}): {desc}")
                return {
                    "validado": False,
                    "codigo": codigo,
                    "mensaje": desc
                }

            logger.info(f"[OtpClient] OTP validado exitosamente para {user_formatted}.")
            return {
                "validado": True,
                "codigo": 0,
                "mensaje": "Token validado con éxito."
            }

        except PipelineException:
            raise
        except Exception as e:
            logger.error(f"[OtpClient] Error al validar código OTP: {e}")
            raise PipelineException(
                etapa="OTP_VALIDACION",
                mensaje="Fallo al contactar el servicio de validación de OTP.",
                detalle_tecnico=str(e),
                status_code=504
            )


otp_client = OtpClient()
