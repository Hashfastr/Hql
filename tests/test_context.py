from copy import deepcopy

import pytest

from Hql.Compiler import HqlCompiler
from Hql.Config import Config
from Hql.Context import (
    Context,
    get_func,
    get_type,
    register_func,
    register_type,
    type_registry,
)
from Hql.Data import Data
from Hql.Exceptions import HqlExceptions as hqle


class TestTypeRegistry:
    def test_get_type_returns_registered_class(self):
        # int is registered on import as "hql_int"
        assert get_type("hql_int") is not None

    def test_get_type_unknown_raises(self):
        with pytest.raises(hqle.CompilerException):
            get_type("hql_definitely_not_a_type")

    def test_register_type_stores_class(self):
        @register_type("hql_test_registration_marker")
        class _Marker:
            pass

        assert type_registry["hql_test_registration_marker"] is _Marker
        del type_registry["hql_test_registration_marker"]


class TestFuncRegistry:
    def test_get_func_unknown_raises(self):
        with pytest.raises(hqle.CompilerException):
            get_func("definitely_not_a_func")

    def test_register_func_rejects_non_function(self):
        with pytest.raises(hqle.CompilerException):
            @register_func("bad_registration_marker")
            class _NotAFunction:
                pass


class TestContext:
    def test_default_construction(self):
        ctx = Context(data=Data())
        assert ctx.data is not None
        assert ctx.symbol_table == {}
        assert ctx.macros == {}

    def test_bool_reflects_data(self):
        assert not Context(data=Data())

    def test_copy_preserves_data_reference(self):
        d = Data()
        ctx = Context(data=d)
        copy = ctx.copy()
        assert copy.data is d

    def test_copy_preserves_cache_identity(self):
        ctx = Context(data=Data())

        copied = ctx.copy()

        assert copied.cache is ctx.cache

    def test_fork_creates_one_child_cache(self):
        ctx = Context(data=Data())

        copied = ctx.fork()

        assert copied.cache is not ctx.cache
        assert copied.cache.parent is ctx.cache

    def test_deepcopy_preserves_cache_identity(self):
        ctx = Context(data=Data(), symbol_table={"nested": {"value": 1}})

        copied = deepcopy(ctx)

        assert copied is not ctx
        assert copied.symbol_table is not ctx.symbol_table
        assert copied.cache is ctx.cache

    def test_compiler_deepcopy_preserves_cache_identity(self):
        compiler = HqlCompiler(Config())

        copied = deepcopy(compiler)

        assert copied.ctx.cache is compiler.ctx.cache

    def test_compiler_uses_explicit_empty_context(self):
        class Root:
            def __init__(self):
                self.seen = None

            def eval(self, ctx):
                self.seen = ctx
                return ctx

        compiler = HqlCompiler(Config())
        compiler.root = Root()
        ctx = Context(Data())

        result = compiler.run(ctx)

        assert result is ctx
        assert compiler.root.seen is ctx

    def test_merge_into_target_preserves_target_cache(self):
        target = Context(data=Data())
        left = target.copy()
        right = target.copy()
        left.symbol_table["left"] = 1
        right.symbol_table["right"] = 2

        merged = Context.merge([left, right], target=target)

        assert merged is target
        assert merged.cache is target.cache
        assert merged.symbol_table == {"left": 1, "right": 2}

    def test_get_func_unknown_raises(self):
        ctx = Context(data=Data())
        with pytest.raises(hqle.CompilerException):
            ctx.get_func("nonexistent_ctx_func")

    def test_get_db_types_returns_list(self):
        ctx = Context(data=Data())
        assert isinstance(ctx.get_db_types(), list)

    def test_symbol_table_isolated_across_copies(self):
        # constructor deepcopies, so mutating copy shouldn't touch original
        original = {"x": 1}
        ctx = Context(data=Data(), symbol_table=original)
        ctx.symbol_table["x"] = 99
        assert original["x"] == 1
