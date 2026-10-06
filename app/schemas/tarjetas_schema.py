from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from fastapi import UploadFile, File, Form
from datetime import datetime
from enum import Enum

class EstadoTarjetaEnum(str, Enum):
    EMITIDA = "Emitida"
    ACTIVA = "Activa"
    CANCELADA = "Cancelada"

class EstadoRegistroEnum(str, Enum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"
    SUSPENDIDO = "SUSPENDIDO"
    CANCELADO = "CANCELADO"
    FALLECIDO = "FALLECIDO"

class TarjetaCreateSchema(BaseModel):
    tipo_tarjeta: Optional[str] = "contadores"
    tipoTarjeta: Optional[str] = None
    codigo: Optional[str] = None
    expediente: Optional[int] = 0
    solicitante: Optional[str] = None
    nombreTitular: Optional[str] = None
    documento: Optional[str] = None
    identificacion: Optional[str] = None
    matricula: Optional[str] = None
    numeroTarjeta: Optional[str] = None
    correo: Optional[str] = None
    representante: Optional[str] = None
    tarjeta: Optional[str] = "Activa"
    estado: Optional[str] = None
    fecha: Optional[str] = None

class ValidadorConfigSchema(BaseModel):
    val_foto: Optional[bool] = True
    val_nombres: Optional[bool] = True
    val_matricula: Optional[bool] = True
    val_numero_identificacion: Optional[bool] = True
    val_codigo_tarjeta: Optional[bool] = True
    val_estado: Optional[bool] = True

class ConsultaMatriculaResponseSchema(BaseModel):
    disponibles: list[Dict[str, Any]] = []
    pdf: Optional[str] = None
    encontrado: bool = False


class BrandingCredentialsCreateSchema(BaseModel):
    idCliente: Optional[int] = Field(None, description="ID del cliente (opcional)")
    version_actual: int = Field(1, description="Versión actual")
    version_publicada: Optional[int] = None
    logo: Optional[str] = None  # base64 string
    patron: Optional[str] = None
    logo_impresion: Optional[str] = None  # base64 string
    patron_impresion: Optional[str] = None  # base64 string
    color_fondo: str = Field(..., description="Color de fondo es requerido")
    color_letra: str = Field(..., description="Color de letra es requerido")
    color_letra_impresion: Optional[str] = Field("#0f172a", description="Color de letra para versión impresión")
    nombre_director: Optional[str] = Field(None, description="Nombre completo del director")
    firma_director: Optional[str] = Field(None, description="Firma del director (base64 string)")
    usuario_creacion_id: int = Field(..., description="ID del usuario creador")
    tipo_id: int = Field(..., description="ID del tipo es requerido")

class BrandingCredentialsUpdateSchema(BaseModel):
    version_publicada: Optional[int] = None
    logo: Optional[str] = None
    patron: Optional[str] = None
    logo_impresion: Optional[str] = None
    patron_impresion: Optional[str] = None
    color_fondo: Optional[str] = None
    color_letra: Optional[str] = None
    color_letra_impresion: Optional[str] = None
    nombre_director: Optional[str] = None
    firma_director: Optional[str] = None

class InstitucionalConfigCreateSchema(BaseModel):
    nombre_director: str = Field(..., description="Nombre completo del Director General")
    cargo_director: str = Field("DIRECTOR GENERAL", description="Cargo oficial del firmante")
    firma_director: Optional[str] = Field(None, description="Firma en Base64")
    usuario_creacion_id: Optional[int] = Field(141, description="ID del usuario creador")

class InstitucionalConfigUpdateSchema(BaseModel):
    version_publicada: int = Field(..., description="ID o versión a publicar")

class AuditoriaApiCreateSchema(BaseModel):
    client_id: int = Field(..., description="ID del cliente asociado a la operación")
    tipo_id: int = Field(..., description="ID del tipo de recurso (Contadores o Sociedades)")
    metodo: str = Field(..., description="Método HTTP (POST, GET, PUT, etc.)")
    url: str = Field(..., description="URL completa del endpoint consultado")
    fecha_creacion: Optional[datetime] = Field(None, description="Fecha y hora de la petición")
    tipo_asociado_id: Optional[int] = Field(None, description="ID del tipo de operación")
    duracion_ms: Optional[int] = Field(None, description="Duración de la petición en milisegundos")
    codigo_http: Optional[int] = Field(200, description="Código de respuesta HTTP (200, 400, 500, etc.)")
    parametros_peticion: Optional[Dict[str, Any]] = Field(None, description="Parámetros JSON enviados en la petición")

    cuerpo_respuesta_peticion: Optional[Dict[str, Any]] = Field(None, description="Cuerpo JSON de la respuesta del servidor")

class ContadorCreateSchema(BaseModel):
    no_tarjeta: str = Field(..., description="Número de tarjeta profesional")
    nombres: str = Field(..., description="Nombres del contador")
    primer_apellido: str = Field(..., description="Primer apellido")
    segundo_apellido: Optional[str] = Field(None, description="Segundo apellido")
    no_expd: int = Field(..., description="Número de expediente")
    tipo_documento: str = Field(..., description="Tipo de documento (CC, CE, etc.)")
    no_documento: int = Field(..., description="Número de documento")
    universidad: Optional[str] = Field(None, description="Universidad de egreso")
    estado_contador: str = Field("ACTIVO", description="Estado del contador")
    resolucion: Optional[str] = Field(None, description="Número de resolución")
    fecha_estado: Optional[datetime] = Field(None, description="Fecha del estado")
    fecha_radicacion: Optional[datetime] = Field(None, description="Fecha de radicación")
    fecha_resolucion: Optional[datetime] = Field(None, description="Fecha de resolución")
    acta_jcc: Optional[int] = Field(None, description="Número de acta de la JCC")
    fecha_grado: Optional[datetime] = Field(None, description="Fecha de grado")
    seccional: Optional[str] = Field(None, description="Seccional")
    correo: Optional[str] = Field(None, description="Correo del contador")
    fecha_emision: Optional[datetime] = Field(None, description="Fecha de emisión")
    tipo_asociado_id: int = Field(..., description="ID del tipo de asociado (primeraVez=1, duplicado=2, sustitucion=3, modificacion=4)")
    estado_tarjeta_id: int = Field(..., description="ID del estado de la tarjeta (Activa=1, Emitida=2, Cancelada=3)")
    foto: Optional[str] = Field(None, description="Foto contador")

class SociedadCreateSchema(BaseModel):
    no_expd: int = Field(..., description="Número de expediente")
    razon_social: str = Field(..., description="Razón social de la sociedad")
    nit: str = Field(..., description="NIT de la sociedad")
    tipo_sociedad: str = Field(..., description="Tipo de sociedad")
    inscripcion: Optional[int] = Field(None, description="Número de inscripción")
    fecha_radicacion: Optional[datetime] = Field(None, description="Fecha de radicación")
    estado_sociedad: str = Field("ACTIVO", description="Estado de la sociedad")
    resolucion: Optional[str] = Field(None, description="Número de resolución")
    fecha_resolucion: Optional[datetime] = Field(None, description="Fecha de resolución")
    acta_jcc: Optional[str] = Field(None, description="Número de acta de la JCC")
    estado_solicitud: Optional[str] = Field(None, description="Estado de la solicitud")
    tipo_solicitud: Optional[str] = Field(None, description="Tipo de solicitud")
    fecha_emision: Optional[datetime] = Field(None, description="Fecha de emisión")
    tipo_asociado_id: int = Field(..., description="ID del tipo de asociado (primeraVez=1, duplicado=2, sustitucion=3, modificacion=4)")
    estado_tarjeta_id: int = Field(..., description="ID del estado de la tarjeta (Activa=1, Emitida=2, Cancelada=3)")
    foto: Optional[str] = Field(None, description="Foto sociedad")
    representante_legal: Optional[str] = Field(None, description="Representante legal de la sociedad")

class ConsultaTarjetaSchema(BaseModel):
    documento: str = Field(..., description="Número de documento de identificación")
    tipo: Optional[str] = Field("", description="Tipo de consulta ('primeraVez', 'duplicado', 'sustitucion', 'modificacion', etc.)")

class EmisionMasivaRequestSchema(BaseModel):
    tipo_tarjeta: str = Field("contadores", description="Tipo de titular: 'contadores' o 'sociedades'")
    tipo_tramite: Optional[str] = Field("primeraVez", description="Tipo de trámite ('primeraVez', 'duplicado', 'sustitucion', 'modificacion')")
    identificaciones: List[str] = Field(..., description="Lista de números de documento o NITs a emitir")
    archivo_nombre: Optional[str] = Field(None, description="Nombre del archivo fuente CSV")
    asincrono: Optional[bool] = Field(False, description="Forzar procesamiento asíncrono en segundo plano")
    creado_por: Optional[str] = Field("Administrador", description="Usuario administrativo que realiza la carga")

class InstitucionalConfigCreateSchema(BaseModel):
    nombre_director: str = Field(..., description="Nombre completo del Director General de la JCC")
    cargo_director: Optional[str] = Field("DIRECTOR GENERAL", description="Cargo oficial institucional")
    firma_director: str = Field(..., description="Imagen en formato Base64 o data URI de la firma oficial")
    publicado: Optional[bool] = Field(True, description="Indica si entra en vigencia de inmediato")
    usuario_creacion_id: Optional[int] = Field(None, description="ID del usuario que realiza la modificación")

class InstitucionalConfigUpdateSchema(BaseModel):
    nombre_director: Optional[str] = Field(None, description="Nombre completo del Director General")
    cargo_director: Optional[str] = Field(None, description="Cargo oficial institucional")
    firma_director: Optional[str] = Field(None, description="Firma en Base64")
    publicado: Optional[bool] = Field(None, description="Estado de publicación")
