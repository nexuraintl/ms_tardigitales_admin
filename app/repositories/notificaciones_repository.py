import aiomysql
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.core.database import get_client_connection


class NotificacionesRepository:
    """
    Repositorio para el módulo de Notificaciones (HU-JCC-020).
    Persistencia transaccional en la tabla tn_tarjetavirtual_notificaciones.
    """

    async def _ensure_schedule_columns(self, cursor) -> None:
        """Asegura de forma idempotente las columnas proxima_ejecucion y ultimo_envio."""
        await cursor.execute("SHOW COLUMNS FROM tn_tarjetavirtual_notificaciones")
        existing = {row[0] if not isinstance(row, dict) else row["Field"] for row in (await cursor.fetchall() or [])}
        if "proxima_ejecucion" not in existing:
            await cursor.execute(
                "ALTER TABLE tn_tarjetavirtual_notificaciones ADD COLUMN proxima_ejecucion DATETIME NULL AFTER respetar_rango"
            )
        if "ultimo_envio" not in existing:
            await cursor.execute(
                "ALTER TABLE tn_tarjetavirtual_notificaciones ADD COLUMN ultimo_envio DATETIME NULL AFTER proxima_ejecucion"
            )

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

    async def count_tarjetas_activas_por_audiencia(
        self,
        audiencia: Optional[str] = "Todos",
        client_id: Optional[int] = None
    ) -> int:
        """Cuenta las tarjetas digitales en estado Activa según la audiencia objetivo."""
        aud = (audiencia or "Todos").strip().lower()
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cursor:
                total = 0
                if aud in ("contadores", "contador", "todos", ""):
                    await cursor.execute(
                        "SELECT COUNT(*) FROM tn_tarjetavirtual_contadores WHERE UPPER(TRIM(estado)) = 'ACTIVA'"
                    )
                    row = await cursor.fetchone()
                    total += int(row[0]) if row and row[0] else 0

                if aud in ("sociedades", "sociedad", "todos", ""):
                    await cursor.execute(
                        "SELECT COUNT(*) FROM tn_tarjetavirtual_sociedades WHERE UPPER(TRIM(estado)) = 'ACTIVA'"
                    )
                    row = await cursor.fetchone()
                    total += int(row[0]) if row and row[0] else 0

                return total
        finally:
            conn.close()

    async def count_entregadas_hoy(
        self,
        canal: str,
        audiencia: str,
        hoy_str: str,
        client_id: Optional[int] = None,
    ) -> int:
        """Cuenta cuántas notificaciones ya fueron entregadas hoy para un canal/audiencia."""
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cursor:
                await self._ensure_schedule_columns(cursor)
                await cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM tn_tarjetavirtual_notificaciones
                    WHERE client_id = %s
                      AND canal = %s
                      AND audiencia = %s
                      AND estado = 'Entregada'
                      AND (
                          DATE(ultimo_envio) = %s
                          OR (ultimo_envio IS NULL AND DATE(fecha_creacion) = %s)
                      )
                    """,
                    (client_id, canal, audiencia, hoy_str, hoy_str),
                )
                row = await cursor.fetchone()
                return int(row[0]) if row and row[0] else 0
        finally:
            conn.close()

    async def get_active_fcm_tokens_by_tipo(
        self,
        client_id: Optional[int] = None
    ) -> Dict[str, List[str]]:
        """Obtiene los tokens FCM activos agrupados por tipo_tarjeta para sincronizar topics."""
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    """
                    SELECT DISTINCT tipo_tarjeta, fcm_token
                    FROM tn_tarjetavirtual_dispositivos
                    WHERE estado = 'activo'
                      AND fcm_token IS NOT NULL
                      AND TRIM(fcm_token) <> ''
                    """
                )
                rows = await cursor.fetchall() or []
                grouped: Dict[str, List[str]] = {"contadores": [], "sociedades": []}
                for r in rows:
                    tipo = str(r.get("tipo_tarjeta") or "").strip().lower()
                    tok = str(r.get("fcm_token") or "").strip()
                    if not tok:
                        continue
                    if tipo in grouped:
                        grouped[tipo].append(tok)
                return grouped
        finally:
            conn.close()

    async def mark_fcm_token_inactive(
        self,
        fcm_token: str,
        client_id: Optional[int] = None
    ) -> None:
        """Marca como inactivo un token FCM que Firebase reportó como UNREGISTERED."""
        if not fcm_token:
            return
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE tn_tarjetavirtual_dispositivos SET estado = 'inactivo' WHERE fcm_token = %s",
                    (fcm_token,),
                )
                await conn.commit()
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
                await self._ensure_schedule_columns(cursor)
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
                        respetar_rango,
                        proxima_ejecucion,
                        ultimo_envio
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
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
                    1 if data.get("respetar_rango", True) else 0,
                    data.get("proxima_ejecucion"),
                    data.get("ultimo_envio"),
                )
                await cursor.execute(query, params)
                await conn.commit()
                return cursor.lastrowid
        finally:
            conn.close()

    async def claim_due_notificaciones(
        self,
        now_dt: datetime,
        client_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Obtiene y reserva de forma atómica ('En proceso') las notificaciones programadas
        cuya proxima_ejecucion ya venció (<= now_dt) para evitar envíos duplicados.
        """
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await self._ensure_schedule_columns(cursor)
                await cursor.execute(
                    """
                    SELECT
                        id, client_id, titulo, mensaje, tipo, canal, audiencia,
                        destinatarios, fecha, estado, creado_por AS creadoPor,
                        hora_inicio, hora_fin, max_diario, recurrencia,
                        respetar_rango, proxima_ejecucion, ultimo_envio
                    FROM tn_tarjetavirtual_notificaciones
                    WHERE client_id = %s
                      AND estado = 'Programada'
                      AND proxima_ejecucion IS NOT NULL
                      AND proxima_ejecucion <= %s
                    ORDER BY proxima_ejecucion ASC, id ASC
                    LIMIT %s
                    """,
                    (client_id, now_dt, limit),
                )
                rows = list(await cursor.fetchall() or [])
                if not rows:
                    return []

                claimed: List[Dict[str, Any]] = []
                for row in rows:
                    await cursor.execute(
                        """
                        UPDATE tn_tarjetavirtual_notificaciones
                        SET estado = 'En proceso'
                        WHERE id = %s AND estado = 'Programada'
                        """,
                        (row["id"],),
                    )
                    if cursor.rowcount == 1:
                        claimed.append(row)
                await conn.commit()
                return claimed
        finally:
            conn.close()

    async def update_notificacion_ejecucion(
        self,
        notif_id: int,
        estado: str,
        destinatarios: Optional[int] = None,
        proxima_ejecucion: Optional[datetime] = None,
        ultimo_envio: Optional[datetime] = None,
        fecha_display: Optional[str] = None,
        client_id: Optional[int] = None,
    ) -> None:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cursor:
                await self._ensure_schedule_columns(cursor)
                sets = ["estado = %s", "proxima_ejecucion = %s"]
                params: List[Any] = [estado, proxima_ejecucion]
                if destinatarios is not None:
                    sets.append("destinatarios = %s")
                    params.append(int(destinatarios))
                if ultimo_envio is not None:
                    sets.append("ultimo_envio = %s")
                    params.append(ultimo_envio)
                if fecha_display is not None:
                    sets.append("fecha = %s")
                    params.append(fecha_display)
                params.append(notif_id)
                await cursor.execute(
                    f"UPDATE tn_tarjetavirtual_notificaciones SET {', '.join(sets)} WHERE id = %s",
                    tuple(params),
                )
                await conn.commit()
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
