import hashlib
import logging
from datetime import datetime, date
from typing import Dict, Any, Optional, Tuple
from fastapi import HTTPException, status
from app.constants import CAMERCLOUD_ENABLED, CAMERCLOUD_FALLBACK_UNSIGNED
from app.repositories.certificados_repository import CertificadosRepository
from app.services.camercloud_signature_service import (
    CamercloudError,
    CamercloudNoCertificateError,
    CamercloudSignatureService,
)
from app.services.certificado_pdf_service import CertificadoPdfService

logger = logging.getLogger("certificados_service")


class CertificadosService:
    def __init__(
        self,
        repository: Optional[CertificadosRepository] = None,
        camercloud_service: Optional[CamercloudSignatureService] = None,
    ):
        self.repo = repository or CertificadosRepository()
        self.pdf_service = CertificadoPdfService()
        self.camercloud_service = camercloud_service or CamercloudSignatureService()

    def _formatear_para_mfe(self, record: Dict[str, Any]) -> Dict[str, Any]:
        tipo_raw = (record.get("tipo") or "").lower()
        is_contador = tipo_raw == "contador"
        detalles = record.get("payload_detalles") or {}
        
        def _as_str(val: Any) -> Optional[str]:
            if val is None or val == "":
                return None
            return str(val)

        # Antecedentes
        raw_antecedentes = detalles.get("ANTECEDENTES") or []
        formatted_antecedents = []
        for ant in raw_antecedentes:
            formatted_antecedents.append({
                "sanctionType": str(ant.get("SAN_TIPO") or ""),
                "durationMonths": ant.get("SAN_MESES"),
                "resolutionNumber": str(ant.get("SAN_RESOLUCION") or ""),
                "resolutionDate": str(ant.get("SAN_FECHA_RESOLUCION") or ""),
                "enforcementDate": str(ant.get("SAN_FECHA_EJECUTORIA") or ""),
                "completionDate": _as_str(ant.get("SAN_FECHA_FIN"))
            })

        # Formateo de fechas
        gen_at = str(record.get("fecha_generacion") or "")
        firm_at = _as_str(record.get("fecha_firma_onac"))

        return {
            "id": f"{tipo_raw}-{record.get('n_certificado')}",
            "type": "Contador" if is_contador else "Sociedad",
            "certificateNumber": str(record.get("n_certificado") or ""),
            "identifier": str(record.get("documento") or ""),
            "holder": str(record.get("nombre_titular") or ""),
            "generatedAt": gen_at,
            "signedAt": firm_at,
            "status": str(record.get("estado") or "ACTIVO"),
            "professionalCard": _as_str(detalles.get("CON_NRO_TARJETA")) if is_contador else None,
            "cardType": _as_str(detalles.get("CON_TIPO_TARJETA")) if is_contador else None,
            "documentMunicipality": _as_str(detalles.get("MUNICIPIO_DOCUMENTO")) if is_contador else None,
            "documentDepartment": _as_str(detalles.get("DEPARTAMENTO_DOCUMENTO")) if is_contador else None,
            "companyCode": _as_str(detalles.get("SOC_CODIGO")) if not is_contador else None,
            "legalRepresentative": _as_str(detalles.get("SOC_REPRESENTANTE_LEGAL")) if not is_contador else None,
            "municipality": _as_str(detalles.get("MUNICIPIO")) if not is_contador else None,
            "department": _as_str(detalles.get("DEPARTAMENTO")) if not is_contador else None,
            "updatedAt": str(detalles.get("CON_FECHA_ACTUALIZACION") or detalles.get("SOC_FECHA_ACTUALIZACION") or gen_at),
            "antecedents": formatted_antecedents
        }

    async def listar_certificados(
        self,
        client_id: Optional[int] = None,
        search: Optional[str] = None,
        tipo: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        raw_result = await self.repo.get_all(client_id=client_id, search=search, tipo=tipo, page=page, page_size=page_size)
        items = [self._formatear_para_mfe(r) for r in raw_result["items"]]
        return {"total": raw_result["total"], "items": items}

    async def obtener_por_numero(self, n_certificado: str, client_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        record = await self.repo.get_by_n_certificado(n_certificado, client_id=client_id)
        if not record:
            return None
        return self._formatear_para_mfe(record)

    async def obtener_pdf_certificado(
        self,
        n_certificado: str,
        client_id: Optional[int] = None,
    ) -> Tuple[bytes, str, Optional[str]]:
        """
        Obtiene el PDF oficial de un certificado para descarga administrativa.
        Prioriza el PDF firmado almacenado en BD (0 tokens / 0 firmas adicionales).
        """
        record = await self.repo.get_by_n_certificado(
            n_certificado, client_id=client_id, include_pdf=True
        )
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Certificado no encontrado",
            )

        sig_code = record.get("signature_code")
        pdf_almacenado = record.get("pdf_bytes")
        if pdf_almacenado:
            return pdf_almacenado, "ALMACENADO", sig_code

        if sig_code and CAMERCLOUD_ENABLED:
            try:
                pdf_descargado = await self.camercloud_service.descargar_pdf_firmado(sig_code)
                if pdf_descargado:
                    await self.repo.actualizar_contenido_pdf(
                        n_certificado, pdf_descargado, client_id=client_id
                    )
                    return pdf_descargado, "ALMACENADO", sig_code
            except Exception as e_dl:
                logger.warning(
                    "[CertificadosService] Error descargando PDF firmado %s desde CamerCloud: %s",
                    sig_code,
                    e_dl,
                )

        # Fallback para certificados históricos previos a la integración CamerCloud
        cert_mfe = self._formatear_para_mfe(record)
        config_inst = await self.repo.get_configuracion_institucional(client_id=client_id)
        if "nombre_director" not in cert_mfe and config_inst.get("nombre_director"):
            cert_mfe["nombre_director"] = config_inst["nombre_director"]
        if "cargo_director" not in cert_mfe and config_inst.get("cargo_director"):
            cert_mfe["cargo_director"] = config_inst["cargo_director"]
        if "firma_director" not in cert_mfe and config_inst.get("firma_director"):
            cert_mfe["firma_director"] = config_inst["firma_director"]

        pdf_bytes = self.pdf_service.generar_pdf(cert_mfe)
        return pdf_bytes, "REGENERADO", sig_code

    async def procesar_solicitud_myjcc(self, data: Dict[str, Any], client_id: Optional[int] = None) -> Dict[str, Any]:
        tipo = data.get("tipo", "contador").lower()
        n_cert = str(data.get("N_CERTIFICADO") or "").strip()
        detalles = data.get("Detalles", {})

        if n_cert:
            existente = await self.repo.get_by_n_certificado(
                n_cert, client_id=client_id, include_pdf=True
            )
            if existente:
                pdf_existente = existente.get("pdf_bytes")
                sig_existente = existente.get("signature_code")
                if pdf_existente:
                    return {
                        **existente,
                        "origen": "ALMACENADO",
                        "firmado_camercloud": bool(sig_existente),
                        "pdf_bytes": pdf_existente,
                    }
                if sig_existente and CAMERCLOUD_ENABLED:
                    try:
                        pdf_recuperado = await self.camercloud_service.descargar_pdf_firmado(sig_existente)
                        if pdf_recuperado:
                            await self.repo.actualizar_contenido_pdf(
                                n_cert, pdf_recuperado, client_id=client_id
                            )
                            return {
                                **existente,
                                "origen": "ALMACENADO",
                                "firmado_camercloud": True,
                                "pdf_bytes": pdf_recuperado,
                            }
                    except Exception as e_rec:
                        logger.warning(
                            "[CertificadosService] Error recuperando PDF %s desde CamerCloud: %s",
                            sig_existente,
                            e_rec,
                        )

        # Homologación de nombre según HU
        if tipo == "contador":
            nombres = detalles.get("CON_NOMBRES", "").strip()
            ap1 = detalles.get("CON_APELLIDO1", "").strip()
            ap2 = detalles.get("CON_APELLIDO2", "").strip()
            nombre_titular = f"{nombres} {ap1} {ap2}".strip()
        else:
            nombre_titular = detalles.get("SOC_RAZON_SOCIAL", "").strip()

        fecha_gen = data.get("fechaGeneracion") or str(date.today())

        # Consulta de configuración institucional vigente (Director General, cargo y firma)
        config_inst = await self.repo.get_configuracion_institucional(client_id=client_id)
        if "nombre_director" not in data and config_inst.get("nombre_director"):
            data["nombre_director"] = config_inst["nombre_director"]
        if "cargo_director" not in data and config_inst.get("cargo_director"):
            data["cargo_director"] = config_inst["cargo_director"]
        if "firma_director" not in data and config_inst.get("firma_director"):
            data["firma_director"] = config_inst["firma_director"]

        raw_pdf_bytes = self.pdf_service.generar_pdf(data)
        pdf_bytes = raw_pdf_bytes
        signature_code: Optional[str] = None
        auth_code: Optional[str] = None
        fecha_firma: Optional[str] = None
        firmado_camercloud = False

        if CAMERCLOUD_ENABLED:
            try:
                firma_res = await self.camercloud_service.firmar_pdf_desatendida(
                    pdf_bytes=raw_pdf_bytes,
                    n_certificado=n_cert,
                )
                pdf_bytes = firma_res["pdf_bytes"]
                signature_code = firma_res.get("signature_code")
                auth_code = firma_res.get("auth_code")
                fecha_firma = firma_res.get("fecha_firma")
                firmado_camercloud = True
            except (CamercloudNoCertificateError, CamercloudError) as e_cc:
                if CAMERCLOUD_FALLBACK_UNSIGNED:
                    logger.warning(
                        "[CertificadosService] CamerCloud no pudo firmar %s (fallback habilitado): %s",
                        n_cert,
                        e_cc,
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Error al certificar el PDF con CamerCloud: {e_cc}",
                    )
            except Exception as e_cc:
                if CAMERCLOUD_FALLBACK_UNSIGNED:
                    logger.warning(
                        "[CertificadosService] Error inesperado CamerCloud para %s (fallback habilitado): %s",
                        n_cert,
                        e_cc,
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Error inesperado al certificar el PDF con CamerCloud: {e_cc}",
                    )

        pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()

        db_payload = {
            "n_certificado": n_cert,
            "tipo": tipo,
            "documento": data.get("documento", ""),
            "nombre_titular": nombre_titular,
            "fecha_generacion": fecha_gen,
            "fecha_firma_onac": fecha_firma,
            "estado": detalles.get("ESTADO", "ACTIVO"),
            "payload_detalles": detalles,
            "origen": "GENERADO" if data.get("Nuevo", True) else "REGENERADO",
            "ruta_pdf": f"certificados/{n_cert}.pdf",
            "hash_sha256": pdf_hash,
            "signature_code": signature_code,
            "auth_code": auth_code,
            "firmado_camercloud": firmado_camercloud,
            "pdf_bytes": pdf_bytes,
        }

        await self.repo.guardar_certificado(db_payload, client_id=client_id)
        return db_payload
