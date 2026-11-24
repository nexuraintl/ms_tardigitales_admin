import base64
import json
from typing import List, Dict, Any, Optional
from app.core.database import get_client_connection


def _encode_pdf_blob(pdf_bytes: Optional[bytes]) -> Optional[str]:
    """Codifica el PDF a texto ASCII Base64 para evitar el bug escape_bytes_prefixed de aiomysql."""
    if not pdf_bytes:
        return None
    if isinstance(pdf_bytes, (bytes, bytearray)):
        return base64.b64encode(bytes(pdf_bytes)).decode("ascii")
    if isinstance(pdf_bytes, str):
        return pdf_bytes.strip() or None
    return None


def _decode_pdf_blob(raw: Any) -> Optional[bytes]:
    """Decodifica contenido_pdf desde Base64 ASCII o bytes PDF crudos."""
    if not raw:
        return None
    if isinstance(raw, memoryview):
        raw = raw.tobytes()
    if isinstance(raw, (bytes, bytearray)):
        b = bytes(raw)
        if b.startswith(b"%PDF"):
            return b
        try:
            decoded = base64.b64decode(b)
            if decoded.startswith(b"%PDF"):
                return decoded
        except Exception:
            pass
        return b
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return None
        try:
            return base64.b64decode(s)
        except Exception:
            return None
    return None

