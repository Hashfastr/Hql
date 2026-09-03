from types import SimpleNamespace

import pytest

from Hql.Exceptions import HqlExceptions as hqle
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
