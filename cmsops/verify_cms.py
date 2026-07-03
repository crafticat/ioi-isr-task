from __future__ import annotations
import os, subprocess, time

VERIFY_CONTEST_ID = int(os.environ.get("VERIFY_CONTEST_ID", "1"))
VERIFY_USERNAME = os.environ.get("VERIFY_USERNAME", "verifier")

def import_task(task_dir: str) -> str:
    """Import (or replace) the task into the verify contest; return its name."""
    subprocess.run(
        ["cmsImportTask", "-L", "italy_yaml", "-u", "-c", str(VERIFY_CONTEST_ID), task_dir],
        check=True,
    )
    import yaml
    with open(os.path.join(task_dir, "task.yaml"), encoding="utf-8") as fh:
        return yaml.safe_load(fh)["name"]

def submit_and_score(task_name: str, solution_files: list[str],
                     timeout_s: int = 900) -> dict[str, dict[int, float]]:
    from cms.db import SessionGen, Submission, SubmissionResult, Task, Participation, User
    results: dict[str, dict[int, float]] = {}
    for sol in solution_files:
        subprocess.run(
            ["cmsAddSubmission", "-c", str(VERIFY_CONTEST_ID),
             "-f", os.path.join("solutions", sol), VERIFY_USERNAME, task_name],
            check=True,
        )
    # Poll until every submission for this task is scored, then read subtask maxima.
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        with SessionGen() as s:
            task = s.query(Task).filter(Task.name == task_name).one()
            subs = (s.query(Submission)
                    .join(Participation).join(User)
                    .filter(Submission.task_id == task.id,
                            User.username == VERIFY_USERNAME).all())
            done = 0
            for sub in subs:
                sr = s.query(SubmissionResult).filter(
                    SubmissionResult.submission_id == sub.id,
                    SubmissionResult.dataset_id == task.active_dataset_id).first()
                if sr is not None and sr.scored():
                    done += 1
                    fname = sub.files.keys().__iter__().__next__() if sub.files else "solution"
                    detail = sr.score_details or []
                    # score_details is a list of per-subtask dicts (idx, score).
                    per_st = {}
                    for i, st in enumerate(detail, start=1):
                        idx = int(st.get("idx", i)) if isinstance(st, dict) else i
                        val = float(st.get("score", 0)) if isinstance(st, dict) else 0.0
                        per_st[idx] = val
                    results[fname] = per_st
            if done == len(subs) and subs:
                return results
        time.sleep(5)
    raise TimeoutError("submissions did not finish scoring within the deadline")
