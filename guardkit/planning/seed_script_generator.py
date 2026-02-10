"""
Seed Script Generator for GuardKit Feature Planning.

Generates executable bash scripts containing all guardkit graphiti add-context
commands needed to seed ADRs, specifications, and warnings into the knowledge
graph.

Coverage Target: >= 80%
"""

from pathlib import Path
import stat


def generate_seed_script(
    feature_id: str,
    adr_paths: list[Path],
    spec_path: Path,
    warnings_path: Path | None = None,
    output_dir: Path = Path("scripts"),
) -> Path:
    """Generate bash script for Graphiti seeding.

    Creates an executable bash script that seeds all feature-related documents
    into Graphiti. The script includes status checks, add-context commands for
    each document, and verification.

    Args:
        feature_id: The feature identifier (e.g., "FEAT-FP-002").
        adr_paths: List of paths to ADR markdown files.
        spec_path: Path to the feature specification file.
        warnings_path: Optional path to the warnings markdown file.
        output_dir: Directory where the script will be created.
            Defaults to "scripts".

    Returns:
        Path to the created executable bash script.

    Example:
        >>> adrs = [Path("docs/adr/0001.md"), Path("docs/adr/0002.md")]
        >>> script = generate_seed_script("FEAT-001", adrs, Path("docs/spec.md"))
        >>> script.name
        'seed-FEAT-001.sh'
    """
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename from feature_id
    filename = f"seed-{feature_id}.sh"
    output_path = output_dir / filename

    # Build script content
    script_lines = [
        "#!/usr/bin/env bash",
        "set -e",
        "",
        f'echo "=== Seeding {feature_id} ==="',
        "",
        "# 1. Check Graphiti status",
        "guardkit graphiti status",
        "",
        "# 2. Seed ADR files",
        'echo "Seeding ADR files..."',
    ]

    # Add ADR commands
    for adr_path in adr_paths:
        # Convert path to POSIX format for bash compatibility
        adr_str = str(adr_path).replace("\\", "/")
        script_lines.append(f"guardkit graphiti add-context {adr_str}")

    script_lines.extend([
        "",
        "# 3. Seed feature specification",
        'echo "Seeding feature specification..."',
        f"guardkit graphiti add-context {str(spec_path).replace(chr(92), '/')}",
    ])

    # Add warnings section if provided
    if warnings_path is not None:
        warnings_str = str(warnings_path).replace("\\", "/")
        script_lines.extend([
            "",
            "# 4. Seed warnings",
            'echo "Seeding warnings..."',
            f"guardkit graphiti add-context {warnings_str}",
        ])

    script_lines.extend([
        "",
        "# 5. Verify",
        'echo "Verifying seeding..."',
        "guardkit graphiti verify --verbose",
        "",
        'echo "=== Seeding complete ==="',
        "",
    ])

    # Write the script
    content = "\n".join(script_lines)
    output_path.write_text(content)

    # Make the script executable (chmod +x equivalent)
    current_mode = output_path.stat().st_mode
    output_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return output_path
