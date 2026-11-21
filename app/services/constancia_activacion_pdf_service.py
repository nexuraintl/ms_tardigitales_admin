"""
Servicio oficial de generación de PDF y gestión de plantillas Word (.docx)
para el Soporte de Activación de Tarjeta Digital.
Unidad Administrativa Especial Junta Central de Contadores (UAE JCC).
"""

import os
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, date
from typing import Dict, Any, Optional, List, Tuple
from xml.sax.saxutils import escape as xml_escape
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

KEYWORDS_CONTADORES: List[Tuple[str, str]] = [
    ("TARJETA_PROFESIONAL", "Tarjeta profesional"),
    ("NOMBRE_COMPLETO", "Nombre completo"),
    ("EXPEDIENTE", "Expediente"),
    ("TIPO", "Tipo"),
    ("FECHA_EMISION", "Fecha emisión"),
    ("CEDULA", "Cédula de ciudadanía"),
    ("CORREO", "Correo"),
    ("UNIVERSIDAD", "Universidad"),
    ("ESTADO_TARJETA", "Estado tarjeta"),
    ("ESTADO_REGISTRO", "Estado registro"),
    ("RESOLUCION", "Resolución"),
    ("FECHA_ESTADO", "Fecha del estado"),
    ("FECHA_RADICACION", "Fecha de radicación"),
    ("FECHA_RESOLUCION", "Fecha de resolución"),
    ("ACTA_JCC", "Acta JCC"),
    ("FECHA_GRADO", "Fecha de grado"),
    ("SECCIONAL", "Seccional"),
    ("FECHA_ACTIVACION", "Fecha activación"),
    ("NUMERO_SOPORTE", "Número de soporte (consecutivo por fecha de activación)"),
    ("FECHA_GENERACION", "Fecha y hora de generación del soporte"),
]

KEYWORDS_SOCIEDADES: List[Tuple[str, str]] = [
    ("EXPEDIENTE", "Expediente"),
    ("RAZON_SOCIAL", "Razón social"),
    ("NIT", "NIT"),
    ("TIPO", "Tipo"),
    ("CORREO", "Correo"),
    ("FECHA_EMISION", "Fecha emisión"),
    ("TIPO_REGISTRO", "Tipo de registro"),
    ("INSCRIPCION", "Inscripción"),
    ("FECHA_RADICACION", "Fecha de radicación"),
    ("ESTADO_TARJETA", "Estado de la tarjeta"),
    ("ESTADO_SOCIEDAD", "Estado de la sociedad"),
    ("RESOLUCION", "Resolución"),
    ("FECHA_RESOLUCION", "Fecha de resolución"),
    ("ACTA_JCC", "Acta JCC"),
    ("ESTADO_SOLICITUD", "Estado de la solicitud"),
    ("TIPO_SOLICITUD", "Tipo de solicitud"),
    ("FECHA_ACTIVACION", "Fecha activación"),
    ("NUMERO_SOPORTE", "Número de soporte (consecutivo por fecha de activación)"),
    ("FECHA_GENERACION", "Fecha y hora de generación del soporte"),
]

VALID_KEYS_CONTADORES = {k for k, _ in KEYWORDS_CONTADORES}
VALID_KEYS_SOCIEDADES = {k for k, _ in KEYWORDS_SOCIEDADES}

_CONTENT_TYPES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="jpg" ContentType="image/jpeg"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/><Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>"""

_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>"""

_STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial" w:eastAsia="Arial"/><w:sz w:val="20"/><w:szCs w:val="20"/><w:lang w:val="es-CO"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="80"/></w:pPr></w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>"""

_HEADER1_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:p><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:drawing><wp:anchor distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="0" behindDoc="1" locked="0" layoutInCell="1" allowOverlap="1"><wp:simplePos x="0" y="0"/><wp:positionH relativeFrom="page"><wp:align>center</wp:align></wp:positionH><wp:positionV relativeFrom="page"><wp:align>center</wp:align></wp:positionV><wp:extent cx="4572000" cy="5913120"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapNone/><wp:docPr id="2" name="Marca de agua"/><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="2" name="watermark.jpg"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rIdWm"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="4572000" cy="5913120"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:anchor></w:drawing></w:r><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="2377440" cy="597408"/><wp:docPr id="1" name="Logo JCC"/><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="1" name="logo.jpg"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rIdLogo"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="2377440" cy="597408"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p></w:hdr>"""

_FOOTER1_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:p><w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">Síguenos en:</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="right" w:pos="9640"/></w:tabs><w:spacing w:before="0" w:after="0"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:color w:val="1A9BD7"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr><w:t xml:space="preserve">www.jcc.gov.co</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:color w:val="1A9BD7"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:t xml:space="preserve">#TuHistoriaNuestraHistoria</w:t></w:r></w:p></w:ftr>"""

