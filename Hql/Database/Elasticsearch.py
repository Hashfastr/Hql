from __future__ import annotations
from Hql.Exceptions import HqlExceptions as hqle
from Hql.Context import Context, register_database
from Hql.Database import Database
from Hql.Data import Schema, Data, Table
from Hql.Types.Elasticsearch import ESTypes
from Hql.Compiler import LuceneCompiler, QueryDSLCompiler

from typing import TYPE_CHECKING, Union
import json
import logging

from elasticsearch import Elasticsearch as ES
from elasticsearch import AuthenticationException as ESAuthExcept

if TYPE_CHECKING:
    from Hql.Operators.Operator import Operator
    from Hql.Compiler import BranchDescriptor
    from Hql.Expressions.References import NamedReference

# Index in a database to grab data from, extremely simple.
@register_database('Elasticsearch')
class Elasticsearch(Database):
    def __init__(self, config:dict, name:str='Elasticsearch'):
        Database.__init__(self, config)
        self.name = name
       
        # Default index pattern
        self.pattern = "*"

        conf = self.config.get('conf', dict())

        # Set to the config default to avoid DoS
        # Can be changed by the take operator for example.
        self.limit:int = conf.get('limit', 100000)
        
        # Default scroll max, cannot be higher than 10k
        # Higher values are generally better, each request has some time to it
        # 10000 is faster than 10x1000
        self.scroll_max = conf.get('scroll_max', 10000)
        self.scroll_time = conf.get('scroll_time', '1m')
        self.timeout = conf.get('timeout', 10)

        self.methods = [
            'index',
            'macro'
        ]
        
        # skips ssl verification for https
        self.verify_certs = conf.get('verify_certs', True)
        self.use_ssl = conf.get('use_ssl', True)

        if 'hosts' in conf:
            self.hosts = conf.get('hosts')
        elif 'host' in conf:
            self.hosts = [conf.get('host')]
        else:
            raise hqle.ConfigException(f'Missing hosts config in Elasticsearch config for {self.name}')

        self.username = conf.get('username', 'elastic')
        self.password = conf.get('password', 'changeme')

        if conf.get('compiler', 'lucene') == 'lucene':
            self.compiler = LuceneCompiler()
            self.compiler_type = 'Lucene'
        elif conf['compiler'] == 'dsl':
            self.compiler = QueryDSLCompiler()
            self.compiler_type = 'DSL'
        else:
            raise hqle.ConfigException(f'Invalid compiler type {conf["compiler"]} for Elasticsearch')

        self.client = ES(
            self.hosts,
            basic_auth=(self.username, self.password),
            verify_certs=self.verify_certs,
            request_timeout=self.timeout,
            retry_on_timeout=True,
            max_retries=3
        )

    def __str__(self) -> str:
        return f'{self.type} - {self.name}'

    def to_dict(self):
        self.query, _ = self.compile()
        
        return {
            'id': self.id,
            'type': self.type,
            'index': self.pattern,
            'limit': self.limit,
            'query': self.query,
            'ops': [x.to_dict() for x in self.preamble.pipes]
        }

    def compile(self) -> tuple[dict, None]:
        import copy

        compiler = copy.deepcopy(self.compiler)

        query, _ = compiler.compile(None, prep=False)
        if not isinstance(query, (dict, str)):
            e = f'Expected (dict, str) got {type(query)}'
            logging.error(e)
            raise hqle.CompilerException(e)

        if isinstance(query, str):
            query = {
                "query": {
                    "query_string": {
                        "query": query
                    }
                }
            }
        else:
            query = {
                "query": query
            }

        return query, None

    def simple_compile(self) -> dict:
        query = self.compiler.simple_compile()
        return {
            'index': self.pattern,
            'query': query,
            'limit': self.limit
        }
            
    def get_variable(self, name:NamedReference):
        self.pattern = name.name
        return self

    def add_index(self, index:str):
        self.pattern = index

    def add_op(self, op: Union[Operator, BranchDescriptor]) -> tuple[Union[Operator, None], Union[Operator, None]]:
        from Hql.Compiler import BranchDescriptor
        from Hql.Operators.Take import Take, Operator

        if isinstance(op, BranchDescriptor):
            op = op.get_op()

        if isinstance(op, Take):
            if op.tables:
                return None, op

            limit = op.expr.eval(self.ctx)
            assert isinstance(limit, int)
            self.limit = limit if limit < self.limit else self.limit

            return op, None

        acc, rej = self.compiler.add_op(op)
        assert isinstance(acc, (Operator, type(None)))
        assert isinstance(rej, (Operator, type(None)))
        return acc, rej

    def gen_elastic_schema(self, props:dict) -> dict:
        schema = {}
        for i in props:
            if 'properties' in props[i]:
                schema[i] = self.gen_elastic_schema(props[i]['properties'])
                continue
            schema[i] = ESTypes.from_name(props[i]['type'])()
        return schema

    def eval(self, ctx: Context) -> Context:
        try:
            self.query, ops = self.compile()
            data = self.make_query()
            # Run extra ops from prepend
            for op in ops:
                ctx.data = data
                data = op.eval(ctx)
            return data
        except ESAuthExcept:
            user = self.config.get('ELASTIC_USER', 'elastic')
            raise hqle.ConfigException(f'Elasticsearch authentication with user {user} failed') from None

    def make_query(self) -> Data:
        from elasticsearch.helpers import scan
        logging.debug("Starting initial query")

        logging.debug(f"{self.type} query, using the following {self.compiler_type}:")
        logging.debug(json.dumps(self.query))
        logging.debug(f'Index pattern: {self.pattern}')
        logging.debug(f'Limit: {self.limit}')
        
        res = scan(
            self.client,
            index=self.pattern,
            size=self.scroll_max,
            query=self.query
        )
        
        logging.debug("Start scrolling")
        
        remainder = self.limit
        got = 0
        results = dict()
        for i in res:
            if remainder <= 0:
                break

            index = i['_index']
            if not i.get('_source', {}):
                continue

            if index not in results:
                results[index] = []
            results[index].append(i['_source'])

            remainder -= 1
            got += 1

        logging.debug(f'Got {got} results')

        tables = []
        for i in results:
            table = Table(init_data=results[i], name=i)
            
            # mapping = self.client.indices.get_mapping(index=i)
            # schema = self.gen_elastic_schema(mapping[i]['mappings']['properties'])
            # schema = Schema(schema=schema).convert_schema(target='hql')
            # schema = Schema.merge([table.schema, schema])

            # table.set_schema(schema)
            tables.append(table)

        return Data(tables=tables)
