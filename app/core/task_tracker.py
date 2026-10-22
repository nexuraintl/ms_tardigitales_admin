import asyncio
import logging
from typing import Coroutine, Any, Optional, Set

logger = logging.getLogger("task_tracker")

# Conjunto global persistente en memoria para prevenir que el recolector de basura (GC)
# de Python 3.11+ destruya corutinas en segundo plano desvinculadas.
_BACKGROUND_TASKS: Set[asyncio.Task] = set()

def create_tracked_task(
    coro: Coroutine[Any, Any, Any],
    name: Optional[str] = None
) -> asyncio.Task:
    """
    Crea y registra una tarea asíncrona en memoria persistente, asociando callbacks
    de telemetría para registrar caídas, excepciones no capturadas o cancelaciones.
    """
    task = asyncio.create_task(coro, name=name)
    _BACKGROUND_TASKS.add(task)

    def _done_callback(t: asyncio.Task) -> None:
        _BACKGROUND_TASKS.discard(t)
        task_name = t.get_name() or "unnamed_task"
        if t.cancelled():
            logger.info(f"[TaskTracker] Tarea '{task_name}' cancelada ordenadamente.")
        elif t.exception():
            logger.error(
                f"[TaskTracker] Tarea '{task_name}' finalizó con excepción no capturada: {t.exception()}",
                exc_info=t.exception()
            )

    task.add_done_callback(_done_callback)
    return task

def get_tracked_task(name: str) -> Optional[asyncio.Task]:
    """Retorna la tarea activa correspondiente al nombre especificado si sigue en ejecución."""
    for t in _BACKGROUND_TASKS:
        if t.get_name() == name and not t.done():
            return t
    return None

def is_task_alive(name: str) -> bool:
    """Verifica si la tarea con el nombre indicado existe y continúa ejecutándose."""
    t = get_tracked_task(name)
    return t is not None and not t.done()
