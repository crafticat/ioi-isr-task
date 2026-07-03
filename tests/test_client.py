import pytest
from cmsops.client import CmsAdminClient

@pytest.mark.livecms
def test_login_succeeds(live_settings):
    c = CmsAdminClient(live_settings)
    c.login()
    assert c._logged_in
    assert "awslogin" in c.session.cookies

@pytest.mark.livecms
def test_login_bad_password_raises(live_settings):
    bad = live_settings.__class__(live_settings.base_url, live_settings.username, "wrong")
    c = CmsAdminClient(bad)
    with pytest.raises(RuntimeError, match="login failed"):
        c.login()

@pytest.mark.livecms
def test_export_roundtrip(live_settings):
    # Precondition: a task with id 1 exists in the dev CMS (seed via cmsImportTask).
    c = CmsAdminClient(live_settings)
    zip_bytes = c.export_task(1)
    assert zip_bytes[:2] == b"PK"          # zip magic
    # Re-import as an update (replace by name) — must not raise.
    c.import_task(zip_bytes, update=True)
