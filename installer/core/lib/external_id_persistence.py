"""
External ID Persistence Layer

Provides persistent JSON storage for internal ↔ external ID mappings and
PM tool counters with atomic operations, file locking, and corruption recovery.

Features:
- Atomic read-modify-write operations
- File locking for concurrent access (fcntl)
- Automatic backup before writes
- Corruption detection and recovery
- Auto-create directories as needed
- Pretty-printed JSON for human readability

Usage:
    persistence = ExternalIDPersistence()

    # Save mappings
    mappings = {"TASK-E01-b2c4": {"jira": "PROJ-1", "github": "1"}}
    persistence.save_mappings(mappings)

    # Load mappings
    loaded = persistence.load_mappings()

    # Save counters
    counters = {"jira": {"PROJ": 2}, "azure_devops": 1, "linear": {}, "github": 1}
    persistence.save_counters(counters)

    # Load counters
    loaded_counters = persistence.load_counters()
"""

import json
import os
import tempfile
import fcntl
import shutil
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Dict, Any, Union


class ExternalIDPersistence:
    """
    Manages persistent storage for external ID mappings and counters.

    Attributes:
        state_dir (Path): Directory for state files (.claude/state/)
        VERSION (str): Schema version for JSON files
        MAPPING_FILE (str): Filename for mapping storage
        COUNTER_FILE (str): Filename for counter storage
    """

    # Constants (addresses architectural review feedback #3)
    VERSION = "1.0"
    MAPPING_FILE = "external_id_mapping.json"
    COUNTER_FILE = "external_id_counters.json"
    MAPPING_KEY = "mappings"
    COUNTER_KEY = "counters"
    VERSION_KEY = "version"
    UPDATED_KEY = "updated"

    def __init__(self, state_dir: Path = None):
        """
        Initialize persistence layer.

        Args:
            state_dir: Directory for state files. Defaults to .claude/state/
        """
        if state_dir is None:
            # Default to .claude/state/ in current working directory
            state_dir = Path.cwd() / ".claude" / "state"

        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def save_mappings(self, mappings: Dict[str, Dict[str, str]]) -> None:
        """
        Save mappings to JSON with atomic write.

        Creates backup before write, uses temp file + atomic rename.

        Args:
            mappings: Dictionary of internal_id -> {tool: external_id}

        Example:
            >>> persistence.save_mappings({
            ...     "TASK-E01-b2c4": {"jira": "PROJ-1", "github": "1"}
            ... })
        """
        path = self.state_dir / self.MAPPING_FILE
        data = self._wrap_data(self.MAPPING_KEY, mappings)

        with self._file_lock(path):
            self._atomic_write(path, data)

    def load_mappings(self, _retry: int = 0) -> Dict[str, Dict[str, str]]:
        """
        Load mappings from JSON, handle missing/corrupt files.

        Returns empty dict if file missing.
        Attempts backup restore if corrupted (once only).

        Args:
            _retry: Internal recursion counter (prevents infinite loops)

        Returns:
            Dictionary of internal_id -> {tool: external_id}

        Example:
            >>> mappings = persistence.load_mappings()
            >>> print(mappings.get("TASK-E01-b2c4"))
            {'jira': 'PROJ-1', 'github': '1'}
        """
        # Recursion limit (addresses architectural review feedback #1)
        if _retry >= 2:
            # Already tried backup and still failed, give up
            return {}

        path = self.state_dir / self.MAPPING_FILE

        if not path.exists():
            return {}

        with self._file_lock(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)

                if not self._validate_mapping_data(data):
                    raise ValueError("Invalid mapping data structure")

                return data.get(self.MAPPING_KEY, {})

            except (json.JSONDecodeError, ValueError) as e:
                # Try backup once (only if _retry < 1)
                if _retry < 1:
                    backup_path = path.with_suffix(path.suffix + '.bak')
                    if backup_path.exists():
                        self._restore_from_backup(path)
                        return self.load_mappings(_retry=_retry + 1)  # Increment counter

                # No backup available or already tried, return empty
                return {}

    def save_counters(self, counters: Dict[str, Union[int, Dict[str, int]]]) -> None:
        """
        Save counters to JSON with atomic write.

        Args:
            counters: Dictionary of tool -> counter value
                      Format: {"jira": {"PROJ": 1}, "azure_devops": 1, ...}

        Example:
            >>> persistence.save_counters({
            ...     "jira": {"PROJ": 1},
            ...     "azure_devops": 1,
            ...     "linear": {},
            ...     "github": 1
            ... })
        """
        path = self.state_dir / self.COUNTER_FILE
        data = self._wrap_data(self.COUNTER_KEY, counters)

        with self._file_lock(path):
            self._atomic_write(path, data)

    def load_counters(self, _retry: int = 0) -> Dict[str, Union[int, Dict[str, int]]]:
        """
        Load counters from JSON, handle missing/corrupt files.

        Returns default structure if file missing.
        Attempts backup restore if corrupted (once only).

        Args:
            _retry: Internal recursion counter (prevents infinite loops)

        Returns:
            Dictionary of tool -> counter value

        Example:
            >>> counters = persistence.load_counters()
            >>> print(counters["jira"]["PROJ"])
            1
        """
        # Recursion limit (addresses architectural review feedback #1)
        if _retry >= 2:
            # Already tried backup and still failed, return defaults
            return self._default_counter_structure()

        path = self.state_dir / self.COUNTER_FILE

        if not path.exists():
            return self._default_counter_structure()

        with self._file_lock(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)

                if not self._validate_counter_data(data):
                    raise ValueError("Invalid counter data structure")

                return data.get(self.COUNTER_KEY, self._default_counter_structure())

            except (json.JSONDecodeError, ValueError):
                # Try backup once (only if _retry < 1)
                if _retry < 1:
                    backup_path = path.with_suffix(path.suffix + '.bak')
                    if backup_path.exists():
                        self._restore_from_backup(path)
                        return self.load_counters(_retry=_retry + 1)  # Increment counter

                return self._default_counter_structure()

    def _atomic_write(self, path: Path, data: dict) -> None:
        """
        Write JSON atomically with backup to prevent corruption.

        Process:
        1. Create backup if file exists
        2. Write to temp file in same directory
        3. Flush and fsync to ensure disk write
        4. Atomic rename temp -> target
        5. Cleanup temp file on failure

        Args:
            path: Target file path
            data: Dictionary to write as JSON

        Raises:
            OSError: If disk full or permission denied
            IOError: If write fails
        """
        # Create backup before overwrite
        if path.exists():
            self._create_backup(path)

        # Write to temp file in same directory (atomic rename requirement)
        temp_fd, temp_path = tempfile.mkstemp(
            dir=path.parent,
            prefix='.tmp_',
            suffix='.json'
        )

        try:
            with os.fdopen(temp_fd, 'w') as f:
                # Pretty-print for human readability (sort keys for consistent diffs)
                json.dump(data, f, indent=2, sort_keys=True)
                f.flush()
                os.fsync(f.fileno())  # Force disk write

            # Atomic rename (POSIX guarantees atomicity)
            os.replace(temp_path, path)

        except Exception:
            # Cleanup temp file on failure
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    def _create_backup(self, path: Path) -> None:
        """
        Create .bak file before overwriting.

        Args:
            path: File to backup
        """
        if not path.exists():
            return

        backup_path = path.with_suffix(path.suffix + '.bak')
        shutil.copy2(path, backup_path)

    def _restore_from_backup(self, path: Path) -> None:
        """
        Restore file from .bak backup.

        Args:
            path: File to restore

        Raises:
            FileNotFoundError: If backup doesn't exist
        """
        backup_path = path.with_suffix(path.suffix + '.bak')

        if not backup_path.exists():
            raise FileNotFoundError(f"No backup found: {backup_path}")

        shutil.copy2(backup_path, path)

    @contextmanager
    def _file_lock(self, path: Path):
        """
        File locking context manager for concurrent access protection.

        Uses fcntl (Unix/Linux/macOS) with .lock file alongside target.
        Blocks until lock acquired (no timeout per architectural review #2).

        Args:
            path: File to lock

        Yields:
            None (context manager for use with 'with' statement)

        Example:
            >>> with persistence._file_lock(path):
            ...     # File operations here are protected
            ...     pass
        """
        lock_path = path.with_suffix(path.suffix + '.lock')
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        with open(lock_path, 'w') as lock_file:
            try:
                # Acquire exclusive lock (blocks until available)
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                yield
            finally:
                # Release lock
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _wrap_data(self, key: str, value: dict) -> dict:
        """
        Wrap data in standard JSON envelope with version and timestamp.

        DRY helper (addresses architectural review feedback #4).

        Args:
            key: Data key ("mappings" or "counters")
            value: Data payload

        Returns:
            Wrapped dictionary with version and updated timestamp
        """
        return {
            self.VERSION_KEY: self.VERSION,
            self.UPDATED_KEY: datetime.now(timezone.utc).isoformat(),
            key: value
        }

    def _validate_mapping_data(self, data: dict) -> bool:
        """
        Validate mapping file structure.

        Args:
            data: Loaded JSON data

        Returns:
            True if valid, False otherwise
        """
        # Check required top-level keys
        required_keys = [self.VERSION_KEY, self.UPDATED_KEY, self.MAPPING_KEY]
        if not all(k in data for k in required_keys):
            return False

        # Validate version
        if data[self.VERSION_KEY] != self.VERSION:
            return False

        # Validate mappings structure
        mappings = data[self.MAPPING_KEY]
        if not isinstance(mappings, dict):
            return False

        # Validate each mapping
        for internal_id, external_ids in mappings.items():
            if not isinstance(external_ids, dict):
                return False
            # Each external ID should be a string
            for tool, ext_id in external_ids.items():
                if not isinstance(ext_id, str):
                    return False

        return True

    def _validate_counter_data(self, data: dict) -> bool:
        """
        Validate counter file structure.

        Args:
            data: Loaded JSON data

        Returns:
            True if valid, False otherwise
        """
        # Check required top-level keys
        required_keys = [self.VERSION_KEY, self.UPDATED_KEY, self.COUNTER_KEY]
        if not all(k in data for k in required_keys):
            return False

        # Validate version
        if data[self.VERSION_KEY] != self.VERSION:
            return False

        # Validate counters structure
        counters = data[self.COUNTER_KEY]
        if not isinstance(counters, dict):
            return False

        # Validate each counter (can be int or dict of ints)
        for tool, counter in counters.items():
            if isinstance(counter, int):
                # Global counter (azure_devops, github)
                continue
            elif isinstance(counter, dict):
                # Keyed counter (jira, linear)
                for key, value in counter.items():
                    if not isinstance(value, int):
                        return False
            else:
                return False

        return True

    def _default_counter_structure(self) -> Dict[str, Union[int, Dict[str, int]]]:
        """
        Get default counter structure matching ExternalIDMapper.

        Returns:
            Default counter dictionary
        """
        return {
            "jira": {},
            "azure_devops": 0,
            "linear": {},
            "github": 0
        }


# Module-level convenience function
def get_persistence(state_dir: Path = None) -> ExternalIDPersistence:
    """
    Get persistence instance (convenience function).

    Args:
        state_dir: Optional custom state directory

    Returns:
        ExternalIDPersistence instance

    Example:
        >>> from lib.external_id_persistence import get_persistence
        >>> persistence = get_persistence()
        >>> persistence.save_mappings({...})
    """
    return ExternalIDPersistence(state_dir)
