$ErrorActionPreference = "Stop"
python scripts/export_openapi.py
python scripts/generate_evidence.py
pytest -q
