"""
Template Versioning System

Manages semantic versioning for templates with:
- Version field in manifest.json (major.minor.patch)
- Changelog tracking
- Template lineage (based_on field)
- Version comparison utilities

TASK-012: Template Packaging & Distribution (Sub-task 2: TASK-062)
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple


@dataclass
class SemanticVersion:
    """
    Semantic version (major.minor.patch).

    Follows semantic versioning specification: https://semver.org/
    """

    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        """Format as version string."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def __eq__(self, other: object) -> bool:
        """Check equality."""
        if not isinstance(other, SemanticVersion):
            return False
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __lt__(self, other: "SemanticVersion") -> bool:
        """Compare versions."""
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __le__(self, other: "SemanticVersion") -> bool:
        """Compare versions."""
        return self < other or self == other

    def __gt__(self, other: "SemanticVersion") -> bool:
        """Compare versions."""
        return not self <= other

    def __ge__(self, other: "SemanticVersion") -> bool:
        """Compare versions."""
        return not self < other

    @classmethod
    def parse(cls, version_string: str) -> "SemanticVersion":
        """
        Parse version string into SemanticVersion.

        Args:
            version_string: Version string like "1.2.3"

        Returns:
            SemanticVersion

        Raises:
            ValueError: If version string is invalid
        """
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version_string)
        if not match:
            raise ValueError(f"Invalid semantic version: {version_string}")

        major, minor, patch = match.groups()
        return cls(int(major), int(minor), int(patch))

    def bump_major(self) -> "SemanticVersion":
        """Create new version with bumped major number (resets minor and patch)."""
        return SemanticVersion(self.major + 1, 0, 0)

    def bump_minor(self) -> "SemanticVersion":
        """Create new version with bumped minor number (resets patch)."""
        return SemanticVersion(self.major, self.minor + 1, 0)

    def bump_patch(self) -> "SemanticVersion":
        """Create new version with bumped patch number."""
        return SemanticVersion(self.major, self.minor, self.patch + 1)


@dataclass
class ChangelogEntry:
    """Single changelog entry."""

    version: str
    date: str
    changes: List[str] = field(default_factory=list)
    author: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "version": self.version,
            "date": self.date,
            "changes": self.changes
        }
        if self.author:
            data["author"] = self.author
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChangelogEntry":
        """Create from dictionary."""
        return cls(
            version=data["version"],
            date=data["date"],
            changes=data.get("changes", []),
            author=data.get("author")
        )


@dataclass
class TemplateLineage:
    """Template lineage information (inheritance tracking)."""

    based_on: Optional[str] = None
    based_on_version: Optional[str] = None
    customizations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {}
        if self.based_on:
            data["based_on"] = self.based_on
        if self.based_on_version:
            data["based_on_version"] = self.based_on_version
        if self.customizations:
            data["customizations"] = self.customizations
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemplateLineage":
        """Create from dictionary."""
        return cls(
            based_on=data.get("based_on"),
            based_on_version=data.get("based_on_version"),
            customizations=data.get("customizations", [])
        )


