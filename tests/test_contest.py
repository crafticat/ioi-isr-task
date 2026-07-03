from datetime import datetime, timezone
from cmsops.contest import is_contest_live

def _dt(s): return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)

def test_live_when_between_start_and_stop():
    assert is_contest_live(_dt("2026-07-01T09:00"), _dt("2026-07-01T14:00"),
                           now=_dt("2026-07-01T10:00")) is True

def test_not_live_before_start():
    assert is_contest_live(_dt("2026-07-01T09:00"), _dt("2026-07-01T14:00"),
                           now=_dt("2026-07-01T08:00")) is False

def test_not_live_after_stop():
    assert is_contest_live(_dt("2026-07-01T09:00"), _dt("2026-07-01T14:00"),
                           now=_dt("2026-07-01T15:00")) is False

def test_none_bounds_are_not_live():
    assert is_contest_live(None, None, now=_dt("2026-07-01T10:00")) is False
