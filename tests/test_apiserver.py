from datetime import datetime, timedelta, timezone

import pytest

from Hql.Apiserver import HqlRequest, local_naive, resolve_window
from Hql.Hac import Hac
from Hql.Hac.Engine import Detection
from Hql.Threading import HacThread


def request(**kwargs) -> HqlRequest:
    return HqlRequest(hql='x', **kwargs)


def test_no_window_keeps_the_schedule_default():
    assert resolve_window(request()) == (None, None)


@pytest.mark.parametrize('text, expected', [
    ('30m', timedelta(minutes=30)),
    ('1h', timedelta(hours=1)),
    ('7d', timedelta(days=7)),
    ('1.5days', timedelta(days=1.5)),
])
def test_lookback_is_parsed_like_ago(text, expected):
    assert resolve_window(request(lookback=text)) == (expected, None)


@pytest.mark.parametrize('text', ['soon', '0h', '-1h', 'h'])
def test_bad_lookback_is_refused(text):
    with pytest.raises(ValueError):
        resolve_window(request(lookback=text))


def test_absolute_range_is_a_lookback_ending_at_end():
    start, end = datetime(2026, 11, 1, 9), datetime(2026, 11, 1, 17)
    assert resolve_window(request(start=start, end=end)) == (timedelta(hours=8), end)


def test_zoned_range_becomes_local_naive_time():
    end = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
    lookback, query_now = resolve_window(request(start=end - timedelta(hours=2), end=end))
    assert lookback == timedelta(hours=2)
    assert query_now is not None and query_now.tzinfo is None
    assert query_now == end.astimezone().replace(tzinfo=None)
    assert local_naive(query_now) is query_now


@pytest.mark.parametrize('kwargs', [
    {'start': datetime(2026, 11, 1, 10), 'end': datetime(2026, 11, 1, 9)},
    {'start': datetime(2026, 11, 1, 10), 'end': datetime(2026, 11, 1, 10)},
    {'start': datetime(2026, 11, 1, 10)},
    {'end': datetime(2026, 11, 1, 10)},
    {'start': datetime(2026, 11, 1, 9), 'end': datetime(2026, 11, 1, 10), 'lookback': '1h'},
])
def test_bad_range_is_refused(kwargs):
    with pytest.raises(ValueError):
        resolve_window(request(**kwargs))


def detection(hac, lookback=None) -> Detection:
    det = Detection.__new__(Detection)
    det.hac = hac
    det.lookback = lookback
    return det


def test_timerange_defaults_to_the_schedule_interval():
    now = datetime(2026, 11, 14, 12)
    assert detection(Hac({}, 'test')).timerange(now) == (now - timedelta(hours=1), now)


def test_timerange_uses_the_lookback():
    now = datetime(2026, 11, 14, 12)
    det = detection(Hac({}, 'test'), lookback=timedelta(days=7))
    assert det.timerange(now) == (now - timedelta(days=7), now)


def test_plain_hql_has_no_timerange():
    assert detection(None).timerange(datetime(2026, 11, 14, 12)) is None


def test_run_dict_reports_the_window_searched():
    now = datetime(2026, 11, 14, 12)
    det = detection(Hac({}, 'test'), lookback=timedelta(minutes=30))
    det.id = 'det'
    d = HacThread(det, query_now=now).to_dict()
    assert d['timerange'] == {'start': '2026-11-14T11:30:00', 'end': '2026-11-14T12:00:00'}

    assert 'timerange' not in HacThread(detection(None), query_now=now).to_dict()
