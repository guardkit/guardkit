"""
Lightweight JSONL logger for Graphiti query results.

Tracks what queries return (empty vs populated, result count, relevance)
to validate data quality over time. Designed for debugging data quality,
not production telemetry.

Log file: .guardkit/graphiti-query-log.jsonl (append-only, 1MB rotation)

Usage:
    from guardkit.knowledge.query_logger import log_query

    log_query(
        operation="search",
        query="authentication patterns",
        group_ids=["architecture_decisions"],
        result_count=3,
        first_result_preview="JWT-based auth is recommended for...",
        source="graphiti_client",
    )
"""

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default log file location (relative to project root)
_DEFAULT_LOG_DIR = ".guardkit"
_DEFAULT_LOG_FILENAME = "graphiti-query-log.jsonl"
_MAX_FILE_SIZE_BYTES = 1_048_576  # 1 MB
_PREVIEW_LENGTH = 50

# Module-level lock for thread-safe file writes
_write_lock = threading.Lock()


def _get_log_path(base_dir: Optional[str] = None) -> Path:
    """Get the log file path, creating the directory if needed.

    Args:
        base_dir: Override base directory (for testing). If None, uses cwd.

    Returns:
        Path to the JSONL log file.
    """
    if base_dir is not None:
        log_dir = Path(base_dir) / _DEFAULT_LOG_DIR
    else:
        log_dir = Path.cwd() / _DEFAULT_LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / _DEFAULT_LOG_FILENAME


def _rotate_if_needed(log_path: Path) -> None:
    """Rotate log file if it exceeds the size limit.

    Rotation strategy: rename current file to .1 (overwriting any previous .1),
    then new writes go to a fresh file. Simple single-backup rotation.

    Args:
        log_path: Path to the current log file.
    """
    try:
        if log_path.exists() and log_path.stat().st_size > _MAX_FILE_SIZE_BYTES:
            rotated = log_path.with_suffix(".jsonl.1")
            log_path.rename(rotated)
    except OSError as e:
        logger.debug("Log rotation failed (non-critical): %s", e)


def _build_entry(
    operation: str,
    query: str,
    group_ids: Optional[List[str]],
    result_count: int,
    first_result_preview: Optional[str],
    source: str,
) -> Dict[str, Any]:
    """Build a log entry dictionary.

    Args:
        operation: Type of operation ("search", "add_episode", etc.)
        query: The query text or episode name.
        group_ids: Group IDs used in the query.
        result_count: Number of results returned.
        first_result_preview: Preview of the first result (truncated to 50 chars).
        source: Calling context identifier (e.g., "graphiti_client", "task-work").

    Returns:
        Dictionary ready for JSON serialization.
    """
    preview = None
    if first_result_preview is not None:
        preview = first_result_preview[:_PREVIEW_LENGTH]

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "operation": operation,
        "query": query,
        "group_ids": group_ids or [],
        "result_count": result_count,
        "first_result_preview": preview,
    }


def log_query(
    operation: str,
    query: str,
    group_ids: Optional[List[str]] = None,
    result_count: int = 0,
    first_result_preview: Optional[str] = None,
    source: str = "graphiti_client",
    base_dir: Optional[str] = None,
) -> None:
    """Log a Graphiti query result to the JSONL log file.

    Thread-safe, append-only, with automatic 1MB rotation.
    Failures are silently logged at DEBUG level — never raises.

    Args:
        operation: Type of operation ("search", "add_episode", etc.)
        query: The query text or episode name.
        group_ids: Group IDs used in the query.
        result_count: Number of results returned.
        first_result_preview: Preview of first result (truncated to 50 chars).
        source: Calling context identifier.
        base_dir: Override base directory (for testing).
    """
    try:
        entry = _build_entry(
            operation=operation,
            query=query,
            group_ids=group_ids,
            result_count=result_count,
            first_result_preview=first_result_preview,
            source=source,
        )
        line = json.dumps(entry, separators=(",", ":")) + "\n"

        with _write_lock:
            log_path = _get_log_path(base_dir)
            _rotate_if_needed(log_path)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line)
    except Exception as e:
        logger.debug("Query logging failed (non-critical): %s", e)


def extract_preview(results: List[Dict[str, Any]]) -> Optional[str]:
    """Extract a preview string from search results.

    Looks for 'fact', 'name', or 'content' fields in the first result.

    Args:
        results: List of result dictionaries from a search.

    Returns:
        First 50 characters of the first result's content, or None.
    """
    if not results:
        return None
    first = results[0]
    for key in ("fact", "name", "content"):
        value = first.get(key)
        if value and isinstance(value, str):
            return value[:_PREVIEW_LENGTH]
    return None
