import aiomysql
from typing import List, Dict, Any, Optional
from app.core.database import get_client_connection

class NotificacionesRepository:
    """
    Repositorio para el módulo de Notificaciones (HU-JCC-020).
    Persistencia transaccional en la tabla tn_tarjetavirtual_notificaciones.
    """

    async def list_notificaciones(
        self,
        client_id: Optional[int] = None,
        canal: Optional[str] = None,
        estado: Optional[str] = None,
        audiencia: Optional[str] = None,
        texto: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = """
                    SELECT 
                        id,
                        client_id,
                        titulo,
                        mensaje,
                        tipo,
                        canal,
                        audiencia,
                        destinatarios,
                        fecha,
                        estado,
                        creado_por AS creadoPor,
                        hora_inicio,
                        hora_fin,
                        max_diario,
                        recurrencia,
                        respetar_rango,
                        CAST(fecha_creacion AS CHAR) AS fecha_creacion
                    FROM tn_tarjetavirtual_notificaciones
                    WHERE client_id = %s
                """
                params = [client_id]

                if canal and canal.strip():
                    query += " AND canal = %s"
                    params.append(canal.strip())

                if estado and estado.strip():
                    query += " AND estado = %s"
                    params.append(estado.strip())

                if audiencia and audiencia.strip():
                    query += " AND audiencia = %s"
                    params.append(audiencia.strip())

                if texto and texto.strip():
                    query += " AND (titulo LIKE %s OR mensaje LIKE %s)"
                    like_pattern = f"%{texto.strip()}%"
                    params.extend([like_pattern, like_pattern])

                query += " ORDER BY id DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])

                await cursor.execute(query, tuple(params))
                rows = await cursor.fetchall()
                return list(rows) if rows else []
        finally:
            conn.close()

    async def create_notificacion(
        self,
        data: Dict[str, Any],
        client_id: Optional[int] = None
    ) -> int:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cursor:
                query = """
                    INSERT INTO tn_tarjetavirtual_notificaciones (
                        client_id,
                        titulo,
                        mensaje,
                        tipo,
                        canal,
                        audiencia,
                        destinatarios,
                        fecha,
                        estado,
                        creado_por,
                        hora_inicio,
                        hora_fin,
                        max_diario,
                        recurrencia,
                        respetar_rango
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """
                cid = client_id or data.get("client_id")
                params = (
                    cid,
                    data.get("titulo"),
                    data.get("mensaje"),
                    data.get("tipo", "Informativa"),
                    data.get("canal"),
                    data.get("audiencia", "Todos"),
                    int(data.get("destinatarios") or 0),
                    data.get("fecha"),
                    data.get("estado", "Programada"),
                    data.get("creadoPor") or data.get("creado_por", "Administrador"),
                    data.get("hora_inicio", "07:00"),
                    data.get("hora_fin", "17:00"),
                    int(data.get("max_diario") or 2),
                    data.get("recurrencia", "No repetir"),
                    1 if data.get("respetar_rango", True) else 0
                )
                await cursor.execute(query, params)
                await conn.commit()
                return cursor.lastrowid
        finally:
            conn.close()

    async def get_notificacion_by_id(
        self,
        notif_id: int,
        client_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = """
                    SELECT 
                        id,
                        client_id,
                        titulo,
                        mensaje,
                        tipo,
                        canal,
                        audiencia,
                        destinatarios,
                        fecha,
                        estado,
                        creado_por AS creadoPor,
                        hora_inicio,
                        hora_fin,
                        max_diario,
                        recurrencia,
                        respetar_rango,
                        CAST(fecha_creacion AS CHAR) AS fecha_creacion
                    FROM tn_tarjetavirtual_notificaciones
                    WHERE id = %s AND client_id = %s
                """
                await cursor.execute(query, (notif_id, client_id))
                return await cursor.fetchone()
        finally:
            conn.close()
