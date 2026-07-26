#!/usr/bin/env bash
set -euo pipefail
python scripts/export_openapi.py
python scripts/generate_evidence.py
pytest -q
