# CMS internals discovered while building Uchuva

Cherry-picked notes on the `ioi-isr/cms` fork. Pin to commit
`ec40793` (israeli_cms_beta) for these line numbers.

## italy_yaml loader contract

`cmscontrib/loaders/italy_yaml.py`:

| Discovery | Path attempts |
|---|---|
| Statement | `statement/`, `statements/`, `Statement/`, `Statements/`, `testo/` |
| Attachments | `att/`, `attachements/`, `Attachements/`, `attachments/`, `Attachments/` |
| Solutions | `solutions/`, `Solutions/`, `solution/`, `Solution/` (subdir OR flat) |
| Validators | `validators/`, `Validators/`, `validator/`, `Validator/` |
| Managers | `managers/`, `Managers/` (also `check/checker` for prebuilt binary) |
| Generators | `generators/`, `Generators/`, `generator/`, `Generator/` |
| Testcases | `tests.zip`, `testcases.zip`, `tests/`, `testcases/`, legacy `input/`+`output/` |

`task.yaml` keys consumed (subset):
- `task_type` ∈ `Batch`, `BatchAndOutput`, `OutputOnly`, `Communication`, `TwoSteps`
- `task_type_parameters` — **plain YAML list**, no `!!python/tuple`
- `compilation` (overrides) ∈ `alone`, `grader`, `stub`
- `output_eval` (overrides) ∈ `diff`, `comparator`, `realprecision`
- `feedback_level` ∈ `full`, `restricted`, `oi_restricted`
- `score_mode` ∈ `max`, `max_subtask`, `max_tokened_last`
- `token_mode` ∈ `disabled`, `infinite`, `finite`
- `n_input` / `n_test` — required for legacy `input/`+`output/` layout
- `model_solutions` — list of `{name, description, expected_score_min, expected_score_max, subtask_expected_scores}` (scores must be float)
- `generators` — list of `{filename, input_template, output_template, language}`
- `subtask_validators` — list of `{filename, subtask_index}` (subtask index can be inferred from filename if it contains a digit)

Subtask scoring derived from `gen/GEN`:
- `#ST: <points>` opens a new subtask.
- Sum of all `#ST:` points must equal exactly 100, else import fails.
- `#COPY: <path>` copies a prepared file verbatim as the next input.
- Other non-`#` lines are passed as argv to the compiled `gen/generator.*`
  (stdout becomes the input file).

## Custom checker (comparator) interface

`cms/grading/tasktypes/Batch.py`:

```
argv[1] = input file
argv[2] = expected output
argv[3] = contestant output
stdout  = a single float in [0.0, 1.0]
stderr  = optional textual message
```

Combined with `GroupMin`:
- subtask points × `min(per-test scores in subtask)`.

For the common "15% partial credit" rule (correct -1 detection but wrong T):
- 1.0 if exact match
- 0.15 if expected ≠ -1, contestant ≠ -1, but values differ
- 0.0 otherwise

## Validator runtime

`cms/grading/subtask_validation.py:_run_validator`:

```
./validator input.txt output.txt
stdin  = input.txt
exit 0 = pass
exit !=0 = fail (stderr captured)
```

Compiled by CMS at import time via `compile_manager_source` (uses isolate).

## Score visibility

To make contestants see scores in the UI:
- `task.feedback_level = "full"` (otherwise default ILOI value `oi_restricted` hides scores)
- `contest.token_mode = "infinite"` AND `task.token_mode = "infinite"`
  (CMS reveals scores via tokens; infinite ⇒ contestants auto-have a token per submission)
- `contest.score_precision`, `task.score_precision` ≥ 2 to see decimals like 20.95

## Admin endpoints worth knowing

- `GET /task/<task_id>/export` — produces the canonical italy_yaml-loadable
  zip (tests bundled into `tests.zip`, solutions in subdir form). This is
  THE recommended format for cross-CMS transfer.
- `POST /dataset/<dataset_id>/generator/<gen_id>/generate` — runs a
  registered generator from the admin UI.
- `POST /dataset/<dataset_id>/generators/add` — add a new generator.

## isolate cgroup v2 setup (containerized)

Without systemd, no `isolate-cg-keeper.service` runs. Wire manually:

```bash
sudo mkdir -p /run/isolate /sys/fs/cgroup/isolate
echo '+cpu +memory +pids +cpuset +io' | sudo tee /sys/fs/cgroup/cgroup.subtree_control >/dev/null
echo '+cpu +memory +pids +cpuset +io' | sudo tee /sys/fs/cgroup/isolate/cgroup.subtree_control >/dev/null
echo '/sys/fs/cgroup/isolate' | sudo tee /run/isolate/cgroup >/dev/null
```

Controllers MUST be enabled in `/sys/fs/cgroup/isolate/cgroup.subtree_control`
(not just root), else isolate fails opening `memory.events` in box-N
cgroups.

## arm64 isolate workaround

Upstream `http://www.ucw.cz/isolate/debian/` is amd64-only. Patch the
Dockerfile to build from source:

```dockerfile
RUN apt-get install -y libcap-dev libsystemd-dev pkg-config asciidoc-base && \
    cd /tmp && \
    curl -L https://github.com/ioi/isolate/archive/refs/tags/v2.0.tar.gz | tar xz && \
    cd isolate-2.0 && make isolate && \
    (make install-isolate || make install)
```
