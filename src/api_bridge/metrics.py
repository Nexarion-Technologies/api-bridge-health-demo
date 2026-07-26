from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest


class BridgeMetrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "demo_bridge_requests_total",
            "Bridge requests by route and outcome.",
            ("route", "outcome"),
            registry=self.registry,
        )
        self.upstream = Counter(
            "demo_bridge_upstream_requests_total",
            "Synthetic upstream requests by outcome.",
            ("outcome",),
            registry=self.registry,
        )
        self.upstream_latency = Histogram(
            "demo_bridge_upstream_latency_seconds",
            "Synthetic upstream request latency.",
            registry=self.registry,
        )

    def render(self) -> bytes:
        return generate_latest(self.registry)
