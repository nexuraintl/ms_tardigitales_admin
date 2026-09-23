import aiomysql
import json
import math
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.core.database import get_client_connection

class TarjetasRepository:

    async def get_all(
        self, 
        tipo_tarjeta: Optional[str] = None, 
        client_id: Optional[int] = None, 
        page: int = 1, 
        page_size: int = 10,
        texto: Optional[str] = None,               # Búsqueda general (nombre / razón social, tarjeta/inscripción, expediente, documento/nit, correo)
        filtro_documento: Optional[str] = None,    # Documento (contadores) / NIT (sociedades)
        filtro_expediente: Optional[str] = None,   # No. Expediente
        filtro_resolucion: Optional[str] = None,   # Resolución
        filtro_acta_jcc: Optional[str] = None,     # Acta JCC
        filtro_no_tarjeta: Optional[str] = None,   # Número de tarjeta (solo contadores)
        filtro_inscripcion: Optional[str] = None,  # Inscripción (solo sociedades)
        filtro_correo: Optional[str] = None,       # Correo electrónico
        order_by: Optional[str] = None,
        order_dir: str = "DESC"
    ) -> Dict[str, Any]:

        page_size = min(max(page_size, 1), 100)
        page = max(page, 1)
        
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                if tipo_tarjeta not in ["contadores", "sociedades"]:
                    return {"data": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

                offset = (page - 1) * page_size
                order_dir = "ASC" if order_dir.upper() == "ASC" else "DESC"

                # ==========================================
                # CONSTRUCCIÓN DINÁMICA DE FILTROS Y ORDEN
                # ==========================================
                if tipo_tarjeta == "contadores":
                    base_from = "FROM tn_tarjetavirtual_contadores ttc"
                    
                    # Whitelist de columnas permitidas para ordenar (evita SQL Injection)
                    columnas_permitidas = {
                        "id": "ttc.id",
                        "no_tarjeta": "ttc.no_tarjeta",
                        "nombre_completo": "nombre_completo",
                        "documento": "documento",
                        "no_expd": "ttc.no_expd",
                        "resolucion": "ttc.resolucion",
                        "acta_jcc": "ttc.acta_jcc",
                        "correo": "ttc.correo",
                        "fecha_emision": "ttc.fecha_emision"
                    }
                    
                    # Condiciones WHERE dinámicas
                    conditions = ["1=1"]
                    params = []
                    
                    if texto:
                        term = f"%{texto}%"
                        conditions.append("""(
                            CONCAT(IFNULL(ttc.nombres, ''), ' ', IFNULL(ttc.primer_apellido, ''), ' ', IFNULL(ttc.segundo_apellido, '')) LIKE %s
                            OR ttc.no_tarjeta LIKE %s
                            OR CAST(ttc.no_expd AS CHAR) LIKE %s
                            OR ttc.no_documento LIKE %s
                            OR CONCAT(IFNULL(ttc.tipo_documento, ''), ' ', IFNULL(ttc.no_documento, '')) LIKE %s
                            OR ttc.correo LIKE %s
                        )""")
                        params.extend([term, term, term, term, term, term])
                    if filtro_documento:
                        term_doc = f"%{filtro_documento}%"
                        conditions.append("(ttc.no_documento LIKE %s OR CONCAT(IFNULL(ttc.tipo_documento, ''), ' ', IFNULL(ttc.no_documento, '')) LIKE %s)")
                        params.extend([term_doc, term_doc])
                    if filtro_expediente:
                        conditions.append("CAST(ttc.no_expd AS CHAR) LIKE %s")
                        params.append(f"%{filtro_expediente}%")
                    if filtro_resolucion:
                        conditions.append("ttc.resolucion LIKE %s")
                        params.append(f"%{filtro_resolucion}%")
                    if filtro_acta_jcc:
                        conditions.append("ttc.acta_jcc LIKE %s")
                        params.append(f"%{filtro_acta_jcc}%")
                    if filtro_no_tarjeta:
                        conditions.append("ttc.no_tarjeta LIKE %s")
                        params.append(f"%{filtro_no_tarjeta}%")
                    if filtro_correo:
                        conditions.append("ttc.correo LIKE %s")
                        params.append(f"%{filtro_correo}%")

                    where_clause = " WHERE " + " AND ".join(conditions)
                    
                    # Columna de ordenamiento
                    order_column = columnas_permitidas.get(order_by, "ttc.id")

                elif tipo_tarjeta == "sociedades":
                    base_from = "FROM tn_tarjetavirtual_sociedades tts"
                    
                    columnas_permitidas = {
                        "id": "tts.id",
                        "razon_social": "tts.razon_social",
                        "nit": "tts.nit",
                        "no_expd": "tts.no_expd",
                        "inscripcion": "tts.inscripcion",
                        "resolucion": "tts.resolucion",
                        "acta_jcc": "tts.acta_jcc",
                        "fecha_emision": "tts.fecha_emision"
                    }
                    
                    conditions = ["1=1"]
                    params = []
                    
                    if texto:
                        term = f"%{texto}%"
                        conditions.append("""(
                            tts.razon_social LIKE %s
                            OR tts.nit LIKE %s
                            OR CAST(tts.no_expd AS CHAR) LIKE %s
                            OR tts.inscripcion LIKE %s
                            OR tts.resolucion LIKE %s
                        )""")
                        params.extend([term, term, term, term, term])
                    if filtro_documento:
                        conditions.append("tts.nit LIKE %s")
                        params.append(f"%{filtro_documento}%")
                    if filtro_expediente:
                        conditions.append("CAST(tts.no_expd AS CHAR) LIKE %s")
                        params.append(f"%{filtro_expediente}%")
                    if filtro_resolucion:
                        conditions.append("tts.resolucion LIKE %s")
                        params.append(f"%{filtro_resolucion}%")
                    if filtro_acta_jcc:
                        conditions.append("tts.acta_jcc LIKE %s")
                        params.append(f"%{filtro_acta_jcc}%")
                    if filtro_inscripcion:
                        conditions.append("tts.inscripcion LIKE %s")
                        params.append(f"%{filtro_inscripcion}%")

                    where_clause = " WHERE " + " AND ".join(conditions)
                    order_column = columnas_permitidas.get(order_by, "tts.id")

                # ==========================================
                # 1. CONSULTA DE CONTEO (CON FILTROS)
                # ==========================================
                count_query = f"SELECT COUNT(*) as total {base_from} {where_clause}"
                await cursor.execute(count_query, tuple(params))
                count_result = await cursor.fetchone()
                total_records = count_result['total'] if count_result else 0

                total_pages = math.ceil(total_records / page_size) if total_records > 0 else 0

                if total_records == 0:
                    return {"data": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

                # ==========================================
                # 2. CONSULTA DE DATOS (CON FILTROS, ORDEN Y PAGINACIÓN)
                # ==========================================
                if tipo_tarjeta == "contadores":
                    select_fields = """
                        SELECT ttc.id,
                            ttc.no_tarjeta,
                            CONCAT(IFNULL(ttc.nombres,''), ' ', IFNULL(ttc.primer_apellido,''), ' ', IFNULL(ttc.segundo_apellido,'')) AS nombre_completo,
                            CONCAT(IFNULL(ttc.nombres,''), ' ', IFNULL(ttc.primer_apellido,''), ' ', IFNULL(ttc.segundo_apellido,'')) AS solicitante,
                            ttc.nombres,
                            ttc.primer_apellido,
                            ttc.segundo_apellido,
                            ttc.no_expd,
                            ttc.no_expd AS expediente,
                            ttc.tipo_asociado,
                            DATE_FORMAT(ttc.fecha_emision, '%%Y-%%m-%%d %%H:%%i:%%s') AS fecha_emision,
                            CONCAT(IFNULL(ttc.tipo_documento,''), ' ', IFNULL(ttc.no_documento,'')) AS documento,
                            ttc.tipo_documento,
                            ttc.no_documento,
                            ttc.correo,
                            ttc.universidad,
                            ttc.estado AS estado_tarjeta,
                            ttc.estado_contador AS estado_registro,
                            ttc.estado_contador,
                            ttc.resolucion,
                            DATE_FORMAT(ttc.fecha_estado, '%%Y-%%m-%%d %%H:%%i:%%s') AS fecha_estado,
                            DATE_FORMAT(ttc.fecha_resolucion, '%%Y-%%m-%%d') AS fecha_resolucion,
                            ttc.acta_jcc,
                            DATE_FORMAT(ttc.fecha_grado, '%%Y-%%m-%%d') AS fecha_grado,
                            ttc.seccional,
                            ttc.foto
                    """
                else:
                    select_fields = """
                        SELECT tts.id,
                            tts.no_expd,
                            tts.no_expd AS expediente,
                            tts.razon_social,
                            tts.razon_social AS solicitante,
                            tts.nit,
                            tts.nit AS documento,
                            tts.tipo_asociado,
                            DATE_FORMAT(tts.fecha_emision, '%%Y-%%m-%%d %%H:%%i:%%s') AS fecha_emision,
                            tts.tipo_sociedad,
                            tts.inscripcion,
                            DATE_FORMAT(tts.fecha_radicacion, '%%Y-%%m-%%d %%H:%%i:%%s') AS fecha_radicacion,
                            tts.estado AS estado_tarjeta,
                            tts.estado_sociedad AS estado_registro,
                            tts.estado_sociedad,
                            tts.resolucion,
                            DATE_FORMAT(tts.fecha_resolucion, '%%Y-%%m-%%d') AS fecha_resolucion,
                            tts.acta_jcc,
                            tts.estado_solicitud,
                            tts.tipo_solicitud,
                            tts.representante_legal,
                            tts.foto
                    """

                data_query = f"""
                    {select_fields}
                    {base_from}
                    {where_clause}
                    ORDER BY {order_column} {order_dir}
                    LIMIT %s OFFSET %s
                """
                
                # Importante: los parámetros del LIMIT y OFFSET van al final
                data_params = params + [page_size, offset]
                await cursor.execute(data_query, tuple(data_params))
                rows = await cursor.fetchall()

                return {
                    "data": rows,
                    "total": total_records,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages
                }
                
        except Exception as e:
            print(f"Error al obtener el listado de tarjetas: {e}")
            raise e
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
                            ttc.universidad,
                            ttc.tipo_asociado,
                            CONCAT(ttc.tipo_documento, " ", ttc.no_documento) AS documento,
                            ttc.correo,
                            DATE_FORMAT(ttc.fecha_emision, '%%Y-%%m-%%d %%H:%%i:%%s') AS fecha_emision,
                            ttc.no_expd,
                            CONCAT(ttc.nombres, " ",ttc.primer_apellido, " ", ttc.segundo_apellido) AS nombre_completo,
                            ttc.no_tarjeta,
                            ttc.estado_contador,
                            ttc.estado AS estado_tarjeta,
                            ttc.foto
                        FROM tn_tarjetavirtual_contadores ttc 
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
                            tts.resolucion,
                            DATE_FORMAT(tts.fecha_emision, '%%Y-%%m-%%d %%H:%%i:%%s') AS fecha_emision,
                            tts.tipo_asociado,
                            tts.nit,
                            tts.estado AS estado_tarjeta,
                            tts.estado_sociedad,
                            tts.representante_legal AS representante,
                            tts.foto  
                        FROM tn_tarjetavirtual_sociedades tts
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

    async def get_historial(self, tarjeta_id: int, client_id: Optional[int] = None, tipo: Optional[str] = None) -> Dict[str, Any]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 1. Obtener estados de la tarjeta
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
                estados = await cursor.fetchall()

                # 2. Obtener lecturas QR
                try:
                    await cursor.execute(
                        """
                        SELECT
                            id,
                            tarjeta_id,
                            endpoint,
                            metodo,
                            codigo_http,
                            ip,
                            DATE_FORMAT(fecha, '%%Y-%%m-%%d %%H:%%i') AS fecha
                        FROM tn_tarjetavirtual_lecturas_historial
                        WHERE tarjeta_id = %s
                        ORDER BY id DESC
                        """,
                        (tarjeta_id,)
                    )
                    lecturas = await cursor.fetchall()
                except Exception:
                    lecturas = []

                # 3. Intentar obtener datos básicos de la tarjeta (Contadores o Sociedades según tipo)
                tarjeta = None
                if tipo and (tipo.lower() == 'sociedad' or tipo.lower() == 'sociedades'):
                    await cursor.execute(
                        """
                        SELECT 
                            tts.id, 
                            tts.no_expd, 
                            tts.no_expd AS expediente, 
                            tts.nit, 
                            tts.nit AS documento, 
                            tts.razon_social, 
                            tts.razon_social AS solicitante, 
                            tts.inscripcion, 
                            tts.inscripcion AS matricula,
                            tts.representante_legal, 
                            tts.representante_legal AS representante, 
                            tts.estado AS estado_tarjeta, 
                            tts.estado AS tarjeta, 
                            DATE_FORMAT(tts.fecha_emision, '%%Y-%%m-%%d %%H:%%i:%%s') AS fecha_emision, 
                            tts.foto
                        FROM tn_tarjetavirtual_sociedades tts 
                        WHERE tts.id = %s
                        """,
                        (tarjeta_id,)
                    )
                    tarjeta = await cursor.fetchone()
                
                if not tarjeta:
                    await cursor.execute(
                        """
                        SELECT 
                            ttc.id, 
                            ttc.no_expd, 
                            ttc.no_expd AS expediente, 
                            CONCAT(IFNULL(ttc.tipo_documento,''), ' ', IFNULL(ttc.no_documento,'')) AS documento, 
                            ttc.no_documento,
                            ttc.tipo_documento,
                            CONCAT(IFNULL(ttc.nombres,''), ' ', IFNULL(ttc.primer_apellido,''), ' ', IFNULL(ttc.segundo_apellido,'')) AS nombre_completo, 
                            CONCAT(IFNULL(ttc.nombres,''), ' ', IFNULL(ttc.primer_apellido,''), ' ', IFNULL(ttc.segundo_apellido,'')) AS solicitante, 
                            ttc.no_tarjeta, 
                            ttc.no_tarjeta AS matricula, 
                            ttc.estado AS estado_tarjeta, 
                            ttc.estado AS tarjeta, 
                            ttc.correo, 
                            ttc.universidad, 
                            DATE_FORMAT(ttc.fecha_emision, '%%Y-%%m-%%d %%H:%%i:%%s') AS fecha_emision, 
                            ttc.foto
                        FROM tn_tarjetavirtual_contadores ttc 
                        WHERE ttc.id = %s
                        """,
                        (tarjeta_id,)
                    )
                    tarjeta = await cursor.fetchone()

                if not tarjeta:
                    await cursor.execute(
                        """
                        SELECT 
                            tts.id, 
                            tts.no_expd, 
                            tts.no_expd AS expediente, 
                            tts.nit, 
                            tts.nit AS documento, 
                            tts.razon_social, 
                            tts.razon_social AS solicitante, 
                            tts.inscripcion, 
                            tts.inscripcion AS matricula,
                            tts.representante_legal, 
                            tts.representante_legal AS representante, 
                            tts.estado AS estado_tarjeta, 
                            tts.estado AS tarjeta, 
                            DATE_FORMAT(tts.fecha_emision, '%%Y-%%m-%%d %%H:%%i:%%s') AS fecha_emision, 
                            tts.foto
                        FROM tn_tarjetavirtual_sociedades tts 
                        WHERE tts.id = %s
                        """,
                        (tarjeta_id,)
                    )
                    tarjeta = await cursor.fetchone()

                # Si no hay estados explícitos aún para este ID, generar registro inicial de emisión
                if not estados:
                    estados = [
                        {
                            "id": 1,
                            "tarjeta_id": tarjeta_id,
                            "estado": "Emitida",
                            "descripcion": "Credencial generada correctamente.",
                            "fecha": "Recientemente",
                            "realizado_por": "Sistema JCC"
                        }
                    ]

                return {
                    "tarjeta": tarjeta,
                    "estados": estados or [],
                    "lecturas": lecturas or []
                }
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
                    FROM tn_tarjetavirtual_config_validador
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
                    "SELECT id FROM tn_tarjetavirtual_config_validador WHERE client_id = %s LIMIT 1",
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
                        UPDATE tn_tarjetavirtual_config_validador SET
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
                        INSERT INTO tn_tarjetavirtual_config_validador (
                            client_id, val_foto, val_nombres, val_matricula,
                            val_numero_identificacion, val_codigo_tarjeta, val_estado
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (client_id, vf, vn, vm, vnum, vc, ve)
                    )
                return True
        finally:
            conn.close()

    async def get_columns_config(self, tipo_tarjeta: str = "contadores", client_id: Optional[int] = None) -> List[Dict[str, Any]]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT
                        key_name AS `key`,
                        label,
                        visible_defecto,
                        es_filtrable,
                        orden,
                        tipo_dato
                    FROM tn_tarjetavirtual_config_columnas_filtro_tarjetas
                    WHERE tipo_tarjeta = %s
                    ORDER BY orden ASC
                    """,
                    (tipo_tarjeta,)
                )
                rows = await cursor.fetchall()
                for row in rows:
                    row["visible_defecto"] = bool(row["visible_defecto"])
                    row["es_filtrable"] = bool(row["es_filtrable"])
                return rows
        finally:
            conn.close()

    # Buscar por tipo y cliente (Tabla Única Unificada)
    async def get_by_cliente_and_tipo(self, id_cliente: Optional[int], tipo_id: int, client_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        cid = client_id or id_cliente
        conn = await get_client_connection(cid)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT
                        id, tipo_id, version, publicado,
                        version AS version_actual,
                        CASE WHEN publicado = 1 THEN version ELSE NULL END AS version_publicada,
                        logo, patron, color_fondo, color_letra, fuente_letra,
                        usuario_creacion_id,
                        DATE_FORMAT(created_at, '%%Y-%%m-%%d %%H:%%i') AS created_at_formatted
                    FROM tn_tarjetavirtual_configuracion_branding
                    WHERE tipo_id = %s
                    ORDER BY publicado DESC, version DESC
                    LIMIT 1
                    """,
                    (tipo_id,),
                )
                return await cursor.fetchone()
        finally:
            conn.close()

    async def create_branding_credentials(self, branding_credencials_data: Dict[str, Any], client_id: Optional[int] = None) -> int:
        cid = client_id or branding_credencials_data.get("idCliente", 20001)
        tipo_id = int(branding_credencials_data.get("tipo_id", 1))
        conn = await get_client_connection(cid)
        cursor = None
        try:
            cursor = await conn.cursor()
            await cursor.execute("START TRANSACTION")
            
            await cursor.execute(
                "SELECT COALESCE(MAX(version), 0) FROM tn_tarjetavirtual_configuracion_branding WHERE tipo_id = %s",
                (tipo_id,)
            )
            max_row = await cursor.fetchone()
            next_version = (max_row[0] if max_row else 0) + 1
            
            is_published = 0
            pub_v = branding_credencials_data.get("version_publicada")
            if pub_v is not None and int(pub_v) == next_version:
                is_published = 1
                await cursor.execute(
                    "UPDATE tn_tarjetavirtual_configuracion_branding SET publicado = 0 WHERE tipo_id = %s",
                    (tipo_id,)
                )

            await cursor.execute(
                """
                INSERT INTO tn_tarjetavirtual_configuracion_branding (
                    tipo_id, version, publicado, logo, patron, color_fondo,
                    color_letra, fuente_letra, usuario_creacion_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    tipo_id,
                    next_version,
                    is_published,
                    branding_credencials_data.get("logo"),
                    branding_credencials_data.get("patron"),
                    branding_credencials_data.get("color_fondo"),
                    branding_credencials_data.get("color_letra"),
                    branding_credencials_data.get("fuente_letra"),
                    branding_credencials_data.get("usuario_creacion_id")
                )
            )
            
            branding_id = cursor.lastrowid
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
                        id, tipo_id, version, publicado,
                        version AS version_actual,
                        CASE WHEN publicado = 1 THEN version ELSE NULL END AS version_publicada,
                        logo, patron, color_fondo, color_letra, fuente_letra,
                        usuario_creacion_id,
                        DATE_FORMAT(created_at, '%%Y-%%m-%%d %%H:%%i') AS created_at_formatted
                    FROM tn_tarjetavirtual_configuracion_branding
                    WHERE id = %s OR tipo_id = %s
                    ORDER BY publicado DESC, version DESC
                    LIMIT 1
                    """,
                    (branding_credential_id, branding_credential_id)
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
                        id, tipo_id, version, publicado,
                        version AS version_publicada,
                        logo, patron, color_fondo, color_letra, fuente_letra,
                        usuario_creacion_id,
                        DATE_FORMAT(created_at, '%%Y-%%m-%%d %%H:%%i') AS created_at_formatted
                    FROM tn_tarjetavirtual_configuracion_branding
                    WHERE (tipo_id = %s OR id = %s) AND publicado = 1
                    ORDER BY version DESC
                    LIMIT 1
                    """,
                    (branding_credential_id, branding_credential_id)
                )
                row = await cursor.fetchone()
                
                if not row:
                    await cursor.execute(
                        """
                        SELECT
                            id, tipo_id, version, publicado,
                            version AS version_publicada,
                            logo, patron, color_fondo, color_letra, fuente_letra,
                            usuario_creacion_id,
                            DATE_FORMAT(created_at, '%%Y-%%m-%%d %%H:%%i') AS created_at_formatted
                        FROM tn_tarjetavirtual_configuracion_branding
                        WHERE tipo_id = %s OR id = %s
                        ORDER BY version DESC
                        LIMIT 1
                        """,
                        (branding_credential_id, branding_credential_id)
                    )
                    row = await cursor.fetchone()
                    
                return row
        except Exception as e:
            print(f"Error al obtener branding publicado: {e}")
            raise e
        finally:
            conn.close()

    async def update_branding_credentials(self, branding_id: int, update_data: Dict[str, Any], client_id: Optional[int] = None) -> bool:
        return await self.create_branding_credentials(update_data, client_id) > 0

    async def validate_version_exists(self, branding_id: int, version: int, client_id: Optional[int] = None) -> bool:
        """Valida si una versión específica existe en la tabla de branding"""
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM tn_tarjetavirtual_configuracion_branding
                    WHERE (tipo_id = %s OR id = %s) AND version = %s
                    """,
                    (branding_id, branding_id, version)
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
                    raise ValueError(f"La versión {version_to_publish} no existe en el registro (MS-3858)")
                
                await cursor.execute(
                    """
                    UPDATE tn_tarjetavirtual_configuracion_branding
                    SET publicado = 0
                    WHERE tipo_id = %s OR id = %s
                    """,
                    (branding_id, branding_id)
                )
                
                await cursor.execute(
                    """
                    UPDATE tn_tarjetavirtual_configuracion_branding
                    SET publicado = 1, updated_at = NOW()
                    WHERE (tipo_id = %s OR id = %s) AND version = %s
                    """,
                    (branding_id, branding_id, version_to_publish)
                )
        finally:
            conn.close()

    async def list_history_branding_credentials(
        self,
        branding_id: int,
        client_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:

        page_size = min(max(page_size, 1), 100)
        page = max(page, 1)
        offset = (page - 1) * page_size

        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM tn_tarjetavirtual_configuracion_branding
                    WHERE tipo_id = %s OR id = %s
                    """,
                    (branding_id, branding_id)
                )
                total_row = await cursor.fetchone()
                total = total_row["total"] if total_row else 0
                total_pages = math.ceil(total / page_size) if total > 0 else 0

                await cursor.execute(
                    """
                    SELECT
                        id,
                        tipo_id,
                        version,
                        publicado,
                        logo,
                        patron,
                        color_fondo,
                        color_letra,
                        fuente_letra,
                        DATE_FORMAT(created_at, '%%Y-%%m-%%d %%H:%%i') AS created_at_formatted
                    FROM tn_tarjetavirtual_configuracion_branding
                    WHERE tipo_id = %s OR id = %s
                    ORDER BY version DESC
                    LIMIT %s OFFSET %s
                    """,
                    (branding_id, branding_id, page_size, offset)
                )
                rows = await cursor.fetchall()

                return {
                    "data": rows,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages
                }
        finally:
            conn.close()

    async def exists_society(
        self,
        nit: str,
        client_id: Optional[int] = None,
    ) -> bool:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT 1
                    FROM tn_tarjetavirtual_sociedades
                    WHERE nit = %s
                    LIMIT 1
                    """,
                    (nit,),
                )
                result = await cursor.fetchone()
                return result is not None
        finally:
            conn.close()

    async def exists_accountant(
            self,
            no_documento: str,
            client_id: Optional[int] = None,
        ) -> bool:
            conn = await get_client_connection(client_id)
            try:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute(
                        """
                        SELECT 1
                        FROM tn_tarjetavirtual_contadores
                        WHERE no_documento = %s
                        LIMIT 1
                        """,
                        (no_documento,),
                    )
                    result = await cursor.fetchone()
                    return result is not None
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
                        tipo_asociado,
                        estado,
                        foto
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s
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
                    data.get("tipo_asociado") or data.get("tipo_asociado_id") or "Contador Público",
                    data.get("estado") or data.get("estado_tarjeta") or "Emitida",
                    data.get("foto")
                )
                
                await cursor.execute(query, values)
                new_id = cursor.lastrowid
                
                try:
                    hist_query = """
                        INSERT INTO tn_tarjetavirtual_estados_historial (tarjeta_id, estado, descripcion, realizado_por)
                        VALUES (%s, %s, %s, %s)
                    """
                    await cursor.execute(hist_query, (new_id, "Emitida", "Credencial generada correctamente.", "Sistema JCC"))
                except Exception as e_hist:
                    print(f"[TarjetasRepository] Warning: No se pudo crear historial inicial: {e_hist}")

                await conn.commit()
                return new_id
                
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
                        tipo_asociado,
                        estado,
                        foto,
                        representante_legal
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s
                    )
                """
                
                values = (
                    data.get("no_expd") or 0,
                    data.get("razon_social") or "Sin Razón Social",
                    data.get("nit") or "",
                    data.get("tipo_sociedad") or "SOCIEDAD DE CONTADORES",
                    data.get("inscripcion"),
                    data.get("fecha_radicacion"),
                    data.get("estado_sociedad") or "ACTIVO",
                    data.get("resolucion"),
                    data.get("fecha_resolucion"),
                    str(data.get("acta_jcc")) if data.get("acta_jcc") is not None else None,
                    data.get("estado_solicitud"),
                    data.get("tipo_solicitud"),
                    data.get("fecha_emision") or datetime.now(),
                    data.get("tipo_asociado") or data.get("tipo_asociado_id") or "Sociedad de Contadores Públicos",
                    data.get("estado") or data.get("estado_tarjeta") or "Emitida",
                    data.get("foto"),
                    data.get("representante_legal") or data.get("representante")
                )
                
                await cursor.execute(query, values)
                new_id = cursor.lastrowid
                
                try:
                    hist_query = """
                        INSERT INTO tn_tarjetavirtual_estados_historial (tarjeta_id, estado, descripcion, realizado_por)
                        VALUES (%s, %s, %s, %s)
                    """
                    await cursor.execute(hist_query, (new_id, "Emitida", "Credencial generada correctamente.", "Sistema JCC"))
                except Exception as e_hist:
                    print(f"[TarjetasRepository] Warning: No se pudo crear historial inicial: {e_hist}")

                await conn.commit()
                return new_id
                
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
                        tipo_tarjeta,
                        metodo,
                        url,
                        fecha_creacion,
                        tipo_asociado,
                        duracion_ms,
                        parametros_peticion,
                        cuerpo_respuesta_peticion
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """
                
                values = (
                    data.get("client_id"),
                    data.get("tipo_tarjeta") or data.get("tipo_id"),
                    data.get("metodo"),
                    data.get("url"),
                    data.get("fecha_creacion") or datetime.now(),
                    data.get("tipo_asociado") or data.get("tipo_asociado_id"),
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

    async def get_all_auditoria_api(
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
        
        page_size = min(max(page_size, 1), 100)
        page = max(page, 1)
        
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                
                # ============================================
                # Construcción dinámica de filtros WHERE
                # ============================================
                where_conditions = ["tapi.client_id = %s"]
                params = [client_id]
                
                if fecha_desde and fecha_desde.strip():
                    where_conditions.append("tapi.fecha_creacion >= %s")
                    params.append(fecha_desde.strip())
                
                if fecha_hasta and fecha_hasta.strip():
                    where_conditions.append("tapi.fecha_creacion <= %s")
                    params.append(fecha_hasta.strip())
                
                if endpoint and endpoint.strip() and endpoint != "Todos":
                    clean_ep = endpoint.strip().strip('/')
                    where_conditions.append("(tapi.url LIKE %s OR tapi.tipo_tarjeta LIKE %s)")
                    params.extend([f"%{clean_ep}%", f"%{clean_ep}%"])
                
                if tipo and tipo.strip() and tipo != "Todos":
                    clean_tipo = tipo.strip()
                    where_conditions.append("(tapi.tipo_asociado LIKE %s OR tapi.parametros_peticion LIKE %s)")
                    params.extend([f"%{clean_tipo}%", f'%"tipo": "{clean_tipo}"%'])
                
                if texto and texto.strip():
                    t = f"%{texto.strip()}%"
                    where_conditions.append("(tapi.parametros_peticion LIKE %s OR tapi.cuerpo_respuesta_peticion LIKE %s OR tapi.url LIKE %s)")
                    params.extend([t, t, t])

                if cambiar_estado is not None and cambiar_estado.strip() != "" and cambiar_estado != "Todos":
                    st_val = cambiar_estado.strip().lower()
                    if st_val == "true":
                        where_conditions.append("(tapi.parametros_peticion LIKE %s OR JSON_UNQUOTE(JSON_EXTRACT(tapi.parametros_peticion, '$.cambiarEstado')) = 'true')")
                        params.append('%"cambiarEstado": true%')
                    elif st_val == "false":
                        where_conditions.append("(tapi.parametros_peticion LIKE %s OR JSON_UNQUOTE(JSON_EXTRACT(tapi.parametros_peticion, '$.cambiarEstado')) = 'false')")
                        params.append('%"cambiarEstado": false%')
                
                where_clause = " AND ".join(where_conditions)
                
                # ============================================
                # 1. Consulta de conteo total
                # ============================================
                count_query = f"""
                    SELECT COUNT(*) as total
                    FROM tn_tarjetavirtual_auditoria_api tapi
                    WHERE {where_clause};
                """
                await cursor.execute(count_query, tuple(params))
                count_result = await cursor.fetchone()
                total_records = count_result['total'] if count_result else 0
                
                total_pages = math.ceil(total_records / page_size) if total_records > 0 else 0
                
                if total_records == 0:
                    return {
                        "data": [],
                        "total": 0,
                        "page": page,
                        "page_size": page_size,
                        "total_pages": 0
                    }
                
                # ============================================
                # 2. Consulta principal con LIMIT y OFFSET
                # ============================================
                offset = (page - 1) * page_size
                
                data_query = f"""
                    SELECT
                        tapi.id,
                        DATE_FORMAT(tapi.fecha_creacion, '%%Y-%%m-%%d %%H:%%i') AS fecha_hora,
                        tapi.url AS endpoint,
                        tapi.metodo,
                        tapi.tipo_asociado AS tipo,
                        tapi.duracion_ms,
                        tapi.url,
                        tapi.parametros_peticion,
                        tapi.cuerpo_respuesta_peticion
                    FROM tn_tarjetavirtual_auditoria_api tapi
                    WHERE {where_clause}
                    ORDER BY tapi.fecha_creacion DESC
                    LIMIT %s OFFSET %s;
                """
                
                data_params = tuple(params) + (page_size, offset)
                await cursor.execute(data_query, data_params)
                rows = await cursor.fetchall()
                
                # Parseo de campos JSON
                for item in rows:
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
                
                return {
                    "data": rows,
                    "total": total_records,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages
                }
                
        except Exception as e:
            print(f"Error al obtener el listado de auditoría API: {e}")
            raise e
        finally:
            conn.close()

    # =========================================================================
    # GESTIÓN DE LOTES Y COLA DE EMISIÓN MASIVA (HU-JCC-006)
    # =========================================================================

    async def create_emision_lote(
        self,
        client_id: int,
        tipo_tarjeta: str,
        tipo_tramite: str,
        total_registros: int,
        archivo_nombre: Optional[str] = None,
        creado_por: Optional[str] = None,
    ) -> int:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cursor:
                query = """
                    INSERT INTO tn_tarjetavirtual_emision_lotes (
                        client_id, tipo_tarjeta, tipo_tramite, archivo_nombre,
                        total_registros, procesados, exitosos, duplicados, fallidos,
                        estado, creado_por, fecha_creacion
                    ) VALUES (%s, %s, %s, %s, %s, 0, 0, 0, 0, 'PENDIENTE', %s, NOW())
                """
                await cursor.execute(query, (
                    client_id, tipo_tarjeta, tipo_tramite, archivo_nombre,
                    total_registros, creado_por
                ))
                await conn.commit()
                return cursor.lastrowid
        finally:
            conn.close()

    async def insert_emision_lote_items(
        self,
        lote_id: int,
        documentos: List[str],
        client_id: Optional[int] = None
    ) -> None:
        if not documentos:
            return
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cursor:
                query = """
                    INSERT INTO tn_tarjetavirtual_emision_lote_items (
                        lote_id, documento_o_nit, resultado
                    ) VALUES (%s, %s, 'PENDIENTE')
                """
                values = [(lote_id, doc.strip()) for doc in documentos if doc.strip()]
                if values:
                    await cursor.executemany(query, values)
                    await conn.commit()
        finally:
            conn.close()

    async def update_emision_lote_progress(
        self,
        lote_id: int,
        procesados: int,
        exitosos: int,
        duplicados: int,
        fallidos: int,
        estado: str,
        mensaje: Optional[str] = None,
        finalizado: bool = False,
        client_id: Optional[int] = None
    ) -> None:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cursor:
                if finalizado:
                    query = """
                        UPDATE tn_tarjetavirtual_emision_lotes
                        SET procesados = %s, exitosos = %s, duplicados = %s, fallidos = %s,
                            estado = %s, mensaje = %s, fecha_fin = NOW()
                        WHERE id = %s
                    """
                    await cursor.execute(query, (procesados, exitosos, duplicados, fallidos, estado, mensaje, lote_id))
                else:
                    query = """
                        UPDATE tn_tarjetavirtual_emision_lotes
                        SET procesados = %s, exitosos = %s, duplicados = %s, fallidos = %s,
                            estado = %s, mensaje = %s
                        WHERE id = %s
                    """
                    await cursor.execute(query, (procesados, exitosos, duplicados, fallidos, estado, mensaje, lote_id))
                await conn.commit()
        finally:
            conn.close()

    async def update_emision_lote_item(
        self,
        lote_id: int,
        documento: str,
        resultado: str,
        tarjeta_id: Optional[int] = None,
        mensaje_detalle: Optional[str] = None,
        client_id: Optional[int] = None
    ) -> None:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cursor:
                query = """
                    UPDATE tn_tarjetavirtual_emision_lote_items
                    SET resultado = %s, tarjeta_id = %s, mensaje_detalle = %s
                    WHERE lote_id = %s AND documento_o_nit = %s
                """
                await cursor.execute(query, (resultado, tarjeta_id, mensaje_detalle, lote_id, documento))
                await conn.commit()
        finally:
            conn.close()

    async def get_emision_lote(self, lote_id: int, client_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = "SELECT * FROM tn_tarjetavirtual_emision_lotes WHERE id = %s"
                await cursor.execute(query, (lote_id,))
                return await cursor.fetchone()
        finally:
            conn.close()

    async def get_emision_lote_items(
        self,
        lote_id: int,
        client_id: Optional[int] = None,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = """
                    SELECT * FROM tn_tarjetavirtual_emision_lote_items
                    WHERE lote_id = %s
                    ORDER BY id ASC
                    LIMIT %s
                """
                await cursor.execute(query, (lote_id, limit))
                return await cursor.fetchall()
        finally:
            conn.close()

    async def get_pending_queue_items(
        self,
        limit: int = 10,
        client_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = """
                    SELECT 
                        i.id,
                        i.lote_id,
                        l.client_id,
                        i.documento_o_nit,
                        i.resultado,
                        l.tipo_tarjeta,
                        l.tipo_tramite
                    FROM tn_tarjetavirtual_emision_lote_items i
                    INNER JOIN tn_tarjetavirtual_emision_lotes l ON i.lote_id = l.id
                    WHERE i.resultado = 'PENDIENTE' AND l.estado IN ('EN_COLA', 'PENDIENTE', 'PROCESANDO')
                    ORDER BY i.id ASC
                    LIMIT %s
                """
                await cursor.execute(query, (limit,))
                return await cursor.fetchall()
        finally:
            conn.close()

    async def claim_queue_item(
        self,
        item_id: int,
        lote_id: int,
        client_id: Optional[int] = None
    ) -> None:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE tn_tarjetavirtual_emision_lote_items SET resultado = 'PROCESANDO' WHERE id = %s",
                    (item_id,)
                )
                await cursor.execute(
                    "UPDATE tn_tarjetavirtual_emision_lotes SET estado = 'PROCESANDO' WHERE id = %s AND estado IN ('EN_COLA', 'PENDIENTE')",
                    (lote_id,)
                )
                await conn.commit()
        finally:
            conn.close()

    async def update_queue_item_result(
        self,
        item_id: int,
        lote_id: int,
        resultado: str,
        tarjeta_id: Optional[int] = None,
        mensaje_detalle: Optional[str] = None,
        client_id: Optional[int] = None
    ) -> None:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    UPDATE tn_tarjetavirtual_emision_lote_items
                    SET resultado = %s, tarjeta_id = %s, mensaje_detalle = %s, fecha_proceso = NOW()
                    WHERE id = %s
                    """,
                    (resultado, tarjeta_id, mensaje_detalle, item_id)
                )
                col_inc = "exitosos = exitosos + 1" if resultado == "emitido_exitosamente" else (
                    "duplicados = duplicados + 1" if resultado == "omitido_duplicado" else "fallidos = fallidos + 1"
                )
                await cursor.execute(
                    f"""
                    UPDATE tn_tarjetavirtual_emision_lotes
                    SET procesados = procesados + 1, {col_inc}
                    WHERE id = %s
                    """,
                    (lote_id,)
                )
                await conn.commit()
        finally:
            conn.close()

    async def finalize_lote_if_completed(
        self,
        lote_id: int,
        client_id: Optional[int] = None
    ) -> Optional[str]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT COUNT(*) as pendientes
                    FROM tn_tarjetavirtual_emision_lote_items
                    WHERE lote_id = %s AND resultado IN ('PENDIENTE', 'PROCESANDO')
                    """,
                    (lote_id,)
                )
                res = await cursor.fetchone()
                if res and res["pendientes"] == 0:
                    await cursor.execute(
                        "SELECT total_registros, exitosos, duplicados, fallidos FROM tn_tarjetavirtual_emision_lotes WHERE id = %s",
                        (lote_id,)
                    )
                    lote = await cursor.fetchone()
                    exitosos = lote["exitosos"] if lote else 0
                    duplicados = lote["duplicados"] if lote else 0
                    fallidos = lote["fallidos"] if lote else 0
                    estado_final = "FINALIZADO" if (exitosos > 0 or duplicados > 0) else "FALLIDO"
                    msg = f"Lote completado: {exitosos} emitidos, {duplicados} omitidos por duplicado, {fallidos} no procesados o fallidos."
                    await cursor.execute(
                        """
                        UPDATE tn_tarjetavirtual_emision_lotes
                        SET estado = %s, mensaje = %s, fecha_fin = NOW()
                        WHERE id = %s
                        """,
                        (estado_final, msg, lote_id)
                    )
                    await conn.commit()
                    return estado_final
                return None
        finally:
            conn.close()

    async def get_queue_config(self, client_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        conn = await get_client_connection(client_id)
        try:
            cid = client_id or int(os.getenv("CLIENT_ID", "20001"))
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = "SELECT * FROM tn_tarjetavirtual_config_colas WHERE client_id = %s"
                await cursor.execute(query, (cid,))
                return await cursor.fetchone()
        finally:
            conn.close()

    async def save_queue_config(self, client_id: Optional[int], config_data: Dict[str, Any]) -> Dict[str, Any]:
        conn = await get_client_connection(client_id)
        try:
            cid = client_id or int(os.getenv("CLIENT_ID", "20001"))
            async with conn.cursor() as cursor:
                query = """
                    INSERT INTO tn_tarjetavirtual_config_colas (
                        client_id, worker_enabled, poll_interval_seconds, batch_size,
                        item_delay_seconds, circuit_breaker_fail_threshold,
                        circuit_breaker_cooldown_seconds, max_retries_per_item,
                        scheduler_enabled, scheduler_interval_seconds, scheduler_auto_enqueue
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        worker_enabled = VALUES(worker_enabled),
                        poll_interval_seconds = VALUES(poll_interval_seconds),
                        batch_size = VALUES(batch_size),
                        item_delay_seconds = VALUES(item_delay_seconds),
                        circuit_breaker_fail_threshold = VALUES(circuit_breaker_fail_threshold),
                        circuit_breaker_cooldown_seconds = VALUES(circuit_breaker_cooldown_seconds),
                        max_retries_per_item = VALUES(max_retries_per_item),
                        scheduler_enabled = VALUES(scheduler_enabled),
                        scheduler_interval_seconds = VALUES(scheduler_interval_seconds),
                        scheduler_auto_enqueue = VALUES(scheduler_auto_enqueue)
                """
                worker_en = config_data.get("worker_enabled", config_data.get("habilitado", True))
                poll_int = config_data.get("poll_interval_seconds", config_data.get("intervalo_sondeo_segundos", 5.0))
                b_size = config_data.get("batch_size", config_data.get("tamano_lote", 10))
                item_delay = config_data.get("item_delay_seconds", config_data.get("delay_por_item_segundos", 0.05))
                cb_fail = config_data.get("circuit_breaker_fail_threshold", config_data.get("circuit_breaker_max_fallos", 3))
                cb_cool = config_data.get("circuit_breaker_cooldown_seconds", config_data.get("circuit_breaker_cooldown_segundos", 60))
                sched_sec = config_data.get("scheduler_interval_seconds")
                if not sched_sec and "scheduler_intervalo_minutos" in config_data:
                    sched_sec = int(config_data["scheduler_intervalo_minutos"]) * 60
                elif not sched_sec:
                    sched_sec = 3600

                await cursor.execute(query, (
                    cid,
                    1 if worker_en else 0,
                    float(poll_int),
                    int(b_size),
                    float(item_delay),
                    int(cb_fail),
                    int(cb_cool),
                    int(config_data.get("max_retries_per_item", 2)),
                    1 if config_data.get("scheduler_enabled", True) else 0,
                    int(sched_sec),
                    1 if config_data.get("scheduler_auto_enqueue", True) else 0
                ))
                await conn.commit()
            return await self.get_queue_config(cid)
        finally:
            conn.close()

    async def get_emision_lotes_list(
        self,
        client_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 10,
        estado: Optional[str] = None,
        tipo_tarjeta: Optional[str] = None
    ) -> Dict[str, Any]:
        conn = await get_client_connection(client_id)
        try:
            cid = client_id or int(os.getenv("CLIENT_ID", "20001"))
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                where_clauses = ["client_id = %s"]
                params: List[Any] = [cid]
                if estado and estado != "TODOS":
                    where_clauses.append("estado = %s")
                    params.append(estado)
                if tipo_tarjeta and tipo_tarjeta != "TODOS":
                    where_clauses.append("tipo_tarjeta = %s")
                    params.append(tipo_tarjeta)

                where_sql = " AND ".join(where_clauses)
                count_query = f"SELECT COUNT(*) as total FROM tn_tarjetavirtual_emision_lotes WHERE {where_sql}"
                await cursor.execute(count_query, tuple(params))
                total = (await cursor.fetchone())["total"]

                offset = (page - 1) * page_size
                query = f"""
                    SELECT 
                        id, client_id, tipo_tarjeta, tipo_tramite, total_registros,
                        procesados, exitosos, duplicados, fallidos, estado, archivo_nombre,
                        mensaje, creado_por,
                        DATE_FORMAT(fecha_creacion, '%%Y-%%m-%%d %%H:%%i:%%s') as fecha_creacion,
                        DATE_FORMAT(fecha_fin, '%%Y-%%m-%%d %%H:%%i:%%s') as fecha_fin,
                        TIMESTAMPDIFF(SECOND, fecha_creacion, fecha_fin) as tiempo_proceso_segundos
                    FROM tn_tarjetavirtual_emision_lotes
                    WHERE {where_sql}
                    ORDER BY id DESC
                    LIMIT %s OFFSET %s
                """
                query_params = list(params) + [page_size, offset]
                await cursor.execute(query, tuple(query_params))
                items = await cursor.fetchall()

                return {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
                    "items": items
                }
        finally:
            conn.close()

    async def get_queue_metrics(self, client_id: Optional[int] = None) -> Dict[str, Any]:
        conn = await get_client_connection(client_id)
        try:
            cid = client_id or int(os.getenv("CLIENT_ID", "20001"))
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT 
                        COUNT(*) as total_lotes,
                        COALESCE(SUM(CASE WHEN estado IN ('EN_COLA', 'PROCESANDO', 'PENDIENTE') THEN 1 ELSE 0 END), 0) as lotes_activos,
                        COALESCE(SUM(CASE WHEN estado = 'FINALIZADO' THEN 1 ELSE 0 END), 0) as lotes_completados,
                        COALESCE(SUM(CASE WHEN estado = 'FALLIDO' THEN 1 ELSE 0 END), 0) as lotes_fallidos,
                        COALESCE(SUM(total_registros), 0) as total_historico,
                        COALESCE(SUM(exitosos), 0) as total_exitosos,
                        COALESCE(SUM(duplicados), 0) as total_duplicados,
                        COALESCE(SUM(fallidos), 0) as total_fallidos
                    FROM tn_tarjetavirtual_emision_lotes WHERE client_id = %s
                    """,
                    (cid,)
                )
                metricas_lotes = await cursor.fetchone() or {}

                await cursor.execute(
                    """
                    SELECT COUNT(*) as items_pendientes
                    FROM tn_tarjetavirtual_emision_lote_items i
                    INNER JOIN tn_tarjetavirtual_emision_lotes l ON i.lote_id = l.id
                    WHERE l.client_id = %s AND i.resultado = 'PENDIENTE'
                    """,
                    (cid,)
                )
                metricas_items = await cursor.fetchone() or {}

                return {
                    "total_lotes": int(metricas_lotes.get("total_lotes") or 0),
                    "lotes_activos": int(metricas_lotes.get("lotes_activos") or 0),
                    "lotes_completados": int(metricas_lotes.get("lotes_completados") or 0),
                    "lotes_fallidos": int(metricas_lotes.get("lotes_fallidos") or 0),
                    "total_historico_registros": int(metricas_lotes.get("total_historico") or 0),
                    "total_exitosos": int(metricas_lotes.get("total_exitosos") or 0),
                    "total_duplicados": int(metricas_lotes.get("total_duplicados") or 0),
                    "total_fallidos": int(metricas_lotes.get("total_fallidos") or 0),
                    "items_pendientes_en_cola": int(metricas_items.get("items_pendientes") or 0)
                }
        finally:
            conn.close()

    async def create_sincronizacion_log(self, data: Dict[str, Any], client_id: Optional[int] = None) -> int:
        cid = client_id or int(os.getenv("CLIENT_ID", "20001"))
        conn = await get_client_connection(cid)
        try:
            async with conn.cursor() as cursor:
                query = """
                    INSERT INTO tn_tarjetavirtual_sincronizacion_logs (
                        origen, fecha_inicio, fecha_fin, duracion_ms,
                        estado, total_encolados, contadores_encolados, sociedades_encoladas,
                        errores_count, detalle
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                values = (
                    data.get("origen", "PROGRAMADO"),
                    data.get("fecha_inicio") or datetime.now(),
                    data.get("fecha_fin") or datetime.now(),
                    int(data.get("duracion_ms", 0)),
                    data.get("estado", "EXITOSO"),
                    int(data.get("total_encolados", 0)),
                    int(data.get("contadores_encolados", 0)),
                    int(data.get("sociedades_encoladas", 0)),
                    int(data.get("errores_count", 0)),
                    (data.get("detalle") or "")[:500]
                )
                await cursor.execute(query, values)
                await conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"[TarjetasRepository] Error al insertar sincronizacion_log: {e}")
            return 0
        finally:
            conn.close()

    async def get_sincronizacion_logs(self, client_id: Optional[int] = None, limit: int = 15) -> List[Dict[str, Any]]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = """
                    SELECT id, origen, fecha_inicio, fecha_fin, duracion_ms,
                           estado, total_encolados, contadores_encolados, sociedades_encoladas,
                           errores_count, detalle, creado_en
                    FROM tn_tarjetavirtual_sincronizacion_logs
                    ORDER BY id DESC
                    LIMIT %s
                """
                await cursor.execute(query, (limit,))
                rows = await cursor.fetchall()
                result = []
                for r in rows:
                    result.append({
                        "id": r["id"],
                        "origen": r["origen"],
                        "fecha_inicio": r["fecha_inicio"].isoformat() if hasattr(r["fecha_inicio"], "isoformat") and r["fecha_inicio"] else str(r["fecha_inicio"]),
                        "fecha_fin": r["fecha_fin"].isoformat() if hasattr(r["fecha_fin"], "isoformat") and r["fecha_fin"] else (str(r["fecha_fin"]) if r["fecha_fin"] else None),
                        "duracion_ms": r["duracion_ms"],
                        "estado": r["estado"],
                        "total_encolados": r["total_encolados"],
                        "contadores_encolados": r["contadores_encolados"],
                        "sociedades_encoladas": r["sociedades_encoladas"],
                        "errores_count": r["errores_count"],
                        "detalle": r["detalle"],
                        "creado_en": r["creado_en"].isoformat() if hasattr(r["creado_en"], "isoformat") and r["creado_en"] else str(r["creado_en"])
                    })
                return result
        finally:
            conn.close()

    async def get_ultima_sincronizacion_log(self, client_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        logs = await self.get_sincronizacion_logs(client_id, limit=1)
        return logs[0] if logs else None
