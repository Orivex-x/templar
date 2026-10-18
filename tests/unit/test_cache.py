"""Cache provider contract tests."""

import time

import pytest

from templar.cache import Cache, CacheManager, FileCache, MemoryCache
from templar.cache.RedisCache import RedisCache
from templar.db import create_database


@pytest.mark.parametrize("provider", [MemoryCache(), FileCache])
def test_cache_providers_store_expire_and_delete_values(provider, tmp_path):
    if provider is FileCache:
        provider = FileCache(tmp_path / "cache")

    cache = Cache(provider)

    cache.set("answer", {"value": 42})

    assert cache.get("answer") == {"value": 42}

    cache.delete("answer")

    assert cache.get("answer") is None

    cache.set("temporary", "value", ttl=0.01)
    time.sleep(0.02)

    assert cache.get("temporary") is None

    cache.set("one", 1)
    cache.set("two", 2)
    cache.clear()

    assert cache.get("one") is None
    assert cache.get("two") is None


def test_cache_manager_uses_the_active_cache_backend(tmp_path):
    manager = CacheManager({"cache_backend": "file", "cache_file": {"directory": str(tmp_path)}})
    manager.provider.set("key", "value")

    assert manager.provider.get("key") == "value"


@pytest.mark.parametrize("provider", [MemoryCache(), FileCache])
def test_namespaced_cache_clear_preserves_other_namespaces(provider, tmp_path):
    if provider is FileCache:
        provider = FileCache(tmp_path / "cache")

    first = Cache(provider, namespace="first")
    second = Cache(provider, namespace="second")
    first.set("key", "first")
    second.set("key", "second")

    first.clear()

    assert first.get("key") is None
    assert second.get("key") == "second"


def test_sql_orm_rejects_mongodb_explicitly():
    with pytest.raises(RuntimeError, match="MongoDB is not supported"):
        create_database({"db_engine": "mongodb", "db_uri": "mongodb://localhost/test"})


def test_redis_cache_clear_deletes_scan_results_in_bounded_batches():
    class FakeRedis:
        def __init__(self):
            self.deleted = []

        def scan_iter(self, match):
            assert match == "templar:project:*"

            return iter([f"templar:project:{index}" for index in range(1_001)])

        def delete(self, *keys):
            self.deleted.append(keys)

    cache = RedisCache.__new__(RedisCache)
    cache.client = FakeRedis()
    cache.prefix = "templar:"
    cache.DELETE_BATCH_SIZE = 500

    cache.clear_prefix("project:")

    assert [len(batch) for batch in cache.client.deleted] == [500, 500, 1]


def test_redis_cache_clear_prefix_escapes_namespace_glob_metacharacters():
    class FakeRedis:
        def scan_iter(self, match):
            self.match = match

            return iter(())

        def delete(self, *_keys):
            raise AssertionError("No keys should be deleted in this test")

    cache = RedisCache.__new__(RedisCache)
    cache.client = FakeRedis()
    cache.prefix = "templar:"

    cache.clear_prefix("tenant[*]?:")

    assert cache.client.match == r"templar:tenant\[\*\]\?:*"
