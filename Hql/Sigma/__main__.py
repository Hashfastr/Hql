'''
python3 -m Hql.Sigma: run and convert Sigma rules.

  run FILE              run one rule, results as JSON
  run-dir DIR           run every rule under DIR

Runs search the last hour, --lookback widens or narrows that, e.g. -b 7d.
Findings are json unless --format says ndjson or csv.
  convert FILE          convert one rule, to Hql unless told otherwise
  convert-dir DIR       convert every rule under DIR
'''
from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Optional
from pathlib import Path
import argparse
import datetime
import json
import logging
import shutil
import sys
import threading
import time

if TYPE_CHECKING:
    from Hql.Config import Config
    from Hql.Threading import HacThread

FORCE_WARNING = (
    'WARNING: forcing a language compiles the rule with no logsource routing or field '
    'mapping, so field names stay as the rule wrote them and the output can be wrong '
    'for your data. Use mappings in your config (the sigma header) instead.'
)

def lookback(text:str) -> datetime.timedelta:
    '''A --lookback like 1h, 30m, 7d or 1.5days, as ago() takes them.'''
    from Hql.Functions.time import parse_timespan
    from Hql.Exceptions import HqlExceptions as hqle

    try:
        delta = parse_timespan(text)
    except hqle.ArgumentException:
        raise argparse.ArgumentTypeError(f'invalid lookback {text!r}, expected e.g. 1h, 30m or 7d')
    if delta <= datetime.timedelta(0):
        raise argparse.ArgumentTypeError(f'lookback must be positive, got {text!r}')
    return delta

def threads(text:str) -> int:
    try:
        count = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f'invalid thread count {text!r}, expected a whole number')
    if count < 1:
        raise argparse.ArgumentTypeError(f'thread count must be at least 1, got {count}')
    return count

def build_parser() -> argparse.ArgumentParser:
    from Hql.Sigma import FORCED_LANGUAGES, DEFAULT_TABLE, OUTPUT_FORMATS

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('-c', '--config', help='Location of the config file or directory, default ./conf', default='./conf')
    common.add_argument('-v', '--verbose', help='Set verbosity to debug', action='store_true')
    common.add_argument('-l', '--logging-level', help='Verbosity level 1-5, where 5 is debug, 1 is critical, default is 3, warning.', type=int)

    running = argparse.ArgumentParser(add_help=False)
    running.add_argument('-f', '--format', choices=list(OUTPUT_FORMATS), default='json',
        help='How findings are written: json, the data and schema per rule as before; '
             'ndjson, one finding per line; csv, one finding per row. ndjson and csv '
             'lead each finding with _rule and _table, default json')
    running.add_argument('-b', '--lookback', type=lookback, default='1h',
        help='How far back to search, e.g. 30m, 1h, 7d, default 1h')

    convert = argparse.ArgumentParser(add_help=False)
    target = convert.add_mutually_exclusive_group()
    target.add_argument('--plan', help="Compile through the config's mappings and print the plan, with each database's native query", action='store_true')
    target.add_argument('-L', '--force-language', choices=list(FORCED_LANGUAGES), help='Compile straight to this language, ignoring mappings. Can give bad output, prefer mappings')
    convert.add_argument('--table', default=DEFAULT_TABLE, help=f'Table name for forced languages that need one (kusto, postgres), default {DEFAULT_TABLE}')

    parser = argparse.ArgumentParser(prog='python3 -m Hql.Sigma', description='Run and convert Sigma rules')
    sub = parser.add_subparsers(dest='command', required=True, metavar='command')

    p = sub.add_parser('run', parents=[common, running], help='Run a single Sigma rule')
    p.add_argument('file', type=Path, help='Sigma rule file')

    p = sub.add_parser('run-dir', parents=[common, running], help='Run every Sigma rule (*.yml, *.yaml) under a directory')
    p.add_argument('directory', type=Path, help='Directory of Sigma rules, searched recursively')
    p.add_argument('-o', '--output', type=Path, help='Write each rule\'s findings here, mirroring the directory, in the --format, otherwise stdout')
    p.add_argument('-t', '--threads', type=threads,
        help='Rules run at once, default the config\'s hacengine max_threads, or 16')

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

def run_rule(path:Path, conf:Config, lookback:datetime.timedelta, fmt:str='json') -> str:
    from Hql.Sigma import run, format_findings
    data = run(path.read_text(), conf, name=str(path), lookback=lookback)
    return format_findings(data, fmt, rule=str(path))

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
        # ndjson and csv with no findings are empty, not a blank line
        if out:
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

