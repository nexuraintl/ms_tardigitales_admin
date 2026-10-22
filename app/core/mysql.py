import os
import aiomysql

# Conexión al Gestor de Base de Datos Central (gestion_bdconex)
DB1_HOST = os.getenv("DB1_HOST")
DB1_PORT = int(os.getenv("MYSQL_PORT", 3306))
DB1_NAME = os.getenv("DB1_NAME")
DB1_USER = os.getenv("DB1_USER")
DB1_PASS = os.getenv("DB1_PASS")

async def get_mysql_connection():
    if not DB1_HOST:
        raise ValueError("DB1_HOST no está configurado para la base de datos central.")
        
    connection = await aiomysql.connect(
        host=DB1_HOST,
        port=DB1_PORT,
        user=DB1_USER,
        password=DB1_PASS,
        db=DB1_NAME,
        autocommit=True,
        connect_timeout=10
    )
    return connection
