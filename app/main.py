import pymysql
import aiomysql
from fastapi import FastAPI, APIRouter, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from app.api.v1.routes import tarjetas

from app.core.exceptions import PipelineException

app = FastAPI(
    title="Microservicio Tarjetas Digitales Admin",
    description="API Gateway Multitenant para Tarjetas Digitales",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url="/tardigitales/openapi.json"
)

# Manejador global para Excepciones por Etapas (PipelineException)
@app.exception_handler(PipelineException)
async def pipeline_exception_handler(request: Request, exc: PipelineException):
    print(f"[PipelineException] Etapa '{exc.etapa}': {exc.mensaje} | Detalle: {exc.detalle_tecnico}")
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )

# Manejadores globales de errores no capturados de Base de Datos MySQL
@app.exception_handler(pymysql.Error)
async def pymysql_exception_handler(request: Request, exc: pymysql.Error):
    error_cls = type(exc).__name__
    print(f"[Global DB Handler] Error de MySQL no capturado ({error_cls}): {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "code": 500,
            "error": {
                "codigo_error": 3899,
                "etapa": "ERROR_DESCONOCIDO_MYSQL",
                "mensaje": "Se produjo un error no controlado en la base de datos MySQL.",
                "detalle_tecnico": str(exc),
                "tipo_excepcion": error_cls
            }
        },
    )

@app.exception_handler(aiomysql.Error)
async def aiomysql_exception_handler(request: Request, exc: aiomysql.Error):
    error_cls = type(exc).__name__
    print(f"[Global DB Handler] Error de aiomysql no capturado ({error_cls}): {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "code": 500,
            "error": {
                "codigo_error": 3899,
                "etapa": "ERROR_DESCONOCIDO_MYSQL",
                "mensaje": "Se produjo un error no controlado en la base de datos MySQL asíncrona.",
                "detalle_tecnico": str(exc),
                "tipo_excepcion": error_cls
            }
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

# HU-JCC-005: Tarea programada recurrente (Background Task Loop)
async def _iniciar_tarea_programada_recurrente():
    import os, asyncio
    enable_scheduler = os.getenv("ENABLE_SCHEDULER", "true").lower() == "true"
    interval_seconds = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "3600"))
    if not enable_scheduler:
        print("[Scheduler] Tarea programada recurrente deshabilitada por configuración.")
        return

    print(f"[Scheduler] Tarea programada HU-JCC-005 iniciada (Intervalo: {interval_seconds}s)...")
    from app.services.scheduler_service import SchedulerService
    scheduler = SchedulerService()
    
    await asyncio.sleep(10)
    while True:
        try:
            print("[Scheduler] Ejecutando ciclo recurrente de emisión HU-JCC-005...")
            await scheduler.ejecutar_emision_recurrente()
        except Exception as e:
            print(f"[Scheduler] Error en ciclo de emisión recurrente: {e}")
        await asyncio.sleep(interval_seconds)

@app.on_event("startup")
async def startup_event():
    import asyncio
    asyncio.create_task(_iniciar_tarea_programada_recurrente())

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
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