_DOC_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdS" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rIdH" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/><Relationship Id="rIdF" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/></Relationships>"""

_HDR_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdLogo" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/logo.jpg"/><Relationship Id="rIdWm" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/watermark.jpg"/></Relationships>"""

_DOCUMENT_CONTADORES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:body><w:p><w:pPr><w:spacing w:before="240" w:after="0"/><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr><w:t xml:space="preserve">UAE JUNTA CENTRAL DE CONTADORES</w:t></w:r></w:p><w:p><w:pPr><w:spacing w:before="0" w:after="360"/><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr><w:t xml:space="preserve">SOPORTE DE ACTIVACIÓN DE LA TARJETA PROFESIONAL DIGITAL</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="2700"/></w:tabs><w:spacing w:before="0" w:after="60"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr><w:t xml:space="preserve">Número de Soporte:</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr><w:t xml:space="preserve">{NUMERO_SOPORTE}</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="3500"/></w:tabs><w:spacing w:before="0" w:after="60"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr><w:t xml:space="preserve">Fecha y hora de generación:</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr><w:t xml:space="preserve">{FECHA_GENERACION}</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="5600"/></w:tabs><w:spacing w:before="0" w:after="300"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr><w:t xml:space="preserve">Identificador único de Registro (expediente):</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr><w:t xml:space="preserve">{EXPEDIENTE}</w:t></w:r></w:p><w:p><w:pPr><w:spacing w:before="0" w:after="100"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:t xml:space="preserve">1. Identificación del titular</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="4400"/></w:tabs><w:spacing w:before="0" w:after="60"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">Nombre completo:</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">{NOMBRE_COMPLETO}</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="4400"/></w:tabs><w:spacing w:before="0" w:after="60"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">Tipo de identificación:</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">Cédula de Ciudadanía</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="4400"/></w:tabs><w:spacing w:before="0" w:after="60"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">Número de identificación:</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">{CEDULA}</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="4400"/></w:tabs><w:spacing w:before="0" w:after="60"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">Número de Tarjeta Profesional:</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">{TARJETA_PROFESIONAL}</w:t></w:r></w:p><w:p><w:pPr><w:spacing w:before="200" w:after="100"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:t xml:space="preserve">2. Información de la Tarjeta Profesional Digital</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="4400"/></w:tabs><w:spacing w:before="0" w:after="60"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">Fecha y hora de emisión:</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">{FECHA_EMISION}</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="4400"/></w:tabs><w:spacing w:before="0" w:after="60"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">Fecha y hora de activación:</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">{FECHA_ACTIVACION}</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="4400"/></w:tabs><w:spacing w:before="0" w:after="60"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">Canal de activación:</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">Aplicación móvil (JCC DIGITAL)</w:t></w:r></w:p><w:p><w:pPr><w:spacing w:before="200" w:after="100"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:t xml:space="preserve">3. Soporte de activación y entrega</w:t></w:r></w:p><w:p><w:pPr><w:spacing w:before="0" w:after="200" w:line="300" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">De acuerdo con los registros generados por la Consola de Administración de Tarjeta Profesional Digital de la UAE Junta Central De Contadores, el titular identificado en el presente documento completó satisfactoriamente el proceso de activación de su Tarjeta Profesional Digital en la fecha y hora señaladas en este soporte.</w:t></w:r></w:p><w:p><w:pPr><w:spacing w:before="0" w:after="200" w:line="300" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">En consecuencia, el presente documento deja soporte de la activación y puesta a disposición de la Tarjeta Profesional Digital a su titular y constituye el soporte electrónico de su entrega en el entorno digital.</w:t></w:r></w:p><w:sectPr><w:headerReference w:type="default" r:id="rIdH"/><w:footerReference w:type="default" r:id="rIdF"/><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="2300" w:right="1300" w:bottom="1700" w:left="1300" w:header="600" w:footer="700" w:gutter="0"/></w:sectPr></w:body></w:document>"""

_DOCUMENT_SOCIEDADES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:body><w:p><w:pPr><w:spacing w:before="240" w:after="0"/><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr><w:t xml:space="preserve">UAE JUNTA CENTRAL DE CONTADORES</w:t></w:r></w:p><w:p><w:pPr><w:spacing w:before="0" w:after="360"/><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr><w:t xml:space="preserve">SOPORTE DE ACTIVACIÓN DE LA TARJETA PROFESIONAL DIGITAL</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="2700"/></w:tabs><w:spacing w:before="0" w:after="60"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr><w:t xml:space="preserve">Número de Soporte:</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr><w:t xml:space="preserve">{NUMERO_SOPORTE}</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="3500"/></w:tabs><w:spacing w:before="0" w:after="60"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr><w:t xml:space="preserve">Fecha y hora de generación:</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr><w:t xml:space="preserve">{FECHA_GENERACION}</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="5600"/></w:tabs><w:spacing w:before="0" w:after="300"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr><w:t xml:space="preserve">Identificador único de Registro (expediente):</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr><w:t xml:space="preserve">{EXPEDIENTE}</w:t></w:r></w:p><w:p><w:pPr><w:spacing w:before="0" w:after="100"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:t xml:space="preserve">1. Identificación del titular</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="4400"/></w:tabs><w:spacing w:before="0" w:after="60"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">Razón social:</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">{RAZON_SOCIAL}</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="4400"/></w:tabs><w:spacing w:before="0" w:after="60"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">Tipo de identificación:</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">NIT</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="4400"/></w:tabs><w:spacing w:before="0" w:after="60"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">Número de identificación:</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">{NIT}</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="4400"/></w:tabs><w:spacing w:before="0" w:after="60"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">Número de Tarjeta Profesional / Registro:</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">{INSCRIPCION}</w:t></w:r></w:p><w:p><w:pPr><w:spacing w:before="200" w:after="100"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:t xml:space="preserve">2. Información de la Tarjeta Profesional Digital</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="4400"/></w:tabs><w:spacing w:before="0" w:after="60"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">Fecha y hora de emisión:</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">{FECHA_EMISION}</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="4400"/></w:tabs><w:spacing w:before="0" w:after="60"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">Fecha y hora de activación:</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">{FECHA_ACTIVACION}</w:t></w:r></w:p><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="4400"/></w:tabs><w:spacing w:before="0" w:after="60"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">Canal de activación:</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">Aplicación móvil (JCC DIGITAL)</w:t></w:r></w:p><w:p><w:pPr><w:spacing w:before="200" w:after="100"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:b/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr><w:t xml:space="preserve">3. Soporte de activación y entrega</w:t></w:r></w:p><w:p><w:pPr><w:spacing w:before="0" w:after="200" w:line="300" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">De acuerdo con los registros generados por la Consola de Administración de Tarjeta Profesional Digital de la UAE Junta Central De Contadores, el titular identificado en el presente documento completó satisfactoriamente el proceso de activación de su Tarjeta Profesional Digital en la fecha y hora señaladas en este soporte.</w:t></w:r></w:p><w:p><w:pPr><w:spacing w:before="0" w:after="200" w:line="300" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr><w:t xml:space="preserve">En consecuencia, el presente documento deja soporte de la activación y puesta a disposición de la Tarjeta Profesional Digital a su titular y constituye el soporte electrónico de su entrega en el entorno digital.</w:t></w:r></w:p><w:sectPr><w:headerReference w:type="default" r:id="rIdH"/><w:footerReference w:type="default" r:id="rIdF"/><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="2300" w:right="1300" w:bottom="1700" w:left="1300" w:header="600" w:footer="700" w:gutter="0"/></w:sectPr></w:body></w:document>"""


