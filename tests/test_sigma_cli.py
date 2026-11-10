from pathlib import Path
import io
import json
import logging
import threading
from datetime import datetime, timedelta

import pytest

from Hql.Config import Config
from Hql.Helpers import can_thread
from Hql.Sigma import __main__ as cli

RULE = (
    'title: t\nid: 5d8a3c1e-0000-4000-8000-000000000000\nstatus: test\n'
    'author: me\ndescription: d\nlogsource:\n  product: x\ndetection:\n  sel:\n    a: 1\n  condition: sel\n'
)


def make_rules(root:Path, names:list[str]) -> None:
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(RULE)
    # Not a rule, never counted
    (root / 'config.yml').write_text('foo: bar\n')


@pytest.fixture
def fake_detections(monkeypatch):
    '''Detections that fail, match nothing or match a row, going by their file name.'''
    import polars as pl
    from Hql.Context import Context
    from Hql.Data import Data, Table
    from Hql.Hac.Engine import Detection

    threads = set()

    def run(self, query_time=None, ctx=None):
        threads.add(threading.get_ident())
        name = Path(self.src).name
        if 'fail' in name:
            raise RuntimeError('boom')
        if 'empty' in name:
            return Context(Data())
        return Context(Data([Table(df=pl.DataFrame({'a': [1]}), name='t')]))

    monkeypatch.setattr(Detection, 'run', run)
    return threads


def test_empty_results_are_not_written(tmp_path, capsys, fake_detections):
    rules, out = tmp_path / 'rules', tmp_path / 'out'
    make_rules(rules, ['hit.yml', 'sub/empty.yml', 'fail.yml'])

    rc = cli.run_directory(rules, out, Config())

    assert rc == 1
    assert sorted(p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()) == ['hit.json']
    assert json.loads((out / 'hit.json').read_text())['data'] == {'t': [{'a': 1}]}
    assert '3/3 ran | 1 with results | 1 failed | 0 running | 0 remaining' in capsys.readouterr().err


def test_empty_results_are_not_printed(tmp_path, capsys, fake_detections):
    make_rules(tmp_path, ['hit.yml', 'empty.yml'])

    assert cli.run_directory(tmp_path, None, Config()) == 0

    stdout = capsys.readouterr().out
    assert 'hit.yml' in stdout
    assert 'empty.yml' not in stdout


def test_run_directory_is_bounded_by_max_threads(tmp_path, monkeypatch, fake_detections):
    from Hql.Threading import HacPool

    seen = []
    add = HacPool.add_detection
    def tracked(self, *args, **kwargs):
        tid = add(self, *args, **kwargs)
        seen.append(len(self.pool) + len(self.queue))
        return tid
    monkeypatch.setattr(HacPool, 'add_detection', tracked)

    make_rules(tmp_path, [f'hit{i}.yml' for i in range(7)])
    conf = Config()
    conf.conf['general']['hacengine'] = {'max_threads': 3}

    assert cli.run_directory(tmp_path, tmp_path / 'out', conf) == 0
    assert len(list((tmp_path / 'out').glob('*.json'))) == 7
    assert len(seen) == 7 and max(seen) <= 3
    if can_thread():
        # Ran off the main thread
        assert threading.get_ident() not in fake_detections


def test_invalid_sigma_rule_counts_as_failed(tmp_path, capsys):
    (tmp_path / 'bad.yml').write_text('logsource: [\ndetection: :\n')

    assert cli.run_directory(tmp_path, None, Config()) == 1
    assert '1/1 ran | 0 with results | 1 failed' in capsys.readouterr().err


def test_convert_directory_stays_serial(tmp_path, capsys):
    make_rules(tmp_path, ['a.yml'])
    assert cli.directory(tmp_path, None, '.hql', lambda p: 'converted') == 0
    assert 'converted' in capsys.readouterr().out


def test_status_bar_counts():
    bar = cli.StatusBar(4, results=True)
    bar.finish(True, True)
    bar.finish(True, False)
    bar.finish(False)

    assert (bar.ran, bar.hits, bar.failed, bar.remaining) == (3, 1, 1, 1)
    assert bar.text() == '3/4 ran | 1 with results | 1 failed | 1 remaining'
    assert 'with results' not in cli.StatusBar(1, results=False).text()


