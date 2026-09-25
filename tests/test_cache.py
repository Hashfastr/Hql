from copy import deepcopy

from Hql.Cache import Cache
from Hql.Cache.requests import CacheSession


def test_deepcopy_preserves_cache_identity():
    cache = Cache()

    assert deepcopy(cache) is cache


def test_empty_parent_accepts_child_write_back():
    parent = Cache()
    child = Cache(parent=parent)
    child.set("key", None, "value")

    child.write_back()

    assert parent.get("key") == "value"


def test_cache_session_delegates_once_and_reuses_response():
    response = object()
    cache_misses = []

    class BackingSession:
        def __init__(self):
            self.calls = 0

        def get(self, url, **kwargs):
            self.calls += 1
            return response

    backing = BackingSession()
    session = CacheSession(session=backing)

    on_miss = lambda: cache_misses.append(True)
    first = session.get("https://example.test", on_miss=on_miss)
    second = session.get("https://example.test", on_miss=on_miss)

    assert first is response
    assert second is response
    assert backing.calls == 1
    assert len(cache_misses) == 1
