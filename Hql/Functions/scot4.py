from __future__ import annotations
from . import Function
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Context import register_func
import requests
import json
import urllib.parse

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from Hql.Data import Data, Table
    from Hql.Hac import Hac
    from Hql.Context import Context

@register_func('scot4')
class scot4(Function):
    """Publish HQL detection results to a SCOT 4 server."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        from Hql.Expressions.Literals import StringLiteral, Bool
        from Hql.Expressions.References import NamedExpression, NamedReference

        Function.__init__(self, args, 0, -1, conf)
        self.params = {
            'server': self.conf.get('default', None),
            # always_union is the older config name, the effective default stays off
            'union': self.conf.get('union', self.conf.get('always_union', False))
        }

        if 'source_tags' not in self.conf:
            self.conf['source_tags'] = dict()

        if 'link_transform' not in self.conf['source_tags']:
            self.conf['source_tags']['link_transform'] = 'domain'

        if 'blacklist' not in self.conf['source_tags']:
            self.conf['source_tags']['blacklist'] = []

        if 'row_limit' not in self.conf:
            self.conf['row_limit'] = 100

        self.verify_tls = self.conf.get('verify_tls', True)
        if not isinstance(self.verify_tls, bool):
            raise hqle.ConfigException(
                'scot4 function config verify_tls must be a boolean'
            )

        for i in self.args:
            if not isinstance(i, NamedExpression):
                raise hqle.ArgumentException(f'Invalid argument expression given to scot4: {i}')
            # The parser gives names as NamedReferences
            if not isinstance(i.paths[0], (StringLiteral, NamedReference)) or len(i.paths) > 1:
                raise hqle.ArgumentException(f'Invalid parameter name(s) given to scot4: {i.paths}')
            val = i.paths[0].str()

            if val not in self.params:
                raise hqle.ArgumentException(f'Invalid parameter given to scot4: {val}')

            # Unwrap literals so they compare against config values
            if isinstance(i.value, StringLiteral):
                self.params[val] = i.value.str()
            elif isinstance(i.value, Bool):
                self.params[val] = i.value.value
            else:
                raise hqle.ArgumentException(f'Invalid value given to scot4 parameter {val}: {i.value.deparse()}')

        for i in self.params:
            if self.params[i] == None:
                raise hqle.ArgumentException(f'Missing required parameter {i} in scot4')

        self.server = dict()
        for i in self.conf['servers']:
            if i['name'] == self.params['server']:
                self.server = i

        if not self.server:
            raise hqle.ArgumentException(f'Attempting to use invalid scot4 server definition {self.params["server"]}')

        self.timeout = 5
        self.owner = 'HaC-Engine'

    def eval(self, ctx: Context, receiver=None) -> object:
        from Hql.Data import Data, Table
        import time
        
        if not ctx.hac or not ctx.data:
            return Data()

        self.update_hac(ctx.hac)
        time.sleep(1)
        res = self.post_alertgroup(ctx.data, ctx.hac)
        return Data([Table(init_data=res)])

    def post(self, api:str, json:dict):
        url = self.server['host'] + api
        headers = {
            'Authorization': f'apikey {self.server["apikey"]}'
        }

        res = requests.post(
            url=url,
            headers=headers,
            json=json,
            timeout=self.timeout,
            verify=self.verify_tls,
        )

        if res.status_code != 200:
            logging.error(f'Post to scot returned a {res.status_code}')
            logging.error(res.text)

        return res

    def get(self, api:str, json:Optional[dict]=None, params:Optional[dict]=None):
        url = self.server['host'] + api
        headers = {
            'Authorization': f'apikey {self.server["apikey"]}'
        }

        if json:
            res = requests.get(
                url=url,
                headers=headers,
                json=json,
                timeout=self.timeout,
                verify=self.verify_tls,
            )
        elif params:
            param_strs = []
            for i in params:
                param_strs.append(f'{i}={urllib.parse.quote_plus(params[i])}')
            url += '?' + '&'.join(param_strs)
            res = requests.get(
                url=url,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_tls,
            )
        else:
            res = requests.get(
                url=url,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_tls,
            )

        if res.status_code != 200:
            logging.error(f'Get from scot returned a {res.status_code}')
            logging.error(res.text)

        return res

    def put(self, api:str, json:dict):
        url = self.server['host'] + api
        headers = {
            'Authorization': f'apikey {self.server["apikey"]}'
        }

        res = requests.put(
            url=url,
            headers=headers,
            json=json,
            timeout=self.timeout,
            verify=self.verify_tls,
        )

        if res.status_code != 200:
            logging.error(f'Put to scot returned a {res.status_code}')
            logging.error(res.text)

        return res

    def post_alertgroup(self, data:Data, hac:Hac):
        from Hql.Expressions.References import Wildcard, NamedReference
        from Hql.Operators.Union import Union as HqlUnion
        from Hql.Context import Context

        union = self.params['union']
        if union:
           data = HqlUnion([Wildcard('*')], NamedReference('scot4_unioned')).eval(Context(data))

        srcs = hac.get('references')
        assert isinstance(srcs, list)
        tags = hac.get('tags')
        assert isinstance(tags, list)

        if not data or len(data) == 0:
            logging.debug('Scot4 given empty alertgroup, skipping')
            return []

        out = []
        for i in data:
            alerts = self.gen_alerts(i)

            body = {
                'subject': hac.get('title'),
                'sources': self.process_sources(srcs),
                'tags': tags,
                'alerts': alerts
            }

            res = self.post('/api/v1/alertgroup/', body)

            # catch all non-200s
            code = res.status_code - 200
            if code < 0 or code > 99:
                res = json.loads(res.text)
                logging.error(res)
                continue

            res = json.loads(res.text)
            new = {
                'id': res['id'],
                'owner': res['owner'],
                'created': res['created']
            }
            out.append(new)

        return out


    def update_hac(self, hac:Hac):
        guide = self.get_guide(hac)
        if guide['resultCount']:
            guide = guide['result'][0]
        else:
            guide = self.make_guide(hac)

        self.update_guide(guide, hac)

        sig = self.get_signature(str(hac.get('title')))
        
        if not sig['result']:
            sig = self.create_signature(hac)
        else:
            sig = sig['result'][0]

        sig_id = sig['id']
        sig = self.update_signature(sig_id, hac)
        self.link_guide(guide, sig)

    def create_signature(self, hac:Hac):
        signature = {
            'name': hac.get('title'),
            'owner': self.owner,
            'status': 'enabled'
        }
        raw_return = self.post('/api/v1/signature/', signature).text
        return json.loads(raw_return)
    
    def update_signature(self, sig_id:int, hac:Hac):
        signature = {
            'name': hac.get('title'),
            'owner': self.owner,
            'status': 'enabled',
            'description': hac.get('description'),
            'data': {
                'signature_body': hac.get('src'),
                'signature_group': [
                    'HaC-Engine'
                ]
            }
        }

        raw_return = self.put(f'/api/v1/signature/{sig_id}', signature).text
        return json.loads(raw_return)

    def get_signature(self, subject:str):
        raw_return = self.get('/api/v1/signature/', params={'name':subject}).text
        return json.loads(raw_return)

    def get_guide(self, hac:Hac):
        title = hac.get('title')
        raw_return = self.get('/api/v1/guide/', params={'subject':title}).text
        return json.loads(raw_return)

    def make_guide(self, hac:Hac):
        guide = {
            'guide': {
                'owner': self.owner,
                'tlp': 'unset',
                'subject': hac.get('title'),
                'status': 'current'
            }
        }

        raw_return = self.post('/api/v1/guide/', guide).text
        return json.loads(raw_return)

    def update_guide(self, guide:dict, hac:Hac):
        entries = self.get_guide_entries(guide)
        if not entries:
            self.make_guide_entry(guide, hac)
        else:
            self.update_guide_entry(entries[0].get('id'), hac)

    def get_guide_entries(self, guide:dict) -> list:
        gid = guide.get('id')
        raw_return = self.get(f'/api/v1/guide/{gid}/entry').text
        return json.loads(raw_return)['result']
    
    def make_guide_entry(self, guide:dict, hac:Hac):
        entry = {
            'entry': {
                'owner': self.owner,
                'target_type': 'guide',
                'target_id': guide['id'],
                'entry_data': {
                    'html': hac.render(target='html')
                }
            }
        }

        raw_return = self.post('/api/v1/entry/', entry).text
        return json.loads(raw_return)

    def update_guide_entry(self, entry:int, hac:Hac):
        entry_data = {
            'entry_data': {
                'html': hac.render(target='html')
            }
        }

        raw_return = self.put(f'/api/v1/entry/{entry}', entry_data).text
        return json.loads(raw_return)
    
    def get_guide_signatures(self, guide:dict) -> list:
        gid = guide['id']
        raw_return = self.get(f"/api/v1/guide/{gid}/signatures").text
        return json.loads(raw_return)

    def link_guide(self, guide:dict, signature:dict):
        # check if we're already linked
        guide_sigs = self.get_guide_signatures(guide)
        for i in guide_sigs:
            if i.get('id') == signature['id']:
                return ''
        
        title = guide.get('title')
        logging.debug(f'Linking new signature to guide {title}')

        link = {
            'v0_type': 'signature',
            'v0_id': signature['id'],
            'v1_type': 'guide',
            'v1_id': guide['id']
        }

        raw_return = self.post('/api/v1/link/', link).text
        return json.loads(raw_return)

    def gen_alerts(self, table:Table):
        limit = self.conf['row_limit']
        alerts = []
        for i in table.to_dicts()[:limit]:
            alerts.append({'data': i})
        return alerts

    def process_sources(self, sources:list[str]) -> list[str]:
        import re
        pat = re.compile(r'(https?://)?(?P<domain>[^/]+)(/.*)?')

        out = []
        for i in sources:
            if self.conf['source_tags']['link_transform'] == 'domain':
                res = pat.search(i)
                if res:
                    i = res.group(2)
            out.append(i)

        return out
