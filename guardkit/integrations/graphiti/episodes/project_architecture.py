"""ProjectArchitectureEpisode dataclass for capturing system architecture patterns.

This schema prevents "architectural drift" by maintaining consistent
architecture context in the Graphiti knowledge graph.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ProjectArchitectureEpisode:
    """Project architecture patterns episode schema.

    Captures system architecture patterns including style, layers,
    modules, design patterns, and conventions. This information
    helps maintain architectural consistency across the project.

    Attributes:
        entity_type: The entity type identifier (always "project_architecture")
        architecture_style: Architecture style (e.g., "layered", "clean", "hexagonal", "microservices")
        pattern_description: Natural language description of the architecture pattern
        layers: List of architectural layers (e.g., ["domain", "application", "infrastructure"])
        key_modules: List of key modules in the system
        design_patterns: List of design patterns used (e.g., ["repository", "factory"])
        conventions: List of coding conventions
        directory_structure: Brief description of directory organization
        naming_conventions: Description of naming conventions used

    Example:
        >>> episode = ProjectArchitectureEpisode(
        ...     architecture_style="clean",
        ...     layers=["domain", "application", "infrastructure"],
        ...     design_patterns=["repository", "factory"],
        ... )
        >>> episode.get_entity_id()
        'project_architecture_main'
    """

    entity_type: str = "project_architecture"

    # Architecture style
    architecture_style: str = ""  # "layered", "clean", "hexagonal", "microservices"
    pattern_description: str = ""

    # Layers/modules
    layers: List[str] = field(default_factory=list)  # ["domain", "application", "infrastructure"]
    key_modules: List[str] = field(default_factory=list)

    # Patterns used
    design_patterns: List[str] = field(default_factory=list)
    conventions: List[str] = field(default_factory=list)

    # File organization
    directory_structure: str = ""  # Brief description
    naming_conventions: str = ""

    def to_episode_content(self) -> str:
        """Convert to natural language content for Graphiti.

        Returns:
            A formatted string containing all architecture information
            suitable for storage as an episode in Graphiti.
        """
        # Build layers section
        layers_section = ""
        if self.layers:
            layers_section = "\n".join(f"- {layer}" for layer in self.layers)
        else:
            layers_section = "- (none specified)"

        # Build key modules section
        modules_section = ""
        if self.key_modules:
            modules_section = "\n".join(f"- {module}" for module in self.key_modules)
        else:
            modules_section = "- (none specified)"

        # Build design patterns section
        patterns_section = ""
        if self.design_patterns:
            patterns_section = "\n".join(f"- {pattern}" for pattern in self.design_patterns)
        else:
            patterns_section = "- (none specified)"

        # Build conventions section
        conventions_section = ""
        if self.conventions:
            conventions_section = "\n".join(f"- {convention}" for convention in self.conventions)
        else:
            conventions_section = "- (none specified)"

        return f"""
Architecture Style: {self.architecture_style}

Description: {self.pattern_description}

Layers:
{layers_section}

Key Modules:
{modules_section}

Design Patterns:
{patterns_section}

Conventions:
{conventions_section}

Directory Structure: {self.directory_structure}

Naming Conventions: {self.naming_conventions}
"""

    def get_entity_id(self) -> str:
        """Get stable entity ID for upsert operations.

        Returns:
            A stable, predictable entity ID that allows Graphiti
            to update existing episodes rather than creating duplicates.
        """
        return "project_architecture_main"
