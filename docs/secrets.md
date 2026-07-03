# Secrets and environments

GitHub → repo Settings → Environments → "production":
  - Required reviewers: <named staff>  (this is the approval click before any deploy)
  - Secrets: CMS_BASE_URL, CMS_UPLOADER_USER, CMS_UPLOADER_PASS

`deploy.yml` is bound to this environment, so every run pauses for approval.
