from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest
import requests

from Hql.Context import Context
from Hql.Data import Data
from Hql.Database.CSV import CSV
from Hql.Database.JSON import JSON


BODIES = {
    JSON: '[{"host": "a", "count": 1}, {"host": "b", "count": 2}]',
    CSV: 'host,count\na,1\nb,2\n',
}

SUFFIX = {JSON: 'json', CSV: 'csv'}


class FakeSession:
    """Stands in for requests.Session and counts real fetches."""

    def __init__(self, text):
        self.text = text
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        return SimpleNamespace(status_code=200, text=self.text)


def http_db(cls, backing, url='https://files.example.test/hosts'):
    db = cls({'conf': {}}, name='remote', session=backing)
    db.urls.append(url)
    return db


def hosts(data):
    return list(data)[0].df['host'].to_list()


@pytest.mark.parametrize('cls', [JSON, CSV])
def test_default_session_is_a_plain_requests_session(cls):
    db = cls({'conf': {}})

    assert type(db._session) is requests.Session


@pytest.mark.parametrize('cls', [JSON, CSV])
def test_repeated_eval_fetches_once(cls):
    backing = FakeSession(BODIES[cls])
    db = http_db(cls, backing)
    ctx = Context(Data())

    first = db.eval(ctx).data
    second = db.eval(ctx).data

    assert len(backing.calls) == 1
    assert hosts(first) == hosts(second) == ['a', 'b']


@pytest.mark.parametrize('cls', [JSON, CSV])
def test_repeated_eval_loads_once(cls, monkeypatch):
    backing = FakeSession(BODIES[cls])
    db = http_db(cls, backing)
    ctx = Context(Data())
    loads = []
    load = db.load
    monkeypatch.setattr(db, 'load', lambda: loads.append(True) or load())

    db.eval(ctx)
    db.eval(ctx)

    assert len(loads) == 1


@pytest.mark.parametrize('cls', [JSON, CSV])
def test_local_files_are_cached(cls, tmp_path):
    path = tmp_path / f'hosts.{SUFFIX[cls]}'
    path.write_text(BODIES[cls])
    ctx = Context(Data())

    def file_db():
        db = cls({'conf': {'local-base': str(tmp_path)}}, name='local')
        db.files.append(path.name)
        return db

    file_db().eval(ctx)
    path.unlink()

    assert hosts(file_db().eval(ctx).data) == ['a', 'b']


# each database() call builds a new instance, so the cache has to live on the context
@pytest.mark.parametrize('cls', [JSON, CSV])
def test_instances_share_the_context_cache(cls):
    backing = FakeSession(BODIES[cls])
    ctx = Context(Data())

    http_db(cls, backing).eval(ctx)
    http_db(cls, backing).eval(ctx)
    http_db(cls, backing, url='https://files.example.test/other').eval(ctx)

    assert backing.calls == ['https://files.example.test/hosts', 'https://files.example.test/other']


@pytest.mark.parametrize('cls', [JSON, CSV])
def test_child_context_reads_parent_cache(cls):
    backing = FakeSession(BODIES[cls])
    root = Context(Data())

    http_db(cls, backing).eval(root)
    http_db(cls, backing).eval(root.fork())

    assert len(backing.calls) == 1


@pytest.mark.parametrize('cls', [JSON, CSV])
def test_limits_are_part_of_the_key(cls):
    backing = FakeSession(BODIES[cls])
    ctx = Context(Data())

    http_db(cls, backing).eval(ctx)
    limited = http_db(cls, backing)
    limited.set_limit('*', 1)
    data = limited.eval(ctx).data

    assert len(backing.calls) == 2
    assert hosts(data) == ['a']


# the compiler deep copies databases
@pytest.mark.parametrize('cls', [JSON, CSV])
def test_deepcopy_keeps_caching(cls):
    backing = FakeSession(BODIES[cls])
    db = http_db(cls, backing)
    ctx = Context(Data())

    db.eval(ctx)
    copy.deepcopy(db).eval(ctx)

    assert len(backing.calls) == 1


# operators work on ctx.data, they must not be able to change what's cached
@pytest.mark.parametrize('cls', [JSON, CSV])
def test_cached_data_is_isolated_from_callers(cls):
    backing = FakeSession(BODIES[cls])
    db = http_db(cls, backing)
    ctx = Context(Data())

    first = db.eval(ctx).data
    table = list(first)[0]
    table.truncate(1)
    table.schema.schema = None
    first.tables.clear()

    second = db.eval(ctx).data

    assert hosts(second) == ['a', 'b']
    assert len(list(second)[0].schema)
