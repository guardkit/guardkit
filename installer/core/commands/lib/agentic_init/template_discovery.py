"""Template discovery for agentic-init command.

This module provides functionality to discover templates from both personal and repository
locations, with personal templates taking precedence.

Personal templates: ~/.agentecflow/templates/ (user-created with /template-create or /template-init)
Repository templates: installer/core/templates/ (built-in, distributed with system)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import json


@dataclass
class TemplateInfo:
    """Template information."""

    name: str
    version: str
    source: str  # "personal" or "repository"
    source_path: Path
    description: str
    language: str
    frameworks: List[str]
    architecture: str


class TemplateDiscovery:
    """Discover templates from personal and repository sources."""

    def __init__(
        self,
        personal_path: Optional[Path] = None,
        repo_path: Optional[Path] = None
    ):
        """
        Initialize template discovery.

        Args:
            personal_path: Path to personal templates (default: ~/.agentecflow/templates)
            repo_path: Path to repository templates (default: installer/core/templates)
        """
        self.personal_path = personal_path or Path.home() / ".agentecflow/templates"
        self.repo_path = repo_path or Path("installer/core/templates")

    def discover(self) -> List[TemplateInfo]:
        """
        Discover all available templates.

        Returns:
            List of templates (personal first, then repository)
        """
        print("�� Discovering templates...")

        templates = []

        # 1. Discover personal templates (PRIORITY)
        personal_templates = self._scan_directory(self.personal_path, source="personal")
        if personal_templates:
            print(f"  ✓ Found {len(personal_templates)} personal template(s)")
            templates.extend(personal_templates)

        # 2. Discover repository templates
        repo_templates = self._scan_directory(self.repo_path, source="repository")
        if repo_templates:
            print(f"  ✓ Found {len(repo_templates)} repository template(s)")

        # 3. Merge with priority (personal overrides repository)
        templates.extend(self._filter_duplicates(repo_templates, templates))

        if not templates:
            print("  ⚠️  No templates found")
            return []

        print(f"\n📊 Total: {len(templates)} available template(s)")

        return templates

    def _scan_directory(
        self,
        directory: Path,
        source: str
    ) -> List[TemplateInfo]:
        """
        Scan directory for templates.

        Args:
            directory: Directory to scan
            source: "personal" or "repository"

        Returns:
            List of discovered templates
        """
        if not directory.exists():
            return []

        templates = []

        # Each subdirectory is a template
        for template_dir in directory.iterdir():
            if not template_dir.is_dir():
                continue

            # Check for manifest.json
            manifest_file = template_dir / "manifest.json"
            if not manifest_file.exists():
                continue

            try:
                # Parse manifest
                template = self._parse_manifest(manifest_file, source)
                if template:
                    templates.append(template)
            except Exception as e:
                print(f"  ⚠️  Failed to parse {template_dir.name}: {e}")
                continue

        return templates

    def _parse_manifest(
        self,
        manifest_file: Path,
        source: str
    ) -> Optional[TemplateInfo]:
        """
        Parse template manifest.json.

        Args:
            manifest_file: Path to manifest.json
            source: "personal" or "repository"

        Returns:
            TemplateInfo if valid, None otherwise
        """
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)

        # Required fields
        name = manifest.get("name")
        version = manifest.get("version", "1.0.0")

        if not name:
            return None

        # Optional fields
        description = manifest.get("description", "")
        language = manifest.get("language", "")
        frameworks = manifest.get("frameworks", [])
        architecture = manifest.get("architecture", "")

        return TemplateInfo(
            name=name,
            version=version,
            source=source,
            source_path=manifest_file.parent,
            description=description,
            language=language,
            frameworks=frameworks,
            architecture=architecture
        )

    def _filter_duplicates(
        self,
        repo_templates: List[TemplateInfo],
        personal_templates: List[TemplateInfo]
    ) -> List[TemplateInfo]:
        """
        Filter repository templates that are overridden by personal templates.

        Args:
            repo_templates: Templates from repository directory
            personal_templates: Templates from personal directory (priority)

        Returns:
            Repository templates not overridden by personal
        """
        personal_names = {t.name for t in personal_templates}

        filtered = []
        for template in repo_templates:
            if template.name in personal_names:
                print(f"  ℹ️  Skipping repository '{template.name}' (personal version exists)")
            else:
                filtered.append(template)

        return filtered

    def find_by_name(self, templates: List[TemplateInfo], name: str) -> Optional[TemplateInfo]:
        """
        Find template by name.

        Args:
            templates: List of templates
            name: Template name to find

        Returns:
            TemplateInfo if found, None otherwise
        """
        for template in templates:
            if template.name == name:
                return template
        return None


def discover_templates() -> List[TemplateInfo]:
    """
    Convenience function to discover templates.

    Returns:
        List of available templates
    """
    discovery = TemplateDiscovery()
    return discovery.discover()
