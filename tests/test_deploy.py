import pytest
from datetime import datetime, timezone
from cmsops.deploy import deploy

class FakeClient:
    def __init__(self, existing_zip=b"PKsnapshot"):
        self.existing_zip = existing_zip
        self.calls = []
    def export_task(self, task_id):
        self.calls.append(("export", task_id)); return self.existing_zip
    def import_task(self, zip_bytes, *, update, contest_id=None, **kw):
        self.calls.append(("import", update, contest_id))

def test_refuses_live_contest(tmp_path):
    (tmp_path / "task.zip").write_bytes(b"PKnew")
    c = FakeClient()
    with pytest.raises(RuntimeError, match="running contest"):
        deploy(c, task_id=5, contest_id=2, zip_path=str(tmp_path/"task.zip"),
               snapshots_dir=str(tmp_path),
               contest_start=datetime(2026,7,1,9,tzinfo=timezone.utc),
               contest_stop=datetime(2026,7,1,14,tzinfo=timezone.utc),
               now=datetime(2026,7,1,10,tzinfo=timezone.utc),
               force_live=False)
    assert ("import", True, 2) not in c.calls    # never imported

def test_snapshots_before_import(tmp_path):
    (tmp_path / "task.zip").write_bytes(b"PKnew")
    c = FakeClient(existing_zip=b"PKold")
    deploy(c, task_id=5, contest_id=2, zip_path=str(tmp_path/"task.zip"),
           snapshots_dir=str(tmp_path),
           contest_start=None, contest_stop=None, now=None, force_live=False)
    # export happened before import
    assert c.calls[0][0] == "export" and c.calls[1][0] == "import"
    # a snapshot file was written
    snaps = list((tmp_path).glob("task_5_*.zip"))
    assert snaps and snaps[0].read_bytes() == b"PKold"