class StatusBar:
    '''
    One self-redrawing line on stderr tracking a directory run. Log records and
    stdout output clear it first and it redraws after, so they never interleave,
    even when they come from worker threads. Does nothing unless stderr is a terminal.
    '''

    def __init__(self, total:int, results:bool):
        self.total = total
        self.results = results
        self.ran = 0
        self.hits = 0
        self.failed = 0
        # Rules in flight, None when the run is serial
        self.running:Optional[int] = None
        self.current = ''
        self.started = time.perf_counter()
        # Time each finished rule took, with its name, for the summary
        self.durations:list[tuple[float, str]] = []
        self.threads = 1
        self.enabled = sys.stderr.isatty()
        self._lock = threading.RLock()
        self._wrapped:list[tuple[logging.Handler, Callable]] = []

    def __enter__(self) -> StatusBar:
        self.started = time.perf_counter()
        if self.enabled:
            for handler in logging.getLogger().handlers:
                self._wrap(handler)
        return self

    def __exit__(self, *_) -> None:
        for handler, emit in self._wrapped:
            handler.emit = emit  # type: ignore[method-assign]
        self._wrapped = []
        self.clear()

    def _wrap(self, handler:logging.Handler) -> None:
        emit = handler.emit
        def wrapped(record:logging.LogRecord) -> None:
            with self._lock:
                self.clear()
                emit(record)
                self.draw()
        handler.emit = wrapped  # type: ignore[method-assign]
        self._wrapped.append((handler, emit))

    @property
    def remaining(self) -> int:
        return self.total - self.ran

    @property
    def elapsed(self) -> float:
        return time.perf_counter() - self.started

    def summary(self) -> str:
        '''How long the run took and how fast it went.'''
        wall = self.elapsed
        line = f'Finished in {duration(wall)}'
        if not self.ran:
            return line

        line += f', {self.ran / wall:.1f} rules/s' if wall else ''
        if not self.durations:
            return line

        busy = sum(x for x, _ in self.durations)
        slowest, name = max(self.durations)
        line += f', average {duration(busy / len(self.durations))} per rule'
        if self.threads > 1 and wall:
            # Rule time over wall time is how much the threads bought
            line += f', {duration(busy)} of rule time over {self.threads} threads ({busy / wall:.1f}x)'
        return line + f', slowest {duration(slowest)} {name}'

    def text(self) -> str:
        parts = [f'{self.ran}/{self.total} ran']
        if self.results:
            parts.append(f'{self.hits} with results')
        parts.append(f'{self.failed} failed')
        if self.running is not None:
            parts.append(f'{self.running} running')
        parts.append(f'{self.remaining} remaining')
        return ' | '.join(parts)

    def clear(self) -> None:
        if not self.enabled:
            return
        with self._lock:
            sys.stderr.write('\r\x1b[2K')
            sys.stderr.flush()

    def draw(self) -> None:
        if not self.enabled:
            return
        line = f'{self.text()} | {duration(self.elapsed)}'
        if self.current:
            line += f' | {self.current}'
        width = shutil.get_terminal_size().columns
        if len(line) >= width:
            line = line[:max(width - 2, 0)] + '…'
        with self._lock:
            sys.stderr.write('\r\x1b[2K' + line)
            sys.stderr.flush()

    def start(self, path:str) -> None:
        self.current = path
        self.draw()

    def finish(self, ok:bool, hit:bool=False, took:Optional[float]=None, name:str='') -> None:
        self.ran += 1
        if took is not None:
            self.durations.append((took, name))
        if not ok:
            self.failed += 1
        elif hit:
            self.hits += 1
        self.current = ''
        self.draw()

    def emit(self, text:str) -> None:
        '''Print to stdout without tearing the bar.'''
        with self._lock:
            self.clear()
            print(text, flush=True)
            self.draw()

def duration(seconds:float) -> str:
    '''Seconds as 0.42s, 12.3s, 4m05s or 1h02m.'''
    if seconds < 10:
        return f'{seconds:.2f}s'
    if seconds < 60:
        return f'{seconds:.1f}s'
    minutes, secs = divmod(int(round(seconds)), 60)
    if minutes < 60:
        return f'{minutes}m{secs:02d}s'
    hours, minutes = divmod(minutes, 60)
    return f'{hours}h{minutes:02d}m'

def sigma_rules(root:Path) -> list[Path]:
    from Hql.Parser.Sigma import is_sigma_text
    from Hql.Sigma import collect_rules

    rules = []
    for path in collect_rules(root):
        try:
            text = path.read_text()
        except Exception as e:
            logging.error(f'Failed reading {path}: {e}')
            continue
        # Rule directories also hold configs and tests, those aren't failures
        if is_sigma_text(text):
            rules.append(path)
        else:
            logging.info(f'Skipping {path}, not a Sigma rule')
    return rules

