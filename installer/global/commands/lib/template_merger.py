"""
Template Update/Merge Functionality

Handles template updates when name conflicts occur:
- Detects existing template by name
- Prompts user (Overwrite/Merge/Cancel)
- Implements merge logic (preserves customizations)
- Updates version number
- Adds changelog entry

TASK-012: Template Packaging & Distribution (Sub-task 3: TASK-063)
"""

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Set


class MergeStrategy(Enum):
    """Merge strategy options."""

    OVERWRITE = "overwrite"
    MERGE = "merge"
    CANCEL = "cancel"


@dataclass
class MergeResult:
    """Result of merge operation."""

    success: bool
    strategy: MergeStrategy
    new_version: Optional[str] = None
    files_added: List[str] = field(default_factory=list)
    files_updated: List[str] = field(default_factory=list)
    files_preserved: List[str] = field(default_factory=list)
    custom_agents_preserved: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "strategy": self.strategy.value,
            "new_version": self.new_version,
            "files_added": self.files_added,
            "files_updated": self.files_updated,
            "files_preserved": self.files_preserved,
            "custom_agents_preserved": self.custom_agents_preserved,
            "errors": self.errors,
            "warnings": self.warnings
        }


class TemplateMerger:
    """
    Handles template updates and merging with conflict resolution.

    Features:
    - Detects existing templates by name
    - Interactive user prompts for conflict resolution
    - Smart merge logic that preserves custom agents
    - Automatic version bumping on merge
    - Changelog updates with merge details

    Example:
        merger = TemplateMerger(
            existing_path=Path("templates/my-template"),
            new_path=Path("updates/my-template")
        )

        # Interactive prompt
        result = merger.merge_interactive()

        # Or programmatic
        result = merger.merge(strategy=MergeStrategy.MERGE)
    """

    def __init__(
        self,
        existing_path: Path,
        new_path: Path,
        backup_dir: Optional[Path] = None
    ):
        """
        Initialize merger.

        Args:
            existing_path: Path to existing template directory
            new_path: Path to new/updated template directory
            backup_dir: Optional backup directory (default: existing_path.parent / "backups")
        """
        self.existing_path = existing_path
        self.new_path = new_path
        self.backup_dir = backup_dir or (existing_path.parent / "backups")

        if not existing_path.exists():
            raise FileNotFoundError(f"Existing template not found: {existing_path}")

        if not new_path.exists():
            raise FileNotFoundError(f"New template not found: {new_path}")

    def detect_conflict(self) -> bool:
        """
        Check if templates have the same name (conflict).

        Returns:
            True if names match (conflict exists)
        """
        existing_manifest = self._load_manifest(self.existing_path)
        new_manifest = self._load_manifest(self.new_path)

        existing_name = existing_manifest.get("template", {}).get("name", "")
        new_name = new_manifest.get("template", {}).get("name", "")

        return existing_name == new_name and existing_name != ""

    def merge_interactive(self) -> MergeResult:
        """
        Interactive merge with user prompt.

        Returns:
            MergeResult with operation details
        """
        # Show comparison
        comparison = self.compare_templates()

        print("\n" + "=" * 60)
        print("Template Update Detected")
        print("=" * 60)

        existing_manifest = self._load_manifest(self.existing_path)
        new_manifest = self._load_manifest(self.new_path)

        existing_version = existing_manifest.get("template", {}).get("version", "unknown")
        new_version = new_manifest.get("template", {}).get("version", "unknown")

        print(f"\nExisting: {self.existing_path.name} (v{existing_version})")
        print(f"New:      {self.new_path.name} (v{new_version})")

        print(f"\nChanges detected:")
        print(f"  Files to add:    {len(comparison['files_to_add'])}")
        print(f"  Files to update: {len(comparison['files_to_update'])}")
        print(f"  Custom agents:   {len(comparison['custom_agents'])}")

        if comparison['custom_agents']:
            print(f"\n  Custom agents found (will be preserved):")
            for agent in comparison['custom_agents'][:5]:
                print(f"    - {agent}")
            if len(comparison['custom_agents']) > 5:
                print(f"    ... and {len(comparison['custom_agents']) - 5} more")

        print("\nOptions:")
        print("  [O] Overwrite - Replace all files (custom agents will be lost)")
        print("  [M] Merge     - Update files, preserve custom agents (recommended)")
        print("  [C] Cancel    - Do nothing")

        while True:
            choice = input("\nYour choice (O/M/C): ").strip().upper()

            if choice == "O":
                return self.merge(MergeStrategy.OVERWRITE)
            elif choice == "M":
                return self.merge(MergeStrategy.MERGE)
            elif choice == "C":
                return MergeResult(success=False, strategy=MergeStrategy.CANCEL)
            else:
                print("Invalid choice. Please enter O, M, or C.")

    def merge(self, strategy: MergeStrategy) -> MergeResult:
        """
        Execute merge with specified strategy.

        Args:
            strategy: Merge strategy to use

        Returns:
            MergeResult with operation details
        """
        if strategy == MergeStrategy.CANCEL:
            return MergeResult(success=False, strategy=strategy)

        # Create backup
        backup_path = self._create_backup()

        try:
            if strategy == MergeStrategy.OVERWRITE:
                result = self._merge_overwrite()
            else:  # MERGE
                result = self._merge_smart()

            result.success = True
            return result

        except Exception as e:
            # Restore from backup on error
            self._restore_backup(backup_path)
            return MergeResult(
                success=False,
                strategy=strategy,
                errors=[f"Merge failed: {e}"]
            )

    def compare_templates(self) -> Dict[str, Any]:
        """
        Compare existing and new templates.

        Returns:
            Dictionary with comparison results
        """
        existing_files = self._get_file_list(self.existing_path)
        new_files = self._get_file_list(self.new_path)

        files_to_add = new_files - existing_files
        files_to_update = existing_files & new_files
        files_only_in_existing = existing_files - new_files

        # Identify custom agents
        custom_agents = self._identify_custom_agents()

        return {
            "files_to_add": sorted(list(files_to_add)),
            "files_to_update": sorted(list(files_to_update)),
            "files_only_in_existing": sorted(list(files_only_in_existing)),
            "custom_agents": sorted(list(custom_agents))
        }

    def _merge_overwrite(self) -> MergeResult:
        """
        Overwrite existing template with new template.

        Returns:
            MergeResult
        """
        # Remove existing directory
        shutil.rmtree(self.existing_path)

        # Copy new directory
        shutil.copytree(self.new_path, self.existing_path)

        # Get file list
        files = self._get_file_list(self.existing_path)

        return MergeResult(
            success=True,
            strategy=MergeStrategy.OVERWRITE,
            files_updated=sorted(list(files))
        )

    def _merge_smart(self) -> MergeResult:
        """
        Smart merge: update files, preserve custom agents.

        Returns:
            MergeResult
        """
        result = MergeResult(success=True, strategy=MergeStrategy.MERGE)

        # Get custom agents before merge
        custom_agents = self._identify_custom_agents()

        # Save existing version info before overwriting manifest
        existing_manifest = self._load_manifest(self.existing_path)
        existing_version = existing_manifest.get("template", {}).get("version")
        existing_changelog = existing_manifest.get("changelog", [])

        # Copy custom agents to temporary location
        temp_agents_dir = self.backup_dir / "temp_agents"
        temp_agents_dir.mkdir(parents=True, exist_ok=True)

        custom_agent_paths = {}
        for agent_name in custom_agents:
            agent_path = self.existing_path / "agents" / agent_name
            if agent_path.exists():
                temp_path = temp_agents_dir / agent_name
                shutil.copy2(agent_path, temp_path)
                custom_agent_paths[agent_name] = temp_path

        # Update files from new template
        comparison = self.compare_templates()

        for file_rel_path in comparison['files_to_add']:
            src = self.new_path / file_rel_path
            dst = self.existing_path / file_rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            result.files_added.append(file_rel_path)

        for file_rel_path in comparison['files_to_update']:
            # Skip custom agents (will be preserved)
            if file_rel_path.startswith("agents/") and Path(file_rel_path).name in custom_agents:
                result.files_preserved.append(file_rel_path)
                continue

            # Skip manifest.json (will be handled specially)
            if file_rel_path == "manifest.json":
                result.files_preserved.append(file_rel_path)
                continue

            src = self.new_path / file_rel_path
            dst = self.existing_path / file_rel_path
            shutil.copy2(src, dst)
            result.files_updated.append(file_rel_path)

        # Restore custom agents
        for agent_name, temp_path in custom_agent_paths.items():
            dst = self.existing_path / "agents" / agent_name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(temp_path, dst)
            result.custom_agents_preserved.append(agent_name)

        # Restore existing version and changelog before bumping
        if existing_version:
            manifest = self._load_manifest(self.existing_path)
            manifest.setdefault("template", {})["version"] = existing_version
            if existing_changelog:
                manifest["changelog"] = existing_changelog
            self._save_manifest(manifest)

        # Bump version and update changelog
        from template_versioning import TemplateVersionManager

        version_manager = TemplateVersionManager(self.existing_path)

        try:
            changes = [
                f"Merged with new template version",
                f"Added {len(result.files_added)} new files",
                f"Updated {len(result.files_updated)} files",
                f"Preserved {len(result.custom_agents_preserved)} custom agents"
            ]

            new_version = version_manager.bump_version("minor", changes)
            result.new_version = new_version

        except Exception as e:
            result.warnings.append(f"Could not update version: {e}")

        return result

    def _identify_custom_agents(self) -> Set[str]:
        """
        Identify custom agents (agents in existing but not in new).

        Returns:
            Set of custom agent filenames
        """
        existing_agents_dir = self.existing_path / "agents"
        new_agents_dir = self.new_path / "agents"

        if not existing_agents_dir.exists():
            return set()

        existing_agents = {f.name for f in existing_agents_dir.glob("*.md")}

        if not new_agents_dir.exists():
            return existing_agents

        new_agents = {f.name for f in new_agents_dir.glob("*.md")}

        # Custom agents are those in existing but not in new
        custom_agents = existing_agents - new_agents

        return custom_agents

    def _get_file_list(self, template_path: Path) -> Set[str]:
        """
        Get list of all files in template (relative paths).

        Args:
            template_path: Path to template directory

        Returns:
            Set of relative file paths
        """
        files = set()

        for file_path in template_path.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(template_path)
                files.add(str(rel_path))

        return files

    def _create_backup(self) -> Path:
        """
        Create backup of existing template.

        Returns:
            Path to backup directory
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.existing_path.name}_backup_{timestamp}"
        backup_path = self.backup_dir / backup_name

        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.existing_path, backup_path)

        return backup_path

    def _restore_backup(self, backup_path: Path) -> None:
        """Restore from backup."""
        if backup_path.exists():
            shutil.rmtree(self.existing_path)
            shutil.copytree(backup_path, self.existing_path)

    def _load_manifest(self, template_path: Path) -> Dict[str, Any]:
        """Load manifest.json from template."""
        manifest_path = template_path / "manifest.json"

        if not manifest_path.exists():
            return {}

        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_manifest(self, manifest: Dict[str, Any]) -> None:
        """Save manifest.json to existing template."""
        manifest_path = self.existing_path / "manifest.json"

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)


def detect_existing_template(
    template_name: str,
    search_paths: Optional[List[Path]] = None
) -> Optional[Path]:
    """
    Detect existing template by name.

    Args:
        template_name: Template name to search for
        search_paths: Optional list of directories to search (default: standard locations)

    Returns:
        Path to existing template or None if not found
    """
    if search_paths is None:
        search_paths = [
            Path.home() / ".agentecflow" / "templates",
            Path(".claude") / "templates",
            Path("installer/local/templates")
        ]

    for search_path in search_paths:
        if not search_path.exists():
            continue

        template_path = search_path / template_name
        if template_path.exists() and template_path.is_dir():
            # Verify it's a template by checking for manifest.json
            if (template_path / "manifest.json").exists():
                return template_path

    return None


# Module exports
__all__ = [
    "TemplateMerger",
    "MergeStrategy",
    "MergeResult",
    "detect_existing_template",
]
