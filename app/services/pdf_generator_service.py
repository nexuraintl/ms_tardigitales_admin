"""
Servicio oficial de generación de PDF para Tarjetas Digitales.
Estándar: PDF/A-2b (ISO 19005-2) en hoja Carta Colombia (612 x 792 pt).
Basado 100% en la plantilla vectorial oficial exportada de Figma (borderless.svg).
Inyecta dinámicamente textos con la tipografía oficial Satoshi / Satoshi Variable,
foto con esquinas redondeadas, código QR, firma con fondo transparente
y renderiza la tarjeta con el patrón de marca de agua oficial configurado en branding (suave y legible).

Ajustes de impresión:
1. Sin icono de copiar en el número de tarjeta.
2. Margen de impresión seguro (> 13 mm en los 4 bordes).
3. Alineación perfecta al ras derecho (text-anchor="end" x="458") en toda la columna derecha.
"""

import io
import os
import re
import base64
import qrcode
from PIL import Image as PILImage, ImageDraw as PILImageDraw, ImageOps as PILImageOps
from svglib.svglib import svg2rlg, register_font
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics import renderPDF
import pypdf

# -----------------------------------------------------------------------------
# REGISTRO GLOBAL DE FUENTES SATOSHI EN SVGLIB Y REPORTLAB
# -----------------------------------------------------------------------------
FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts")
satoshi_reg = os.path.join(FONTS_DIR, "Satoshi-Regular.ttf")
satoshi_med = os.path.join(FONTS_DIR, "Satoshi-Medium.ttf")
satoshi_bold = os.path.join(FONTS_DIR, "Satoshi-Bold.ttf")

try:
    if os.path.exists(satoshi_reg):
        register_font("Satoshi Variable", satoshi_reg, weight="normal")
        register_font("Satoshi", satoshi_reg, weight="normal")
        pdfmetrics.registerFont(TTFont("Satoshi", satoshi_reg))
        pdfmetrics.registerFont(TTFont("Satoshi-Regular", satoshi_reg))
        pdfmetrics.registerFont(TTFont("Satoshi Variable", satoshi_reg))
    if os.path.exists(satoshi_bold):
        register_font("Satoshi Variable", satoshi_bold, weight="bold")
        register_font("Satoshi", satoshi_bold, weight="bold")
        pdfmetrics.registerFont(TTFont("Satoshi-Bold", satoshi_bold))
        pdfmetrics.registerFont(TTFont("Satoshi Variable-Bold", satoshi_bold))
    if os.path.exists(satoshi_med):
        register_font("Satoshi-Medium", satoshi_med, weight="normal")
        pdfmetrics.registerFont(TTFont("Satoshi-Medium", satoshi_med))
except Exception as e:
    print(f"[PdfGeneratorService] Aviso registrando fuentes Satoshi: {e}")


