"""
Template Q&A Session Persistence.

Handles saving and loading Q&A sessions for resume functionality.
Uses Python stdlib only (no external dependencies).

Part of TASK-001B: Interactive Q&A Session for /template-init (Greenfield)
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


DEFAULT_SESSION_FILE = ".template-init-session.json"


class PersistenceError(Exception):
    """Raised when session save/load operations fail."""

    pass


def save_session(
    answers: Dict[str, Any],
    session_file: Optional[Path] = None,
    include_metadata: bool = True,
) -> Path:
    """
    Save Q&A session to a JSON file.

    Args:
        answers: Dictionary of Q&A answers
        session_file: Path to save file (default: .template-init-session.json)
        include_metadata: Whether to include metadata (timestamp, version)

    Returns:
        Path to saved session file

    Raises:
        PersistenceError: If save operation fails
    """
    if session_file is None:
        session_file = Path(DEFAULT_SESSION_FILE)

    try:
        # Build session data
        session_data = {
            "answers": answers,
        }

        # Add metadata
        if include_metadata:
            session_data["metadata"] = {
                "saved_at": datetime.utcnow().isoformat() + "Z",
                "version": "1.0",
            }

        # Write to file
        session_file.parent.mkdir(parents=True, exist_ok=True)
        with session_file.open("w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        return session_file

    except OSError as e:
        raise PersistenceError(f"Failed to save session to {session_file}: {e}")
    except (TypeError, ValueError) as e:
        raise PersistenceError(f"Failed to serialize session data: {e}")


def load_session(session_file: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load Q&A session from a JSON file.

    Args:
        session_file: Path to session file (default: .template-init-session.json)

    Returns:
        Dictionary of Q&A answers

    Raises:
        PersistenceError: If load operation fails or file doesn't exist
    """
    if session_file is None:
        session_file = Path(DEFAULT_SESSION_FILE)

    if not session_file.exists():
        raise PersistenceError(f"Session file not found: {session_file}")

    try:
        with session_file.open("r", encoding="utf-8") as f:
            session_data = json.load(f)

        # Extract answers (handle both old and new format)
        if "answers" in session_data:
            return session_data["answers"]
        else:
            # Legacy format: entire file is answers
            return session_data

    except OSError as e:
        raise PersistenceError(f"Failed to read session from {session_file}: {e}")
    except json.JSONDecodeError as e:
        raise PersistenceError(f"Invalid JSON in session file {session_file}: {e}")


def session_exists(session_file: Optional[Path] = None) -> bool:
    """
    Check if a session file exists.

    Args:
        session_file: Path to session file (default: .template-init-session.json)

    Returns:
        True if session file exists, False otherwise
    """
    if session_file is None:
        session_file = Path(DEFAULT_SESSION_FILE)

    return session_file.exists() and session_file.is_file()


def delete_session(session_file: Optional[Path] = None) -> bool:
    """
    Delete a session file.

    Args:
        session_file: Path to session file (default: .template-init-session.json)

    Returns:
        True if file was deleted, False if it didn't exist

    Raises:
        PersistenceError: If deletion fails
    """
    if session_file is None:
        session_file = Path(DEFAULT_SESSION_FILE)

    if not session_file.exists():
        return False

    try:
        session_file.unlink()
        return True
    except OSError as e:
        raise PersistenceError(f"Failed to delete session file {session_file}: {e}")


def get_session_metadata(session_file: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Get metadata from a session file without loading the full session.

    Args:
        session_file: Path to session file (default: .template-init-session.json)

    Returns:
        Dictionary of metadata, or None if not available

    Raises:
        PersistenceError: If read operation fails
    """
    if session_file is None:
        session_file = Path(DEFAULT_SESSION_FILE)

    if not session_file.exists():
        return None

    try:
        with session_file.open("r", encoding="utf-8") as f:
            session_data = json.load(f)

        return session_data.get("metadata")

    except (OSError, json.JSONDecodeError) as e:
        raise PersistenceError(f"Failed to read metadata from {session_file}: {e}")


def backup_session(
    session_file: Optional[Path] = None, backup_suffix: str = ".backup"
) -> Path:
    """
    Create a backup of the current session file.

    Args:
        session_file: Path to session file (default: .template-init-session.json)
        backup_suffix: Suffix to append to backup file

    Returns:
        Path to backup file

    Raises:
        PersistenceError: If backup operation fails
    """
    if session_file is None:
        session_file = Path(DEFAULT_SESSION_FILE)

    if not session_file.exists():
        raise PersistenceError(f"Cannot backup non-existent session: {session_file}")

    backup_file = session_file.with_suffix(session_file.suffix + backup_suffix)

    try:
        # Read original
        with session_file.open("r", encoding="utf-8") as f:
            content = f.read()

        # Write backup
        with backup_file.open("w", encoding="utf-8") as f:
            f.write(content)

        return backup_file

    except OSError as e:
        raise PersistenceError(f"Failed to create backup {backup_file}: {e}")


def merge_sessions(
    base_session: Dict[str, Any], override_session: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge two session answer dictionaries.

    Values in override_session take precedence over base_session.

    Args:
        base_session: Base answers dictionary
        override_session: Override answers dictionary

    Returns:
        Merged dictionary
    """
    merged = base_session.copy()
    merged.update(override_session)
    return merged


def validate_session_data(session_data: Dict[str, Any]) -> bool:
    """
    Validate that session data has the expected structure.

    Args:
        session_data: Session data to validate

    Returns:
        True if valid, False otherwise
    """
    # Must be a dictionary
    if not isinstance(session_data, dict):
        return False

    # If it has metadata, validate structure
    if "metadata" in session_data:
        metadata = session_data["metadata"]
        if not isinstance(metadata, dict):
            return False
        if "version" not in metadata:
            return False

    # If it has answers, validate it's a dict
    if "answers" in session_data:
        if not isinstance(session_data["answers"], dict):
            return False

    return True


def get_session_summary(session_file: Optional[Path] = None) -> Dict[str, Any]:
    """
    Get a summary of a saved session without loading all data.

    Args:
        session_file: Path to session file (default: .template-init-session.json)

    Returns:
        Dictionary with summary information

    Raises:
        PersistenceError: If read operation fails
    """
    if session_file is None:
        session_file = Path(DEFAULT_SESSION_FILE)

    if not session_file.exists():
        return {
            "exists": False,
            "path": str(session_file),
        }

    try:
        metadata = get_session_metadata(session_file)
        answers = load_session(session_file)

        # Count sections with answers
        sections_completed = len([k for k, v in answers.items() if v is not None])

        return {
            "exists": True,
            "path": str(session_file),
            "saved_at": metadata.get("saved_at") if metadata else None,
            "version": metadata.get("version") if metadata else None,
            "sections_completed": sections_completed,
            "total_answers": len(answers),
        }

    except PersistenceError:
        # Re-raise persistence errors
        raise
    except Exception as e:
        raise PersistenceError(f"Failed to get session summary: {e}")


# Module exports
__all__ = [
    "PersistenceError",
    "save_session",
    "load_session",
    "session_exists",
    "delete_session",
    "get_session_metadata",
    "backup_session",
    "merge_sessions",
    "validate_session_data",
    "get_session_summary",
    "DEFAULT_SESSION_FILE",
]
