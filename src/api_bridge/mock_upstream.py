from __future__ import annotations

from fastapi import FastAPI, Query

app = FastAPI(title="Synthetic Upstream", version="1.0.0")

RECORDS = [
    {
        "source_id": "src_bridge_001",
        "revision": "rev-4",
        "title": "Synthetic readiness record",
        "content": "Readiness passed for the synthetic upstream. Evidence is bounded and read-only.",
        "classification": "internal",
        "internal_token": "not-a-real-token-and-must-be-redacted",
    },
    {
        "source_id": "src_bridge_002",
        "revision": "rev-2",
        "title": "Synthetic retry policy",
        "content": "The bridge uses bounded timeouts, limited retries, no redirects, and explicit failure evidence.",
        "classification": "internal",
    },
    {
        "source_id": "src_bridge_003",
        "revision": "rev-1",
        "title": "Synthetic observability note",
        "content": "Health, readiness, request counters, upstream counters, latency, trace IDs, and source hashes are available.",
        "classification": "internal",
    },
]


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True, "service": "synthetic-upstream", "version": "1.0.0"}


@app.get("/v1/records")
async def records(q: str = Query(min_length=1, max_length=300), limit: int = Query(default=5, ge=1, le=10)) -> dict:
    tokens = [token for token in q.casefold().split() if token]
    ranked = []
    for row in RECORDS:
        text = f"{row['title']} {row['content']}".casefold()
        score = sum(text.count(token) for token in tokens)
        if score:
            ranked.append((score, row))
    ranked.sort(key=lambda item: (-item[0], item[1]["source_id"]))
    selected = [row for _, row in ranked[:limit]]
    return {"ok": True, "records": selected, "bounded": True}
