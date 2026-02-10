"""
ADR File Generator for GuardKit.

Generates Architecture Decision Record (ADR) markdown files from Decision Log
entries in research templates.

Coverage Target: >=85%
"""

from pathlib import Path
from datetime import date
import re

from guardkit.planning.spec_parser import Decision


def _extract_feature_number(feature_id: str) -> str:
    """
    Extract feature number from feature ID.

    Examples:
        "FEAT-FP-002" -> "FP-002"
        "FP-002" -> "FP-002"
        "ABC-123" -> "ABC-123"
    """
    # Remove FEAT- prefix if present
    if feature_id.upper().startswith("FEAT-"):
        return feature_id[5:]
    return feature_id


def _create_slug(title: str) -> str:
    """
    Create URL-friendly slug from title.

    - Convert to lowercase
    - Replace spaces with hyphens
    - Remove special characters (keep only alphanumeric and hyphens)
    - Truncate to 50 characters
    """
    # Convert to lowercase
    slug = title.lower()

    # Replace spaces with hyphens
    slug = slug.replace(' ', '-')

    # Remove special characters (keep only alphanumeric and hyphens)
    slug = re.sub(r'[^a-z0-9-]', '', slug)

    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)

    # Remove leading/trailing hyphens
    slug = slug.strip('-')

    # Truncate to 50 characters
    if len(slug) > 50:
        slug = slug[:50]

    return slug


def _generate_adr_content(
    decision: Decision,
    feature_id: str,
    feature_number: str,
    slug: str,
    today: str,
) -> str:
    """Generate ADR markdown content."""
    return f"""# ADR-{feature_number}-{slug}: {decision.title}

**Status:** {decision.adr_status}
**Date:** {today}
**Feature:** {feature_id}
**Decision:** {decision.number}

## Status

{decision.adr_status}

## Date

{today}

## Context

{decision.rationale}

## Decision

{decision.title}

## Rationale

{decision.rationale}

## Alternatives Rejected

{decision.alternatives_rejected}

## Consequences

Implementation must follow this decision. See feature spec for full context.
"""


def generate_adrs(
    decisions: list[Decision],
    feature_id: str,
    output_dir: Path = Path("docs/adr"),
    check_duplicates: bool = True,
) -> list[Path]:
    """
    Generate ADR markdown files from Decision Log entries.

    Args:
        decisions: List of Decision objects to generate ADRs for
        feature_id: Feature ID (e.g., "FEAT-FP-002" or "FP-002")
        output_dir: Directory to write ADR files (default: docs/adr)
        check_duplicates: Skip existing files if True, overwrite if False

    Returns:
        List of Path objects for generated ADR files
    """
    if not decisions:
        return []

    # Resolve to absolute path
    output_dir = output_dir.resolve()

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract feature number for filenames
    feature_number = _extract_feature_number(feature_id)

    # Get today's date
    today = date.today().isoformat()

    generated_files = []

    for decision in decisions:
        # Skip decisions with empty titles
        if not decision.title or not decision.title.strip():
            continue

        # Create slug from title
        slug = _create_slug(decision.title)

        # Skip if slug is empty after cleaning
        if not slug:
            continue

        # Create filename
        filename = f"ADR-{feature_number}-{slug}.md"
        file_path = output_dir / filename

        # Check for duplicates
        if check_duplicates and file_path.exists():
            continue

        # Generate content
        content = _generate_adr_content(
            decision=decision,
            feature_id=feature_id,
            feature_number=feature_number,
            slug=slug,
            today=today,
        )

        # Write file
        file_path.write_text(content)
        generated_files.append(file_path)

    return generated_files
