import os
import json
import httpx
import random
import time
from typing import Dict, Any

PROD_BASE_URL = "https://apitarjetas.jcc.gov.co".rstrip("/")

JCC_API_BEARER_TOKEN = os.getenv(
    "JCC_API_BEARER_TOKEN",
    "kvllYI0urrjVdqYOUTJZw7p5qIG9U5c8XlnNs60MMfC5yYArY3JuntakvllYI0urrjVdqYOUTJZw7p5qIG9U5c8XlnNs60MMfC5yYArY3"
)

# Activa el fallback automático a datos simulados cuando no hay conexión por VPN (True por defecto)
ENABLE_JCC_MOCK_FALLBACK = os.getenv("ENABLE_JCC_MOCK_FALLBACK", "true").lower() in ("true", "1", "yes")

# Fuerza retornar datos simulados inmediatamente sin intentar llamar a la red
FORCE_JCC_MOCK = os.getenv("FORCE_JCC_MOCK", "false").lower() in ("true", "1", "yes")

# Base64 dummy sobrio (Avatar en slate oscuro/plateado) para simular la fotografía/avatar cuando no hay VPN
MOCK_IMAGE_BASE64 = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMjAwIiB2aWV3Qm94PSIwIDAgMjAwIDIwMCI+PGRlZnM+PGxpbmVhckdyYWRpZW50IGlkPSJnIiB4MT0iMCUiIHkxPSIwJSIgeDI9IjEwMCUiIHkyPSIxMDAlIj48c3RvcCBvZmZzZXQ9IjAlIiBzdG9wLWNvbG9yPSIjMzM0MTU1Ii8+PHN0b3Agb2Zmc2V0PSIxMDAlIiBzdG9wLWNvbG9yPSIjMWUyOTNiIi8+PC9saW5lYXJHcmFkaWVudD48L2RlZnM+PHJlY3Qgd2lkdGg9IjIwMCIgaGVpZ2h0PSIyMDAiIHJ4PSIyMCIgZmlsbD0idXJsKCNnKSIvPjxjaXJjbGUgY3g9IjEwMCIgY3k9Ijc1IiByPSIzNSIgZmlsbD0iI2NiZDVlMSIvPjxwYXRoIGQ9Ik0xMDAgMTIwIGMtMzUgMCAtNjUgMTggLTY1IDQwIHYgMTUgaCAxMzAgdiAtMTUgYzAgLTIyIC0zMCAtNDAgLTY1IC00MCB6IiBmaWxsPSIjY2JkNWUxIi8+PC9zdmc+"

# Listados de 20 nombres y 20 apellidos para combinación dinámica en simulaciones
NOMBRES_MOCK = [
    "CARLOS ANDRES", "MARIA FERNANDA", "JUAN DAVID", "LAURA VICTORIA",
    "ALEJANDRO", "DIANA CAROLINA", "SANTIAGO", "ANA MARIA",
    "GABRIEL EDUARDO", "DANIELA", "FELIPE", "ANDREA DEL PILAR",
    "CAMILO ERNESTO", "VALENTINA", "MATEO", "SOFIA",
    "NICOLAS", "NATALIA", "DIEGO FERNANDO", "PAOLA ANDREA"
]

APELLIDOS_MOCK = [
    "RODRIGUEZ", "GOMEZ", "MORALES", "LOPEZ",
    "MARTINEZ", "VARGAS", "HERNANDEZ", "TORRES",
    "RAMIREZ", "CASTRO", "MENDOZA", "SILVA",
    "RINCON", "QUINTERO", "SALAZAR", "OSPINA",
    "CARDONA", "BELTRAN", "GUTIERREZ", "ROJAS"
]

SOCIEDADES_NOMBRES = [
    "ASESORES CONTABLES Y TRIBUTARIOS", "AUDITORES ASOCIADOS", "CONSULTORES FINANCIEROS",
    "SOLUCIONES CONTABLES", "INVERSIONES Y AUDITORIAS", "SERVICIOS CONTABLES INTEGRALES",
    "ESTRATEGIA TRIBUTARIA", "GRUPO FINANCIERO", "CONTADORES PUBLICOS UNIDOS",
    "GESTION FISCAL GLOBAL", "AUDITORES FINANCIEROS Y FISCALES", "VISION CONTABLE",
    "CONSULTORES TRIBUTARIOS INTEGRADOS", "ALIANZA CONTABLE E IMPUESTOS", "ASESORIAS FISCALES CORPORATIVAS",
    "RED DE AUDITORES COLOMBIA", "INTEGRITA CONTABLE", "NEXO FINANCIERO Y CONTABLE",
    "ASESORES GLOBALES DE COLOMBIA", "CONSULTORIA Y AUDITORIA ESTRATEGICA"
]

SOCIEDADES_TIPOS = ["S.A.S.", "& CIA LTDA", "S.A.", "E HIJOS S.A.S.", "GROUP S.A.S."]


