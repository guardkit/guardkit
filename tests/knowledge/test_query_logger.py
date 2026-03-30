"""
Tests for guardkit.knowledge.query_logger

Covers JSONL logging, log rotation, thread safety, preview extraction,
and error handling.

Coverage Target: >=85%
"""

import json
import os
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from guardkit.knowledge.query_logger import (
    _DEFAULT_LOG_FILENAME,
    _MAX_FILE_SIZE_BYTES,
    _PREVIEW_LENGTH,
    _build_entry,
    _get_log_path,
    _rotate_if_needed,
    extract_preview,
    log_query,
)


# ============================================================================
# 1. _get_log_path Tests
# ============================================================================

class TestGetLogPath:
    """Test log path resolution and directory creation."""

    def test_creates_guardkit_dir(self, tmp_path):
        """Log directory is created if it doesn't exist."""
        path = _get_log_path(base_dir=str(tmp_path))
        assert path.parent.exists()
        assert path.parent.name == ".guardkit"

    def test_returns_jsonl_filename(self, tmp_path):
        """Returns the correct log filename."""
        path = _get_log_path(base_dir=str(tmp_path))
        assert path.name == _DEFAULT_LOG_FILENAME

    def test_idempotent_directory_creation(self, tmp_path):
        """Calling twice doesn't error on existing directory."""
        _get_log_path(base_dir=str(tmp_path))
        path = _get_log_path(base_dir=str(tmp_path))
        assert path.parent.exists()


# ============================================================================
# 2. _build_entry Tests
# ============================================================================

class TestBuildEntry:
    """Test log entry construction."""

    def test_all_fields_present(self):
        """Entry contains all required fields."""
        entry = _build_entry(
            operation="search",
            query="test query",
            group_ids=["group1"],
            result_count=5,
            first_result_preview="some preview text",
            source="test",
        )
        assert "timestamp" in entry
        assert entry["operation"] == "search"
        assert entry["query"] == "test query"
        assert entry["group_ids"] == ["group1"]
        assert entry["result_count"] == 5
        assert entry["first_result_preview"] == "some preview text"
        assert entry["source"] == "test"

    def test_preview_truncated_to_50_chars(self):
        """Preview is truncated to 50 characters."""
        long_preview = "x" * 100
        entry = _build_entry(
            operation="search",
            query="q",
            group_ids=None,
            result_count=0,
            first_result_preview=long_preview,
            source="test",
        )
        assert len(entry["first_result_preview"]) == _PREVIEW_LENGTH

    def test_none_preview_stays_none(self):
        """None preview remains None."""
        entry = _build_entry(
            operation="search",
            query="q",
            group_ids=None,
            result_count=0,
            first_result_preview=None,
            source="test",
        )
        assert entry["first_result_preview"] is None

    def test_none_group_ids_becomes_empty_list(self):
        """None group_ids normalizes to empty list."""
        entry = _build_entry(
            operation="search",
            query="q",
            group_ids=None,
            result_count=0,
            first_result_preview=None,
            source="test",
        )
        assert entry["group_ids"] == []

    def test_timestamp_is_iso8601(self):
        """Timestamp is in ISO 8601 format."""
        entry = _build_entry(
            operation="search",
            query="q",
            group_ids=None,
            result_count=0,
            first_result_preview=None,
            source="test",
        )
        # Should parse without error
        from datetime import datetime
        datetime.fromisoformat(entry["timestamp"])


# ============================================================================
# 3. _rotate_if_needed Tests
# ============================================================================

class TestRotateIfNeeded:
    """Test log rotation logic."""

    def test_no_rotation_under_limit(self, tmp_path):
        """File under 1MB is not rotated."""
        log_file = tmp_path / "test.jsonl"
        log_file.write_text("small content\n")
        _rotate_if_needed(log_file)
        assert log_file.exists()
        assert not log_file.with_suffix(".jsonl.1").exists()

    def test_rotation_over_limit(self, tmp_path):
        """File over 1MB is rotated to .jsonl.1."""
        log_file = tmp_path / "test.jsonl"
        # Write just over 1MB
        log_file.write_bytes(b"x" * (_MAX_FILE_SIZE_BYTES + 1))
        _rotate_if_needed(log_file)
        assert not log_file.exists()
        assert log_file.with_suffix(".jsonl.1").exists()

    def test_rotation_overwrites_previous_backup(self, tmp_path):
        """Second rotation overwrites the .1 backup."""
        log_file = tmp_path / "test.jsonl"
        backup = log_file.with_suffix(".jsonl.1")

        # First rotation
        log_file.write_bytes(b"first" * (_MAX_FILE_SIZE_BYTES + 1))
        _rotate_if_needed(log_file)
        assert backup.exists()

        # Write new content and rotate again
        log_file.write_bytes(b"second" * (_MAX_FILE_SIZE_BYTES + 1))
        _rotate_if_needed(log_file)
        assert backup.exists()
        assert b"second" in backup.read_bytes()

    def test_rotation_handles_missing_file(self, tmp_path):
        """Rotation is a no-op for nonexistent file."""
        log_file = tmp_path / "nonexistent.jsonl"
        _rotate_if_needed(log_file)  # Should not raise


# ============================================================================
# 4. log_query Tests
# ============================================================================

