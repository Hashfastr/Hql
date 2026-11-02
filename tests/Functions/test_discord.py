from types import SimpleNamespace

import pytest

from Hql.Context import Context
from Hql.Data import Data, Table
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Expressions.Literals import Integer, StringLiteral
from Hql.Expressions.References import NamedExpression, NamedReference
from Hql.Functions.discord import DESCRIPTION_LIMIT, discord, table_text
from Hql.Hac import Hac


GUILDS = [{'id': '100', 'name': 'DEATHCon'}, {'id': '200', 'name': 'Other'}]
CHANNELS = [
    {'id': '300', 'name': 'alerts', 'type': 2},  # voice channel of the same name
    {'id': '301', 'name': 'alerts', 'type': 0},
    {'id': '302', 'name': 'general', 'type': 0},
]


def discord_config(**overrides):
    conf = {
        'token': 'test-token',
        'default_server': 'DEATHCon',
        'default_channel': 'alerts',
    }
    conf.update(overrides)
    return conf


def param(name, value):
    return NamedExpression([NamedReference(name)], value)


class FakeDiscord:
    """Records requests and answers like the Discord API."""

    def __init__(self, status_code=200):
        self.gets = []
        self.posts = []
        self.status_code = status_code

    def get(self, url, **kwargs):
        self.gets.append(url)
        body = GUILDS if url.endswith('/users/@me/guilds') else CHANNELS
        return SimpleNamespace(status_code=200, text='', json=lambda: body)

    def post(self, url, **kwargs):
        self.posts.append({'url': url, **kwargs})
        return SimpleNamespace(status_code=self.status_code, text='Missing Access', json=lambda: {'id': '999'})


@pytest.fixture
def api(monkeypatch):
    fake = FakeDiscord()
    monkeypatch.setattr('Hql.Functions.discord.requests.get', fake.get)
    monkeypatch.setattr('Hql.Functions.discord.requests.post', fake.post)
    return fake


def alerts_ctx(rows=None, hac=None):
    rows = rows if rows is not None else [
        {'IpAddress': '10.0.0.5', 'TargetUserName': 'alice', 'Requests': 3},
    ]
    return Context(data=Data([Table(init_data=rows, name='kerberoast')]), symbol_table={}, hac=hac)


def hac():
    return Hac({'title': 'Kerberoasting', 'id': 'abc-123', 'level': 'high', 'description': 'Many RC4 tickets', 'status': 'test'}, 'test')


def test_posts_table_alert_to_named_channel(api):
    out = discord([], conf=discord_config()).eval(alerts_ctx(hac=hac()))

    assert api.gets[-1].endswith('/guilds/100/channels')
    assert len(api.posts) == 1
    post = api.posts[0]
    assert post['url'].endswith('/channels/301/messages')
    assert post['headers']['Authorization'] == 'Bot test-token'

    embed = post['json']['embeds'][0]
    assert embed['title'] == 'Kerberoasting'
    assert embed['color'] == 0xf57c00
    assert embed['description'].startswith('Many RC4 tickets\n\n```\n')
    assert 'IpAddress' in embed['description'] and 'alice' in embed['description']
    assert embed['footer']['text'] == 'kerberoast: showing 1 of 1 rows'
    assert {'name': 'Detection', 'value': 'abc-123', 'inline': False} in embed['fields']

    row = list(out)[0].to_dicts()[0]
    assert row['status'] == 'posted' and row['message_id'] == '999' and row['rows'] == 1


def test_parameters_override_defaults(api):
    function = discord([param('server', StringLiteral('Other')), param('channel', StringLiteral('#general'))], conf=discord_config())
    function.eval(alerts_ctx())

    assert api.gets[-1].endswith('/guilds/200/channels')
    assert api.posts[0]['url'].endswith('/channels/302/messages')


def test_ids_skip_lookups(api):
    function = discord([param('server', StringLiteral('100')), param('channel', StringLiteral('555'))], conf=discord_config())
    function.eval(alerts_ctx())

    assert api.gets == []
    assert api.posts[0]['url'].endswith('/channels/555/messages')


def test_without_hac_uses_table_name(api):
    discord([], conf=discord_config()).eval(alerts_ctx())

    embed = api.posts[0]['json']['embeds'][0]
    assert embed['title'] == 'Hql alert: kerberoast'
    assert embed['description'].startswith('```\n')


def test_unknown_server_raises(api):
    function = discord([param('server', StringLiteral('Nope'))], conf=discord_config())
    with pytest.raises(hqle.ArgumentException, match='server named Nope'):
        function.eval(alerts_ctx())


def test_unknown_channel_raises(api):
    function = discord([param('channel', StringLiteral('missing'))], conf=discord_config())
    with pytest.raises(hqle.ArgumentException, match='channel named missing'):
        function.eval(alerts_ctx())


def test_failed_post_raises(monkeypatch):
    fake = FakeDiscord(status_code=403)
    monkeypatch.setattr('Hql.Functions.discord.requests.get', fake.get)
    monkeypatch.setattr('Hql.Functions.discord.requests.post', fake.post)

    with pytest.raises(hqle.ConfigException, match='403: Missing Access'):
        discord([], conf=discord_config()).eval(alerts_ctx())


def test_invalid_arguments_raise():
    with pytest.raises(hqle.ArgumentException, match='Invalid parameter given'):
        discord([param('guild', StringLiteral('x'))], conf=discord_config())
    with pytest.raises(hqle.ArgumentException, match='Invalid value'):
        discord([param('channel', Integer(5))], conf=discord_config())
    with pytest.raises(hqle.ArgumentException, match='Missing required parameter channel'):
        discord([], conf=discord_config(default_channel=None))


def test_empty_results_do_not_post(api):
    out = discord([], conf=discord_config()).eval(alerts_ctx(rows=[]))

    assert api.posts == []
    assert len(out) == 0


def test_no_token_skips_without_requests(api):
    out = discord([], conf=discord_config(token='')).eval(alerts_ctx())

    assert api.gets == [] and api.posts == []
    assert list(out)[0].to_dicts()[0]['status'] == 'skipped: no discord token configured'


def test_row_limit_and_size_limit(api):
    rows = [{'host': f'host-{i}', 'cmd': 'x' * 200} for i in range(500)]
    discord([], conf=discord_config(row_limit=400)).eval(alerts_ctx(rows=rows))

    embed = api.posts[0]['json']['embeds'][0]
    assert len(embed['description']) <= DESCRIPTION_LIMIT
    shown = int(embed['footer']['text'].split('showing ')[1].split(' of')[0])
    assert 0 < shown < 400
    assert embed['footer']['text'].endswith('of 500 rows')


def test_table_text_aligns_columns():
    text, kept = table_text([{'a': 'x', 'bb': 1}, {'a': 'longer', 'bb': None}, {'a': 'list', 'bb': ['p', 'q']}], 1000)

    assert kept == 3
    assert text.split('\n') == [
        'a      | bb',
        '-------+-----',
        'x      | 1',
        'longer |',
        'list   | p, q',
    ]
