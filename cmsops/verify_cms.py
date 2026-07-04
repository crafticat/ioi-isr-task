"""In-container glue for cmsops.verify.

Everything here runs INSIDE the devcms container (the CMS venv provides the
``cms*`` CLIs on PATH and the ``cms.db`` package). The only pure function is
:func:`parse_score_details`, which is unit-tested from the host.

Environment:
    VERIFY_CONTEST_ID  id of the contest to import into / submit to
    VERIFY_USERNAME    contestant username the verifier submits as
"""
from __future__ import annotations
import os
import subprocess
import time

VERIFY_CONTEST_ID = int(os.environ.get("VERIFY_CONTEST_ID", "1"))
VERIFY_USERNAME = os.environ.get("VERIFY_USERNAME", "verifier")

# Loader sentinel files written into the task dir by italy_yaml. A stale
# .import_error makes the next `cmsImportTask -u` abort ("last attempt to
# import failed"); removing .itime forces the full has-changed update path so
# repeated verify runs behave like a fresh import.
_LOADER_SENTINELS = (".itime", ".import_error")


def import_task(task_dir: str) -> str:
    """Import (or update) the task into the verify contest; return its name.

    Uses ``cmsImportTask -L italy_yaml -u -S -c <contest>``: ``-S`` skips the
    statement (verify only needs the dataset, so fixture tasks don't have to
    ship a PDF).

    Note: if the task declares ``model_solutions:``, the importer also creates
    placeholder submissions under the hidden ``__model_solutions__`` system
    participation (a *different* contest). We never poll those — verify
    submits its own copies as VERIFY_USERNAME and tracks their ids.
    """
    task_dir = os.path.abspath(task_dir)
    for sentinel in _LOADER_SENTINELS:
        try:
            os.remove(os.path.join(task_dir, sentinel))
        except OSError:
            pass
    subprocess.run(
        ["cmsImportTask", "-L", "italy_yaml", "-u", "-S",
         "-c", str(VERIFY_CONTEST_ID), task_dir],
        check=True,
    )
    import yaml
    with open(os.path.join(task_dir, "task.yaml"), encoding="utf-8") as fh:
        return yaml.safe_load(fh)["name"]


def parse_score_details(score_details: object) -> dict[int, float]:
    """Extract per-subtask scores from a Group* ``score_details`` blob.

    The fork's ``ScoreTypeGroup.compute_score`` (cms/grading/scoretypes/abc.py)
    stores one dict per subtask::

        {"idx": <0-based subtask index>, "score": <rounded score>,
         "max_score": ..., "score_fraction": ..., "testcases": [...]}

    and cms/grading/scorecache.py parses the same ``idx``/``score`` keys.
    Non-group details (e.g. the Sum score type stores per-testcase dicts
    without ``idx``+``score``, compile failures store ``[]``) yield ``{}``.
    """
    out: dict[int, float] = {}
    if not isinstance(score_details, list):
        return out
    for st in score_details:
        if isinstance(st, dict) and "idx" in st and "score" in st:
            out[int(st["idx"])] = float(st["score"])
    return out


def submit_and_score(
    task_dir: str,
    task_name: str,
    solution_files: list[str],
    timeout_s: int = 900,
) -> dict[str, dict[int, float]]:
    """Submit each ``solutions/<file>`` as VERIFY_USERNAME and await scores.

    Returns ``{solution_filename: {subtask_idx: score}}`` built from each
    submission's ``SubmissionResult.score_details`` (per-solution — the
    ``ParticipationTaskScore.subtask_max_scores`` cache is *not* usable here
    because it aggregates the max over all of the participation's submissions,
    which would mask a weak solution behind the full one).
    """
    from cms.db import SessionGen, Submission, SubmissionResult, Task, \
        Participation, User

    task_dir = os.path.abspath(task_dir)

    def _task(s) -> "Task":
        return (s.query(Task)
                .filter(Task.contest_id == VERIFY_CONTEST_ID,
                        Task.name == task_name).one())

    def _own_submission_ids(s, task) -> set[int]:
        rows = (s.query(Submission.id)
                .join(Participation).join(User)
                .filter(Submission.task_id == task.id,
                        User.username == VERIFY_USERNAME).all())
        return {row[0] for row in rows}

    # Submit sequentially, mapping each new submission id to the solution
    # filename we just sent (no reverse-engineering from Submission.files).
    sub_id_to_sol: dict[int, str] = {}
    for sol in solution_files:
        path = os.path.join(task_dir, "solutions", sol)
        if not os.path.isfile(path):
            raise FileNotFoundError("model solution file not found: %s" % path)
        with SessionGen() as s:
            task = _task(s)
            if len(task.submission_format) != 1:
                raise RuntimeError(
                    "verify only supports single-file tasks; %s has "
                    "submission_format %r" % (task_name, task.submission_format))
            codename = task.submission_format[0]
            before = _own_submission_ids(s, task)
        # cmsAddSubmission signature (cmscontrib/AddSubmission.py):
        #   cmsAddSubmission -c CONTEST -f <codename>:<path> USERNAME TASKNAME
        # -f is repeatable; language is inferred from the file extension
        # against the contest's languages.
        subprocess.run(
            ["cmsAddSubmission", "-c", str(VERIFY_CONTEST_ID),
             "-f", "%s:%s" % (codename, path), VERIFY_USERNAME, task_name],
            check=True,
        )
        with SessionGen() as s:
            task = _task(s)
            new = _own_submission_ids(s, task) - before
            if len(new) != 1:
                raise RuntimeError(
                    "expected exactly one new submission for %s, found %d"
                    % (sol, len(new)))
            sub_id_to_sol[new.pop()] = sol

    # Poll until every submission we created is scored.
    deadline = time.time() + timeout_s
    results: dict[str, dict[int, float]] = {}
    while time.time() < deadline:
        with SessionGen() as s:
            task = _task(s)
            results = {}
            for sub_id, sol in sub_id_to_sol.items():
                sr = (s.query(SubmissionResult)
                      .filter(SubmissionResult.submission_id == sub_id,
                              SubmissionResult.dataset_id ==
                              task.active_dataset_id)
                      .first())
                if sr is not None and sr.scored():
                    results[sol] = parse_score_details(sr.score_details)
            if len(results) == len(sub_id_to_sol) and sub_id_to_sol:
                return results
        time.sleep(5)
    raise TimeoutError(
        "submissions did not finish scoring within %ds (scored %d/%d)"
        % (timeout_s, len(results), len(sub_id_to_sol)))
