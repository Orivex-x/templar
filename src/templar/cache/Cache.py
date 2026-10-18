import sys
from .CacheProvider import CacheProvider

sys.dont_write_bytecode = True

class Cache:
    def __init__(self, provider: CacheProvider, namespace: str | None = None):
        self.provider = provider

        if namespace is not None and (not isinstance(namespace, str) or not namespace.strip()):
            raise ValueError("Cache namespace must be a non-empty string")

        self.namespace = namespace.strip() if namespace else None

    def _key(self, key: str) -> str:
        if not isinstance(key, str):
            raise TypeError("Cache keys must be strings")

        return f"{self.namespace}:{key}" if self.namespace else key

    def get(self, key: str):
        return self.provider.get(self._key(key))
    
    def set(self, key: str, value, ttl=None):
        return self.provider.set(self._key(key), value, ttl)

    def delete(self, key: str):
        return self.provider.delete(self._key(key))

    def clear(self):
        if self.namespace:
            return self.provider.clear_prefix(f"{self.namespace}:")

        return self.provider.clear()
