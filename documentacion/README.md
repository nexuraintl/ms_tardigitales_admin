# Documentación Técnica de Endpoints (01 a 04) - Microservicio Python FastAPI

> **Destinatario / Consumo:** Modelos de Inteligencia Artificial (Claude / LLM), Arquitectos de Software e Ingenieros Backend.  
> **Servicio:** `ms_tardigitales_admin` (FastAPI + aiomysql + ReportLab / PyPDF / svglib).  
> **Entorno Local / Preproducción Oficial:** `http://local-jcc.nexura.com.co` (Gateway Docker Nginx).  
> **Tenant / Cliente Predeterminado:** `20001` (UAE Junta Central de Contadores - JCC).  
> **Documentación Interactiva Swagger:** `http://local-jcc.nexura.com.co/apig/tardigitales/docs`  
> **OpenAPI JSON:** `http://local-jcc.nexura.com.co/apig/tardigitales/openapi.json`

---

## 1. Directrices Obligatorias para la IA (Claude Prompting System Rules)

Al analizar, depurar, refactorizar o extender los endpoints de este microservicio, Claude debe acatar sin excepciones los siguientes estándares arquitectónicos:

1. **Nombres Canónicos de Base de Datos (Cero Alias Legacy):**
   - En consultas SQL, servicios (`TarjetasService`), repositorios (`TarjetasRepository`) y esquemas Pydantic, utilizar **únicamente** los nombres reales de las columnas.
   - Prohibido reintroducir alias como `solicitante` (usar `nombre_completo` para contadores o `razon_social` para sociedades), `expediente` (usar `no_expd`), `matricula` (usar `no_tarjeta`), `tarjeta` (usar `estado_tarjeta`).
2. **Tratamiento Canónico de Siglas:**
   - Mantener siempre en mayúscula sostenida: `NIT`, `JCC`, `QR`, `PDF`, `CC`, `CE`, `TI`, `ID`, `SHA256`, `API`.
3. **Manejo Centralizado de Excepciones:**
   - Lanzar siempre `PipelineException` (`app/core/exceptions.py`), indicando:
     - `etapa`: Código técnico de la fase que falla (ej: `'CONSULTA_HASH'`, `'VALIDACION_TOKEN'`, `'GENERACION_PDF'`).
     - `mensaje`: Texto amigable y claro en formato tipo oración (`Sentence case`).
     - `detalle_tecnico`: Mensaje de error interno (`str(e)`).
     - `cliente_id`: Tenant ID.
     - `status_code`: Código HTTP semántico (`404`, `400`, `500`).
4. **Conexiones Asíncronas Multitenant:**
   - La base de datos es MariaDB/MySQL. Toda operación asíncrona se efectúa mediante `conn = await get_client_connection(client_id)` y `async with conn.cursor(aiomysql.DictCursor) as cursor:`. Prohibido el uso de cursores bloqueantes en el ciclo de eventos.

---

## 2. Mapa Resumen de los Primeros Cuatro Endpoints

| # | Endpoint Oficial en Gateway | Método HTTP | Repositorio / Servicio | Archivo de Especificación |
|---|---|:---:|---|---|
| **01** | `/apig/tardigitales/admin/tarjetas/verificar` <br> `/apig/tardigitales/admin/tarjetas/verificar/{hash}` | `GET` | `TarjetasRepository.get_by_hash` <br> `TarjetasService.get_tarjeta_by_hash` | [`01_INFORMACION_CONTADOR_SOCIEDAD.md`](./01_INFORMACION_CONTADOR_SOCIEDAD.md) |
| **02** | `/apig/tardigitales/admin/tarjetas/activar-movil` | `POST` | `TarjetasService.activar_tarjeta_movil` <br> `TarjetasRepository.activar_dispositivo_movil` | [`02_ACTIVACION_TARJETA_MOVIL.md`](./02_ACTIVACION_TARJETA_MOVIL.md) |
| **03** | `/apig/tardigitales/admin/tarjetas/branding-credentials/info-published/{id}` <br> `/apig/tardigitales/admin/tarjetas/branding-institucional/info-published` | `GET` | `TarjetasRepository.get_branding_credentials_public` <br> `TarjetasRepository.get_institucional_published` | [`03_BRANDING_CREDENCIALES_E_INSTITUCIONAL.md`](./03_BRANDING_CREDENCIALES_E_INSTITUCIONAL.md) |
| **04** | `/apig/tardigitales/admin/tarjetas/verificar/{hash}/pdf` <br> `/apig/tardigitales/admin/tarjetas/pdf/{id}` | `GET` | `TarjetasService.generar_pdf_tarjeta_by_hash` <br> `PdfGeneratorService.generar_pdf_tarjeta` | [`04_EXPORTAR_PDF_COMPARTIR_TARJETA.md`](./04_EXPORTAR_PDF_COMPARTIR_TARJETA.md) |