def extraer_palabras_clave_docx(docx_bytes: bytes) -> List[str]:
    """
    Extrae todas las palabras clave escritas entre llaves {PALABRA_CLAVE}
    dentro de word/document.xml, word/header*.xml y word/footer*.xml.
    Lanza ValueError si el archivo no es un .docx (ZIP + XML) válido.
    """
    if not docx_bytes:
        raise ValueError("El archivo está vacío.")
    try:
        zf = zipfile.ZipFile(io.BytesIO(docx_bytes))
    except Exception as e:
        raise ValueError("El archivo seleccionado no es un documento Word (.docx) válido.") from e

    with zf:
        xml_names = [
            n for n in zf.namelist()
            if re.match(r"^word/(document|header\d*|footer\d*)\.xml$", n)
        ]
        if "word/document.xml" not in xml_names:
            raise ValueError("El archivo seleccionado no contiene una estructura Word (.docx) válida.")

        found: List[str] = []
        seen = set()
        pattern = re.compile(r"\{\s*([A-Za-z0-9_ÁÉÍÓÚÑáéíóúñ]+)\s*\}")
        for name in xml_names:
            try:
                tree = ET.fromstring(zf.read(name))
            except Exception as e_xml:
                raise ValueError("El contenido XML del documento Word (.docx) es inválido.") from e_xml

            for p in tree.iter(f"{W_NS}p"):
                text = "".join(t.text for t in p.iter(f"{W_NS}t") if t.text)
                for m in pattern.finditer(text):
                    key = m.group(1).strip()
                    if key and key not in seen:
                        seen.add(key)
                        found.append(key)
        return found


