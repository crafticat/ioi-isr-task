# Secrets, variables, and the deploy gate

## ⚠️ This repo is PUBLIC (testing phase)

Currently public so the deploy approval gate works on the free plan and CI is easy
to watch. That is fine **right now** because the repo holds only framework code —
no task packages, no contest data, no secrets (secrets live in GitHub Actions
secrets, never in the repo).

**Before adding any real (unpublished) task package or any contest data, make the
repo private and move the deploy gate to GitHub Pro/Team.** Leaking an unpublished
competition task is a real harm. To go private later:

    gh repo edit crafticat/ioi-isr-task --visibility private --accept-visibility-change-consequences
    # then upgrade the account to Pro/Team and re-run the required-reviewer command below.

## Repo secrets (set these — the values are yours; never paste them to the agent)

Each command prompts for the value on stdin, so it never lands in shell history:

    gh secret set CMS_BASE_URL      --repo crafticat/ioi-isr-task   # e.g. https://cms.ioi-isr.example (no trailing slash)
    gh secret set CMS_READER_USER   --repo crafticat/ioi-isr-task   # ai-reader username
    gh secret set CMS_READER_PASS   --repo crafticat/ioi-isr-task   # ai-reader password
    gh secret set CMS_UPLOADER_USER --repo crafticat/ioi-isr-task   # ai-uploader username
    gh secret set CMS_UPLOADER_PASS --repo crafticat/ioi-isr-task   # ai-uploader password

Which workflow uses which: `deploy.yml` → CMS_UPLOADER_*; `drift.yml` and
`dataset.yml` → CMS_READER_*; the `probe.yml` reachability check → CMS_BASE_URL only.

## Repo variable (not a secret)

verify.yml pins the CMS fork to a known-good commit:

    gh variable set CMS_FORK_SHA --repo crafticat/ioi-isr-task --body <ioi-isr/cms commit sha>

## The deploy gate (already enabled)

`deploy.yml` runs in the `production` environment, which has a **required reviewer**
(you, crafticat) — every deploy pauses for an explicit approval click before it
imports. This was enabled with:

    uid=$(gh api users/crafticat --jq .id)
    printf '{"wait_timer":0,"reviewers":[{"type":"User","id":%s}]}' "$uid" \
      | gh api --method PUT repos/crafticat/ioi-isr-task/environments/production --input -

Add more reviewers (multi-operator) by extending the `reviewers` array. Required
reviewers are free on public repos and on Pro/Team private repos; they are **not**
available on free private repos — which is why the repo is public during testing.
