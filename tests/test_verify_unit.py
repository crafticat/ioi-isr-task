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
