from fastapi import APIRouter, Query, Path, HTTPException, status, Response
from typing import Optional
from app.schemas.certificados import ProcesarCertificadoRequest, CertificadosListResponse, CertificadoItemResponse
from app.services.certificados_service import CertificadosService

router = APIRouter()
certificados_service = CertificadosService()

@router.get("", response_model=CertificadosListResponse, summary="Listar certificados unificados para el MFE")
async def listar_certificados(
    search: Optional[str] = Query(None, description="Término de búsqueda: certificado, NIT, documento o nombre"),
    tipo: Optional[str] = Query("todos", description="Filtro de titular: todos, contador, sociedad"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    result = await certificados_service.listar_certificados(
        search=search,
        tipo=tipo,
        page=page,
        page_size=page_size
    )
    return result

@router.get("/{n_certificado}", response_model=CertificadoItemResponse, summary="Obtener detalle de un certificado")
async def obtener_detalle(n_certificado: str = Path(..., description="Número único de certificado")):
    cert = await certificados_service.obtener_por_numero(n_certificado)
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificado no encontrado")
    return cert

@router.get("/{n_certificado}/pdf", summary="Descargar PDF oficial del certificado")
async def descargar_pdf(n_certificado: str = Path(..., description="Número único de certificado")):
    cert = await certificados_service.obtener_por_numero(n_certificado)
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificado no encontrado")
    
    # Contenido binario PDF mínimo para simulación oficial
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Title (Certificado Oficial) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="certificado-{n_certificado}.pdf"',
            "X-Numero-Certificado": n_certificado,
            "X-Origen-Documento": "ALMACENADO"
        }
    )

# Endpoint oficial de integración MyJCC
@router.post("/procesar", summary="Recepción y procesamiento de certificados desde MyJCC")
async def procesar_certificado(req: ProcesarCertificadoRequest):
    data = req.dict()
    guardado = await certificados_service.procesar_solicitud_myjcc(data)
    
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Title (Certificado Firmado ONAC) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="certificado-{req.N_CERTIFICADO}.pdf"',
            "X-Numero-Certificado": req.N_CERTIFICADO,
            "X-Origen-Documento": guardado["origen"]
        }
    )
