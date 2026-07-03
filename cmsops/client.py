from __future__ import annotations
import io
import requests
from cmsops.config import Settings

class CmsAdminClient:
    """Drives the ioi-isr/cms AdminWebServer over HTTP.

    Auth: GET /login to obtain the _xsrf cookie, POST /login with
    username/password/_xsrf to obtain the awslogin session cookie, then reuse
    the session (xsrf_cookies=True means every POST echoes _xsrf).
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.session = requests.Session()
        self._logged_in = False

    def _url(self, path: str) -> str:
        return f"{self.settings.base_url}{path}"

    def _xsrf_token(self) -> str:
        token = self.session.cookies.get("_xsrf")
        if not token:
            raise RuntimeError("no _xsrf cookie yet; GET a page before POSTing")
        return token

    def login(self, timeout: float = 30.0) -> None:
        # 1. GET /login → sets the _xsrf cookie.
        self.session.get(self._url("/login"), timeout=timeout)
        # 2. POST /login with the double-submit token.
        resp = self.session.post(
            self._url("/login"),
            data={
                "username": self.settings.username,
                "password": self.settings.password,
                "_xsrf": self._xsrf_token(),
            },
            allow_redirects=False,
            timeout=timeout,
        )
        # LoginHandler redirects (302) to "/" on success and back to the login
        # page (with an error query) on failure.
        if resp.status_code not in (302, 303) or "awslogin" not in self.session.cookies:
            raise RuntimeError(
                f"login failed (status={resp.status_code}); check CMS_USERNAME/CMS_PASSWORD"
            )
        self._logged_in = True

    def _ensure_login(self) -> None:
        if not self._logged_in:
            self.login()

    def export_task(self, task_id: int, timeout: float = 120.0) -> bytes:
        """GET /task/{id}/export → italy_yaml zip bytes (perm AUTHENTICATED)."""
        self._ensure_login()
        resp = self.session.get(self._url(f"/task/{task_id}/export"), timeout=timeout)
        resp.raise_for_status()
        ctype = resp.headers.get("Content-Type", "")
        if "zip" not in ctype:
            raise RuntimeError(
                f"export did not return a zip (Content-Type={ctype!r}); "
                f"task {task_id} may have no active dataset"
            )
        return resp.content

    def import_task(
        self,
        zip_bytes: bytes,
        *,
        update: bool,
        contest_id: int | None = None,
        loader: str = "italy_yaml",
        no_statement: bool = False,
        timeout: float = 300.0,
    ) -> None:
        """POST /tasks/import multipart (perm PERMISSION_ALL).

        update=True replaces an existing same-named task's dataset package in
        place (keeps submissions + active-dataset pointer).
        """
        self._ensure_login()
        # Refresh a page to guarantee a current _xsrf cookie before the POST.
        self.session.get(self._url("/tasks"), timeout=timeout)
        data = {"_xsrf": self._xsrf_token(), "loader": loader}
        if update:
            data["update"] = "true"
        if no_statement:
            data["no_statement"] = "true"
        if contest_id is not None:
            data["contest_id"] = str(contest_id)
        files = {"task_file": ("task.zip", io.BytesIO(zip_bytes), "application/zip")}
        resp = self.session.post(
            self._url("/tasks/import"),
            data=data,
            files=files,
            allow_redirects=False,
            timeout=timeout,
        )
        # Handler redirects to /tasks (or the model-solutions config page) on
        # success; a 200 that re-renders the form means the import failed.
        if resp.status_code not in (302, 303):
            raise RuntimeError(
                f"import failed (status={resp.status_code}); "
                f"account may lack permission_all, or the package is invalid"
            )
