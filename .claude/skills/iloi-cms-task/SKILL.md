---
name: iloi-cms-task
description: Build a new ILOI/IOI-style competitive-programming task targeting the ioi-isr CMS fork (italy_yaml format). Use this when the user wants to create a new problem from a .docx/spec, set it up for CMS, add tests + validators + reference solutions + custom checker, and verify end-to-end. Walks through algorithm verification, adversarial test design, per-subtask discrimination, statement PDF export, CMS arm64 docker setup, and submission-level verification.
---

# Building an ILOI CMS task package, end to end

This skill captures the exact procedure used to build a verified, importable
ILOI task. **Don't skip the verification steps** — most mistakes come from
plausible-but-wrong algorithm answers being recorded as "expected" outputs.

## Pre-flight

Required inputs from the user:
- A problem document (typically `.docx`) with statement + subtask weights.
- A working directory.
- Knowledge of which CMS fork is target (default: `ioi-isr/cms`, branch
  `israeli_cms_beta`).

Optional but useful:
- Hebrew-aware PDF tooling (LibreOffice/Pages/Word) for statement export.
- Apple-silicon mac OR Linux box with docker + privileged + cgroup v2.

## Phase 1 — Read the problem carefully

1. Extract the .docx text. **Don't trust the first extraction** — raw OOXML
   often concatenates table-cell digits ("1" + "3" → "13") and you can
   easily misread the subtask weights. Always cross-check against the
   rendered PDF or the original Word document.
2. Identify: function signature, U/N/P bounds, output bound (existence!),
   subtask count and weights (sum must equal 100), special rules like a
   "15% partial credit" floor.
3. Convert .docx → PDF for the statement once and inspect the rendered
   layout. `soffice --headless --convert-to pdf <file>.docx` works but
   substitutes fonts (Liberation Sans for Arial, etc). For a real contest,
   ask the user to export from Word/Pages directly.

## Phase 2 — Design the algorithm

Before writing the solver:
1. Reformulate (often a problem is naturally a subset-sum / parity / cycle
   problem in disguise).
2. Derive a complexity bound. **Re-derive the K_max / time-budget bound at
   the worst valid input** — not the typical input. A bound calibrated for
   the easy case can silently exclude pathological-but-legal inputs.
3. Hand-check on at least the sample testcases and one adversarial case.

## Phase 3 — Scaffold the task package

