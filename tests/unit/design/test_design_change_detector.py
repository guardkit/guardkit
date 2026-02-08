"""
Unit tests for design change detection.

Tests cover:
    - Extraction hash computation and comparison
    - Cache TTL validation
    - Design change detection logic
    - State-aware handling for different task states
    - Cache invalidation on design URL change
    - Edge cases and error handling

Coverage Target: >=85%
Test Count: 25+ tests
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
import hashlib


# ============================================================================
# 1. Extraction Hash Tests (5 tests)
# ============================================================================


class TestExtractionHash:
    """Test suite for extraction hash computation."""

    def test_compute_hash_from_design_data(self):
        """Test computing SHA-256 hash from design data."""
        from guardkit.design.change_detector import compute_extraction_hash

        design_data = {"elements": [{"name": "Button"}], "tokens": {"primary": "#000"}}
        hash_result = compute_extraction_hash(design_data)

        # Should return 16-character hex hash
        assert len(hash_result) == 16
        assert all(c in "0123456789abcdef" for c in hash_result)

    def test_same_data_produces_same_hash(self):
        """Test that identical design data produces identical hash."""
        from guardkit.design.change_detector import compute_extraction_hash

        design_data = {"elements": [{"name": "Button"}], "tokens": {"primary": "#000"}}
        hash1 = compute_extraction_hash(design_data)
        hash2 = compute_extraction_hash(design_data)

        assert hash1 == hash2

    def test_different_data_produces_different_hash(self):
        """Test that different design data produces different hash."""
        from guardkit.design.change_detector import compute_extraction_hash

        data1 = {"elements": [{"name": "Button"}]}
        data2 = {"elements": [{"name": "Input"}]}

        hash1 = compute_extraction_hash(data1)
        hash2 = compute_extraction_hash(data2)

        assert hash1 != hash2

    def test_hash_handles_nested_structures(self):
        """Test hash computation with deeply nested structures."""
        from guardkit.design.change_detector import compute_extraction_hash

        complex_data = {
            "elements": [
                {
                    "name": "Button",
                    "children": [
                        {"name": "Icon", "props": ["color", "size"]},
                        {"name": "Text"}
                    ]
                }
            ],
            "tokens": {"colors": {"primary": "#000", "secondary": "#fff"}}
        }

        hash_result = compute_extraction_hash(complex_data)
        assert len(hash_result) == 16

    def test_hash_is_deterministic_across_runs(self):
        """Test that hash is consistent across multiple runs."""
        from guardkit.design.change_detector import compute_extraction_hash

        design_data = {"elements": [{"name": "Button"}], "tokens": {"primary": "#000"}}
        hashes = [compute_extraction_hash(design_data) for _ in range(5)]

        # All hashes should be identical
        assert len(set(hashes)) == 1


# ============================================================================
# 2. Cache TTL Tests (5 tests)
# ============================================================================


class TestCacheTTL:
    """Test suite for cache time-to-live validation."""

    def test_is_cache_expired_within_ttl(self):
        """Test cache not expired when within TTL window."""
        from guardkit.design.change_detector import is_cache_expired

        # Extracted 30 minutes ago, TTL is 1 hour
        extracted_at = (datetime.now() - timedelta(minutes=30)).isoformat()
        ttl_seconds = 3600

        assert is_cache_expired(extracted_at, ttl_seconds) is False

    def test_is_cache_expired_beyond_ttl(self):
        """Test cache expired when beyond TTL window."""
        from guardkit.design.change_detector import is_cache_expired

        # Extracted 2 hours ago, TTL is 1 hour
        extracted_at = (datetime.now() - timedelta(hours=2)).isoformat()
        ttl_seconds = 3600

        assert is_cache_expired(extracted_at, ttl_seconds) is True

    def test_is_cache_expired_exactly_at_ttl(self):
        """Test cache expired when exactly at TTL boundary."""
        from guardkit.design.change_detector import is_cache_expired

        # Extracted exactly 1 hour ago
        extracted_at = (datetime.now() - timedelta(seconds=3600)).isoformat()
        ttl_seconds = 3600

        # At boundary, should be expired
        assert is_cache_expired(extracted_at, ttl_seconds) is True

    def test_is_cache_expired_with_invalid_timestamp(self):
        """Test handling of invalid timestamp format."""
        from guardkit.design.change_detector import is_cache_expired

        with pytest.raises(ValueError):
            is_cache_expired("invalid-timestamp", 3600)

    def test_is_cache_expired_with_custom_ttl(self):
        """Test cache expiration with custom TTL values."""
        from guardkit.design.change_detector import is_cache_expired

        # Extracted 10 minutes ago, custom TTL of 5 minutes
        extracted_at = (datetime.now() - timedelta(minutes=10)).isoformat()
        ttl_seconds = 300  # 5 minutes

        assert is_cache_expired(extracted_at, ttl_seconds) is True


# ============================================================================
# 3. Design Change Detection Tests (6 tests)
# ============================================================================


class TestDesignChangeDetection:
    """Test suite for design change detection logic."""

    def test_detect_no_change_same_hash(self):
        """Test no change detected when hashes match."""
        from guardkit.design.change_detector import has_design_changed

        old_hash = "a3f2b5c1d8e9f0a1"
        new_hash = "a3f2b5c1d8e9f0a1"

        assert has_design_changed(old_hash, new_hash) is False

    def test_detect_change_different_hash(self):
        """Test change detected when hashes differ."""
        from guardkit.design.change_detector import has_design_changed

        old_hash = "a3f2b5c1d8e9f0a1"
        new_hash = "b4e3c6d2a9f1e0b2"

        assert has_design_changed(old_hash, new_hash) is True

    def test_check_design_freshness_fresh_cache(self):
        """Test design freshness check with fresh cache."""
        from guardkit.design.change_detector import check_design_freshness

        metadata = {
            "extracted_at": (datetime.now() - timedelta(minutes=30)).isoformat(),
            "extraction_hash": "a3f2b5c1d8e9f0a1"
        }
        ttl_seconds = 3600

        result = check_design_freshness(metadata, ttl_seconds)

        assert result["is_fresh"] is True
        assert result["needs_refresh"] is False

    def test_check_design_freshness_expired_cache(self):
        """Test design freshness check with expired cache."""
        from guardkit.design.change_detector import check_design_freshness

        metadata = {
            "extracted_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "extraction_hash": "a3f2b5c1d8e9f0a1"
        }
        ttl_seconds = 3600

        result = check_design_freshness(metadata, ttl_seconds)

        assert result["is_fresh"] is False
        assert result["needs_refresh"] is True

    def test_check_design_freshness_missing_metadata(self):
        """Test design freshness check with missing metadata."""
        from guardkit.design.change_detector import check_design_freshness

        metadata = {}
        ttl_seconds = 3600

        result = check_design_freshness(metadata, ttl_seconds)

        assert result["is_fresh"] is False
        assert result["needs_refresh"] is True

    def test_detect_design_change_with_mcp_requery(self):
        """Test full design change detection flow with MCP requery."""
        from guardkit.design.change_detector import detect_design_change

        old_metadata = {
            "extracted_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "extraction_hash": "a3f2b5c1d8e9f0a1",
            "design_url": "figma://file/abc123/node/2:2"
        }

        # Mock MCP extraction returning new design data
        mock_extractor = Mock()
        new_design_data = {"elements": [{"name": "NewButton"}]}
        mock_extractor.extract_from_url.return_value = new_design_data

        result = detect_design_change(old_metadata, mock_extractor, ttl_seconds=3600)

        assert result["changed"] is True
        assert result["old_hash"] == "a3f2b5c1d8e9f0a1"
        assert result["new_hash"] != "a3f2b5c1d8e9f0a1"


# ============================================================================
# 4. State-Aware Handling Tests (5 tests)
# ============================================================================


class TestStateAwareHandling:
    """Test suite for state-aware design change handling."""

    def test_handle_backlog_state_silent_refresh(self):
        """Test BACKLOG state: silent cache refresh."""
        from guardkit.design.state_handlers import handle_design_change

        task_state = "BACKLOG"
        change_info = {"changed": True, "old_hash": "abc", "new_hash": "def"}

        result = handle_design_change(task_state, change_info)

        assert result["action"] == "silent_refresh"
        assert result["notify_user"] is False
        assert "message" in result

    def test_handle_in_progress_state_pause_and_notify(self):
        """Test IN_PROGRESS state: pause and notify user."""
        from guardkit.design.state_handlers import handle_design_change

        task_state = "IN_PROGRESS"
        change_info = {"changed": True, "old_hash": "abc", "new_hash": "def"}

        result = handle_design_change(task_state, change_info)

        assert result["action"] == "pause_and_notify"
        assert result["notify_user"] is True
        assert "continue" in result["options"]
        assert "restart" in result["options"]

    def test_handle_in_review_state_flag_in_notes(self):
        """Test IN_REVIEW state: flag design change in review notes."""
        from guardkit.design.state_handlers import handle_design_change

        task_state = "IN_REVIEW"
        change_info = {"changed": True, "old_hash": "abc", "new_hash": "def"}

        result = handle_design_change(task_state, change_info)

        assert result["action"] == "flag_in_review"
        assert result["notify_reviewer"] is True
        assert "review_note" in result

    def test_handle_completed_state_require_new_task(self):
        """Test COMPLETED state: require new task."""
        from guardkit.design.state_handlers import handle_design_change

        task_state = "COMPLETED"
        change_info = {"changed": True, "old_hash": "abc", "new_hash": "def"}

        result = handle_design_change(task_state, change_info)

        assert result["action"] == "require_new_task"
        assert result["notify_user"] is True
        assert "no automatic re-processing" in result["message"].lower()

    def test_handle_no_change_all_states(self):
        """Test no-change scenario across all states."""
        from guardkit.design.state_handlers import handle_design_change

        change_info = {"changed": False, "old_hash": "abc", "new_hash": "abc"}

        for state in ["BACKLOG", "IN_PROGRESS", "IN_REVIEW", "COMPLETED"]:
            result = handle_design_change(state, change_info)
            assert result["action"] == "no_action"
            assert result["notify_user"] is False


# ============================================================================
# 5. Cache Management Tests (4 tests)
# ============================================================================


class TestCacheManagement:
    """Test suite for cache management operations."""

    def test_get_cache_path_for_design_url(self):
        """Test cache path generation from design URL."""
        from guardkit.design.cache_manager import get_cache_path

        design_url = "figma://file/abc123/node/2:2"
        cache_dir = Path("/tmp/.guardkit/cache/design")

        cache_path = get_cache_path(design_url, cache_dir)

        assert cache_path.parent == cache_dir
        assert cache_path.suffix == ".json"
        # Path should be deterministic hash of URL
        expected_hash = hashlib.sha256(design_url.encode()).hexdigest()[:16]
        assert expected_hash in str(cache_path)

    def test_invalidate_cache_on_url_change(self, tmp_path):
        """Test cache invalidation when design URL changes."""
        from guardkit.design.cache_manager import invalidate_cache, get_cache_path

        old_url = "figma://file/abc123/node/2:2"
        cache_dir = tmp_path / ".guardkit" / "cache" / "design"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Create a cache file first
        cache_file = get_cache_path(old_url, cache_dir)
        cache_file.write_text('{"cached_at": "2024-01-01T00:00:00"}')

        # Should remove old cache entry
        result = invalidate_cache(old_url, cache_dir)

        assert result["invalidated"] is True
        assert result["reason"] == "design_url_changed"
        assert not cache_file.exists()

    def test_clean_expired_cache_entries(self):
        """Test cleanup of expired cache entries."""
        from guardkit.design.cache_manager import clean_expired_caches

        cache_dir = Path("/tmp/.guardkit/cache/design")
        ttl_seconds = 3600

        # Should return count of cleaned entries
        result = clean_expired_caches(cache_dir, ttl_seconds)

        assert "cleaned_count" in result
        assert isinstance(result["cleaned_count"], int)

    def test_cache_directory_creation(self):
        """Test automatic cache directory creation."""
        from guardkit.design.cache_manager import ensure_cache_dir

        cache_dir = Path("/tmp/.guardkit/cache/design/test_subdir")

        # Should create directory if it doesn't exist
        ensure_cache_dir(cache_dir)

        assert cache_dir.exists()
        assert cache_dir.is_dir()


# ============================================================================
# 6. Integration with AutoBuild Tests (3 tests)
# ============================================================================


class TestAutoBuildIntegration:
    """Test suite for integration with autobuild.py."""

    def test_check_design_before_phase_0(self):
        """Test design freshness check before Phase 0 execution."""
        from guardkit.design.change_detector import check_design_before_phase_0

        task_metadata = {
            "design_extraction": {
                "extracted_at": (datetime.now() - timedelta(hours=2)).isoformat(),
                "extraction_hash": "a3f2b5c1d8e9f0a1",
                "design_url": "figma://file/abc123/node/2:2"
            },
            "status": "IN_PROGRESS"
        }

        mock_extractor = Mock()
        mock_extractor.extract_from_url.return_value = {
            "elements": [{"name": "Button"}]
        }

        result = check_design_before_phase_0(task_metadata, mock_extractor)

        assert "action" in result
        assert "changed" in result
        assert "fresh_metadata" in result

    def test_silent_update_timestamp_no_change(self):
        """Test silent timestamp update when design unchanged."""
        from guardkit.design.change_detector import update_extraction_metadata

        task_file = Path("/tmp/test_task.md")
        old_hash = "a3f2b5c1d8e9f0a1"
        new_hash = "a3f2b5c1d8e9f0a1"  # Same hash

        result = update_extraction_metadata(task_file, old_hash, new_hash)

        assert result["updated"] is True
        assert result["timestamp_updated"] is True
        assert result["hash_changed"] is False

    def test_apply_state_policy_on_change(self):
        """Test state-aware policy application on design change."""
        from guardkit.design.change_detector import apply_state_policy

        task_state = "IN_PROGRESS"
        design_changed = True
        change_info = {"old_hash": "abc", "new_hash": "def"}

        result = apply_state_policy(task_state, design_changed, change_info)

        # IN_PROGRESS should pause and notify
        assert result["action"] == "pause_and_notify"
        assert result["notify_user"] is True


# ============================================================================
# 7. Edge Cases and Error Handling (3 tests)
# ============================================================================


class TestEdgeCases:
    """Test suite for edge cases and error handling."""

    def test_handle_missing_extraction_metadata(self):
        """Test handling when task has no design_extraction metadata."""
        from guardkit.design.change_detector import check_design_freshness

        metadata = None
        ttl_seconds = 3600

        result = check_design_freshness(metadata, ttl_seconds)

        assert result["is_fresh"] is False
        assert result["needs_refresh"] is True

    def test_handle_mcp_extraction_failure(self):
        """Test handling when MCP extraction fails during requery."""
        from guardkit.design.change_detector import detect_design_change

        old_metadata = {
            "extracted_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "extraction_hash": "a3f2b5c1d8e9f0a1",
            "design_url": "figma://file/abc123/node/2:2"
        }

        mock_extractor = Mock()
        mock_extractor.extract_from_url.side_effect = Exception("MCP unavailable")

        result = detect_design_change(old_metadata, mock_extractor, ttl_seconds=3600)

        assert result["error"] is True
        assert "MCP unavailable" in result["message"]

    def test_handle_corrupted_cache_file(self):
        """Test handling of corrupted cache files."""
        from guardkit.design.cache_manager import load_cache

        cache_file = Path("/tmp/corrupted_cache.json")
        cache_file.write_text("not valid json{{{")

        result = load_cache(cache_file)

        # Should return None or default value on corruption
        assert result is None or result == {}
