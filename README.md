# API Bridge Health Demo

A production-shaped FastAPI bridge pattern using synthetic upstream data. It
exposes health, readiness, version, schema, Prometheus metrics, and a bounded
read-only context endpoint with authentication, retries, timeouts, trace IDs,
source provenance, response hashing, and tests.

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/healthz` | No | Process liveness only |
| GET | `/version` | No | Release and contract metadata |
| GET | `/readyz` | Bearer token | Configuration and upstream readiness |
| GET | `/schema` | Bearer token | Explicit route/read-only contract |
| POST | `/v1/context/summary` | Bearer token | Bounded synthetic upstream read |
| GET | `/metrics` | No | Prometheus-format service metrics |

## Quick start with Docker

```bash
cp .env.example .env
# Replace the local placeholder token in .env.
docker compose up --build -d

curl -sS http://localhost:8080/healthz
curl -sS -H "Authorization: Bearer $DEMO_BRIDGE_TOKEN" http://localhost:8080/readyz
curl -sS -X POST http://localhost:8080/v1/context/summary \
  -H "Authorization: Bearer $DEMO_BRIDGE_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"query":"readiness evidence","limit":3}'
```

## Local development

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -q
python scripts/export_openapi.py
python scripts/generate_evidence.py
uvicorn api_bridge.main:app --reload --port 8080
```

## Design boundaries

- The bridge accepts only a known operation and bounded query/limit fields.
- It follows no redirects and reads no arbitrary URL supplied by a caller.
- The configured upstream origin is operator-controlled.
- Responses are size-bounded, recursively redacted, marked synthetic/untrusted,
  and attributed with source IDs, revisions, hashes, and a trace ID.
- Authentication is a local demo bearer token. A production deployment should
  use managed secrets, TLS, identity-aware access, rotation, network policy, and
  source-native least privilege.

No Microsoft Graph, QuickBooks, customer, or production account is contacted.
