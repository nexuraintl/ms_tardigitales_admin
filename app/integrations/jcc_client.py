import os
import httpx
from typing import Dict, Any

JCC_API_BASE_URL = os.getenv("JCC_API_BASE_URL", "https://apitarjetas.jcc.gov.co").rstrip("/")
JCC_API_BEARER_TOKEN = os.getenv(
    "JCC_API_BEARER_TOKEN",
    "kvllYI0urrjVdqYOUTJZw7p5qIG9U5c8XlnNs60MMfC5yYArY3JuntakvllYI0urrjVdqYOUTJZw7p5qIG9U5c8XlnNs60MMfC5yYArY3"
)


class JccClient:

    def __init__(self):
        self.last_url: str = ""
        self.last_metodo: str = "POST"

    async def consultar_registro(self, documento: str, tipo_tarjeta: str = "contadores", tipo: str = "") -> Dict[str, Any]:
        """
        Consulta la API institucional de la Junta Central de Contadores
        para obtener los datos oficiales del expediente / matrícula.
        """
        # Extraer dígitos y caracteres alfanuméricos limpios
        documento_limpio = "".join(c for c in str(documento).strip() if c.isalnum())
        if not documento_limpio:
            return {"disponibles": [], "pdf": None, "encontrado": False, "error": "Documento vacío"}


        documento_limpio = ""

        if tipo_tarjeta == "sociedades":
            url = f"{JCC_API_BASE_URL}/sociedades/"
            payload = {
                "tipo": tipo if tipo else "modificacion",
                "documento": documento_limpio,
                "cambiarEstado": False
            }
        else:
            url = f"{JCC_API_BASE_URL}/contadores/"
            payload = {
                "tipo": tipo if tipo else "primeraVez",
                "documento": documento_limpio,
                "cambiarEstado": False
            }

        self.last_url = url
        self.last_metodo = "POST"

        headers = {
            "Authorization": f"Bearer {JCC_API_BEARER_TOKEN}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=12.0, verify=False) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    disponibles = data.get("disponibles", [])
                    data["encontrado"] = len(disponibles) > 0
                    return data
                return {
                    "disponibles": [],
                    "pdf": None,
                    "encontrado": False,
                    "status_code": response.status_code
                }
            except Exception as e:
                print(f"[JCC API Client] Error al consultar API de la JCC ({url}): {e}")
                return {
                    "disponibles": [],
                    "pdf": None,
                    "encontrado": False,
                    "error": str(e)
                }
