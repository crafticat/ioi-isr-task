# ADR 0002 — verify.yml proven green on GitHub-hosted runners

**Date:** 2026-07-04
**Status:** Done

## What was proven

The `verify` workflow performs real CMS evaluation on a GitHub-hosted runner
(`ubuntu-24.04`): it builds the fork's docker image, brings up an isolated
CMS (postgres + privileged devcms with isolate cgroup-v2 wiring), imports the
changed task, submits every declared model solution as the `verifier` user, and
asserts per-subtask scores against `subtask_expected_scores`.

Proof runs (PR #1, branch `verify-green`):

- ❌ First attempt: https://github.com/crafticat/ioi-isr-task/actions/runs/28706348657
  — failed on a CI-only uid mismatch (runner checkout uid 1001 vs container
  uid 1100): pip couldn't write `cmsops.egg-info` at the mounted repo root.
  Fix: chmod the whole mounted workspace, not just `tasks/`.
- ✅ Green run: https://github.com/crafticat/ioi-isr-task/actions/runs/28706441992
  — log excerpt (the actual assertion output):

  ```
  OK       full.cpp       subtask 1: 30.0
  OK       full.cpp       subtask 2: 70.0
  OK       weak_int32.cpp subtask 1: 30.0
  OK       weak_int32.cpp subtask 2: 0.0    (deliberate int32 overflow — declared 0)
  ```

The negative path was proven locally (mis-declared expectation → `MISMATCH`,
exit 1), plus `verify_result` fails loudly on tasks declaring no expectations.

## Pinning

CI checks out the CMS fork at repo variable `CMS_FORK_SHA`
(= `6748a045df4f47a617c2023e1cc7eeba7049a666`, the commit the pipeline was
validated against). Bump it deliberately, re-running verify on a fixture PR.

## Fixture

`tasks/aplusb/` — 2 subtasks (30/70), two model solutions (`full.cpp`,
`weak_int32.cpp`) with opposite ST2 outcomes, kept permanently as the pipeline's
canary: any change to the verify machinery must keep this task green.