def validar_palabras_clave_docx(docx_bytes: bytes, tipo_tarjeta: str) -> Tuple[List[str], List[str]]:
    """
    Retorna (palabras_encontradas, palabras_invalidas) según el tipo ('contadores' o 'sociedades').
    """
    encontradas = extraer_palabras_clave_docx(docx_bytes)
    is_soc = "sociedad" in str(tipo_tarjeta or "").lower()
    valid_set = VALID_KEYS_SOCIEDADES if is_soc else VALID_KEYS_CONTADORES
    invalidas = [k for k in encontradas if k not in valid_set]
    return encontradas, invalidas


class ConstanciaActivacionPdfService:

    def __init__(self):
        self.assets_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets"
        )
        self.logo_path = os.path.join(self.assets_dir, "logo_certificado_jcc.jpg")
        self.watermark_path = os.path.join(self.assets_dir, "watermark_certificado_jcc.jpg")

    def generar_docx_ejemplo(self, tipo_tarjeta: str = "contadores") -> Tuple[bytes, str]:
        """
        Construye en memoria el archivo Word (.docx) oficial de ejemplo con las palabras clave
        ubicadas, el logotipo institucional y la marca de agua oficial.
        """
        is_soc = "sociedad" in str(tipo_tarjeta or "").lower()
        filename = (
            "Formato_ejemplo_Plantilla_Activacion_Sociedades.docx"
            if is_soc else
            "Formato_ejemplo_Plantilla_Activacion_Contadores.docx"
        )
        titulo_core = (
            "Formato de ejemplo – Plantilla de activación (sociedad)"
            if is_soc else
            "Formato de ejemplo – Plantilla de activación (contador)"
        )
        core_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f"<dc:title>{titulo_core}</dc:title>"
            '<dcterms:created xsi:type="dcterms:W3CDTF">2026-11-18T12:00:00Z</dcterms:created>'
            "</cp:coreProperties>"
        )

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", _CONTENT_TYPES_XML)
            zf.writestr("_rels/.rels", _RELS_XML)
            zf.writestr(
                "word/document.xml",
                _DOCUMENT_SOCIEDADES_XML if is_soc else _DOCUMENT_CONTADORES_XML,
            )
            zf.writestr("word/styles.xml", _STYLES_XML)
            zf.writestr("word/header1.xml", _HEADER1_XML)
            zf.writestr("word/footer1.xml", _FOOTER1_XML)
            zf.writestr("word/_rels/document.xml.rels", _DOC_RELS_XML)
            zf.writestr("word/_rels/header1.xml.rels", _HDR_RELS_XML)
            zf.writestr("docProps/core.xml", core_xml)
            if os.path.exists(self.logo_path):
                zf.write(self.logo_path, "word/media/logo.jpg")
            if os.path.exists(self.watermark_path):
                zf.write(self.watermark_path, "word/media/watermark.jpg")
        buf.seek(0)
        return buf.getvalue(), filename

    @staticmethod
    def _format_datetime(dt_val: Any, empty_default: str = "No registrada") -> str:
        """Formatea fecha y hora a DD/MM/AAAA – HH:MM:SS."""
        if dt_val is None or str(dt_val).strip() == "":
            return empty_default
        if isinstance(dt_val, (datetime, date)):
            if isinstance(dt_val, datetime):
                return dt_val.strftime("%d/%m/%Y – %H:%M:%S")
            return dt_val.strftime("%d/%m/%Y – 00:00:00")

        s = str(dt_val).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(s.split(".")[0], fmt)
                if ":" in s:
                    return dt.strftime("%d/%m/%Y – %H:%M:%S")
                return dt.strftime("%d/%m/%Y – 00:00:00")
            except Exception:
                continue
        return s

    @classmethod
    def construir_mapa_reemplazo(cls, datos: Dict[str, Any], tipo_tarjeta: str = "contadores") -> Dict[str, str]:
        """
        Construye el diccionario de reemplazo {PALABRA_CLAVE: valor} para un registro
        de contador o sociedad. Si un campo no tiene valor, retorna cadena vacía "".
        """
        is_soc = "sociedad" in str(tipo_tarjeta or datos.get("tipo_tarjeta") or "").lower()

        def clean_val(v: Any) -> str:
            if v is None:
                return ""
            s = str(v).strip()
            return "" if s.lower() == "none" else s

        def clean_date(v: Any) -> str:
            if v is None or str(v).strip() == "":
                return ""
            return cls._format_datetime(v, empty_default="")

        consecutivo = datos.get("consecutivo_soporte_activacion") or datos.get("consecutivo")
        anio_act = datetime.now().year
        f_act_raw = datos.get("fecha_activacion")
        if f_act_raw:
            m_yr = re.search(r"(20\d{2})", str(f_act_raw))
            if m_yr:
                anio_act = int(m_yr.group(1))
        numero_soporte = f"ACT-{anio_act}-{int(consecutivo):06d}" if consecutivo else ""
        fecha_gen = datetime.now().strftime("%d/%m/%Y – %H:%M:%S")

        if is_soc:
            return {
                "EXPEDIENTE": clean_val(datos.get("no_expd")),
                "RAZON_SOCIAL": clean_val(datos.get("razon_social") or datos.get("nombre_completo")),
                "NIT": clean_val(datos.get("nit") or datos.get("no_documento")),
                "TIPO": clean_val(datos.get("tipo_asociado")),
                "CORREO": clean_val(datos.get("correo")),
                "FECHA_EMISION": clean_date(datos.get("fecha_emision")),
                "TIPO_REGISTRO": clean_val(datos.get("tipo_sociedad")),
                "INSCRIPCION": clean_val(datos.get("inscripcion") or datos.get("no_tarjeta")),
                "FECHA_RADICACION": clean_date(datos.get("fecha_radicacion")),
                "ESTADO_TARJETA": clean_val(datos.get("estado_tarjeta") or datos.get("estado")),
                "ESTADO_SOCIEDAD": clean_val(datos.get("estado_sociedad")),
                "RESOLUCION": clean_val(datos.get("resolucion")),
                "FECHA_RESOLUCION": clean_date(datos.get("fecha_resolucion")),
                "ACTA_JCC": clean_val(datos.get("acta_jcc")),
                "ESTADO_SOLICITUD": clean_val(datos.get("estado_solicitud")),
                "TIPO_SOLICITUD": clean_val(datos.get("tipo_solicitud")),
                "FECHA_ACTIVACION": clean_date(datos.get("fecha_activacion")),
                "NUMERO_SOPORTE": numero_soporte,
                "FECHA_GENERACION": fecha_gen,
            }

        nombre_comp = clean_val(datos.get("nombre_completo"))
        if not nombre_comp:
            noms = clean_val(datos.get("nombres"))
            ap1 = clean_val(datos.get("primer_apellido"))
            ap2 = clean_val(datos.get("segundo_apellido"))
            nombre_comp = " ".join(x for x in (noms, ap1, ap2) if x)

        return {
            "TARJETA_PROFESIONAL": clean_val(datos.get("no_tarjeta")),
            "NOMBRE_COMPLETO": nombre_comp,
            "EXPEDIENTE": clean_val(datos.get("no_expd")),
            "TIPO": clean_val(datos.get("tipo_asociado")),
            "FECHA_EMISION": clean_date(datos.get("fecha_emision")),
            "CEDULA": clean_val(datos.get("no_documento")),
            "CORREO": clean_val(datos.get("correo")),
            "UNIVERSIDAD": clean_val(datos.get("universidad")),
            "ESTADO_TARJETA": clean_val(datos.get("estado_tarjeta") or datos.get("estado")),
            "ESTADO_REGISTRO": clean_val(datos.get("estado_contador")),
            "RESOLUCION": clean_val(datos.get("resolucion")),
            "FECHA_ESTADO": clean_date(datos.get("fecha_estado")),
            "FECHA_RADICACION": clean_date(datos.get("fecha_radicacion")),
            "FECHA_RESOLUCION": clean_date(datos.get("fecha_resolucion")),
            "ACTA_JCC": clean_val(datos.get("acta_jcc")),
            "FECHA_GRADO": clean_date(datos.get("fecha_grado")),
            "SECCIONAL": clean_val(datos.get("seccional")),
            "FECHA_ACTIVACION": clean_date(datos.get("fecha_activacion")),
            "NUMERO_SOPORTE": numero_soporte,
            "FECHA_GENERACION": fecha_gen,
        }

    @staticmethod
    def _reemplazar_placeholders(texto: str, mapa: Dict[str, str]) -> str:
        if not texto:
            return ""
        pattern = re.compile(r"\{\s*([A-Za-z0-9_ÁÉÍÓÚÑáéíóúñ]+)\s*\}")
        return pattern.sub(lambda m: mapa.get(m.group(1).strip(), ""), texto)

    def generar_pdf_desde_docx(self, docx_bytes: Optional[bytes], datos: Dict[str, Any]) -> bytes:
        """
        Si existe plantilla Word (.docx) activa (docx_bytes), reemplaza todas las palabras clave
        por los valores del registro y renderiza el documento en PDF.
        Si no existe plantilla activa o falla la lectura, usa el generador por defecto actual.
        """
        if not docx_bytes:
            return self.generar_pdf(datos)

        try:
            tipo = str(datos.get("tipo_tarjeta") or datos.get("tipo") or "contadores").lower()
            mapa = self.construir_mapa_reemplazo(datos, tipo)

            with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
                doc_xml = zf.read("word/document.xml")
                logo_img = None
                wm_img = None
                for name in zf.namelist():
                    low = name.lower()
                    if low.startswith("word/media/") and ("logo" in low or "image1" in low):
                        try:
                            logo_img = ImageReader(io.BytesIO(zf.read(name)))
                        except Exception:
                            pass
                    elif low.startswith("word/media/") and ("watermark" in low or "wm" in low or "image2" in low):
                        try:
                            wm_img = ImageReader(io.BytesIO(zf.read(name)))
                        except Exception:
                            pass

            tree = ET.fromstring(doc_xml)
            body = tree.find(f"{W_NS}body")
            if body is None:
                return self.generar_pdf(datos)

            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            w_page, h_page = letter  # 612 x 792 pt
            x_left = 65.0
            x_right = 547.0
            width_body = x_right - x_left

            def draw_page_chrome():
                # Marca de agua
                if wm_img is not None:
                    c.saveState()
                    clip = c.beginPath()
                    clip.rect(x_left, 60, width_body, h_page - 120)
                    c.clipPath(clip, stroke=0, fill=0)
                    c.drawImage(wm_img, x_left + 15, 120, width=440.0, height=560.0, mask="auto")
                    c.restoreState()
                elif os.path.exists(self.watermark_path):
                    c.saveState()
                    clip = c.beginPath()
                    clip.rect(x_left, 60, width_body, h_page - 120)
                    c.clipPath(clip, stroke=0, fill=0)
                    c.drawImage(self.watermark_path, x_left + 15, 120, width=440.0, height=560.0, mask="auto")
                    c.restoreState()

                # Logo superior
                if logo_img is not None:
                    c.drawImage(logo_img, x_right - 230.0, h_page - 80, width=230.0, height=58.0, mask="auto")
                elif os.path.exists(self.logo_path):
                    c.drawImage(self.logo_path, x_right - 230.0, h_page - 80, width=230.0, height=58.0, mask="auto")

                # Pie de página institucional
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

            draw_page_chrome()
            y = h_page - 108.0

            for elem in body:
                tag = elem.tag.split("}")[-1]
                if tag == "p":
                    y = self._render_docx_paragraph(c, elem, mapa, x_left, x_right, width_body, w_page, h_page, y, draw_page_chrome)
                elif tag == "tbl":
                    y = self._render_docx_table(c, elem, mapa, x_left, x_right, width_body, h_page, y, draw_page_chrome)

            c.showPage()
            c.save()
            buffer.seek(0)
            return buffer.getvalue()
        except Exception as e_docx:
            print(f"[ConstanciaActivacionPdfService] Fallback a generador por defecto tras error en .docx: {e_docx}")
            return self.generar_pdf(datos)

    def _render_docx_paragraph(
        self,
        c: canvas.Canvas,
        p_elem: ET.Element,
        mapa: Dict[str, str],
        x_left: float,
        x_right: float,
        width_body: float,
        w_page: float,
        h_page: float,
        y: float,
        draw_page_chrome,
    ) -> float:
        pPr = p_elem.find(f"{W_NS}pPr")
        jc_val = "left"
        before_pt = 0.0
        after_pt = 4.0
        tab_pos_pt: Optional[float] = None

        if pPr is not None:
            jc = pPr.find(f"{W_NS}jc")
            if jc is not None and jc.get(f"{W_NS}val"):
                jc_val = jc.get(f"{W_NS}val", "left")
            spacing = pPr.find(f"{W_NS}spacing")
            if spacing is not None:
                if spacing.get(f"{W_NS}before"):
                    try:
                        before_pt = float(spacing.get(f"{W_NS}before", "0")) / 20.0
                    except Exception:
                        pass
                if spacing.get(f"{W_NS}after"):
                    try:
                        after_pt = float(spacing.get(f"{W_NS}after", "80")) / 20.0
                    except Exception:
                        pass
            tabs = pPr.find(f"{W_NS}tabs")
            if tabs is not None:
                tab_el = tabs.find(f"{W_NS}tab")
                if tab_el is not None and tab_el.get(f"{W_NS}pos"):
                    try:
                        tab_pos_pt = float(tab_el.get(f"{W_NS}pos", "3600")) / 20.0
                    except Exception:
                        pass

        # Extraer runs y detectar si hay tabulador o placeholders divididos entre runs
        segments: List[List[Tuple[str, bool, float]]] = [[]]
        max_font_sz = 10.0
        for r in p_elem.findall(f"{W_NS}r"):
            rPr = r.find(f"{W_NS}rPr")
            is_bold = rPr is not None and rPr.find(f"{W_NS}b") is not None
            sz_pt = 10.0
            if rPr is not None:
                sz_el = rPr.find(f"{W_NS}sz")
                if sz_el is not None and sz_el.get(f"{W_NS}val"):
                    try:
                        sz_pt = float(sz_el.get(f"{W_NS}val", "20")) / 2.0
                    except Exception:
                        pass
            if sz_pt > max_font_sz:
                max_font_sz = sz_pt

            for child in r:
                ctag = child.tag.split("}")[-1]
                if ctag == "tab":
                    segments.append([])
                elif ctag == "t" and child.text:
                    segments[-1].append((child.text, is_bold, sz_pt))

        full_raw = "".join("".join(t for t, _, _ in seg) for seg in segments)
        if not full_raw.strip():
            return y - max(6.0, before_pt + after_pt)

        y -= before_pt
        if y < 85.0:
            c.showPage()
            draw_page_chrome()
            y = h_page - 108.0

        # Caso 1: Párrafo con tabulador (etiqueta: \t valor)
        if len(segments) >= 2:
            left_text = self._reemplazar_placeholders("".join(t for t, _, _ in segments[0]), mapa)
            right_text = self._reemplazar_placeholders("".join("".join(t for t, _, _ in seg) for seg in segments[1:]), mapa)
            left_bold = any(b for _, b, _ in segments[0])
            right_bold = any(b for seg in segments[1:] for _, b, _ in seg)

            y -= max_font_sz + 3.0
            c.setFillColor(colors.HexColor("#0f172a"))
            c.setFont("Helvetica-Bold" if left_bold else "Helvetica", max_font_sz)
            c.drawString(x_left, y, left_text)

            col_offset = tab_pos_pt if tab_pos_pt is not None else max(150.0, c.stringWidth(left_text, "Helvetica-Bold", max_font_sz) + 14.0)
            label_w = c.stringWidth(left_text, "Helvetica-Bold" if left_bold else "Helvetica", max_font_sz)
            if col_offset < label_w + 10.0:
                col_offset = label_w + 10.0

            c.setFont("Helvetica-Bold" if right_bold else "Helvetica", max_font_sz)
            c.drawString(x_left + col_offset, y, right_text)
            return y - max(3.0, after_pt)

        # Caso 2: Párrafo continuo (centrado, justificado o alineado)
        # Reconstruir HTML para Paragraph de ReportLab reemplazando placeholders sobre el texto unido
        any_bold = any(b for _, b, _ in segments[0])
        all_bold = bool(segments[0]) and all(b for _, b, _ in segments[0])
        replaced_full = self._reemplazar_placeholders(full_raw, mapa)

        if jc_val == "center" and len(replaced_full) < 95:
            y -= max_font_sz + 4.0
            c.setFillColor(colors.HexColor("#0f172a"))
            c.setFont("Helvetica-Bold" if any_bold else "Helvetica", max_font_sz)
            c.drawCentredString(w_page / 2.0, y, replaced_full.strip())
            return y - max(3.0, after_pt)

        align_map = {
            "center": TA_CENTER,
            "both": TA_JUSTIFY,
            "distribute": TA_JUSTIFY,
            "right": TA_RIGHT,
        }
        p_style = ParagraphStyle(
            name="DocxParagraph",
            fontName="Helvetica-Bold" if all_bold else "Helvetica",
            fontSize=max_font_sz,
            leading=max_font_sz * 1.45,
            alignment=align_map.get(jc_val, TA_LEFT),
            textColor=colors.HexColor("#0f172a"),
        )

        # Si mezcla negrita e inline normal (ej. "Nombre completo: {NOMBRE_COMPLETO}" sin tab)
        if any_bold and not all_bold:
            parts_html = []
            # Unir runs contiguos con mismo bold para no cortar placeholders
            grouped: List[Tuple[str, bool]] = []
            for txt, b, _ in segments[0]:
                if grouped and grouped[-1][1] == b:
                    grouped[-1] = (grouped[-1][0] + txt, b)
                else:
                    grouped.append((txt, b))
            for g_txt, g_bold in grouped:
                rep = xml_escape(self._reemplazar_placeholders(g_txt, mapa))
                parts_html.append(f"<b>{rep}</b>" if g_bold else rep)
            html_text = "".join(parts_html)
        else:
            html_text = xml_escape(replaced_full)

        para = Paragraph(html_text, p_style)
        _, h_p = para.wrap(width_body, 400)
        if y - h_p < 75.0:
            c.showPage()
            draw_page_chrome()
            y = h_page - 108.0
        para.drawOn(c, x_left, y - h_p)
        return y - h_p - max(4.0, after_pt)

    def _render_docx_table(
        self,
        c: canvas.Canvas,
        tbl_elem: ET.Element,
        mapa: Dict[str, str],
        x_left: float,
        x_right: float,
        width_body: float,
        h_page: float,
        y: float,
        draw_page_chrome,
    ) -> float:
        rows = tbl_elem.findall(f"{W_NS}tr")
        if not rows:
            return y
        y -= 6.0
        for tr in rows:
            cells = tr.findall(f"{W_NS}tc")
            if not cells:
                continue
            if y < 90.0:
                c.showPage()
                draw_page_chrome()
                y = h_page - 108.0
            col_w = width_body / max(1, len(cells))
            y -= 15.0
            for idx, tc in enumerate(cells):
                raw_cell = " ".join(
                    "".join(t.text for t in p.iter(f"{W_NS}t") if t.text)
                    for p in tc.findall(f"{W_NS}p")
                ).strip()
                text_cell = self._reemplazar_placeholders(raw_cell, mapa)
                is_bold = tc.find(f".//{W_NS}b") is not None
                c.setFillColor(colors.HexColor("#0f172a"))
                c.setFont("Helvetica-Bold" if is_bold else "Helvetica", 9.5)
                c.drawString(x_left + idx * col_w + 4.0, y, text_cell[:75])
            c.setStrokeColor(colors.HexColor("#e2e8f0"))
            c.setLineWidth(0.5)
            c.line(x_left, y - 4.0, x_right, y - 4.0)
        return y - 8.0

    def generar_pdf(self, datos: Dict[str, Any]) -> bytes:
        """
        Genera el PDF del Soporte de Activación por defecto en formato Carta.
        """
        tipo = str(datos.get("tipo_tarjeta") or datos.get("tipo") or "contadores").lower()
        is_sociedad = "sociedad" in tipo

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

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        w_page, h_page = letter
        x_left = 65.0
        x_right = 547.0
        width_body = x_right - x_left

        if os.path.exists(self.watermark_path):
            c.saveState()
            clip = c.beginPath()
            clip.rect(x_left, 60, width_body, h_page - 120)
            c.clipPath(clip, stroke=0, fill=0)
            c.drawImage(self.watermark_path, x_left + 15, 120, width=440.0, height=560.0, mask="auto")
            c.restoreState()

        if os.path.exists(self.logo_path):
            logo_w = 230.0
            logo_h = 58.0
            c.drawImage(self.logo_path, x_right - logo_w, h_page - 80, width=logo_w, height=logo_h, mask="auto")

        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.HexColor("#0f172a"))
        y = h_page - 120
        c.drawCentredString(w_page / 2.0, y, "UAE JUNTA CENTRAL DE CONTADORES")
        y -= 16
        c.drawCentredString(w_page / 2.0, y, "SOPORTE DE ACTIVACIÓN DE LA TARJETA PROFESIONAL")
        y -= 16
        c.drawCentredString(w_page / 2.0, y, "DIGITAL")

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
