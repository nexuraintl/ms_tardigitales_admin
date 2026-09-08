from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

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
    logo: Optional[str] = None
    color_fondo: str = Field(..., description="Color de fondo es requerido") 
    color_letra: str = Field(..., description="Color de letra es requerido") 
    fuente_letra: str = Field(..., description="Fuente es requerida") 
    usuario_creacion_id: int = Field(80, description="ID del usuario creador")
    usuario_actualizacion_id: Optional[int] = None
    tipo_id: int = Field(..., description="ID del tipo es requerido")

class BrandingCredentialsUpdateSchema(BaseModel):
    version_publicada: Optional[int] = None
    logo: Optional[str] = None
    color_fondo: Optional[str] = None
    color_letra: Optional[str] = None
    fuente_letra: Optional[str] = None
    usuario_actualizacion_id: Optional[int] = None