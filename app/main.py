import pymysql
import aiomysql
from fastapi import FastAPI, APIRouter, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from app.api.v1.routes import tarjetas, colas

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
admin_router.include_router(colas.router, tags=["Admin - Colas y Procesos"])

app.include_router(admin_router)

# -------------------------------------------------------------
# WORKER CONTINUO DE PROCESAMIENTO DE COLAS (DATABASE POLLING CONSUMER)
# -------------------------------------------------------------
async def _iniciar_queue_worker():
    from app.services.queue_worker_service import queue_worker
    from app.config.queue_config import queue_config

    if not queue_config.WORKER_ENABLED:
        print("[QueueWorker] Worker de colas deshabilitado por configuración (QUEUE_WORKER_ENABLED=false).")
        return

    await queue_worker.iniciar_worker()

# HU-JCC-005: Tarea programada recurrente (Background Task Loop)
async def _iniciar_tarea_programada_recurrente():
    from app.config.queue_config import queue_config
    import os, asyncio

    client_id = int(os.getenv("CLIENT_ID", "20001"))
    from app.services.scheduler_service import scheduler_service
    
    await asyncio.sleep(10)
    while True:
        if not queue_config.SCHEDULER_ENABLED:
            await asyncio.sleep(60)
            continue

        try:
            print(f"[Scheduler] Ejecutando ciclo recurrente de emisión HU-JCC-005 (Intervalo DB: {queue_config.SCHEDULER_INTERVAL_SECONDS}s)...")
            await scheduler_service.ejecutar_emision_recurrente(client_id=client_id)
        except Exception as e:
            print(f"[Scheduler] Error en ciclo de emisión recurrente: {e}")

        await asyncio.sleep(queue_config.SCHEDULER_INTERVAL_SECONDS)

@app.on_event("startup")
async def startup_event():
    import asyncio
    import os
    from app.config.queue_config import queue_config
    from app.repositories.tarjetas_repository import TarjetasRepository

    # 1. Cargar configuración dinámica de colas y worker desde la Base de Datos
    try:
        cid = int(os.getenv("CLIENT_ID", "20001"))
        repo = TarjetasRepository()
        config_db = await repo.get_queue_config(cid)
        if config_db:
            queue_config.load_from_db(config_db)
            print(f"[Config] Configuración de colas cargada desde MySQL (tn_tarjetavirtual_config_colas) para cliente {cid}.")
    except Exception as e:
        print(f"[Config] Usando configuración por defecto de colas en memoria ({e})")

    # 2. Iniciar tareas en segundo plano
    asyncio.create_task(_iniciar_queue_worker())
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

