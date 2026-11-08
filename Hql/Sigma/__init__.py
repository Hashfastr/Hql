'''
Sigma operations: running and converting Sigma rules.

Conversion follows the config's mappings by default: a rule's logsource resolves
against the config's sigma header, and its fields are renamed by the maps there.
A forced language skips all of that and compiles the detection straight to one
backend, with the field names exactly as the rule wrote them.
'''
from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Optional, Union
from pathlib import Path

from Hql.Exceptions import HqlExceptions as hqle

if TYPE_CHECKING:
    from Hql.Compiler import Compiler
    from Hql.Config import Config
    from Hql.Data import Data

RULE_SUFFIXES = ('.yml', '.yaml')

# Placeholder table for languages whose queries must name one
DEFAULT_TABLE = 'events'

def _lucene(table:str) -> Compiler:
    from Hql.Compiler import LuceneCompiler
    return LuceneCompiler()

def _querydsl(table:str) -> Compiler:
    from Hql.Compiler import QueryDSLCompiler
    return QueryDSLCompiler()

def _kql(table:str) -> Compiler:
    from Hql.Compiler import KQLCompiler
    return KQLCompiler()

def _spl(table:str) -> Compiler:
    from Hql.Compiler import SPLCompiler
    return SPLCompiler()

def _kusto(table:str) -> Compiler:
    from Hql.Compiler import KustoCompiler
    compiler = KustoCompiler()
    compiler.add_index(table)
    return compiler

def _postgres(table:str) -> Compiler:
    from Hql.Compiler import PostgresCompiler
    return PostgresCompiler(table)

# Languages a conversion can be forced to, and the file extension for each
FORCED_LANGUAGES:dict[str, tuple[Callable[[str], Compiler], str]] = {
    'lucene': (_lucene, 'lucene'),
    'querydsl': (_querydsl, 'json'),
    'kql': (_kql, 'kql'),
    'spl': (_spl, 'spl'),
    'kusto': (_kusto, 'kusto'),
    'postgres': (_postgres, 'sql'),
}

def collect_rules(path:Path) -> list[Path]:
    '''Every YAML file under a directory, recursively, in a stable order.'''
    return sorted(x for x in path.rglob('*') if x.is_file() and x.suffix in RULE_SUFFIXES)

def check_rule(text:str) -> None:
    '''Raise unless text is a Sigma rule, so it is never quietly run as Hql.'''
    from Hql.Parser.Sigma import is_sigma_text

    if not is_sigma_text(text):
        raise hqle.QueryException('Not a Sigma rule, missing a top level logsource or detection')

def run(text:str, conf:Config, name:str='') -> Data:
    from Hql.Data import Data
    from Hql.Helpers import run_query

    check_rule(text)
    out = run_query(text, conf, name=name)
    if not isinstance(out, Data):
        raise hqle.QueryException(f'Running {name} gave {type(out)}, not Data')
    return out

def convert(text:str, conf:Config, name:str='', plan:bool=False) -> str:
    '''
    Hql for a rule, with its HaC comment, or with plan the rule compiled through
    the config's mappings, as JSON holding each database's native query.
    '''
    from Hql.Helpers import run_query

    check_rule(text)
    if plan:
        out = run_query(text, conf, name=name, plan=True)
    else:
        out = run_query(text, conf, name=name, deparse=True)

    if not isinstance(out, str):
        raise hqle.QueryException(f'Converting {name} gave {type(out)}, not text')
    return out

def force_convert(text:str, language:str, table:str=DEFAULT_TABLE) -> tuple[Union[str, dict], Optional[str]]:
    '''
    The rule's detection compiled straight to one language, with no config, database
    or field mapping. Returns the query and, as Hql, whatever the language can't express.
    '''
    from Hql.Compiler import HqlCompiler
    from Hql.Config import Config
    from Hql.Operators.Where import Where
    from Hql.Parser.Sigma import SigmaParser
    from Hql.Query import Query, QueryStatement
    from Hql.Expressions import PipeExpression

    if language not in FORCED_LANGUAGES:
        raise hqle.CompilerException(f'Unknown language {language}, expected one of {", ".join(FORCED_LANGUAGES)}')

    check_rule(text)

    # An empty config, so no header, posthql or mappings
    conf = Config()
    parser = SigmaParser(text, conf)
    parser.assemble()

    asm = parser.assembly
    if not isinstance(asm, Query) or not asm.statements:
        raise hqle.CompilerException(f'Sigma assembled to {type(asm)}, not a Query')
    stmt = asm.statements[-1]
    if not isinstance(stmt, QueryStatement) or not isinstance(stmt.root, PipeExpression):
        raise hqle.CompilerException('Sigma rule did not assemble to a piped query')
    where = stmt.root.pipes[0]
    if not isinstance(where, Where):
        raise hqle.CompilerException(f'Sigma rule detection assembled to {type(where)}, not a where')

    # Preprocess into what backends take, e.g. not() -> Not
    desc, _ = HqlCompiler(conf).compile(where)

    factory, _ = FORCED_LANGUAGES[language]
    compiler = factory(table)
    _, rejected = compiler.add_op(desc)
    query, _ = compiler.compile(None, prep=False)

    if not isinstance(query, (str, dict)):
        raise hqle.CompilerException(f'{language} compiled to nothing, it cannot express any of this rule')

    return query, rejected.deparse() if rejected else None