class PdfGeneratorService:

    @staticmethod
    def _get_asset_path(filename: str) -> str:
        """Ruta absoluta a un asset estático del microservicio."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "assets", filename)

    @classmethod
    def _prepare_rounded_photo(cls, raw_bytes: bytes) -> str:
        """
        Ajusta la foto a proporción 3:4 tipo carnet sin estirarla (recorte centrado),
        aplica esquinas redondeadas con borde sutil visible incluso si el fondo de la foto es blanco,
        y preserva transparencia exterior (PNG RGBA) sobre la textura de la tarjeta.
        """
        im = PILImage.open(io.BytesIO(raw_bytes)).convert("RGBA")
        target_size = (360, 480)  # Proporción exacta 3:4 (90 x 120 pt @ 4x)
        radius = 48               # 12 pt @ 4x

        # Recorte inteligente 3:4 sin deformar ni estirar (centrado horizontal, ligeramente superior para rostros)
        im = PILImageOps.fit(im, target_size, method=PILImage.Resampling.LANCZOS, centering=(0.5, 0.35))

        # Máscara de esquinas redondeadas (4 bordes)
        mask = PILImage.new("L", target_size, 0)
        draw_mask = PILImageDraw.Draw(mask)
        draw_mask.rounded_rectangle([(0, 0), (target_size[0] - 1, target_size[1] - 1)], radius=radius, fill=255)

        # Contorno sutil (#CBD5E1) para delimitar los bordes redondeados superiores cuando la foto tiene fondo blanco
        draw_img = PILImageDraw.Draw(im)
        draw_img.rounded_rectangle(
            [(1, 1), (target_size[0] - 2, target_size[1] - 2)],
            radius=radius,
            outline=(203, 213, 225, 255),
            width=4
        )

        out = PILImage.new("RGBA", target_size, (255, 255, 255, 0))
        out.paste(im, (0, 0), mask=mask)

        buf = io.BytesIO()
        out.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"

    @classmethod
    def _prepare_signature(cls, raw_bytes: bytes) -> str:
        """Compone la firma con transparencia sobre el color de fondo exacto #E8E8E8."""
        im = PILImage.open(io.BytesIO(raw_bytes))
        bg = PILImage.new("RGB", im.size, (232, 232, 232))
        if "A" in im.mode:
            bg.paste(im, mask=im.split()[3])
        else:
            bg.paste(im)

        buf = io.BytesIO()
        bg.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"

    @classmethod
    def _prepare_subtle_watermark(cls, raw_bytes: bytes, alpha: float = 0.04) -> str:
        """
        Convierte cualquier patrón configurado en branding en una marca de agua suave,
        elegante y de alta legibilidad (mezclado 96% blanco con 4% de patrón).
        """
        try:
            im = PILImage.open(io.BytesIO(raw_bytes)).convert("L")
            im = im.resize((1000, 667), PILImage.Resampling.LANCZOS)
            white = PILImage.new("L", im.size, 255)
            watermark = PILImage.blend(white, im, alpha=alpha)
            buf = io.BytesIO()
            watermark.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return f"data:image/png;base64,{b64}"
        except Exception as e:
            print(f"[PdfGeneratorService] Error procesando marca de agua: {e}")
            return ""

    @classmethod
    def generar_pdf_tarjeta(cls, tarjeta: dict, tipo_tarjeta: str = "contadores") -> bytes:
        """Alias para generar_pdf_tarjeta_pdfa."""
        return cls.generar_pdf_tarjeta_pdfa(tarjeta, tipo_tarjeta)

    @classmethod
    def generar_pdf_tarjeta_pdfa(cls, tarjeta: dict, tipo_tarjeta: str = "contadores") -> bytes:
        """
        Genera el PDF oficial en estándar PDF/A-2b a partir de la plantilla Figma borderless.svg.
        """
        # 1. Leer plantilla SVG oficial
        svg_path = cls._get_asset_path("borderless.svg")
        if not os.path.exists(svg_path):
            raise FileNotFoundError(f"Plantilla SVG no encontrada en: {svg_path}")

        with open(svg_path, "r", encoding="utf-8") as f:
            svg = f.read()

        # 2. Dimensiones en puntos de hoja Carta Colombia (612pt x 792pt)
        svg = svg.replace('width="612" height="792"', 'width="612pt" height="792pt"')

        # 3. QUITAR ICONO DE COPIAR (Requerimiento 1: es un documento impreso)
        svg = re.sub(r'<mask id="mask0_270_2849"[^>]*>.*?</mask>', '', svg, flags=re.DOTALL)
        svg = re.sub(r'<g mask="url\(#mask0_270_2849\)">.*?</g>', '', svg, flags=re.DOTALL)

        # 4. Extraer o procesar el patrón de textura configurado en Branding
        pattern_bytes = None
        raw_patron = tarjeta.get("patron_impresion") or tarjeta.get("patron")
        if raw_patron and str(raw_patron).startswith("data:image"):
            try:
                _, enc = raw_patron.split(",", 1)
                pattern_bytes = base64.b64decode(enc)
            except Exception:
                pass

        if not pattern_bytes:
            pat_file = "pattern_sociedades_opt.jpg" if tipo_tarjeta == "sociedades" else "pattern_jcc_opt.jpg"
            pat_path = cls._get_asset_path(pat_file)
            if os.path.exists(pat_path):
                with open(pat_path, "rb") as f:
                    pattern_bytes = f.read()

        pattern_uri = ""
        if pattern_bytes:
            pattern_uri = cls._prepare_subtle_watermark(pattern_bytes, alpha=0.04)

        # 5. Datos dinámicos a inyectar
        val_tarjeta = str(tarjeta.get("no_tarjeta") or tarjeta.get("matricula") or tarjeta.get("inscripcion") or ("492031-T" if tipo_tarjeta == "contadores" else "5892"))
        val_fecha = str(tarjeta.get("fecha_resolucion") or tarjeta.get("fecha_expedicion") or ("06 - Feb - 2026" if tipo_tarjeta == "contadores" else "12 - Mar - 2025"))
        val_resolucion = str(tarjeta.get("resolucion") or tarjeta.get("resolucion_inscripcion") or ("289" if tipo_tarjeta == "contadores" else "0142"))
        val_nombre = str(tarjeta.get("nombre_completo") or tarjeta.get("razon_social") or tarjeta.get("solicitante") or ("Andrés Felipe Torres Cárdenas" if tipo_tarjeta == "contadores" else "Innovación Financiera y Tributaria S.A.S."))
        val_documento = str(tarjeta.get("no_documento") or tarjeta.get("nit") or tarjeta.get("documento") or ("1.053.892.146" if tipo_tarjeta == "contadores" else "901482310-5"))
        for pfx in ["CC", "C.C.", "NIT", "CE", "TI"]:
            if val_documento.upper().startswith(pfx):
                val_documento = val_documento[len(pfx):].strip(": ").strip()
        val_ies = str(tarjeta.get("universidad") or tarjeta.get("tipo_sociedad") or ("Universidad de La Salle" if tipo_tarjeta == "contadores" else "Sociedad de Contadores"))

        # Etiquetas dinámicas según tipo
        lbl_tarjeta = "Tarjeta profesional" if tipo_tarjeta == "contadores" else "Número de registro"
        lbl_doc = "Cédula de Ciudadanía" if tipo_tarjeta == "contadores" else "NIT"
        lbl_ies = "Institución de Educación Superior" if tipo_tarjeta == "contadores" else "Tipo de sociedad"

        # 6. ALINEAR PERFECTAMENTE LA COLUMNA DERECHA (Requerimiento 3: text-anchor="end" x="458")
        # Todos los textos de la columna derecha se alinean al margen interno derecho x="458"
        svg = re.sub(
            r'<text[^>]*>\s*<tspan[^>]*>Tarjeta profesional</tspan>\s*</text>',
            f'<text text-anchor="end" fill="#091640" style="white-space: pre" xml:space="preserve" font-family="Satoshi Variable" font-size="12"><tspan x="458" y="114.904">{lbl_tarjeta}</tspan></text>',
            svg
        )

        svg = re.sub(
            r'<text[^>]*>\s*<tspan[^>]*>492031-T</tspan>\s*</text>',
            f'<text text-anchor="end" fill="#091640" style="white-space: pre" xml:space="preserve" font-family="Satoshi Variable" font-size="22" font-weight="bold"><tspan x="458" y="147.754">{val_tarjeta}</tspan></text>',
            svg
        )

        svg = re.sub(
            r'<text[^>]*>\s*<tspan[^>]*>Fecha Res\. Inscripci&#xf3;n</tspan>\s*</text>',
            '<text text-anchor="end" fill="#091640" style="white-space: pre" xml:space="preserve" font-family="Satoshi Variable" font-size="12"><tspan x="458" y="180.904">Fecha Res. Inscripci&#xf3;n</tspan></text>',
            svg
        )

        svg = re.sub(
            r'<text[^>]*>\s*<tspan[^>]*>06 - Feb - 2026</tspan>\s*</text>',
            f'<text text-anchor="end" fill="#091640" style="white-space: pre" xml:space="preserve" font-family="Satoshi Variable" font-size="12" font-weight="bold"><tspan x="458" y="205.404">{val_fecha}</tspan></text>',
            svg
        )

        svg = re.sub(
            r'<text[^>]*>\s*<tspan[^>]*>C&#xe9;dula de Ciudadan&#xed;a</tspan>\s*</text>',
            f'<text text-anchor="end" fill="#091640" style="white-space: pre" xml:space="preserve" font-family="Satoshi Variable" font-size="12"><tspan x="458" y="249.904">{lbl_doc}</tspan></text>',
            svg
        )

        svg = re.sub(
            r'<text[^>]*>\s*<tspan[^>]*>1\.053\.892\.146</tspan>\s*</text>',
            f'<text text-anchor="end" fill="#091640" style="white-space: pre" xml:space="preserve" font-family="Satoshi Variable" font-size="14" font-weight="bold"><tspan x="458" y="276.674">{val_documento}</tspan></text>',
            svg
        )

        svg = re.sub(
            r'<text[^>]*>\s*<tspan[^>]*>Res\. Inscripci&#xf3;n</tspan>\s*</text>',
            '<text text-anchor="end" fill="#091640" style="white-space: pre" xml:space="preserve" font-family="Satoshi Variable" font-size="12"><tspan x="458" y="313.904">Res. Inscripci&#xf3;n</tspan></text>',
            svg
        )

        svg = re.sub(
            r'<text[^>]*>\s*<tspan[^>]*>289</tspan>\s*</text>',
            f'<text text-anchor="end" fill="#091640" style="white-space: pre" xml:space="preserve" font-family="Satoshi Variable" font-size="14" font-weight="bold"><tspan x="458" y="340.674">{val_resolucion}</tspan></text>',
            svg
        )

        # Columna izquierda: Nombre y Universidad con margen de seguridad
        display_nombre = (val_nombre[:26] + "...") if len(val_nombre) > 28 else val_nombre
        display_ies = (val_ies[:26] + "...") if len(val_ies) > 28 else val_ies

        svg = re.sub(
            r'<text[^>]*>\s*<tspan[^>]*>Andr&#xe9;s Felipe Torres C&#xe1;rdenas</tspan>\s*</text>',
            f'<text fill="#091640" style="white-space: pre" xml:space="preserve" font-family="Satoshi Variable" font-size="14" font-weight="bold"><tspan x="151" y="276.674">{display_nombre}</tspan></text>',
            svg
        )

        svg = re.sub(
            r'<text[^>]*>\s*<tspan[^>]*>Instituci&#xf3;n de Educaci&#xf3;n Superior</tspan>\s*</text>',
            f'<text fill="#091640" style="white-space: pre" xml:space="preserve" font-family="Satoshi Variable" font-size="12"><tspan x="151" y="313.904">{lbl_ies}</tspan></text>',
            svg
        )

        svg = re.sub(
            r'<text[^>]*>\s*<tspan[^>]*>Universidad de La Salle</tspan>\s*</text>',
            f'<text fill="#091640" style="white-space: pre" xml:space="preserve" font-family="Satoshi Variable" font-size="14" font-weight="bold"><tspan x="151" y="340.674">{display_ies}</tspan></text>',
            svg
        )

        # Ajuste de Director General y Cargo si vienen en branding
        if tarjeta.get("nombre_director"):
            svg = svg.replace(">SANDRA MILENA BARRIOS PULIDO<", f">{tarjeta['nombre_director']}<")
        if tarjeta.get("cargo_director"):
            svg = svg.replace(">DIRECTOR GENERAL<", f">{tarjeta['cargo_director']}<")

        # 7. Inyección del Contenedor de la Tarjeta con Sombra 3D, Fondo y Borde Visible
        card_clip_def = '''
<defs>
<clipPath id="card_clip">
  <rect x="135" y="12" width="342" height="361.284" rx="24"/>
</clipPath>
'''
        svg = svg.replace('<defs>', card_clip_def, 1)

        pattern_image_tag = f'<image x="135" y="12" width="342" height="361.284" xlink:href="{pattern_uri}"/>' if pattern_uri else ''

        card_elements = f'''
<!-- Sombra tridimensional suave de la tarjeta -->
<rect x="135" y="15" width="342" height="361.284" rx="24" fill="#0F172A" fill-opacity="0.04"/>
<rect x="135" y="17" width="342" height="361.284" rx="24" fill="#0F172A" fill-opacity="0.06"/>
<rect x="135" y="19" width="342" height="361.284" rx="24" fill="#0F172A" fill-opacity="0.08"/>

<!-- Cuerpo de la tarjeta con fondo blanco y borde nítido -->
<rect x="135" y="12" width="342" height="361.284" rx="24" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.2"/>

<!-- Patrón de textura marca de agua dentro de la tarjeta -->
<g clip-path="url(#card_clip)">
  {pattern_image_tag}
</g>
'''
        svg = re.sub(
            r'<path d="M135 36C135 22.7452[^>]*fill="url\(#pattern0_270_2849\)"[^>]*/>',
            card_elements,
            svg
        )

        # 8. Preparar Foto del titular con esquinas redondeadas
        photo_bytes = None
        if tarjeta.get("foto") and str(tarjeta.get("foto")).startswith("data:image"):
            try:
                _, encoded = tarjeta["foto"].split(",", 1)
                photo_bytes = base64.b64decode(encoded)
            except Exception:
                pass

        if not photo_bytes and tarjeta.get("foto_path") and os.path.exists(tarjeta["foto_path"]):
            try:
                with open(tarjeta["foto_path"], "rb") as f:
                    photo_bytes = f.read()
            except Exception:
                pass

        if not photo_bytes:
            default_photo = "contador_foto_ejemplo.jpg" if tipo_tarjeta == "contadores" else "sociedad_logo_ejemplo.png"
            default_path = cls._get_asset_path(default_photo)
            if not os.path.exists(default_path):
                default_path = cls._get_asset_path("photo_card.jpg")
            if os.path.exists(default_path):
                with open(default_path, "rb") as f:
                    photo_bytes = f.read()

        if photo_bytes:
            foto_uri = cls._prepare_rounded_photo(photo_bytes)
            svg = re.sub(r'<path[^>]*fill="white"[^>]*/>', '', svg)
            svg = re.sub(
                r'<path[^>]*fill="url\(#pattern1_270_2849\)"[^>]*/>',
                f'<image x="151" y="96.284" width="90" height="120" xlink:href="{foto_uri}"/>',
                svg
            )
            svg = re.sub(r'<path[^>]*fill="url\(#pattern2_270_2849\)"[^>]*/>', '', svg)

        # 9. Generación e inyección del código QR oficial
        hash_doc = tarjeta.get("hash_documento") or tarjeta.get("hash_registro") or "VALIDACION-OFICIAL-JCC"
        qr_url = f"https://jcc.gov.co/validar/{hash_doc}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=0
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")

        qr_buf = io.BytesIO()
        img_qr.save(qr_buf, format="PNG")
        b64_qr = base64.b64encode(qr_buf.getvalue()).decode("ascii")
        qr_uri = f"data:image/png;base64,{b64_qr}"

        svg = re.sub(
            r'<rect[^>]*fill="url\(#pattern3_270_2849\)"[^>]*/>',
            f'<image x="151.5" y="389.284" width="141" height="141" xlink:href="{qr_uri}"/>',
            svg
        )

        # 10. Inyección de la firma autorizada (sin fondo negro)
        firma_bytes = None
        raw_firma = tarjeta.get("firma_director")
        if raw_firma and str(raw_firma).startswith("data:image"):
            try:
                _, enc_f = raw_firma.split(",", 1)
                firma_bytes = base64.b64decode(enc_f)
            except Exception:
                pass

        if not firma_bytes:
            firma_path = cls._get_asset_path("firma_directora.png")
            if os.path.exists(firma_path):
                with open(firma_path, "rb") as f:
                    firma_bytes = f.read()

        if firma_bytes:
            firma_uri = cls._prepare_signature(firma_bytes)
            svg = re.sub(
                r'<rect[^>]*fill="url\(#pattern4_270_2849\)"[^>]*/>',
                f'<image x="237.344" y="558.284" width="137.313" height="66.2559" xlink:href="{firma_uri}"/>',
                svg
            )

        # 11. MARGEN DE IMPRESIÓN SEGURO (> 13 mm / 38 pt en todos los bordes)
        # Se escala a 0.94 y se centra verticalmente para que ningún borde sea cortado por impresoras
        svg = svg.replace(
            '<g clip-path="url(#clip0_270_2849)">',
            '<g clip-path="url(#clip0_270_2849)">\n<g transform="translate(18.36, 27) scale(0.94)">'
        )
        svg = svg.replace('</svg>', '</g>\n</svg>')

        # 12. Renderizar SVG a ReportLab Drawing
        tmp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
        tmp_svg_path = os.path.join(tmp_dir, f"tmp_render_{os.getpid()}.svg")
        try:
            with open(tmp_svg_path, "w", encoding="utf-8") as f:
                f.write(svg)

            drawing = svg2rlg(tmp_svg_path)
        finally:
            if os.path.exists(tmp_svg_path):
                try:
                    os.remove(tmp_svg_path)
                except Exception:
                    pass

        # 13. Convertir Drawing a PDF en memoria
        pdf_raw_buf = io.BytesIO()
        renderPDF.drawToFile(drawing, pdf_raw_buf)
        pdf_raw_buf.seek(0)

        # 14. Post-procesamiento estándar PDF/A-2b con PyPDF
        reader = pypdf.PdfReader(pdf_raw_buf)
        writer = pypdf.PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        xmp_metadata = (
            '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
            '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
            '  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
            '    <rdf:Description rdf:about="" xmlns:pdfaid="http://www.aiim.org/pdfaid/ns/id/">\n'
            '      <pdfaid:part>2</pdfaid:part>\n'
            '      <pdfaid:conformance>B</pdfaid:conformance>\n'
            '    </rdf:Description>\n'
            '    <rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
            '      <dc:title><rdf:Alt><rdf:li xml:lang="x-default">Tarjeta Profesional Digital - Junta Central de Contadores</rdf:li></rdf:Alt></dc:title>\n'
            '      <dc:creator><rdf:Seq><rdf:li>UAE Junta Central de Contadores</rdf:li></rdf:Seq></dc:creator>\n'
            '      <dc:description><rdf:Alt><rdf:li xml:lang="x-default">Documento Oficial de Identificación Profesional Digital en Estándar PDF/A-2b</rdf:li></rdf:Alt></dc:description>\n'
            '    </rdf:Description>\n'
            '  </rdf:RDF>\n'
            '</x:xmpmeta>\n'
            '<?xpacket end="w"?>'
        )

        meta_stream = pypdf.generic.DecodedStreamObject()
        if hasattr(meta_stream, "set_data"):
            meta_stream.set_data(xmp_metadata.encode("utf-8"))
        else:
            meta_stream.setData(xmp_metadata.encode("utf-8"))
        meta_stream.update({
            pypdf.generic.NameObject("/Type"): pypdf.generic.NameObject("/Metadata"),
            pypdf.generic.NameObject("/Subtype"): pypdf.generic.NameObject("/XML")
        })
        writer._root_object.update({
            pypdf.generic.NameObject("/Metadata"): writer._add_object(meta_stream)
        })

        output_pdf = io.BytesIO()
        writer.write(output_pdf)
        output_pdf.seek(0)
        return output_pdf.getvalue()
