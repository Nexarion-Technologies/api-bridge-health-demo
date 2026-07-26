from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from api_bridge.config import Settings
from api_bridge.main import create_app


class SyntheticUpstream:
    async def health(self):
        return {"ok": True, "service": "synthetic-evidence-upstream", "version": "1.0.0"}

    async def fetch_records(self, query: str, limit: int, trace_id: str):
        return [{
            "source_id": "src_bridge_001",
            "revision": "rev-4",
            "title": "Synthetic readiness record",
            "content": "Readiness passed for the synthetic upstream. Evidence is bounded and read-only.",
            "classification": "internal",
        }][:limit]


def main() -> int:
    app = create_app(settings=Settings(bridge_token="evidence-placeholder"), upstream=SyntheticUpstream())
    client = TestClient(app)
    headers = {"Authorization": "Bearer evidence-placeholder", "X-Request-ID": "trace-evidence-001"}
    evidence = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "healthz": client.get("/healthz").json(),
        "readyz": client.get("/readyz", headers=headers).json(),
        "version": client.get("/version").json(),
        "schema": client.get("/schema", headers=headers).json(),
        "context_summary": client.post("/v1/context/summary", headers=headers, json={"query": "readiness evidence", "limit": 3}).json(),
    }
    path = Path("evidence/generated/api-bridge-evidence.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(path)
    return 0 if evidence["readyz"]["ok"] and evidence["context_summary"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
