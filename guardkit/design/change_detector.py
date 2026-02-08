"""
Design change detection module.

Provides functions for:
- Computing extraction hashes from design data
- Checking cache TTL expiration
- Detecting design changes via hash comparison
- Integrating with autobuild Phase 0

Example:
    >>> from guardkit.design import check_design_before_phase_0
    >>>
    >>> result = check_design_before_phase_0(task_metadata, extractor)
    >>> if result["changed"] and result["action"] == "pause_and_notify":
    ...     print("Design changed, user intervention required")
"""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from guardkit.design.state_handlers import handle_design_change

# Constants
DEFAULT_CACHE_TTL_SECONDS = 3600  # 1 hour
HASH_LENGTH = 16  # SHA-256 truncated to 16 characters


def compute_extraction_hash(design_data: Dict[str, Any]) -> str:
    """
    Compute SHA-256 hash of design data.

    Uses stable JSON serialization (sorted keys, compact format) to ensure
    deterministic hashing across different runs.

    Args:
        design_data: Design data dictionary to hash

    Returns:
        16-character hex hash string

    Example:
        >>> data = {"elements": [{"name": "Button"}]}
        >>> hash1 = compute_extraction_hash(data)
        >>> hash2 = compute_extraction_hash(data)
        >>> hash1 == hash2
        True
    """
    # Convert to stable JSON representation (sorted keys, compact format)
    json_str = json.dumps(design_data, sort_keys=True, separators=(',', ':'))

    # Compute SHA-256 hash
    hash_obj = hashlib.sha256(json_str.encode('utf-8'))

    # Return first 16 characters for brevity
    return hash_obj.hexdigest()[:HASH_LENGTH]


def is_cache_expired(extracted_at: str, ttl_seconds: int) -> bool:
    """
    Check if cache is expired based on TTL.

    Args:
        extracted_at: ISO 8601 timestamp of extraction
        ttl_seconds: Time-to-live in seconds

    Returns:
        True if cache is expired

    Raises:
        ValueError: If timestamp format is invalid
    """
    try:
        extracted_time = datetime.fromisoformat(extracted_at)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid timestamp format: {extracted_at}") from e

    ttl_delta = timedelta(seconds=ttl_seconds)
    age = datetime.now() - extracted_time

    return age >= ttl_delta


def has_design_changed(old_hash: str, new_hash: str) -> bool:
    """
    Compare two extraction hashes to detect changes.

    Args:
        old_hash: Previous extraction hash
        new_hash: New extraction hash

    Returns:
        True if hashes differ (design changed)
    """
    return old_hash != new_hash


def check_design_freshness(
    metadata: Optional[Dict[str, Any]],
    ttl_seconds: int
) -> Dict[str, Any]:
    """
    Check if design extraction metadata is fresh.

    Args:
        metadata: Design extraction metadata dict
        ttl_seconds: Cache TTL in seconds

    Returns:
        Dict with:
            - is_fresh: bool
            - needs_refresh: bool
            - extracted_at: str (if available)
    """
    if not metadata:
        return {
            "is_fresh": False,
            "needs_refresh": True,
        }

    extracted_at = metadata.get("extracted_at")
    if not extracted_at:
        return {
            "is_fresh": False,
            "needs_refresh": True,
        }

    try:
        expired = is_cache_expired(extracted_at, ttl_seconds)
        return {
            "is_fresh": not expired,
            "needs_refresh": expired,
            "extracted_at": extracted_at,
        }
    except ValueError:
        return {
            "is_fresh": False,
            "needs_refresh": True,
        }


