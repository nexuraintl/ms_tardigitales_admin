import os
import aiomysql
from fastapi import status
from app.core.mysql import get_mysql_connection
from app.core.exceptions import PipelineException

async def get_client_mysql_config(client_id: int):
    if not os.getenv("DB1_HOST"):
        return None
        
    try:
        connection = await get_mysql_connection()
    except Exception as e:
        print(f"[Database Manager] Error de conexión al servidor central de base de datos: {e}")
        raise PipelineException(
            etapa="CONEXION_DB_CENTRAL",
            mensaje="No fue posible conectar con el servidor central de base de datos multitenant.",
            detalle_tecnico=str(e),
            cliente_id=client_id,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    try:
        async with connection.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                """
                SELECT
                    nombreBaseDeDatos,
                    usuario,
                    contrasena,
                    hosting,
                    puerto,
                    tipoDeBaseDeDatos
                FROM tn_gestion_bdconex
                WHERE idCliente = %s
                AND tipoDeBaseDeDatos = 'mysql'
                LIMIT 1
                """,
                (client_id,)
            )
            result = await cursor.fetchone()
            return result
    except Exception as e:
        print(f"[Database Manager] Error al consultar tn_gestion_bdconex para cliente {client_id}: {e}")
        raise PipelineException(
            etapa="CONSULTA_BDCONEX",
            mensaje=f"Error al consultar la tabla tn_gestion_bdconex para la entidad cliente {client_id}.",
            detalle_tecnico=str(e),
            cliente_id=client_id,
            tabla_afectada="tn_gestion_bdconex",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    finally:
        connection.close()

async def get_client_connection(client_id: int | None = None):
    # 1. Resolver el client_id
    if not client_id:
        default_id = os.getenv("CLIENT_ID")
        client_id = int(default_id) if default_id else None

    if not client_id:
        raise PipelineException(
            etapa="TENANT_CLIENT_ID_REQUERIDO",
            mensaje="Identificador de la entidad (client_id) no especificado en los parámetros de la solicitud.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # 2. Obtener configuración dinámica desde la base de datos central (tn_gestion_bdconex)
    config = await get_client_mysql_config(client_id)
    if not config:
        raise PipelineException(
            etapa="CONFIGURACION_TENANT_NO_ENCONTRADA",
            mensaje=f"No se encontró ninguna configuración de base de datos activa para el client_id {client_id} en tn_gestion_bdconex.",
            cliente_id=client_id,
            tabla_afectada="tn_gestion_bdconex",
            status_code=status.HTTP_404_NOT_FOUND
        )

    # 3. Establecer conexión dinámica con la base de datos del cliente
    host = config["hosting"]
    port = int(config["puerto"] or 3306)
    db_name = config["nombreBaseDeDatos"]

    try:
        connection = await aiomysql.connect(
            host=host,
            port=port,
            user=config["usuario"],
            password=config["contrasena"],
            db=db_name,
            autocommit=True
        )
        return connection
    except Exception as e:
        print(f"[Database Manager] Error al conectar a la DB del cliente {client_id} ({db_name}@{host}:{port}): {e}")
        raise PipelineException(
            etapa="CONEXION_DB_TENANT",
            mensaje=f"Fallo al conectar con la base de datos de la entidad cliente {client_id} ({db_name} en {host}:{port}).",
            detalle_tecnico=str(e),
            cliente_id=client_id,
            base_datos_cliente=f"{db_name}@{host}:{port}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

