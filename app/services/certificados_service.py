import hashlib
from datetime import datetime, date
from typing import Dict, Any, Optional
from app.repositories.certificados_repository import CertificadosRepository

class CertificadosService:
    def __init__(self, repository: Optional[CertificadosRepository] = None):
        self.repo = repository or CertificadosRepository()

    def _formatear_para_mfe(self, record: Dict[str, Any]) -> Dict[str, Any]:
        tipo_raw = (record.get("tipo") or "").lower()
        is_contador = tipo_raw == "contador"
        detalles = record.get("payload_detalles") or {}
        
        # Antecedentes
        raw_antecedentes = detalles.get("ANTECEDENTES") or []
        formatted_antecedents = []
        for ant in raw_antecedentes:
            formatted_antecedents.append({
                "sanctionType": ant.get("SAN_TIPO") or "",
                "durationMonths": ant.get("SAN_MESES"),
                "resolutionNumber": ant.get("SAN_RESOLUCION") or "",
                "resolutionDate": ant.get("SAN_FECHA_RESOLUCION") or "",
                "enforcementDate": ant.get("SAN_FECHA_EJECUTORIA") or "",
                "completionDate": ant.get("SAN_FECHA_FIN")
            })

        # Formateo de fechas
        gen_at = record.get("fecha_generacion") or ""
        firm_at = record.get("fecha_firma_onac")

        return {
            "id": f"{tipo_raw}-{record.get('n_certificado')}",
            "type": "Contador" if is_contador else "Sociedad",
            "certificateNumber": record.get("n_certificado", ""),
            "identifier": record.get("documento", ""),
            "holder": record.get("nombre_titular", ""),
            "generatedAt": gen_at,
            "signedAt": firm_at,
            "status": record.get("estado", "ACTIVO"),
            "professionalCard": detalles.get("CON_NRO_TARJETA") if is_contador else None,
            "cardType": detalles.get("CON_TIPO_TARJETA") if is_contador else None,
            "documentMunicipality": detalles.get("MUNICIPIO_DOCUMENTO") if is_contador else None,
            "documentDepartment": detalles.get("DEPARTAMENTO_DOCUMENTO") if is_contador else None,
            "companyCode": str(detalles.get("SOC_CODIGO")) if not is_contador and detalles.get("SOC_CODIGO") else None,
            "legalRepresentative": detalles.get("SOC_REPRESENTANTE_LEGAL") if not is_contador else None,
            "municipality": detalles.get("MUNICIPIO") if not is_contador else None,
            "department": detalles.get("DEPARTAMENTO") if not is_contador else None,
            "updatedAt": detalles.get("CON_FECHA_ACTUALIZACION") or detalles.get("SOC_FECHA_ACTUALIZACION") or gen_at,
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

    async def procesar_solicitud_myjcc(self, data: Dict[str, Any], client_id: Optional[int] = None) -> Dict[str, Any]:
        tipo = data.get("tipo", "contador").lower()
        n_cert = data.get("N_CERTIFICADO")
        detalles = data.get("Detalles", {})
        
        # Homologación de nombre según HU
        if tipo == "contador":
            nombres = detalles.get("CON_NOMBRES", "").strip()
            ap1 = detalles.get("CON_APELLIDO1", "").strip()
            ap2 = detalles.get("CON_APELLIDO2", "").strip()
            nombre_titular = f"{nombres} {ap1} {ap2}".strip()
        else:
            nombre_titular = detalles.get("SOC_RAZON_SOCIAL", "").strip()

        fecha_gen = data.get("fechaGeneracion") or str(date.today())
        
        # Simulación de respuesta de firma ONAC
        fecha_firma = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
            "hash_sha256": hashlib.sha256(n_cert.encode()).hexdigest()
        }

        await self.repo.guardar_certificado(db_payload, client_id=client_id)
        return db_payload
