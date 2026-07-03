from __future__ import annotations
from datetime import datetime, timezone

def is_contest_live(start: datetime | None, stop: datetime | None,
                    now: datetime | None = None) -> bool:
    if start is None or stop is None:
        return False
    now = now or datetime.now(timezone.utc)
    return start <= now <= stop
