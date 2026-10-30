import logging
from typing import Optional
from fastapi import APIRouter, Query, status
from app.schemas.otp import (
    SolicitarOtpRequestSchema,
    SolicitarOtpResponseSchema,
    ValidarOtpRequestSchema,
    ValidarOtpResponseSchema
)
from app.services.otp_service import otp_service

logger = logging.getLogger("routes_otp")

router = APIRouter()


@router.post(
    "/solicitar",
    response_model=SolicitarOtpResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Solicitar código OTP para activación móvil",
    description="Recibe el hash de la tarjeta (obtenido del QR) y el número de expediente ingresado por el titular. Verifica que pertenezcan a la misma tarjeta y genera el código OTP a través del servicio corporativo."
)
async def solicitar_otp(
    payload: SolicitarOtpRequestSchema,
    client_id: Optional[int] = Query(None, description="ID de cliente multi-tenant (opcional)")
):
    cid = payload.client_id or client_id
    return await otp_service.solicitar_otp(
        hash_sha256=payload.hash,
        expediente=payload.expediente,
        client_id=cid
    )


@router.post(
    "/validar",
    response_model=ValidarOtpResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Validar código OTP ingresado en App Móvil",
    description="Verifica si el código OTP de 6 dígitos suministrado por el usuario coincide y se encuentra vigente para la tarjeta especificada por su hash."
)
async def validar_otp(
    payload: ValidarOtpRequestSchema,
    client_id: Optional[int] = Query(None, description="ID de cliente multi-tenant (opcional)")
):
    cid = payload.client_id or client_id
    return await otp_service.validar_otp(
        hash_sha256=payload.hash,
        token=payload.token,
        expediente=payload.expediente,
        client_id=cid
    )
