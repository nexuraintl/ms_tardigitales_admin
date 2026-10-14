import asyncio
import logging
from typing import Optional
from app.config.queue_config import queue_config
from app.repositories.tarjetas_repository import TarjetasRepository
from app.services.emision_engine_service import EmisionEngineService
from app.constants import DEFAULT_CLIENT_ID

logger = logging.getLogger("queue_worker")

class QueueWorkerService:
    """
    Worker Continuo de Procesamiento de Colas (Database Polling Consumer).
    Garantiza persistencia, tolerancia a fallos y auto-recuperación ante reinicios.
    """

    def __init__(
        self,
        repository: Optional[TarjetasRepository] = None,
        engine: Optional[EmisionEngineService] = None
    ):
        self.repository = repository or TarjetasRepository()
        self.engine = engine or EmisionEngineService(self.repository)
        self.running = False
        self.estado = "INACTIVO"
        self._consecutive_network_errors = 0
        self._circuit_breaker_open = False

    def get_status(self) -> dict:
        cb_estado = "CERRADO (NORMAL)"
        if self._circuit_breaker_open:
            cb_estado = "ABIERTO (COOLDOWN)"
        elif self._consecutive_network_errors > 0:
            cb_estado = f"DEGRADADO ({self._consecutive_network_errors} fallos)"

        return {
            "activo": self.running and queue_config.WORKER_ENABLED,
            "estado": self.estado if queue_config.WORKER_ENABLED else "PAUSADO_CONFIGURACION",
            "circuit_breaker_estado": cb_estado,
            "fallos_consecutivos": self._consecutive_network_errors
        }

    async def iniciar_worker(self):
        """
        Bucle continuo del Worker.
        Lee registros en estado 'PENDIENTE' de la base de datos y los despacha ordenadamente.
        """
        self.running = True
        logger.info(
            f"[QueueWorker] Worker continuo de colas INICIADO. "
            f"(batch_size={queue_config.BATCH_SIZE}, poll_interval={queue_config.POLL_INTERVAL_SECONDS}s, "
            f"item_delay={queue_config.ITEM_DELAY_SECONDS}s)"
        )

        while self.running:
            if not queue_config.WORKER_ENABLED:
                self.estado = "PAUSADO"
                await asyncio.sleep(queue_config.POLL_INTERVAL_SECONDS)
                continue

            try:
                self.estado = "EN_ESPERA"
                # 1. Extraer paquete de tareas pendientes (con límite parametrizable y fallback de tenant)
                items = await self.repository.get_pending_queue_items(
                    limit=queue_config.BATCH_SIZE,
                    client_id=DEFAULT_CLIENT_ID
                )

                if not items:
                    # En momentos de reposo, rescatar items huerfanos y finalizar lotes pendientes
                    try:
                        await self.repository.recover_stuck_queue_items(timeout_minutes=5, client_id=DEFAULT_CLIENT_ID)
                        await self.repository.finalize_uncompleted_lotes_if_ready(client_id=DEFAULT_CLIENT_ID)
                    except Exception as clean_err:
                        logger.warning(f"[QueueWorker] Verificacion periodica de lotes: {clean_err}")

                    # No hay tareas pendientes en la cola: reposo de bajo consumo
                    self.estado = "EN_ESPERA"
                    await asyncio.sleep(queue_config.POLL_INTERVAL_SECONDS)
                    continue

                self.estado = "PROCESANDO"
                logger.info(f"[QueueWorker] Procesando tanda de {len(items)} registros pendientes...")

                lotes_afectados = set()

                for item in items:
                    item_id = item["id"]
                    lote_id = item["lote_id"]
                    cid = item.get("client_id") or DEFAULT_CLIENT_ID
                    doc = item["documento_o_nit"]
                    tipo_tarjeta = item.get("tipo_tarjeta", "contadores")
                    tipo_tramite = item.get("tipo_tramite", "primeraVez")
                    lotes_afectados.add(lote_id)

                    try:
                        # Reclamar item para evitar procesamiento duplicado
                        await self.repository.claim_queue_item(item_id=item_id, lote_id=lote_id, client_id=cid)

                        # Procesar emision o sincronizacion de estados a traves del motor unificado
                        if tipo_tramite == "sincronizacion_estados":
                            res = await self.engine.sincronizar_estado_tarjeta_individual(
                                documento_o_nit=doc,
                                tipo_tarjeta=tipo_tarjeta,
                                client_id=cid
                            )
                        elif tipo_tarjeta == "sociedades":
                            res = await self.engine.emitir_sociedad_individual(
                                nit=doc,
                                tipo_tramite=tipo_tramite,
                                client_id=cid
                            )
                        else:
                            res = await self.engine.sincronizar_foto_contador(
                                documento=doc,
                                tipo_tramite=tipo_tramite,
                                client_id=cid
                            )

                        resultado_key = res.get("resultado", "error")

                        # Control del Circuit Breaker por fallos de conectividad con JCC
                        if resultado_key == "error_conexion":
                            self._consecutive_network_errors += 1
                        else:
                            self._consecutive_network_errors = 0

                        # Actualizar resultado en base de datos
                        await self.repository.update_queue_item_result(
                            item_id=item_id,
                            lote_id=lote_id,
                            resultado=resultado_key,
                            tarjeta_id=res.get("id"),
                            mensaje_detalle=res.get("mensaje"),
                            client_id=cid
                        )

                    except Exception as item_err:
                        logger.error(f"[QueueWorker] Error procesando item #{item_id} (doc: {doc}): {item_err}", exc_info=True)
                        try:
                            await self.repository.update_queue_item_result(
                                item_id=item_id,
                                lote_id=lote_id,
                                resultado="fallido",
                                mensaje_detalle=f"Fallo de procesamiento interno: {str(item_err)[:250]}",
                                client_id=cid
                            )
                        except Exception as up_err:
                            logger.error(f"[QueueWorker] Error marcando fallo en item #{item_id}: {up_err}")

                    # Si el Circuit Breaker se dispara por caida de VPN / red
                    if self._consecutive_network_errors >= queue_config.CIRCUIT_BREAKER_FAIL_THRESHOLD:
                        logger.warning(
                            f"[QueueWorker] Circuit Breaker activado: {self._consecutive_network_errors} fallos seguidos de red con JCC. "
                            f"Enfriando por {queue_config.CIRCUIT_BREAKER_COOLDOWN_SECONDS} segundos..."
                        )
                        self._circuit_breaker_open = True
                        self.estado = "CIRCUITO_ABIERTO_COOLDOWN"
                        await asyncio.sleep(queue_config.CIRCUIT_BREAKER_COOLDOWN_SECONDS)
                        self._circuit_breaker_open = False
                        self._consecutive_network_errors = 0
                        self.estado = "EN_ESPERA"
                        break

                    # Pausa microscopica parametrizable entre emisiones para proteger la API externa
                    if queue_config.ITEM_DELAY_SECONDS > 0:
                        await asyncio.sleep(queue_config.ITEM_DELAY_SECONDS)

                # Verificar y finalizar los lotes que ya hayan culminado todos sus items
                for lid in lotes_afectados:
                    await self.repository.finalize_lote_if_completed(lote_id=lid, client_id=DEFAULT_CLIENT_ID)

                self.estado = "EN_ESPERA"

            except asyncio.CancelledError:
                logger.info("[QueueWorker] Worker detenido ordenadamente.")
                self.running = False
                self.estado = "DETENIDO"
                break
            except Exception as e:
                logger.error(f"[QueueWorker] Excepción no controlada en bucle de colas: {e}", exc_info=True)
                self.estado = "ERROR"
                await asyncio.sleep(queue_config.POLL_INTERVAL_SECONDS)

    def detener_worker(self):
        self.running = False
        self.estado = "DETENIDO"

# Instancia singleton del worker para acceso global y telemetría
queue_worker = QueueWorkerService()

