import json
from typing import List, Dict, Any, Optional
from app.core.database import get_client_connection

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
                count_sql = f"SELECT COUNT(*) FROM tn_certificados_expedidos WHERE {where_sql}"
                await cur.execute(count_sql, tuple(params))
                total_row = await cur.fetchone()
                total = total_row[0] if total_row else 0

                # Paginación
                offset = (max(page, 1) - 1) * page_size
                query_sql = f"""
                    SELECT id, client_id, n_certificado, tipo, documento, nombre_titular, 
                           fecha_generacion, fecha_firma_onac, estado, payload_detalles, origen, created_at
                    FROM tn_certificados_expedidos
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

    async def get_by_n_certificado(self, n_certificado: str, client_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cur:
                sql = """
                    SELECT id, client_id, n_certificado, tipo, documento, nombre_titular, 
                           fecha_generacion, fecha_firma_onac, estado, payload_detalles, origen, ruta_pdf, hash_sha256
                    FROM tn_certificados_expedidos
                    WHERE n_certificado = %s
                    LIMIT 1
                """
                await cur.execute(sql, (n_certificado,))
                row = await cur.fetchone()
                if not row:
                    return None
                
                raw_detalles = row[9]
                detalles = json.loads(raw_detalles) if isinstance(raw_detalles, str) else (raw_detalles or {})
                return {
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
                    "hash_sha256": row[12]
                }
        finally:
            conn.close()

    async def guardar_certificado(self, data: Dict[str, Any], client_id: Optional[int] = None) -> int:
        conn = await get_client_connection(client_id)
        try:
            async with conn.cursor() as cur:
                sql = """
                    INSERT INTO tn_certificados_expedidos
                    (client_id, n_certificado, tipo, documento, nombre_titular, fecha_generacion, fecha_firma_onac, estado, payload_detalles, origen, ruta_pdf, hash_sha256)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    nombre_titular = VALUES(nombre_titular),
                    fecha_firma_onac = VALUES(fecha_firma_onac),
                    estado = VALUES(estado),
                    payload_detalles = VALUES(payload_detalles),
                    ruta_pdf = VALUES(ruta_pdf),
                    hash_sha256 = VALUES(hash_sha256),
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
                    data.get("hash_sha256")
                )
                await cur.execute(sql, params)
                return cur.lastrowid
        finally:
            conn.close()
