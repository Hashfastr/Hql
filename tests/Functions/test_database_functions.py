import json

import pytest

from Hql.Config import Config
from Hql.Context import Context
from Hql.Data import Data
from Hql.Database.JSON import JSON
from Hql.Expressions.Literals import StringLiteral
from Hql.Expressions.References import NamedReference
from Hql.Functions.file import file
from Hql.Functions.http import http
from Hql.Functions.index import index
from Hql.Functions.macro import macro


@pytest.fixture
def ctx(tmp_path):
    (tmp_path / 'd.json').write_text(json.dumps([{'n': 1}, {'n': 2}]))

    config = Config()
    config.add_database('test', {
        'name': 'json',
        'type': 'JSON',
        'conf': {'local-base': str(tmp_path)},
        'macro': {'everything': {'hql': "database('json').file('d.json')"}},
    })
    config.load_general('test', {'default_db': 'json'})

    return Context(data=Data(), symbol_table={'f': StringLiteral('d.json')}, config=config)


def json_db(ctx):
    dbconf = ctx.config.get_database('json')
    return JSON(dbconf, name='json')


class TestFile:
    def test_preprocess_keeps_resolved_names(self, ctx):
        func = file([NamedReference('f')])
        func.preprocess(ctx)
        assert func.names == [StringLiteral('d.json')]

    def test_eval_uses_let_variable(self, ctx):
        db = file([NamedReference('f')]).eval(ctx, receiver=json_db(ctx))
        assert db.files == ['d.json']

        out = db.eval(ctx).data
        assert out['d.json'].df['n'].to_list() == [1, 2]

    def test_falls_back_to_default_db(self, ctx):
        db = file([StringLiteral('d.json')]).eval(ctx)
        assert isinstance(db, JSON)
        assert db.files == ['d.json']


class TestHttp:
    def test_eval_uses_let_variable(self, ctx):
        db = http([NamedReference('f')]).eval(ctx, receiver=json_db(ctx))
        assert db.urls == ['d.json']

    def test_appends_urls(self, ctx):
        db = http([StringLiteral('a.json')]).eval(ctx, receiver=json_db(ctx))
        db = http([StringLiteral('b.json')]).eval(ctx, receiver=db)
        assert db.urls == ['a.json', 'b.json']

    def test_falls_back_to_default_db(self, ctx):
        db = http([StringLiteral('a.json')]).eval(ctx)
        assert isinstance(db, JSON)
        assert db.urls == ['a.json']


class TestIndex:
    def test_falls_back_to_default_db(self, ctx, monkeypatch):
        added = []
        monkeypatch.setattr(JSON, 'add_index', lambda self, name: added.append(name), raising=False)

        db = index([StringLiteral('logs-*')]).eval(ctx)

        assert isinstance(db, JSON)
        assert added == ['logs-*']


class TestMacro:
    def test_eval_uses_let_variable(self, ctx):
        ctx.symbol_table['m'] = StringLiteral('everything')
        func = macro([NamedReference('m')])

        iset = func.eval(ctx, receiver=json_db(ctx))

        assert func.names == [StringLiteral('everything')]
        assert len(iset.upstream) == 1
