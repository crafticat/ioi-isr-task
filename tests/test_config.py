import pytest
from cmsops.config import Settings

def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("CMS_BASE_URL", "https://cms.example/")
    monkeypatch.setenv("CMS_USERNAME", "ai-reader")
    monkeypatch.setenv("CMS_PASSWORD", "secret")
    s = Settings.from_env()
    assert s.base_url == "https://cms.example"   # trailing slash stripped
    assert s.username == "ai-reader"
    assert s.password == "secret"

def test_settings_missing_raises(monkeypatch):
    monkeypatch.delenv("CMS_BASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="CMS_BASE_URL"):
        Settings.from_env()
