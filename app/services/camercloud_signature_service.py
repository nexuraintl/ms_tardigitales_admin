"""
Cliente asíncrono para firma digital desatendida (PAdES) de PDFs
mediante la API de CamerCloud (Viafirma Fortress).

Flujo oficial de firma desatendida (Manual Viafirma Fortress, sección 1.6.5):
1. POST {base_url}/oauth2/v1/token (client_credentials) -> access_token (cacheado en memoria)
2. Resolución de certificateCode (configurado o autodescubierto vía GET /api/v1/client/{client_id}/certificate)
3. POST {base_url}/api/v1/signature (PADES_B, RSA_SHA256, ENVELOPED) -> authCode, exeCode
4. POST {base_url}/api/v1/signature/{exeCode}/execute -> bytesB64 firmado, signatureCode
"""

import asyncio
import base64
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

import httpx

from app.constants import (
    CAMERCLOUD_BASE_URL,
    CAMERCLOUD_CERTIFICATE_CODE,
    CAMERCLOUD_CERTIFICATE_PASSWORD,
    CAMERCLOUD_CLIENT_ID,
    CAMERCLOUD_CLIENT_SECRET,
    CAMERCLOUD_REDIRECT_URI,
    CAMERCLOUD_TIMEOUT_SECONDS,
)

logger = logging.getLogger("camercloud_signature")
COLOMBIA_TZ = timezone(timedelta(hours=-5))


class CamercloudError(Exception):
    """Error base en comunicación o procesamiento con CamerCloud."""


class CamercloudNoCertificateError(CamercloudError):
    """El sistema cliente en CamerCloud no tiene un certificado .p12 activo para firma desatendida."""


