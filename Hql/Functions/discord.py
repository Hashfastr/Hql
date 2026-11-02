from __future__ import annotations
from . import Function
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Context import register_func
import requests
import datetime

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from Hql.Data import Data, Table
    from Hql.Hac import Hac
    from Hql.Context import Context

API = 'https://discord.com/api/v10'

# Discord embed limits
DESCRIPTION_LIMIT = 4096
CELL_WIDTH = 32

# embed side bar colour by HaC level
COLORS = {
    'critical': 0xd32f2f,
    'high': 0xf57c00,
    'medium': 0xfbc02d,
    'low': 0x1976d2,
}
DEFAULT_COLOR = 0x9e9e9e

# text and announcement channels
TEXT_CHANNELS = (0, 5)

def table_text(rows:list[dict], max_chars:int) -> tuple[str, int]:
    """Render rows as a fixed width table, dropping rows from the end until it fits.

    Returns the text and the number of rows kept.
    """
    if not rows:
        return '', 0

    def cell(value) -> str:
        if isinstance(value, list):
            value = ', '.join(str(i) for i in value)
        text = '' if value is None else str(value).replace('\n', ' ')
        return text if len(text) <= CELL_WIDTH else text[:CELL_WIDTH - 1] + '…'

    cols = list(rows[0].keys())
    cells = [[cell(row.get(c)) for c in cols] for row in rows]

    for keep in range(len(cells), 0, -1):
        widths = [max(len(c), *(len(r[i]) for r in cells[:keep])) for i, c in enumerate(cols)]
        lines = [' | '.join(c.ljust(w) for c, w in zip(cols, widths))]
        lines.append('-+-'.join('-' * w for w in widths))
        lines += [' | '.join(v.ljust(w) for v, w in zip(r, widths)) for r in cells[:keep]]

        text = '\n'.join(line.rstrip() for line in lines)
        if len(text) <= max_chars:
            return text, keep

    return '', 0

@register_func('discord')
class discord(Function):
    """Post HQL results to a Discord channel as a table alert."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        from Hql.Expressions.Literals import StringLiteral
        from Hql.Expressions.References import NamedExpression, NamedReference

        Function.__init__(self, args, 0, 2, conf)
        self.params:dict[str, Optional[str]] = {
            'server': self.conf.get('default_server', None),
            'channel': self.conf.get('default_channel', None),
        }

        for i in self.args:
            if not isinstance(i, NamedExpression):
                raise hqle.ArgumentException(f'Invalid argument expression given to discord: {i}')
            # The parser gives names as NamedReferences
            if not isinstance(i.paths[0], (StringLiteral, NamedReference)) or len(i.paths) > 1:
                raise hqle.ArgumentException(f'Invalid parameter name(s) given to discord: {i.paths}')
            val = i.paths[0].str()

            if val not in self.params:
                raise hqle.ArgumentException(f'Invalid parameter given to discord: {val}')

            if not isinstance(i.value, StringLiteral):
                raise hqle.ArgumentException(f'Invalid value given to discord parameter {val}: {i.value.deparse()}')
            self.params[val] = i.value.str()

        for i in self.params:
            if self.params[i] is None:
                raise hqle.ArgumentException(f'Missing required parameter {i} in discord')

        self.server = str(self.params['server'])
        self.channel = str(self.params['channel'])

        self.token = self.conf.get('token', '')
        self.row_limit = self.conf.get('row_limit', 10)
        self.timeout = 5

    def eval(self, ctx: Context, receiver=None) -> object:
        from Hql.Data import Data, Table

        if not ctx.data:
            return Data()

        tables = [i for i in ctx.data if len(i) > 0]
        if not tables:
            return Data()

        if not self.token:
            logging.warning('No discord token configured, skipping the alert')
            res = [self.result(i, 'skipped: no discord token configured') for i in tables]
            return Data([Table(init_data=res)])

        channel = self.resolve_channel(self.resolve_server())

        res = []
        for i in tables:
            message = self.post(f'/channels/{channel}/messages', {'embeds': [self.embed(i, ctx.hac)]})
            res.append(self.result(i, 'posted', message.get('id', '')))

        return Data([Table(init_data=res)])

    def result(self, table:Table, status:str, message_id:str='') -> dict:
        return {
            'table': table.name,
            'server': self.server,
            'channel': self.channel,
            'rows': len(table),
            'status': status,
            'message_id': message_id,
        }

    def headers(self) -> dict:
        return {
            'Authorization': f'Bot {self.token}',
            'User-Agent': 'DiscordBot (https://github.com/Hql, 1.0)',
        }

    def get(self, api:str):
        res = requests.get(API + api, headers=self.headers(), timeout=self.timeout)
        if not 200 <= res.status_code < 300:
            raise hqle.ConfigException(f'Discord GET {api} failed with {res.status_code}: {res.text}')
        return res.json()

    def post(self, api:str, json:dict) -> dict:
        res = requests.post(API + api, headers=self.headers(), json=json, timeout=self.timeout)
        if not 200 <= res.status_code < 300:
            raise hqle.ConfigException(f'Discord POST {api} failed with {res.status_code}: {res.text}')
        return res.json()

    # IDs are used as is, names are looked up through the bot's servers and channels
    def resolve_server(self) -> str:
        if self.server.isdigit():
            return self.server

        for i in self.get('/users/@me/guilds'):
            if i['name'] == self.server:
                return i['id']
        raise hqle.ArgumentException(f'Discord bot is not in a server named {self.server}')

    def resolve_channel(self, server_id:str) -> str:
        channel = self.channel.lstrip('#')
        if channel.isdigit():
            return channel

        for i in self.get(f'/guilds/{server_id}/channels'):
            if i['name'] == channel and i.get('type') in TEXT_CHANNELS:
                return i['id']
        raise hqle.ArgumentException(f'No text channel named {channel} in discord server {self.server}')

    def embed(self, table:Table, hac:Optional[Hac]) -> dict:
        title = hac.get('title') if hac else ''
        level = hac.get('level') if hac else ''
        description = hac.get('description') if hac else ''
        detection_id = hac.get('id') if hac else ''

        assert isinstance(title, str) and isinstance(level, str)
        assert isinstance(description, str) and isinstance(detection_id, str)

        title = title or f'Hql alert: {table.name}'
        description = description.strip()
        if len(description) > 1000:
            description = description[:999] + '…'

        # room left for the table after the description and the code fence
        room = DESCRIPTION_LIMIT - len(description) - len('\n\n```\n\n```')
        text, shown = table_text(table.to_dicts()[:self.row_limit], room)

        body = f'```\n{text}\n```'
        if description:
            body = f'{description}\n\n{body}'

        fields = [
            {'name': 'Level', 'value': level or 'n/a', 'inline': True},
            {'name': 'Rows', 'value': str(len(table)), 'inline': True},
        ]
        if detection_id:
            fields.append({'name': 'Detection', 'value': detection_id, 'inline': False})

        return {
            'title': title[:256],
            'description': body,
            'color': COLORS.get(level.lower(), DEFAULT_COLOR),
            'fields': fields,
            'footer': {'text': f'{table.name}: showing {shown} of {len(table)} rows'},
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
