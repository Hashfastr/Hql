from __future__ import annotations
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Context import Context, register_database
from Hql.Database import Database
from Hql.Data import Data
from Hql.Compiler import SPLCompiler

from typing import TYPE_CHECKING, Optional, Union
import datetime
import logging

if TYPE_CHECKING:
    from Hql.Operators.Operator import Operator

# Index in a database to grab data from, extremely simple.
@register_database('Splunk')
class Splunk(Database):
    def __init__(self, config:dict, name:str='Splunk'):
        Database.__init__(self, config)
        self.name = name
        conf = self.config.get('conf', dict())

        # Set to the config default to avoid DoS
        # Can be changed by the take operator for example.
        self.limit:int = conf.get('limit', 100000)

        self.methods = [
            'index',
            'macro'
        ]

        # skips ssl verification for https
        self.verify_certs = conf.get('verify_certs', True)
        self.use_ssl = conf.get('use_ssl', True)

        if 'host' in conf:
            self.host = conf.get('host')
        else:
            raise hqle.ConfigException(f'Missing host config in Splunk config for {self.name}')
        self.port = int(conf.get('port', 8089))

        self.username = conf.get('username', None)
        self.password = conf.get('password', None)
        self.token = conf.get('token', None)

        self.compiler = SPLCompiler()

        self.indexes = []

        # Passed as search job time bounds rather than compiled into SPL
        self.earliest:Optional[datetime.datetime] = None
        self.latest:Optional[datetime.datetime] = None

    def add_index(self, index:str):
        self.indexes.append(index)

    def add_timebound(self, start:datetime.datetime, end:datetime.datetime) -> tuple[Database, Union[None, Operator]]:
        if not self.config.get('timeseries', True):
            # Fake consume it if we don't use it
            logging.debug(f'Skipping timeseries for {self.type}')
            return self, None

        self.earliest = start
        self.latest = end
        return self, None

    def to_dict(self):
        self.query = self.compile()

        return {
            'id': self.id,
            'type': self.type,
            'limit': self.limit,
            'query': self.query
        }

    def compile(self) -> str:
        from Hql.Operators.Take import Take
        from Hql.Operators.Where import Where
        from Hql.Expressions.Logic import Equality, BinaryLogic
        from Hql.Expressions.Literals import Integer, StringLiteral
        from Hql.Expressions.References import NamedReference
        from Hql.Compiler import HqlCompiler
        from Hql.Config import Config
        import copy

        compiler = copy.deepcopy(self.compiler)

        # Add preamble and recompile
        if self.preamble:
            new_ops = list(self.preamble.pipes)

            if compiler.top_level_expr:
                new_ops.append(Where(compiler.top_level_expr))

            new_ops += compiler.ops

            vestigial = HqlCompiler(Config())
            desc = vestigial.optimize(new_ops)

            # Rerun everything through a fresh compiler so preamble ops get prepped
            compiler = SPLCompiler(time_format=compiler.time_format)
            for i in desc:
                _, rej = compiler.add_op(i.get_op())
                if rej:
                    raise hqle.CompilerException(f'Splunk preamble for {self.name} cannot be compiled to SPL: {rej.deparse()}')

        if self.indexes:
            indexes = []
            for i in self.indexes:
                expr = Equality(NamedReference('index'), [StringLiteral(i, verbatim=True)], cs=False)
                indexes.append(expr)
            expr = BinaryLogic(indexes, logic_and=False)
            compiler.add_top_level(Where(expr))

        if self.limit > 0:
            compiler.add_op(Take(Integer(self.limit), []))

        query, _ = compiler.compile(None)
        assert isinstance(query, str)
        return query

    def connect(self):
        import splunklib.client as client

        auth_params = {
            'host': self.host,
            'port': self.port,
            'scheme': 'https' if self.use_ssl else 'http',
            'verify': self.verify_certs
        }

        if self.token:
            auth_params['token'] = self.token
        else:
            if self.username == None:
                raise hqle.ConfigException(f'Unconfigured username in Splunk config {self.name}')
            if self.password == None:
                raise hqle.ConfigException(f'Unconfigured password in Splunk config {self.name}')

            auth_params['username'] = self.username
            auth_params['password'] = self.password

        service = client.connect(**auth_params)
        return service

    def eval(self, ctx:Context, **kwargs) -> Context:
        self.query = self.compile()
        ctx.data = self.make_query()
        return ctx

    def make_query(self, **kwargs) -> Data:
        from splunklib import results
        from Hql.Data import Table

        if self.earliest:
            kwargs.setdefault('earliest_time', self.earliest.isoformat())
        if self.latest:
            kwargs.setdefault('latest_time', self.latest.isoformat())

        logging.debug(f'{self.type} query:\n{self.query}')

        conn = self.connect()
        # blocking so results are complete when read
        job = conn.jobs.create(self.query, exec_mode='blocking', rf='*', **kwargs)
        # count=0 returns all results instead of the default 100
        res = job.results(output_mode='json', count=0)
        reader = results.JSONResultsReader(res)

        data = []
        for i in reader:
            if isinstance(i, results.Message):
                logging.debug(f'Splunk {i.type}: {i.message}')
            elif isinstance(i, dict):
                data.append(i)
        table = Table(init_data=data, name=self.name)

        job.delete()

        return Data(tables=[table])
