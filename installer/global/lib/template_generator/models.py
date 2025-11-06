"""
Pydantic Data Models for Template Generation

Provides structured data models for template files including CLAUDE.md content.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class TemplateClaude(BaseModel):
    """Generated CLAUDE.md structure

    Represents the complete structure of a CLAUDE.md file that will guide
    Claude Code when working with template-generated projects.
    """

    schema_version: str = Field(default="1.0.0", description="Data contract version")

    # Content sections (all in Markdown format)
    architecture_overview: str = Field(description="Markdown describing architecture patterns and layers")
    technology_stack: str = Field(description="Markdown describing technology stack and versions")
    project_structure: str = Field(description="Markdown describing folder structure with explanations")
    naming_conventions: str = Field(description="Markdown describing naming rules with examples")
    patterns: str = Field(description="Markdown describing patterns and best practices")
    examples: str = Field(description="Markdown with code examples demonstrating patterns")
    quality_standards: str = Field(description="Markdown with quality guidelines and testing requirements")
    agent_usage: str = Field(description="Markdown describing which agents to use when")

    # Metadata
    generated_at: str = Field(description="ISO 8601 timestamp")
    confidence_score: float = Field(ge=0.0, le=1.0, description="AI confidence (0.0-1.0)")

    def to_markdown(self) -> str:
        """Convert TemplateClaude to full CLAUDE.md content

        Returns:
            Complete CLAUDE.md file content in Markdown format
        """
        sections = [
            "# Claude Code Project Instructions",
            "",
            f"**Generated**: {self.generated_at}",
            f"**Confidence**: {self.confidence_score:.0%}",
            "",
            "---",
            "",
            self.architecture_overview,
            "",
            self.technology_stack,
            "",
            self.project_structure,
            "",
            self.naming_conventions,
            "",
            self.patterns,
            "",
            self.examples,
            "",
            self.quality_standards,
            "",
            self.agent_usage,
            "",
            "---",
            "",
            f"**Last Updated**: {self.generated_at}",
        ]
        return "\n".join(sections)
