"""
State Paths Module

Centralized state file path management for GuardKit.
Provides consistent state directory location and filename constants.

TASK-FIX-STATE02: Centralize medium priority state file paths
"""

from pathlib import Path


# State directory constants
STATE_DIR_NAME = ".agentecflow"
STATE_SUBDIR_NAME = "state"


# State filename constants (with leading dots for hidden files)
AGENT_ENHANCE_STATE = ".agent-enhance-state.json"
TEMPLATE_CREATE_STATE = ".template-create-state.json"
TEMPLATE_CONFIG = ".template-create-config.json"
TEMPLATE_SESSION = ".template-init-session.json"
TEMPLATE_PARTIAL_SESSION = ".template-init-partial-session.json"


def get_state_dir() -> Path:
    """
    Get the state directory path, creating it if it doesn't exist.

    Returns:
        Path: Absolute path to ~/.agentecflow/state/

    Example:
        >>> state_dir = get_state_dir()
        >>> state_dir.exists()
        True
        >>> str(state_dir).endswith('.agentecflow/state')
        True
    """
    state_dir = Path.home() / STATE_DIR_NAME / STATE_SUBDIR_NAME
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def get_state_file(filename: str) -> Path:
    """
    Get absolute path to a state file in the state directory.

    Args:
        filename: Name of the state file (e.g., ".agent-enhance-state.json")

    Returns:
        Path: Absolute path to the state file

    Example:
        >>> path = get_state_file(".agent-enhance-state.json")
        >>> str(path).endswith('.agentecflow/state/.agent-enhance-state.json')
        True
    """
    return get_state_dir() / filename


def get_phase_request_file(phase: int) -> Path:
    """
    Get absolute path to phase-specific agent request file.

    Args:
        phase: Phase number (1-8)

    Returns:
        Path: Absolute path to phase request file

    Example:
        >>> path = get_phase_request_file(6)
        >>> str(path).endswith('.agentecflow/state/.agent-request-phase6.json')
        True
    """
    return get_state_dir() / f".agent-request-phase{phase}.json"


def get_phase_response_file(phase: int) -> Path:
    """
    Get absolute path to phase-specific agent response file.

    Args:
        phase: Phase number (1-8)

    Returns:
        Path: Absolute path to phase response file

    Example:
        >>> path = get_phase_response_file(6)
        >>> str(path).endswith('.agentecflow/state/.agent-response-phase6.json')
        True
    """
    return get_state_dir() / f".agent-response-phase{phase}.json"


# Module exports
__all__ = [
    "get_state_dir",
    "get_state_file",
    "get_phase_request_file",
    "get_phase_response_file",
    "AGENT_ENHANCE_STATE",
    "TEMPLATE_CREATE_STATE",
    "TEMPLATE_CONFIG",
    "TEMPLATE_SESSION",
    "TEMPLATE_PARTIAL_SESSION",
]