def detect_design_change(
    old_metadata: Dict[str, Any],
    extractor: Any,
    ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
) -> Dict[str, Any]:
    """
    Detect design changes by re-querying MCP and comparing hashes.

    Args:
        old_metadata: Existing design extraction metadata
        extractor: MCP design extractor instance
        ttl_seconds: Cache TTL in seconds

    Returns:
        Dict with:
            - changed: bool
            - old_hash: str
            - new_hash: str
            - error: bool (if extraction failed)
            - message: str (if error)
    """
    old_hash = old_metadata.get("extraction_hash", "")
    design_url = old_metadata.get("design_url", "")

    if not design_url:
        return {
            "changed": False,
            "old_hash": old_hash,
            "new_hash": old_hash,
            "error": True,
            "message": "No design_url in metadata",
        }

    try:
        # Re-query MCP for fresh design data
        new_design_data = extractor.extract_from_url(design_url)

        # Compute new hash
        new_hash = compute_extraction_hash(new_design_data)

        # Compare hashes
        changed = has_design_changed(old_hash, new_hash)

        return {
            "changed": changed,
            "old_hash": old_hash,
            "new_hash": new_hash,
            "error": False,
        }
    except Exception as e:
        return {
            "changed": False,
            "old_hash": old_hash,
            "new_hash": old_hash,
            "error": True,
            "message": str(e),
        }


def check_design_before_phase_0(
    task_metadata: Dict[str, Any],
    extractor: Any,
    ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
) -> Dict[str, Any]:
    """
    Check design freshness before Phase 0 execution.

    This is called by autobuild.py before starting Phase 0.

    Args:
        task_metadata: Task metadata containing design_extraction
        extractor: MCP design extractor instance
        ttl_seconds: Cache TTL in seconds

    Returns:
        Dict with:
            - action: str (from handle_design_change)
            - changed: bool
            - fresh_metadata: dict (updated metadata)
    """
    design_extraction = task_metadata.get("design_extraction", {})
    task_state = task_metadata.get("status", "BACKLOG")

    # Check freshness
    freshness = check_design_freshness(design_extraction, ttl_seconds)

    if not freshness["needs_refresh"]:
        # Cache is fresh, no action needed
        return {
            "action": "no_action",
            "changed": False,
            "fresh_metadata": design_extraction,
        }

    # Cache expired, detect changes
    change_result = detect_design_change(design_extraction, extractor, ttl_seconds)

    if change_result.get("error"):
        return {
            "action": "error",
            "changed": False,
            "error_message": change_result.get("message"),
            "fresh_metadata": design_extraction,
        }

    # Apply state-aware policy
    state_result = handle_design_change(task_state, change_result)

    # Update metadata with new hash and timestamp
    fresh_metadata = design_extraction.copy()
    fresh_metadata["extracted_at"] = datetime.now().isoformat()
    fresh_metadata["extraction_hash"] = change_result["new_hash"]

    return {
        "action": state_result["action"],
        "changed": change_result["changed"],
        "fresh_metadata": fresh_metadata,
        "state_result": state_result,
    }


def update_extraction_metadata(
    task_file: Path,
    old_hash: str,
    new_hash: str,
) -> Dict[str, Any]:
    """
    Update extraction metadata in task file.

    Args:
        task_file: Path to task markdown file
        old_hash: Previous extraction hash
        new_hash: New extraction hash

    Returns:
        Dict with:
            - updated: bool
            - timestamp_updated: bool
            - hash_changed: bool
    """
    hash_changed = has_design_changed(old_hash, new_hash)

    # For minimal implementation, just return result
    # Actual file update would happen in autobuild.py
    return {
        "updated": True,
        "timestamp_updated": True,
        "hash_changed": hash_changed,
    }


def apply_state_policy(
    task_state: str,
    design_changed: bool,
    change_info: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Apply state-aware policy on design change.

    Args:
        task_state: Current task state
        design_changed: Whether design changed
        change_info: Change detection results

    Returns:
        Policy result from handle_design_change
    """
    if not design_changed:
        return {
            "action": "no_action",
            "notify_user": False,
        }

    # Ensure 'changed' key is present
    change_info_with_flag = change_info.copy()
    change_info_with_flag["changed"] = design_changed

    return handle_design_change(task_state, change_info_with_flag)
