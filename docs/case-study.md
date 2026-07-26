# Case Study: Maintainable API Bridge Pattern

## Problem

Workflows become brittle when each one implements vendor authentication,
timeouts, retries, response parsing, redaction, health checks, and telemetry.

## Demonstrated approach

The bridge centralizes service-specific mechanics behind a small REST contract.
Callers receive consistent liveness, readiness, version, schema, metrics, and a
bounded context response. Source IDs, revisions, content hashes, trace IDs, and
read-only posture make the result auditable.

## Evidence

- tests cover authentication, route contracts, bounds, redaction, failures, and
  metrics;
- `docs/openapi.json` is generated from the app;
- `evidence/api-bridge-evidence.json` captures a synthetic health/readiness/
  schema/context sequence;
- Docker runs as a non-root user with a read-only filesystem, dropped
  capabilities, and `no-new-privileges` in Compose.
