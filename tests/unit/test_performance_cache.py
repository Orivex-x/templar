import time

from templar.cache import Cache, FileCache, MemoryCache
from templar.core.Performance import cache_result


def test_cache_result_uses_the_cache_contract_and_expires(tmp_path):
    calls = 0
    cache = Cache(FileCache(tmp_path / "cache"))

    @cache_result(ttl_seconds=0.01, cache=cache)
    def expensive(value):
        nonlocal calls
        calls += 1

        return {"value": value, "call": calls}

    assert expensive("Ada") == {"value": "Ada", "call": 1}
    assert expensive("Ada") == {"value": "Ada", "call": 1}

    time.sleep(0.02)

    assert expensive("Ada") == {"value": "Ada", "call": 2}


def test_cache_result_backends_are_explicit_and_isolated():
    first_cache = Cache(MemoryCache())
    second_cache = Cache(MemoryCache())
    first_calls = second_calls = 0

    @cache_result(cache=first_cache)
    def first(value):
        nonlocal first_calls
        first_calls += 1

        return (value, first_calls)

    @cache_result(cache=second_cache)
    def second(value):
        nonlocal second_calls
        second_calls += 1

        return (value, second_calls)

    assert first("same") == ("same", 1)
    assert second("same") == ("same", 1)
    assert first("same") == ("same", 1)
    assert second("same") == ("same", 1)


def test_cache_result_namespace_prevents_shared_backend_collisions():
    shared_cache = Cache(MemoryCache())
    first_calls = second_calls = 0

    @cache_result(cache=shared_cache, namespace="project-one")
    def first(value):
        nonlocal first_calls
        first_calls += 1

        return (value, first_calls)

    @cache_result(cache=shared_cache, namespace="project-two")
    def second(value):
        nonlocal second_calls
        second_calls += 1

        return (value, second_calls)

    assert first("same") == ("same", 1)
    assert second("same") == ("same", 1)
    assert first("same") == ("same", 1)
    assert second("same") == ("same", 1)


def test_cache_namespace_is_applied_before_the_shared_provider():
    provider = MemoryCache()
    first = Cache(provider, namespace="project-one")
    second = Cache(provider, namespace="project-two")

    first.set("homepage", {"project": "one"})
    second.set("homepage", {"project": "two"})

    assert first.get("homepage") == {"project": "one"}
    assert second.get("homepage") == {"project": "two"}
