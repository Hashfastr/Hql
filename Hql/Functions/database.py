from __future__ import annotations
from . import Function
from Hql.Context import register_func
from Hql.Exceptions import HqlExceptions as hqle
from typing import TYPE_CHECKING, Optional, Union

import logging

if TYPE_CHECKING:
    from Hql.Expressions import PipeExpression
    from Hql.Context import Context

# This is a meta function resolved while parsing
@register_func('database')
class database(Function):
    """Resolve a configured database by name."""

    def __init__(self, args:list, conf:Optional[dict]=None):
        from Hql.Expressions.Literals import StringLiteral
        from Hql.Expressions.References import Reference
        Function.__init__(self, args, 1, 1)

        dbname = args[0]
        if not isinstance(dbname, (StringLiteral, Reference)):
            raise hqle.ArgumentException(f'Bad database argument datatype {dbname.type}')

        self.dbname:Union[StringLiteral, Reference] = dbname
        self.can_preprocess = True

    def parse_preamble(self, preamble:dict, src:str) -> PipeExpression:
        from Hql.Parser import Parser
        from Hql.Expressions import PipeExpression

        if 'hql' not in preamble:
            raise hqle.ConfigException(f'Missing hql definition in config {src}')

        parser = Parser(preamble['hql'], src)
        parser.assemble(targets=['emptyPipedExpression'])
        if not isinstance(parser.assembly, PipeExpression):
            raise hqle.ConfigException(f'Invalid preamble expression in {src}')

        return parser.assembly

    def eval(self, ctx: Context, receiver=None) -> object:
        return self.preprocess(ctx, receiver=receiver)

    def preprocess(self, ctx: Context, receiver=None) -> object:
        from Hql.Database import Database
        from Hql.Expressions.Literals import StringLiteral

        dbname = self.dbname.preprocess(ctx)
        if not isinstance(dbname, StringLiteral):
            raise hqle.QueryException(f'Given database name is not StringLiteral, {type(dbname)}')

        dbconf = ctx.config.get_database(dbname.str())
        
        if 'type' not in dbconf:
            logging.critical('Missing database type in database config')
            logging.critical(f"Available DB types: {', '.join(ctx.get_db_types())}")
            raise hqle.ConfigException(f'Missing TYPE definition in database config for {dbname.str()}')

        db = ctx.get_db(dbconf['type'])(dbconf, name=dbname.str())
        assert isinstance(db, Database)

        preamble = db.config.get('preamble', dict())
        if preamble:
            preamble = self.parse_preamble(preamble, f'{db.name}/preamble')
            db.preamble = preamble

        return db
