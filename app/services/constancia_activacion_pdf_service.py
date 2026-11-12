"""
Servicio oficial de generación de PDF para el Soporte de Activación de Tarjeta Digital.
Unidad Administrativa Especial Junta Central de Contadores (UAE JCC).
Replica fielmente el formato oficial "Soporte de Activación de Tarjeta Digital".
"""

import os
import io
from datetime import datetime, date
from typing import Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER


class ConstanciaActivacionPdfService:

    def __init__(self):
        self.assets_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets"
        )
        self.logo_path = os.path.join(self.assets_dir, "logo_certificado_jcc.jpg")
        self.watermark_path = os.path.join(self.assets_dir, "watermark_certificado_jcc.jpg")

    @staticmethod
    def _format_datetime(dt_val: Any) -> str:
        """Formatea fecha y hora a DD/MM/AAAA – HH:MM:SS."""
        if not dt_val:
            return "No registrada"
        if isinstance(dt_val, (datetime, date)):
            if isinstance(dt_val, datetime):
                return dt_val.strftime("%d/%m/%Y – %H:%M:%S")
            return dt_val.strftime("%d/%m/%Y")
        
        s = str(dt_val).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(s.split(".")[0], fmt)
                if ":" in s:
                    return dt.strftime("%d/%m/%Y – %H:%M:%S")
                return dt.strftime("%d/%m/%Y")
            except Exception:
                continue
        return s

    def generar_pdf(self, datos: Dict[str, Any]) -> bytes:
        """
        Genera el PDF del Soporte de Activación en formato Carta.
        """
        tipo = str(datos.get("tipo_tarjeta") or datos.get("tipo") or "contadores").lower()
        is_sociedad = "sociedad" in tipo

        # 1. Normalización de campos
        if is_sociedad:
            titular_label = "Razón social:"
            titular_val = str(datos.get("razon_social") or datos.get("nombre_completo") or "").strip().upper()
            tipo_doc = "NIT"
            no_doc = str(datos.get("nit") or datos.get("no_documento") or "").strip()
            registro_label = "Número de Tarjeta Profesional / Registro:"
            registro_val = str(datos.get("no_tarjeta") or datos.get("inscripcion") or datos.get("resolucion") or "-").strip()
        else:
            titular_label = "Nombre completo:"
            titular_val = str(datos.get("nombre_completo") or "").strip().upper()
            if not titular_val:
                noms = str(datos.get("nombres") or "").strip()
                ap1 = str(datos.get("primer_apellido") or "").strip()
                ap2 = str(datos.get("segundo_apellido") or "").strip()
                titular_val = f"{noms} {ap1} {ap2}".strip().upper()
            tipo_doc = str(datos.get("tipo_documento") or "CÉDULA DE CIUDADANÍA").upper()
            if "CC" in tipo_doc:
                tipo_doc = "Cédula de Ciudadanía"
            elif "CE" in tipo_doc:
                tipo_doc = "Cédula de Extranjería"
            elif "NIT" in tipo_doc:
                tipo_doc = "NIT"
            no_doc = str(datos.get("no_documento") or "").strip()
            registro_label = "Número de Tarjeta Profesional:"
            registro_val = str(datos.get("no_tarjeta") or "-").strip()

        no_expd = str(datos.get("no_expd") or "-").strip()
        consecutivo = datos.get("consecutivo_soporte_activacion") or datos.get("consecutivo")
        soporte_num = f"ACT-{datetime.now().year}-{int(consecutivo):06d}" if consecutivo else "Sin consecutivo"
        
        fecha_gen = datetime.now().strftime("%d/%m/%Y – %H:%M:%S")
        fecha_emision = self._format_datetime(datos.get("fecha_emision"))
        fecha_activacion = self._format_datetime(datos.get("fecha_activacion"))

        # 2. Configuración canvas ReportLab
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        w_page, h_page = letter  # 612 x 792 pt
        x_left = 65.0            # Margen izquierdo
        x_right = 547.0          # Margen derecho
        width_body = x_right - x_left

        # 3. Marca de agua suave institucional (fondo)
        if os.path.exists(self.watermark_path):
            c.saveState()
            clip = c.beginPath()
            clip.rect(x_left, 60, width_body, h_page - 120)
            c.clipPath(clip, stroke=0, fill=0)
            c.drawImage(self.watermark_path, x_left + 15, 120, width=440.0, height=560.0, mask="auto")
            c.restoreState()

        # 4. Logo superior oficial (MinComercio + UAE JCC) a la derecha
        if os.path.exists(self.logo_path):
            logo_w = 230.0
            logo_h = 58.0
            c.drawImage(self.logo_path, x_right - logo_w, h_page - 80, width=logo_w, height=logo_h, mask="auto")

        # 5. Título centrado
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.HexColor("#0f172a"))
        y = h_page - 120
        c.drawCentredString(w_page / 2.0, y, "UAE JUNTA CENTRAL DE CONTADORES")
        y -= 16
        c.drawCentredString(w_page / 2.0, y, "SOPORTE DE ACTIVACIÓN DE LA TARJETA PROFESIONAL")
        y -= 16
        c.drawCentredString(w_page / 2.0, y, "DIGITAL")

        # 6. Metadatos de cabecera
        y -= 36
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(x_left, y, "Número de Soporte: ")
        c.setFont("Helvetica", 10.5)
        c.drawString(x_left + 120, y, soporte_num)

        y -= 18
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(x_left, y, "Fecha y hora de generación: ")
        c.setFont("Helvetica", 10.5)
        c.drawString(x_left + 160, y, fecha_gen)

        y -= 18
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(x_left, y, "Identificador único de Registro (expediente): ")
        c.setFont("Helvetica", 10.5)
        c.drawString(x_left + 245, y, no_expd)

        # 7. Sección 1. Identificación del titular
        y -= 34
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x_left, y, "1. Identificación del titular")

        y -= 20
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_left, y, titular_label)
        c.setFont("Helvetica", 10)
        c.drawString(x_left + 150, y, titular_val)

        y -= 18
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_left, y, "Tipo de identificación:")
        c.setFont("Helvetica", 10)
        c.drawString(x_left + 150, y, tipo_doc)

        y -= 18
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_left, y, "Número de identificación:")
        c.setFont("Helvetica", 10)
        c.drawString(x_left + 150, y, no_doc)

        y -= 18
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_left, y, registro_label)
        c.setFont("Helvetica", 10)
        c.drawString(x_left + (240 if is_sociedad else 180), y, registro_val)

        # 8. Sección 2. Información de la Tarjeta Profesional Digital
        y -= 32
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x_left, y, "2. Información de la Tarjeta Profesional Digital")

        y -= 20
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_left, y, "Fecha y hora de emisión:")
        c.setFont("Helvetica", 10)
        c.drawString(x_left + 150, y, fecha_emision)

        y -= 18
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_left, y, "Fecha y hora de activación:")
        c.setFont("Helvetica", 10)
        c.drawString(x_left + 150, y, fecha_activacion)

        y -= 18
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x_left, y, "Canal de activación:")
        c.setFont("Helvetica", 10)
        c.drawString(x_left + 150, y, "Aplicación móvil (JCC DIGITAL)")

        # 9. Sección 3. Soporte de activación y entrega
        y -= 32
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x_left, y, "3. Soporte de activación y entrega")

        style_parrafo = ParagraphStyle(
            name="SoporteTexto",
            fontName="Helvetica",
            fontSize=9.5,
            leading=14.5,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor("#1e293b")
        )

        p1_text = (
            "De acuerdo con los registros generados por la Consola de Administración de "
            "Tarjeta Profesional Digital de la UAE Junta Central De Contadores, el titular "
            "identificado en el presente documento completó satisfactoriamente el proceso "
            "de activación de su Tarjeta Profesional Digital en la fecha y hora señaladas en "
            "este soporte."
        )
        p1 = Paragraph(p1_text, style_parrafo)
        y -= 12
        w_p1, h_p1 = p1.wrap(width_body, 100)
        p1.drawOn(c, x_left, y - h_p1)

        y = y - h_p1 - 12
        p2_text = (
            "En consecuencia, el presente documento deja soporte de la activación y puesta "
            "a disposición de la Tarjeta Profesional Digital a su titular y constituye el soporte "
            "electrónico de su entrega en el entorno digital."
        )
        p2 = Paragraph(p2_text, style_parrafo)
        w_p2, h_p2 = p2.wrap(width_body, 100)
        p2.drawOn(c, x_left, y - h_p2)

        # 10. Pie de página institucional oficial
        y_footer = 42.0
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#334155"))
        c.drawString(x_left, y_footer + 14, "Síguenos en:")

        c.setFont("Helvetica-Bold", 9.5)
        c.setFillColor(colors.HexColor("#0284c7"))
        c.drawString(x_left, y_footer, "www.jcc.gov.co")

        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor("#0284c7"))
        c.drawRightString(x_right, y_footer + 4, "#TuHistoriaNuestraHistoria")

        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer.getvalue()

