"""No-op cache backend used when caching is disabled."""

from .CacheProvider import CacheProvider


class NullCache(CacheProvider):
    """Preserve the cache API without storing or importing optional backends."""

    def get(self, key: str):
        return None

    def set(self, key: str, value, ttl=None):
        return None

    def delete(self, key: str):
        return None

    def clear(self):
        return None

    def clear_prefix(self, prefix: str):
        return None