class TemplateVersionManager:
    """
    Manages template versioning with semantic versioning and changelog tracking.

    Features:
    - Semantic versioning (major.minor.patch)
    - Changelog management with version history
    - Template lineage tracking (based_on field)
    - Version comparison and validation

    Example:
        manager = TemplateVersionManager(template_path=Path("templates/my-template"))
        manager.initialize_version("1.0.0", "Initial release")
        manager.bump_version("minor", "Added new agent")
        changelog = manager.get_changelog()
    """

    def __init__(self, template_path: Path):
        """
        Initialize version manager.

        Args:
            template_path: Path to template directory
        """
        self.template_path = template_path
        self.manifest_path = template_path / "manifest.json"

        if not template_path.exists():
            raise FileNotFoundError(f"Template path does not exist: {template_path}")

    def initialize_version(
        self,
        version: str = "1.0.0",
        initial_message: str = "Initial release",
        author: Optional[str] = None,
        based_on: Optional[str] = None,
        based_on_version: Optional[str] = None
    ) -> None:
        """
        Initialize versioning for template.

        Args:
            version: Initial version string (default: "1.0.0")
            initial_message: Changelog message for initial version
            author: Template author
            based_on: Parent template name (if derived from another)
            based_on_version: Parent template version
        """
        # Validate version format
        SemanticVersion.parse(version)

        # Load or create manifest
        manifest = self._load_manifest()

        # Add version to template section
        if "template" not in manifest:
            manifest["template"] = {}

        manifest["template"]["version"] = version

        # Initialize changelog
        if "changelog" not in manifest:
            manifest["changelog"] = []

        manifest["changelog"].insert(0, ChangelogEntry(
            version=version,
            date=datetime.utcnow().isoformat() + "Z",
            changes=[initial_message],
            author=author
        ).to_dict())

        # Add lineage if provided
        if based_on:
            manifest["lineage"] = TemplateLineage(
                based_on=based_on,
                based_on_version=based_on_version
            ).to_dict()

        self._save_manifest(manifest)

    def bump_version(
        self,
        bump_type: str,
        changes: List[str],
        author: Optional[str] = None
    ) -> str:
        """
        Bump version number and add changelog entry.

        Args:
            bump_type: Type of bump ("major", "minor", "patch")
            changes: List of changes for changelog
            author: Author of changes

        Returns:
            New version string

        Raises:
            ValueError: If bump_type is invalid or template not versioned
        """
        if bump_type not in ["major", "minor", "patch"]:
            raise ValueError(f"Invalid bump type: {bump_type}. Must be major, minor, or patch")

        manifest = self._load_manifest()

        # Get current version
        current_version_str = manifest.get("template", {}).get("version")
        if not current_version_str:
            raise ValueError("Template not versioned. Call initialize_version() first")

        current_version = SemanticVersion.parse(current_version_str)

        # Bump version
        if bump_type == "major":
            new_version = current_version.bump_major()
        elif bump_type == "minor":
            new_version = current_version.bump_minor()
        else:  # patch
            new_version = current_version.bump_patch()

        new_version_str = str(new_version)

        # Update manifest
        manifest["template"]["version"] = new_version_str
        manifest["template"]["last_updated"] = datetime.utcnow().isoformat()[:10]

        # Add changelog entry
        if "changelog" not in manifest:
            manifest["changelog"] = []

        manifest["changelog"].insert(0, ChangelogEntry(
            version=new_version_str,
            date=datetime.utcnow().isoformat() + "Z",
            changes=changes,
            author=author
        ).to_dict())

        self._save_manifest(manifest)

        return new_version_str

    def get_current_version(self) -> Optional[str]:
        """
        Get current version from manifest.

        Returns:
            Version string or None if not versioned
        """
        manifest = self._load_manifest()
        return manifest.get("template", {}).get("version")

    def get_changelog(self) -> List[ChangelogEntry]:
        """
        Get full changelog history.

        Returns:
            List of ChangelogEntry objects, newest first
        """
        manifest = self._load_manifest()
        changelog_data = manifest.get("changelog", [])

        return [ChangelogEntry.from_dict(entry) for entry in changelog_data]

    def get_lineage(self) -> Optional[TemplateLineage]:
        """
        Get template lineage information.

        Returns:
            TemplateLineage or None if not derived from another template
        """
        manifest = self._load_manifest()
        lineage_data = manifest.get("lineage")

        if not lineage_data:
            return None

        return TemplateLineage.from_dict(lineage_data)

    def update_lineage(
        self,
        customizations: Optional[List[str]] = None,
        append: bool = True
    ) -> None:
        """
        Update template lineage customizations.

        Args:
            customizations: List of customization descriptions
            append: Whether to append to existing customizations (default: True)
        """
        manifest = self._load_manifest()

        if "lineage" not in manifest:
            return

        lineage = TemplateLineage.from_dict(manifest["lineage"])

        if customizations:
            if append:
                lineage.customizations.extend(customizations)
            else:
                lineage.customizations = customizations

        manifest["lineage"] = lineage.to_dict()
        self._save_manifest(manifest)

    def compare_versions(self, version_a: str, version_b: str) -> Dict[str, Any]:
        """
        Compare two semantic versions.

        Args:
            version_a: First version string
            version_b: Second version string

        Returns:
            Dictionary with comparison results
        """
        ver_a = SemanticVersion.parse(version_a)
        ver_b = SemanticVersion.parse(version_b)

        return {
            "version_a": version_a,
            "version_b": version_b,
            "equal": ver_a == ver_b,
            "a_newer": ver_a > ver_b,
            "b_newer": ver_b > ver_a,
            "major_change": ver_a.major != ver_b.major,
            "minor_change": ver_a.minor != ver_b.minor,
            "patch_change": ver_a.patch != ver_b.patch
        }

    def validate_version_string(self, version: str) -> Tuple[bool, Optional[str]]:
        """
        Validate version string format.

        Args:
            version: Version string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            SemanticVersion.parse(version)
            return True, None
        except ValueError as e:
            return False, str(e)

    def _load_manifest(self) -> Dict[str, Any]:
        """Load manifest.json."""
        if not self.manifest_path.exists():
            return {}

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_manifest(self, manifest: Dict[str, Any]) -> None:
        """Save manifest.json."""
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)


# Module exports
__all__ = [
    "TemplateVersionManager",
    "SemanticVersion",
    "ChangelogEntry",
    "TemplateLineage",
]
