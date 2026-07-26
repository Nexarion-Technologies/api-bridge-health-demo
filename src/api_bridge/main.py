from __future__ import annotations

import hmac
import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from .config import Settings
from .metrics import BridgeMetrics
from .service import HttpUpstream, Upstream, normalize_records


class ContextRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    limit: int = Field(default=5, ge=1, le=10)


def create_app(
    *,
    settings: Settings | None = None,
    upstream: Upstream | None = None,
    metrics: BridgeMetrics | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    metrics = metrics or BridgeMetrics()
    upstream = upstream or HttpUpstream(settings, metrics)
    app = FastAPI(title="API Bridge Health Demo", version=settings.version)
    app.state.settings = settings
    app.state.metrics = metrics
    app.state.upstream = upstream

    async def require_token(authorization: Annotated[str | None, Header()] = None) -> None:
        if not settings.bridge_token:
            raise HTTPException(status_code=503, detail="bridge authentication is not configured")
        supplied = ""
        if authorization and authorization.casefold().startswith("bearer "):
            supplied = authorization[7:].strip()
        if not supplied or not hmac.compare_digest(supplied, settings.bridge_token):
            raise HTTPException(status_code=401, detail="invalid bridge token")

    @app.get("/healthz")
    async def healthz() -> dict:
        metrics.requests.labels(route="healthz", outcome="ok").inc()
        return {"ok": True, "service": settings.service_name, "version": settings.version}

    @app.get("/version")
    async def version() -> dict:
        metrics.requests.labels(route="version", outcome="ok").inc()
        return {
            "ok": True,
            "service": settings.service_name,
            "version": settings.version,
            "release_id": settings.release_id,
            "git_commit": settings.git_commit,
            "contract": "synthetic-readonly-bridge-v1",
        }

    @app.get("/readyz", dependencies=[Depends(require_token)])
    async def readyz() -> Response:
        try:
            upstream_health = await upstream.health()
            ready = upstream_health.get("ok") is True
            payload = {
                "ok": ready,
                "service": settings.service_name,
                "token_configured": bool(settings.bridge_token),
                "upstream": upstream_health,
                "read_only": True,
            }
            metrics.requests.labels(route="readyz", outcome="ok" if ready else "error").inc()
            return JSONResponse(payload, status_code=200 if ready else 503)
        except RuntimeError as exc:
            metrics.requests.labels(route="readyz", outcome="error").inc()
            return JSONResponse({
                "ok": False,
                "service": settings.service_name,
                "token_configured": bool(settings.bridge_token),
                "upstream": {"ok": False, "error": str(exc)[:300]},
                "read_only": True,
            }, status_code=503)

    @app.get("/schema", dependencies=[Depends(require_token)])
    async def schema() -> dict:
        metrics.requests.labels(route="schema", outcome="ok").inc()
        return {
            "ok": True,
            "contract": "synthetic-readonly-bridge-v1",
            "read_only": True,
            "routes": [
                {"method": "GET", "path": "/healthz", "protected": False},
                {"method": "GET", "path": "/version", "protected": False},
                {"method": "GET", "path": "/readyz", "protected": True},
                {"method": "GET", "path": "/schema", "protected": True},
                {"method": "POST", "path": "/v1/context/summary", "protected": True, "read_oriented": True},
                {"method": "GET", "path": "/metrics", "protected": False},
            ],
            "bounds": {"query_chars": 300, "limit": 10, "response_bytes": settings.upstream_max_response_bytes},
        }

    @app.post("/v1/context/summary", dependencies=[Depends(require_token)])
    async def context_summary(body: ContextRequest, request: Request, x_request_id: Annotated[str | None, Header()] = None) -> Response:
        trace_id = str(x_request_id or uuid.uuid4())[:160]
        try:
            records = await upstream.fetch_records(body.query, body.limit, trace_id)
            sources = normalize_records(records, body.limit)
            payload = {
                "ok": True,
                "trace_id": trace_id,
                "service": settings.service_name,
                "query": body.query,
                "bounded": True,
                "row_count": len(sources),
                "sources": sources,
                "read_only": True,
                "synthetic": True,
                "untrusted_upstream_output": True,
            }
            metrics.requests.labels(route="context_summary", outcome="ok").inc()
            return JSONResponse(payload, status_code=200)
        except RuntimeError as exc:
            metrics.requests.labels(route="context_summary", outcome="error").inc()
            return JSONResponse({
                "ok": False,
                "trace_id": trace_id,
                "service": settings.service_name,
                "error": str(exc)[:300],
                "read_only": True,
                "synthetic": True,
            }, status_code=503)

    @app.get("/metrics", include_in_schema=False)
    async def prometheus_metrics() -> Response:
        return Response(content=metrics.render(), media_type="text/plain; version=0.0.4")

    return app


app = create_app()
