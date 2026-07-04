# Using the agent — the three roles

Nothing here requires installing anything. Only task authors need a Claude login.

## 1. Author a question (browser, zero install)

1. Open **claude.ai/code** in your browser, signed in with **your own** Claude
   subscription, and connect it to this repo.
2. Say what you want: *"Create a task about X — N ≤ 2·10⁵, subtasks for the
   quadratic and the greedy special case."* Claude (with the `iloi-cms-task`
   skill, auto-loaded from this repo) writes the statement, generator,
   solutions, validators, checker, and per-subtask expected scores, then pushes
   a branch.
3. **Self-test happens in CI:** the `verify` workflow imports the task into a
   throwaway CMS on a GitHub runner, runs every model solution, and asserts each
   subtask scores exactly what it should. Read the green/red report on the PR
   and tell Claude what to fix; iterate until green.
4. Say "it's ready" — deployment is the approver's move, not yours and not
   Claude's.

Power-user variant: run Claude Code locally with docker for an instant local
verify loop. Optional; the browser path is the supported default.

## 2. Approve a deploy (no Claude needed)

1. Actions → **deploy** → Run workflow (task id, task dir, contest id).
2. GitHub pauses the run for **your approval** (required reviewer on the
   `production` environment). Glance at the PR/diff it came from, approve.
3. The workflow snapshots the server's current version first (rollback =
   redeploy the snapshot from `snapshots/`), refuses running contests by
   default, and logs everything.

## 3. Ask about results (no install; Claude login only if you want the Q&A)

Open claude.ai/code on this repo and ask: *"Did any student manage to solve
DamLogs ST5?"* The `cms-analytics` skill answers from the fetched dataset,
always stating how fresh the data is and showing the query behind the answer —
so you can verify it yourself. (Coaches who prefer dashboards use the CMS
admin pages and never touch any of this.)

## Safety model in one line

Claude can only push git branches — the CMS is touched exclusively by the four
reviewed workflows, with scoped accounts, a human approval click on every
deploy, snapshots before every change, and a freeze during running contests.