class CertificadosRepository:
    def __init__(self):
        pass

    async def get_all(
        self,
        client_id: Optional[int] = None,
        search: Optional[str] = None,
        tipo: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        conn = await get_client_connection(client_id)
        try:
            where_clauses = ["1=1"]
            params = []

            if tipo and tipo.lower() != "todos":
                where_clauses.append("tipo = %s")
                params.append(tipo.lower())

            if search and search.strip():
                clean_search = f"%{search.strip()}%"
                where_clauses.append("(n_certificado LIKE %s OR documento LIKE %s OR nombre_titular LIKE %s)")
                params.extend([clean_search, clean_search, clean_search])

            where_sql = " AND ".join(where_clauses)

            # Conteo total
            async with conn.cursor() as cur:
                count_sql = f"SELECT COUNT(*) FROM tn_tarjetavirtual_certificados_expedidos WHERE {where_sql}"
                await cur.execute(count_sql, tuple(params))
                total_row = await cur.fetchone()
                total = total_row[0] if total_row else 0

                # Paginación
                offset = (max(page, 1) - 1) * page_size
                query_sql = f"""
                    SELECT id, client_id, n_certificado, tipo, documento, nombre_titular, 
                           fecha_generacion, fecha_firma_onac, estado, payload_detalles, origen, created_at
                    FROM tn_tarjetavirtual_certificados_expedidos
                    WHERE {where_sql}
                    ORDER BY id DESC
                    LIMIT %s OFFSET %s
                """
                exec_params = list(params) + [page_size, offset]
                await cur.execute(query_sql, tuple(exec_params))
                rows = await cur.fetchall()

                items = []
                for r in rows:
                    raw_detalles = r[9]
                    detalles = json.loads(raw_detalles) if isinstance(raw_detalles, str) else (raw_detalles or {})
                    items.append({
                        "id": str(r[0]),
                        "client_id": r[1],
                        "n_certificado": r[2],
                        "tipo": r[3],
                        "documento": r[4],
                        "nombre_titular": r[5],
                        "fecha_generacion": str(r[6]) if r[6] else "",
                        "fecha_firma_onac": str(r[7]) if r[7] else None,
                        "estado": r[8],
                        "payload_detalles": detalles,
                        "origen": r[10],
                        "created_at": str(r[11]) if r[11] else ""
                    })

                return {"total": total, "items": items}
        finally:
            conn.close()

    async def get_by_n_certificado(
        self,
        n_certificado: str,
        client_id: Optional[int] = None,
        include_pdf: bool = False,
    ) -> Optional[Dict[str, Any]]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cur:
                pdf_col = ", contenido_pdf" if include_pdf else ""
                sql = f"""
                    SELECT id, client_id, n_certificado, tipo, documento, nombre_titular, 
                           fecha_generacion, fecha_firma_onac, estado, payload_detalles, origen,
                           ruta_pdf, hash_sha256, signature_code, auth_code{pdf_col}
                    FROM tn_tarjetavirtual_certificados_expedidos
                    WHERE n_certificado = %s
                    LIMIT 1
                """
                await cur.execute(sql, (n_certificado,))
                row = await cur.fetchone()
                if not row:
                    return None
                
                raw_detalles = row[9]
                detalles = json.loads(raw_detalles) if isinstance(raw_detalles, str) else (raw_detalles or {})
                result = {
                    "id": str(row[0]),
                    "client_id": row[1],
                    "n_certificado": row[2],
                    "tipo": row[3],
                    "documento": row[4],
                    "nombre_titular": row[5],
                    "fecha_generacion": str(row[6]) if row[6] else "",
                    "fecha_firma_onac": str(row[7]) if row[7] else None,
                    "estado": row[8],
                    "payload_detalles": detalles,
                    "origen": row[10],
                    "ruta_pdf": row[11],
                    "hash_sha256": row[12],
                    "signature_code": row[13],
                    "auth_code": row[14],
                }
                if include_pdf:
                    result["pdf_bytes"] = _decode_pdf_blob(row[15])
                return result
        finally:
            conn.close()

    async def guardar_certificado(self, data: Dict[str, Any], client_id: Optional[int] = None) -> int:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cur:
                sql = """
                    INSERT INTO tn_tarjetavirtual_certificados_expedidos
                    (client_id, n_certificado, tipo, documento, nombre_titular, fecha_generacion,
                     fecha_firma_onac, estado, payload_detalles, origen, ruta_pdf, hash_sha256,
                     signature_code, auth_code, contenido_pdf)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    nombre_titular = VALUES(nombre_titular),
                    fecha_firma_onac = COALESCE(VALUES(fecha_firma_onac), fecha_firma_onac),
                    estado = VALUES(estado),
                    payload_detalles = VALUES(payload_detalles),
                    ruta_pdf = VALUES(ruta_pdf),
                    hash_sha256 = VALUES(hash_sha256),
                    signature_code = COALESCE(VALUES(signature_code), signature_code),
                    auth_code = COALESCE(VALUES(auth_code), auth_code),
                    contenido_pdf = COALESCE(VALUES(contenido_pdf), contenido_pdf),
                    updated_at = NOW()
                """
                params = (
                    client_id or 20001,
                    data["n_certificado"],
                    data["tipo"],
                    data["documento"],
                    data["nombre_titular"],
                    data["fecha_generacion"],
                    data.get("fecha_firma_onac"),
                    data.get("estado", "ACTIVO"),
                    json.dumps(data.get("payload_detalles", {})),
                    data.get("origen", "GENERADO"),
                    data.get("ruta_pdf"),
                    data.get("hash_sha256"),
                    data.get("signature_code"),
                    data.get("auth_code"),
                    _encode_pdf_blob(data.get("pdf_bytes")),
                )
                await cur.execute(sql, params)
                return cur.lastrowid
        finally:
            conn.close()

    async def actualizar_contenido_pdf(
        self,
        n_certificado: str,
        pdf_bytes: bytes,
        client_id: Optional[int] = None,
    ) -> None:
        encoded = _encode_pdf_blob(pdf_bytes)
        if not encoded:
            return
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE tn_tarjetavirtual_certificados_expedidos
                    SET contenido_pdf = %s, updated_at = NOW()
                    WHERE n_certificado = %s
                    """,
                    (encoded, n_certificado),
                )
        finally:
            conn.close()

    async def get_configuracion_institucional(self, client_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Obtiene la configuración institucional vigente (Director General, cargo y firma oficial)
        desde la tabla tn_tarjetavirtual_configuracion_institucional.
        """
        default_config = {
            "nombre_director": "SANDRA MILENA BARRIOS PULIDO",
            "cargo_director": "DIRECTOR GENERAL",
            "firma_director": None
        }
        try:
            conn = await get_client_connection(client_id)
            try:
                import aiomysql
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    sql = """
                        SELECT nombre_director, cargo_director, firma_director
                        FROM tn_tarjetavirtual_configuracion_institucional
                        WHERE publicado = 1
                        ORDER BY version DESC
                        LIMIT 1
                    """
                    await cur.execute(sql)
                    row = await cur.fetchone()
                    if not row:
                        sql_fallback = """
                            SELECT nombre_director, cargo_director, firma_director
                            FROM tn_tarjetavirtual_configuracion_institucional
                            ORDER BY version DESC
                            LIMIT 1
                        """
                        await cur.execute(sql_fallback)
                        row = await cur.fetchone()

                    if row:
                        return {
                            "nombre_director": row.get("nombre_director") or default_config["nombre_director"],
                            "cargo_director": row.get("cargo_director") or default_config["cargo_director"],
                            "firma_director": row.get("firma_director")
                        }
            finally:
                conn.close()
        except Exception as e:
            # Fallback seguro a los datos institucionales por defecto
            pass

        return default_config
