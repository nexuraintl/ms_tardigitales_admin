import time
import base64
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, UploadFile, status
from datetime import datetime
from app.repositories.tarjetas_repository import TarjetasRepository
from app.schemas.tarjetas_schema import (
    TarjetaCreateSchema,
    ValidadorConfigSchema,
    BrandingCredentialsCreateSchema,
    BrandingCredentialsUpdateSchema,
    AuditoriaApiCreateSchema,
    ContadorCreateSchema,
    SociedadCreateSchema,
    ConsultaMatriculaResponseSchema,
    EstadoTarjetaEnum,
    EstadoRegistroEnum
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
            # Consultar API de la JCC a través del módulo de integraciones
            result = await self.jcc_client.consultar_registro(
                documento=documento,
                tipo_tarjeta=tipo_tarjeta,
                tipo=tipo
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
            raise PipelineException(
                etapa="CONSULTA_API_JCC",
                mensaje="No se encontró ningún registro oficial para el documento especificado en la JCC.",
                cliente_id=client_id,
                status_code=status.HTTP_404_NOT_FOUND
            )

        duracion_ms = int((time.perf_counter() - start) * 1000)

        try:
            await self.auditoria.registrar(
                client_id=client_id,
                tipo_tarjeta=tipo_tarjeta,
                tipo=tipo,
                metodo="POST",
                url=self.jcc_client.last_url or "",
                parametros_peticion={
                    "tipo": tipo,
                    "documento": documento,
                    "cambiarEstado": False,
                },
                cuerpo_respuesta=result,
                duracion_ms=duracion_ms,
            )
        except PipelineException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error guardando auditoría: {e}")
            raise PipelineException(
                etapa="REGISTRO_AUDITORIA",
                mensaje="La consulta a la JCC fue exitosa, pero falló el registro en la tabla de auditoría (jcc_auditoria_api).",
                detalle_tecnico=str(e),
                cliente_id=client_id,
                tabla_afectada="jcc_auditoria_api",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
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
        
        page_size = min(max(page_size, 1), 100)

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
                order_dir=order_dir
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
                "fecha_emision": datetime.now(),
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

        try:
            existe_sociedad = await self.repository.exists_society(nit, client_id)
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
                "fecha_emision": datetime.now(),
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

    async def get_validador_config(self, client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            return await self.repository.get_validador_config(client_id)
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

    async def save_validador_config(self, data: ValidadorConfigSchema, client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            await self.repository.save_validador_config(data.dict(), client_id)
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

            branding_data = {
                "version_actual": data.version_actual,
                "version_publicada": data.version_publicada,
                "logo": logo_val,
                "patron": patron_val,
                "color_fondo": data.color_fondo,
                "color_letra": data.color_letra,
                "fuente_letra": data.fuente_letra,
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
            existing = await self.repository.get_by_id_branding_credencials(branding_credential_id, client_id)
            if not existing:
                raise PipelineException(
                    etapa="BRANDING_CREDENTIALS",
                    mensaje=f"Branding credencial con ID {branding_credential_id} no encontrado.",
                    cliente_id=client_id,
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            await self.repository.update_branding_credentials_change_version(
                branding_credential_id,
                data.dict(exclude_none=True), 
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
            return result
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
            page_size = min(max(page_size, 1), 100)
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
            page_size = min(max(page_size, 1), 100)
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