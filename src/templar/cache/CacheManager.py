import sys
from .RedisCache import RedisCache
from .FileCache import FileCache
from .MemoryCache import MemoryCache
from .NullCache import NullCache

sys.dont_write_bytecode = True

class CacheManager:
    def __init__(self, config):
        cache_config = self._get(config, "cache", {})
        enabled = self._get(cache_config, "enabled", self._get(config, "cache_enabled", True))

        if enabled is False:
            self.provider = NullCache()

            return

        provider_name = self._get(
            cache_config,
            "provider",
            self._get(config, "cache_backend", "memory"),
        ).lower()

        providers = {
            "redis": RedisCache,
            "file": FileCache,
            "memory": MemoryCache,
            "custom": self._load_custom_provider
        }

        if provider_name not in providers:
            raise ValueError(f"Unsupported cache provider: {provider_name}")

        provider_cls = providers[provider_name]

        if provider_name == "custom":
            self.provider = provider_cls(self._get(cache_config, "custom", {}))
        else:
            provider_config = self._get(cache_config, provider_name, self._get(config, f"cache_{provider_name}", None))

            if provider_name == "redis" and provider_config is None:
                redis_url = self._get(config, "cache_redis_url", None)
                provider_config = {"url": redis_url} if redis_url else None

            if provider_name == "file" and provider_config is None:
                directory = self._get(config, "cache_file_dir", None)
                provider_config = {"directory": directory} if directory else None

            self.provider = self._build_provider(provider_cls, provider_config)

    def _load_custom_provider(self, custom_config):
        cls_path = self._get(custom_config, "class")
        module_name, class_name = cls_path.rsplit(".", 1)
        module = __import__(module_name, fromlist=[class_name])
        cls = getattr(module, class_name)

        return cls(self._get(custom_config, "options", {}))

    def _build_provider(self, provider_cls, provider_config):
        if provider_config is None:
            return provider_cls()

        if isinstance(provider_config, dict):
            try:
                return provider_cls(**provider_config)
            except TypeError:
                return provider_cls(provider_config)

        try:
            return provider_cls(provider_config)
        except TypeError:
            return provider_cls()

    def _get(self, source, key, default=None):
        if isinstance(source, dict):
            return source.get(key, default)

        return getattr(source, key, default)
