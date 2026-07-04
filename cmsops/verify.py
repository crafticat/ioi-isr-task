from __future__ import annotations
import os
import sys

def compare_scores(
    expected: dict[str, dict[int, float]],
    actual: dict[str, dict[int, float]],
) -> tuple[bool, str]:
    """expected/actual: {solution_filename: {subtask_index: score}}.

    A solution matches if every expected subtask score equals the actual score.
    """
    lines: list[str] = []
    ok = True
    for sol, exp in expected.items():
        act = actual.get(sol, {})
        for st_idx, exp_score in exp.items():
            got = act.get(st_idx)
            if got is None or abs(got - exp_score) > 1e-6:
                ok = False
                lines.append(f"MISMATCH {sol} subtask {st_idx}: expected {exp_score}, got {got}")
            else:
                lines.append(f"OK       {sol} subtask {st_idx}: {got}")
    return ok, "\n".join(lines) if lines else "OK (no expectations declared)"


def verify_result(
    expected: dict[str, dict[int, float]],
    actual: dict[str, dict[int, float]],
) -> tuple[bool, str]:
    """Wraps compare_scores with a guard: a task that declares NO expectations
    must not pass verification vacuously (that would let an under-specified task
    through CI). Fail loud instead."""
    if not expected:
        return False, ("FAIL: task declares no model_solutions/subtask_expected_scores; "
                       "nothing was verified")
    return compare_scores(expected, actual)


def _load_expectations(task_dir: str) -> dict[str, dict[int, float]]:
    """Read subtask_expected_scores from the canonical task.yaml.

    Canonical schema (tasks/_template/task.yaml): each `model_solutions:`
    entry carries `files:` (list of filenames under solutions/) and
    `subtask_expected_scores:` mapping the 0-based subtask index (as a
    string — the same `idx` the Group* score types write in score_details)
    to `{min: .., max: ..}`. Verify pins the max (target) score.
    """
    import yaml  # PyYAML ships in the CMS venv
    with open(os.path.join(task_dir, "task.yaml"), encoding="utf-8") as fh:
        meta = yaml.safe_load(fh)
    out: dict[str, dict[int, float]] = {}
    for sol in meta.get("model_solutions", meta.get("solutions", [])) or []:
        files = sol.get("files") or []
        name = files[0] if files else sol.get("name", "solution")
        scores = sol.get("subtask_expected_scores") or {}
        out[name] = {int(k): float(v["max"] if isinstance(v, dict) else v)
                     for k, v in scores.items()}
    return out


def run(task_dir: str) -> int:
    """Headless verify inside the devcms container.

    Steps (uses cms CLIs already on PATH + a live DB):
      1. cmsImportTask -L italy_yaml -u -S -c <verify_contest_id> <task_dir>
      2. cmsAddSubmission for each declared model solution (as the verifier)
      3. wait for scoring, read each submission's score_details per subtask
      4. compare to subtask_expected_scores
    """
    from cmsops.verify_cms import import_task, submit_and_score  # thin cms.db wrappers
    task_dir = os.path.abspath(task_dir)
    expected = _load_expectations(task_dir)
    task_name = import_task(task_dir)
    actual = submit_and_score(task_dir, task_name, sorted(expected.keys()))
    ok, report = verify_result(expected, actual)
    print(report)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run(sys.argv[1]))
