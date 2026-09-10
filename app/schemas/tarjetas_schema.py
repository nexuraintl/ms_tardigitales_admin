from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from fastapi import UploadFile, File, Form
from datetime import datetime

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
    idCliente: int = Field(..., description="ID del cliente es requerido")
    version_actual: int = Field(1, description="Versión actual")
    version_publicada: Optional[int] = None
    logo: Optional[str] = None  # Ya NO es UploadFile, será base64 string
    color_fondo: str = Field(..., description="Color de fondo es requerido")
    color_letra: str = Field(..., description="Color de letra es requerido")
    fuente_letra: str = Field(..., description="Fuente es requerida")
    usuario_creacion_id: int = Field(..., description="ID del usuario creador")
    tipo_id: int = Field(..., description="ID del tipo es requerido")

class BrandingCredentialsUpdateSchema(BaseModel):
    version_publicada: Optional[int] = None
    logo: Optional[str] = None
    color_fondo: Optional[str] = None
    color_letra: Optional[str] = None
    fuente_letra: Optional[str] = None

class AuditoriaApiCreateSchema(BaseModel):
    client_id: int = Field(..., description="ID del cliente asociado a la operación")
    tipo_id: int = Field(..., description="ID del tipo de recurso (Contadores o Sociedades)")
    metodo: str = Field(..., description="Método HTTP (POST, GET, PUT, etc.)")
    url: str = Field(..., description="URL completa del endpoint consultado")
    fecha_creacion: Optional[datetime] = Field(None, description="Fecha y hora de la petición")
    tipo_asociado_id: Optional[int] = Field(None, description="ID del tipo de operación")
    duracion_ms: Optional[int] = Field(None, description="Duración de la petición en milisegundos")
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
    fecha_emision: Optional[datetime] = Field(None, description="Fecha de emisión")
    tipo_asociado_id: int = Field(..., description="ID del tipo de asociado (primeraVez=1, duplicado=2, sustitucion=3)")
    estado_tarjeta_id: int = Field(..., description="ID del estado de la tarjeta (Activa=1, Emitida=2, Cancelada=3)")

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
    tipo_asociado_id: int = Field(..., description="ID del tipo de asociado (primeraVez=1, duplicado=2, sustitucion=3)")
    estado_tarjeta_id: int = Field(..., description="ID del estado de la tarjeta (Activa=1, Emitida=2, Cancelada=3)")