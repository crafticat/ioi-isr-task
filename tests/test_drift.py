import io, zipfile
from cmsops.drift import normalize_zip, diff_trees, strip_top_dir

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

def test_strip_top_dir_removes_common_prefix():
    assert strip_top_dir({"task/task.yaml": b"x", "task/sub/a": b"y"}) == {"task.yaml": b"x", "sub/a": b"y"}

def test_strip_top_dir_noop_when_multiple_tops():
    t = {"a/x": b"1", "b/y": b"2"}
    assert strip_top_dir(t) == t

def test_strip_top_dir_noop_when_no_subpath():
    t = {"task.yaml": b"x"}
    assert strip_top_dir(t) == t