class TestLogQuery:
    """Test the main log_query function."""

    def test_appends_jsonl_line(self, tmp_path):
        """Each call appends exactly one JSONL line."""
        log_query(
            operation="search",
            query="test query",
            group_ids=["g1"],
            result_count=3,
            first_result_preview="preview",
            source="test",
            base_dir=str(tmp_path),
        )
        log_path = tmp_path / ".guardkit" / _DEFAULT_LOG_FILENAME
        assert log_path.exists()
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["operation"] == "search"
        assert entry["result_count"] == 3

    def test_multiple_appends(self, tmp_path):
        """Multiple calls append multiple lines."""
        for i in range(5):
            log_query(
                operation="search",
                query=f"query {i}",
                result_count=i,
                source="test",
                base_dir=str(tmp_path),
            )
        log_path = tmp_path / ".guardkit" / _DEFAULT_LOG_FILENAME
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 5

    def test_add_episode_operation(self, tmp_path):
        """Logs add_episode operations."""
        log_query(
            operation="add_episode",
            query="Episode Name",
            group_ids=["decisions"],
            result_count=1,
            first_result_preview="Episode content here...",
            source="graphiti_client",
            base_dir=str(tmp_path),
        )
        log_path = tmp_path / ".guardkit" / _DEFAULT_LOG_FILENAME
        entry = json.loads(log_path.read_text().strip())
        assert entry["operation"] == "add_episode"
        assert entry["query"] == "Episode Name"

    def test_triggers_rotation(self, tmp_path):
        """Log rotation occurs when file exceeds 1MB."""
        log_dir = tmp_path / ".guardkit"
        log_dir.mkdir(parents=True)
        log_path = log_dir / _DEFAULT_LOG_FILENAME
        # Pre-fill with data just over 1MB
        log_path.write_bytes(b"x" * (_MAX_FILE_SIZE_BYTES + 1))

        log_query(
            operation="search",
            query="post-rotation query",
            result_count=0,
            source="test",
            base_dir=str(tmp_path),
        )
        # Old file should have been rotated
        backup = log_path.with_suffix(".jsonl.1")
        assert backup.exists()
        # New file should have the latest entry
        assert log_path.exists()
        entry = json.loads(log_path.read_text().strip())
        assert entry["query"] == "post-rotation query"

    def test_never_raises(self, tmp_path):
        """log_query never raises, even on write failure."""
        with patch("guardkit.knowledge.query_logger._get_log_path", side_effect=OSError("disk full")):
            # Should not raise
            log_query(
                operation="search",
                query="test",
                result_count=0,
                source="test",
                base_dir=str(tmp_path),
            )

    def test_default_source(self, tmp_path):
        """Default source is 'graphiti_client'."""
        log_query(
            operation="search",
            query="test",
            result_count=0,
            base_dir=str(tmp_path),
        )
        log_path = tmp_path / ".guardkit" / _DEFAULT_LOG_FILENAME
        entry = json.loads(log_path.read_text().strip())
        assert entry["source"] == "graphiti_client"


# ============================================================================
# 5. extract_preview Tests
# ============================================================================

class TestExtractPreview:
    """Test preview extraction from search results."""

    def test_empty_results(self):
        """Empty results return None."""
        assert extract_preview([]) is None

    def test_extracts_fact_field(self):
        """Extracts from 'fact' field."""
        results = [{"fact": "JWT auth is the recommended approach"}]
        preview = extract_preview(results)
        assert preview == "JWT auth is the recommended approach"

    def test_extracts_name_field(self):
        """Falls back to 'name' if no 'fact'."""
        results = [{"name": "Authentication Decision"}]
        preview = extract_preview(results)
        assert preview == "Authentication Decision"

    def test_extracts_content_field(self):
        """Falls back to 'content' if no 'fact' or 'name'."""
        results = [{"content": "Some content here"}]
        preview = extract_preview(results)
        assert preview == "Some content here"

    def test_truncates_long_preview(self):
        """Preview is truncated to 50 characters."""
        long_fact = "a" * 100
        results = [{"fact": long_fact}]
        preview = extract_preview(results)
        assert len(preview) == _PREVIEW_LENGTH

    def test_skips_empty_string_fields(self):
        """Skips empty string fields."""
        results = [{"fact": "", "name": "Valid Name"}]
        preview = extract_preview(results)
        assert preview == "Valid Name"

    def test_no_recognized_fields(self):
        """Returns None if no recognized fields found."""
        results = [{"uuid": "123", "score": 0.9}]
        assert extract_preview(results) is None


# ============================================================================
# 6. Thread Safety Tests
# ============================================================================

class TestThreadSafety:
    """Test concurrent log_query calls."""

    def test_concurrent_writes(self, tmp_path):
        """Multiple threads can write without corruption."""
        num_threads = 10
        writes_per_thread = 20
        barrier = threading.Barrier(num_threads)

        def writer(thread_id):
            barrier.wait()
            for i in range(writes_per_thread):
                log_query(
                    operation="search",
                    query=f"thread-{thread_id}-query-{i}",
                    result_count=i,
                    source=f"thread-{thread_id}",
                    base_dir=str(tmp_path),
                )

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        log_path = tmp_path / ".guardkit" / _DEFAULT_LOG_FILENAME
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == num_threads * writes_per_thread

        # Verify each line is valid JSON
        for line in lines:
            entry = json.loads(line)
            assert "timestamp" in entry
            assert "query" in entry
