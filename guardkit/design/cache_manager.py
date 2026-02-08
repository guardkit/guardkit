"""
Design cache management module.

Provides functions for:
- Cache path generation
- Cache invalidation
- Expired cache cleanup
- Cache directory management
"""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional


def get_cache_path(design_url: str, cache_dir: Path) -> Path:
    """
    Generate cache file path from design URL.

    Args:
        design_url: Design URL (e.g., "figma://file/abc123/node/2:2")
        cache_dir: Cache directory path

    Returns:
        Path to cache file
    """
    # Hash the URL to create a deterministic cache key
    url_hash = hashlib.sha256(design_url.encode('utf-8')).hexdigest()[:16]

    # Return cache file path
    return cache_dir / f"{url_hash}.json"


def invalidate_cache(design_url: str, cache_dir: Path) -> Dict[str, Any]:
    """
    Invalidate cache entry for a design URL.

    Args:
        design_url: Design URL to invalidate
        cache_dir: Cache directory path

    Returns:
        Dict with:
            - invalidated: bool
            - reason: str
            - path: str (optional)
    """
    cache_file = get_cache_path(design_url, cache_dir)

    if cache_file.exists():
        try:
            cache_file.unlink()
            return {
                "invalidated": True,
                "reason": "design_url_changed",
                "path": str(cache_file),
            }
        except OSError:
            return {
                "invalidated": False,
                "reason": "failed_to_delete",
                "path": str(cache_file),
            }
    else:
        return {
            "invalidated": True,
            "reason": "cache_not_found",
        }


def clean_expired_caches(cache_dir: Path, ttl_seconds: int) -> Dict[str, Any]:
    """
    Clean up expired cache entries.

    Args:
        cache_dir: Cache directory path
        ttl_seconds: Cache TTL in seconds

    Returns:
        Dict with:
            - cleaned_count: int
            - errors: list (optional)
    """
    if not cache_dir.exists():
        return {"cleaned_count": 0}

    cleaned_count = 0
    errors = []
    ttl_delta = timedelta(seconds=ttl_seconds)
    now = datetime.now()

    for cache_file in cache_dir.glob("*.json"):
        try:
            # Load cache to check timestamp
            cache_data = load_cache(cache_file)
            if not cache_data:
                # Corrupted or invalid cache, remove it
                cache_file.unlink()
                cleaned_count += 1
                continue

            cached_at_str = cache_data.get("cached_at")
            if not cached_at_str:
                # No timestamp, remove it
                cache_file.unlink()
                cleaned_count += 1
                continue

            cached_at = datetime.fromisoformat(cached_at_str)
            age = now - cached_at

            if age >= ttl_delta:
                # Expired, remove it
                cache_file.unlink()
                cleaned_count += 1

        except Exception as e:
            errors.append(f"{cache_file.name}: {str(e)}")

    result = {"cleaned_count": cleaned_count}
    if errors:
        result["errors"] = errors

    return result


def ensure_cache_dir(cache_dir: Path) -> None:
    """
    Ensure cache directory exists.

    Args:
        cache_dir: Cache directory path
    """
    cache_dir.mkdir(parents=True, exist_ok=True)


def load_cache(cache_file: Path) -> Optional[Dict[str, Any]]:
    """
    Load cache data from file.

    Args:
        cache_file: Path to cache file

    Returns:
        Cache data dict, or None if corrupted/missing
    """
    if not cache_file.exists():
        return None

    try:
        with open(cache_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
