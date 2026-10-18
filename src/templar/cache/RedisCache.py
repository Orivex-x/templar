import sys
import json

from .CacheProvider import CacheProvider

sys.dont_write_bytecode = True

"""
The recommended production backend cache
"""
class RedisCache(CacheProvider):
    DELETE_BATCH_SIZE = 500
    def __init__(self, host="localhost", port=6379, db=0, url=None, prefix="templar:"):
        import redis
        self.client = redis.Redis.from_url(url) if url else redis.Redis(host=host, port=port, db=db)
        self.prefix = prefix

    def _key(self, key: str) -> str:
        if not isinstance(key, str):
            raise TypeError("Cache keys must be strings")

        return f"{self.prefix}{key}"

    def get(self, key: str):
        value = self.client.get(self._key(key))

        if value is None:
            return None

        try:
            return json.loads(value.decode("utf-8") if isinstance(value, bytes) else value)
        except (TypeError, ValueError):
            self.delete(key)

            return None

    def set(self, key: str, value, ttl=None):
        if ttl is not None and ttl <= 0:
            self.delete(key)

            return

        try:
            encoded = json.dumps(value)
        except (TypeError, ValueError) as exc:
            raise TypeError("RedisCache values must be JSON serializable") from exc

        self.client.set(self._key(key), encoded, ex=None if ttl is None else max(1, int(ttl)))

    def delete(self, key: str):
        self.client.delete(self._key(key))

    def clear(self):
        self._delete_matching(f"{self.prefix}*")

    def clear_prefix(self, prefix: str):
        if not isinstance(prefix, str):
            raise TypeError("Cache prefixes must be strings")

        self._delete_matching(f"{self.prefix}{self._escape_glob(prefix)}*")

    @staticmethod
    def _escape_glob(value: str) -> str:
        """Treat cache namespaces as literal keys, not Redis glob syntax."""
        return (
            value.replace("\\", "\\\\")
            .replace("*", "\\*")
            .replace("?", "\\?")
            .replace("[", "\\[")
            .replace("]", "\\]")
        )

    def _delete_matching(self, pattern: str) -> None:
        """Delete scan results incrementally instead of retaining every key."""
        batch = []

        for key in self.client.scan_iter(match=pattern):
            batch.append(key)

            if len(batch) >= self.DELETE_BATCH_SIZE:
                self.client.delete(*batch)
                batch.clear()
        if batch:
            self.client.delete(*batch)
