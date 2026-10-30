import logging
import httpx
from typing import Dict, Any, Optional
from app.repositories.tarjetas_repository import TarjetasRepository
from app.integrations.otp_client import otp_client, OtpClient
from app.core.exceptions import PipelineException
from app.constants import OTP_TIME_VALIDATE, PREPROD_PHP_BRIDGE_URL

logger = logging.getLogger("otp_service")


class OtpService:
    """
    Servicio de orquestación para la emisión y validación de OTP en la activación
    de credenciales digitales desde la App Móvil.
    """

    def __init__(self, repository: Optional[TarjetasRepository] = None, client: Optional[OtpClient] = None):
        self.repository = repository or TarjetasRepository()
        self.otp_client = client or otp_client

    @staticmethod
    def enmascarar_correo(email: Optional[str]) -> str:
        """
        Enmascara una dirección de correo electrónico para proteger la privacidad del usuario.
        Ejemplo: kateagudelo2@hotmail.com -> k***2@hotmail.com
        """
        if not email or "@" not in email:
            return "***@***.***"

        partes = email.strip().split("@")
        usuario = partes[0]
        dominio = partes[1]

        if len(usuario) <= 2:
            usuario_enmascarado = f"{usuario[0]}*"
        else:
            usuario_enmascarado = f"{usuario[0]}***{usuario[-1]}"

        return f"{usuario_enmascarado}@{dominio}"

    async def solicitar_otp(
        self,
        hash_sha256: str,
        expediente: str,
        client_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        1. Busca la tarjeta digital emitida mediante su hash SHA-256 (del QR).
        2. Valida que el número de expediente digitado por el usuario coincida con el registrado.
        3. Obtiene el correo electrónico oficial del titular.
        4. Genera el código OTP a través del servicio corporativo Nexura y entrega el correo enmascarado.
        """
        hash_limpio = str(hash_sha256).strip()
        exp_input = str(expediente).strip()

        # 1. Consultar la tarjeta por su hash canónico
        tarjeta = await self.repository.get_by_hash(hash_sha256=hash_limpio, client_id=client_id)
        if not tarjeta:
            logger.warning(f"[OtpService] Tarjeta no encontrada con hash: {hash_limpio}")
            raise PipelineException(
                etapa="OTP_SOLICITUD",
                mensaje="No se encontró ninguna tarjeta asociada al hash suministrado.",
                cliente_id=client_id,
                status_code=404
            )

        # 2. Validar coincidencia de expediente
        exp_bd = str(tarjeta.get("no_expd") or "").strip()
        if not exp_bd or exp_bd != exp_input:
            logger.warning(
                f"[OtpService] Discrepancia de expediente para hash {hash_limpio}. "
                f"Esperado={exp_bd}, Recibido={exp_input}"
            )
            raise PipelineException(
                etapa="OTP_SOLICITUD",
                mensaje="El número de expediente suministrado no coincide con el registrado en la credencial.",
                cliente_id=client_id,
                status_code=400
            )

        # 3. Validar existencia de correo oficial
        correo = (tarjeta.get("correo") or "").strip()
        if not correo or "@" not in correo:
            logger.warning(f"[OtpService] Tarjeta {hash_limpio} no posee un correo electrónico válido.")
            raise PipelineException(
                etapa="OTP_SOLICITUD",
                mensaje="El titular de la tarjeta no tiene un correo electrónico válido registrado en la JCC.",
                cliente_id=client_id,
                status_code=422
            )

        documento_canonico = str(tarjeta.get("no_documento") or tarjeta.get("nit") or exp_input).strip()

        # 4. Generar código OTP mediante el servicio corporativo
        resp_otp = await self.otp_client.generar_otp(
            user_identifier=documento_canonico,
            email=correo,
            time_validate=OTP_TIME_VALIDATE
        )

        codigo_generado = resp_otp.get("token")
        correo_enmascarado = self.enmascarar_correo(correo)

        msg_log = (
            f"[OtpService] OTP generado exitosamente para doc '{documento_canonico}' (Exp: {exp_input}) "
            f"| Token: {codigo_generado} | Correo: {correo} -> {correo_enmascarado}"
        )
        print(msg_log)
        logger.info(msg_log)

        # 5. Despacho de correo OTP a través del puente de PHP NX9 (sxMailer con correo controlado)
        try:
            bridge_base = PREPROD_PHP_BRIDGE_URL.rstrip("/")
            if not bridge_base.endswith("/api/TarjetasDigitales"):
                bridge_base = f"{bridge_base}/api/TarjetasDigitales"
            url_enviar_otp = f"{bridge_base}/enviarOtp"

            headers_bridge = {
                "Host": "local-jcc.nexura.com.co",
                "Content-Type": "application/json"
            }
            nombre_titular = tarjeta.get("nombre") or tarjeta.get("razon_social") or "Usuario"
            payload_email = {
                "correo": correo,
                "nombre": nombre_titular,
                "codigo_otp": str(codigo_generado),
                "expira_minutos": OTP_TIME_VALIDATE
            }

            logger.info(f"[OtpService] Despachando correo OTP a puente NX9: {url_enviar_otp}...")
            async with httpx.AsyncClient(timeout=15.0) as http_client:
                resp_mail = await http_client.post(url_enviar_otp, json=payload_email, headers=headers_bridge)
                if resp_mail.status_code == 200:
                    data_mail = resp_mail.json()
                    log_despacho = (
                        f"[OtpService] Correo OTP despachado vía puente NX9 -> Destino: {data_mail.get('correo_destinatario')} "
                        f"(Original: {data_mail.get('correo_original')}, Controlado: {data_mail.get('es_controlado')})"
                    )
                    print(log_despacho)
                    logger.info(log_despacho)
                else:
                    log_warn = f"[OtpService] Advertencia: Puente NX9 retornó HTTP {resp_mail.status_code}: {resp_mail.text}"
                    print(log_warn)
                    logger.warning(log_warn)
        except Exception as err_mail:
            log_err = f"[OtpService] No se pudo despachar correo OTP vía puente NX9: {err_mail}"
            print(log_err)
            logger.error(log_err)

        return {
            "status": "success",
            "message": "Código de verificación generado y despachado.",
            "correo_enmascarado": correo_enmascarado,
            "expira_en_minutos": OTP_TIME_VALIDATE
        }

    async def validar_otp(
        self,
        hash_sha256: str,
        token: str,
        expediente: Optional[str] = None,
        client_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Valida el código OTP ingresado por el usuario en la App Móvil para la tarjeta referenciada por su hash.
        """
        hash_limpio = str(hash_sha256).strip()
        token_limpio = str(token).strip()

        tarjeta = await self.repository.get_by_hash(hash_sha256=hash_limpio, client_id=client_id)
        if not tarjeta:
            logger.warning(f"[OtpService] Validación rechazada: Tarjeta no encontrada con hash {hash_limpio}")
            raise PipelineException(
                etapa="OTP_VALIDACION",
                mensaje="Tarjeta no encontrada con el hash suministrado.",
                cliente_id=client_id,
                status_code=404
            )

        if expediente:
            exp_bd = str(tarjeta.get("no_expd") or "").strip()
            if exp_bd != str(expediente).strip():
                raise PipelineException(
                    etapa="OTP_VALIDACION",
                    mensaje="El número de expediente no coincide con la credencial.",
                    cliente_id=client_id,
                    status_code=400
                )

        documento_canonico = str(tarjeta.get("no_documento") or tarjeta.get("nit") or hash_limpio).strip()

        resultado = await self.otp_client.validar_otp(
            user_identifier=documento_canonico,
            otp_code=token_limpio
        )

        if not resultado.get("validado"):
            mensaje_error = resultado.get("mensaje") or "Código de verificación inválido o expirado."
            raise PipelineException(
                etapa="OTP_VALIDACION",
                mensaje=mensaje_error,
                cliente_id=client_id,
                status_code=400
            )

        print(f"[OtpService] OTP validado satisfactoriamente para doc '{documento_canonico}' (Hash: {hash_limpio}).")
        logger.info(f"[OtpService] OTP validado satisfactoriamente para doc '{documento_canonico}'.")

        return {
            "status": "success",
            "validado": True,
            "message": "Código OTP validado correctamente."
        }


otp_service = OtpService()
