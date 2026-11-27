import base64
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("fcm_push_service")

TOPIC_TODOS = "jcc_todos"
TOPIC_CONTADORES = "jcc_contadores"
TOPIC_SOCIEDADES = "jcc_sociedades"

_firebase_app = None
_firebase_init_attempted = False


def resolver_topic_audiencia(audiencia: Optional[str]) -> str:
    """Mapea la audiencia del MFE Admin al topic canónico de FCM."""
    aud = (audiencia or "Todos").strip().lower()
    if aud in ("contadores", "contador"):
        return TOPIC_CONTADORES
    if aud in ("sociedades", "sociedad"):
        return TOPIC_SOCIEDADES
    return TOPIC_TODOS


def resolver_topics_por_tipo_tarjeta(tipo_tarjeta: Optional[str]) -> List[str]:
    """Retorna los topics a los que debe suscribirse un dispositivo según su tipo de tarjeta."""
    tipo = (tipo_tarjeta or "").strip().lower()
    topics = [TOPIC_TODOS]
    if tipo in ("contadores", "contador"):
        topics.append(TOPIC_CONTADORES)
    elif tipo in ("sociedades", "sociedad"):
        topics.append(TOPIC_SOCIEDADES)
    return topics


def _load_service_account_dict() -> Optional[Dict[str, Any]]:
    raw_json = (os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON") or "").strip()
    if raw_json:
        try:
            if raw_json.startswith("{"):
                return json.loads(raw_json)
            decoded = base64.b64decode(raw_json).decode("utf-8")
            return json.loads(decoded)
        except Exception as e:
            logger.error("[FcmPushService] Error parseando FIREBASE_SERVICE_ACCOUNT_JSON: %s", e)

    sa_path = (
        os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        or ""
    ).strip()
    if sa_path and os.path.isfile(sa_path):
        try:
            with open(sa_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("[FcmPushService] Error leyendo credenciales en %s: %s", sa_path, e)

    return None


def _get_firebase_app():
    global _firebase_app, _firebase_init_attempted
    if _firebase_app is not None:
        return _firebase_app
    if _firebase_init_attempted:
        return None
    _firebase_init_attempted = True

    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        logger.warning("[FcmPushService] Paquete firebase-admin no instalado; envíos FCM deshabilitados.")
        return None

    try:
        if firebase_admin._apps:
            _firebase_app = firebase_admin.get_app()
            return _firebase_app

        sa_dict = _load_service_account_dict()
        if not sa_dict:
            logger.warning(
                "[FcmPushService] Sin credenciales Firebase (FIREBASE_SERVICE_ACCOUNT_JSON / FIREBASE_SERVICE_ACCOUNT_PATH)."
            )
            return None

        cred = credentials.Certificate(sa_dict)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info(
            "[FcmPushService] Firebase Admin inicializado correctamente (project_id=%s).",
            sa_dict.get("project_id"),
        )
        return _firebase_app
    except Exception as e:
        logger.error("[FcmPushService] Error inicializando Firebase Admin: %s", e, exc_info=True)
        return None


class FcmPushService:
    """
    Servicio híbrido de notificaciones push sobre Firebase Cloud Messaging (FCM HTTP v1):
    - Masivas por audiencia (Todos / Contadores / Sociedades): Topics (`jcc_todos`, `jcc_contadores`, `jcc_sociedades`).
    - Puntuales (1 a 1): Token directo con detección de tokens no registrados (`UnregisteredError`).
    """

    def is_enabled(self) -> bool:
        return _get_firebase_app() is not None

    def _build_platform_configs(self):
        from firebase_admin import messaging

        android_cfg = messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(sound="default"),
        )
        apns_cfg = messaging.APNSConfig(
            headers={"apns-priority": "10"},
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound="default", badge=1),
            ),
        )
        return android_cfg, apns_cfg

    def _iid_topic_batch(self, app, action: str, topic: str, tokens: List[str]) -> Dict[str, int]:
        """
        Llama a IID batchAdd / batchRemove usando OAuth2 Bearer + header `access_token_auth: true`
        (requerido por iid.googleapis.com con tokens OAuth2 de cuenta de servicio).
        """
        import requests

        access_tok = app.credential.get_access_token().access_token
        url = f"https://iid.googleapis.com/iid/v1:{action}"
        ok_count = 0
        fail_count = 0

        for i in range(0, len(tokens), 1000):
            chunk = tokens[i : i + 1000]
            try:
                resp = requests.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {access_tok}",
                        "access_token_auth": "true",
                        "Content-Type": "application/json",
                    },
                    json={"to": f"/topics/{topic}", "registration_tokens": chunk},
                    timeout=20,
                )
                if resp.status_code == 200:
                    results_arr = (resp.json() or {}).get("results", [])
                    for item in results_arr:
                        if isinstance(item, dict) and item.get("error"):
                            fail_count += 1
                        else:
                            ok_count += 1
                else:
                    logger.error(
                        "[FcmPushService] IID %s topic '%s' HTTP %s: %s",
                        action,
                        topic,
                        resp.status_code,
                        resp.text[:300],
                    )
                    fail_count += len(chunk)
            except Exception as e:
                logger.error("[FcmPushService] Error IID %s topic '%s': %s", action, topic, e)
                fail_count += len(chunk)

        return {"success": ok_count, "failure": fail_count}

    def suscribir_tokens_a_topics(
        self,
        tokens: List[str],
        tipo_tarjeta: str,
    ) -> Dict[str, Any]:
        """Suscribe hasta N tokens (en bloques de 1000) a `jcc_todos` y al topic del tipo de tarjeta."""
        app = _get_firebase_app()
        clean_tokens = [t.strip() for t in tokens if t and t.strip()]
        if not app or not clean_tokens:
            return {"enabled": bool(app), "tokens": len(clean_tokens), "results": {}}

        topics = resolver_topics_por_tipo_tarjeta(tipo_tarjeta)
        results: Dict[str, Any] = {}
        for topic in topics:
            results[topic] = self._iid_topic_batch(app, "batchAdd", topic, clean_tokens)

        return {"enabled": True, "tokens": len(clean_tokens), "results": results}

    def suscribir_dispositivo(self, fcm_token: Optional[str], tipo_tarjeta: str) -> Dict[str, Any]:
        if not fcm_token or not fcm_token.strip():
            return {"enabled": self.is_enabled(), "skipped": True}
        return self.suscribir_tokens_a_topics([fcm_token.strip()], tipo_tarjeta)

    def desuscribir_tokens(
        self,
        tokens: List[str],
        tipo_tarjeta: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Desuscribe tokens de todos los topics aplicables (ej. al revocar/inactivar tarjeta)."""
        app = _get_firebase_app()
        clean_tokens = [t.strip() for t in tokens if t and t.strip()]
        if not app or not clean_tokens:
            return {"enabled": bool(app), "tokens": len(clean_tokens), "results": {}}

        topics = (
            resolver_topics_por_tipo_tarjeta(tipo_tarjeta)
            if tipo_tarjeta
            else [TOPIC_TODOS, TOPIC_CONTADORES, TOPIC_SOCIEDADES]
        )
        results: Dict[str, Any] = {}
        for topic in topics:
            results[topic] = self._iid_topic_batch(app, "batchRemove", topic, clean_tokens)

        return {"enabled": True, "tokens": len(clean_tokens), "results": results}

    def enviar_a_audiencia(
        self,
        audiencia: str,
        titulo: str,
        mensaje: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Envía una notificación masiva en 1 sola petición FCM al topic de la audiencia."""
        app = _get_firebase_app()
        topic = resolver_topic_audiencia(audiencia)
        if not app:
            return {"sent": False, "enabled": False, "topic": topic, "error": "FCM no configurado"}

        from firebase_admin import messaging

        android_cfg, apns_cfg = self._build_platform_configs()
        str_data = {str(k): str(v) for k, v in (data or {}).items() if v is not None}

        msg = messaging.Message(
            topic=topic,
            notification=messaging.Notification(title=titulo, body=mensaje),
            android=android_cfg,
            apns=apns_cfg,
            data=str_data or None,
        )
        try:
            message_id = messaging.send(msg, app=app)
            logger.info("[FcmPushService] Push enviado al topic '%s' -> %s", topic, message_id)
            return {"sent": True, "enabled": True, "topic": topic, "message_id": message_id}
        except Exception as e:
            logger.error("[FcmPushService] Error enviando push al topic '%s': %s", topic, e, exc_info=True)
            return {"sent": False, "enabled": True, "topic": topic, "error": str(e)}

    def enviar_a_tokens_lote(
        self,
        tokens: List[str],
        titulo: str,
        mensaje: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Envía una notificación a una lista de tokens en lotes de hasta 500 (FCM HTTP v1 multicast).
        Devuelve conteo de éxitos, fallos y la lista de tokens UNREGISTERED para limpieza automática.
        """
        app = _get_firebase_app()
        clean_tokens = list(dict.fromkeys(t.strip() for t in tokens if t and t.strip()))
        if not app:
            return {
                "sent": False,
                "enabled": False,
                "total": len(clean_tokens),
                "success": 0,
                "failure": 0,
                "unregistered_tokens": [],
                "error": "FCM no configurado",
            }
        if not clean_tokens:
            return {
                "sent": False,
                "enabled": True,
                "total": 0,
                "success": 0,
                "failure": 0,
                "unregistered_tokens": [],
            }

        from firebase_admin import messaging

        android_cfg, apns_cfg = self._build_platform_configs()
        str_data = {str(k): str(v) for k, v in (data or {}).items() if v is not None}

        total_ok = 0
        total_fail = 0
        unregistered: List[str] = []

        for i in range(0, len(clean_tokens), 500):
            chunk = clean_tokens[i : i + 500]
            multicast = messaging.MulticastMessage(
                tokens=chunk,
                notification=messaging.Notification(title=titulo, body=mensaje),
                android=android_cfg,
                apns=apns_cfg,
                data=str_data or None,
            )
            try:
                batch_resp = messaging.send_each_for_multicast(multicast, app=app)
                total_ok += batch_resp.success_count
                total_fail += batch_resp.failure_count
                for idx, item_resp in enumerate(batch_resp.responses):
                    if not item_resp.success and isinstance(item_resp.exception, messaging.UnregisteredError):
                        unregistered.append(chunk[idx])
            except Exception as e:
                logger.error("[FcmPushService] Error enviando lote multicast: %s", e, exc_info=True)
                total_fail += len(chunk)

        return {
            "sent": total_ok > 0,
            "enabled": True,
            "mode": "multicast",
            "total": len(clean_tokens),
            "success": total_ok,
            "failure": total_fail,
            "unregistered_tokens": unregistered,
        }

    def enviar_a_token(
        self,
        fcm_token: str,
        titulo: str,
        mensaje: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Envía una notificación puntual 1 a 1 a un dispositivo específico."""
        app = _get_firebase_app()
        if not app:
            return {"sent": False, "enabled": False, "unregistered": False, "error": "FCM no configurado"}

        from firebase_admin import messaging

        android_cfg, apns_cfg = self._build_platform_configs()
        str_data = {str(k): str(v) for k, v in (data or {}).items() if v is not None}

        msg = messaging.Message(
            token=fcm_token,
            notification=messaging.Notification(title=titulo, body=mensaje),
            android=android_cfg,
            apns=apns_cfg,
            data=str_data or None,
        )
        try:
            message_id = messaging.send(msg, app=app)
            return {"sent": True, "enabled": True, "unregistered": False, "message_id": message_id}
        except messaging.UnregisteredError:
            logger.warning("[FcmPushService] Token FCM no registrado/expirado; debe marcarse inactivo.")
            return {"sent": False, "enabled": True, "unregistered": True, "error": "UNREGISTERED"}
        except Exception as e:
            logger.error("[FcmPushService] Error enviando push puntual: %s", e)
            return {"sent": False, "enabled": True, "unregistered": False, "error": str(e)}