def directory(root:Path, out_dir:Optional[Path], suffix:str, op:Callable[[Path], str]) -> int:
    '''Apply op to every rule under root, one at a time.'''
    if not root.is_dir():
        logging.error(f'{root} is not a directory')
        return 1

    rules = sigma_rules(root)
    with StatusBar(len(rules), results=False) as bar:
        for path in rules:
            name = str(path.relative_to(root))
            bar.start(name)
            start = time.perf_counter()
            try:
                out = op(path)
            except Exception as e:
                logging.debug('', exc_info=True)
                logging.error(f'Failed {path}: {e}')
                bar.finish(False, took=time.perf_counter() - start, name=name)
                continue

            if out_dir is None:
                bar.emit(f'==> {path} <==\n{out}')
            else:
                write(out, (out_dir / path.relative_to(root)).with_suffix(suffix))
            bar.finish(True, took=time.perf_counter() - start, name=name)

    print(bar.text(), file=sys.stderr)
    print(bar.summary(), file=sys.stderr)
    return 1 if bar.failed else 0

# How often the run loop checks on its threads
POLL_SECONDS = 0.05

def run_directory(root:Path, out_dir:Optional[Path], conf:Config, lookback:Optional[datetime.timedelta]=None, fmt:str='json', threads:Optional[int]=None) -> int:
    '''
    Run every rule under root through the HaC engine's pool, up to the config's
    threads, or the config's hacengine max_threads, at once. Rules that match nothing aren't written.
    '''
    from collections import deque
    from Hql.Hac.Engine import Detection
    from Hql.Sigma import DEFAULT_LOOKBACK, OUTPUT_FORMATS, format_findings
    from Hql.Helpers import can_thread
    from Hql.Threading import HacPool

    if not root.is_dir():
        logging.error(f'{root} is not a directory')
        return 1

    if lookback is None:
        lookback = DEFAULT_LOOKBACK
    rules = sigma_rules(root)
    if threads is None:
        threads = int(conf.get_engine().get('max_threads', 16))
    max_threads = max(threads, 1)
    if max_threads > 1 and not can_thread():
        logging.warning(f'This Python has the GIL, rules run one at a time despite {max_threads} threads')
    pool = HacPool(max_threads=max_threads)
    pending = deque(rules)

    def submit(path:Path) -> bool:
        try:
            detection = Detection(path.read_text(), str(path), conf, lookback=lookback)
        except Exception as e:
            logging.debug('', exc_info=True)
            logging.error(f'Failed {path}: {e}')
            return False
        # Detection already logged why the rule is invalid
        if detection.sigma_error:
            return False
        pool.add_detection(detection)
        return True

    def collect(t:HacThread) -> None:
        path = Path(t.detection.src)
        name = str(path.relative_to(root))
        if t.failed:
            bar.finish(False, took=t.duration, name=name)
            return

        if t.output:
            out = format_findings(t.output, fmt, rule=str(path))
            if out_dir is not None:
                write(out, (out_dir / path.relative_to(root)).with_suffix(OUTPUT_FORMATS[fmt]))
            # Every ndjson line names its rule, so the stream stays one valid file
            elif fmt == 'ndjson':
                bar.emit(out)
            # A rule's json or csv only parses on its own, mark where each starts
            else:
                bar.emit(f'==> {path} <==\n{out}')
        bar.finish(True, bool(t.output), took=t.duration, name=name)

    with StatusBar(len(rules), results=True) as bar:
        bar.running = 0
        # What can actually run at once, a GIL build runs one at a time
        bar.threads = min(max_threads, len(rules)) if can_thread() else 1
        while pending or pool.pool or pool.queue:
            while pending and len(pool.pool) + len(pool.queue) < max_threads:
                if not submit(pending.popleft()):
                    bar.finish(False)

            pool.clear_queue()
            pool.gather_threads()
            # Finished threads are out of the pool now, count before redrawing for them
            bar.running = len(pool.pool)
            for t in pool.get_completed():
                try:
                    collect(t)
                except Exception as e:
                    logging.debug('', exc_info=True)
                    logging.error(f'Failed writing results for {t.detection.src}: {e}')
                    bar.finish(False)

            bar.running = len(pool.pool)
            bar.draw()
            if pool.pool:
                time.sleep(POLL_SECONDS)

    print(bar.text(), file=sys.stderr)
    print(bar.summary(), file=sys.stderr)
    return 1 if bar.failed else 0

def main(argv:Optional[list[str]]=None) -> int:
    args = build_parser().parse_args(argv)
    conf = setup(args)

    if args.command == 'run':
        return single(args.file, None, lambda p: run_rule(p, conf, args.lookback, args.format))

    if args.command == 'run-dir':
        return run_directory(args.directory, args.output, conf, lookback=args.lookback, fmt=args.format, threads=args.threads)

    if args.force_language:
        print(FORCE_WARNING, file=sys.stderr)

    convert = lambda p: convert_rule(p, conf, args)
    if args.command == 'convert':
        return single(args.file, args.output, convert)
    return directory(args.directory, args.output, convert_suffix(args), convert)

if __name__ == '__main__':
    sys.exit(main())
