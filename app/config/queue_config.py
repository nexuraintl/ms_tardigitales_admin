from typing import Dict, Any, Optional

class QueueConfig:
    """
    Configuración centralizada del Sistema de Colas, Lotes y Worker.
    La fuente de verdad primaria es la Base de Datos (tabla tn_tarjetavirtual_config_colas).
    """

    def __init__(self):
        # 1. Parámetros del Worker Continuo de Procesamiento
        self.WORKER_ENABLED: bool = True
        self.POLL_INTERVAL_SECONDS: float = 5.0
        self.BATCH_SIZE: int = 10
        self.ITEM_DELAY_SECONDS: float = 0.05

        # 2. Resiliencia de Red y Circuit Breaker
        self.CIRCUIT_BREAKER_FAIL_THRESHOLD: int = 3
        self.CIRCUIT_BREAKER_COOLDOWN_SECONDS: int = 60
        self.MAX_RETRIES_PER_ITEM: int = 2

        # 3. Parámetros de la Tarea Automática Recurrente (HU-JCC-005)
        self.SCHEDULER_ENABLED: bool = True
        self.SCHEDULER_INTERVAL_SECONDS: int = 3600
        self.SCHEDULER_AUTO_ENQUEUE: bool = True

    def load_from_db(self, db_dict: Optional[Dict[str, Any]] = None):
        """Carga y actualiza los parámetros en caliente a partir del registro en base de datos."""
        if not db_dict or not isinstance(db_dict, dict):
            return

        if "worker_enabled" in db_dict and db_dict["worker_enabled"] is not None:
            self.WORKER_ENABLED = bool(db_dict["worker_enabled"])
        if "poll_interval_seconds" in db_dict and db_dict["poll_interval_seconds"] is not None:
            self.POLL_INTERVAL_SECONDS = float(db_dict["poll_interval_seconds"])
        if "batch_size" in db_dict and db_dict["batch_size"] is not None:
            self.BATCH_SIZE = int(db_dict["batch_size"])
        if "item_delay_seconds" in db_dict and db_dict["item_delay_seconds"] is not None:
            self.ITEM_DELAY_SECONDS = float(db_dict["item_delay_seconds"])

        if "circuit_breaker_fail_threshold" in db_dict and db_dict["circuit_breaker_fail_threshold"] is not None:
            self.CIRCUIT_BREAKER_FAIL_THRESHOLD = int(db_dict["circuit_breaker_fail_threshold"])
        if "circuit_breaker_cooldown_seconds" in db_dict and db_dict["circuit_breaker_cooldown_seconds"] is not None:
            self.CIRCUIT_BREAKER_COOLDOWN_SECONDS = int(db_dict["circuit_breaker_cooldown_seconds"])
        if "max_retries_per_item" in db_dict and db_dict["max_retries_per_item"] is not None:
            self.MAX_RETRIES_PER_ITEM = int(db_dict["max_retries_per_item"])

        if "scheduler_enabled" in db_dict and db_dict["scheduler_enabled"] is not None:
            self.SCHEDULER_ENABLED = bool(db_dict["scheduler_enabled"])
        if "scheduler_interval_seconds" in db_dict and db_dict["scheduler_interval_seconds"] is not None:
            self.SCHEDULER_INTERVAL_SECONDS = int(db_dict["scheduler_interval_seconds"])
        if "scheduler_auto_enqueue" in db_dict and db_dict["scheduler_auto_enqueue"] is not None:
            self.SCHEDULER_AUTO_ENQUEUE = bool(db_dict["scheduler_auto_enqueue"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_enabled": self.WORKER_ENABLED,
            "poll_interval_seconds": self.POLL_INTERVAL_SECONDS,
            "batch_size": self.BATCH_SIZE,
            "item_delay_seconds": self.ITEM_DELAY_SECONDS,
            "circuit_breaker_fail_threshold": self.CIRCUIT_BREAKER_FAIL_THRESHOLD,
            "circuit_breaker_cooldown_seconds": self.CIRCUIT_BREAKER_COOLDOWN_SECONDS,
            "max_retries_per_item": self.MAX_RETRIES_PER_ITEM,
            "scheduler_enabled": self.SCHEDULER_ENABLED,
            "scheduler_interval_seconds": self.SCHEDULER_INTERVAL_SECONDS,
            "scheduler_auto_enqueue": self.SCHEDULER_AUTO_ENQUEUE,
        }

queue_config = QueueConfig()
