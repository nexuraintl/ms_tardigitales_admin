from fastapi import APIRouter, Query, HTTPException, Path, Body, Form, File, UploadFile
from typing import List, Dict, Any, Optional
from app.services.tarjetas_service import TarjetasService
from app.schemas.tarjetas_schema import (
    TarjetaCreateSchema,
    ValidadorConfigSchema,
    BrandingCredentialsCreateSchema,
    BrandingCredentialsUpdateSchema
)

router = APIRouter()
service = TarjetasService()

@router.get("/list")
async def list_tarjetas(
    tipo_tarjeta: Optional[str] = Query(None, description="Filtrar por 'contadores' o 'sociedades'"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.list_tarjetas(tipo_tarjeta, client_id)

@router.get("/consult-registry")
async def consult_registry(
    documento: str = Query(..., description="Número de documento de identidad o NIT a consultar"),
    tipo_tarjeta: str = Query("contadores", description="Tipo de registro ('contadores' o 'sociedades')"),
    tipo: Optional[str] = Query("", description="Tipo de consulta ('primeraVez', 'modificacion', etc.)"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.consult_registry(documento, tipo_tarjeta, tipo, client_id)


@router.get("/get/{id}")
async def get_tarjeta(
    id: int = Path(..., description="ID de la tarjeta"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.get_tarjeta(id, client_id)

@router.post("/create")
async def create_tarjeta(
    data: TarjetaCreateSchema = Body(...),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.create_tarjeta(data, client_id)

@router.get("/historial/{id}")
async def get_historial(
    id: int = Path(..., description="ID de la tarjeta"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.get_historial(id, client_id)

@router.get("/validador-qr/get-config")
async def get_validador_config(
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.get_validador_config(client_id)

@router.post("/validador-qr/update-config")
async def update_validador_config(
    data: ValidadorConfigSchema = Body(...),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.save_validador_config(data, client_id)


# Branding de credenciales
@router.post("/branding-credentials/create")
async def create_branding_credentials(
    idCliente: int = Form(...),
    version_actual: int = Form(1),
    version_publicada: Optional[int] = Form(None),
    logo: Optional[UploadFile] = File(None),
    color_fondo: str = Form(...),
    color_letra: str = Form(...),
    fuente_letra: str = Form(...),
    usuario_creacion_id: int = Form(...),
    tipo_id: int = Form(...),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
):
    logo_base64 = await service.process_image_to_base64(logo)

    data = BrandingCredentialsCreateSchema(
        idCliente=idCliente,
        version_actual=version_actual,
        version_publicada=version_publicada,
        logo=logo_base64,
        color_fondo=color_fondo,
        color_letra=color_letra,
        fuente_letra=fuente_letra,
        usuario_creacion_id=usuario_creacion_id,
        tipo_id=tipo_id,
    )

    return await service.create_or_update_branding_credentials(data, client_id)

@router.put("/branding-credentials/update/change-version/{id}")
async def update_branding_credentials(
    id: int = Path(..., description="ID único del Branding credentials"),
    data: BrandingCredentialsUpdateSchema = Body(...),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.update_branding_credentials_change_version(id, data, client_id)

@router.get("/branding-credentials/info/{id}")
async def get_branding_credentials(
    id: int = Path(..., description="ID único del Branding credentials"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.get_branding_credentials(id, client_id)

@router.get("/branding-credentials/info-publicada/{id}")
async def get_branding_credentials(
    id: int = Path(..., description="ID único del Branding credentials"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.get_branding_credentials_publish(id, client_id)

@router.get("/branding-credentials/list-history-versions/{id}")
async def list_history_branding_credentials(
    id: int = Path(..., description="ID Branding credentials"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.list_history_branding_credentials(id, client_id)

# Auditoria API
@router.get("/auditoria-api/list")
async def list_auditoria_api(
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.list_auditoria_api(client_id)

@router.post('/contador/create')
async def create_tarjeta_contador(
    documento: str = Query(..., description="Número de documento de identificacion"),
    tipo: Optional[str] = Query("", description="Tipo de consulta ('primeraVez', 'duplicado', 'sustitucion', etc.)"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.create_tarjeta_contador(documento, tipo, client_id)

@router.post('/sociedad/create')
async def create_tarjeta_sociedad(
    documento: str = Query(..., description="Número de documento de identificacion"),
    tipo: Optional[str] = Query("", description="Tipo de consulta ('primeraVez', 'duplicado', 'sustitucion', etc.)"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.create_tarjeta_sociedad(documento, tipo, client_id)