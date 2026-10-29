import pytest

from Hql.Context import Context, get_func
from Hql.Data import Data, Table
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Expressions.Literals import StringLiteral
from Hql.Functions.base64 import base64dec, base64enc, base64off


class TestBase64Encode:
    def test_backslashes_not_escaped(self, empty_ctx):
        out = base64enc([StringLiteral('C:\\Windows')]).preprocess(empty_ctx)
        assert out == StringLiteral('QzpcV2luZG93cw==')

    def test_non_ascii_with_encoding(self, empty_ctx):
        out = base64enc([StringLiteral('é'), StringLiteral('utf-8')]).preprocess(empty_ctx)
        assert out == StringLiteral('w6k=')

    def test_utf16le_encoding(self, empty_ctx):
        out = base64enc([StringLiteral('hi'), StringLiteral('utf-16le')]).preprocess(empty_ctx)
        assert out == StringLiteral('aABpAA==')

    def test_unencodable_raises_argument_exception(self, empty_ctx):
        with pytest.raises(hqle.ArgumentException):
            base64enc([StringLiteral('é')]).preprocess(empty_ctx)

    def test_eval_broadcasts(self):
        ctx = Context(data=Data([Table(init_data=[{'x': 1}], name='t')]))
        out = base64enc([StringLiteral('ABC')]).eval(ctx)
        assert out['t'].series.series.to_list() == ['QUJD']


class TestBase64Decode:
    def test_decode(self, empty_ctx):
        assert base64dec([StringLiteral('aGk=')]).preprocess(empty_ctx) == StringLiteral('hi')

    def test_decode_with_encoding(self, empty_ctx):
        out = base64dec([StringLiteral('w6k='), StringLiteral('utf-8')]).preprocess(empty_ctx)
        assert out == StringLiteral('é')

    def test_invalid_input_raises_argument_exception(self, empty_ctx):
        with pytest.raises(hqle.ArgumentException):
            base64dec([StringLiteral('not base64!')]).preprocess(empty_ctx)

    def test_eval_broadcasts(self):
        ctx = Context(data=Data([Table(init_data=[{'x': 1}], name='t')]))
        out = base64dec([StringLiteral('aGk=')]).eval(ctx)
        assert out['t'].series.series.to_list() == ['hi']


class TestBase64Offset:
    def test_sigma_modifier_name_registered(self):
        assert get_func('base64offset') is base64off

    def test_accepts_conf(self):
        base64off([StringLiteral('hi')], conf={})

    def test_offsets_use_byte_length(self):
        f = base64off([StringLiteral('é'), StringLiteral('utf-8')])
        parts = f.calc_offset('é'.encode('utf-8'))
        assert [x.str() for x in parts] == ['w6', 'Op', 'Dq']

    def test_offsets_ascii(self):
        f = base64off([StringLiteral('http')])
        parts = f.calc_offset(b'http')
        assert [x.str() for x in parts] == ['aHR0c', 'h0dH', 'odHRw']

    def test_preprocess_returns_offsets(self, empty_ctx):
        from Hql.Expressions.Literals import Multivalue

        out = base64off([StringLiteral('é'), StringLiteral('utf-8')]).preprocess(empty_ctx)
        assert isinstance(out, Multivalue)
        assert len(out) == 3
