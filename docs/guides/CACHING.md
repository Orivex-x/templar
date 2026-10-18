# Caching Guide

Templar includes a high-performance caching layer supporting memory, filesystem, and Redis cache providers.

---

## 1. Supported Cache Backends

- **`MemoryCache`:** In-memory dictionary cache. Ideal for local development and single-process instances.
- **`FileCache`:** Disk-persisted cache. Useful for persisting cached items between server restarts without external services.
- **`RedisCache`:** High-performance distributed cache for production multi-worker environments (requires `pip install "templar[cache]"`).
- **`NullCache`:** No-op cache useful for test environments.

---

## 2. Configuration

Configure your cache backend in `templar.config.yml`:

```yaml
dev:
  cache_backend: memory
  cache_ttl: 300  # Default TTL in seconds

prod:
  cache_backend: redis
  cache_redis_url: ${REDIS_URL}  # e.g., redis://localhost:6379/0
  cache_namespace: myapp_prod
  cache_ttl: 3600
```

---

## 3. Cache API Usage

Access the configured cache instance directly from `templar.cache`:

```python
from templar.cache import CacheManager
from templar.Config import Config

config = Config()
cache = CacheManager.get_cache(config)

# Store a value (with optional TTL in seconds)
cache.set("weather_data_london", {"temp": 18, "condition": "Sunny"}, ttl=600)

# Retrieve a value
weather = cache.get("weather_data_london")
if weather:
    print(f"Temperature: {weather['temp']}°C")

# Delete a key
cache.delete("weather_data_london")

# Clear entire cache / namespace
cache.clear()
```

---

## 4. Cache Namespacing

In shared Redis environments, Templar namespaces all keys to avoid collision with other projects or environments:

```python
# In templar.config.yml:
# cache_namespace: myproject_v1

# Stored key in Redis: "myproject_v1:weather_data_london"
```

Calling `cache.clear()` will only purge keys matching the configured namespace prefix.
