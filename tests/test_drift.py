import io, zipfile
from cmsops.drift import normalize_zip, diff_trees

def _zip(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()

def test_normalize_is_order_independent():
    a = normalize_zip(_zip({"a.txt": "1", "b.txt": "2"}))
    b = normalize_zip(_zip({"b.txt": "2", "a.txt": "1"}))
    assert a == b

def test_diff_detects_changed_file():
    repo = normalize_zip(_zip({"task.yaml": "time_limit: 1"}))
    live = normalize_zip(_zip({"task.yaml": "time_limit: 2"}))
    changed = diff_trees(repo, live)
    assert "task.yaml" in changed

def test_diff_empty_when_equal():
    z = normalize_zip(_zip({"task.yaml": "x"}))
    assert diff_trees(z, z) == []
