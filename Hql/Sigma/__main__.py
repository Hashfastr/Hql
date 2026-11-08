'''
python3 -m Hql.Sigma: run and convert Sigma rules.

  run FILE              run one rule, results as JSON
  run-dir DIR           run every rule under DIR
  convert FILE          convert one rule, to Hql unless told otherwise
  convert-dir DIR       convert every rule under DIR
'''
from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Optional
from pathlib import Path
import argparse
import json
import logging
import sys

if TYPE_CHECKING:
    from Hql.Config import Config

FORCE_WARNING = (
    'WARNING: forcing a language compiles the rule with no logsource routing or field '
    'mapping, so field names stay as the rule wrote them and the output can be wrong '
    'for your data. Use mappings in your config (the sigma header) instead.'
)

def build_parser() -> argparse.ArgumentParser:
    from Hql.Sigma import FORCED_LANGUAGES, DEFAULT_TABLE

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('-c', '--config', help='Location of the config file or directory, default ./conf', default='./conf')
    common.add_argument('-v', '--verbose', help='Set verbosity to debug', action='store_true')
    common.add_argument('-l', '--logging-level', help='Verbosity level 1-5, where 5 is debug, 1 is critical, default is 3, warning.', type=int)

    convert = argparse.ArgumentParser(add_help=False)
    target = convert.add_mutually_exclusive_group()
    target.add_argument('--plan', help="Compile through the config's mappings and print the plan, with each database's native query", action='store_true')
    target.add_argument('-L', '--force-language', choices=list(FORCED_LANGUAGES), help='Compile straight to this language, ignoring mappings. Can give bad output, prefer mappings')
    convert.add_argument('--table', default=DEFAULT_TABLE, help=f'Table name for forced languages that need one (kusto, postgres), default {DEFAULT_TABLE}')

    parser = argparse.ArgumentParser(prog='python3 -m Hql.Sigma', description='Run and convert Sigma rules')
    sub = parser.add_subparsers(dest='command', required=True, metavar='command')

    p = sub.add_parser('run', parents=[common], help='Run a single Sigma rule')
    p.add_argument('file', type=Path, help='Sigma rule file')

    p = sub.add_parser('run-dir', parents=[common], help='Run every Sigma rule (*.yml, *.yaml) under a directory')
    p.add_argument('directory', type=Path, help='Directory of Sigma rules, searched recursively')
    p.add_argument('-o', '--output', type=Path, help='Write each rule\'s results as JSON here, mirroring the directory, otherwise stdout')

    p = sub.add_parser('convert', parents=[common, convert], help='Convert a single Sigma rule, to Hql by default')
    p.add_argument('file', type=Path, help='Sigma rule file')
    p.add_argument('-o', '--output', type=Path, help='Output file, otherwise stdout')

    p = sub.add_parser('convert-dir', parents=[common, convert], help='Convert every Sigma rule (*.yml, *.yaml) under a directory')
    p.add_argument('directory', type=Path, help='Directory of Sigma rules, searched recursively')
    p.add_argument('-o', '--output', type=Path, help='Output directory mirroring the input\'s structure, otherwise stdout')

    return parser

def setup(args:argparse.Namespace) -> Config:
    from Hql.Config import Config
    from Hql.Helpers import config_logging

    if args.logging_level:
        config_logging(args.logging_level)
    elif args.verbose:
        config_logging(5)
    else:
        config_logging(3)

    return Config(Path(args.config))

def run_rule(path:Path, conf:Config) -> str:
    from Hql.Sigma import run
    return json.dumps(run(path.read_text(), conf, name=str(path)).to_dict(), indent=2)

def convert_rule(path:Path, conf:Config, args:argparse.Namespace) -> str:
    from Hql.Sigma import convert, force_convert

    text = path.read_text()
    if not args.force_language:
        return convert(text, conf, name=str(path), plan=args.plan)

    query, rejected = force_convert(text, args.force_language, table=args.table)
    if rejected:
        logging.warning(f'{path}: {args.force_language} cannot express part of this rule, it is left out: {rejected}')
    return json.dumps(query, indent=2) if isinstance(query, dict) else query

def convert_suffix(args:argparse.Namespace) -> str:
    from Hql.Sigma import FORCED_LANGUAGES

    if args.force_language:
        return '.' + FORCED_LANGUAGES[args.force_language][1]
    return '.json' if args.plan else '.hql'

def write(out:str, dest:Optional[Path]) -> None:
    if dest is None:
        print(out)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(out if out.endswith('\n') else out + '\n')

def single(path:Path, dest:Optional[Path], op:Callable[[Path], str]) -> int:
    try:
        write(op(path), dest)
    except Exception as e:
        logging.debug('', exc_info=True)
        logging.error(f'Failed {path}: {e}')
        return 1
    return 0

def directory(root:Path, out_dir:Optional[Path], suffix:str, op:Callable[[Path], str]) -> int:
    from Hql.Parser.Sigma import is_sigma_text
    from Hql.Sigma import collect_rules

    if not root.is_dir():
        logging.error(f'{root} is not a directory')
        return 1

    failed:list[Path] = []
    done = 0
    for path in collect_rules(root):
        try:
            # Rule directories also hold configs and tests, those aren't failures
            if not is_sigma_text(path.read_text()):
                logging.info(f'Skipping {path}, not a Sigma rule')
                continue

            out = op(path)
            if out_dir is None:
                print(f'==> {path} <==')
                print(out)
            else:
                write(out, (out_dir / path.relative_to(root)).with_suffix(suffix))
            done += 1
        except Exception as e:
            logging.debug('', exc_info=True)
            logging.error(f'Failed {path}: {e}')
            failed.append(path)

    print(f'{done} succeeded, {len(failed)} failed', file=sys.stderr)
    return 1 if failed else 0

def main(argv:Optional[list[str]]=None) -> int:
    args = build_parser().parse_args(argv)
    conf = setup(args)

    if args.command == 'run':
        return single(args.file, None, lambda p: run_rule(p, conf))

    if args.command == 'run-dir':
        return directory(args.directory, args.output, '.json', lambda p: run_rule(p, conf))

    if args.force_language:
        print(FORCE_WARNING, file=sys.stderr)

    convert = lambda p: convert_rule(p, conf, args)
    if args.command == 'convert':
        return single(args.file, args.output, convert)
    return directory(args.directory, args.output, convert_suffix(args), convert)

if __name__ == '__main__':
    sys.exit(main())
