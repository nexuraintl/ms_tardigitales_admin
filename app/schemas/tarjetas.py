from pydantic import BaseModel, Field
from typing import Optional, List

class TarjetaBase(BaseModel):
    tipo_tarjeta: str = Field(..., example="contadores", description="Tipo de tarjeta: 'contadores' o 'sociedades'")
    codigo: str = Field(..., example="TC-2026-0045", description="Código único de la tarjeta")
    expediente: int = Field(..., example=84920, description="Número de expediente oficial")
    solicitante: str = Field(..., example="Carlos Alberto Mendoza", description="Nombre del titular o Razón Social")
    documento: str = Field(..., example="CC 1018472910", description="Documento de identidad o NIT")
    matricula: str = Field(..., example="MP-94820", description="Número de matrícula profesional o registro")
    correo: Optional[str] = Field(None, example="carlos.mendoza@email.com", description="Correo electrónico institucional")
    representante: Optional[str] = Field(None, example="N/A", description="Representante legal (aplica para sociedades)")
    tarjeta: str = Field(..., example="Virtual Activa", description="Estado de la credencial: 'Virtual Activa', 'En Trámite', etc.")
    fecha: str = Field(..., example="2026-05-18", description="Fecha de emisión (formato YYYY-MM-DD)")

class TarjetaCreate(TarjetaBase):
    client_id: int = Field(..., example=20001, description="ID de la entidad cliente")

class TarjetaResponse(TarjetaBase):
    id: int = Field(..., example=1, description="Identificador único del registro")

    class Config:
        from_attributes = True

class EstadoHistorialItem(BaseModel):
    id: int
    tarjeta_id: int
    estado: str
    descripcion: Optional[str]
    fecha: str
    realizado_por: str

class LecturaHistorialItem(BaseModel):
    id: int
    tarjeta_id: int
    fecha: str
    endpoint: str
    metodo: str
    codigo_http: int
    ip: str

class HistorialTarjetaResponse(BaseModel):
    estados: List[EstadoHistorialItem]
    lecturas: List[LecturaHistorialItem]

class ValidadorConfigSave(BaseModel):
    client_id: int = Field(..., example=20001)
    val_foto: int = Field(1, example=1)
    val_nombres: int = Field(1, example=1)
    val_matricula: int = Field(1, example=1)
    val_numero_identificacion: int = Field(0, example=0)
    val_codigo_tarjeta: int = Field(1, example=1)
    val_estado: int = Field(1, example=1)

class ValidadorConfigResponse(BaseModel):
    val_foto: int
    val_nombres: int
    val_matricula: int
    val_numero_identificacion: int
    val_codigo_tarjeta: int
    val_estado: int

