#!/usr/bin/env python3
"""Feature detection module for GuardKit/RequireKit integration.

This module provides functions to gracefully detect which features are available
based on installed packages and configuration markers. It enables commands to
adapt behavior at runtime without hard dependencies.

Key Features:
    - Detects RequireKit installation via marker files
    - Supports both new (JSON) and legacy marker formats
    - Cross-platform path handling with pathlib
    - Graceful error handling for missing files and invalid JSON
    - Provides version detection for installed packages

Module Design:
    - No external dependencies beyond standard library
    - Marker-based detection (non-intrusive, works with Conductor worktrees)
    - Shared helper for DRY principle (extract common path logic)
    - Type hints on all functions for IDE and linting support
    - Google-style docstrings for API clarity

Example:
    >>> from installer.core.commands.lib.feature_detection import supports_bdd
    >>> if supports_bdd():
    ...     print("BDD workflow available")
    ... else:
    ...     print("RequireKit not installed")

Part of: Task BDD-F3EA - Create feature_detection module for RequireKit detection
Architecture: Phase 2.5 recommended refactoring applied (marker path extraction)
Author: Claude (Anthropic)
Created: 2025-11-30
"""

import json
import logging
from pathlib import Path
from typing import Optional

# Configure logging (no propagation unless explicitly enabled by caller)
logger = logging.getLogger(__name__)


# Constants for marker file locations
_AGENTECFLOW_DIR = ".agentecflow"
_MARKER_FILE_NEW = "require-kit.marker.json"
_MARKER_FILE_LEGACY = "require-kit.marker"


def _get_marker_file_paths() -> list[Path]:
    """Get paths to check for RequireKit marker files.

    Returns marker file paths in priority order (new format first, then legacy).
    Uses pathlib for cross-platform compatibility.

    Returns:
        List of Path objects to check, in priority order. Checks:
        1. ~/.agentecflow/require-kit.marker.json (new JSON format)
        2. ~/Projects/require-kit/require-kit.marker (legacy format)

    Example:
        >>> paths = _get_marker_file_paths()
        >>> print(paths[0])
        /Users/username/.agentecflow/require-kit.marker.json
    """
    home = Path.home()
    return [
        home / _AGENTECFLOW_DIR / _MARKER_FILE_NEW,      # New JSON format
        home / "Projects" / "require-kit" / _MARKER_FILE_LEGACY  # Legacy format
    ]


def supports_bdd() -> bool:
    """Check if BDD workflow is supported.

    BDD (Behavior-Driven Development) workflow requires RequireKit to be installed.
    This function checks for the existence of RequireKit marker files in expected
    locations. It handles both the new marker format (JSON) and legacy format.

    Detection logic:
        - Returns True if ~/.agentecflow/require-kit.marker.json exists
        - OR returns True if ~/Projects/require-kit/require-kit.marker exists
        - Otherwise returns False

    This is a graceful check - no exceptions are raised if files don't exist or
    are unreadable. The function simply returns False (feature not available).

    Returns:
        bool: True if RequireKit is installed and BDD workflow available,
              False otherwise.

    Example:
        >>> if supports_bdd():
        ...     print("BDD mode available")
        ... else:
        ...     print("RequireKit not installed - use standard mode")
    """
    try:
        marker_paths = _get_marker_file_paths()
        return any(path.exists() for path in marker_paths)
    except (OSError, RuntimeError) as e:
        logger.debug(f"Error checking BDD support: {e}")
        return False


def supports_requirements() -> bool:
    """Check if requirements management is supported.

    Requirements management features (EARS notation, requirements tracking)
    require RequireKit to be installed. This function uses the same detection
    logic as BDD support since requirements management is core to RequireKit.

    Returns:
        bool: True if RequireKit is installed and requirements management available,
              False otherwise.

    Example:
        >>> if supports_requirements():
        ...     print("Requirements management available")
    """
    return supports_bdd()


def supports_epics() -> bool:
    """Check if epic/feature hierarchy is supported.

    Epic and feature hierarchy management (parent-child task relationships)
    require RequireKit to be installed. This function uses the same detection
    logic as BDD support since epic management is provided by RequireKit.

    Returns:
        bool: True if RequireKit is installed and epic management available,
              False otherwise.

    Example:
        >>> if supports_epics():
        ...     print("Epic hierarchy available")
    """
    return supports_bdd()


def get_requirekit_version() -> Optional[str]:
    """Get RequireKit version from marker file.

    Attempts to read the RequireKit version from the new marker file format
    (JSON). The version is extracted from the "version" field in the JSON object.

    If RequireKit is not installed, returns None. If the marker file exists but
    is not valid JSON or doesn't contain a version field, logs a warning and
    returns None.

    File format (expected):
        {
            "package": "require-kit",
            "version": "1.0.0",
            ...other metadata...
        }

    Returns:
        Optional[str]: Version string if available (e.g., "1.0.0"),
                      None if RequireKit not installed or version unavailable.

    Raises:
        No exceptions. All errors are logged and None is returned.

    Example:
        >>> version = get_requirekit_version()
        >>> if version:
        ...     print(f"RequireKit version {version} installed")
        ... else:
        ...     print("RequireKit not installed or version unavailable")
    """
    if not supports_bdd():
        return None

    marker_path = Path.home() / _AGENTECFLOW_DIR / _MARKER_FILE_NEW

    if not marker_path.exists():
        return None

    try:
        with open(marker_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            version = data.get("version")
            if isinstance(version, str):
                return version
            else:
                logger.debug(f"Invalid version type in marker file: {type(version)}")
                return None
    except json.JSONDecodeError as e:
        logger.debug(f"Failed to parse marker file JSON: {e}")
        return None
    except (IOError, OSError) as e:
        logger.debug(f"Failed to read marker file: {e}")
        return None
    except Exception as e:
        logger.debug(f"Unexpected error reading RequireKit version: {e}")
        return None


# Public API
__all__ = [
    "supports_bdd",
    "supports_requirements",
    "supports_epics",
    "get_requirekit_version",
]
