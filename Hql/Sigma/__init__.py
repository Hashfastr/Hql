'''
Sigma operations: running and converting Sigma rules.

Conversion follows the config's mappings by default: a rule's logsource resolves
against the config's sigma header, and its fields are renamed by the maps there.
A forced language skips all of that and compiles the detection straight to one
backend, with the field names exactly as the rule wrote them.
'''
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Callable, Iterator, Optional, Union
from pathlib import Path
from datetime import timedelta

from Hql.Exceptions import HqlExceptions as hqle

if TYPE_CHECKING:
    from Hql.Compiler import Compiler
    from Hql.Config import Config
    from Hql.Data import Data

RULE_SUFFIXES = ('.yml', '.yaml')

# How far back a Sigma rule looks unless told otherwise. Rules carry no schedule,
# so this is the window, not one derived from how often they run.
DEFAULT_LOOKBACK = timedelta(hours=1)

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

# Formats a run's findings can be written in, and the file extension for each
OUTPUT_FORMATS = {
    'json': '.json',
    'ndjson': '.ndjson',
    'csv': '.csv',
}

def finding_rows(data:Data, rule:str='') -> Iterator[dict]:
    '''
    Each row of each table as one finding, led by the rule that found it and the
    table it came from, so rows from many rules can share one stream.
    '''
    for table in data:
        for row in table.to_dicts():
            yield {'_rule': rule, '_table': table.name, **row}

def _csv_cell(value:Any) -> Any:
    import json
    # Nested values have no CSV form, JSON keeps them readable and parseable
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, default=str)
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return value

def format_findings(data:Data, fmt:str='json', rule:str='') -> str:
    '''
    A run's findings as text, without a trailing newline and empty when there are
    none, except json, which always shows the data and schema as Data.to_dict does.
    '''
    import csv
    import io
    import json

    if fmt not in OUTPUT_FORMATS:
        raise hqle.ArgumentException(f'Unknown output format {fmt}, expected one of {", ".join(OUTPUT_FORMATS)}')

    if fmt == 'json':
        return json.dumps(data.to_dict(), indent=2, default=str)

    rows = list(finding_rows(data, rule))
    if fmt == 'ndjson':
        return '\n'.join(json.dumps(x, default=str) for x in rows)

    if not rows:
        return ''
    # Every column any row has, in the order they first appear
    columns = list(dict.fromkeys(k for row in rows for k in row))
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=columns, lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _csv_cell(v) for k, v in row.items()})
    return out.getvalue().removesuffix('\n')

def collect_rules(path:Path) -> list[Path]:
    '''Every YAML file under a directory, recursively, in a stable order.'''
    return sorted(x for x in path.rglob('*') if x.is_file() and x.suffix in RULE_SUFFIXES)

def check_rule(text:str) -> None:
    '''Raise unless text is a Sigma rule, so it is never quietly run as Hql.'''
    from Hql.Parser.Sigma import is_sigma_text

    if not is_sigma_text(text):
        raise hqle.QueryException('Not a Sigma rule, missing a top level logsource or detection')

def run(text:str, conf:Config, name:str='', lookback:timedelta=DEFAULT_LOOKBACK) -> Data:
    '''Run a rule over the last lookback of data.'''
    from Hql.Data import Data
    from Hql.Helpers import run_query

    check_rule(text)
    out = run_query(text, conf, name=name, lookback=lookback)
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
