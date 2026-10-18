import sys, hmac, hashlib, base64, json, secrets, threading, time
from typing import Optional, Any

from templar.Config import Config

sys.dont_write_bytecode = True

class SessionStore:
    def get(self, sid: str) -> dict: ...
    def load(self, sid: str) -> tuple[dict | None, int | None]: ...
    def save(self, sid: str, data: dict) -> None: ...
    def save_if_version(self, sid: str, data: dict, version: int) -> bool: ...
    def create(self, data: dict) -> str: ...
    def delete(self, sid: str) -> None: ...


def normalize_session_data(data: dict) -> dict:
    """Enforce one JSON-only session contract for every backend.

    Redis persists JSON, so accepting arbitrary Python objects in the memory
    backend makes a later backend switch silently discard otherwise valid
    application state. Round-tripping also gives both backends identical data.
    """
    if not isinstance(data, dict):
        raise TypeError("Session data must be a dictionary")

    try:
        normalized = json.loads(json.dumps(data, separators=(",", ":")))
    except (TypeError, ValueError) as exc:
        raise TypeError("Session values must be JSON serializable") from exc

    if not isinstance(normalized, dict):  # Defensive; JSON object is required.
        raise TypeError("Session data must be a JSON object")

    return normalized

class MemorySessionStore(SessionStore):
    """Thread-safe, expiring in-process store for opaque session IDs."""

    def __init__(self, ttl_seconds: int = 86_400):
        if ttl_seconds <= 0:
            raise ValueError("Session TTL must be greater than zero")

        self._ttl_seconds = ttl_seconds
        self._store = {}
        self._lock = threading.RLock()

    def _expires_at(self) -> float:
        return time.time() + self._ttl_seconds

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [sid for sid, (_, expires_at, _) in self._store.items() if expires_at <= now]

        for sid in expired:
            self._store.pop(sid, None)

    def get(self, sid) -> Any:
        with self._lock:
            self._purge_expired()
            record = self._store.get(sid)

            return dict(record[0]) if record else None

    def load(self, sid: str) -> tuple[dict | None, int | None]:
        with self._lock:
            self._purge_expired()
            record = self._store.get(sid)

            if record is None:
                return None, None

            data, _expires_at, version = record

            return dict(data), version

    def save(self, sid, data) -> None:
        data = normalize_session_data(data)

        with self._lock:
            self._purge_expired()
            current = self._store.get(sid)
            version = current[2] + 1 if current else 1
            self._store[sid] = (dict(data), self._expires_at(), version)

    def save_if_version(self, sid: str, data: dict, version: int) -> bool:
        data = normalize_session_data(data)

        with self._lock:
            self._purge_expired()
            current = self._store.get(sid)

            if current is None or current[2] != version:
                return False

            self._store[sid] = (dict(data), self._expires_at(), version + 1)

            return True

    def create(self, data) -> str:
        sid = secrets.token_urlsafe(24)
        self.save(sid, data)

        return sid

    def delete(self, sid) -> None:
        with self._lock:
            self._store.pop(sid, None)


class RedisSessionStore(SessionStore):
    """Shared Redis-backed session storage for multi-worker deployments."""

    def __init__(self, url: str, ttl_seconds: int = 86_400):
        try:
            import redis
            from redis.exceptions import WatchError
        except ImportError as exc:
            raise RuntimeError("Redis sessions require the 'redis' optional dependency") from exc

        self._ttl_seconds = ttl_seconds
        self._client = redis.Redis.from_url(url, decode_responses=True)
        self._watch_error = WatchError
        self._prefix = "templar:session:"

    def get(self, sid) -> Any:
        data, _version = self.load(sid)

        return data

    def load(self, sid: str) -> tuple[dict | None, int | None]:
        raw = self._client.get(self._prefix + sid)

        if not raw:
            return None, None

        payload = json.loads(raw)

        # Backwards-compatible read of sessions written before versioning.
        if isinstance(payload, dict) and "data" in payload and "version" in payload:
            return payload["data"], payload["version"]

        return payload, 0

    def save(self, sid, data) -> None:
        data = normalize_session_data(data)
        _current_data, version = self.load(sid)
        next_version = (version or 0) + 1
        self._client.setex(
            self._prefix + sid,
            self._ttl_seconds,
            json.dumps({"data": data, "version": next_version}, separators=(",", ":")),
        )

    def save_if_version(self, sid: str, data: dict, version: int) -> bool:
        data = normalize_session_data(data)
        key = self._prefix + sid

        with self._client.pipeline() as pipeline:
            try:
                pipeline.watch(key)
                raw = pipeline.get(key)

                if not raw:
                    pipeline.unwatch()

                    return False

                payload = json.loads(raw)
                current_version = payload.get("version", 0) if isinstance(payload, dict) and "data" in payload else 0

                if current_version != version:
                    pipeline.unwatch()

                    return False

                pipeline.multi()
                pipeline.setex(key, self._ttl_seconds, json.dumps({"data": data, "version": version + 1}, separators=(",", ":")))
                pipeline.execute()

                return True
            except self._watch_error:
                return False

    def create(self, data) -> str:
        sid = secrets.token_urlsafe(24)
        self.save(sid, data)

        return sid

    def delete(self, sid) -> None:
        self._client.delete(self._prefix + sid)

# Cookie signer (HMAC)
def sign(session_payload: dict, secret: str) -> str:
    payload = base64.urlsafe_b64encode(json.dumps(session_payload, separators=(",", ":")).encode()).decode()
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

    return f"{payload}.{sig}"

def unsign(signed: str, secret: str) -> Optional[dict]:
    try:
        payload_b64, sig = signed.rsplit(".", 1)
        expected = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(sig, expected):
            return None
        
        payload_json = base64.urlsafe_b64decode(payload_b64.encode()).decode()

        return json.loads(payload_json)
    except Exception:
        return None
