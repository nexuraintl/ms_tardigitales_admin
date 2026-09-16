import os
import json
import httpx
from typing import Dict, Any

PROD_BASE_URL = "https://apitarjetas.jcc.gov.co".rstrip("/")
SIM_BASE_URL = "https://preproduccion-se-caligovco.nexura.com/api/Rit".rstrip("/")

JCC_API_BEARER_TOKEN = os.getenv(
    "JCC_API_BEARER_TOKEN",
    "kvllYI0urrjVdqYOUTJZw7p5qIG9U5c8XlnNs60MMfC5yYArY3JuntakvllYI0urrjVdqYOUTJZw7p5qIG9U5c8XlnNs60MMfC5yYArY3"
)

class JccClient:

    def __init__(self):
        self.last_url: str = ""
        self.last_metodo: str = "POST"
        self.use_simulation_only = False 

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
            # Para sociedades, permitimos el guion y quitamos puntos/espacios
            # Ejemplo: "900.724.363-0" -> "900724363-0"
            return "".join(c for c in str(documento).strip() if c.isalnum() or c == "-")
        else:
            # Para contadores, solo alfanuméricos
            return "".join(c for c in str(documento).strip() if c.isalnum())

    async def consultar_registro(self, documento: str, tipo_tarjeta: str = "contadores", tipo: str = "") -> Dict[str, Any]:
        
        documento_limpio = self._limpiar_documento(documento, tipo_tarjeta)
        if not documento_limpio:
            return {"disponibles": [], "pdf": None, "encontrado": False, "error": "Documento vacío"}

        if tipo_tarjeta == "sociedades":
            prod_endpoint = "/sociedades/"
            sim_endpoint = "/tarjetaSociedades"
            tipo_defecto = "primeraVez" 
        else:
            prod_endpoint = "/contadores/"
            sim_endpoint = "/tarjetaContadores"
            tipo_defecto = "primeraVez"

        tipo_map = {
            "Primera vez": "primeraVez",
            "Duplicado": "duplicado",
            "Sustitución": "sustitucion",
            "Sustitucion": "sustitucion",
            "Modificación": "modificacion",
            "Modificacion": "modificacion",
            "primeraVez": "primeraVez",
            "duplicado": "duplicado",
            "sustitucion": "sustitucion",
            "modificacion": "modificacion"
        }
        tipo_final = tipo_map.get(tipo, tipo if tipo else tipo_defecto)

        payload = {
            "tipo": tipo_final,
            "documento": documento_limpio,
            "cambiarEstado": False
        }
        
        payload_str = json.dumps(payload)

        urls_to_try = []
        if self.use_simulation_only:
            urls_to_try.append(f"{SIM_BASE_URL}{sim_endpoint}")
        else:
            urls_to_try.append(f"{PROD_BASE_URL}{prod_endpoint}")
            urls_to_try.append(f"{SIM_BASE_URL}{sim_endpoint}")

        async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
            for url in urls_to_try:
                self.last_url = url
                self.last_metodo = "POST"
                
                try:
                    if "preproduccion" in url or "nexura" in url:
                        headers = {
                            "Content-Type": "text/plain", 
                            "Accept": "*/*",
                            "User-Agent": "PostmanRuntime/7.49.1",
                            "Connection": "keep-alive"
                        }
                        print(f"[JCC API Client] Enviando a Simulación URL: {url}")
                        print(f"[JCC API Client] Payload enviado: {payload_str}")
                        
                        response = await client.post(url, content=payload_str, headers=headers)
                    else:
                        headers = {
                            "Authorization": f"Bearer {JCC_API_BEARER_TOKEN}",
                            "Content-Type": "application/json",
                            "Accept": "application/json"
                        }
                        response = await client.post(url, json=payload, headers=headers)
                    
                    if response.status_code == 200:
                        raw_data = response.json()
                        data = self._normalizar_respuesta(raw_data)

                        if "error" in data and data["error"]:
                            print(f"[JCC API Client] API reportó error lógico: {data['error']}")
                            continue 

                        disponibles = data.get("disponibles", [])
                        
                        if disponibles:
                            data["encontrado"] = True
                            return data
                        else:
                            print(f"[JCC API Client] No hay disponibles en {url}")
                            continue 

                    else:
                        print(f"[JCC API Client] Error HTTP {response.status_code} en {url}")
                        print(f"[JCC API Client] Detalle error: {response.text}")
                        continue

                except Exception as e:
                    print(f"[JCC API Client] Excepción conectando a {url}: {e}")
                    continue

        return {
            "disponibles": [],
            "pdf": None,
            "encontrado": False,
            "error": "No se encontraron registros en Producción ni en Simulación."
        }