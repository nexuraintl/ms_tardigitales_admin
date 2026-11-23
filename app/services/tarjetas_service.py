import time
import base64
from typing import List, Dict, Any, Optional, Tuple
from fastapi import HTTPException, UploadFile, status
from datetime import datetime
from app.repositories.tarjetas_repository import TarjetasRepository
from app.schemas.tarjetas_schema import (
    ActivacionMovilRequestSchema,
    RegistroLecturaRequestSchema,
    TarjetaCreateSchema,
    ValidadorConfigSchema,
    BrandingCredentialsCreateSchema,
    BrandingCredentialsUpdateSchema,
    AuditoriaApiCreateSchema,
    ContadorCreateSchema,
    SociedadCreateSchema,
    ConsultaMatriculaResponseSchema,
    EstadoTarjetaEnum,
    EstadoRegistroEnum,
    InstitucionalConfigCreateSchema,
    InstitucionalConfigUpdateSchema
)
from app.integrations.jcc_client import JccClient
from app.services.auditoria_service import AuditoriaService
from app.constants import TipoTarjeta
from app.core.exceptions import PipelineException

class TarjetasService:

    def __init__(self):
        self.repository = TarjetasRepository()
        self.jcc_client = JccClient()
        self.auditoria = AuditoriaService(self.repository)

    async def consult_registry(
        self,
        documento: str,
        tipo_tarjeta: str = "contadores",
        tipo: str = "",
        client_id: Optional[int] = None
    ) -> Dict[str, Any]:
        
        start = time.perf_counter()
        result: Optional[Dict[str, Any]] = None

        if not documento or not str(documento).strip():
            raise PipelineException(
                etapa="PARAMETROS_INVALIDOS",
                mensaje="El número de documento de identidad o NIT es estrictamente requerido para la consulta.",
                cliente_id=client_id,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Consultar API de la JCC a través del módulo de integraciones (con auditoría automática garantizada)
            result = await self.jcc_client.consultar_registro(
                documento=documento,
                tipo_tarjeta=tipo_tarjeta,
                tipo=tipo,
                client_id=client_id,
            )
        except Exception as e:
            print(f"[TarjetasService] Error al consultar registro JCC: {e}")
            raise PipelineException(
                etapa="CONSULTA_API_JCC",
                mensaje="Error al consultar el registro institucional en la API de la JCC.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                contexto=f"documento={documento}, tipo_tarjeta={tipo_tarjeta}, tipo={tipo}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not result or not result.get("encontrado") or not result.get("data"):
            # Respaldo: Buscar si existe en la base de datos local
            try:
                local_search = await self.repository.get_all(
                    tipo_tarjeta=tipo_tarjeta,
                    client_id=client_id,
                    texto=documento,
                    page=1,
                    page_size=5
                )
                if local_search and local_search.get("data"):
                    local_match = local_search["data"][0]
                    return {
                        "status": "success",
                        "data": local_match
                    }
            except Exception as e_local:
                print(f"[TarjetasService] Fallback local search error: {e_local}")

            raise PipelineException(
                etapa="CONSULTA_API_JCC",
                mensaje="No se encontró ningún registro oficial para el documento especificado en la JCC.",
                cliente_id=client_id,
                status_code=status.HTTP_404_NOT_FOUND
            )

        return {
            "status": "success",
            "data": result["data"]
        }

    async def list_tarjetas(
        self, 
        tipo_tarjeta: Optional[str] = None, 
        client_id: Optional[int] = None, 
        page: int = 1, 
        page_size: int = 10,
        filtros: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_dir: str = "DESC"
    ) -> Dict[str, Any]:
        
        page_size = min(max(page_size, 1), 50000)

        try:
            filtros = filtros or {}
            return await self.repository.get_all(
                tipo_tarjeta=tipo_tarjeta,
                client_id=client_id,
                page=page,
                page_size=page_size,
                texto=filtros.get("texto"),
                filtro_documento=filtros.get("documento"),
                filtro_expediente=filtros.get("expediente"),
                filtro_resolucion=filtros.get("resolucion"),
                filtro_acta_jcc=filtros.get("acta_jcc"),
                filtro_no_tarjeta=filtros.get("no_tarjeta"),
                filtro_inscripcion=filtros.get("inscripcion"),
                filtro_correo=filtros.get("correo"),
                order_by=order_by,
                order_dir=order_dir,
                extra_filters=filtros
            )
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al listar tarjetas: {e}")
            tabla_target = "tn_tarjetavirtual_contadores" if tipo_tarjeta == "contadores" else "tn_tarjetavirtual_sociedades"
            raise PipelineException(
                etapa="TABLA_PRINCIPAL",
                mensaje="No fue posible cargar el listado de tarjetas desde la base de datos de la entidad.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                tabla_afectada=tabla_target,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def get_tarjeta(self, tarjeta_id: int, tipo_tarjeta: Optional[str] = None, client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            tarjeta = await self.repository.get_by_id(tarjeta_id, tipo_tarjeta, client_id)
            if not tarjeta:
                raise PipelineException(
                    etapa="TABLA_PRINCIPAL",
                    mensaje="Tarjeta digital no encontrada en la base de datos del cliente.",
                    cliente_id=client_id,
                    status_code=status.HTTP_404_NOT_FOUND
                )
            return tarjeta
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al obtener tarjeta {tarjeta_id}: {e}")
            raise PipelineException(
                etapa="TABLA_PRINCIPAL",
                mensaje=f"No fue posible consultar la tarjeta solicitada (ID: {tarjeta_id}).",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def sanitizar_tarjeta_validador(self, tarjeta: Dict[str, Any], client_id: Optional[int] = None) -> Dict[str, Any]:
        if not tarjeta:
            return tarjeta

        is_sociedad = bool(tarjeta.get("tipo_tarjeta") == "sociedades" or tarjeta.get("nit") or tarjeta.get("razon_social"))
        tipo_str = "sociedades" if is_sociedad else "contadores"

        try:
            cfg = await self.get_validador_config(tipo_str, client_id)
        except Exception as e_cfg:
            print(f"[TarjetasService] Advertencia al obtener config validador para sanitización: {e_cfg}")
            cfg = None

        if not cfg:
            return tarjeta

        tarjeta_sanitizada = dict(tarjeta)

        def is_visible(canonical_key: str, legacy_key: Optional[str] = None) -> bool:
            v_can = cfg.get(canonical_key) if canonical_key in cfg else None
            v_leg = cfg.get(legacy_key) if (legacy_key and legacy_key in cfg) else None
            if v_can is not None and v_leg is not None:
                return bool(v_can or v_leg)
            if v_can is not None:
                return bool(v_can)
            if v_leg is not None:
                return bool(v_leg)
            return True

        if is_sociedad:
            if not is_visible("val_numero_registro", "val_matricula"):
                tarjeta_sanitizada["inscripcion"] = None
                tarjeta_sanitizada["no_tarjeta"] = None
                tarjeta_sanitizada["matricula"] = None
            if not is_visible("val_fecha_resolucion"):
                tarjeta_sanitizada["fecha_resolucion"] = None
            if not is_visible("val_expediente"):
                tarjeta_sanitizada["no_expd"] = None
                tarjeta_sanitizada["expediente"] = None
            if not is_visible("val_razon_social", "val_nombres"):
                tarjeta_sanitizada["razon_social"] = None
                tarjeta_sanitizada["nombre_completo"] = None
                tarjeta_sanitizada["solicitante"] = None
            if not is_visible("val_nit", "val_numero_identificacion"):
                tarjeta_sanitizada["nit"] = None
                tarjeta_sanitizada["no_documento"] = None
                tarjeta_sanitizada["documento"] = None
            if not is_visible("val_tipo_registro"):
                tarjeta_sanitizada["tipo_sociedad"] = None
                tarjeta_sanitizada["tipo_asociado"] = None
            if not is_visible("val_resolucion"):
                tarjeta_sanitizada["resolucion"] = None
            if not is_visible("val_estado"):
                tarjeta_sanitizada["estado_tarjeta"] = None
                tarjeta_sanitizada["estado"] = None
                tarjeta_sanitizada["estado_sociedad"] = None
            if not is_visible("val_codigo_tarjeta"):
                tarjeta_sanitizada["hash_sha256"] = None
            if not is_visible("val_foto"):
                tarjeta_sanitizada["foto"] = None
        else:
            if not is_visible("val_tarjeta_profesional", "val_matricula"):
                tarjeta_sanitizada["no_tarjeta"] = None
                tarjeta_sanitizada["matricula"] = None
                tarjeta_sanitizada["inscripcion"] = None
            if not is_visible("val_fecha_resolucion"):
                tarjeta_sanitizada["fecha_resolucion"] = None
            if not is_visible("val_resolucion"):
                tarjeta_sanitizada["resolucion"] = None
            if not is_visible("val_nombre", "val_nombres"):
                tarjeta_sanitizada["nombre_completo"] = None
                tarjeta_sanitizada["solicitante"] = None
                tarjeta_sanitizada["nombres"] = None
                tarjeta_sanitizada["primer_apellido"] = None
                tarjeta_sanitizada["segundo_apellido"] = None
            if not is_visible("val_cedula", "val_numero_identificacion"):
                tarjeta_sanitizada["no_documento"] = None
                tarjeta_sanitizada["documento"] = None
            if not is_visible("val_institucion"):
                tarjeta_sanitizada["universidad"] = None
            if not is_visible("val_expediente"):
                tarjeta_sanitizada["no_expd"] = None
                tarjeta_sanitizada["expediente"] = None
            if not is_visible("val_estado"):
                tarjeta_sanitizada["estado_tarjeta"] = None
                tarjeta_sanitizada["estado"] = None
                tarjeta_sanitizada["estado_contador"] = None
            if not is_visible("val_codigo_tarjeta"):
                tarjeta_sanitizada["hash_sha256"] = None
            if not is_visible("val_foto"):
                tarjeta_sanitizada["foto"] = None

        return tarjeta_sanitizada

    async def get_tarjeta_by_hash(
        self,
        hash_sha256: str,
        tipo_tarjeta: Optional[str] = None,
        client_id: Optional[int] = None,
        sanitizar: bool = False,
        ip: Optional[str] = None,
        auto_log: bool = False
    ) -> Dict[str, Any]:
        try:
            tarjeta = await self.repository.get_by_verification_token(hash_sha256, tipo_tarjeta, client_id)
            if not tarjeta:
                raise PipelineException(
                    etapa="TABLA_PRINCIPAL",
                    mensaje="Tarjeta digital no encontrada con el hash suministrado.",
                    cliente_id=client_id,
                    status_code=status.HTTP_404_NOT_FOUND
                )
            if auto_log:
                try:
                    doc = str(tarjeta.get("no_documento") or tarjeta.get("nit") or "")
                    if doc:
                        import asyncio
                        asyncio.create_task(
                            self.repository.registrar_lectura(
                                documento_consultado=doc,
                                documento_consultor=None,
                                origen="Navegador web",
                                ip=ip,
                                client_id=client_id
                            )
                        )
                except Exception as e_log:
                    print(f"[TarjetasService] Advertencia auto-registro lectura web: {e_log}")

            if sanitizar:
                tarjeta = await self.sanitizar_tarjeta_validador(tarjeta, client_id)
            return tarjeta
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al obtener tarjeta por hash {hash_sha256}: {e}")
            raise PipelineException(
                etapa="TABLA_PRINCIPAL",
                mensaje="No fue posible consultar la tarjeta solicitada con el hash indicado.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def generar_pdf_tarjeta(
        self,
        tarjeta_id: int,
        tipo_tarjeta: Optional[str] = None,
        client_id: Optional[int] = None
        , base_url: Optional[str] = None
    ) -> Tuple[bytes, str]:
        tarjeta = await self.get_tarjeta(tarjeta_id, tipo_tarjeta, client_id)
        is_sociedad = bool(tarjeta.get("nit") or (tipo_tarjeta and tipo_tarjeta.lower() in ["sociedades", "sociedad"]))
        tipo_str = "sociedades" if is_sociedad else "contadores"

        try:
            branding = await self.get_branding_public(tipo=tipo_str, client_id=client_id)
        except Exception as e_br:
            print(f"[TarjetasService] Advertencia obteniendo branding para PDF: {e_br}")
            branding = None

        datos_combinados = dict(tarjeta)
        datos_combinados["tipo_tarjeta"] = tipo_str
        if base_url:
            datos_combinados["base_url"] = base_url
        if branding:
            b_data = branding.get("data") if (isinstance(branding, dict) and "data" in branding) else branding
            for k in ["patron", "patron_impresion", "logo", "logo_impresion", "color_fondo", "color_letra", "color_letra_impresion", "nombre_director", "cargo_director", "firma_director"]:
                if b_data.get(k) and not datos_combinados.get(k):
                    datos_combinados[k] = b_data[k]

        # Respetar la versión de firma institucional con la que se emitió la tarjeta
        try:
            v_firma = tarjeta.get("version_firma")
            if v_firma:
                inst_ver = await self.repository.get_institucional_by_version(int(v_firma), client_id)
                if inst_ver:
                    if inst_ver.get("nombre_director"):
                        datos_combinados["nombre_director"] = inst_ver["nombre_director"]
                    if inst_ver.get("cargo_director"):
                        datos_combinados["cargo_director"] = inst_ver["cargo_director"]
                    if inst_ver.get("firma_director"):
                        datos_combinados["firma_director"] = inst_ver["firma_director"]
        except Exception as e_vf:
            print(f"[TarjetasService] Advertencia cargando firma por version_firma en generar_pdf_tarjeta: {e_vf}")

        from app.services.pdf_generator_service import PdfGeneratorService
        pdf_bytes = PdfGeneratorService.generar_pdf_tarjeta(datos_combinados)

        prefijo = "sociedad" if is_sociedad else "contador"
        id_val = tarjeta.get("nit") or tarjeta.get("inscripcion") if is_sociedad else tarjeta.get("no_tarjeta") or tarjeta.get("no_documento") or tarjeta_id
        clean_id = "".join(c for c in str(id_val) if c.isalnum() or c in ("-", "_"))
        filename = f"tarjeta_{prefijo}_{clean_id}.pdf"
        return pdf_bytes, filename

    async def generar_pdf_tarjeta_by_hash(
        self,
        hash_sha256: str,
        tipo_tarjeta: Optional[str] = None,
        client_id: Optional[int] = None
        , base_url: Optional[str] = None
    ) -> Tuple[bytes, str]:
        tarjeta = await self.get_tarjeta_by_hash(hash_sha256, tipo_tarjeta, client_id, sanitizar=False)
        is_sociedad = bool(tarjeta.get("nit") or (tipo_tarjeta and tipo_tarjeta.lower() in ["sociedades", "sociedad"]))
        tipo_str = "sociedades" if is_sociedad else "contadores"

        try:
            branding = await self.get_branding_public(tipo=tipo_str, client_id=client_id)
        except Exception as e_br:
            print(f"[TarjetasService] Advertencia obteniendo branding para PDF: {e_br}")
            branding = None

        datos_combinados = dict(tarjeta)
        datos_combinados["tipo_tarjeta"] = tipo_str
        if base_url:
            datos_combinados["base_url"] = base_url
        if branding:
            b_data = branding.get("data") if (isinstance(branding, dict) and "data" in branding) else branding
            for k in ["patron", "patron_impresion", "logo", "logo_impresion", "color_fondo", "color_letra", "color_letra_impresion", "nombre_director", "cargo_director", "firma_director"]:
                if b_data.get(k) and not datos_combinados.get(k):
                    datos_combinados[k] = b_data[k]

        # Respetar la versión de firma institucional con la que se emitió la tarjeta
        try:
            v_firma = tarjeta.get("version_firma")
            if v_firma:
                inst_ver = await self.repository.get_institucional_by_version(int(v_firma), client_id)
                if inst_ver:
                    if inst_ver.get("nombre_director"):
                        datos_combinados["nombre_director"] = inst_ver["nombre_director"]
                    if inst_ver.get("cargo_director"):
                        datos_combinados["cargo_director"] = inst_ver["cargo_director"]
                    if inst_ver.get("firma_director"):
                        datos_combinados["firma_director"] = inst_ver["firma_director"]
        except Exception as e_vf:
            print(f"[TarjetasService] Advertencia cargando firma por version_firma en generar_pdf_tarjeta: {e_vf}")

        from app.services.pdf_generator_service import PdfGeneratorService
        pdf_bytes = PdfGeneratorService.generar_pdf_tarjeta(datos_combinados)

        prefijo = "sociedad" if is_sociedad else "contador"
        id_val = tarjeta.get("nit") or tarjeta.get("inscripcion") if is_sociedad else tarjeta.get("no_tarjeta") or tarjeta.get("no_documento") or "cert"
        clean_id = "".join(c for c in str(id_val) if c.isalnum() or c in ("-", "_"))
        filename = f"tarjeta_{prefijo}_{clean_id}.pdf"
        return pdf_bytes, filename

    async def generar_constancia_activacion(
        self,
        tarjeta_id: int,
        tipo_tarjeta: Optional[str] = None,
        client_id: Optional[int] = None
    ) -> Tuple[bytes, str]:
        tarjeta = await self.get_tarjeta(tarjeta_id, tipo_tarjeta, client_id)
        if not tarjeta:
            raise PipelineException(
                etapa="CONSTANCIA_ACTIVACION",
                mensaje="No se encontró la tarjeta consultada.",
                cliente_id=client_id or 20001,
                status_code=status.HTTP_404_NOT_FOUND
            )

        estado_actual = str(tarjeta.get("estado_tarjeta") or tarjeta.get("estado") or "").strip()
        if estado_actual.lower() not in ["activa", "activo"]:
            raise PipelineException(
                etapa="CONSTANCIA_ACTIVACION",
                mensaje=f"La tarjeta se encuentra en estado '{estado_actual}'. La constancia de activación solo está disponible para tarjetas en estado Activa.",
                cliente_id=client_id or 20001,
                status_code=status.HTTP_409_CONFLICT
            )

        is_sociedad = bool(tarjeta.get("nit") or (tipo_tarjeta and tipo_tarjeta.lower() in ["sociedades", "sociedad"]))
        tipo_str = "sociedades" if is_sociedad else "contadores"

        # Obtener o asignar consecutivo oficial (persiste en BD)
        consecutivo = await self.repository.obtener_o_asignar_consecutivo_activacion(
            tarjeta_id=tarjeta_id,
            tipo_tarjeta=tipo_str,
            client_id=client_id
        )

        datos = dict(tarjeta)
        datos["tipo_tarjeta"] = tipo_str
        datos["consecutivo_soporte_activacion"] = consecutivo

        plantilla_activa = await self.repository.obtener_plantilla_activacion_activa(tipo_str, client_id=client_id)
        docx_bytes = plantilla_activa.get("contenido_docx") if plantilla_activa else None

        from app.services.constancia_activacion_pdf_service import ConstanciaActivacionPdfService
        pdf_service = ConstanciaActivacionPdfService()
        pdf_bytes = pdf_service.generar_pdf_desde_docx(docx_bytes, datos)

        prefijo = "sociedad" if is_sociedad else "contador"
        id_val = tarjeta.get("nit") if is_sociedad else (tarjeta.get("no_tarjeta") or tarjeta.get("no_documento") or tarjeta_id)
        clean_id = "".join(c for c in str(id_val) if c.isalnum() or c in ("-", "_"))
        filename = f"constancia_activacion_{prefijo}_{clean_id}.pdf"
        return pdf_bytes, filename


    async def create_tarjeta_contador(
        self,
        documento: str,
        tipo: str,
        client_id: Optional[int] = None,
        tipo_tarjeta: str = "contadores",
    ) -> Dict[str, Any]:
        try:
            consulta = await self.jcc_client.consultar_registro(
                documento=documento,
                tipo_tarjeta=tipo_tarjeta,
                tipo=tipo,
                client_id=client_id,
            )
        except Exception as e:
            print(f"[TarjetasService] Error llamando API JCC en create_tarjeta_contador: {e}")
            raise PipelineException(
                etapa="CONSULTA_API_JCC",
                mensaje="Error al consultar la API de la JCC para la emisión de la tarjeta.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        item = consulta.get("data")
        if not item or not consulta.get("encontrado"):
            return {
                "status": "no_data",
                "message": "No se encontraron registros disponibles en el JCC o los datos no cumplen los criterios."
            }

        tipo_asociado_key = tipo if tipo else "primeraVez"
        estado_tarjeta = EstadoTarjetaEnum.EMITIDA.value
        no_documento = item.get("no_documento")

        try:
            existe_contador = await self.repository.exists_accountant(no_documento, client_id)
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error verificando existencia contador: {e}")
            raise PipelineException(
                etapa="CHECK_EXISTENCIA",
                mensaje="Error al verificar en la base de datos si el contador ya se encuentra registrado.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                tabla_afectada="tn_tarjetavirtual_contadores",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if existe_contador:
            raise PipelineException(
                etapa="CHECK_EXISTENCIA",
                mensaje=f"El contador con número documento {no_documento} ya está registrado previamente.",
                cliente_id=client_id,
                tabla_afectada="tn_tarjetavirtual_contadores",
                status_code=status.HTTP_409_CONFLICT
            )

        try:
            contador_data = {
                "no_tarjeta": item.get("no_tarjeta", ""),
                "nombres": item.get("nombres", ""),
                "primer_apellido": item.get("primer_apellido", ""),
                "segundo_apellido": item.get("segundo_apellido", ""),
                "no_expd": item.get("no_expd", 0),
                "tipo_documento": item.get("tipo_documento", "CC"),
                "no_documento": item.get("no_documento", documento),
                "universidad": item.get("universidad", ""),
                "estado_contador": item.get("estado_contador", "ACTIVO"),
                "resolucion": item.get("resolucion", ""),
                "fecha_estado": item.get("fecha_estado"),
                "fecha_radicacion": item.get("fecha_radicacion"),
                "fecha_resolucion": item.get("fecha_resolucion"),
                "acta_jcc": item.get("acta_jcc"),
                "fecha_grado": item.get("fecha_grado"),
                "seccional": item.get("seccional", ""),
                "correo": item.get("correo", ""),
                "tipo_asociado": tipo_asociado_key,
                "estado": estado_tarjeta,
                "foto": item.get("pdf")
            }
            
            new_id = await self.repository.create_contadores(contador_data, client_id)
            return {
                "status": "success",
                "id": new_id,
                "message": "Tarjeta digital de contador emitida exitosamente."
            }
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error insertando contador en DB: {e}")
            raise PipelineException(
                etapa="TABLA_PRINCIPAL",
                mensaje="Error en la base de datos al registrar la tarjeta en la tabla tn_tarjetavirtual_contadores.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                tabla_afectada="tn_tarjetavirtual_contadores",
                contexto="create_tarjeta_contador -> repository.create_contadores",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    async def create_tarjeta_sociedad(
        self,
        documento: str,
        tipo: str,
        client_id: Optional[int] = None,
        tipo_tarjeta: str = "sociedades",
    ) -> Dict[str, Any]:
        try:
            consulta = await self.jcc_client.consultar_registro(
                documento=documento,
                tipo_tarjeta=tipo_tarjeta,
                tipo=tipo,
                client_id=client_id,
            )
        except Exception as e:
            print(f"[TarjetasService] Error llamando API JCC en create_tarjeta_sociedad: {e}")
            raise PipelineException(
                etapa="CONSULTA_API_JCC",
                mensaje="Error al consultar la API de la JCC para la emisión de la tarjeta de sociedad.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        item = consulta.get("data")
        if not item or not consulta.get("encontrado"):
            return {
                "status": "no_data",
                "message": "No se encontraron registros disponibles en el JCC o los datos no cumplen los criterios."
            }
        
        tipo_asociado_key = tipo if tipo else "primeraVez"
        estado_tarjeta = EstadoTarjetaEnum.EMITIDA.value
        nit = item.get("nit") or documento

        expd = item.get("no_expd") or item.get("NO_EXPD")

        try:
            existe_sociedad = await self.repository.exists_society(nit, client_id, no_expd=expd)
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error verificando existencia sociedad: {e}")
            raise PipelineException(
                etapa="CHECK_EXISTENCIA",
                mensaje="Error al verificar en la base de datos si la sociedad ya se encuentra registrada.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                tabla_afectada="tn_tarjetavirtual_sociedades",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if existe_sociedad:
            raise PipelineException(
                etapa="CHECK_EXISTENCIA",
                mensaje=f"La sociedad con NIT {nit} ya está registrada previamente.",
                cliente_id=client_id,
                tabla_afectada="tn_tarjetavirtual_sociedades",
                status_code=status.HTTP_409_CONFLICT
            )

        try:
            sociedad_data = {
                "no_expd": item.get("no_expd", 0),
                "razon_social": item.get("razon_social", ""),
                "nit": nit,
                "tipo_sociedad": item.get("tipo_sociedad", "SOCIEDAD DE CONTADORES"),
                "inscripcion": item.get("inscripcion"),
                "fecha_radicacion": item.get("fecha_radicacion"),
                "estado_sociedad": item.get("estado_sociedad", "ACTIVO"),
                "resolucion": item.get("resolucion", ""),
                "fecha_resolucion": item.get("fecha_resolucion"),
                "acta_jcc": str(item.get("acta_jcc")) if item.get("acta_jcc") is not None else None,
                "estado_solicitud": item.get("estado_solicitud"),
                "tipo_solicitud": item.get("tipo_solicitud"),
                "correo": item.get("correo", ""),
                "representante_legal": item.get("representante_legal", ""),
                "tipo_asociado": tipo_asociado_key,
                "estado": estado_tarjeta,
                "foto": item.get("pdf")
            }
            
            new_id = await self.repository.create_sociedades(sociedad_data, client_id)
            return {
                "status": "success",
                "id": new_id,
                "message": "Tarjeta digital de sociedad emitida exitosamente."
            }
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error insertando sociedad en DB: {e}")
            raise PipelineException(
                etapa="TABLA_PRINCIPAL",
                mensaje="Error en la base de datos al registrar la tarjeta en la tabla tn_tarjetavirtual_sociedades.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                tabla_afectada="tn_tarjetavirtual_sociedades",
                contexto="create_tarjeta_sociedad -> repository.create_sociedades",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def get_historial(self, tarjeta_id: int, client_id: Optional[int] = None, tipo: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            return await self.repository.get_historial(tarjeta_id, client_id, tipo)
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al obtener historial de tarjeta {tarjeta_id}: {e}")
            raise PipelineException(
                etapa="TABLA_INTERMEDIA",
                mensaje=f"No fue posible consultar el historial para la tarjeta ID {tarjeta_id}.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                tabla_afectada="tn_tarjetavirtual_historial",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def get_validador_config(self, tipo_tarjeta: str = "contadores", client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            return await self.repository.get_validador_config(tipo_tarjeta, client_id)
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al cargar configuración de validador: {e}")
            raise PipelineException(
                etapa="CONFIGURACION_VALIDADOR",
                mensaje="No fue posible cargar la configuración del validador QR.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def save_validador_config(self, data: ValidadorConfigSchema, tipo_tarjeta: str = "contadores", client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            config_dict = data.dict()
            # Validar que al menos un campo sea True
            if not any(bool(v) for k, v in config_dict.items() if k.startswith("val_")):
                raise PipelineException(
                    etapa="CONFIGURACION_VALIDADOR",
                    mensaje="Debe seleccionar al menos un campo visible para guardar la configuración del validador público.",
                    cliente_id=client_id,
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            await self.repository.save_validador_config(config_dict, tipo_tarjeta, client_id)
            return {
                "status": "success",
                "message": "Configuración del validador guardada exitosamente."
            }
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al guardar configuración de validador: {e}")
            raise PipelineException(
                etapa="CONFIGURACION_VALIDADOR",
                mensaje="No fue posible guardar la configuración del validador QR.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def get_columns_config(self, tipo_tarjeta: str = "contadores", client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            cols = await self.repository.get_columns_config(tipo_tarjeta, client_id)
            return {
                "status": "success",
                "data": cols
            }
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al cargar configuración de columnas: {e}")
            raise PipelineException(
                etapa="CONFIGURACION_COLUMNAS",
                mensaje="No fue posible cargar la configuración de columnas.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def create_or_update_branding_credentials(self, data: BrandingCredentialsCreateSchema, client_id: Optional[int] = None,) -> Dict[str, Any]:
        try:
            cid = client_id or data.idCliente or 20001
            existing = await self.repository.get_by_cliente_and_tipo(
                cid, data.tipo_id, client_id=cid
            )

            logo_val = data.logo or (existing.get("logo") if existing else None)
            patron_val = data.patron or (existing.get("patron") if existing else None)
            logo_impresion_val = data.logo_impresion or (existing.get("logo_impresion") if existing else None)
            patron_impresion_val = data.patron_impresion or (existing.get("patron_impresion") if existing else None)
            color_letra_impresion_val = data.color_letra_impresion or (existing.get("color_letra_impresion") if existing else "#0f172a")
            nombre_director_val = data.nombre_director if data.nombre_director is not None else (existing.get("nombre_director") if existing else None)
            firma_director_val = data.firma_director if data.firma_director is not None else (existing.get("firma_director") if existing else None)

            branding_data = {
                "version_actual": data.version_actual,
                "version_publicada": data.version_publicada,
                "logo": logo_val,
                "patron": patron_val,
                "logo_impresion": logo_impresion_val,
                "patron_impresion": patron_impresion_val,
                "color_fondo": data.color_fondo,
                "color_letra": data.color_letra,
                "color_letra_impresion": color_letra_impresion_val,
                "nombre_director": nombre_director_val,
                "firma_director": firma_director_val,
                "observacion": data.observacion.strip() if data.observacion else None,
                "usuario_creacion_id": data.usuario_creacion_id,
                "tipo_id": data.tipo_id,
            }
            new_id = await self.repository.create_branding_credentials(branding_data, cid)
            return {
                "id": new_id,
                "status": "success",
                "message": "Branding credencial creada exitosamente.",
            }
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error en upsert branding: {e}")
            raise PipelineException(
                etapa="BRANDING_CREDENTIALS",
                mensaje="No fue posible guardar la configuración de branding credenciales.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def update_branding_credentials_change_version(self, branding_credential_id: int, data: BrandingCredentialsUpdateSchema, client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            observacion_limpia = (data.observacion or "").strip()
            if not observacion_limpia:
                raise PipelineException(
                    etapa="BRANDING_CREDENTIALS",
                    mensaje="La observación o justificación es obligatoria para publicar una versión de branding.",
                    cliente_id=client_id,
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            existing = await self.repository.get_by_id_branding_credencials(branding_credential_id, client_id)
            if not existing:
                raise PipelineException(
                    etapa="BRANDING_CREDENTIALS",
                    mensaje=f"Branding credencial con ID {branding_credential_id} no encontrado.",
                    cliente_id=client_id,
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            payload = data.dict(exclude_none=True)
            payload["observacion"] = observacion_limpia
            await self.repository.update_branding_credentials_change_version(
                branding_credential_id,
                payload, 
                client_id
            )
                        
            return {
                "id": branding_credential_id,
                "status": "success",
                "message": "Versión publicada actualizada exitosamente."
            }
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al actualizar versión publicada {branding_credential_id}: {e}")
            raise PipelineException(
                etapa="BRANDING_CREDENTIALS",
                mensaje="No fue posible actualizar la versión publicada del branding.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def get_branding_credentials(self, branding_credential_id: int, client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            result = await self.repository.get_by_id_branding_credencials(branding_credential_id, client_id)
            if not result:
                raise PipelineException(
                    etapa="BRANDING_CREDENTIALS",
                    mensaje=f"Branding credencial con ID {branding_credential_id} no encontrado.",
                    cliente_id=client_id,
                    status_code=status.HTTP_404_NOT_FOUND
                )

            # Inyectar la configuración institucional vigente (Nombre, Cargo y Firma del Director General)
            try:
                institucional = await self.repository.get_institucional_published(client_id)
                if institucional:
                    result["nombre_director"] = institucional.get("nombre_director") or result.get("nombre_director") or "SANDRA MILENA BARRIOS PULIDO"
                    result["cargo_director"] = institucional.get("cargo_director") or "DIRECTOR GENERAL"
                    result["firma_director"] = institucional.get("firma_director") or result.get("firma_director")
            except Exception as e_inst:
                print(f"[TarjetasService] Advertencia al combinar datos institucionales en get_branding_credentials: {e_inst}")

            return result
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al obtener Branding credencial {branding_credential_id}: {e}")
            raise PipelineException(
                etapa="BRANDING_CREDENTIALS",
                mensaje="No fue posible obtener la información del branding.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def get_branding_credentials_publish(self, branding_credential_id: int, client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            result = await self.repository.get_branding_credentials_publish(branding_credential_id, client_id)
            if not result:
                raise PipelineException(
                    etapa="BRANDING_CREDENTIALS",
                    mensaje=f"Branding credencial con ID {branding_credential_id} no encontrado.",
                    cliente_id=client_id,
                    status_code=status.HTTP_404_NOT_FOUND
                )

            # Inyectar la configuración institucional vigente (Nombre, Cargo y Firma del Director General)
            nombre_director = result.get("nombre_director") or "SANDRA MILENA BARRIOS PULIDO"
            cargo_director = "DIRECTOR GENERAL"
            firma_director = result.get("firma_director")

            try:
                institucional_resp = await self.get_institucional_published(client_id)
                institucional_data = institucional_resp.get("data") if isinstance(institucional_resp, dict) else None
                if institucional_data:
                    nombre_director = institucional_data.get("nombre_director") or nombre_director
                    cargo_director = institucional_data.get("cargo_director") or cargo_director
                    firma_director = institucional_data.get("firma_director") or firma_director
            except Exception as e_inst:
                print(f"[TarjetasService] Advertencia al combinar datos institucionales en get_branding_credentials_publish: {e_inst}")

            return {
                "tipo_id": result.get("tipo_id"),
                "version": result.get("version"),
                "color_fondo": result.get("color_fondo"),
                "color_letra": result.get("color_letra"),
                "color_letra_impresion": result.get("color_letra_impresion") or "#0f172a",
                "logo": result.get("logo"),
                "patron": result.get("patron"),
                "logo_impresion": result.get("logo_impresion"),
                "patron_impresion": result.get("patron_impresion"),
                "nombre_director": nombre_director,
                "cargo_director": cargo_director,
                "firma_director": firma_director,
                "observacion": result.get("observacion")
            }
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al obtener Branding credencial publicada {branding_credential_id}: {e}")
            raise PipelineException(
                etapa="BRANDING_CREDENTIALS",
                mensaje="No fue posible obtener la información del branding publicado.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def list_history_branding_credentials(
        self,
        branding_credential_id: int,
        client_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        try:
            page_size = min(max(page_size, 1), 50000)
            page = max(page, 1)

            return await self.repository.list_history_branding_credentials(
                branding_credential_id, client_id, page, page_size
            )
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al obtener el historial de versiones de Branding {branding_credential_id}: {e}")
            raise PipelineException(
                etapa="BRANDING_CREDENTIALS",
                mensaje="No fue posible obtener el historial de versiones del branding.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def get_branding_public(self, tipo: str, client_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Retorna la configuración de branding activa y publicada para la aplicación móvil o clientes externos,
        incluyendo logos, patrones, colores institucionales, nombre del director y firma institucional.
        """
        tipo_str = str(tipo).strip().lower()
        if tipo_str in ["1", "contador", "contadores"]:
            tipo_id = 1
            tipo_nombre = "contadores"
        elif tipo_str in ["2", "sociedad", "sociedades"]:
            tipo_id = 2
            tipo_nombre = "sociedades"
        else:
            tipo_id = 1
            tipo_nombre = "contadores"

        try:
            result = await self.repository.get_branding_credentials_publish(tipo_id, client_id)
            if not result:
                result = await self.repository.get_by_id_branding_credencials(tipo_id, client_id)

            if not result:
                result = {
                    "tipo_id": tipo_id,
                    "version": 1,
                    "publicado": 1,
                    "color_fondo": "#14275f" if tipo_id == 1 else "#134567",
                    "color_letra": "#ffffff",
                    "nombre_director": "SANDRA MILENA BARRIOS PULIDO",
                    "cargo_director": "DIRECTOR GENERAL",
                    "firma_director": None,
                    "logo": None,
                    "patron": None
                }

            # Consultar configuración institucional vigente (Firma y Nombre del Director)
            institucional = None
            try:
                institucional = await self.repository.get_institucional_published(client_id)
            except Exception as e_inst:
                print(f"[TarjetasService] Advertencia: No se pudo obtener config institucional: {e_inst}")

            nombre_director = (
                (institucional.get("nombre_director") if institucional else None)
                or result.get("nombre_director")
                or "SANDRA MILENA BARRIOS PULIDO"
            )
            cargo_director = (
                (institucional.get("cargo_director") if institucional else None)
                or "DIRECTOR GENERAL"
            )
            firma_director = (
                (institucional.get("firma_director") if institucional else None)
                or result.get("firma_director")
            )

            return {
                "status": "success",
                "data": {
                    "tipo_id": tipo_id,
                    "tipo_tarjeta": tipo_nombre,
                    "version": result.get("version") or result.get("version_publicada") or 1,
                    "publicado": bool(result.get("publicado", 1)),
                    "color_fondo": result.get("color_fondo"),
                    "color_letra": result.get("color_letra"),
                    "color_letra_impresion": result.get("color_letra_impresion") or "#0f172a",
                    "nombre_director": nombre_director,
                    "cargo_director": cargo_director,
                    "firma_director": firma_director,
                    "logo": result.get("logo"),
                    "patron": result.get("patron"),
                    "logo_impresion": result.get("logo_impresion"),
                    "patron_impresion": result.get("patron_impresion"),
                    "observacion": result.get("observacion"),
                    "created_at": result.get("created_at_formatted")
                }
            }
        except Exception as e:
            print(f"[TarjetasService] Error al obtener branding público {tipo}: {e}")
            raise PipelineException(
                etapa="BRANDING_CREDENTIALS",
                mensaje="No fue posible obtener la información de branding solicitada.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # =========================================================================
    # BRANDING INSTITUCIONAL (GLOBAL)
    # =========================================================================
    async def get_institucional_published(self, client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            result = await self.repository.get_institucional_published(client_id)
            if not result:
                clean_data = {
                    "nombre_director": "SANDRA MILENA BARRIOS PULIDO",
                    "cargo_director": "DIRECTOR GENERAL",
                    "firma_director": None,
                    "version": 1,
                    "observacion": None
                }
            else:
                clean_data = {
                    "nombre_director": result.get("nombre_director") or "SANDRA MILENA BARRIOS PULIDO",
                    "cargo_director": result.get("cargo_director") or "DIRECTOR GENERAL",
                    "firma_director": result.get("firma_director"),
                    "version": result.get("version") or 1,
                    "observacion": result.get("observacion")
                }
            return {
                "status": "success",
                "data": clean_data
            }
        except Exception as e:
            print(f"[TarjetasService] Error al consultar configuración institucional: {e}")
            raise PipelineException(
                etapa="BRANDING_INSTITUCIONAL",
                mensaje="No fue posible obtener la información institucional publicada.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def get_institucional_by_version(self, version: int, client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            result = await self.repository.get_institucional_by_version(version, client_id)
            if not result:
                raise PipelineException(
                    etapa="BRANDING_INSTITUCIONAL",
                    mensaje=f"No se encontró la versión {version} de la firma institucional.",
                    cliente_id=client_id,
                    status_code=status.HTTP_404_NOT_FOUND
                )
            return {
                "status": "success",
                "data": {
                    "version": int(result.get("version") or version),
                    "nombre_director": result.get("nombre_director") or "SANDRA MILENA BARRIOS PULIDO",
                    "cargo_director": result.get("cargo_director") or "DIRECTOR GENERAL",
                    "firma_director": result.get("firma_director")
                }
            }
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al consultar firma institucional versión {version}: {e}")
            raise PipelineException(
                etapa="BRANDING_INSTITUCIONAL",
                mensaje=f"No fue posible obtener la firma institucional para la versión {version}.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def actualizar_datos_personales(
        self,
        tarjeta_id: int,
        tipo_tarjeta: str = "contadores",
        usuario: str = "admin",
        ip: Optional[str] = None,
        client_id: Optional[int] = None
    ) -> Dict[str, Any]:
        from app.repositories.tarjetas_repository import extraer_partes_nit

        tipo_norm = "sociedades" if (tipo_tarjeta and "sociedad" in str(tipo_tarjeta).lower()) else "contadores"
        tarjeta = await self.repository.get_by_id(tarjeta_id, tipo_norm, client_id)
        if not tarjeta:
            raise PipelineException(
                etapa="REGISTRO_NO_ENCONTRADO",
                mensaje="No se encontró el registro de la tarjeta seleccionada en la base de datos.",
                cliente_id=client_id,
                status_code=status.HTTP_404_NOT_FOUND
            )

        doc_registro = str(tarjeta.get("nit") if tipo_norm == "sociedades" else tarjeta.get("no_documento") or "").strip()
        if not doc_registro:
            raise PipelineException(
                etapa="DOCUMENTO_INVALIDO",
                mensaje="El registro seleccionado no cuenta con un número de identificación válido para consultar MYJCC.",
                cliente_id=client_id,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            consulta = await self.jcc_client.consultar_all(
                documento=doc_registro,
                tipo_tarjeta=tipo_norm,
                client_id=client_id
            )
        except Exception as e_conn:
            raise PipelineException(
                etapa="SERVICIO_MYJCC_NO_DISPONIBLE",
                mensaje="No fue posible consultar el servicio MYJCC en este momento. La información del registro se conserva sin cambios.",
                detalle_tecnico=str(e_conn),
                cliente_id=client_id,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        if not consulta or consulta.get("es_error_conexion"):
            raise PipelineException(
                etapa="SERVICIO_MYJCC_NO_DISPONIBLE",
                mensaje="No fue posible consultar el servicio MYJCC en este momento. La información del registro se conserva sin cambios.",
                detalle_tecnico=(consulta.get("error") if consulta else "Fallo de comunicación con MYJCC"),
                cliente_id=client_id,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        item_jcc = consulta.get("data")
        if not consulta.get("encontrado") or not item_jcc:
            tipo_lbl = "Sociedad" if tipo_norm == "sociedades" else "Contador público"
            doc_lbl = "NIT" if tipo_norm == "sociedades" else "cédula de ciudadanía"
            raise PipelineException(
                etapa="SIN_INFORMACION_MYJCC",
                mensaje=f"No se encontró información en MYJCC para el {tipo_lbl} con {doc_lbl} {doc_registro}. No se realizó ningún cambio en los datos del registro.",
                cliente_id=client_id,
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Validar concordancia del documento retornado por MYJCC (Escenario 9 - Criterio 3)
        if tipo_norm == "sociedades":
            raw_ret = item_jcc.get("raw_nit")
            if raw_ret is not None and str(raw_ret).strip() != "":
                _, raiz_reg, full_reg = extraer_partes_nit(doc_registro)
                _, raiz_ret, full_ret = extraer_partes_nit(raw_ret)
                if raiz_reg and raiz_ret and raiz_reg != raiz_ret and full_reg != full_ret:
                    raise PipelineException(
                        etapa="DOCUMENTO_INCONSISTENTE_MYJCC",
                        mensaje="La información retornada por MYJCC no corresponde al número de NIT del registro seleccionado.",
                        cliente_id=client_id,
                        status_code=status.HTTP_409_CONFLICT
                    )
        else:
            raw_ret = item_jcc.get("raw_no_documento")
            if raw_ret is not None and str(raw_ret).strip() != "":
                clean_reg = "".join(c for c in doc_registro if c.isalnum())
                clean_ret = "".join(c for c in str(raw_ret) if c.isalnum())
                if clean_reg and clean_ret and clean_reg != clean_ret:
                    raise PipelineException(
                        etapa="DOCUMENTO_INCONSISTENTE_MYJCC",
                        mensaje="La información retornada por MYJCC no corresponde a la cédula de ciudadanía del registro seleccionado.",
                        cliente_id=client_id,
                        status_code=status.HTTP_409_CONFLICT
                    )

        res_upd = await self.repository.actualizar_datos_personales_tarjeta(
            tarjeta_id=tarjeta_id,
            tipo_tarjeta=tipo_norm,
            data_jcc=item_jcc,
            usuario=usuario,
            ip=ip,
            client_id=client_id
        )

        return {
            "status": "success",
            "message": "Datos personales actualizados correctamente con la información de MYJCC.",
            "data": res_upd["tarjeta"],
            "auditoria": res_upd["auditoria"]
        }

    async def create_institucional_version(
        self,
        data: InstitucionalConfigCreateSchema,
        client_id: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            payload = data.dict()
            new_id = await self.repository.create_institucional_version(payload, client_id)
            return {
                "status": "success",
                "message": "Nueva versión institucional guardada exitosamente.",
                "id": new_id
            }
        except Exception as e:
            print(f"[TarjetasService] Error al crear versión institucional: {e}")
            raise PipelineException(
                etapa="BRANDING_INSTITUCIONAL",
                mensaje="No fue posible guardar la nueva versión institucional.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def list_institucional_history(
        self,
        client_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        try:
            result = await self.repository.list_institucional_history(
                client_id=client_id,
                page=page,
                page_size=page_size
            )
            return {
                "status": "success",
                **result
            }
        except Exception as e:
            print(f"[TarjetasService] Error al listar historial institucional: {e}")
            raise PipelineException(
                etapa="BRANDING_INSTITUCIONAL",
                mensaje="No fue posible obtener el historial de versiones institucionales.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def publish_institucional_version(
        self,
        version_id: int,
        client_id: Optional[int] = None,
        observacion: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            observacion_limpia = (observacion or "").strip()
            if not observacion_limpia:
                raise PipelineException(
                    etapa="BRANDING_INSTITUCIONAL",
                    mensaje="La observación o justificación es obligatoria para publicar la configuración institucional.",
                    cliente_id=client_id,
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            await self.repository.publish_institucional_version(version_id, client_id, observacion=observacion_limpia)
            return {
                "status": "success",
                "message": f"Versión institucional {version_id} publicada exitosamente."
            }
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al publicar versión institucional: {e}")
            raise PipelineException(
                etapa="BRANDING_INSTITUCIONAL",
                mensaje="No fue posible publicar la versión institucional solicitada.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def create_auditoria_api(self, data: AuditoriaApiCreateSchema, client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            new_id = await self.repository.create_auditoria_api(data.dict(), client_id)
            return {
                "id": new_id,
                "status": "success",
                "message": "Creacion de la auditoría API creada exitosamente."
            }
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al crear la auditoría API: {e}")
            raise PipelineException(
                etapa="REGISTRO_AUDITORIA",
                mensaje="No fue posible guardar el registro en la tabla de auditoría (jcc_auditoria_api).",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                tabla_afectada="jcc_auditoria_api",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def list_auditoria_api(
        self,
        client_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 10,
        fecha_desde: Optional[str] = None,
        fecha_hasta: Optional[str] = None,
        endpoint: Optional[str] = None,
        tipo: Optional[str] = None,
        texto: Optional[str] = None,
        cambiar_estado: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            page_size = min(max(page_size, 1), 50000)
            return await self.repository.get_all_auditoria_api(
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
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al listar la auditoría API: {e}")
            raise PipelineException(
                etapa="REGISTRO_AUDITORIA",
                mensaje="No fue posible cargar la lista de auditoría desde la tabla jcc_auditoria_api.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                tabla_afectada="jcc_auditoria_api",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    async def activar_tarjeta_movil(self, payload: ActivacionMovilRequestSchema) -> Dict[str, Any]:
        client_id = payload.client_id or 20001
        # 1. Obtener tarjeta por hash privado de activación
        tarjeta = await self.repository.get_by_hash(payload.token, client_id=client_id)
        if not tarjeta:
            # Validar si el usuario intentó activar usando el token público del PDF
            tarjeta_pub = await self.repository.get_by_verification_token(payload.token, client_id=client_id)
            if tarjeta_pub:
                raise PipelineException(
                    etapa="ACTIVACION_MOVIL",
                    mensaje="El código suministrado corresponde al token público de verificación del PDF y no puede utilizarse para activar la credencial móvil.",
                    cliente_id=client_id,
                    status_code=status.HTTP_403_FORBIDDEN
                )
            raise PipelineException(
                etapa="ACTIVACION_MOVIL",
                mensaje="No se encontró ninguna credencial registrada con el código o token suministrado.",
                cliente_id=client_id,
                status_code=status.HTTP_404_NOT_FOUND
            )

        estado_actual = str(tarjeta.get("estado_tarjeta") or tarjeta.get("estado") or "").strip()
        tipo_tarjeta = tarjeta.get("tipo_tarjeta") or ("sociedades" if tarjeta.get("nit") else "contadores")
        tarjeta_id = tarjeta["id"]

        # 2. Validar que la tarjeta no esté cancelada o inactiva
        if estado_actual.lower() in ["cancelada", "inactiva"]:
            raise PipelineException(
                etapa="ACTIVACION_MOVIL",
                mensaje=f"La credencial se encuentra en estado '{estado_actual}' y no puede ser activada en el dispositivo móvil.",
                cliente_id=client_id,
                status_code=status.HTTP_409_CONFLICT
            )

        ya_estaba_activa = estado_actual.lower() in ["activa", "activo"]

        # 3. Ejecutar activación en base de datos
        await self.repository.activar_tarjeta_movil(
            tarjeta_id=tarjeta_id,
            tipo_tarjeta=tipo_tarjeta,
            fcm_token=payload.fcm_token,
            device_id=payload.device_id,
            device_os=payload.device_os,
            device_modelo=payload.device_modelo,
            app_version=payload.app_version,
            client_id=client_id
        )

        # 4. Obtener branding publicado para la app móvil
        try:
            branding = await self.get_branding_public(tipo=tipo_tarjeta, client_id=client_id)
        except Exception as e_br:
            print(f"[TarjetasService] Advertencia obteniendo branding en activacion: {e_br}")
            branding = None

        # 5. Refrescar estado en el objeto retorno
        tarjeta["estado_tarjeta"] = "Activa"
        tarjeta["estado"] = "Activa"

        # 6. Si pasó de Emitida a Activa, asignar consecutivo, generar constancia PDF y enviar al correo del titular
        if not ya_estaba_activa:
            try:
                consecutivo = await self.repository.obtener_o_asignar_consecutivo_activacion(
                    tarjeta_id=tarjeta_id,
                    tipo_tarjeta=tipo_tarjeta,
                    client_id=client_id,
                )
                tarjeta["consecutivo_soporte_activacion"] = consecutivo
                pdf_bytes, filename = await self.generar_constancia_activacion(
                    tarjeta_id=tarjeta_id,
                    tipo_tarjeta=tipo_tarjeta,
                    client_id=client_id,
                )
                correo_titular = str(tarjeta.get("correo") or "").strip()
                nombre_titular = str(
                    tarjeta.get("razon_social")
                    or tarjeta.get("nombre_completo")
                    or " ".join(
                        str(tarjeta.get(k) or "").strip()
                        for k in ("nombres", "primer_apellido", "segundo_apellido")
                        if tarjeta.get(k)
                    )
                    or "Titular"
                ).strip()
                numero_soporte = f"ACT-{datetime.now().year}-{int(consecutivo):06d}" if consecutivo else ""
                if correo_titular and "@" in correo_titular:
                    from app.services.notificacion_activacion_service import despachar_correo_constancia_activacion
                    await despachar_correo_constancia_activacion(
                        correo=correo_titular,
                        nombre=nombre_titular,
                        pdf_bytes=pdf_bytes,
                        filename=filename,
                        numero_soporte=numero_soporte,
                    )
            except Exception as e_const:
                print(f"[TarjetasService] Advertencia al generar/enviar constancia de activación: {e_const}")

        return {
            "success": True,
            "mensaje": "Credencial ya se encontraba activa. Dispositivo móvil sincronizado." if ya_estaba_activa else "Credencial digital activada exitosamente en el dispositivo móvil.",
            "data": {
                "tarjeta": tarjeta,
                "branding": branding,
                "dispositivo": {
                    "device_id": payload.device_id,
                    "device_os": payload.device_os,
                    "fcm_token_registrado": bool(payload.fcm_token)
                }
            }
        }

    async def get_reportes_dashboard(
        self,
        fecha_desde: Optional[str] = None,
        fecha_hasta: Optional[str] = None,
        segmento: str = "all",
        tipo_reporte: str = "general",
        estado: Optional[str] = None,
        client_id: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            return await self.repository.get_reportes_dashboard(
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                segmento=segmento,
                tipo_reporte=tipo_reporte,
                estado=estado,
                client_id=client_id
            )
        except Exception as e:
            print(f"[TarjetasService] Error al obtener datos del reporte dashboard: {e}")
            raise PipelineException(
                etapa="REPORTES_DASHBOARD",
                mensaje="No fue posible obtener las métricas del reporte dashboard.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def registrar_lectura(
        self,
        payload: RegistroLecturaRequestSchema,
        ip: Optional[str] = None
    ) -> Dict[str, Any]:
        """Registra un evento de lectura QR clasificando origen móvil vs web (HU: Gestión de Registro y Consulta de Auditoría)."""
        try:
            # Clasificación automática de origen (HU: Dispositivo móvil vs Navegador web)
            if payload.origen:
                origen = payload.origen
            elif payload.tipo_qr and payload.tipo_qr.lower() == "estatico":
                origen = "Navegador web"
            else:
                origen = "Dispositivo móvil"

            resultado = await self.repository.registrar_lectura(
                documento_consultado=payload.documento_consultado,
                documento_consultor=payload.documento_consultor,
                origen=origen,
                ip=ip,
                client_id=payload.client_id,
                id_lectura=payload.id_lectura,
                fecha_lectura=payload.fecha_lectura
            )
            mensaje = "Lectura previamente sincronizada (idempotencia confirmada)." if resultado.get("ya_registrado") else "Lectura registrada exitosamente."
            return {
                "success": True,
                "mensaje": mensaje,
                "data": resultado
            }
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al registrar lectura QR: {e}")
            raise PipelineException(
                etapa="REGISTRO_LECTURA",
                mensaje="No fue posible registrar el evento de lectura QR.",
                detalle_tecnico=str(e),
                cliente_id=payload.client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def get_historial_lecturas(
        self,
        documento: str,
        filtro: str = "me_consultaron",
        limit: int = 20,
        offset: int = 0,
        client_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Consulta el historial de lecturas según documento del usuario (App Móvil 14:09)."""
        try:
            filtro_norm = "mis_consultas" if str(filtro).lower() == "mis_consultas" else "me_consultaron"
            items, total = await self.repository.get_historial_lecturas_usuario(
                documento=str(documento).strip(),
                filtro=filtro_norm,
                limit=limit,
                offset=offset,
                client_id=client_id
            )
            return {
                "success": True,
                "filtro": filtro_norm,
                "total": total,
                "data": items
            }
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al consultar historial de lecturas: {e}")
            raise PipelineException(
                etapa="CONSULTA_HISTORIAL_LECTURAS",
                mensaje=f"No fue posible consultar el historial de lecturas para el documento {documento}.",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def obtener_novedades(self, client_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Obtiene las novedades del bloque dinámico desde el CMS nx9 para la aplicación móvil.
        """
        return await self.jcc_client.obtener_novedades(client_id=client_id)

    # =========================================================================
    # PLANTILLA DE ACTIVACIÓN (CONTADORES Y SOCIEDADES)
    # =========================================================================
    def obtener_palabras_clave_plantilla(self, tipo_tarjeta: str = "contadores") -> Dict[str, Any]:
        from app.services.constancia_activacion_pdf_service import (
            KEYWORDS_CONTADORES,
            KEYWORDS_SOCIEDADES,
        )
        is_soc = "sociedad" in str(tipo_tarjeta or "").lower()
        tipo_norm = "sociedades" if is_soc else "contadores"
        cat = KEYWORDS_SOCIEDADES if is_soc else KEYWORDS_CONTADORES
        columnas = [
            {"key": k, "placeholder": f"{{{k}}}", "label": lbl}
            for k, lbl in cat
            if k not in ("NUMERO_SOPORTE", "FECHA_GENERACION")
        ]
        soporte = [
            {"key": k, "placeholder": f"{{{k}}}", "label": lbl}
            for k, lbl in cat
            if k in ("NUMERO_SOPORTE", "FECHA_GENERACION")
        ]
        return {
            "tipo_tarjeta": tipo_norm,
            "total": len(cat),
            "columnas": columnas,
            "soporte": soporte,
        }

    def descargar_formato_ejemplo_plantilla(self, tipo_tarjeta: str = "contadores") -> Tuple[bytes, str]:
        from app.services.constancia_activacion_pdf_service import ConstanciaActivacionPdfService
        svc = ConstanciaActivacionPdfService()
        return svc.generar_docx_ejemplo(tipo_tarjeta)

    async def listar_plantillas_activacion(
        self,
        tipo_tarjeta: str = "contadores",
        page: int = 1,
        page_size: int = 5,
        client_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        return await self.repository.listar_plantillas_activacion(
            tipo_tarjeta=tipo_tarjeta,
            page=page,
            page_size=page_size,
            client_id=client_id,
        )

    async def descargar_plantilla_activacion(
        self,
        plantilla_id: int,
        client_id: Optional[int] = None,
    ) -> Tuple[bytes, str]:
        row = await self.repository.obtener_plantilla_activacion_por_id(plantilla_id, client_id=client_id)
        if not row or not row.get("contenido_docx"):
            raise PipelineException(
                etapa="PLANTILLA_NO_ENCONTRADA",
                mensaje="No se encontró la plantilla solicitada en el historial.",
                cliente_id=client_id,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        filename = str(row.get("nombre_archivo") or f"plantilla_activacion_{plantilla_id}.docx").strip()
        if not filename.lower().endswith(".docx"):
            filename = f"{filename}.docx"
        return row["contenido_docx"], filename

    async def guardar_plantilla_activacion(
        self,
        tipo_tarjeta: str,
        titulo: str,
        nombre_archivo: str,
        contenido_docx: bytes,
        usuario: str = "admin",
        client_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        from app.services.constancia_activacion_pdf_service import validar_palabras_clave_docx

        tipo_norm = "sociedades" if "sociedad" in str(tipo_tarjeta or "").lower() else "contadores"
        tipo_lbl = "Sociedades" if tipo_norm == "sociedades" else "Contadores"
        titulo_clean = str(titulo or "").strip()

        if not titulo_clean:
            raise PipelineException(
                etapa="VALIDACION_PLANTILLA",
                mensaje="El nombre de la plantilla es obligatorio.",
                cliente_id=client_id,
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        fname_clean = str(nombre_archivo or "").strip()
        if not fname_clean.lower().endswith(".docx"):
            raise PipelineException(
                etapa="FORMATO_ARCHIVO_NO_PERMITIDO",
                mensaje="Formato no permitido. Solo se permiten archivos Word (.docx).",
                cliente_id=client_id,
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        max_bytes = 5 * 1024 * 1024
        if not contenido_docx:
            raise PipelineException(
                etapa="ARCHIVO_VACIO",
                mensaje="Debe cargar el archivo de la plantilla (.docx).",
                cliente_id=client_id,
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if len(contenido_docx) > max_bytes:
            raise PipelineException(
                etapa="TAMANO_MAXIMO_EXCEDIDO",
                mensaje="El archivo supera el tamaño máximo permitido de 5 MB.",
                cliente_id=client_id,
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        try:
            encontradas, invalidas = validar_palabras_clave_docx(contenido_docx, tipo_norm)
        except ValueError as ve:
            raise PipelineException(
                etapa="DOCX_INVALIDO",
                mensaje=str(ve),
                cliente_id=client_id,
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        if invalidas:
            lista_fmt = ", ".join(f"{{{k}}}" for k in invalidas)
            raise PipelineException(
                etapa="PALABRAS_CLAVE_INVALIDAS",
                mensaje=f"El archivo contiene palabras clave que no existen para {tipo_lbl}: {lista_fmt}. Corrija el documento y cárguelo nuevamente.",
                detalle_tecnico=lista_fmt,
                cliente_id=client_id,
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        guardada = await self.repository.guardar_plantilla_activacion(
            tipo_tarjeta=tipo_norm,
            titulo=titulo_clean,
            nombre_archivo=fname_clean,
            tamano_bytes=len(contenido_docx),
            contenido_docx=contenido_docx,
            usuario=usuario,
            client_id=client_id,
        )
        guardada["palabras_clave_detectadas"] = encontradas
        return guardada

