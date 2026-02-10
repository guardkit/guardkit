"""
Warnings Extractor for GuardKit Feature Planning.

Extracts warnings/constraints from ParsedSpec into a standalone markdown file
for Graphiti seeding. This allows warnings to be persisted and seeded into
the knowledge graph separately from the main specification.

Coverage Target: >= 80%
"""

from pathlib import Path


def extract_warnings(
    warnings: list[str],
    feature_id: str,
    output_dir: Path = Path("docs/warnings"),
) -> Path | None:
    """Extract warnings into a separate markdown file for Graphiti seeding.

    Creates a markdown file containing all warnings and constraints for a feature,
    formatted for Graphiti ingestion. The file is named using the feature_id
    to ensure traceability.

    Args:
        warnings: List of warning/constraint strings to extract.
        feature_id: The feature identifier (e.g., "FEAT-FP-002").
        output_dir: Directory where the warnings file will be created.
            Defaults to "docs/warnings".

    Returns:
        Path to the created warnings file, or None if warnings list is empty.

    Example:
        >>> warnings = ["W1: Do not modify core", "W2: Keep backward compat"]
        >>> path = extract_warnings(warnings, "FEAT-001", Path("/tmp"))
        >>> path.name
        'FEAT-001-warnings.md'
    """
    # Return None for empty warnings list
    if not warnings:
        return None

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename from feature_id
    filename = f"{feature_id}-warnings.md"
    output_path = output_dir / filename

    # Build markdown content
    content_lines = [
        f"# Warnings & Constraints: {feature_id}",
        "",
        f"{feature_id} has the following warnings and constraints that must be observed during implementation:",
        "",
    ]

    # Add each warning as a bullet point
    for warning in warnings:
        content_lines.append(f"- {warning}")

    # Add trailing newline
    content_lines.append("")

    # Write the file
    content = "\n".join(content_lines)
    output_path.write_text(content)

    return output_path
