from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime

class AntecedenteSchema(BaseModel):
    SAN_TIPO: str
    SAN_MESES: Optional[Union[int, str]] = None
    SAN_RESOLUCION: str
    SAN_FECHA_RESOLUCION: Optional[Union[str, datetime]] = None
    SAN_FECHA_EJECUTORIA: Optional[Union[str, datetime]] = None
    SAN_FECHA_FIN: Optional[Union[str, datetime]] = None

class ProcesarCertificadoRequest(BaseModel):
    Nuevo: bool = Field(True, description="true para primera emisión, false para redescarga")
    fechaGeneracion: Optional[Union[str, date]] = None
    tipo: str = Field(..., description="contador o sociedad")
    documento: str
    N_CERTIFICADO: str
    historia: Optional[str] = "5"
    dirigido: Optional[str] = "QUIEN INTERESE"
    Detalles: Dict[str, Any]

class CertificadoItemResponse(BaseModel):
    id: str
    type: str
    certificateNumber: str
    identifier: str
    holder: str
    generatedAt: str
    signedAt: Optional[str] = None
    status: str
    professionalCard: Optional[str] = None
    cardType: Optional[str] = None
    documentMunicipality: Optional[str] = None
    documentDepartment: Optional[str] = None
    companyCode: Optional[str] = None
    legalRepresentative: Optional[str] = None
    municipality: Optional[str] = None
    department: Optional[str] = None
    updatedAt: str
    antecedents: List[Dict[str, Any]] = []

class CertificadosListResponse(BaseModel):
    total: int
    items: List[CertificadoItemResponse]
