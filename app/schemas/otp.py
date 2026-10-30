from pydantic import BaseModel, Field
from typing import Optional


class SolicitarOtpRequestSchema(BaseModel):
    hash: str = Field(
        ...,
        min_length=10,
        max_length=64,
        example="fb98bcc7ef3167edae16559c4d04b1ffe663735108db2bad5ff6c741b1ef6898",
        description="Hash SHA-256 canónico de la tarjeta obtenido tras escanear el código QR"
    )
    expediente: str = Field(
        ...,
        min_length=1,
        max_length=45,
        example="375883",
        description="Número de expediente ingresado por el titular para validar su identidad"
    )
    client_id: Optional[int] = Field(
        None,
        description="ID de la entidad cliente (multi-tenant)"
    )


class SolicitarOtpResponseSchema(BaseModel):
    status: str = Field("success", example="success")
    message: str = Field(
        "Código de verificación generado y despachado.",
        example="Código de verificación generado y despachado."
    )
    correo_enmascarado: str = Field(
        ...,
        example="k***2@hotmail.com",
        description="Correo electrónico donde se envió el OTP, con caracteres enmascarados para privacidad"
    )
    expira_en_minutos: int = Field(5, example=5, description="Minutos de vigencia del código OTP")


class ValidarOtpRequestSchema(BaseModel):
    hash: str = Field(
        ...,
        min_length=10,
        max_length=64,
        example="fb98bcc7ef3167edae16559c4d04b1ffe663735108db2bad5ff6c741b1ef6898",
        description="Hash SHA-256 canónico de la tarjeta obtenido del código QR"
    )
    token: str = Field(
        ...,
        min_length=4,
        max_length=10,
        example="573882",
        description="Código OTP numérico ingresado por el usuario"
    )
    expediente: Optional[str] = Field(
        None,
        example="375883",
        description="Número de expediente (opcional para validación adicional)"
    )
    client_id: Optional[int] = Field(
        None,
        description="ID de la entidad cliente (multi-tenant)"
    )


class ValidarOtpResponseSchema(BaseModel):
    status: str = Field("success", example="success")
    validado: bool = Field(True, example=True, description="Indica si el OTP es válido y vigente")
    message: str = Field(
        "Código OTP validado correctamente.",
        example="Código OTP validado correctamente."
    )
