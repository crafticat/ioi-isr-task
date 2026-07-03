from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    base_url: str
    username: str
    password: str

    @staticmethod
    def from_env() -> "Settings":
        def req(key: str) -> str:
            val = os.environ.get(key)
            if not val:
                raise RuntimeError(f"missing required env var: {key}")
            return val
        return Settings(
            base_url=req("CMS_BASE_URL").rstrip("/"),
            username=req("CMS_USERNAME"),
            password=req("CMS_PASSWORD"),
        )
