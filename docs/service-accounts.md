# CMS service accounts for the agent

Create two dedicated admins in the production CMS (AWS → Admins → Add):

- **ai-reader** — enabled, NO permission flags. Effectively read-only
  (every mutating handler returns 403 via require_permission). Used by
  drift.yml and dataset.yml. Secret pair: CMS_READER_USER / CMS_READER_PASS.
- **ai-uploader** — used by deploy.yml only.
  - v1 (until Phase 6): set `permission_all` (task import requires it). The
    account is powerful, but the ONLY actor holding its credential is the
    deploy.yml workflow, which is bound to the `production` environment and
    cannot run without a named human's approval click.
  - Phase 6: set only `permission_import` — then the account can import tasks
    and nothing else.
  Secret pair: CMS_UPLOADER_USER / CMS_UPLOADER_PASS.

Rotate on any suspected exposure (revoke via AWS → Admins). Neither account can
SSH, run SQL, change users/scores, or touch infrastructure.

## ⚠️ Creating a read-only account (verified against the fork)

`cmsAddAdmin <user> -p <pass>` has **no read-only flag and creates a
FULL-access admin by default** (`permission_all = true`). To make `ai-reader`
genuinely read-only you must clear its bits after creation — either:

- **AWS web form:** AWS → Admins → ai-reader → uncheck all permissions → save; or
- **SQL:** `UPDATE admins SET permission_all=false, permission_messaging=false
  WHERE username='ai-reader';` (single quotes — it's a string literal).

Then verify: `SELECT username, permission_all, permission_messaging FROM admins;`
— `ai-reader` must show `f | f`. (`ai-uploader` correctly keeps `permission_all
= t`, so no change is needed there.) This was confirmed live against the fork in
the local demo (`cms-demo/`).
