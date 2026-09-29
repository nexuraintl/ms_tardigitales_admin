from typing import Any, Dict, Optional
from app.repositories.tarjetas_repository import TarjetasRepository
from app.audit.builder import build_auditoria_payload

class AuditoriaService:
    def __init__(self, repo: TarjetasRepository):
        self.repo = repo

    async def registrar(
        self,
        *,
        client_id: Optional[int],
        tipo_tarjeta: str,
        tipo: str,
        metodo: str,
        url: str,
        parametros_peticion: Dict[str, Any],
        cuerpo_respuesta: Dict[str, Any],
        duracion_ms: int,
        codigo_http: int = 200,
    ) -> int:

        if "contadores" in url and ("TarjetasDigitales" in url or "tarjetaContadores" in url):
            url = "https://apitarjetas.jcc.gov.co/contadores/"
        elif "sociedades" in url and ("TarjetasDigitales" in url or "tarjetaSociedades" in url):   
            url = "https://apitarjetas.jcc.gov.co/sociedades/"         

        payload = build_auditoria_payload(
            client_id=client_id,
            tipo_tarjeta=tipo_tarjeta,
            tipo=tipo,
            metodo=metodo,
            url=url,
            parametros_peticion=parametros_peticion,
            cuerpo_respuesta=cuerpo_respuesta,
            duracion_ms=duracion_ms,
            codigo_http=codigo_http,
        )

        return await self.repo.create_auditoria_api(payload, client_id=client_id)