Target layout (matches the italy_yaml loader's expectations):

```
TaskName/
├── task.yaml                  # batch+grader, n_input, public_testcases, …
├── statement/statement.pdf
├── sol/                       # canonical model used by CMS
│   ├── grader.cpp             # reads stdin, calls user fn, prints result
│   ├── <task>.h               # function signature shared with contestant
│   └── <task>.cpp             # canonical solution
├── solutions/                 # OPTIONAL reference solutions for testset
│   ├── full.cpp               #   discrimination; each declared in task.yaml
│   ├── partial_*.cpp          #   with expected_score_min/max
│   └── …                      
├── managers/                  # OPTIONAL custom checker for partial credit
│   └── checker.cpp            #   (filename "checker" -> output_eval=comparator)
├── generators/                # OPTIONAL — CMS compiles + lets you run
│   └── generator.cpp          #   from admin UI Generators section
├── validators/                # one per subtask: validator_<N>.cpp
│   └── validator_0..5.cpp     #   subtask 0 == samples, indexes 0-based
├── gen/                       
│   ├── generator.cpp          # argv-driven, one test per invocation
│   ├── GEN                    # script: #ST: <pts> markers + invocation lines
│   ├── build_tests.py         # compiles + walks GEN -> input/output files
│   ├── run_validators.py      # validates every input against its subtask
│   └── judge.py               # local CMS-style scoring with partial credit
├── input/  output/            # 1:1 with GEN lines
└── att/                       # contestant-facing attachments + sample I/O
```

See `templates/` for starter files.

The tree above is the **dev/authoring** layout (used to generate + verify
locally). The **delivered package** that imports into the production CMS is the
canonical export layout — flatter, with tests bundled:

```
TaskName/
├── task.yaml
├── tests.zip                  # input_*.txt / output_*.txt inside
├── managers/                  # grader.cpp, <task>.h, checker.cpp
├── generators/generator.cpp
├── solutions/<name>/<task>.cpp  # each model solution in its own folder
├── validators/validator_0..N.cpp
└── statements/                # english.pdf, hebrew.pdf (+ .docx)
```

`task/<id>/export` from CMS produces exactly this (see Phase 11). Authoring the
`task.yaml` in the canonical schema (below) means the package round-trips
without hand-editing.

### task.yaml essentials

**Two schemas exist — author in the canonical one.** The local `italy_yaml`
dev-loader auto-derives the task type from the on-disk layout and accepts a
minimal yaml. But the **production ILOI CMS importer** (and what
`task/<id>/export` round-trips to) uses a richer, discrete-key schema. Author
in that canonical schema — it's a superset the dev-loader ignores the extras
of, so the same package imports cleanly into the real CMS with zero fix-up.
`templates/task.yaml` is the canonical form; the key differences from the old
minimal form:

- Use discrete keys, NOT the `task_type_parameters` tuple:
  - `compilation: grader` (or `alone` for no grader)
  - `output_eval: comparator` (if you ship `managers/checker.cpp`) or `diff`
  - `infile: ''` / `outfile: ''`
- Declare `submission_format: [TASKNAME.%l]`.
- Declare a **`validators:` block** — one entry per subtask with `subtask_index`
  (0-based, index 0 == samples). The dev-loader auto-detects validators from
  the dir; the production importer needs them listed. Easy to forget, and a
  missing block silently drops per-subtask input validation.
- CMS meta the production importer expects: `version: Default`,
  `score_mode: max_subtask`, `feedback_level: oi_restricted`,
  `score_precision: 2`, and the `token_*` fields (`token_mode` +
  `token_min_interval`/`token_gen_initial`/`token_gen_number`/`token_gen_interval`).
- `primary_language: he`, but keep `title:` in **English** (the Hebrew title
  lives in the statement).
- `n_input` MUST equal the number of `input_*.txt` files in `tests.zip`
  (`input_template: input_*.txt`, `output_template: output_*.txt`).
- `score_type: GroupMin` + regex `score_type_parameters`; sum of points must be
  **exactly 100** (see Phase 6b for the codename/regex convention).
- All scores are Python **floats** (write `100.0`, not `100`).
- Set each key **once** — a duplicate `public_testcases` (or any repeated key)
  is a silent YAML footgun; the last one wins.

### What is "public"? Two independent axes (don't conflate them)

"Public" means two different things in CMS. They're controlled separately and
confusing them causes bogus "answer leak" scares (see failure-mode #16).

**Axis 1 — test *bytes* the contestant can read → SAMPLES ONLY, always.**
The only testcases whose raw input/output bytes are ever visible are the
**sample tests printed in the statement** (shipped as `att/sample-*.in/.out`
attachments; they're the `ST0`/subtask-0 group, worth **0 points**, and every
submission runs against them). They leak nothing — the contestant already has
them from the statement — and they let contestants verify I/O format. Every
other (scoring) test stays byte-hidden; CMS never hands out its input/output.

**Axis 2 — `public_testcases` in task.yaml → per-test VERDICT visibility.**
This does NOT expose bytes. It controls whether a contestant sees per-test
pass/fail/score on a submission *without spending a token*.
- Default: **`public_testcases: all`** — better debugging feedback, no answer
  exposure. This is the confirmed ILOI default.
- `feedback_level: oi_restricted` is the safety collar: it collapses feedback
  to the **subtask level** (no per-test verdicts). The fixed Uchuva/DamLogs
  packages ship `public_testcases: all` + `feedback_level: oi_restricted`.

**The one real caveat — low-entropy outputs.** For yes/no or tiny-integer
outputs, a *full* per-test verdict channel can let a contestant reconstruct the
answer key over a few submissions and hardcode it. `oi_restricted` (subtask-only
feedback) prevents this. So only use `feedback_level: full` on such decision-
style tasks if you also drop verdict visibility back to samples-only.

| Axis | Setting | Rule |
|---|---|---|
| Test bytes (statement/attachments) | samples only | Always. `ST0`, 0 pts. |
| `public_testcases` (verdict visibility) | `all` | Default; pair with `feedback_level: oi_restricted`. |

## Phase 4 — Write the canonical model solution

Put it at `sol/<task>.cpp`. This solution's output on every test in `gen/GEN`
becomes the "expected answer". Bugs here become wrong answers in the testset.

**Verification protocol — do all three:**

1. **Brute-force stress** (small inputs, ground truth):
   - Implement a true 2^T sign-mask enumerator in C++.
   - Random sample N≤4, P[i] small, U≤30. Cap T≤22.
   - 1000-5000 trials, expect 0 mismatches.

2. **Independent algorithm** (different code path, medium inputs):
   - Implement the problem via classic subset-sum DP (O(T·S)) or other
     algorithm that doesn't share code with the model.
   - Where DP is decisive (S not too large), cross-check.

3. **Per-test sanity** (the actual testset):
   - For every test in `input/`, run the independent algorithm where
     budgets allow, and confirm it returns the same T_min as the model.
   - For tests beyond DP budget, fall back to a closed-form structural
     verifier per generator mode (e.g. `n1_only`, `subtract_only`,
     `path1big` all have analytic answers).

See `references/verification.md` for ready-to-adapt scripts.

## Phase 5 — Design the testset adversarially

Random tests are typically *not* hard. Per-subtask, identify the cheap
solver you want to defeat:

| Subtask kind | Defeat with |
|---|---|
| N=1 closed form | U just below 2^k boundary (forces correct divisibility check) |
| "subtract-only suffices" | Large T_sub (≥ 10⁵) forces brute force out of budget |
| N=2 | "path1big" style P=[1, 2^40] with U near U_max → T_min ~ 2·U |
| "≤ K turns when zeroable" | Mixed-required: random signs s.t. U is NOT a cyclic prefix sum |
| Full | T_min ≫ K (path1big, sparse-cycle), bit-cascade U (2^k - 1) |

**Generator hygiene:**
- `mixed_required` mode should `reject + reseed` any U where subtract-only
  also solves it. Without this rejection, "mixed" tests may accidentally
  fall to a subtract-only solver.
- Set `feedback_level: oi_restricted` for production; `full` for local dev.
- Add an `impossible` mode that picks `U % 2^E_min != 0` for -1 cases.

## Phase 6 — Validators (one per subtask)

Each `validators/validator_<i>.cpp` reads stdin, validates the input,
exits 0 on pass / non-zero on fail. CMS compiles them in its sandbox at
import time and runs them per testcase.

**Common pitfall:** Don't use `CARRY_LIMIT > 62` with signed `long long` —
shifts by ≥64 are UB and GCC silently no-ops them. For T ≤ 1000, `CARRY_LIMIT
= 62` is safe.

For "structural" constraints (subtract-only solvable, ≤K turns achievable),
the validator can re-implement the relevant feasibility check directly so
it's an independent witness of the testset's correctness.

## Phase 6b — Subtask containment (CRITICAL — easy to forget)

**Audit:** for each subtask K, count how many tests `validator_K` passes
vs. how many are assigned to subtask K via your GEN. If 47-71 tests pass
the validator but live in OTHER subtasks (real Uchuva numbers!), you have
*containment debt*: a contestant who solves subtask K's constraint
algorithm gets only partial credit because tests demonstrating K's
constraint are scattered into harder subtasks.

**Fix:** use regex-based `score_type_parameters` so every test is assigned
to every subtask whose validator passes. **Prefer explicit `ST<k>_` codename
tags** over bare single letters — they're unambiguous and match the canonical
export form:

```yaml
score_type: GroupMin
score_type_parameters:
  - [0,  ".*ST0_(?#CMS)"]   # samples (0 pts)
  - [3,  ".*ST1_(?#CMS)"]   # subtask 1 (N=1)
  - [4,  ".*ST2_(?#CMS)"]   # subtask 2 (subtract-only)
  - [21, ".*ST3_(?#CMS)"]   # subtask 3 (N=2)
  - [35, ".*ST4_(?#CMS)"]   # subtask 4 (T≤1000)
  - [37, ".*ST5_(?#CMS)"]   # subtask 5 (full — matches every test)
```

`(?#CMS)` is a regex inline comment (a no-op) that acts as a right boundary so
`.*ST1_` cannot accidentally match `ST10_`/`ST11_`. Each test is named
`input_ST1_ST2_ST4_ST5_017_bde.txt` — the `ST<k>` tags list exactly the
subtasks it satisfies (a trailing letter suffix like `_bde` is fine to keep as
a human-readable mnemonic). The bare single-letter form `.*b.*` also works
(DamLogs still uses it) but is easier to get wrong.

Produce the codenames with `gen/classify_and_rename.py` (in `templates/`):

1. Compile every `validators/validator_<i>.cpp`.
2. For each test, run every validator → record pass/fail.
3. Build codename `ST<i>_..._NNN` from the set of passing validators.
4. Lay out as `input_<codename>.txt` / `output_<codename>.txt` (bundled into
   `tests.zip` for the canonical package).

CMS then matches each test's codename against each subtask's regex; a test is
in every subtask whose regex matches.

**Always do this.** It's a one-script post-processing step and turns a
naively-assigned testset into properly-contained one. Verify reference
solutions still score their declared values afterward (they will if the
algorithms are correct).

## Phase 7 — Reference solutions with expected scores

For each cheap-solver-class you want to discriminate, write one in
`solutions/`. In the canonical package each solution lives in its own folder:
`solutions/<name>/TASKNAME.cpp`. Declare each in `task.yaml` with its
`language` and `files`:

```yaml
model_solutions:
  - name: full
    description: Intended solution.
    expected_score_min: 100.0
    expected_score_max: 100.0
    language: C++17 / g++
    files: [TASKNAME.cpp]
```

**Pin per-subtask scores, not just the total.** The strongest calibration
guard is `subtask_expected_scores` — declare the expected value of EACH
subtask, so a drift that raises one subtask while lowering another (net-zero
on the total) still fails the import:

```yaml
  - name: subtract_only_fallback
    description: subtract-only + return-1 fallback; stacks the 15% rule.
    expected_score_min: 20.95
    expected_score_max: 20.95
    language: C++17 / g++
    files: [TASKNAME.cpp]
    subtask_expected_scores:
      '1': {min: 3.0,  max: 3.0}
      '2': {min: 4.0,  max: 4.0}
      '3': {min: 3.15, max: 3.15}
      '4': {min: 5.25, max: 5.25}
      '5': {min: 5.55, max: 5.55}
```

**Ship targeted probe solutions — one per subtask.** Beyond the intended
solution and any cheap-exploit ceilings, include solutions that isolate a
single subtask:

- **Single-subtask probe** (e.g. `st3_only`): solves exactly subtask K and
  scores 0 everywhere else. Pins that subtask's full value; if it starts
  scoring on other subtasks, a test leaked across a boundary.
- **15%-floor probe** (`verdict_only` / `yes_no`): a correct-existence-only
  solver that collects exactly 15% of every subtask. Its per-subtask expected
  scores are literally 0.15 × each subtask's points (e.g. 0.45 / 0.60 / 3.15 /
  5.25 / 5.55). If those move, the checker's partial-credit rule or the GEN
  changed under you.

These are cheap to write and turn "did the total look right?" into "is every
subtask calibrated to the point?". The local `gen/judge.py --verify-all`
script validates the totals; the production importer validates
`subtask_expected_scores` per subtask at import time.

## Phase 8 — Custom checker (only if the statement needs partial credit)

If the statement awards partial credit for non-trivial conditions (e.g. a
"15% if -1 detection correct, T value wrong"), default `diff` scoring can't
express it. Add `managers/checker.cpp` with the CMS comparator interface:

```cpp
// argv[1]=input, argv[2]=expected, argv[3]=user_output
// stdout: a single number in [0.0, 1.0]
// stderr: contestant-facing outcome — emit a translate:<key> TOKEN
```

Combined with `GroupMin`, returning 0.15 on partial-credit tests gives the
right per-subtask floor automatically.

**Feedback messages must be `translate:` tokens, not free English.** The
checker's stderr line is shown to the contestant as the outcome; the ILOI CMS
localizes it from a translation key. Use exactly:

- `translate:success` — full credit (score 1.0)
- `translate:wrong` — no credit (score 0.0)
- `translate:partial` — partial credit (e.g. 0.15)

Free-text English (`"Correct"`, `"Wrong (returned -1)"`) ships an
un-localized, contest-inconsistent message and gets rewritten on import — the
Uchuva re-export replaced every stderr string with one of these three tokens.
`templates/checker.cpp` already uses them.

Set `output_eval: comparator` (the canonical discrete key; the old
`task_type_parameters` tuple's third slot).

## Phase 9 — CMS local setup (macOS arm64)

The ioi-isr Dockerfile pulls `isolate` from a Debian repo that's amd64-only.
On Apple Silicon, **patch the Dockerfile to build isolate from source**:

```dockerfile
RUN apt-get install -y libcap-dev libsystemd-dev pkg-config asciidoc-base && \
    cd /tmp && \
    curl -L https://github.com/ioi/isolate/archive/refs/tags/v2.0.tar.gz | tar xz && \
    cd isolate-2.0 && make isolate && make install
```

At container startup, wire up isolate v2's cgroup runtime (no systemd in
the container, so the standard `isolate-cg-keeper.service` is unavailable):

```bash
sudo mkdir -p /run/isolate /sys/fs/cgroup/isolate
echo '+cpu +memory +pids +cpuset +io' | sudo tee /sys/fs/cgroup/cgroup.subtree_control
echo '+cpu +memory +pids +cpuset +io' | sudo tee /sys/fs/cgroup/isolate/cgroup.subtree_control
echo '/sys/fs/cgroup/isolate' | sudo tee /run/isolate/cgroup
```

**Critical:** controllers must be enabled in `/sys/fs/cgroup/isolate/cgroup.subtree_control`
(not just root) so isolate's `box-N` cgroups inherit them. Without this,
isolate fails with `Cannot open /sys/fs/cgroup/isolate/box-0/memory.events`.

See `templates/setup_cms.sh` for an idempotent end-to-end script.

## Phase 10 — Import + verify in real CMS

```bash
# 1. DB
psql -h devdb -U postgres -d postgres -c "SELECT pg_terminate_backend(pid) \
    FROM pg_stat_activity WHERE datname='cmsdb' AND pid <> pg_backend_pid();"
dropdb -h devdb -U postgres cmsdb && createdb -h devdb -U postgres cmsdb
cmsInitDB

# 2. Import
cmsImportTask -L italy_yaml /path/to/task
# Expect "Found N model solution(s)", "Found M validator(s)", "Found G generator(s)",
# "Imported X model solution(s)", "Import finished (new task id: 1)"

# 3. Contest + user (via cms.db API or admin UI)

# 4. Start services
cmsLogService 0 &
cmsResourceService -a <contest_id> &

# 5. Wait for model-solution evaluation. Compare to declared scores via:
docker exec -i <container> python3 -c '
from cms.db import SessionGen, Submission, ModelSolutionMeta
with SessionGen() as s:
    metas = {m.submission_id: (m.name, m.expected_score_min, m.expected_score_max)
             for m in s.query(ModelSolutionMeta).all()}
    for sub in s.query(Submission).order_by(Submission.id).all():
        sr = sub.get_result()
        score = sr.score if sr and sr.scored() else "pending"
        meta = metas.get(sub.id, (sub.id, None, None))
        print(f"{meta[0]}: got={score} expected=[{meta[1]},{meta[2]}]")'

# Every row must say got == expected (within precision). If not, the testset
# isn't discriminating correctly — go back to phase 5 and tighten.
```

For end-to-end submission flow, log in via the contestant web UI and
submit. Or POST `/tasks/<name>/submit` with multipart-form directly.

## Phase 10a — Audit per-subtask T_min/N/U distributions

**Do this BEFORE red-teaming.** For every subtask whose constraint
is a numerical bound `≤ B`, plot the distribution of its tests'
relevant statistic (T_min, N, U, whatever the bound is). If tests
cluster at `≪ B`, a trivial heuristic with cap < B passes for free —
even though no red-team attacker would try that specific cap.

Lesson from Uchuva: ST4 ("T_min ≤ 1000 when zeroable") had 74 of 77
solvable tests with T_min < 500, only 3 in [500, 999]. A
`brute_force_100` solution would have scored full ST4. The red-team
agent never tried cap=100, so it missed the bug entirely. The fix
was to construct path1big inputs with T_min provably in [500, 1000],
which required a structural sweep — see
`references/distribution-audit.md` for the audit script + fix
recipe.

## Phase 10b — Red-team the testset with an adversarial agent

Before declaring the testset done, dispatch a sub-agent to find
solutions that score "too much" given their algorithmic simplicity:

```
Agent({
  subagent_type: "general-purpose",
  prompt: "Red-team the <task> testset. Read sol/<task>.cpp and
  solutions/*.cpp. Use gen/judge.py to score candidates. Write at least
  8 buggy/heuristic solutions targeting: greedies, wrong subset-sum,
  wrong bounds, multi-special-case stacks, partial-credit exploits.
  Report each as ATTACK <name>: expected_max actual which_subtask.
  Do NOT fix the testset; report only."
})
```

**Interpreting the report — distinguish 3 categories:**

1. **Real leaks** — algorithm that's wrong/heuristic but passes a
   subtask. Add adversarial GEN tests targeting the specific failure.
   Example: O(T) greedy passing ST2 (subtract-only).
2. **Hardware artifacts** — solution passes on dev hardware but would
   TLE on contest hardware. Verify by submitting at lower local TL
   (e.g. 0.2-0.5s). If it TLEs there, trust the contest server.
3. **Legitimate per-subtask scoring** — a stitched-together solver
   (e.g. "N=1 closed form + N=2 full algorithm + brute T≤1000 + fallback")
   that earns ST1+ST2+ST3+ST4 fully. **Not a leak** — that's how subtask
   scoring is designed; each subtask rewards correct per-subtask
   algorithms. Don't try to "fix" this with tests.

See `references/red-teaming.md` for the full attack catalog + how to
classify each kind of finding.

## Phase 11 — Export for upload to another CMS

Use **CMS's own admin endpoint** — don't roll your own format:

```bash
# As admin, with cookies set:
curl -sS -b cookies.txt http://localhost:8889/task/<task_id>/export \
     -o task-export.zip
```

This produces the canonical italy_yaml-loadable zip (tests bundled into
`tests.zip`, solutions in `solutions/<name>/uchuva.cpp` subdir form,
managers/, validators/, statements/). On the receiving CMS:

```bash
unzip task-export.zip
python3 cmscontrib/ImportTask.py -L italy_yaml task/
```

The format the loader accepts on import is a *superset* of what the
exporter produces, so round-trip is clean.

## Common failure modes (in encounter-order)

1. **Subtask weights mis-parsed** from .docx — verify against rendered PDF.
2. **Type errors at import**: `expected_score_min/max` must be float (`3.0`,
   not `3`).
3. **Old task.yaml schema rejected by production importer**: the discrete keys
   `compilation` / `output_eval` / `infile` / `outfile` replace the
   `task_type_parameters` tuple; `submission_format`, a `validators:` block,
   and the `version`/`score_mode`/`feedback_level`/`score_precision`/`token_*`
   meta are all required. Author in the canonical schema (`templates/task.yaml`).
   If you do keep a tuple for the dev-loader, it's a **plain YAML list**, never
   `!!python/tuple`.
4. **Generator-rejected inputs ignored**: `mixed_required` constructing
   subtract-only-solvable U dilutes the subtask.
5. **Validator UB**: `(V >> e)` for `e >= 64` on signed long long with -O2.
6. **K_max too tight**: bounds calibrated for "typical" inputs miss
   pathological-but-legal sparse cycles. Re-derive at U_max.
7. **isolate cgroup not wired**: `/sys/fs/cgroup/isolate/cgroup.subtree_control`
   must propagate controllers down.
8. **CMS DB orphans after redrop**: dropdb fails silently if connections
   linger — `pg_terminate_backend` first.
9. **Score N/A in contestant UI**: set `token_mode: infinite`,
   `feedback_level: full`, `score_precision: 2` on the task + contest.
10. **LibreOffice PDF font substitution** (Liberation vs Arial) — for
    pixel-perfect statement, export from Word/Pages.
11. **Subtask containment debt**: tests satisfying validator_K's
    constraint that aren't assigned to subtask K. Always run
    `classify_and_rename.py` and use regex `score_type_parameters`.
12. **n_input mismatch with `tests/` layout**: even if you use the
    `tests/` directory with `input.<codename>` files, the loader still
    cross-checks against `n_input`. Set it to the actual file count.
13. **Naive O(T) greedies passing on fast dev hardware**: M-series Macs
    execute ~2·10⁹ simple ops/sec; the same greedy would TLE on a
    typical 3 GHz Xeon contest server. **Either trust contest hardware
    will TLE it, or lower the dataset time_limit so dev matches prod.**
14. **Conflating the two axes of "public"** — test-byte visibility (samples
    only, always) vs. `public_testcases` verdict visibility (`all` by default,
    collared by `feedback_level: oi_restricted`). See the "What is public?"
    subsection under Phase 3. `public_testcases: all` does NOT expose bytes and
    does NOT enable a hardcoded-table attack (that earlier "100/100 exploit"
    was a red-team artifact — the agent had filesystem access to `tests/`,
    which a real contestant never does). Only real risk: full per-test feedback
    on a yes/no or tiny-integer task can leak the answer key — use
    `oi_restricted` there.
15. **Mis-categorizing red-team findings as leaks**: a multi-special-case
    stitched solver legitimately earning multiple subtasks is *correct*
    per-subtask scoring, not a bug. Don't add tests to "fix" it.
17. **Checker feedback in free English**: the stderr line must be a
    `translate:success` / `translate:wrong` / `translate:partial` token so the
    CMS localizes it — free text gets rewritten on import.
18. **Missing `validators:` block in task.yaml**: the production importer needs
    validators listed with `subtask_index`; the dev-loader auto-detects them,
    so this passes locally then silently drops input validation in prod.
19. **Only the total is pinned**: declare `subtask_expected_scores` per model
    solution — a net-zero calibration drift (one subtask up, another down)
    passes a total-only check but is a real bug. Ship one single-subtask probe
    per subtask plus a 15%-floor probe.
20. **Duplicate top-level yaml key** (e.g. `public_testcases` set twice): silent
    — the last occurrence wins. Set each key once.

## When applying this skill

When the user gives you a .docx (or other spec):

1. Read it carefully — extract bounds, subtask weights, special rules.
2. **Confirm the parsed subtask weights with the user** before continuing.
3. Brainstorm the algorithm (use the `superpowers:brainstorming` skill).
4. Write a plan (use `superpowers:writing-plans`) that goes through phases
   2–11 in this skill.
5. Implement phase-by-phase with the verification scripts.
6. **Don't skip verification** — every "expected" output in `output/` is
   generated by the model, so a model bug → testset bug.

See `templates/` for ready-to-copy starter files, and `references/` for
deeper notes on CMS internals discovered while building Uchuva.
