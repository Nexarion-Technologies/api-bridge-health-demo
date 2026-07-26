from api_bridge.service import normalize_records, redact


def test_recursive_redaction():
    value = {"safe": 1, "password": "x", "nested": {"api_key": "y"}}
    result = redact(value)
    assert result["safe"] == 1
    assert result["password"] == "[REDACTED]"
    assert result["nested"]["api_key"] == "[REDACTED]"


def test_normalization_drops_incomplete_rows_and_bounds_content():
    rows = [
        {"source_id": "src-1", "revision": "r1", "title": "Title", "content": "x" * 5000},
        {"source_id": "", "content": "ignored"},
    ]
    result = normalize_records(rows, 10)
    assert len(result) == 1
    assert len(result[0]["snippet"]) == 800
    assert len(result[0]["content_hash"]) == 64
