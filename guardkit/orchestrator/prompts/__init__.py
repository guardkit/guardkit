"""Protocol loading utilities for AutoBuild prompt builders.

This module provides cached access to protocol reference files that are
read at runtime by prompt builders in the AutoBuild orchestrator.

Protocol files are markdown documents containing focused subsets of the
full task-work specification, sized for efficient context injection.

Example:
    >>> from guardkit.orchestrator.prompts import load_protocol
    >>> execution = load_protocol("autobuild_execution_protocol")
    >>> assert "Phase 3" in execution
    >>> assert len(execution) <= 20480
"""

from pathlib import Path
from typing import Dict


_PROTOCOL_DIR = Path(__file__).parent

# In-memory cache: protocol files are read once per Python process
_cache: Dict[str, str] = {}


def load_protocol(protocol_name: str) -> str:
    """Load a protocol file by name. Cached per process.

    Args:
        protocol_name: Protocol identifier without .md extension.
            Valid names: "autobuild_execution_protocol",
            "autobuild_design_protocol"

    Returns:
        Protocol file content as a string.

    Raises:
        FileNotFoundError: If the protocol file does not exist.
            Error message lists available protocols.

    Example:
        >>> content = load_protocol("autobuild_execution_protocol")
        >>> "PLAYER_REPORT_SCHEMA" in content
        True
    """
    if protocol_name in _cache:
        return _cache[protocol_name]

    protocol_file = _PROTOCOL_DIR / f"{protocol_name}.md"
    if not protocol_file.exists():
        available = sorted(p.stem for p in _PROTOCOL_DIR.glob("*.md"))
        raise FileNotFoundError(
            f"Protocol '{protocol_name}' not found at {protocol_file}. "
            f"Available protocols: {', '.join(available) or 'none'}"
        )

    content = protocol_file.read_text(encoding="utf-8")
    _cache[protocol_name] = content
    return content


def clear_cache() -> None:
    """Clear the protocol cache. Used in tests."""
    _cache.clear()


__all__ = ["load_protocol", "clear_cache"]
