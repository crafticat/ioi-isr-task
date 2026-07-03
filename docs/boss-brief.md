# Why the AI cannot damage the CMS — one page

**The AI has no CMS credentials and no CMS network path.** It only pushes git
branches to the tasks repo and reads CI output. Everything that touches the CMS
is one of four small, reviewed, version-controlled GitHub workflows using two
scoped service accounts stored as Actions secrets — never visible to the model.

1. **No write path in the agent.** Claude cannot SSH, run SQL, or call the CMS.
2. **Reads are read-only by the CMS's own permission model.** `ai-reader` has no
   permission bits → HTTP 403 on every mutating admin handler.
3. **Every deploy needs a human click.** deploy.yml is bound to the `production`
   environment with required reviewers; it cannot run until a named person
   approves. It snapshots the previous package first (one-command rollback) and
   refuses running contests by default.
4. **Prompt injection is contained.** Malicious student text can at most make the
   agent push a bad branch or *request* a deploy — which still needs CI green +
   the human approval. No silent write path exists.
5. **Nothing new runs on your server.** All server-side changes are ordinary
   reviewed PRs to ioi-isr/cms.

## Live demo (5 minutes)
1. Log into AWS as `ai-reader`; try to edit a task → **403, denied by CMS**.
2. Trigger deploy.yml → it **pauses for approval**; show the reviewer prompt.
3. Approve; show the snapshot committed to `snapshots/`; then redeploy the
   snapshot to demonstrate one-command rollback.
4. Show a `drift` PR: a hand-edit on the server surfaced automatically as a diff.
