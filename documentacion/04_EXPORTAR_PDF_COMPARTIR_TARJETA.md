# Endpoint 04: Exportar PDF / Compartir Tarjeta

> **Destinatario / Consumo:** Modelos de IA (Claude / LLM) e Ingenieros Backend.  
> **Servicio:** `ms_tardigitales_admin` (`app/services/pdf_generator_service.py`).  
> **Ruta API:** `/apig/tardigitales/admin/tarjetas/verificar/{hash}/pdf`.

---

## 1. Definición del Endpoint HTTP

- **Método:** `GET`
- **Ruta Principal (Por Hash):** `/apig/tardigitales/admin/tarjetas/verificar/{hash}/pdf`
- **Ruta Alternativa (Por ID):** `/apig/tardigitales/admin/tarjetas/pdf/{id}`
- **Parámetros Query:**
  - `download` (`bool`, default: `true`): Alterna entre `attachment` e `inline`.
  - `tipo_tarjeta` (`str`, opcional): `'contadores'` o `'sociedades'`.
  - `client_id` (`int`, opcional): ID del Tenant.

- **Headers de Respuesta:**
  - `Content-Type: application/pdf`
  - `Content-Disposition: attachment; filename="tarjeta_contador_320890-T.pdf"`
  - `Cache-Control: no-cache, no-store, must-revalidate`

---

## 2. Arquitectura de Generación PDF (`PdfGeneratorService`)

La generación del documento no utiliza HTML estático ni WebView; está construida mediante **manipulación vectorial SVG y ReportLab Graphics**:

1. **Plantilla Base:** Carga la plantilla vectorial SVG oficial exportada de Figma (`app/assets/borderless.svg`).
2. **Registro Tipográfico:** Registra las fuentes oficiales Satoshi (`Satoshi-Regular.ttf`, `Satoshi-Bold.ttf`, `Satoshi-Medium.ttf`) tanto en `svglib` como en `reportlab.pdfbase.pdfmetrics`.
3. **Inyección de Foto:**
   - La foto del titular se redimensiona a 460x460 px con LANCZOS.
   - Aplica esquinas redondeadas (`radius=64`) sobre fondo blanco puro con PIL.
4. **Inyección de QR Dinámico:**
   - Genera el código QR vectorial/rasterizado con corrección de errores nivel M para la URL:
     `http://local-jcc.nexura.com.co/admin/tardigitales/verificar?token={hash_sha256}`.
5. **Composición de Firma:**
   - Monta la firma del Director General con canal alfa transparente preservando nitidez.
6. **Márgenes de Seguridad para Impresión:**
   - Escala el gráfico a factor 0.94 y compensa la posición para garantizar un margen perimetral seguro superior a 13 mm en los 4 bordes.
7. **Conversión y Metadatos PDF/A-2b:**
   - Convierte el SVG a ReportLab Drawing y de Drawing a PDF en memoria.
   - Con `pypdf`, inyecta el paquete XMP con `pdfaid:part="2"` y `pdfaid:conformance="B"` para cumplir con el estándar ISO 19005-2.
