from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _secret(name: str) -> str:
    file_value = os.getenv(f"{name}_FILE", "").strip()
    if file_value:
        return Path(file_value).read_text(encoding="utf-8").strip()
    return os.getenv(name, "").strip()


@dataclass(frozen=True)
class Settings:
    service_name: str = "api-bridge-health-demo"
    version: str = "1.0.0"
    release_id: str = "public-demo-v1.0.0"
    git_commit: str = "unknown"
    bridge_token: str = ""
    upstream_base_url: str = "http://127.0.0.1:8081"
    upstream_timeout_seconds: float = 2.0
    upstream_max_response_bytes: int = 65_536
    upstream_retries: int = 2

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            version=os.getenv("SERVICE_VERSION", "1.0.0"),
            release_id=os.getenv("RELEASE_ID", "public-demo-v1.0.0"),
            git_commit=os.getenv("GIT_COMMIT", "unknown"),
            bridge_token=_secret("DEMO_BRIDGE_TOKEN"),
            upstream_base_url=os.getenv("UPSTREAM_BASE_URL", "http://127.0.0.1:8081").rstrip("/"),
            upstream_timeout_seconds=max(0.1, min(float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "2.0")), 10.0)),
            upstream_max_response_bytes=max(1024, min(int(os.getenv("UPSTREAM_MAX_RESPONSE_BYTES", "65536")), 1_048_576)),
            upstream_retries=max(1, min(int(os.getenv("UPSTREAM_RETRIES", "2")), 3)),
        )
