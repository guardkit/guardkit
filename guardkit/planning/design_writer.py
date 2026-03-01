"""
Design Markdown Writer with Jinja2 Templates.

This module provides the DesignWriter class for generating design
documentation from /system-design entities. Outputs markdown files
for DDRs, API contracts, data models, and component diagrams.

Also provides the scan_next_ddr_number() helper function for DDR numbering.

Public API:
    DesignWriter: Main writer class for design artefacts
    scan_next_ddr_number: Helper to find next DDR number

Example:
    from guardkit.planning.design_writer import DesignWriter, scan_next_ddr_number
    from guardkit.knowledge.entities.design_decision import DesignDecision
    from guardkit.knowledge.entities.api_contract import ApiContract
    from guardkit.knowledge.entities.data_model import DataModel

    writer = DesignWriter()

    # Write a DDR
    writer.write_ddr(decision, Path("docs/design"))

    # Write an API contract
    writer.write_api_contract(contract, Path("docs/design"))

    # Write a data model
    writer.write_data_model(model, Path("docs/design"))

    # Write a component diagram
    writer.write_component_diagram("Order Management", components, Path("docs/design"))

    # Find next DDR number
    next_num = scan_next_ddr_number(Path("docs/design/decisions"))
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union

from jinja2 import Environment, PackageLoader, select_autoescape

from guardkit.knowledge.entities.design_decision import DesignDecision
from guardkit.knowledge.entities.api_contract import ApiContract
from guardkit.knowledge.entities.data_model import DataModel


def scan_next_ddr_number(decisions_dir: Path) -> int:
    """Scan decisions directory for the next available DDR number.

    Looks for files matching the pattern DDR-NNN.md and returns
    max(N) + 1. Returns 1 if no DDR files exist or the directory
    doesn't exist.

    Args:
        decisions_dir: Path to the decisions directory to scan.

    Returns:
        Next available DDR number (1-based).

    Example:
        # With DDR-001.md, DDR-002.md, DDR-003.md present:
        next_num = scan_next_ddr_number(Path("docs/design/decisions"))
        # Returns 4
    """
    if not decisions_dir.exists():
        return 1

    pattern = re.compile(r"^DDR-(\d{3})\.md$")
    max_number = 0

    for file_path in decisions_dir.iterdir():
        match = pattern.match(file_path.name)
        if match:
            number = int(match.group(1))
            if number > max_number:
                max_number = number

    return max_number + 1


def _slugify(name: str, max_length: int = 30) -> str:
    """Convert name to URL-safe slug.

    Args:
        name: The name to convert
        max_length: Maximum length of the slug (default 30)

    Returns:
        Lowercase, hyphenated slug truncated to max_length
    """
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    slug = re.sub(r'-+', '-', slug)
    return slug[:max_length]


class DesignWriter:
    """Generates design documentation from /system-design entities.

    Uses Jinja2 templates to render markdown documentation for
    DDRs, API contracts, data models, and component diagrams.

    Output directory structure:
        docs/design/
            decisions/    DDR-NNN.md files
            contracts/    API-{slug}.md files
            models/       DM-{slug}.md files
            diagrams/     Component diagram files

    Attributes:
        env: Jinja2 environment for template loading

    Example:
        writer = DesignWriter()
        writer.write_ddr(decision, Path("docs/design"))
        writer.write_api_contract(contract, Path("docs/design"))
        writer.write_data_model(model, Path("docs/design"))
        writer.write_component_diagram("Orders", components, Path("docs/design"))
    """

    def __init__(self) -> None:
        """Initialize DesignWriter with Jinja2 environment."""
        self.env = Environment(
            loader=PackageLoader("guardkit", "templates"),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def write_ddr(
        self,
        decision: DesignDecision,
        output_dir: Union[str, Path],
    ) -> None:
        """Write a Design Decision Record (DDR) markdown file.

        Renders the ddr.md.j2 template with the given decision and writes
        the output to output_dir/decisions/DDR-NNN.md.

        Creates the decisions/ subdirectory if it doesn't exist.

        Args:
            decision: DesignDecision instance to render.
            output_dir: Base output directory (e.g., docs/design/).

        Example:
            writer.write_ddr(decision, Path("docs/design"))
            # Creates: docs/design/decisions/DDR-001.md
        """
        output_path = Path(output_dir)
        decisions_path = output_path / "decisions"
        decisions_path.mkdir(parents=True, exist_ok=True)

        current_date = datetime.now().strftime("%Y-%m-%d")
        template = self.env.get_template("ddr.md.j2")
        content = template.render(decision=decision, date=current_date)

        filename = f"{decision.entity_id}.md"
        (decisions_path / filename).write_text(content)

    def write_api_contract(
        self,
        contract: ApiContract,
        output_dir: Union[str, Path],
    ) -> None:
        """Write an API contract markdown file.

        Renders the api-contract.md.j2 template with the given contract
        and writes the output to output_dir/contracts/API-{slug}.md.

        Creates the contracts/ subdirectory if it doesn't exist.

        Args:
            contract: ApiContract instance to render.
            output_dir: Base output directory (e.g., docs/design/).

        Example:
            writer.write_api_contract(contract, Path("docs/design"))
            # Creates: docs/design/contracts/API-order-management.md
        """
        output_path = Path(output_dir)
        contracts_path = output_path / "contracts"
        contracts_path.mkdir(parents=True, exist_ok=True)

        current_date = datetime.now().strftime("%Y-%m-%d")
        template = self.env.get_template("api-contract.md.j2")
        content = template.render(contract=contract, date=current_date)

        filename = f"{contract.entity_id}.md"
        (contracts_path / filename).write_text(content)

    def write_data_model(
        self,
        model: DataModel,
        output_dir: Union[str, Path],
    ) -> None:
        """Write a data model markdown file.

        Generates a markdown representation of the data model with
        entity definitions, their attributes, relationships, and invariants.
        Writes to output_dir/models/DM-{slug}.md.

        Creates the models/ subdirectory if it doesn't exist.

        Args:
            model: DataModel instance to render.
            output_dir: Base output directory (e.g., docs/design/).

        Example:
            writer.write_data_model(model, Path("docs/design"))
            # Creates: docs/design/models/DM-order-management.md
        """
        output_path = Path(output_dir)
        models_path = output_path / "models"
        models_path.mkdir(parents=True, exist_ok=True)

        current_date = datetime.now().strftime("%Y-%m-%d")

        lines: List[str] = []
        lines.append(f"# {model.entity_id}: {model.bounded_context} Data Model")
        lines.append("")
        lines.append(f"> Date: {current_date}")
        lines.append("")

        if model.entities:
            lines.append("## Entities")
            lines.append("")

            for entity in model.entities:
                entity_name = entity.get("name", "Unknown")
                lines.append(f"### {entity_name}")
                lines.append("")

                attributes = entity.get("attributes", [])
                if attributes:
                    lines.append("**Attributes:**")
                    lines.append("")
                    for attr in attributes:
                        lines.append(f"- `{attr}`")
                    lines.append("")

                relationships = entity.get("relationships", [])
                if relationships:
                    lines.append("**Relationships:**")
                    lines.append("")
                    for rel in relationships:
                        lines.append(f"- {rel}")
                    lines.append("")

        if model.invariants:
            lines.append("## Invariants")
            lines.append("")
            for invariant in model.invariants:
                lines.append(f"- {invariant}")
            lines.append("")

        content = "\n".join(lines)
        filename = f"{model.entity_id}.md"
        (models_path / filename).write_text(content)

    def write_component_diagram(
        self,
        container: str,
        components: List[Dict],
        output_dir: Union[str, Path],
    ) -> None:
        """Write a C4 Level 3 component diagram markdown file.

        Renders the component-l3.md.j2 template with the given container
        name and component list. Writes to output_dir/diagrams/{slug}.md.

        Creates the diagrams/ subdirectory if it doesn't exist.

        Args:
            container: Container/bounded context name for the diagram.
            components: List of dicts with 'name' and 'description' keys.
            output_dir: Base output directory (e.g., docs/design/).

        Example:
            writer.write_component_diagram(
                "Order Management",
                [{"name": "OrderService", "description": "Handles orders"}],
                Path("docs/design"),
            )
            # Creates: docs/design/diagrams/order-management.md
        """
        output_path = Path(output_dir)
        diagrams_path = output_path / "diagrams"
        diagrams_path.mkdir(parents=True, exist_ok=True)

        current_date = datetime.now().strftime("%Y-%m-%d")
        template = self.env.get_template("component-l3.md.j2")
        content = template.render(
            container=container,
            components=components,
            date=current_date,
        )

        slug = _slugify(container)
        filename = f"{slug}.md"
        (diagrams_path / filename).write_text(content)