class CamercloudSignatureService:
    _token_lock: Optional[asyncio.Lock] = None
    _cached_token: Optional[str] = None
    _token_expires_at: float = 0.0
    _cached_certificate_code: Optional[str] = None

    def __init__(
        self,
        base_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        certificate_code: Optional[str] = None,
        certificate_password: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        self.base_url = (base_url or CAMERCLOUD_BASE_URL).rstrip("/")
        self.client_id = (client_id or CAMERCLOUD_CLIENT_ID).strip()
        self.client_secret = (client_secret or CAMERCLOUD_CLIENT_SECRET).strip()
        self.redirect_uri = (redirect_uri or CAMERCLOUD_REDIRECT_URI).strip() or "*"
        self.certificate_code = (
            certificate_code if certificate_code is not None else CAMERCLOUD_CERTIFICATE_CODE
        ).strip()
        self.certificate_password = (
            certificate_password if certificate_password is not None else CAMERCLOUD_CERTIFICATE_PASSWORD
        ).strip()
        self.timeout = float(timeout_seconds or CAMERCLOUD_TIMEOUT_SECONDS)

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        if cls._token_lock is None:
            cls._token_lock = asyncio.Lock()
        return cls._token_lock

    @classmethod
    def invalidate_cache(cls) -> None:
        cls._cached_token = None
        cls._token_expires_at = 0.0
        cls._cached_certificate_code = None

    async def obtener_token(self, force_refresh: bool = False) -> str:
        """
        Obtiene y cachea el token OAuth2 Bearer de cliente en memoria.
        Evita consumir llamadas innecesarias a /oauth2/v1/token mientras el token siga vigente.
        """
        now = time.time()
        if not force_refresh and self.__class__._cached_token and now < self.__class__._token_expires_at:
            return self.__class__._cached_token

        async with self._get_lock():
            now = time.time()
            if not force_refresh and self.__class__._cached_token and now < self.__class__._token_expires_at:
                return self.__class__._cached_token

            url = f"{self.base_url}/oauth2/v1/token"
            form_data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "grant_type": "client_credentials",
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    url,
                    data=form_data,
                    headers={"Accept": "application/json"},
                )

            if resp.status_code != 200:
                raise CamercloudError(
                    f"Error autenticando en CamerCloud (HTTP {resp.status_code}): {resp.text[:300]}"
                )

            data = resp.json()
            token = str(data.get("access_token") or "").strip()
            if not token:
                raise CamercloudError("CamerCloud no devolvió access_token en /oauth2/v1/token.")

            expires_in = int(data.get("expires_in") or 3600)
            ttl = max(expires_in - 60, 30)
            self.__class__._cached_token = token
            self.__class__._token_expires_at = time.time() + ttl
            return token

    async def resolver_certificate_code(self, token: str) -> str:
        """
        Retorna el certificateCode configurado o intenta autodescubrir el primer certificado
        activo alojado en el cliente vía GET /api/v1/client/{client_id}/certificate.
        """
        if self.certificate_code:
            return self.certificate_code
        if self.__class__._cached_certificate_code:
            return self.__class__._cached_certificate_code

        url = f"{self.base_url}/api/v1/client/{self.client_id}/certificate"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )

        if resp.status_code != 200:
            raise CamercloudError(
                f"Error consultando certificados del cliente {self.client_id} (HTTP {resp.status_code}): {resp.text[:300]}"
            )

        certs = resp.json()
        if not isinstance(certs, list) or not certs:
            raise CamercloudNoCertificateError(
                f"El cliente '{self.client_id}' en CamerCloud no tiene ningún certificado .p12 cargado para firma desatendida."
            )

        first_code = str((certs[0] or {}).get("code") or "").strip()
        if not first_code:
            raise CamercloudNoCertificateError(
                f"El cliente '{self.client_id}' retornó certificados sin atributo 'code'."
            )

        self.__class__._cached_certificate_code = first_code
        return first_code

    async def descargar_pdf_firmado(self, signature_code: str) -> Optional[bytes]:
        """
        Descarga el binario PDF firmado desde CamerCloud utilizando su signatureCode.
        Usado únicamente como respaldo si un certificado firmado carece de caché local.
        """
        code = str(signature_code or "").strip()
        if not code:
            return None

        token = await self.obtener_token()
        url = f"{self.base_url}/api/v1/signature/download/{code}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 401:
                token = await self.obtener_token(force_refresh=True)
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                )

        if resp.status_code == 200 and resp.content:
            return resp.content

        logger.warning(
            "[CamerCloud] No fue posible descargar el documento %s (HTTP %s): %s",
            code,
            resp.status_code,
            resp.text[:200],
        )
        return None

    async def firmar_pdf_desatendida(
        self,
        pdf_bytes: bytes,
        n_certificado: str,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Firma digitalmente un documento PDF en modo desatendido (PAdES_B / RSA_SHA256 / ENVELOPED).
        Retorna el binario firmado, signature_code, auth_code y fecha_firma.
        """
        if not pdf_bytes:
            raise CamercloudError("El contenido PDF a firmar está vacío.")

        token = await self.obtener_token()
        cert_code = await self.resolver_certificate_code(token)

        doc_name = filename or f"certificado-{n_certificado}.pdf"
        pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")

        req_payload: Dict[str, Any] = {
            "certificateCode": cert_code,
            "signatureConfigurations": [
                {
                    "ref": str(n_certificado),
                    "signatureType": "PADES_B",
                    "signatureAlgorithm": "RSA_SHA256",
                    "packaging": "ENVELOPED",
                    "document": {
                        "name": doc_name,
                        "bytesB64": pdf_b64,
                    },
                }
            ],
        }
        if self.certificate_password:
            req_payload["certificatePassword"] = self.certificate_password

        sig_url = f"{self.base_url}/api/v1/signature"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp_req = await client.post(
                sig_url,
                json=req_payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            if resp_req.status_code == 401:
                token = await self.obtener_token(force_refresh=True)
                resp_req = await client.post(
                    sig_url,
                    json=req_payload,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )

            if resp_req.status_code != 200:
                raise CamercloudError(
                    f"Error creando solicitud de firma en CamerCloud (HTTP {resp_req.status_code}): {resp_req.text[:300]}"
                )

            req_data = resp_req.json()
            auth_code = str(req_data.get("authCode") or "").strip()
            exe_code = str(req_data.get("exeCode") or "").strip()
            if not exe_code:
                raise CamercloudError(
                    f"CamerCloud no retornó exeCode en /api/v1/signature: {req_data}"
                )

            exec_url = f"{self.base_url}/api/v1/signature/{exe_code}/execute"
            resp_exec = await client.post(
                exec_url,
                json={},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )

        if resp_exec.status_code != 200:
            raise CamercloudError(
                f"Error ejecutando firma desatendida en CamerCloud (HTTP {resp_exec.status_code}): {resp_exec.text[:300]}"
            )

        exec_data = resp_exec.json()
        item = exec_data[0] if isinstance(exec_data, list) and exec_data else (exec_data if isinstance(exec_data, dict) else {})
        signature_code = str(item.get("signatureCode") or "").strip()
        signed_b64 = item.get("bytesB64") or item.get("documentB64") or ""

        signed_pdf_bytes: Optional[bytes] = None
        if signed_b64:
            signed_pdf_bytes = base64.b64decode(signed_b64)
        elif signature_code:
            signed_pdf_bytes = await self.descargar_pdf_firmado(signature_code)

        if not signed_pdf_bytes:
            raise CamercloudError(
                f"CamerCloud ejecutó la firma (signatureCode={signature_code}) pero no devolvió el PDF firmado."
            )

        fecha_firma = datetime.now(COLOMBIA_TZ).strftime("%Y-%m-%d %H:%M:%S")
        return {
            "firmado": True,
            "pdf_bytes": signed_pdf_bytes,
            "signature_code": signature_code,
            "auth_code": auth_code,
            "fecha_firma": fecha_firma,
        }
