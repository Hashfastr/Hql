from __future__ import annotations
from typing import TYPE_CHECKING, Union, Optional

from Hql.Exceptions import HqlExceptions as hqle

if TYPE_CHECKING:
    from Hql.Config import Config
    from Hql.Parser.Sigma.Condition import Condition

import logging

if TYPE_CHECKING:
    from Hql.Functions import DotCompositeFunction, Function
    from Hql.Hac import Hac
    from Hql.Query import Statement

class SigmaParser():
    def __init__(self, txt:str, config:Config):
        from Hql.Query import Query
        import yaml

        self.config = config
        self.loaded = yaml.load(txt, yaml.SafeLoader)
        if isinstance(self.loaded, str):
            raise hqle.QueryException('Invalid sigma supplied to parser')

        self.assembly:Optional[Query] = None

        if self.loaded.get('status', '') == 'deprecated':
            raise hqle.QueryException(f'Sigma rule is deprecated')

    def gen_hac(self) -> Hac:
        from copy import deepcopy
        from Hql.Hac import Hac
        doc:dict = deepcopy(self.loaded)

        try:
            for i in ['detection', 'logsource']:
                doc.pop(i)
        except KeyError as e:
            logging.critical(f"Missing critical field")
            logging.critical(e)
            raise hqle.QueryException(f'Invalid sigma supplied to parser')

        return Hac(doc, 'sigma')

    def assemble(self):
        from Hql.Expressions import PipeExpression
        from Hql.Query import Query, QueryStatement
        from Hql.Parser import Parser as HqlParser
        from Hql.Operators.Where import Where

        # hac = self.gen_hac()
        dac = self.loaded['detection']
        src = self.loaded['logsource']

        prepipe = self.gen_src(src)
        condition:Condition = self.parse_dac(dac)
        expr = PipeExpression([Where(condition.assemble())], prepipe=prepipe)

        posthql_src = ''
        if 'posthql' not in self.loaded['detection'] and 'default' in self.config.conf['sigma']['posthql']:
            posthql_src = self.config.get_posthql('default')['hql']
        elif 'posthql' in self.loaded['detection']:
            posthql_src = self.config.get_posthql(self.loaded['detection']['posthql'])['hql']

        if posthql_src:
            parser = HqlParser(posthql_src, 'SigmaConfig')
            parser.assemble(target='emptyPipedExpression')
            asm = parser.assembly

            if not isinstance(asm, PipeExpression) or asm.prepipe:
                logging.error(asm)
                raise hqle.ConfigException(f'Posthql definition does not compile to an empty piped operator')
            expr.pipes += asm.pipes

        stmts = self.gen_header()
        # for i in condition.selections:
        #     stmts.append(i.gen_let())

        stmts += [QueryStatement(expr)]
        self.assembly = Query(stmts)

    '''
    Statements from the configured sigma header, prepended to every rule
    Used to bring the classes the logsource resolves against into scope

    sigma:
      header: |
        import newmaps.windows
    '''
    def gen_header(self) -> list[Statement]:
        from Hql.Parser import Parser as HqlParser
        from Hql.Query import Query, QueryStatement

        header = self.config.get_sigma_header()
        if not header:
            return []

        parser = HqlParser(header, 'SigmaHeader', paths=self.config.get_import_paths())
        parser.assemble(target='top')
        asm = parser.assembly

        if not isinstance(asm, Query):
            raise hqle.ConfigException(f'Sigma header does not compile to a query, got {type(asm)}')

        for i in asm.statements:
            if isinstance(i, QueryStatement):
                raise hqle.ConfigException('Sigma header has a query statement, it can only hold declarations')

        return asm.statements

    def gen_src(self, src:dict) -> Union[DotCompositeFunction, Function]:
        from Hql.Expressions.Functions import FuncExpr
        from Hql.Expressions.Literals import StringLiteral
        from Hql.Expressions.References import NamedReference
        from Hql.Functions import DotCompositeFunction

        '''
        Category can contain a set of product/service combos
        Products contain a set of services, can be used to narrow down categories
        Services filter down logs from a product
        '''
        order = ['product', 'service', 'category']
        funcs = []

        for i in order:
            if i in src:
                funcs.append(FuncExpr(NamedReference(i), [StringLiteral(src[i])]))

        if len(funcs) == 0:
            raise hqle.QueryException(f'Sigma provided no log sources!')

        return DotCompositeFunction(funcs)

    def parse_dac(self, dac:dict) -> Condition:
        from Hql.Parser.Sigma.Condition import Condition
        from Hql.Parser.Sigma.Selection import Selection

        selections = []
        for i in dac:
            if i in ('condition', 'posthql'):
                continue

            selections.append(Selection(dac[i], name=i))

        return Condition(dac['condition'], selections)
