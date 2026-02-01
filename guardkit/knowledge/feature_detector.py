"""
FeatureDetector - Detects feature specs from IDs and descriptions.

This module provides functionality to:
- Extract feature IDs from text descriptions
- Find feature specification files by feature ID
- Find related features with the same prefix

Part of TASK-GR3-001: Implement FeatureDetector class
"""

import re
from pathlib import Path
from typing import Optional, List


class FeatureDetector:
    """Detects feature specs from IDs and descriptions.

    The FeatureDetector provides methods to extract feature IDs from text,
    locate feature specification files, and find related features based
    on shared prefixes.

    Attributes:
        FEATURE_ID_PATTERN: Compiled regex for matching feature IDs (FEAT-XX-NNN format)
        DEFAULT_FEATURE_PATHS: List of directories to search for feature specs
        project_root: Path to the project root directory

    Example:
        detector = FeatureDetector(project_root=Path("/path/to/project"))

        # Extract feature ID from description
        feature_id = detector.detect_feature_id("Implement FEAT-GR-001 for graphiti")
        # Returns: "FEAT-GR-001"

        # Find feature spec file
        spec_path = detector.find_feature_spec("FEAT-GR-001")
        # Returns: Path to the spec file or None

        # Find related features
        related = detector.find_related_features("FEAT-GR-001")
        # Returns: List of paths to related feature specs
    """

    FEATURE_ID_PATTERN = re.compile(r'FEAT-[A-Z0-9]+-\d+')
    DEFAULT_FEATURE_PATHS = [
        "docs/features",
        ".guardkit/features",
        "features"
    ]

    def __init__(self, project_root: Path):
        """Initialize the FeatureDetector.

        Args:
            project_root: Path to the project root directory.
                Must be a Path object, not None.

        Raises:
            TypeError: If project_root is None
        """
        if project_root is None:
            raise TypeError("project_root cannot be None")
        self.project_root = project_root

    def detect_feature_id(self, description: str) -> Optional[str]:
        """Extract feature ID from description.

        Searches the description for a feature ID matching the pattern
        FEAT-XX-NNN where XX is an alphanumeric prefix and NNN is a number.

        Args:
            description: Text that may contain a feature ID

        Returns:
            The first matching feature ID if found, None otherwise

        Example:
            detector.detect_feature_id("Implement FEAT-GR-001 for graphiti")
            # Returns: "FEAT-GR-001"

            detector.detect_feature_id("No feature ID here")
            # Returns: None
        """
        match = self.FEATURE_ID_PATTERN.search(description)
        return match.group(0) if match else None

    def find_feature_spec(self, feature_id: str) -> Optional[Path]:
        """Find feature spec file for given ID.

        Searches through the default feature paths for a markdown file
        containing the feature ID in its filename.

        Args:
            feature_id: The feature ID to search for (e.g., "FEAT-GR-001")

        Returns:
            Path to the feature spec file if found, None otherwise

        Example:
            detector.find_feature_spec("FEAT-GR-003")
            # Returns: Path("docs/features/FEAT-GR-003-graphiti-enhanced-context.md")
        """
        for search_path in self.DEFAULT_FEATURE_PATHS:
            feature_dir = self.project_root / search_path
            if not feature_dir.exists():
                continue
            for file_path in feature_dir.glob("*.md"):
                if feature_id in file_path.name:
                    return file_path
        return None

    def find_related_features(self, feature_id: str) -> List[Path]:
        """Find features that might be related (same prefix).

        Searches for feature specs that share the same prefix as the
        given feature ID. For example, FEAT-GR-001, FEAT-GR-002, and
        FEAT-GR-003 all share the prefix "FEAT-GR".

        Args:
            feature_id: The feature ID to find relatives for

        Returns:
            List of paths to related feature specs (excluding self)

        Example:
            detector.find_related_features("FEAT-GR-003")
            # Returns: [Path("FEAT-GR-001-...md"), Path("FEAT-GR-002-...md")]
        """
        parts = feature_id.split('-')
        if len(parts) < 2:
            return []

        prefix = '-'.join(parts[:2])

        related = []
        for search_path in self.DEFAULT_FEATURE_PATHS:
            feature_dir = self.project_root / search_path
            if not feature_dir.exists():
                continue
            for file_path in feature_dir.glob(f"{prefix}*.md"):
                if feature_id not in file_path.name:  # Exclude self
                    related.append(file_path)
        return related
