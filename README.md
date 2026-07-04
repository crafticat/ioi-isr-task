# ILOI tasks-as-code

Manage ILOI competition tasks as code and answer contest questions, with the
production CMS touched only by reviewed GitHub Actions workflows through scoped
service accounts. The agent (Claude) only pushes branches — it has no CMS
credentials and no CMS network path.

> ⚠️ **This repo is PUBLIC for the testing phase.** That is safe only while it
> contains framework code and no real data. **Do not push real (unpublished) task
> packages or any contest/student data while it is public** — make it private and
> move to GitHub Pro first. See `docs/secrets.md`.

## Layout
- `cmsops/` — the tested Python package (client, deploy, drift, analytics, verify).
- `.github/workflows/` — `verify` (CI task verification), `deploy` (human-approved
  import), `drift` (server→PR), `dataset` (analytics fetch), `probe` (Phase-0 check).
- `.claude/skills/` — the agent's skills, auto-loaded by any Claude Code session
  on this repo (browser `claude.ai/code` or local): `iloi-cms-task` (authoring a
  question end-to-end) and `cms-analytics` (contest Q&A). Committing them here is
  what makes browser-based, zero-install authoring work.
- `docs/` — `service-accounts.md`, `secrets.md`, `boss-brief.md`.

## Getting started
1. Run the `probe-cms-reachability` workflow (set `CMS_BASE_URL` first) to confirm a
   runner can reach production. See `docs/secrets.md`.
2. Create the `ai-reader` / `ai-uploader` CMS accounts — `docs/service-accounts.md`.
3. Set the repo secrets — `docs/secrets.md`.

Run the test suite locally: `python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]" && pytest`.
