import pymysql
import aiomysql
from fastapi import FastAPI, APIRouter, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from app.api.v1.routes import tarjetas

app = FastAPI(
    title="Microservicio Tarjetas Digitales Admin",
    description="API Gateway Multitenant para Tarjetas Digitales",
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
