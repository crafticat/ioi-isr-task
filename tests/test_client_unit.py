from cmsops.client import CmsAdminClient
from cmsops.config import Settings

def _client():
    return CmsAdminClient(Settings(base_url="https://cms.x", username="u", password="p"))

def test_export_url():
    assert _client()._url("/task/7/export") == "https://cms.x/task/7/export"

def test_xsrf_from_cookie_jar():
    c = _client()
    c.session.cookies.set("_xsrf", "TOKEN123", domain="cms.x")
    assert c._xsrf_token() == "TOKEN123"

def test_xsrf_missing_raises():
    import pytest
    c = _client()
    with pytest.raises(RuntimeError, match="_xsrf"):
        c._xsrf_token()
