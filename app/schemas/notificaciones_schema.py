from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class NotificacionCreateSchema(BaseModel):
    client_id: Optional[int] = Field(None, description="ID de la entidad cliente")
    titulo: str = Field(..., description="Título de la alerta")
    mensaje: str = Field(..., description="Mensaje detallado")
    tipo: Optional[str] = Field("Informativa", description="Tipo de alerta: Informativa, Preventiva, Urgente")
    canal: str = Field(..., description="Canal: Push, Alerta estándar, Notificación interna")
    audiencia: str = Field("Todos", description="Audiencia: Todos, Contadores, Sociedades")
    destinatarios: Optional[int] = Field(0, description="Número de destinatarios calculados")
    fecha: Optional[str] = Field(None, description="Fecha formateada de envío")
    estado: Optional[str] = Field("Programada", description="Estado: Entregada, Programada, Fallida, En proceso")
    creadoPor: Optional[str] = Field("Administrador", description="Usuario creador")
    hora_inicio: Optional[str] = Field("07:00", description="Hora de inicio de rango")
    hora_fin: Optional[str] = Field("17:00", description="Hora de fin de rango")
    max_diario: Optional[int] = Field(2, description="Máximo de alertas diarias")
    recurrencia: Optional[str] = Field("No repetir", description="Recurrencia programada")
    respetar_rango: Optional[bool] = Field(True, description="Indica si respeta el rango de horas")

class NotificacionItemSchema(BaseModel):
    id: int
    client_id: int
    titulo: str
    mensaje: str
    tipo: Optional[str] = "Informativa"
    canal: str
    audiencia: str
    destinatarios: int
    fecha: Optional[str] = None
    estado: str
    creadoPor: str
    hora_inicio: Optional[str] = None
    hora_fin: Optional[str] = None
    max_diario: Optional[int] = None
    recurrencia: Optional[str] = None
    respetar_rango: Optional[bool] = None
    fecha_creacion: Optional[str] = None
