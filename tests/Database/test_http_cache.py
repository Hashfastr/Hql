from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from Hql.Cache import Session as CacheSession
from Hql.Context import Context
from Hql.Data import Data
from Hql.Database.CSV import CSV
from Hql.Database.JSON import JSON


BODIES = {
    JSON: '[{"host": "a", "count": 1}, {"host": "b", "count": 2}]',
    CSV: 'host,count\na,1\nb,2\n',
}


class FakeSession:
    """Stands in for requests.Session and counts real fetches."""

    def __init__(self, text):
        self.text = text
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        return SimpleNamespace(status_code=200, text=self.text)


def http_db(cls, backing, url='https://files.example.test/hosts'):
    db = cls({'conf': {}}, name='remote', session=CacheSession(session=backing))
    db.urls.append(url)
    return db


@pytest.mark.parametrize('cls', [JSON, CSV])
def test_default_session_is_a_cache_session(cls):
    db = cls({'conf': {}})

    assert isinstance(db._session, CacheSession)
    assert db._session.cache is db.cache


@pytest.mark.parametrize('cls', [JSON, CSV])
def test_eval_binds_session_to_context_cache(cls):
    backing = FakeSession(BODIES[cls])
    db = http_db(cls, backing)
    ctx = Context(Data())

    db.eval(ctx)

    assert db.cache is ctx.cache
    assert db._session.cache is ctx.cache


@pytest.mark.parametrize('cls', [JSON, CSV])
def test_repeated_eval_fetches_once(cls):
    backing = FakeSession(BODIES[cls])
    db = http_db(cls, backing)
    ctx = Context(Data())

    first = db.eval(ctx).data
    second = db.eval(ctx).data

    assert len(backing.calls) == 1
    for data in (first, second):
        table = list(data)[0]
        assert table.df['host'].to_list() == ['a', 'b']


# each database() call builds a new instance, so the cache has to live on the context
@pytest.mark.parametrize('cls', [JSON, CSV])
def test_instances_share_the_context_cache(cls):
    backing = FakeSession(BODIES[cls])
    ctx = Context(Data())

    http_db(cls, backing).eval(ctx)
    http_db(cls, backing).eval(ctx)
    http_db(cls, backing, url='https://files.example.test/other').eval(ctx)

    assert backing.calls == ['https://files.example.test/hosts', 'https://files.example.test/other']


# the compiler deep copies databases
@pytest.mark.parametrize('cls', [JSON, CSV])
def test_deepcopy_keeps_caching(cls):
    backing = FakeSession(BODIES[cls])
    db = http_db(cls, backing)
    ctx = Context(Data())

    db.eval(ctx)
    copy.deepcopy(db).eval(ctx)

    assert len(backing.calls) == 1


def test_default_session_fetches_through_requests(monkeypatch):
    import requests

    backing = FakeSession(BODIES[JSON])
    monkeypatch.setattr(requests.Session, 'get', lambda self, url, **kwargs: backing.get(url, **kwargs))
    db = JSON({'conf': {}}, name='remote')
    db.urls.append('https://files.example.test/hosts')
    ctx = Context(Data())

    db.eval(ctx)
    db.eval(ctx)

    assert backing.calls == ['https://files.example.test/hosts']
