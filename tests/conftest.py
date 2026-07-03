import os
import pytest
from cmsops.config import Settings

@pytest.fixture
def live_settings():
    url = os.environ.get("CMS_DEV_URL")
    if not url:
        pytest.skip("CMS_DEV_URL not set; run scripts/testcms_up.sh and export it")
    return Settings(
        base_url=url,
        username=os.environ.get("CMS_USERNAME", "testadmin"),
        password=os.environ.get("CMS_PASSWORD", "testpass"),
    )
