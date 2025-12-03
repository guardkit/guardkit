"""Shared constants for GuardKit."""

from pathlib import Path
from typing import List


class RequireKitConfig:
    """RequireKit integration configuration."""

    MARKER_PRIMARY = "require-kit.marker.json"
    MARKER_LEGACY = "require-kit.marker"
    INSTALL_DIR = ".agentecflow"

    @classmethod
    def marker_paths(cls, base_path: Path = None) -> List[Path]:
        """
        Get paths to check for RequireKit marker files.

        Args:
            base_path: Base directory to search in. Defaults to ~/.agentecflow

        Returns:
            List of marker file paths to check, in priority order
        """
        base = base_path or Path.home() / cls.INSTALL_DIR
        return [base / cls.MARKER_PRIMARY, base / cls.MARKER_LEGACY]
