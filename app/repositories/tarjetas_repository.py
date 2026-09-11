import aiomysql
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.core.database import get_client_connection

class TarjetasRepository:

    async def get_all(self, tipo_tarjeta: Optional[str] = None, client_id: Optional[int] = None) -> List[Dict[str, Any]]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                if tipo_tarjeta == "contadores":
                    await cursor.execute(
                        """
                        SELECT ttc.id,
                            ttc.no_tarjeta,
                            CONCAT(ttc.nombres, " ",ttc.primer_apellido, " ", ttc.segundo_apellido) AS nombre_completo,
                            ttc.no_expd,
                            ttta.nombre AS tipo_asociado,
                            DATE_FORMAT(ttc.fecha_emision, '%Y-%m-%d %H:%i:%s') AS fecha_emision,
                            CONCAT(ttc.tipo_documento, " ", ttc.no_documento) AS documento,
                            ttc.correo,
                            ttet.nombre AS estado_tarjeta,
                            ttc.estado_contador 
                        FROM tn_tarjetavirtual_contadores ttc 
                        INNER JOIN tn_tarjetavirtual_tipos_asociados ttta 
                        ON ttc.tipo_asociado_id = ttta.id 
                        INNER JOIN tn_tarjetavirtual_estados_tarjetas ttet 
                        ON ttc.estado_tarjeta_id = ttet.id
                        ORDER BY ttc.id DESC
                        """
                    )
                elif tipo_tarjeta == "sociedades":
                    await cursor.execute(
                        """
                        SELECT tts.id,
                            tts.no_expd,
                            tts.razon_social,
                            tts.nit,
                            ttta.nombre AS tipo_asociado,
                            DATE_FORMAT(tts.fecha_emision, '%Y-%m-%d %H:%i:%s') AS fecha_emision,
                            tts.inscripcion,
                            ttet.nombre AS estado_tarjeta,
                            tts.estado_sociedad,
                            tts.resolucion  
                        FROM tn_tarjetavirtual_sociedades tts
                        INNER JOIN tn_tarjetavirtual_tipos_asociados ttta 
                        ON tts.tipo_asociado_id = ttta.id 
                        INNER JOIN tn_tarjetavirtual_estados_tarjetas ttet 
                        ON tts.estado_tarjeta_id = ttet.id 
                        ORDER BY tts.id DESC
                        """
                    )
                else:
                    return []
                return await cursor.fetchall()
        finally:
            conn.close()

    async def get_by_id(self, tarjeta_id: int, tipo_tarjeta: Optional[str] = None, client_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                if tipo_tarjeta == "contadores":
                    await cursor.execute(
                        """
                        SELECT ttc.id,
                            ttc.no_tarjeta,
                            CONCAT(ttc.nombres, " ",ttc.primer_apellido, " ", ttc.segundo_apellido) AS nombre_completo,
                            ttc.no_expd,
                            ttta.nombre AS tipo_asociado,
                            DATE_FORMAT(ttc.fecha_emision, '%%Y-%%m-%%d %%H:%%i:%%s') AS fecha_emision,
                            CONCAT(ttc.tipo_documento, " ", ttc.no_documento) AS documento,
                            ttc.correo,
                            ttet.nombre AS estado_tarjeta,
                            ttc.estado_contador 
                        FROM tn_tarjetavirtual_contadores ttc 
                        INNER JOIN tn_tarjetavirtual_tipos_asociados ttta 
                        ON ttc.tipo_asociado_id = ttta.id 
                        INNER JOIN tn_tarjetavirtual_estados_tarjetas ttet 
                        ON ttc.estado_tarjeta_id = ttet.id
                        WHERE ttc.id = %s
                        ORDER BY ttc.id DESC
                        """,
                        (tarjeta_id,)
                    )
                elif tipo_tarjeta == "sociedades":
                    await cursor.execute(
                        """
                        SELECT tts.id,
                            tts.no_expd,
                            tts.razon_social,
                            tts.nit,
                            ttta.nombre AS tipo_asociado,
                            DATE_FORMAT(tts.fecha_emision, '%%Y-%%m-%%d %%H:%%i:%%s') AS fecha_emision,
                            tts.inscripcion,
                            ttet.nombre AS estado_tarjeta,
                            tts.estado_sociedad,
                            tts.resolucion  
                        FROM tn_tarjetavirtual_sociedades tts
                        INNER JOIN tn_tarjetavirtual_tipos_asociados ttta 
                        ON tts.tipo_asociado_id = ttta.id 
                        INNER JOIN tn_tarjetavirtual_estados_tarjetas ttet 
                        ON tts.estado_tarjeta_id = ttet.id
                        WHERE tts.id = %s 
                        ORDER BY tts.id DESC
                        """,
                        (tarjeta_id,)
                    )
                else:
                    return []
                return await cursor.fetchone()
        finally:
            conn.close()

    async def create(self, tarjeta_data: Dict[str, Any], client_id: Optional[int] = None) -> int:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO tn_tarjetavirtual_tarjetas (
                        tipo_tarjeta, codigo, expediente, solicitante, documento,
                        matricula, correo, representante, tarjeta, fecha
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        tarjeta_data.get("tipo_tarjeta") or tarjeta_data.get("tipoTarjeta", "contadores"),
                        tarjeta_data.get("codigo", ""),
                        tarjeta_data.get("expediente", 0),
                        tarjeta_data.get("solicitante") or tarjeta_data.get("nombreTitular", ""),
                        tarjeta_data.get("documento") or tarjeta_data.get("identificacion", ""),
                        tarjeta_data.get("matricula") or tarjeta_data.get("numeroTarjeta", ""),
                        tarjeta_data.get("correo", ""),
                        tarjeta_data.get("representante", None),
                        tarjeta_data.get("tarjeta") or tarjeta_data.get("estado", "Activa"),
                        tarjeta_data.get("fecha", None)
                    )
                )
                return cursor.lastrowid
        finally:
            conn.close()

    async def get_historial(self, tarjeta_id: int, client_id: Optional[int] = None) -> List[Dict[str, Any]]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT
                        id,
                        tarjeta_id,
                        estado,
                        descripcion,
                        DATE_FORMAT(fecha, '%%Y-%%m-%%d %%H:%%i') AS fecha,
                        realizado_por
                    FROM tn_tarjetavirtual_estados_historial
                    WHERE tarjeta_id = %s
                    ORDER BY id DESC
                    """,
                    (tarjeta_id,)
                )
                return await cursor.fetchall()
        finally:
            conn.close()

    async def get_validador_config(self, client_id: Optional[int] = None) -> Dict[str, Any]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT
                        id,
                        client_id,
                        val_foto,
                        val_nombres,
                        val_matricula,
                        val_numero_identificacion,
                        val_codigo_tarjeta,
                        val_estado
                    FROM tn_tarjetavirtual_validador_config
                    WHERE client_id = %s
                    LIMIT 1
                    """,
                    (client_id,)
                )
                row = await cursor.fetchone()
                if row:
                    row["val_foto"] = bool(row["val_foto"])
                    row["val_nombres"] = bool(row["val_nombres"])
                    row["val_matricula"] = bool(row["val_matricula"])
                    row["val_numero_identificacion"] = bool(row["val_numero_identificacion"])
                    row["val_codigo_tarjeta"] = bool(row["val_codigo_tarjeta"])
                    row["val_estado"] = bool(row["val_estado"])
                    return row
                return {
                    "val_foto": True,
                    "val_nombres": True,
                    "val_matricula": True,
                    "val_numero_identificacion": True,
                    "val_codigo_tarjeta": True,
                    "val_estado": True
                }
        finally:
            conn.close()

    async def save_validador_config(self, config_data: Dict[str, Any], client_id: Optional[int] = None) -> bool:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT id FROM tn_tarjetavirtual_validador_config WHERE client_id = %s LIMIT 1",
                    (client_id,)
                )
                exists = await cursor.fetchone()
                
                vf = 1 if config_data.get("val_foto") else 0
                vn = 1 if config_data.get("val_nombres") else 0
                vm = 1 if config_data.get("val_matricula") else 0
                vnum = 1 if config_data.get("val_numero_identificacion") else 0
                vc = 1 if config_data.get("val_codigo_tarjeta") else 0
                ve = 1 if config_data.get("val_estado") else 0

                if exists:
                    await cursor.execute(
                        """
                        UPDATE tn_tarjetavirtual_validador_config SET
                            val_foto = %s,
                            val_nombres = %s,
                            val_matricula = %s,
                            val_numero_identificacion = %s,
                            val_codigo_tarjeta = %s,
                            val_estado = %s,
                            fecha_actualizacion = CURRENT_TIMESTAMP
                        WHERE client_id = %s
                        """,
                        (vf, vn, vm, vnum, vc, ve, client_id)
                    )
                else:
                    await cursor.execute(
                        """
                        INSERT INTO tn_tarjetavirtual_validador_config (
                            client_id, val_foto, val_nombres, val_matricula,
                            val_numero_identificacion, val_codigo_tarjeta, val_estado
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (client_id, vf, vn, vm, vnum, vc, ve)
                    )
                return True
        finally:
            conn.close()

    #Buscar por tipo y cliente
    async def get_by_cliente_and_tipo(self, id_cliente: int, tipo_id: int, client_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT
                        id, idCliente, version_actual, version_publicada,
                        logo, color_fondo, color_letra, fuente_letra,
                        usuario_creacion_id, tipo_id
                    FROM tn_tarjetavirtual_configuracion_branding
                    WHERE idCliente = %s AND tipo_id = %s
                    LIMIT 1
                    """,
                    (id_cliente, tipo_id),
                )
                return await cursor.fetchone()
        finally:
            conn.close()

    async def create_branding_credentials(self, branding_credencials_data: Dict[str, Any], client_id: Optional[int] = None) -> int:
        conn = await get_client_connection(client_id)
        cursor = None
        try:
            cursor = await conn.cursor()
            await cursor.execute("START TRANSACTION")
            
            await cursor.execute(
                """
                INSERT INTO tn_tarjetavirtual_configuracion_branding (
                    idCliente, version_actual, version_publicada, logo, color_fondo,
                    color_letra, fuente_letra, usuario_creacion_id,tipo_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    client_id,
                    int(branding_credencials_data.get("version_actual", 1)),
                    branding_credencials_data.get("version_publicada"),
                    branding_credencials_data.get("logo"),
                    branding_credencials_data.get("color_fondo"),
                    branding_credencials_data.get("color_letra"),
                    branding_credencials_data.get("fuente_letra"),
                    branding_credencials_data.get("usuario_creacion_id"),
                    branding_credencials_data.get("tipo_id")
                )
            )
            
            branding_id = cursor.lastrowid
            
            await cursor.execute(
                """
                INSERT INTO tn_tarjetavirtual_configuracion_branding_historico (
                    idCliente, configuracion_branding_id, version, logo, color_fondo,
                    color_letra, fuente_letra, usuario_creacion_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    client_id,
                    branding_id,
                    int(branding_credencials_data.get("version_actual", 1)),
                    branding_credencials_data.get("logo"),
                    branding_credencials_data.get("color_fondo"),
                    branding_credencials_data.get("color_letra"),
                    branding_credencials_data.get("fuente_letra"),
                    branding_credencials_data.get("usuario_creacion_id")
                )
            )
            
            await cursor.execute("COMMIT")
            
            return branding_id
            
        except Exception as e:
            if cursor:
                await cursor.execute("ROLLBACK")
            print(f"Error en create_branding_credentials: {e}")
            raise e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                conn.close()

    async def get_by_id_branding_credencials(self, branding_credential_id: int, client_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT
                        id,
                        version_actual,
                        version_publicada,
                        logo,
                        color_fondo,
                        color_letra,
                        fuente_letra,
                        usuario_creacion_id
                    FROM tn_tarjetavirtual_configuracion_branding
                    WHERE id = %s
                    LIMIT 1
                    """,
                    (branding_credential_id,)
                )
                row = await cursor.fetchone()
                return row
        finally:
            conn.close()

    async def get_branding_credentials_publish(self, branding_credential_id: int, client_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT
                        tcbh.logo,
                        tcbh.color_fondo,
                        tcbh.color_letra,
                        tcbh.fuente_letra
                    FROM tn_tarjetavirtual_configuracion_branding_historico tcbh
                    INNER JOIN tn_tarjetavirtual_configuracion_branding ttc
                        ON ttc.id = tcbh.configuracion_branding_id
                        AND ttc.version_publicada = tcbh.version
                    WHERE tcbh.configuracion_branding_id = %s
                    ORDER BY tcbh.version DESC
                    LIMIT 1
                    """,
                    (branding_credential_id,)
                )
                
                row = await cursor.fetchone()
                return row
                
        except Exception as e:
            print(f"Error al obtener branding publicado: {e}")
            return None
        finally:
            conn.close()

    async def update_branding_credentials(self, branding_id: int, update_data: Dict[str, Any], client_id: Optional[int] = None) -> bool:
        conn = None
        cursor = None
        try:
            conn = await get_client_connection(client_id)
            cursor = await conn.cursor()
            
            await cursor.execute("START TRANSACTION")
            
            await cursor.execute(
                "SELECT version_actual, idCliente FROM tn_tarjetavirtual_configuracion_branding WHERE id = %s",
                (branding_id,)
            )
            result = await cursor.fetchone()
            if not result:
                raise ValueError(f"Branding con ID {branding_id} no encontrado")
            
            current_version = result[0]
            new_version = current_version + 1
            usuario_creacion = update_data.get("usuario_creacion_id")
                        
            await cursor.execute(
                """
                UPDATE tn_tarjetavirtual_configuracion_branding 
                SET version_actual = %s,
                    version_publicada = COALESCE(%s, version_publicada),
                    logo = COALESCE(%s, logo),
                    color_fondo = COALESCE(%s, color_fondo),
                    color_letra = COALESCE(%s, color_letra),
                    fuente_letra = COALESCE(%s, fuente_letra),
                    usuario_creacion_id = COALESCE(%s, usuario_creacion_id)
                WHERE id = %s
                """,
                (
                    new_version,
                    update_data.get("version_publicada"),
                    update_data.get("logo"),
                    update_data.get("color_fondo"),
                    update_data.get("color_letra"),
                    update_data.get("fuente_letra"),
                    update_data.get("usuario_creacion_id"),
                    branding_id
                )
            )
            
            await cursor.execute(
                """
                INSERT INTO tn_tarjetavirtual_configuracion_branding_historico (
                    idCliente, configuracion_branding_id, version, logo, color_fondo,
                    color_letra, fuente_letra, usuario_creacion_id
                ) SELECT 
                    idCliente, id, %s, logo, color_fondo,
                    color_letra, fuente_letra, %s
                FROM tn_tarjetavirtual_configuracion_branding
                WHERE id = %s
                """,
                (new_version, usuario_creacion, branding_id)
            )
            
            await cursor.execute("COMMIT")
            return True
            
        except Exception as e:
            if cursor:
                await cursor.execute("ROLLBACK")
            raise e
        finally:
            if cursor:
                await cursor.close()
            if conn:
                conn.close() 


    async def validate_version_exists(self, branding_id: int, version: int, client_id: Optional[int] = None) -> bool:
        """Valida si una versión específica existe en el histórico"""
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM tn_tarjetavirtual_configuracion_branding_historico
                    WHERE configuracion_branding_id = %s AND version = %s
                    """,
                    (branding_id, version)
                )
                result = await cursor.fetchone()
                return result['count'] > 0
        finally:
            conn.close()

    async def update_branding_credentials_change_version(self, branding_id: int, data: Dict[str, Any], client_id: Optional[int] = None) -> None:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cursor:
                version_to_publish = data.get('version_publicada')
                
                if not await self.validate_version_exists(branding_id, version_to_publish, client_id):
                    raise ValueError(f"La versión {version_to_publish} no existe en el histórico (MS-3858)")
                
                await cursor.execute(
                    """
                    UPDATE tn_tarjetavirtual_configuracion_branding
                    SET 
                        version_publicada = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        data.get('version_publicada'),
                        branding_id
                    )
                )
                
                if cursor.rowcount == 0:
                    raise ValueError(f"No se pudo actualizar el branding con ID {branding_id}")
                    
        finally:
            conn.close()

    async def list_history_branding_credentials(self, branding_id: int, client_id: Optional[int] = None) -> List[Dict[str, Any]]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT
                        tcbh.id,
                        tcbh.idCliente,
                        tcbh.configuracion_branding_id,
                        tcbh.version,
                        CONCAT("v", tcbh.version) AS version_formatted,
                        tcbh.logo,
                        tcbh.color_fondo,
                        tcbh.color_letra,
                        tcbh.fuente_letra,
                        tcbh.usuario_creacion_id,
                        DATE_FORMAT(tcbh.created_at, '%%Y-%%m-%%d %%H:%%i') AS created_at_formatted,
                        tcbh.created_at,
                        CONCAT("v", tcbh.version, " -- ", DATE_FORMAT(tcbh.created_at, '%%Y-%%m-%%d %%H:%%i')) AS Registro,
                        CASE 
                            WHEN ttc.version_publicada = tcbh.version THEN 'Publicada'
                            ELSE ''
                        END AS publicado
                    FROM tn_tarjetavirtual_configuracion_branding_historico tcbh
                    INNER JOIN tn_tarjetavirtual_configuracion_branding ttc
                        ON ttc.id = tcbh.configuracion_branding_id
                    WHERE tcbh.configuracion_branding_id = %s
                    ORDER BY tcbh.version DESC
                    """,
                    (branding_id,)
                )
                return await cursor.fetchall()
        finally:
            conn.close()

    async def create_contadores(self, data: Dict[str, Any], client_id: Optional[int] = None) -> int:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cursor:
                query = """
                    INSERT INTO tn_tarjetavirtual_contadores (
                        no_tarjeta,
                        nombres,
                        primer_apellido,
                        segundo_apellido,
                        no_expd,
                        tipo_documento,
                        no_documento,
                        universidad,
                        estado_contador,
                        resolucion,
                        fecha_estado,
                        fecha_radicacion,
                        fecha_resolucion,
                        acta_jcc,
                        fecha_grado,
                        seccional,
                        correo,
                        fecha_emision,
                        tipo_asociado_id,
                        estado_tarjeta_id
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """
                
                values = (
                    data.get("no_tarjeta"),
                    data.get("nombres"),
                    data.get("primer_apellido"),
                    data.get("segundo_apellido"),
                    data.get("no_expd"),
                    data.get("tipo_documento"),
                    data.get("no_documento"),
                    data.get("universidad"),
                    data.get("estado_contador", "ACTIVO"),
                    data.get("resolucion"),
                    data.get("fecha_estado"),
                    data.get("fecha_radicacion"),
                    data.get("fecha_resolucion"),
                    data.get("acta_jcc"),
                    data.get("fecha_grado"),
                    data.get("seccional"),
                    data.get("correo"),
                    data.get("fecha_emision") or datetime.now(),
                    data.get("tipo_asociado_id"),
                    data.get("estado_tarjeta_id")
                )
                
                await cursor.execute(query, values)
                await conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            print(f"[TarjetasRepository] Error al crear contador: {e}")
            raise
        finally:
            conn.close()

    async def create_sociedades(self, data: Dict[str, Any], client_id: Optional[int] = None) -> int:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cursor:
                query = """
                    INSERT INTO tn_tarjetavirtual_sociedades (
                        no_expd,
                        razon_social,
                        nit,
                        tipo_sociedad,
                        inscripcion,
                        fecha_radicacion,
                        estado_sociedad,
                        resolucion,
                        fecha_resolucion,
                        acta_jcc,
                        estado_solicitud,
                        tipo_solicitud,
                        fecha_emision,
                        tipo_asociado_id,
                        estado_tarjeta_id
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                """
                
                values = (
                    data.get("no_expd"),
                    data.get("razon_social"),
                    data.get("nit"),
                    data.get("tipo_sociedad"),
                    data.get("inscripcion"),
                    data.get("fecha_radicacion"),
                    data.get("estado_sociedad", "ACTIVO"),
                    data.get("resolucion"),
                    data.get("fecha_resolucion"),
                    data.get("acta_jcc"),
                    data.get("estado_solicitud"),
                    data.get("tipo_solicitud"),
                    data.get("fecha_emision") or datetime.now(),
                    data.get("tipo_asociado_id"),
                    data.get("estado_tarjeta_id")
                )
                
                await cursor.execute(query, values)
                await conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            print(f"[TarjetasRepository] Error al crear sociedad: {e}")
            raise
        finally:
            conn.close()

    async def create_auditoria_api(self, data: Dict[str, Any], client_id: Optional[int] = None) -> int:

        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cursor:
                query = """
                    INSERT INTO tn_tarjetavirtual_auditoria_api (
                        client_id,
                        tipo_id,
                        metodo,
                        url,
                        fecha_creacion,
                        tipo_asociado_id,
                        duracion_ms,
                        parametros_peticion,
                        cuerpo_respuesta_peticion
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """
                
                values = (
                    data.get("client_id"),
                    data.get("tipo_id"),
                    data.get("metodo"),
                    data.get("url"),
                    data.get("fecha_creacion") or datetime.now(),
                    data.get("tipo_asociado_id"),
                    data.get("duracion_ms"),
                    json.dumps(data.get("parametros_peticion")) if data.get("parametros_peticion") else None,
                    json.dumps(data.get("cuerpo_respuesta_peticion")) if data.get("cuerpo_respuesta_peticion") else None
                )
                
                await cursor.execute(query, values)
                await conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            print(f"[TarjetasRepository] Error al crear auditoría API: {e}")
            raise
        finally:
            conn.close()

    async def get_all_auditoria_api(self, client_id: Optional[int] = None) -> List[Dict[str, Any]]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT
                        DATE_FORMAT(tapi.fecha_creacion, '%%Y-%%m-%%d %%H:%%i') AS fecha_hora,
                        ttt.nombre AS endpoint,
                        tapi.metodo,
                        ttasociado.nombre AS tipo,
                        tapi.duracion_ms,
                        tapi.url,
                        tapi.parametros_peticion,
                        tapi.cuerpo_respuesta_peticion
                    FROM tn_tarjetavirtual_auditoria_api tapi
                    INNER JOIN tn_tarjetavirtual_tipos ttt
                    ON tapi.tipo_id = ttt.id
                    INNER JOIN tn_tarjetavirtual_tipos_asociados ttasociado
                    ON tapi.tipo_asociado_id = ttasociado.id
                    WHERE tapi.client_id = %s;
                    """,
                    (client_id,)
                )
                
                row = await cursor.fetchall()
                
                for item in row:
                    if item.get('cuerpo_respuesta_peticion'):
                        try:
                            item['cuerpo_respuesta_peticion'] = json.loads(item['cuerpo_respuesta_peticion'])
                        except (json.JSONDecodeError, TypeError):
                            pass 
                    
                    if item.get('parametros_peticion'):
                        try:
                            item['parametros_peticion'] = json.loads(item['parametros_peticion'])
                        except (json.JSONDecodeError, TypeError):
                            pass
                return row  
        except Exception as e:
            print(f"Error al obtener el listado de auditoría API: {e}")
            return None
        finally:
            conn.close()