"""
Unit tests for cache_manager.py - Design cache management.

Tests cover:
    - Cache path generation
    - Cache invalidation on URL change
    - Expired cache cleanup
    - Cache directory management
    - Cache loading and corruption handling

Coverage Target: >=85%
Test Count: 15+ tests
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from guardkit.design.cache_manager import (
    get_cache_path,
    invalidate_cache,
    clean_expired_caches,
    ensure_cache_dir,
    load_cache,
)


# ============================================================================
# Cache Path Generation Tests (3 tests)
# ============================================================================


class TestCachePath:
    """Test suite for cache path generation."""

    def test_cache_path_deterministic(self, tmp_path):
        """Test cache path generation is deterministic."""
        design_url = "figma://file/abc123/node/2:2"
        cache_dir = tmp_path / "cache"

        path1 = get_cache_path(design_url, cache_dir)
        path2 = get_cache_path(design_url, cache_dir)

        assert path1 == path2

    def test_different_urls_different_paths(self, tmp_path):
        """Test different URLs generate different cache paths."""
        url1 = "figma://file/abc123/node/2:2"
        url2 = "figma://file/abc123/node/3:3"
        cache_dir = tmp_path / "cache"

        path1 = get_cache_path(url1, cache_dir)
        path2 = get_cache_path(url2, cache_dir)

        assert path1 != path2

    def test_cache_path_format(self, tmp_path):
        """Test cache path has correct format."""
        design_url = "figma://file/abc123/node/2:2"
        cache_dir = tmp_path / "cache"

        path = get_cache_path(design_url, cache_dir)

        assert path.parent == cache_dir
        assert path.suffix == ".json"
        assert len(path.stem) == 16  # 16-char hash


# ============================================================================
# Cache Invalidation Tests (4 tests)
# ============================================================================


class TestCacheInvalidation:
    """Test suite for cache invalidation."""

    def test_invalidate_existing_cache(self, tmp_path):
        """Test invalidation of existing cache file."""
        design_url = "figma://file/abc123/node/2:2"
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)

        # Create cache file
        cache_file = get_cache_path(design_url, cache_dir)
        cache_file.write_text('{"data": "test"}')

        result = invalidate_cache(design_url, cache_dir)

        assert result["invalidated"] is True
        assert result["reason"] == "design_url_changed"
        assert not cache_file.exists()

    def test_invalidate_nonexistent_cache(self, tmp_path):
        """Test invalidation when cache doesn't exist."""
        design_url = "figma://file/abc123/node/2:2"
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)

        result = invalidate_cache(design_url, cache_dir)

        assert result["invalidated"] is True
        assert result["reason"] == "cache_not_found"

    def test_invalidate_cache_permissions_error(self, tmp_path, monkeypatch):
        """Test handling of permission errors during invalidation."""
        design_url = "figma://file/abc123/node/2:2"
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)

        # Create cache file
        cache_file = get_cache_path(design_url, cache_dir)
        cache_file.write_text('{"data": "test"}')

        # Mock unlink to raise OSError
        original_unlink = Path.unlink

        def mock_unlink(self, *args, **kwargs):
            if str(self) == str(cache_file):
                raise OSError("Permission denied")
            return original_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", mock_unlink)

        result = invalidate_cache(design_url, cache_dir)

        assert result["invalidated"] is False
        assert result["reason"] == "failed_to_delete"

    def test_invalidate_returns_path(self, tmp_path):
        """Test invalidation result includes cache path."""
        design_url = "figma://file/abc123/node/2:2"
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)

        cache_file = get_cache_path(design_url, cache_dir)
        cache_file.write_text('{"data": "test"}')

        result = invalidate_cache(design_url, cache_dir)

        assert "path" in result
        assert cache_file.name in result["path"]


# ============================================================================
# Cache Cleanup Tests (4 tests)
# ============================================================================


class TestCacheCleanup:
    """Test suite for expired cache cleanup."""

    def test_clean_expired_caches(self, tmp_path):
        """Test cleanup of expired cache entries."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)

        # Create expired cache (3 hours old)
        expired_cache = cache_dir / "expired.json"
        expired_time = (datetime.now() - timedelta(hours=3)).isoformat()
        expired_cache.write_text(json.dumps({"cached_at": expired_time}))

        # Create fresh cache (30 minutes old)
        fresh_cache = cache_dir / "fresh.json"
        fresh_time = (datetime.now() - timedelta(minutes=30)).isoformat()
        fresh_cache.write_text(json.dumps({"cached_at": fresh_time}))

        # Clean with 1 hour TTL
        result = clean_expired_caches(cache_dir, ttl_seconds=3600)

        assert result["cleaned_count"] == 1
        assert not expired_cache.exists()
        assert fresh_cache.exists()

    def test_clean_corrupted_cache(self, tmp_path):
        """Test cleanup removes corrupted cache files."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)

        # Create corrupted cache
        corrupted = cache_dir / "corrupted.json"
        corrupted.write_text("not valid json{{{")

        result = clean_expired_caches(cache_dir, ttl_seconds=3600)

        assert result["cleaned_count"] == 1
        assert not corrupted.exists()

    def test_clean_cache_no_timestamp(self, tmp_path):
        """Test cleanup removes cache without timestamp."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)

        # Create cache without timestamp
        no_timestamp = cache_dir / "no_timestamp.json"
        no_timestamp.write_text(json.dumps({"data": "test"}))

        result = clean_expired_caches(cache_dir, ttl_seconds=3600)

        assert result["cleaned_count"] == 1
        assert not no_timestamp.exists()

    def test_clean_nonexistent_cache_dir(self, tmp_path):
        """Test cleanup when cache directory doesn't exist."""
        cache_dir = tmp_path / "nonexistent_cache"

        result = clean_expired_caches(cache_dir, ttl_seconds=3600)

        assert result["cleaned_count"] == 0


# ============================================================================
# Cache Directory Management Tests (2 tests)
# ============================================================================


class TestCacheDirectory:
    """Test suite for cache directory management."""

    def test_ensure_cache_dir_creates_directory(self, tmp_path):
        """Test cache directory creation."""
        cache_dir = tmp_path / "cache" / "nested" / "path"

        ensure_cache_dir(cache_dir)

        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_ensure_cache_dir_idempotent(self, tmp_path):
        """Test ensure_cache_dir is idempotent."""
        cache_dir = tmp_path / "cache"

        ensure_cache_dir(cache_dir)
        ensure_cache_dir(cache_dir)  # Second call

        assert cache_dir.exists()


# ============================================================================
# Cache Loading Tests (3 tests)
# ============================================================================


class TestCacheLoading:
    """Test suite for cache loading."""

    def test_load_valid_cache(self, tmp_path):
        """Test loading valid cache file."""
        cache_file = tmp_path / "cache.json"
        cache_data = {
            "cached_at": "2024-01-01T00:00:00",
            "data": {"elements": [{"name": "Button"}]}
        }
        cache_file.write_text(json.dumps(cache_data))

        result = load_cache(cache_file)

        assert result == cache_data

    def test_load_corrupted_cache(self, tmp_path):
        """Test loading corrupted cache returns None."""
        cache_file = tmp_path / "corrupted.json"
        cache_file.write_text("not valid json{{{")

        result = load_cache(cache_file)

        assert result is None

    def test_load_nonexistent_cache(self, tmp_path):
        """Test loading nonexistent cache returns None."""
        cache_file = tmp_path / "nonexistent.json"

        result = load_cache(cache_file)

        assert result is None
