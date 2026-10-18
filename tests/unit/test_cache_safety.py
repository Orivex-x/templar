from templar.cache import CacheManager, FileCache, NullCache


def test_file_cache_clear_leaves_non_cache_json_untouched(tmp_path):
    unrelated = tmp_path / "settings.json"
    unrelated.write_text('{"keep": true}', encoding="utf-8")
    cache = FileCache(tmp_path)
    cache.set("answer", 42)

    cache.clear()

    assert unrelated.read_text(encoding="utf-8") == '{"keep": true}'
    assert cache.get("answer") is None


def test_disabled_cache_does_not_construct_configured_backend():
    manager = CacheManager({"cache_enabled": False, "cache_backend": "redis"})

    assert isinstance(manager.provider, NullCache)
    assert manager.provider.get("anything") is None
