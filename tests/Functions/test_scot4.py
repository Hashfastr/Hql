from types import SimpleNamespace

import pytest

from Hql.Exceptions import HqlExceptions as hqle
from Hql.Data import Data
from Hql.Functions.scot4 import scot4


def scot4_config(**overrides):
    conf = {
        'default': 'primary',
        'servers': [
            {
                'name': 'primary',
                'host': 'https://scot.example.test',
                'apikey': 'test-api-key',
            }
        ],
    }
    conf.update(overrides)
    return conf


class RequestRecorder:
    def __init__(self):
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(status_code=200, text='{}')


def test_tls_verification_defaults_to_enabled(monkeypatch):
    request = RequestRecorder()
    monkeypatch.setattr('Hql.Functions.scot4.requests.post', request)
    function = scot4([], conf=scot4_config())

    function.post('/api/v1/alertgroup/', {'subject': 'test'})

    assert function.verify_tls is True
    assert request.calls[0]['verify'] is True


def test_tls_verification_can_be_disabled_for_all_request_methods(monkeypatch):
    post = RequestRecorder()
    get = RequestRecorder()
    put = RequestRecorder()
    monkeypatch.setattr('Hql.Functions.scot4.requests.post', post)
    monkeypatch.setattr('Hql.Functions.scot4.requests.get', get)
    monkeypatch.setattr('Hql.Functions.scot4.requests.put', put)
    function = scot4([], conf=scot4_config(verify_tls=False))

    function.post('/post', {})
    function.get('/get')
    function.get('/get-json', json={'id': 1})
    function.get('/get-params', params={'name': 'example'})
    function.put('/put', {})

    calls = post.calls + get.calls + put.calls
    assert function.verify_tls is False
    assert all(call['verify'] is False for call in calls)


@pytest.mark.parametrize('value', [None, 0, 1, 'false'])
def test_tls_verification_must_be_boolean(value):
    with pytest.raises(hqle.ConfigException, match='verify_tls must be a boolean'):
        scot4([], conf=scot4_config(verify_tls=value))


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

from Hql.Expressions.Literals import Bool, StringLiteral
from Hql.Expressions.References import NamedExpression, NamedReference


def param(name, value):
    return NamedExpression([NamedReference(name)], value)


def two_server_config(**overrides):
    conf = scot4_config(**overrides)
    conf['servers'].append({
        'name': 'other',
        'host': 'https://other.example.test',
        'apikey': 'other-api-key',
    })
    return conf


def test_server_parameter_selects_configured_server():
    function = scot4([param('server', StringLiteral('other'))], conf=two_server_config())

    assert function.server['host'] == 'https://other.example.test'


def test_server_parameter_with_string_literal_name():
    arg = NamedExpression([StringLiteral('server')], StringLiteral('other'))
    function = scot4([arg], conf=two_server_config())

    assert function.server['name'] == 'other'


def test_unknown_server_parameter_raises():
    with pytest.raises(hqle.ArgumentException, match='invalid scot4 server'):
        scot4([param('server', StringLiteral('missing'))], conf=two_server_config())


def test_union_parameter_overrides_config(monkeypatch):
    union_calls = []

    class FakeUnion:
        def __init__(self, *args):
            pass

        def eval(self, ctx):
            union_calls.append(ctx)
            return ctx.data

    import sys
    import Hql.Operators.Union  # noqa: F401  ensure the module is loaded
    monkeypatch.setattr(sys.modules['Hql.Operators.Union'], 'Union', FakeUnion)
    monkeypatch.setattr('Hql.Functions.scot4.requests.post', RequestRecorder())

    hac = SimpleNamespace(get=lambda key: [] if key in ('references', 'tags') else 'title')

    function = scot4([param('union', Bool(False))], conf=scot4_config(always_union=True))
    assert function.params['union'] is False
    function.post_alertgroup(Data(), hac)
    assert union_calls == []

    function = scot4([param('union', Bool(True))], conf=scot4_config())
    assert function.params['union'] is True
    function.post_alertgroup(Data(), hac)
    assert len(union_calls) == 1


def test_union_defaults_off():
    assert scot4([], conf=scot4_config()).params['union'] is False


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

def test_all_get_requests_have_timeout(monkeypatch):
    get = RequestRecorder()
    monkeypatch.setattr('Hql.Functions.scot4.requests.get', get)
    function = scot4([], conf=scot4_config())

    function.get('/get')
    function.get('/get-json', json={'id': 1})
    function.get('/get-params', params={'name': 'example'})

    assert all(call['timeout'] == function.timeout for call in get.calls)


def test_link_guide_skips_already_linked_signature(monkeypatch):
    post = RequestRecorder()
    monkeypatch.setattr('Hql.Functions.scot4.requests.post', post)
    function = scot4([], conf=scot4_config())
    monkeypatch.setattr(function, 'get_guide_signatures', lambda guide: [{'id': 7}])

    assert function.link_guide({'id': 1}, {'id': 7}) == ''
    assert post.calls == []


def test_link_guide_links_new_signature(monkeypatch):
    post = RequestRecorder()
    monkeypatch.setattr('Hql.Functions.scot4.requests.post', post)
    function = scot4([], conf=scot4_config())
    monkeypatch.setattr(function, 'get_guide_signatures', lambda guide: [{'id': 3}])

    function.link_guide({'id': 1}, {'id': 7})

    assert len(post.calls) == 1
    assert post.calls[0]['url'].endswith('/api/v1/link/')
    assert post.calls[0]['json']['v0_id'] == 7
