import os
import time
import logging
import httpx
from typing import Dict, Any, Optional
from app.services.auditoria_service import AuditoriaService
from app.repositories.tarjetas_repository import TarjetasRepository

logger = logging.getLogger("jcc_client")

PROD_BASE_URL = os.getenv("JCC_API_BASE_URL", "https://apitarjetas.jcc.gov.co").rstrip("/")

JCC_API_BEARER_TOKEN = os.getenv(
    "JCC_API_BEARER_TOKEN",
    "kvllYI0urrjVdqYOUTJZw7p5qIG9U5c8XlnNs60MMfC5yYArY3JuntakvllYI0urrjVdqYOUTJZw7p5qIG9U5c8XlnNs60MMfC5yYArY3"
)


class JccClient:

    def __init__(self, auditoria_service: Optional[AuditoriaService] = None):
        self.last_url: str = ""
        self.last_metodo: str = "POST"
        self.auditoria = auditoria_service or AuditoriaService(TarjetasRepository())

    def _normalizar_respuesta(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if "data" in data and isinstance(data["data"], dict):
            inner_data = data["data"]
            if "respuesta" in inner_data and isinstance(inner_data["respuesta"], dict):
                return inner_data["respuesta"]
        return data

    def _limpiar_documento(self, documento: str, tipo_tarjeta: str) -> str:
        """
        Limpia el documento según el tipo de tarjeta.
        - Contadores: Solo alfanuméricos (quita guiones, puntos, espacios).
        - Sociedades: Mantiene el guion (-) y alfanuméricos (quita puntos, espacios).
        """
        if tipo_tarjeta == "sociedades":
            return "".join(c for c in str(documento).strip() if c.isalnum() or c == "-")
        else:
            return "".join(c for c in str(documento).strip() if c.isalnum())

    async def consultar_registro(
        self,
        documento: str,
        tipo_tarjeta: str = "contadores",
        tipo: str = "",
        client_id: Optional[int] = None
    ) -> Dict[str, Any]:
        documento_limpio = self._limpiar_documento(documento, tipo_tarjeta) if documento else ""

        prod_endpoint = "/sociedades/" if tipo_tarjeta == "sociedades" else "/contadores/"
        url = f"{PROD_BASE_URL}{prod_endpoint}"
        self.last_url = url
        self.last_metodo = "POST"

        tipo_final = tipo if tipo else ("modificacion" if tipo_tarjeta == "sociedades" else "primeraVez")

        payload = {
            "tipo": tipo_final,
            "documento": documento_limpio,
            "cambiarEstado": False
        }

        headers = {
            "Authorization": f"Bearer {JCC_API_BEARER_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        resolved_client_id = client_id or int(os.getenv("CLIENT_ID", "20001"))
        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
                response = await client.post(url, json=payload, headers=headers)

            duracion_ms = int((time.perf_counter() - start_time) * 1000)

            # Extraer cuerpo para auditoría
            try:
                cuerpo_audit = response.json() if response.status_code == 200 else {"http_status": response.status_code, "body": response.text}
            except Exception:
                cuerpo_audit = {"http_status": response.status_code, "raw": response.text}

            # Registro automático e incondicional de auditoría API (Obligación Contractual)
            try:
                await self.auditoria.registrar(
                    client_id=resolved_client_id,
                    tipo_tarjeta=tipo_tarjeta,
                    tipo=tipo_final,
                    metodo="POST",
                    url=url,
                    parametros_peticion=payload,
                    cuerpo_respuesta=cuerpo_audit,
                    duracion_ms=duracion_ms
                )
            except Exception as audit_err:
                logger.error(f"[JccClient] Error al registrar auditoría API: {audit_err}")

            if response.status_code == 200:
                raw_data = response.json()
                data = self._normalizar_respuesta(raw_data)

                if "error" in data and data["error"]:
                    return {
                        "encontrado": False,
                        "data": None,
                        "disponibles": [],
                        "es_error_conexion": False,
                        "error": data["error"]
                    }
                
                disponibles = data.get("disponibles", [])
                pdf = data.get("pdf")
                
                if not disponibles and not pdf:
                    return {
                        "encontrado": False,
                        "data": None,
                        "disponibles": [],
                        "es_error_conexion": False
                    }

                disponibles_limpios = []
                for raw_item in (disponibles if disponibles else [{}]):
                    foto_b64 = pdf or raw_item.get("FOTO") or raw_item.get("foto") or ""
                    if not foto_b64 or "no existe" in str(foto_b64).lower() or "error" in str(foto_b64).lower():
                        foto_b64 = None
                    elif not foto_b64.startswith("data:"):
                        foto_b64 = f"data:image/jpeg;base64,{foto_b64}"

                    clean_record = {
                        "no_tarjeta": raw_item.get("NO_TARJETA") or raw_item.get("no_tarjeta", ""),
                        "nombres": raw_item.get("NOMBRES") or raw_item.get("nombres", ""),
                        "primer_apellido": raw_item.get("PRIMER_APELLIDO") or raw_item.get("primer_apellido", ""),
                        "segundo_apellido": raw_item.get("SEGUNDO_APELLIDO") or raw_item.get("segundo_apellido", ""),
                        "no_expd": raw_item.get("NO_EXPD") or raw_item.get("EXPEDIENTE") or raw_item.get("no_expd", 0),
                        "tipo_documento": raw_item.get("TIPO_DOCUMENTO") or raw_item.get("tipo_documento", "CC"),
                        "no_documento": str(raw_item.get("NO_DOCUMENTO") or raw_item.get("no_documento") or documento_limpio),
                        "universidad": raw_item.get("UNIVERSIDAD") or raw_item.get("universidad", ""),
                        "estado_contador": raw_item.get("ESTADO_CONTADOR") or raw_item.get("estado_contador", "ACTIVO"),
                        "resolucion": raw_item.get("RESOLUCION") or raw_item.get("resolucion", ""),
                        "fecha_estado": raw_item.get("FECHA_ESTADO") or raw_item.get("fecha_estado"),
                        "fecha_radicacion": raw_item.get("FECHA_RADICACION") or raw_item.get("fecha_radicacion"),
                        "fecha_resolucion": raw_item.get("FECH_RESOLU") or raw_item.get("FECHA_RESOLUCION") or raw_item.get("fecha_resolucion"),
                        "acta_jcc": raw_item.get("ACTA_JCC") or raw_item.get("acta_jcc"),
                        "fecha_grado": raw_item.get("FECHA_GRADO") or raw_item.get("fecha_grado"),
                        "seccional": raw_item.get("SECCIONAL") or raw_item.get("seccional", ""),
                        "correo": raw_item.get("EMAIL") or raw_item.get("correo", ""),
                        "razon_social": raw_item.get("RAZON_SOCIAL") or raw_item.get("razon_social", ""),
                        "nit": str(raw_item.get("NIT") or raw_item.get("nit") or documento_limpio),
                        "tipo_sociedad": raw_item.get("TIPO_SOCIEDAD") or raw_item.get("tipo_sociedad", "SOCIEDAD DE CONTADORES"),
                        "inscripcion": raw_item.get("INSCRIPCION") or raw_item.get("inscripcion"),
                        "estado_sociedad": raw_item.get("ESTADO_SOCIEDAD") or raw_item.get("estado_sociedad", "ACTIVO"),
                        "estado_solicitud": raw_item.get("ESTADO_SOLICITUD") or raw_item.get("estado_solicitud"),
                        "tipo_solicitud": raw_item.get("TIPO_SOLICITUD") or raw_item.get("tipo_solicitud"),
                        "representante_legal": raw_item.get("REPRESENTANTE_LEGAL") or raw_item.get("representante_legal", ""),
                        "foto": foto_b64,
                        "pdf": foto_b64
                    }
                    disponibles_limpios.append(clean_record)

                return {
                    "encontrado": True,
                    "es_error_conexion": False,
                    "data": disponibles_limpios[0] if disponibles_limpios else None,
                    "disponibles": disponibles_limpios
                }
            else:
                es_servidor = response.status_code >= 500
                return {
                    "encontrado": False,
                    "es_error_conexion": es_servidor,
                    "data": None,
                    "error": f"Error de comunicación HTTP {response.status_code} desde la API JCC"
                }

        except Exception as e:
            duracion_ms = int((time.perf_counter() - start_time) * 1000)
            try:
                await self.auditoria.registrar(
                    client_id=resolved_client_id,
                    tipo_tarjeta=tipo_tarjeta,
                    tipo=tipo_final,
                    metodo="POST",
                    url=url,
                    parametros_peticion=payload,
                    cuerpo_respuesta={"error_conexion": str(e)},
                    duracion_ms=duracion_ms
                )
            except Exception as audit_err:
                logger.error(f"[JccClient] Error al registrar auditoría API tras fallo de red: {audit_err}")

            return {
                "encontrado": False,
                "es_error_conexion": True,
                "data": None,
                "error": f"Error de conexión con la API de la JCC (posible VPN inactiva o servicio inaccesible): {str(e)}"
            }

