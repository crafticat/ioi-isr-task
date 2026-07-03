from cmsops.analytics import parse_ranking_history

def test_parse_history_to_rows():
    raw = [["12", "3", 1719830000, 100.0], ["12", "4", 1719830500, 40.0]]
    rows = parse_ranking_history(raw)
    assert rows[0] == {"user_id": 12, "task_id": 3, "time": 1719830000, "score": 100.0}
    assert rows[1]["task_id"] == 4 and rows[1]["score"] == 40.0

def test_solved_full_filter():
    from cmsops.analytics import users_with_full_score
    rows = [{"user_id": 12, "task_id": 3, "time": 1, "score": 100.0},
            {"user_id": 99, "task_id": 3, "time": 1, "score": 60.0}]
    assert users_with_full_score(rows, task_id=3, full=100.0) == [12]

def test_build_dataset():
    from cmsops.analytics import build_dataset
    d = build_dataset([{"user_id": 1}], "2026-07-03T00:00:00+00:00")
    assert d == {"last_sync": "2026-07-03T00:00:00+00:00", "rows": [{"user_id": 1}]}
