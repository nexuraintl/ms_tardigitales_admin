import time
import base64
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, UploadFile
from datetime import datetime
from app.repositories.tarjetas_repository import TarjetasRepository
from app.schemas.tarjetas_schema import TarjetaCreateSchema, ValidadorConfigSchema, BrandingCredentialsCreateSchema, BrandingCredentialsUpdateSchema, AuditoriaApiCreateSchema, ContadorCreateSchema, SociedadCreateSchema, ConsultaMatriculaResponseSchema
from app.integrations.jcc_client import JccClient
from app.services.auditoria_service import AuditoriaService
from app.constants import TipoTarjeta

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

        try:
            if not documento or not str(documento).strip():
                raise HTTPException(
                    status_code=400,
                    detail="El número de documento de identidad o NIT es estrictamente requerido para la consulta."
                )

            # Consultar API de la JCC a través del módulo de integraciones
            result = await self.jcc_client.consultar_registro(
                documento=documento,
                tipo_tarjeta=tipo_tarjeta,
                tipo=tipo
            )

            if not result or not result.get("encontrado") or not result.get("data"):
                raise HTTPException(
                    status_code=404,
                    detail="No se encontró ningún registro oficial para el documento especificado en la JCC (MS-3835)."
                )

            final_response = {
                "status": "success",
                "data": result["data"]
            }

            return final_response
        except HTTPException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al consultar registro JCC: {e}")
            raise HTTPException(
                status_code=500,
                detail="Error al consultar el registro institucional en la API de la JCC (MS-3834)."
            )
        finally:
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
        except Exception as e:
            print(f"[TarjetasService] Error guardando auditoría: {e}")

        return result

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
                filtro_nombre=filtros.get("nombre"),
                filtro_documento=filtros.get("documento"),
                filtro_expediente=filtros.get("expediente"),
                filtro_resolucion=filtros.get("resolucion"),
                filtro_acta_jcc=filtros.get("acta_jcc"),
                filtro_no_tarjeta=filtros.get("no_tarjeta"),
                filtro_inscripcion=filtros.get("inscripcion"),
                order_by=order_by,
                order_dir=order_dir
            )
        except HTTPException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al listar tarjetas: {e}")
            raise HTTPException(
                status_code=500,
                detail="No fue posible cargar el listado de tarjetas (MS-3830)."
            )

    async def get_tarjeta(self, tarjeta_id: int, tipo_tarjeta: Optional[str] = None, client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            tarjeta = await self.repository.get_by_id(tarjeta_id, tipo_tarjeta ,client_id)
            if not tarjeta:
                raise HTTPException(
                    status_code=404,
                    detail="Tarjeta digital no encontrada (MS-3806)."
                )
            return tarjeta
        except HTTPException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al obtener tarjeta {tarjeta_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="No fue posible consultar la tarjeta solicitada (MS-3830)."
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

            item = consulta.get("data")
            if not item or not consulta.get("encontrado"):
                return {
                    "status": "no_data",
                    "message": "No se encontraron registros disponibles en el JCC o los datos no cumplen los criterios."
                }

            tipo_asociado_key = tipo if tipo else "primeraVez"
            estado_tarjeta = "Vigente"

            no_documento = item.get("no_documento")

            existe_contador = await self.repository.exists_accountant(no_documento, client_id)
            if existe_contador:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "status": "conflict",
                        "message": f"El contador con número documento {no_documento} ya está registrado previamente (MS-3857)."
                    },
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
            except Exception as e:
                print(f"[TarjetasService] Error insertando contador: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Error en la base de datos al registrar la tarjeta (MS-3831).",
                )

        except HTTPException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error crítico al crear tarjeta contadores: {e}")
            raise HTTPException(
                status_code=500,
                detail="Error en la base de datos al registrar la tarjeta (MS-3831).",
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

            item = consulta.get("data")
            if not item or not consulta.get("encontrado"):
                return {
                    "status": "no_data",
                    "message": "No se encontraron registros disponibles en el JCC o los datos no cumplen los criterios."
                }
            
            tipo_asociado_key = tipo if tipo else "primeraVez"
            estado_tarjeta = "Vigente"

            nit = item.get("nit") or documento

            existe_sociedad = await self.repository.exists_society(nit, client_id)
            if existe_sociedad:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "status": "conflict",
                        "message": f"La sociedad con NIT {nit} ya está registrada previamente (MS-3857)."
                    },
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
            except Exception as e:
                print(f"[TarjetasService] Error insertando sociedad: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Error en la base de datos al registrar la tarjeta (MS-3831).",
                )

        except HTTPException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error crítico al crear tarjeta sociedad: {e}")
            raise HTTPException(
                status_code=500,
                detail="Error en la base de datos al registrar la tarjeta (MS-3831).",
            )

    async def get_historial(self, tarjeta_id: int, client_id: Optional[int] = None, tipo: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            return await self.repository.get_historial(tarjeta_id, client_id, tipo)
        except HTTPException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al obtener historial de tarjeta {tarjeta_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="No fue posible obtener el historial de la tarjeta (MS-3832)."
            )

    async def get_validador_config(self, client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            return await self.repository.get_validador_config(client_id)
        except HTTPException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al cargar configuración de validador: {e}")
            raise HTTPException(
                status_code=500,
                detail="No fue posible cargar la configuración del validador (MS-3850)."
            )

    async def save_validador_config(self, data: ValidadorConfigSchema, client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            await self.repository.save_validador_config(data.dict(), client_id)
            return {
                "status": "success",
                "message": "Configuración del validador guardada exitosamente."
            }
        except HTTPException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al guardar configuración de validador: {e}")
            raise HTTPException(
                status_code=500,
                detail="No fue posible guardar la configuración del validador (MS-3851)."
            )

    async def get_columns_config(self, tipo_tarjeta: str = "contadores", client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            cols = await self.repository.get_columns_config(tipo_tarjeta, client_id)
            return {
                "status": "success",
                "data": cols
            }
        except HTTPException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al cargar configuración de columnas: {e}")
            raise HTTPException(
                status_code=500,
                detail="No fue posible cargar la configuración de columnas (MS-3858)."
            )

    async def create_or_update_branding_credentials(self, data: BrandingCredentialsCreateSchema, client_id: Optional[int] = None,) -> Dict[str, Any]:
        try:
            cid = client_id or data.idCliente or 20001
            existing = await self.repository.get_by_cliente_and_tipo(
                cid, data.tipo_id, client_id=cid
            )

            # Preservar logo y patrón de la versión previa si no se enviaron nuevos
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

        except HTTPException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error en upsert branding: {e}")
            raise HTTPException(
                status_code=500,
                detail="No fue posible guardar la configuración de branding (MS-3852).",
            )

    async def update_branding_credentials_change_version(self, branding_credential_id: int, data: BrandingCredentialsUpdateSchema,  client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            existing = await self.repository.get_by_id_branding_credencials(branding_credential_id, client_id)
            if not existing:
                raise HTTPException(
                    status_code=404,
                    detail=f"Branding credencial con ID {branding_credential_id} no encontrado (MS-3857)."
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
            
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al actualizar versión publicada {branding_credential_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="No fue posible actualizar la versión publicada del branding (MS-3856)."
            )

    async def get_branding_credentials(self, branding_credential_id: int, client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            result = await self.repository.get_by_id_branding_credencials(branding_credential_id, client_id)
            if not result:
                raise HTTPException(
                    status_code=404,
                    detail=f"Branding credencial con ID {branding_credential_id} no encontrado."
                )
            return result
        except HTTPException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al obtener Branding credencial {branding_credential_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="No fue posible obtener la información del branding (MS-3855)."
            )

    async def get_branding_credentials_publish(self, branding_credential_id: int, client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            result = await self.repository.get_branding_credentials_publish(branding_credential_id, client_id)
            if not result:
                raise HTTPException(
                    status_code=404,
                    detail=f"Branding credencial con ID {branding_credential_id} no encontrado."
                )
            return result
        except HTTPException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al obtener Branding credencial publicada {branding_credential_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="No fue posible obtener la información del branding (MS-3856)."
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
        except HTTPException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al obtener el historial de versiones de Branding de credenciales {branding_credential_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="No fue posible obtener el historial de versiones de Branding de credenciales (MS-3854)."
            )

    async def create_auditoria_api(self, data: AuditoriaApiCreateSchema, client_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            new_id = await self.repository.create_auditoria_api(data.dict(), client_id)
            return {
                "id": new_id,
                "status": "success",
                "message": "Creacion de la auditoría API creada exitosamente."
            }
        except HTTPException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al crear la auditoría API: {e}")
            raise HTTPException(
                status_code=500,
                detail="No fue posible completar la creacion de la auditoría API (MS-3852)."
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
            # Aseguramos que page_size nunca supere 100
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
        except HTTPException:
            raise
        except Exception as e:
            print(f"[TarjetasService] Error al listar la auditoría API: {e}")
            raise HTTPException(
                status_code=500,
                detail="No fue posible cargar el listado de auditoría API (MS-3852)."
            )