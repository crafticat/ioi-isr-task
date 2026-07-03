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