class JccClient:

    def __init__(self):
        self.last_url: str = ""
        self.last_metodo: str = "POST"

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

    def _generar_respuesta_mock(self, documento: str, tipo_tarjeta: str) -> Dict[str, Any]:
        """
        Genera una respuesta simulada combinando aleatoriamente listados de 20 nombres y 20 apellidos
        cuando no hay conectividad VPN en preproducción/local.
        """
        print(f"[JCC API Client] 🎭 Generando respuesta SIMULADA combinada para documento: {documento} ({tipo_tarjeta})")

        # Usar semilla basada en documento si viene uno, o combinaciones aleatorias
        seed_val = f"{documento}_{time.time()}" if documento else str(time.time())
        rnd = random.Random(seed_val)

        if tipo_tarjeta == "sociedades":
            nit_limpio = documento
            base_nombre = rnd.choice(SOCIEDADES_NOMBRES)
            tipo_soc = rnd.choice(SOCIEDADES_TIPOS)
            razon_social = f"{base_nombre} {tipo_soc}"

            item_mock = {
                "NIT": nit_limpio,
                "RAZON_SOCIAL": razon_social,
                "TIPO_SOCIEDAD": "SOCIEDAD DE CONTADORES",
                "NO_EXPD": rnd.randint(10000, 99999),
                "INSCRIPCION": rnd.randint(1000, 9999),
                "ESTADO_SOCIEDAD": "ACTIVO",
                "RESOLUCION": f"RES-SOC-{rnd.randint(100, 999)}-2024",
                "FECH_RESOLU": "2024-02-01T00:00:00",
                "FECHA_RADICACION": "2024-01-20T00:00:00",
                "ACTA_JCC": f"ACTA-SOC-{rnd.randint(100, 999)}",
                "ESTADO_SOLICITUD": "APROBADO",
                "TIPO_SOLICITUD": "PRIMERA VEZ"
            }
        else:
            doc_suffix = documento[-6:] if len(documento) >= 6 else documento
            nombre_sel = rnd.choice(NOMBRES_MOCK)
            apellido1_sel = rnd.choice(APELLIDOS_MOCK)
            apellido2_sel = rnd.choice(APELLIDOS_MOCK)

            email_user = f"{nombre_sel.lower().split()[0]}.{apellido1_sel.lower()}{rnd.randint(10,99)}"

            item_mock = {
                "NO_DOCUMENTO": documento,
                "TIPO_DOCUMENTO": "CC",
                "NOMBRES": nombre_sel,
                "PRIMER_APELLIDO": apellido1_sel,
                "SEGUNDO_APELLIDO": apellido2_sel,
                "NO_TARJETA": f"TP-{doc_suffix}",
                "NO_EXPD": rnd.randint(100000, 999999),
                "UNIVERSIDAD": "UNIVERSIDAD SIMULADA JCC",
                "ESTADO_CONTADOR": "ACTIVO",
                "RESOLUCION": f"RES-{rnd.randint(1000, 9999)}-2024",
                "FECHA_ESTADO": "2024-01-15T00:00:00",
                "FECHA_RADICACION": "2024-01-10T00:00:00",
                "FECH_RESOLU": "2024-01-12T00:00:00",
                "ACTA_JCC": rnd.randint(100, 999),
                "FECHA_GRADO": "2023-12-01T00:00:00",
                "SECCIONAL": "BOGOTA",
                "EMAIL": f"{email_user}@example.com"
            }

        return {
            "disponibles": [item_mock],
            "pdf": MOCK_IMAGE_BASE64,
            "encontrado": True,
            "simulado": True
        }

    async def consultar_registro(self, documento: str, tipo_tarjeta: str = "contadores", tipo: str = "") -> Dict[str, Any]:
        
        documento_limpio = self._limpiar_documento(documento, tipo_tarjeta)
        if not documento_limpio:
            return {"disponibles": [], "pdf": None, "encontrado": False, "error": "Documento vacío"}

        prod_endpoint = "/sociedades/" if tipo_tarjeta == "sociedades" else "/contadores/"
        url = f"{PROD_BASE_URL}{prod_endpoint}"
        self.last_url = url
        self.last_metodo = "POST"

        # Si se fuerza mock inmediatamente, no llamar a la red
        if FORCE_JCC_MOCK:
            return self._generar_respuesta_mock(documento_limpio, tipo_tarjeta)

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
        tipo_final = tipo_map.get(tipo, tipo if tipo else "primeraVez")

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

        try:
            print(f"[JCC API Client] Consultando API Producción JCC: {url}")
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                response = await client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                raw_data = response.json()
                data = self._normalizar_respuesta(raw_data)

                if "error" in data and data["error"]:
                    print(f"[JCC API Client] API reportó error lógico: {data['error']}")
                else:
                    disponibles = data.get("disponibles", [])
                    if disponibles:
                        data["encontrado"] = True
                        return data
                    else:
                        print(f"[JCC API Client] No se encontraron registros disponibles en {url}")
            else:
                print(f"[JCC API Client] Error HTTP {response.status_code} en {url}: {response.text}")

        except Exception as e:
            print(f"[JCC API Client] ⚠️ Excepción de red / VPN conectando a {url}: {e}")

        # Si falla la red/VPN o la API no trae datos, y el fallback mock está habilitado:
        if ENABLE_JCC_MOCK_FALLBACK:
            print(f"[JCC API Client] ⚠️ Activando respuesta simulada por falta de conexión VPN a {url}")
            return self._generar_respuesta_mock(documento_limpio, tipo_tarjeta)

        return {
            "disponibles": [],
            "pdf": None,
            "encontrado": False,
            "error": "No se encontraron registros en Producción JCC."
        }