"""Performance profiling and optimization decorators."""

import sys
import time
import hashlib
import json
import warnings
from functools import wraps
from typing import Callable, Dict, Any
from templar.core.Logger import get_logger

sys.dont_write_bytecode = True


def configure_result_cache(cache) -> None:
    """Deprecated compatibility shim.

    Cache selection is intentionally explicit now. A process-global backend
    lets a later TemplarServer silently redirect decorators owned by an
    earlier server, which is unsafe for multi-project processes.
    """
    warnings.warn(
        "configure_result_cache() no longer configures a global cache; pass "
        "cache=... to cache_result() or use server.cache_result().",
        DeprecationWarning,
        stacklevel=2,
    )


class PerformanceProfiler:
    """Global performance profiler."""
    
    _measurements: Dict[str, list] = {}
    
    @classmethod
    def record(cls, name: str, elapsed_ms: float) -> None:
        """Record a measurement."""
        if name not in cls._measurements:
            cls._measurements[name] = []

        cls._measurements[name].append(elapsed_ms)
    
    @classmethod
    def get_stats(cls, name: str) -> Dict[str, float]:
        """Get statistics for a measurement."""
        if name not in cls._measurements or not cls._measurements[name]:
            return {}
        
        measurements = cls._measurements[name]

        return {
            "count": len(measurements),
            "total": sum(measurements),
            "average": sum(measurements) / len(measurements),
            "min": min(measurements),
            "max": max(measurements),
        }
    
    @classmethod
    def reset(cls) -> None:
        """Reset all measurements."""
        cls._measurements.clear()
    
    @classmethod
    def print_report(cls) -> None:
        """Print performance report."""
        if not cls._measurements:
            print("No measurements recorded")

            return
        
        print("\n" + "=" * 60)
        print("PERFORMANCE REPORT")
        print("=" * 60)
        
        for name in sorted(cls._measurements.keys()):
            stats = cls.get_stats(name)
            print(f"\n{name}:")
            print(f"  Calls: {stats['count']}")
            print(f"  Total: {stats['total']:.2f}ms")
            print(f"  Average: {stats['average']:.2f}ms")
            print(f"  Min: {stats['min']:.2f}ms")
            print(f"  Max: {stats['max']:.2f}ms")


def profile(name: str = None, threshold_ms: float = 0):
    """
    Decorator to profile function execution time.
    
    Args:
        name: Profile name (defaults to function name)
        threshold_ms: Only record if execution time exceeds threshold
        
    Usage:
        @profile(threshold_ms=10)
        def slow_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        profile_name = name or func.__name__
        logger = get_logger(func.__module__)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            
            if elapsed_ms >= threshold_ms:
                PerformanceProfiler.record(profile_name, elapsed_ms)
                logger.debug(
                    f"{profile_name} executed in {elapsed_ms:.2f}ms"
                )
            
            return result
        
        return wrapper
    
    return decorator


def measure_query_time(func: Callable) -> Callable:
    """
    Decorator to measure database query execution time.
    
    Usage:
        @measure_query_time
        def get_users():
            return db.query("SELECT * FROM users")
    """
    logger = get_logger(func.__module__)
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        PerformanceProfiler.record(f"query:{func.__name__}", elapsed_ms)
        
        if elapsed_ms > 100:  # Log slow queries
            logger.warning(
                f"Slow query: {func.__name__} took {elapsed_ms:.2f}ms"
            )
        
        return result
    
    return wrapper


def cache_result(ttl_seconds: int = 300, cache=None, namespace: str | None = None):
    """
    Decorator to cache function results.
    
    Args:
        ttl_seconds: Cache time-to-live
        cache: Optional Templar cache facade/provider. When omitted, this
            decorator owns an isolated expiring in-memory cache. To use a
            server's configured backend, pass ``cache=server.cache`` or use
            ``server.cache_result(...)``.
        namespace: Optional stable namespace for shared cache backends.
        
    Usage:
        @cache_result(ttl_seconds=300)
        def get_user_count():
            return db.query("SELECT COUNT(*) FROM users")
    """
    if namespace is not None and (not isinstance(namespace, str) or not namespace.strip()):
        raise ValueError("Cache namespace must be a non-empty string")

    def decorator(func: Callable) -> Callable:
        from templar.cache import Cache, MemoryCache

        fallback_cache = Cache(MemoryCache())
        cache_prefix = f"templar:result:{namespace + ':' if namespace else ''}{func.__module__}.{func.__qualname__}:"
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            backend = cache or fallback_cache

            try:
                serialized_key = json.dumps([args, kwargs], sort_keys=True, default=repr, separators=(",", ":"))
                cache_key = cache_prefix + hashlib.sha256(serialized_key.encode("utf-8")).hexdigest()
                cached = backend.get(cache_key)

                if isinstance(cached, dict) and cached.get("_templar_cached_result") is True:
                    return cached["value"]
            except (TypeError, ValueError):
                # Cache key/value limitations must never change the wrapped function's behaviour.
                cache_key = None

            result = func(*args, **kwargs)

            if cache_key is not None:
                try:
                    backend.set(cache_key, {"_templar_cached_result": True, "value": result}, ttl=ttl_seconds)
                except (TypeError, ValueError):
                    pass

            return result
        
        return wrapper
    
    return decorator


def lazy_load(func: Callable) -> Callable:
    """
    Decorator to lazy-load resource on first access.
    
    Usage:
        @lazy_load
        def load_config():
            return Config()
    """
    _instance = None
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal _instance

        if _instance is None:
            _instance = func(*args, **kwargs)

        return _instance
    
    return wrapper


def timeit(func: Callable) -> Callable:
    """
    Simple decorator to print execution time.
    
    Usage:
        @timeit
        def my_function():
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start

        print(f"{func.__name__} took {elapsed:.4f}s")

        return result
    
    return wrapper
