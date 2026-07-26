from __future__ import annotations

from fastapi.testclient import TestClient

from api_bridge.config import Settings
from api_bridge.main import create_app


class FakeUpstream:
    async def health(self):
        return {"ok": True, "service": "fake-upstream"}

    async def fetch_records(self, query: str, limit: int, trace_id: str):
        return [{
            "source_id": "src_test_001",
            "revision": "rev-1",
            "title": "Test readiness evidence",
            "content": "Synthetic readiness evidence for unit testing.",
            "classification": "internal",
            "api_token": "must-be-redacted",
        }][:limit]


class FailingUpstream:
    async def health(self):
        raise RuntimeError("synthetic timeout")

    async def fetch_records(self, query: str, limit: int, trace_id: str):
        raise RuntimeError("synthetic timeout")


def client(upstream=None):
    settings = Settings(bridge_token="unit-test-token", upstream_base_url="http://synthetic.invalid")
    return TestClient(create_app(settings=settings, upstream=upstream or FakeUpstream()))


def auth():
    return {"Authorization": "Bearer unit-test-token"}


def test_health_is_public_and_minimal():
    response = client().get("/healthz")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert "token" not in response.text.casefold()


def test_protected_route_rejects_missing_token():
    response = client().get("/readyz")
    assert response.status_code == 401


def test_readiness_and_schema_are_explicit():
    c = client()
    ready = c.get("/readyz", headers=auth())
    assert ready.status_code == 200
    assert ready.json()["read_only"] is True
    schema = c.get("/schema", headers=auth()).json()
    assert schema["contract"] == "synthetic-readonly-bridge-v1"
    assert all(route["method"] in {"GET", "POST"} for route in schema["routes"])
    assert any(route.get("read_oriented") is True for route in schema["routes"])


def test_context_is_bounded_source_attributed_and_redacted():
    response = client().post(
        "/v1/context/summary",
        headers={**auth(), "X-Request-ID": "trace-test-001"},
        json={"query": "readiness", "limit": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["trace_id"] == "trace-test-001"
    assert body["bounded"] is True
    assert body["read_only"] is True
    assert body["row_count"] == 1
    source = body["sources"][0]
    assert source["source_id"] == "src_test_001"
    assert len(source["content_hash"]) == 64
    assert "must-be-redacted" not in response.text


def test_request_bounds_fail_before_upstream():
    response = client().post("/v1/context/summary", headers=auth(), json={"query": "x" * 301, "limit": 11})
    assert response.status_code == 422


def test_upstream_failure_is_explicit_and_safe():
    c = client(FailingUpstream())
    ready = c.get("/readyz", headers=auth())
    assert ready.status_code == 503
    result = c.post("/v1/context/summary", headers=auth(), json={"query": "readiness", "limit": 1})
    assert result.status_code == 503
    assert result.json()["read_only"] is True
    assert "synthetic timeout" in result.json()["error"]


def test_metrics_are_exposed():
    c = client()
    c.get("/healthz")
    metrics = c.get("/metrics")
    assert metrics.status_code == 200
    assert "demo_bridge_requests_total" in metrics.text