def test_status_bar_clears_around_log_records(monkeypatch):
    stderr = io.StringIO()
    monkeypatch.setattr(cli.sys, 'stderr', stderr)
    handler = logging.StreamHandler(stderr)
    root = logging.getLogger()
    root.addHandler(handler)
    original = handler.emit
    try:
        bar = cli.StatusBar(2, results=True)
        bar.enabled = True
        with bar:
            bar.start('a.yml')
            logging.error('oops')
        # Restored once the run is over
        assert handler.emit == original
    finally:
        root.removeHandler(handler)

    text = stderr.getvalue()
    # The bar is cleared before the record and redrawn after it
    assert '\r\x1b[2Koops\n\r\x1b[2K0/2 ran' in text


@pytest.mark.parametrize('seconds,text', [
    (0.4213, '0.42s'), (12.34, '12.3s'), (245, '4m05s'), (3725, '1h02m'),
])
def test_duration(seconds, text):
    assert cli.duration(seconds) == text


def test_summary_reports_speed_and_slowest(monkeypatch):
    clock = iter([100.0, 110.0])
    monkeypatch.setattr(cli.time, 'perf_counter', lambda: next(clock))
    bar = cli.StatusBar(3, results=True)
    bar.threads = 4
    bar.finish(True, True, took=8.0, name='a.yml')
    bar.finish(True, took=20.0, name='slow.yml')
    bar.finish(False, took=2.0, name='b.yml')

    assert bar.summary() == (
        'Finished in 10.0s, 0.3 rules/s, average 10.0s per rule, '
        '30.0s of rule time over 4 threads (3.0x), slowest 20.0s slow.yml'
    )


def test_run_directory_prints_summary(tmp_path, capsys, fake_detections):
    make_rules(tmp_path, ['hit.yml', 'empty.yml'])
    cli.run_directory(tmp_path, None, Config())
    err = capsys.readouterr().err
    assert 'Finished in ' in err and 'rules/s' in err and 'slowest' in err


@pytest.mark.parametrize('argv,expected', [
    ([], timedelta(hours=1)),
    (['-b', '7d'], timedelta(days=7)),
    (['--lookback', '30m'], timedelta(minutes=30)),
])
def test_lookback_option(argv, expected):
    for command in (['run', 'r.yml'], ['run-dir', 'rules']):
        args = cli.build_parser().parse_args(command + argv)
        assert args.lookback == expected


@pytest.mark.parametrize('bad', ['soon', '0h', '-1h'])
def test_lookback_rejects_bad_values(bad, capsys):
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(['run', 'r.yml', '--lookback', bad])


def test_run_directory_passes_lookback(tmp_path, fake_detections, monkeypatch):
    from Hql.Hac.Engine import Detection

    seen = []
    init = Detection.__init__
    def tracked(self, *args, **kwargs):
        init(self, *args, **kwargs)
        seen.append(self.lookback)
    monkeypatch.setattr(Detection, '__init__', tracked)

    make_rules(tmp_path, ['a.yml', 'b.yml'])
    cli.run_directory(tmp_path, tmp_path / 'out', Config(), lookback=timedelta(days=3))
    cli.run_directory(tmp_path, tmp_path / 'out', Config())
    assert seen == [timedelta(days=3)] * 2 + [timedelta(hours=1)] * 2


def test_detection_lookback_sets_the_window(monkeypatch):
    import Hql.Compiler
    from Hql.Hac.Engine import Detection

    # The window is set on the HaC the compiler gets, before any source resolves
    class Compiler:
        def __init__(self, config, query=None, hac=None):
            self.hac = hac
    monkeypatch.setattr(Hql.Compiler, 'HqlCompiler', Compiler)

    detection = Detection(RULE, 'r.yml', Config(), lookback=timedelta(days=2))
    now = datetime(2026, 1, 10, 12)
    start, end = detection.compile(now).hac.get_timerange()
    assert (start, end) == (now - timedelta(days=2), now)
    # The detection's own HaC is untouched, each run gets a copy
    assert detection.hac.lookback is None


def test_hac_lookback_overrides_schedule():
    from Hql.Hac import Hac
    from Hql.Exceptions import HacExceptions as hace

    hac = Hac({}, src='test')
    hac.set_query_now(datetime(2026, 1, 1, 12))
    assert hac.get_timerange() == (datetime(2026, 1, 1, 11), datetime(2026, 1, 1, 12))

    hac.set_lookback(timedelta(days=1))
    assert hac.get_timerange() == (datetime(2025, 12, 31, 12), datetime(2026, 1, 1, 12))

    hac.set_lookback(None)
    assert hac.get_timerange()[0] == datetime(2026, 1, 1, 11)

    with pytest.raises(hace.HacException):
        hac.set_lookback(timedelta(0))
