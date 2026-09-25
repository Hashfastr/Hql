from Hql.Config import Config
from Hql.Context import Context
from Hql.Data import Data
from Hql.Threading import HacThread, QueryPool


class _CachingDetection:
    id = "cache-test"
    hac = None

    def __init__(self):
        self.seen_ctx = None

    def run(self, query_time=None, ctx=None):
        self.seen_ctx = ctx
        operator_ctx = ctx.copy()
        operator_ctx.cache.set("hac-result", None, "cached")
        return operator_ctx


def test_hac_thread_uses_assigned_context_and_writes_back():
    root = Context(Data())
    local = root.copy()
    detection = _CachingDetection()
    thread = HacThread(detection, ctx=local)

    thread.run()

    assert detection.seen_ctx is local
    assert root.cache.get("hac-result") == "cached"


def test_query_pool_writes_query_cache_to_parent(monkeypatch):
    root = Context(Data())
    pool = QueryPool(auto_run=False, cache=root.cache)

    def fake_run_query(text, config, name="", ctx=None, **kwargs):
        ctx.cache.set("query-result", None, "cached")
        return Data()

    monkeypatch.setattr("Hql.Helpers.run_query", fake_run_query)
    pool.add_query("query", Config())
    pool.pool[0].threaded = False

    pool.start()
    pool.get_completed()

    assert pool.ctx.cache.parent is root.cache
    assert root.cache.get("query-result") == "cached"
