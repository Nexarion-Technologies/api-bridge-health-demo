from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any, Protocol

import httpx

from .config import Settings
from .metrics import BridgeMetrics

SENSITIVE_KEY_FRAGMENTS = ("password", "secret", "token", "api_key", "apikey", "credential", "private_key")


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if any(fragment in str(key).casefold() for fragment in SENSITIVE_KEY_FRAGMENTS):
                result[str(key)] = "[REDACTED]"
            else:
                result[str(key)] = redact(item)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return value[:4000]
    return value


class Upstream(Protocol):
    async def health(self) -> dict[str, Any]: ...
    async def fetch_records(self, query: str, limit: int, trace_id: str) -> list[dict[str, Any]]: ...


class HttpUpstream:
    def __init__(self, settings: Settings, metrics: BridgeMetrics) -> None:
        self.settings = settings
        self.metrics = metrics

    async def _get(self, path: str, *, params: dict[str, Any] | None = None, trace_id: str = "") -> Any:
        last_error: Exception | None = None
        for attempt in range(1, self.settings.upstream_retries + 1):
            started = time.perf_counter()
            try:
                async with httpx.AsyncClient(
                    base_url=self.settings.upstream_base_url,
                    timeout=self.settings.upstream_timeout_seconds,
                    follow_redirects=False,
                ) as client:
                    response = await client.get(path, params=params, headers={"X-Request-ID": trace_id})
                elapsed = time.perf_counter() - started
                self.metrics.upstream_latency.observe(elapsed)
                if len(response.content) > self.settings.upstream_max_response_bytes:
                    raise RuntimeError("upstream response exceeded configured byte limit")
                response.raise_for_status()
                self.metrics.upstream.labels(outcome="ok").inc()
                return response.json()
            except (httpx.HTTPError, ValueError, RuntimeError) as exc:
                self.metrics.upstream.labels(outcome="error").inc()
                last_error = exc
                if attempt < self.settings.upstream_retries:
                    await asyncio.sleep(0.05 * attempt)
        raise RuntimeError(f"synthetic upstream unavailable: {type(last_error).__name__}") from last_error

    async def health(self) -> dict[str, Any]:
        payload = await self._get("/healthz", trace_id="readiness")
        return redact(payload)

    async def fetch_records(self, query: str, limit: int, trace_id: str) -> list[dict[str, Any]]:
        payload = await self._get("/v1/records", params={"q": query, "limit": limit}, trace_id=trace_id)
        rows = payload.get("records", []) if isinstance(payload, dict) else []
        if not isinstance(rows, list):
            raise RuntimeError("upstream records payload is invalid")
        return [redact(row) for row in rows[:limit] if isinstance(row, dict)]


def normalize_records(records: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    normalized = []
    for record in records[:limit]:
        source_id = str(record.get("source_id", ""))[:120]
        revision = str(record.get("revision", "unknown"))[:120]
        title = str(record.get("title", "untitled"))[:300]
        content = str(record.get("content", ""))[:4000]
        if not source_id or not content:
            continue
        normalized.append({
            "source_id": source_id,
            "source_uri": f"synthetic://upstream/{source_id}",
            "source_revision": revision,
            "title": title,
            "snippet": content[:800],
            "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "classification": str(record.get("classification", "internal"))[:80],
        })
    return normalized
