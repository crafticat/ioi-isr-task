import http.client
import io

import pytest
import requests
import requests_mock
from urllib3.response import HTTPResponse

from cmsops.client import CmsAdminClient, NoActiveDatasetError
from cmsops.config import Settings

def _client():
    return CmsAdminClient(Settings(base_url="https://cms.x", username="u", password="p"))

# --- cookie-carrying mock responses -----------------------------------------
# requests_mock's fake raw response always sets raw._original_response = None
# (see its own response.py: cookies are "extracted ... manually" onto
# response.cookies instead, because "we don't create" a real original_response).
# But CmsAdminClient.login()/import_task() rely on requests' *session*-level
# cookie-jar auto-extraction (extract_cookies_to_jar reading
# raw._original_response.msg) — the same mechanism a real server round-trip
# uses, and the one the (skipped-without-a-live-CMS) livecms tests exercise
# for real. A plain `headers={"Set-Cookie": ...}` mock never reaches
# session.cookies, so login()/import_task() would see no _xsrf/awslogin cookie
# no matter what client.py does. _raw() below builds a real
# original_response.msg so the mocked HTTP layer round-trips cookies exactly
# like live CMS does, which is the whole point of an HTTP-layer test.

class _OriginalResponse:
    """Minimal stand-in for the httplib.HTTPResponse requests' cookie-jar
    extraction expects at raw._original_response (needs .msg and .isclosed())."""
    def __init__(self, msg):
        self.msg = msg
    def isclosed(self):
        return True

def _raw(status_code, headers):
    msg = http.client.HTTPMessage()
    for k, v in headers.items():
        msg[k] = v
    return HTTPResponse(status=status_code, headers=headers, body=io.BytesIO(b""),
                        preload_content=False, original_response=_OriginalResponse(msg))

# -----------------------------------------------------------------------------

def test_login_success_sets_awslogin():
    c = _client()
    with requests_mock.Mocker() as m:
        m.get("https://cms.x/login", raw=_raw(200, {"Set-Cookie": "_xsrf=TOK; Path=/"}))
        m.post("https://cms.x/login", raw=_raw(302, {"Set-Cookie": "awslogin=SESSION; Path=/",
                                                       "Location": "/"}))
        c.login()
    assert c._logged_in and "awslogin" in c.session.cookies

def test_login_failure_raises():
    c = _client()
    with requests_mock.Mocker() as m:
        m.get("https://cms.x/login", raw=_raw(200, {"Set-Cookie": "_xsrf=TOK; Path=/"}))
        m.post("https://cms.x/login", status_code=200)   # re-renders form = failure
        with pytest.raises(RuntimeError, match="login failed"):
            c.login()

def test_export_returns_zip():
    c = _client(); c._logged_in = True
    with requests_mock.Mocker() as m:
        m.get("https://cms.x/task/1/export", content=b"PK\x03\x04zip",
              headers={"Content-Type": "application/zip"})
        assert c.export_task(1) == b"PK\x03\x04zip"

def test_export_redirect_is_no_active_dataset():
    c = _client(); c._logged_in = True
    with requests_mock.Mocker() as m:
        m.get("https://cms.x/task/1/export", status_code=302, headers={"Location": "/tasks"})
        with pytest.raises(NoActiveDatasetError):
            c.export_task(1)

def test_export_404_raises_httperror():
    c = _client(); c._logged_in = True
    with requests_mock.Mocker() as m:
        m.get("https://cms.x/task/9/export", status_code=404)
        with pytest.raises(requests.HTTPError):
            c.export_task(9)

def test_export_non_zip_200_fails_loud():
    c = _client(); c._logged_in = True
    with requests_mock.Mocker() as m:
        m.get("https://cms.x/task/1/export", text="<html>error</html>",
              headers={"Content-Type": "text/html"})
        with pytest.raises(RuntimeError, match="non-zip"):
            c.export_task(1)

def test_import_success_on_redirect():
    c = _client(); c._logged_in = True
    with requests_mock.Mocker() as m:
        m.get("https://cms.x/tasks", raw=_raw(200, {"Set-Cookie": "_xsrf=TOK; Path=/"}))
        m.post("https://cms.x/tasks/import", status_code=302, headers={"Location": "/tasks"})
        c.import_task(b"PKzip", update=True)   # must not raise

def test_import_failure_on_200():
    c = _client(); c._logged_in = True
    with requests_mock.Mocker() as m:
        m.get("https://cms.x/tasks", raw=_raw(200, {"Set-Cookie": "_xsrf=TOK; Path=/"}))
        m.post("https://cms.x/tasks/import", status_code=200)   # re-renders form = failure
        with pytest.raises(RuntimeError, match="import failed"):
            c.import_task(b"PKzip", update=True)
