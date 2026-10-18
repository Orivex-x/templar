import sys
import threading
import time

from .CacheProvider import CacheProvider

sys.dont_write_bytecode = True

class MemoryCache(CacheProvider):
    def __init__(self):
        self.store = {}
        self._lock = threading.RLock()

    def _get_live(self, key: str):
        if not isinstance(key, str):
            raise TypeError("Cache keys must be strings")

        value = self.store.get(key)

        if value is None:
            return None

        payload, expires_at = value

        if expires_at is not None and expires_at <= time.monotonic():
            self.store.pop(key, None)

            return None

        return payload

    def _purge_expired(self) -> None:
        now = time.monotonic()
        expired = [key for key, (_, expires_at) in self.store.items() if expires_at is not None and expires_at <= now]

        for key in expired:
            self.store.pop(key, None)

    def get(self, key: str):
        with self._lock:
            return self._get_live(key)

    def set(self, key: str, value, ttl=None):
        if ttl is not None and ttl <= 0:
            self.delete(key)

            return

        expires_at = None if ttl is None else time.monotonic() + float(ttl)

        with self._lock:
            self._purge_expired()
            self.store[key] = (value, expires_at)

    def delete(self, key: str):
        with self._lock:
            self.store.pop(key, None)

    def clear(self):
        with self._lock:
            self.store.clear()

    def clear_prefix(self, prefix: str):
        if not isinstance(prefix, str):
            raise TypeError("Cache prefixes must be strings")

        with self._lock:
            for key in [key for key in self.store if key.startswith(prefix)]:
                self.store.pop(key, None)
