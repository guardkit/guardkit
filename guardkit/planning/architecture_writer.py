"""
Architecture Markdown Writer with Jinja2 Templates.

This module provides the ArchitectureWriter class for generating comprehensive
architecture documentation from system-plan entities. Outputs markdown files
with mermaid diagrams following C4 model conventions.

Public API:
    ArchitectureWriter: Main writer class with write_all() method

Example:
    from guardkit.planning.architecture_writer import ArchitectureWriter
    from guardkit.knowledge.entities import (
        SystemContextDef,
        ComponentDef,
        CrosscuttingConcernDef,
        ArchitectureDecision,
    )

    writer = ArchitectureWriter()
    writer.write_all(
        output_dir="docs/architecture",
        system=system_context,
        components=[comp1, comp2],
        concerns=[concern1],
        decisions=[adr1, adr2],
    )
"""

from datetime import datetime
from pathlib import Path
from typing import List, Union

from jinja2 import Environment, PackageLoader, select_autoescape

from guardkit.knowledge.entities.architecture_context import ArchitectureDecision
from guardkit.knowledge.entities.component import ComponentDef
from guardkit.knowledge.entities.crosscutting import CrosscuttingConcernDef
from guardkit.knowledge.entities.system_context import SystemContextDef


class ArchitectureWriter:
    """Generates architecture documentation from system-plan entities.

    Uses Jinja2 templates to render markdown documentation with mermaid diagrams.
    Supports methodology-aware output (DDD vs non-DDD).

    Attributes:
        env: Jinja2 environment for template loading

    Example:
        writer = ArchitectureWriter()
        writer.write_all(
            output_dir="docs/architecture",
            system=system_context,
            components=[order_mgmt, inventory],
            concerns=[observability],
            decisions=[adr1],
        )
    """

    def __init__(self):
        """Initialize ArchitectureWriter with Jinja2 environment."""
        self.env = Environment(
            loader=PackageLoader("guardkit", "templates"),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def write_all(
        self,
        output_dir: Union[str, Path],
        system: SystemContextDef,
        components: List[ComponentDef],
        concerns: List[CrosscuttingConcernDef],
        decisions: List[ArchitectureDecision],
    ) -> None:
        """Write all architecture documentation files.

        Creates the following structure:
        - output_dir/ARCHITECTURE.md (index)
        - output_dir/system-context.md
        - output_dir/bounded-contexts.md (DDD) or components.md (non-DDD)
        - output_dir/crosscutting-concerns.md
        - output_dir/decisions/ADR-SP-XXX.md (one per decision)

        Args:
            output_dir: Directory to write files to (created if not exists)
            system: System context definition
            components: List of component definitions
            concerns: List of crosscutting concerns
            decisions: List of architecture decisions

        Example:
            writer.write_all(
                output_dir="docs/architecture",
                system=sys_ctx,
                components=[comp1, comp2],
                concerns=[concern1],
                decisions=[adr1, adr2],
            )
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Create decisions subdirectory
        decisions_path = output_path / "decisions"
        decisions_path.mkdir(parents=True, exist_ok=True)

        # Current date for header
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Determine component filename based on methodology
        is_ddd = system.methodology.lower() == "ddd"
        component_filename = "bounded-contexts.md" if is_ddd else "components.md"

        # Render and write system context
        self._write_system_context(output_path, system, current_date)

        # Render and write components
        self._write_components(
            output_path, components, system.methodology, component_filename, current_date
        )

        # Render and write crosscutting concerns
        self._write_crosscutting_concerns(output_path, concerns, current_date)

        # Render and write ADRs
        self._write_adrs(decisions_path, decisions, current_date)

        # Render and write architecture index
        self._write_architecture_index(
            output_path, system, components, concerns, decisions, component_filename, current_date
        )

    def _write_system_context(
        self, output_path: Path, system: SystemContextDef, date: str
    ) -> None:
        """Write system-context.md file."""
        template = self.env.get_template("system-context.md.j2")
        content = template.render(system=system, date=date)
        (output_path / "system-context.md").write_text(content)

    def _write_components(
        self,
        output_path: Path,
        components: List[ComponentDef],
        methodology: str,
        filename: str,
        date: str,
    ) -> None:
        """Write components/bounded-contexts file."""
        template = self.env.get_template("components.md.j2")
        is_ddd = methodology.lower() == "ddd"
        content = template.render(
            components=components,
            is_ddd=is_ddd,
            methodology=methodology,
            date=date,
        )
        (output_path / filename).write_text(content)

    def _write_crosscutting_concerns(
        self, output_path: Path, concerns: List[CrosscuttingConcernDef], date: str
    ) -> None:
        """Write crosscutting-concerns.md file."""
        template = self.env.get_template("crosscutting.md.j2")
        content = template.render(concerns=concerns, date=date)
        (output_path / "crosscutting-concerns.md").write_text(content)

    def _write_adrs(
        self, decisions_path: Path, decisions: List[ArchitectureDecision], date: str
    ) -> None:
        """Write individual ADR files in decisions/ subdirectory."""
        template = self.env.get_template("adr.md.j2")
        for adr in decisions:
            content = template.render(adr=adr, date=date)
            filename = f"{adr.entity_id}.md"
            (decisions_path / filename).write_text(content)

    def _write_architecture_index(
        self,
        output_path: Path,
        system: SystemContextDef,
        components: List[ComponentDef],
        concerns: List[CrosscuttingConcernDef],
        decisions: List[ArchitectureDecision],
        component_filename: str,
        date: str,
    ) -> None:
        """Write ARCHITECTURE.md index file."""
        template = self.env.get_template("architecture-index.md.j2")
        content = template.render(
            system=system,
            components=components,
            concerns=concerns,
            decisions=decisions,
            component_filename=component_filename,
            date=date,
        )
        (output_path / "ARCHITECTURE.md").write_text(content)
