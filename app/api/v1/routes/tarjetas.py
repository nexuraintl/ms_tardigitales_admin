from fastapi import APIRouter, Query, HTTPException, Path, Body, Form, File, UploadFile
from typing import List, Dict, Any, Optional
from app.services.tarjetas_service import TarjetasService
from app.utils.image_utils import ImageUtils
from app.schemas.tarjetas_schema import (
    TarjetaCreateSchema,
    ValidadorConfigSchema,
    BrandingCredentialsCreateSchema,
    BrandingCredentialsUpdateSchema,
    ConsultaTarjetaSchema
)

router = APIRouter()
service = TarjetasService()

@router.get("/list")
async def list_tarjetas(
    tipo_tarjeta: Optional[str] = Query(None, description="Filtrar por 'contadores' o 'sociedades'"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
    page: int = Query(1, ge=1, description="Número de página a consultar"),
    page_size: int = Query(10, ge=1, le=100, description="Cantidad de registros por página (máx 100)"),
    filtro_nombre: Optional[str] = Query(None, description="Nombre completo (contadores) o Razón social (sociedades)"),
    filtro_documento: Optional[str] = Query(None, description="Documento (contadores) o NIT (sociedades)"),
    filtro_expediente: Optional[str] = Query(None, description="Número de expediente"),
    filtro_resolucion: Optional[str] = Query(None, description="Número de resolución"),
    filtro_acta_jcc: Optional[str] = Query(None, description="Número de acta JCC"),
    filtro_no_tarjeta: Optional[str] = Query(None, description="Número de tarjeta (solo contadores)"),
    filtro_inscripcion: Optional[str] = Query(None, description="Inscripción (solo sociedades)"),
    order_by: Optional[str] = Query(None, description="Campo por el cual ordenar (ej: nombre_completo, fecha_emision)"),
    order_dir: str = Query("DESC", pattern="^(ASC|DESC)$", description="Dirección del ordenamiento: ASC o DESC")
):
    
    filtros = {
        "nombre": filtro_nombre,
        "documento": filtro_documento,
        "expediente": filtro_expediente,
        "resolucion": filtro_resolucion,
        "acta_jcc": filtro_acta_jcc,
        "no_tarjeta": filtro_no_tarjeta,
        "inscripcion": filtro_inscripcion
    }
    
    return await service.list_tarjetas(
        tipo_tarjeta=tipo_tarjeta,
        client_id=client_id,
        page=page,
        page_size=page_size,
        filtros=filtros,
        order_by=order_by,
        order_dir=order_dir
    )

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
    tipo_tarjeta: Optional[str] = Query(None, description="Filtrar por 'contadores' o 'sociedades'"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
):
    return await service.get_tarjeta(id, tipo_tarjeta ,client_id)

@router.post("/create")
async def create_tarjeta(
    data: TarjetaCreateSchema = Body(...),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.create_tarjeta(data, client_id)

@router.get("/historial/{id}")
async def get_historial(
    id: int = Path(..., description="ID de la tarjeta"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
    tipo: Optional[str] = Query(None, description="Tipo de tarjeta ('contador' o 'sociedad')")
):
    return await service.get_historial(id, client_id, tipo)

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
    idCliente: Optional[int] = Form(None),
    version_actual: int = Form(1),
    version_publicada: Optional[int] = Form(None),
    logo: Optional[UploadFile] = File(None),
    patron: Optional[UploadFile] = File(None),
    color_fondo: str = Form(...),
    color_letra: str = Form(...),
    fuente_letra: str = Form(...),
    usuario_creacion_id: int = Form(...),
    tipo_id: int = Form(...),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
):
    logo_base64 = await ImageUtils.upload_to_base64(logo)
    patron_base64 = await ImageUtils.upload_to_base64(patron)

    data = BrandingCredentialsCreateSchema(
        idCliente=idCliente,
        version_actual=version_actual,
        version_publicada=version_publicada,
        logo=logo_base64,
        patron=patron_base64,
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

@router.get("/branding-credentials/info-published/{id}")
async def get_branding_credentials(
    id: int = Path(..., description="ID único del Branding credentials"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.get_branding_credentials_publish(id, client_id)

@router.get("/branding-credentials/list-history-versions/{id}")
async def list_history_branding_credentials(
    id: int = Path(..., description="ID Branding credentials"),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
    page: int = Query(1, ge=1, description="Número de página a consultar"),
    page_size: int = Query(10, ge=1, le=100, description="Cantidad de registros por página (máx 100)")
):
    return await service.list_history_branding_credentials(id, client_id, page, page_size)

# Auditoria API
@router.get("/audit-api/list", response_model=Dict[str, Any])
@router.get("/auditoria-api/list", response_model=Dict[str, Any])
async def list_auditoria_api(
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente"),
    page: int = Query(1, ge=1, description="Número de página a consultar"),
    page_size: int = Query(10, ge=1, le=100, description="Cantidad de registros por página (máx 100)"),
    fecha_desde: Optional[str] = Query(None, description="Fecha y hora desde (YYYY-MM-DD HH:MM)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha y hora hasta (YYYY-MM-DD HH:MM)"),
    endpoint: Optional[str] = Query(None, description="Filtro por endpoint (contadores, sociedades)"),
    tipo: Optional[str] = Query(None, description="Filtro por tipo de operación (primeraVez,duplicado,sustitucion,modificacion)"),
    texto: Optional[str] = Query(None, description="Texto a buscar en petición o respuesta"),
    cambiar_estado: Optional[str] = Query(None, description="Filtro por cambiarEstado (true, false)"),
):
    return await service.list_auditoria_api(
        client_id=client_id,
        page=page,
        page_size=page_size,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        endpoint=endpoint,
        tipo=tipo,
        texto=texto,
        cambiar_estado=cambiar_estado,
    )

# Contador creacion
@router.post('/contador/create')
@router.post('/accountant/create')
async def create_tarjeta_contador(
    data: ConsultaTarjetaSchema = Body(...),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.create_tarjeta_contador(
        documento=data.documento,
        tipo=data.tipo,
        client_id=client_id,
    )

# society creacion
@router.post('/sociedad/create')
@router.post('/society/create')
async def create_tarjeta_sociedad(
    data: ConsultaTarjetaSchema = Body(...),
    client_id: Optional[int] = Query(None, description="ID de la entidad cliente")
):
    return await service.create_tarjeta_sociedad(
        documento=data.documento,
        tipo=data.tipo,
        client_id=client_id,
    )