from __future__ import annotations
from typing import TYPE_CHECKING, Union, Optional

from Hql.Exceptions import HqlExceptions as hqle

if TYPE_CHECKING:
    from Hql.Config import Config
    from Hql.Parser.Sigma.Condition import Condition
    from Hql.Query import Query, QueryStatement

import logging

if TYPE_CHECKING:
    from Hql.Functions import DotCompositeFunction, Function
    from Hql.Hac import Hac
    from Hql.Query import Statement

def is_sigma_text(txt:str) -> bool:
    '''
    Whether text is meant as a Sigma rule: it has the top level keys every rule does.
    Found even when the YAML is invalid, so a broken rule isn't mistaken for Hql.
    '''
    import re
    return all(re.search(rf'^{x}\s*:', txt, re.MULTILINE) for x in ('logsource', 'detection'))

class SigmaParser():
    def __init__(self, txt:str, config:Config):
        import yaml

        self.config = config
        try:
            self.loaded = yaml.load(txt, yaml.SafeLoader)
        except yaml.composer.ComposerError as e:
            raise hqle.QueryException('Multi-document Sigma rules, such as correlations, are not supported') from e
        except yaml.YAMLError as e:
            raise hqle.QueryException(f'Sigma rule is not valid YAML: {e}') from e
        if not isinstance(self.loaded, dict):
            raise hqle.QueryException('Invalid sigma supplied to parser')

        self.assembly:Optional[Query] = None
        self.body:Optional[QueryStatement] = None

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

        self.body = QueryStatement(expr)
        self.assembly = Query(self.gen_header() + [self.body])

    def deparse(self) -> str:
        '''
        The configured sigma header as written, then the deparsed rule body.
        Deparsing the assembled header would expand its imports in place.
        '''
        self.assemble()
        if not self.body:
            raise hqle.CompilerException('Sigma rule assembled without a body')

        body = self.body.deparse()
        header = self.config.get_sigma_header().strip()
        if not header:
            return body

        # The header is its own statement, so it needs a separator before the body
        if not header.endswith(';'):
            header += ';'
        return f'{header}\n{body}'

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
            if i in ('condition', 'posthql', 'timeframe'):
                continue

            selections.append(Selection(dac[i], name=i))

        if 'condition' not in dac:
            raise hqle.QueryException('Sigma detection has no condition')

        # A list of conditions matches if any of them do
        condition = dac['condition']
        if isinstance(condition, list):
            condition = ' or '.join(f'({x})' for x in condition)

        return Condition(str(condition), selections)
