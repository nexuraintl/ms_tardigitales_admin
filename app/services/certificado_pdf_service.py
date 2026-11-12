"""
Servicio oficial de generación de PDF para Certificados de Vigencia y Antecedentes Disciplinarios.
Unidad Administrativa Especial Junta Central de Contadores (UAE JCC).
Replica con fidelidad milimétrica el diseño oficial expedido por la entidad.
"""

import os
import io
import base64
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY


class CertificadoPdfService:
    MESES_ES = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    def __init__(self):
        self.assets_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets"
        )
        self.logo_path = os.path.join(self.assets_dir, "logo_certificado_jcc.jpg")
        self.watermark_path = os.path.join(self.assets_dir, "watermark_certificado_jcc.jpg")
        self.firma_path = os.path.join(self.assets_dir, "firma_directora_certificado.jpg")

    @staticmethod
    def _decode_firma_image(firma_raw: Any) -> Optional[ImageReader]:
        """Decodifica una firma en base64 o bytes a ImageReader para ReportLab."""
        if not firma_raw:
            return None
        try:
            if isinstance(firma_raw, bytes):
                return ImageReader(io.BytesIO(firma_raw))
            if isinstance(firma_raw, str):
                s = firma_raw.strip()
                if "," in s:
                    s = s.split(",", 1)[1]
                b = base64.b64decode(s)
                return ImageReader(io.BytesIO(b))
        except Exception as e:
            print(f"[CertificadoPdfService] Aviso decodificando firma dinámica: {e}")
            return None

    @staticmethod
    def _draw_justified_line(
        c: canvas.Canvas,
        text: str,
        x_left: float,
        x_right: float,
        y: float,
        font_name: str,
        font_size: float
    ):
        """Dibuja una línea de texto justificada exactamente entre x_left y x_right."""
        words = text.split()
        if len(words) <= 1:
            c.setFont(font_name, font_size)
            c.drawString(x_left, y, text)
            return

        total_words_width = sum(c.stringWidth(w, font_name, font_size) for w in words)
        available_space = (x_right - x_left) - total_words_width
        space_per_gap = available_space / (len(words) - 1)
        cur_x = x_left
        c.setFont(font_name, font_size)
        for w in words:
            c.drawString(cur_x, y, w)
            cur_x += c.stringWidth(w, font_name, font_size) + space_per_gap

    def _parse_fecha(self, fecha_val: Any) -> tuple[int, str, int]:
        """Parsea fecha y retorna (dia, mes_nombre, anio)."""
        if isinstance(fecha_val, (datetime, date)):
            d, m, y = fecha_val.day, fecha_val.month, fecha_val.year
            return d, self.MESES_ES[m - 1], y

        fecha_str = str(fecha_val or "").strip()
        if not fecha_str:
            hoy = date.today()
            return hoy.day, self.MESES_ES[hoy.month - 1], hoy.year

        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                dt = datetime.strptime(fecha_str.split("T")[0].split()[0], fmt.split()[0])
                return dt.day, self.MESES_ES[dt.month - 1], dt.year
            except Exception:
                continue

        hoy = date.today()
        return hoy.day, self.MESES_ES[hoy.month - 1], hoy.year

    def generar_pdf(self, cert_data: Dict[str, Any]) -> bytes:
        """
        Genera el flujo binario del PDF para un certificado con la diagramación
        exacta requerida por la UAE Junta Central de Contadores.
        """
        # 1. Normalización de campos
        tipo = str(cert_data.get("tipo") or cert_data.get("type") or "contador").lower()
        is_contador = (tipo == "contador")
        
        n_cert = str(
            cert_data.get("N_CERTIFICADO") or
            cert_data.get("certificateNumber") or
            cert_data.get("n_certificado") or
            "0000000000"
        ).strip().upper()

        detalles = cert_data.get("Detalles") or cert_data.get("payload_detalles") or {}

        # Nombre titular
        if is_contador:
            nombres = detalles.get("CON_NOMBRES") or ""
            ap1 = detalles.get("CON_APELLIDO1") or ""
            ap2 = detalles.get("CON_APELLIDO2") or ""
            nombre_titular = f"{nombres} {ap1} {ap2}".strip()
            if not nombre_titular:
                nombre_titular = cert_data.get("nombre_titular") or cert_data.get("holder") or ""
        else:
            nombre_titular = detalles.get("SOC_RAZON_SOCIAL") or cert_data.get("nombre_titular") or cert_data.get("holder") or ""

        nombre_titular = nombre_titular.strip().upper()

        # Documento
        documento = str(
            detalles.get("CON_NRO_DOCUMENTO") or
            detalles.get("SOC_NIT") or
            cert_data.get("documento") or
            cert_data.get("identifier") or
            ""
        ).strip()

        # Tipo de documento
        tdoc_raw = str(detalles.get("TDOC_CODIGO") or "CC").upper()
        if "CC" in tdoc_raw or "CEDULA" in tdoc_raw:
            tipo_doc_desc = "CÉDULA DE CIUDADANÍA"
        elif "CE" in tdoc_raw:
            tipo_doc_desc = "CÉDULA DE EXTRANJERÍA"
        elif "NIT" in tdoc_raw:
            tipo_doc_desc = "NIT"
        elif "PAS" in tdoc_raw:
            tipo_doc_desc = "PASAPORTE"
        else:
            tipo_doc_desc = tdoc_raw

        # Municipio y departamento
        mun = (
            detalles.get("MUNICIPIO_DOCUMENTO") or
            detalles.get("MUNICIPIO") or
            cert_data.get("documentMunicipality") or
            cert_data.get("municipality") or
            "BOGOTÁ D.C."
        ).strip().upper()

        depto = (
            detalles.get("DEPARTAMENTO_DOCUMENTO") or
            detalles.get("DEPARTAMENTO") or
            cert_data.get("documentDepartment") or
            cert_data.get("department") or
            "BOGOTÁ D.C."
        ).strip().upper()

        # Tarjeta profesional o registro de sociedad
        tarjeta = str(
            detalles.get("CON_NRO_TARJETA") or
            cert_data.get("professionalCard") or
            ""
        ).strip()
        if tarjeta and not tarjeta.endswith("-T") and not tarjeta.endswith("-P"):
            tipo_tarjeta = str(detalles.get("CON_TIPO_TARJETA") or "T").upper()
            tarjeta = f"{tarjeta}-{tipo_tarjeta}"

        soc_codigo = str(
            detalles.get("SOC_CODIGO") or
            cert_data.get("companyCode") or
            ""
        ).strip()

        rep_legal = str(
            detalles.get("SOC_REPRESENTANTE_LEGAL") or
            cert_data.get("legalRepresentative") or
            ""
        ).strip().upper()

        # Destinatario
        dirigido = str(cert_data.get("dirigido") or "QUIEN INTERESE").strip().upper()

        # Antecedentes
        antecedentes = (
            detalles.get("ANTECEDENTES") or
            cert_data.get("antecedents") or
            []
        )

        # Fecha de expedición
        fecha_raw = (
            cert_data.get("fechaGeneracion") or
            cert_data.get("fecha_generacion") or
            cert_data.get("generatedAt") or
            date.today()
        )
        dia, mes_nombre, anio = self._parse_fecha(fecha_raw)

        # Ciudad de expedición
        ciudad_exp = "BOGOTA"

        # -------------------------------------------------------------
        # CONSTRUCCIÓN DEL DOCUMENTO PDF EN REPORTLAB
        # -------------------------------------------------------------
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        w_page, h_page = letter  # 612 x 792 pt
        x_left = 85.039          # Margen izquierdo estándar (30 mm)
        x_right = 526.961        # Margen derecho estándar
        width_body = x_right - x_left  # 441.922 pt

        # 1. Marca de Agua Oficial Centrada (Fondo)
        if os.path.exists(self.watermark_path):
            c.saveState()
            clip = c.beginPath()
            clip.rect(x_left, 113.066, width_body, 566.831 - 113.066)
            c.clipPath(clip, stroke=0, fill=0)
            c.drawImage(self.watermark_path, x_left, -15.169, width=450.0, height=582.0, mask="auto")
            c.restoreState()

        # 2. Logotipo Superior UAE Junta Central de Contadores
        if os.path.exists(self.logo_path):
            c.drawImage(self.logo_path, 148.704, 657.773, width=311.811, height=76.535, mask="auto")

        # 3. Encabezado "Certificado No:"
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)
        c.drawCentredString(306.0, 620.247, "Certificado No:")

        # 4. Círculos de Seguridad con los Dígitos del Certificado
        n_chars = len(n_cert)
        step = 22.78
        badge_w = 20.0
        total_w = (n_chars - 1) * step + badge_w
        start_x = 306.0 - (total_w / 2.0)
        y_badge_base = 596.177

        for i, char in enumerate(n_cert):
            bx = start_x + (i * step)
            cx = bx + 10.0
            cy = y_badge_base + 10.0

            # Círculo exterior con borde azul acero
            c.setStrokeColor(colors.HexColor("#8EAFDF"))
            c.setFillColor(colors.HexColor("#F4F8FD"))
            c.setLineWidth(1.0)
            c.circle(cx, cy, 10.0, stroke=1, fill=1)

            # Anillo concéntrico interior suave
            c.setStrokeColor(colors.HexColor("#BFD5F5"))
            c.setLineWidth(0.6)
            c.circle(cx, cy, 8.4, stroke=1, fill=0)

            # Carácter centrado en azul marino oficial
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(colors.HexColor("#0B2554"))
            c.drawCentredString(cx, cy - 3.5, char)

        # 5. Textos Institucionales Centrados
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.black)
        c.drawCentredString(306.0, 558.651, "LA REPUBLICA DE COLOMBIA")
        c.drawCentredString(306.0, 538.898, "MINISTERIO DE COMERCIO, INDUSTRIA Y TURISMO")
        c.drawCentredString(306.0, 519.145, "UNIDAD ADMINISTRATIVA ESPECIAL")
        c.drawCentredString(306.0, 499.392, "JUNTA CENTRAL DE CONTADORES")
        c.drawCentredString(306.0, 473.969, "CERTIFICA A:")

        c.setFont("Helvetica", 10)
        c.drawCentredString(306.0, 462.719, dirigido)

        # 6. Párrafo Principal de Certificación (Justificado)
        style_body = ParagraphStyle(
            "CertBody",
            fontName="Helvetica",
            fontSize=10,
            leading=11.25,
            alignment=TA_JUSTIFY,
            textColor=colors.black
        )

        if is_contador:
            p1_html = (
                f"Que el contador público <b>{nombre_titular}</b> identificado con "
                f"{tipo_doc_desc} No {documento} de {mun} ({depto}) "
                f"Y Tarjeta Profesional No {tarjeta} SI tiene vigente su inscripción en la "
                f"Junta Central de Contadores y desde la fecha de Inscripción."
            )
        else:
            rep_text = f" (Representante Legal: <b>{rep_legal}</b>)" if rep_legal else ""
            p1_html = (
                f"Que la sociedad <b>{nombre_titular}</b> identificada con "
                f"NIT No {documento} de {mun} ({depto}){rep_text} "
                f"y Registro No {soc_codigo} SI tiene vigente su inscripción en la "
                f"Junta Central de Contadores y desde la fecha de Inscripción."
            )

        p1 = Paragraph(p1_html, style_body)
        w1, h1 = p1.wrap(width_body, 120)
        p1.drawOn(c, x_left, 434.37 - h1)

        # 7. Bloque de Antecedentes Disciplinarios
        if not antecedentes:
            # 3 renglones protegidos con asteriscos para evitar adiciones fraudulentas
            ast_l1 = "NO REGISTRA ANTECEDENTES DISCIPLINARIOS " + " ".join(["*"] * 30)
            ast_l2 = " ".join(["*"] * 66)
            ast_l3 = " ".join(["*"] * 66)

            self._draw_justified_line(c, ast_l1, x_left, x_right, 375.200, "Helvetica-Bold", 10)
            self._draw_justified_line(c, ast_l2, x_left, x_right, 363.950, "Helvetica-Bold", 10)
            self._draw_justified_line(c, ast_l3, x_left, x_right, 352.700, "Helvetica-Bold", 10)
        else:
            # En caso de registrar sanciones disciplinarias
            mapa_sanciones = {
                "S": "SUSPENSIÓN",
                "C": "CANCELACIÓN",
                "A": "AMONESTACIÓN",
                "M": "MULTA"
            }
            
            ast_header = "REGISTRA LOS SIGUIENTES ANTECEDENTES DISCIPLINARIOS: " + " ".join(["*"] * 10)
            self._draw_justified_line(c, ast_header, x_left, x_right, 375.200, "Helvetica-Bold", 10)
            
            sanciones_textos = []
            for item in antecedentes:
                stipo_raw = str(item.get("SAN_TIPO") or item.get("sanctionType") or "Sanción").strip()
                stipo = mapa_sanciones.get(stipo_raw.upper(), stipo_raw.upper())
                
                sres = str(item.get("SAN_RESOLUCION") or item.get("resolutionNumber") or "").strip()
                sfres = str(item.get("SAN_FECHA_RESOLUCION") or item.get("resolutionDate") or "").split()[0]
                sfej = str(item.get("SAN_FECHA_EJECUTORIA") or item.get("enforcementDate") or "").split()[0]
                smeses = item.get("SAN_MESES") or item.get("durationMonths")
                
                txt = f"• <b>Sanción:</b> {stipo}"
                if sres:
                    txt += f" según Resolución No <b>{sres}</b>"
                if sfres:
                    txt += f" del {sfres}"
                if sfej:
                    txt += f", ejecutoria {sfej}"
                if smeses:
                    txt += f", con duración de {smeses} meses"
                txt += "."
                sanciones_textos.append(txt)

            p_ant = Paragraph("<br/>".join(sanciones_textos), style_body)
            w_ant, h_ant = p_ant.wrap(width_body, 60)
            p_ant.drawOn(c, x_left, 365.0 - h_ant)

        # 8. Fecha y Vigencia
        p3_html = (
            f"Dado en {ciudad_exp} a los {dia} días del mes de {mes_nombre} de {anio} "
            f"con vigencia de (3) Meses, contados a partir de la fecha de su expedición."
        )
        p3 = Paragraph(p3_html, style_body)
        w3, h3 = p3.wrap(width_body, 80)
        p3.drawOn(c, x_left, 313.0 - h3)

        # 9 y 10. Bloque Dinámico de Firma Oficial, Nombre y Cargo
        nombre_director = str(
            cert_data.get("nombre_director") or
            detalles.get("NOMBRE_DIRECTOR") or
            "SANDRA MILENA BARRIOS PULIDO"
        ).strip().upper()

        cargo_director = str(
            cert_data.get("cargo_director") or
            detalles.get("CARGO_DIRECTOR") or
            "DIRECTOR GENERAL"
        ).strip().upper()

        firma_custom_raw = cert_data.get("firma_director") or detalles.get("FIRMA_DIRECTOR")
        firma_img = self._decode_firma_image(firma_custom_raw)

        if firma_img:
            # Caso A: Firma cargada dinámicamente desde base de datos / branding institucional
            c.drawImage(firma_img, 245.082, 236.0, width=119.055, height=48.0, mask="auto")
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(colors.black)
            c.drawCentredString(306.0, 226.0, nombre_director)
            c.drawCentredString(306.0, 214.905, cargo_director)
        elif nombre_director and nombre_director != "SANDRA MILENA BARRIOS PULIDO":
            # Caso B: Nuevo director configurado pero usando la silueta de firma institucional
            firma_transparente = os.path.join(self.assets_dir, "firma_directora.png")
            img_firma = firma_transparente if os.path.exists(firma_transparente) else self.firma_path
            if os.path.exists(img_firma):
                c.drawImage(img_firma, 245.082, 236.0, width=119.055, height=45.0, mask="auto")
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(colors.black)
            c.drawCentredString(306.0, 226.0, nombre_director)
            c.drawCentredString(306.0, 214.905, cargo_director)
        else:
            # Caso C: Configuración oficial de referencia JCC (Sandra Milena Barrios Pulido)
            if os.path.exists(self.firma_path):
                c.drawImage(self.firma_path, 245.082, 224.085, width=119.055, height=48.188, mask="auto")
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(colors.black)
            c.drawCentredString(306.0, 214.905, cargo_director)

        # 11. Validez Legal Digital (Marco Normativo)
        c.setFont("Helvetica", 10)
        c.drawCentredString(306.0, 175.309, "ESTE CERTIFICADO DIGITAL TIENE PLENA VALIDEZ DE CONFORMIDAD CON LO")
        c.drawCentredString(306.0, 164.059, "ESTABLECIDO EN EL ARTICULO 2 DE LA LEY 527 DE 1999, DECRETO UNICO")
        c.drawCentredString(306.0, 152.809, "REGLAMENTARIO 1074 DE 2015 Y ARTICULO 6 PARAGRAFO 3 DE LA LEY 962 DEL 2005")

        # 12. Mecanismo de Verificación y Consulta
        c.drawCentredString(306.0, 127.386, "Para confirmar los datos y veracidad de este certificado, lo puede consultar en la página web")
        c.drawCentredString(306.0, 116.136, "www.jcc.gov.co digitando el número del certificado")

        c.save()
        return buffer.getvalue()

