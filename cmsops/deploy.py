from __future__ import annotations
import os, sys
from datetime import datetime, timezone
from cmsops.contest import is_contest_live

def deploy(client, *, task_id: int, contest_id: int | None, zip_path: str,
           snapshots_dir: str, contest_start=None, contest_stop=None,
           now=None, force_live: bool = False) -> str:
    if is_contest_live(contest_start, contest_stop, now) and not force_live:
        raise RuntimeError(
            "refusing to deploy to a running contest; set force_live to override")
    # 1. Snapshot the current server package (rollback source) BEFORE importing.
    os.makedirs(snapshots_dir, exist_ok=True)
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    snap_path = os.path.join(snapshots_dir, f"task_{task_id}_{stamp}.zip")
    try:
        with open(snap_path, "wb") as fh:
            fh.write(client.export_task(task_id))
    except Exception as exc:   # task may be new (no server copy yet)
        snap_path = ""
        print(f"note: no pre-deploy snapshot ({exc})")
    # 2. Import (replace by name).
    with open(zip_path, "rb") as fh:
        client.import_task(fh.read(), update=True, contest_id=contest_id)
    print(f"deployed task {task_id}; snapshot={snap_path or 'none'}")
    return snap_path

def main() -> int:
    from cmsops.client import CmsAdminClient
    from cmsops.config import Settings
    task_id = int(os.environ["DEPLOY_TASK_ID"])
    contest_id = int(os.environ["DEPLOY_CONTEST_ID"]) if os.environ.get("DEPLOY_CONTEST_ID") else None
    zip_path = os.environ["DEPLOY_ZIP"]
    force_live = os.environ.get("DEPLOY_FORCE_LIVE", "") == "true"
    client = CmsAdminClient(Settings.from_env())
    start, stop = _fetch_contest_window(client, contest_id)
    deploy(client, task_id=task_id, contest_id=contest_id, zip_path=zip_path,
           snapshots_dir="snapshots", contest_start=start, contest_stop=stop,
           force_live=force_live)
    return 0

def _fetch_contest_window(client, contest_id):
    """Fetch (start, stop) for the contest to enforce the freeze guard.

    Reads the admin contest page; parse start/stop. If unavailable, treat as
    unknown → guard cannot confirm live → require force_live for safety."""
    if contest_id is None:
        return (None, None)
    # Implementation: GET /contest/{id} and parse the datetimes, or add a tiny
    # JSON field to the contest page. Until wired, return a sentinel that forces
    # the operator to pass force_live for contest-attached deploys.
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    return (now - timedelta(days=3650), now + timedelta(days=3650))  # conservative: always "live"

if __name__ == "__main__":
    sys.exit(main())
