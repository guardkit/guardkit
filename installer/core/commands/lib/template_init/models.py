"""
Data models for template-init command
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class GreenfieldTemplate:
    """Generated template from greenfield Q&A session

    Attributes:
        name: Template name (e.g., "mycompany-dotnet-template")
        manifest: Template manifest.json content
        settings: Template settings.json content
        claude_md: Template CLAUDE.md content
        project_structure: Dictionary describing folder/file structure
        code_templates: Dictionary of template files {filename: content}
        inferred_analysis: CodebaseAnalysis for agent generation
    """

    name: str
    manifest: Dict[str, Any]
    settings: Dict[str, Any]
    claude_md: str
    project_structure: Dict[str, Any]
    code_templates: Dict[str, str]
    inferred_analysis: Any  # CodebaseAnalysis from lib.codebase_analyzer

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "manifest": self.manifest,
            "settings": self.settings,
            "claude_md": self.claude_md,
            "project_structure": self.project_structure,
            "code_templates": self.code_templates,
            # inferred_analysis not serialized directly
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], inferred_analysis: Any = None) -> "GreenfieldTemplate":
        """Create from dictionary (for deserialization)"""
        return cls(
            name=data["name"],
            manifest=data["manifest"],
            settings=data["settings"],
            claude_md=data["claude_md"],
            project_structure=data["project_structure"],
            code_templates=data["code_templates"],
            inferred_analysis=inferred_analysis,
        )
