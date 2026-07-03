import json
import os
import tempfile
from pathlib import Path

from guardkit.knowledge.query_logger import log_query


def read_last_entry(base_dir: str) -> dict:
    log_path = Path(base_dir) / ".guardkit" / "memory-query-log.jsonl"
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert lines, "Log file should contain at least one line"
    return json.loads(lines[-1])


def test_log_query_with_items_non_empty():
    with tempfile.TemporaryDirectory() as tmp:
        items = [{"id": "chunk:guardkit:X", "score": 0.9}]
        log_query(
            operation="search",
            query="q",
            items=items,
            base_dir=tmp,
        )
        entry = read_last_entry(tmp)
        assert entry.get("items") == items
        # Ensure other required fields exist
        for key in ["timestamp", "source", "operation", "query", "group_ids", "result_count", "first_result_preview"]:
            assert key in entry


def test_log_query_with_items_empty_list():
    with tempfile.TemporaryDirectory() as tmp:
        items = []
        log_query(
            operation="search",
            query="q",
            items=items,
            base_dir=tmp,
        )
        entry = read_last_entry(tmp)
        assert "items" in entry
        assert entry["items"] == []


def test_log_query_without_items():
    with tempfile.TemporaryDirectory() as tmp:
        log_query(
            operation="search",
            query="q",
            base_dir=tmp,
        )
        entry = read_last_entry(tmp)
        assert "items" not in entry
