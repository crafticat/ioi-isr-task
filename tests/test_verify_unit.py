from cmsops.verify import compare_scores

def test_all_match():
    expected = {"solution_full.cpp": {1: 30, 2: 70}}
    actual   = {"solution_full.cpp": {1: 30, 2: 70}}
    ok, report = compare_scores(expected, actual)
    assert ok and "OK" in report

def test_mismatch_reported():
    expected = {"greedy.cpp": {1: 30, 2: 0}}
    actual   = {"greedy.cpp": {1: 30, 2: 70}}   # greedy unexpectedly passed ST2
    ok, report = compare_scores(expected, actual)
    assert not ok
    assert "greedy.cpp" in report and "2" in report

def test_verify_result_fails_when_no_expectations():
    from cmsops.verify import verify_result
    ok, report = verify_result({}, {})
    assert not ok and "no" in report.lower()

def test_verify_result_delegates_when_expectations_present():
    from cmsops.verify import verify_result
    ok, report = verify_result({"s.cpp": {1: 10}}, {"s.cpp": {1: 10}})
    assert ok


def test_parse_score_details_group():
    # Shape written by ScoreTypeGroup.compute_score (cms/grading/scoretypes/abc.py):
    # one dict per subtask with 0-based "idx" and rounded "score".
    from cmsops.verify_cms import parse_score_details
    details = [
        {"idx": 0, "score_fraction": 1.0, "score": 0.0, "max_score": 0,
         "testcases": [{"idx": "ST0_ST1_ST2_000", "outcome": "Correct"}]},
        {"idx": 1, "score_fraction": 1.0, "score": 30.0, "max_score": 30,
         "testcases": []},
        {"idx": 2, "score_fraction": 0.0, "score": 0.0, "max_score": 70,
         "testcases": []},
    ]
    assert parse_score_details(details) == {0: 0.0, 1: 30.0, 2: 0.0}


def test_parse_score_details_non_group_shapes():
    from cmsops.verify_cms import parse_score_details
    # Compilation failure: ScoreTypeGroup stores [].
    assert parse_score_details([]) == {}
    # Sum score type stores per-testcase dicts without idx+score pairs.
    assert parse_score_details([{"outcome": "Correct", "text": []}]) == {}
    # Defensive: not a list at all.
    assert parse_score_details(None) == {}
    assert parse_score_details({"idx": 0, "score": 1.0}) == {}


def test_load_expectations_canonical_schema(tmp_path):
    from cmsops.verify import _load_expectations
    (tmp_path / "task.yaml").write_text(
        """
name: aplusb
model_solutions:
- name: full
  subtask_expected_scores:
    '0': {min: 0.0, max: 0.0}
    '1': {min: 30.0, max: 30.0}
    '2': {min: 70.0, max: 70.0}
  files:
  - full.cpp
- name: weak_int32
  subtask_expected_scores:
    '1': {min: 30.0, max: 30.0}
    '2': {min: 0.0, max: 0.0}
  files:
  - weak_int32.cpp
""",
        encoding="utf-8",
    )
    expected = _load_expectations(str(tmp_path))
    assert expected == {
        "full.cpp": {0: 0.0, 1: 30.0, 2: 70.0},
        "weak_int32.cpp": {1: 30.0, 2: 0.0},
    }
