import pymysql
import aiomysql
from fastapi import FastAPI, APIRouter, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from app.api.v1.routes import tarjetas, tramites, notificaciones

app = FastAPI(
    title="Microservicio Tarjetas Digitales y Notificaciones",
    description="API Gateway Multitenant para Tarjetas Digitales, Trámites y Emisión de Notificaciones",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url="/tardigitales/openapi.json"
)

# Manejadores globales de errores de Base de Datos MySQL
@app.exception_handler(pymysql.Error)
async def pymysql_exception_handler(request: Request, exc: pymysql.Error):
    error_cls = type(exc).__name__
    print(f"[Global DB Handler] Error de MySQL capturado ({error_cls}): {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "code": "MS_3804_MYSQL_ERROR",
            "message": "Error de base de datos MySQL al procesar la solicitud (MS-3804).",
            "detail": f"Error en la base de datos MySQL ({error_cls}). Por favor verifique los registros del servidor (MS-3804)."
        },
    )

@app.exception_handler(aiomysql.Error)
async def aiomysql_exception_handler(request: Request, exc: aiomysql.Error):
    error_cls = type(exc).__name__
    print(f"[Global DB Handler] Error de aiomysql capturado ({error_cls}): {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "code": "MS_3804_MYSQL_ERROR",
            "message": "Error de base de datos MySQL al procesar la solicitud (MS-3804).",
            "detail": f"Error en la base de datos MySQL ({error_cls}). Por favor verifique los registros del servidor (MS-3804)."
        },
    )

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Documentación Swagger personalizada detrás del Gateway
@app.on_event("startup")
async def startup_event():
    try:
        from app.core.database import get_client_connection
        conn = await get_client_connection(20001)
        async with conn.cursor() as cursor:
            await cursor.execute("""
                INSERT IGNORE INTO tn_tarjetavirtual_tipos_asociados (id, nombre)
                VALUES (1, 'primeraVez'), (2, 'duplicado'), (3, 'sustitucion'), (4, 'modificacion')
            """)
            await conn.commit()
        conn.close()
        print("[Startup] Catálogo de tipos de asociados inicializado exitosamente (1..4).")
    except Exception as e:
        print(f"[Startup] Warning al verificar catálogo de tipos de asociados: {e}")

@app.get("/tardigitales/docs", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(
        openapi_url="/apig/tardigitales/openapi.json",
        title="Tarjetas Digitales API - Swagger Docs"
    )

# -------------------------------------------------------------
# ROUTER ADMINISTRATIVO CENTRAL: /tardigitales/admin
# -------------------------------------------------------------
admin_router = APIRouter(prefix="/tardigitales/admin")

admin_router.include_router(notificaciones.router, prefix="/notificaciones", tags=["Admin - Notificaciones"])
admin_router.include_router(tramites.router, prefix="/tramites", tags=["Admin - Trámites"])
admin_router.include_router(tarjetas.router, prefix="/tarjetas", tags=["Admin - Tarjetas Digitales"])

app.include_router(admin_router)

# Ruta informativa raíz
@app.get("/", include_in_schema=False)
@app.get("/tardigitales", include_in_schema=False)
async def root():
    return {
        "status": "online",
        "service": "Microservicio Tarjetas Digitales y Notificaciones",
        "architecture": "Layered (Controller - Service - Repository - Schema)",
        "admin_prefix": "/tardigitales/admin",
        "docs": "/apig/tardigitales/docs"
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
