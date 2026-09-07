import time

from repopulse.cache import SqliteCache


def test_set_and_get_roundtrip(tmp_path):
    cache = SqliteCache(str(tmp_path / "cache.sqlite3"), ttl_seconds=60)
    cache.set("key1", {"a": 1, "b": [1, 2, 3]})
    assert cache.get("key1") == {"a": 1, "b": [1, 2, 3]}


def test_missing_key_returns_none(tmp_path):
    cache = SqliteCache(str(tmp_path / "cache.sqlite3"))
    assert cache.get("nope") is None


def test_expired_entry_returns_none(tmp_path):
    cache = SqliteCache(str(tmp_path / "cache.sqlite3"), ttl_seconds=0)
    cache.set("key1", {"a": 1})
    time.sleep(0.01)
    assert cache.get("key1") is None


def test_clear_removes_all_entries(tmp_path):
    cache = SqliteCache(str(tmp_path / "cache.sqlite3"))
    cache.set("k1", 1)
    cache.set("k2", 2)
    cache.clear()
    assert cache.get("k1") is None
    assert cache.get("k2") is None
