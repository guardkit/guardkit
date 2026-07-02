"""
System-plan orchestration logic.

This module provides the main orchestration logic for the system-plan command.
Coordinates mode detection, spec parsing, markdown generation via
ArchitectureWriter, and result reporting.

Supports two modes of operation:
  1. Context-file mode (``--context``): Parse a structured spec file and
     generate markdown artefacts.
  2. Interactive mode (default): Detect mode, present questions, generate plan.
     (Interactive mode delegates to Claude Code command spec; this orchestrator
     handles the context-file pipeline.)

Since the fleet-memory cutover (FEAT-MEM-09), ``/system-plan`` operates in
markdown-only mode: parsed architecture is written to ``docs/architecture/``
and no longer persisted to a knowledge graph.

Public API:
    run_system_plan: Main async orchestration entry point

Example:
    from guardkit.planning.system_plan import run_system_plan

    await run_system_plan(
        description="GuardKit",
        mode=None,
        focus="all",
        no_questions=False,
        defaults=False,
        context_file="docs/architecture/guardkit-system-spec.md",
        enable_context=True,
    )
"""

import logging
from pathlib import Path
from typing import Optional

from guardkit.planning.arch_spec_parser import ArchSpecResult, parse_architecture_spec
from guardkit.planning.architecture_writer import ArchitectureWriter
from guardkit.planning.mode_detector import detect_mode

logger = logging.getLogger(__name__)

# Default output directory for architecture markdown artefacts
_DEFAULT_OUTPUT_DIR = "docs/architecture"


def _write_artefacts(
    spec: ArchSpecResult,
    output_dir: str,
) -> list:
    """Generate markdown artefacts via ArchitectureWriter.

    Args:
        spec: Parsed architecture spec result.
        output_dir: Directory for output files.

    Returns:
        List of file paths written.
    """
    if spec.system_context is None:
        logger.warning(
            "[Planning] Cannot write artefacts: no system context parsed"
        )
        return []

    output_path = Path(output_dir)
    writer = ArchitectureWriter()
    writer.write_all(
        output_dir=output_path,
        system=spec.system_context,
        components=spec.components,
        concerns=spec.concerns,
        decisions=spec.decisions,
    )

    # Collect written file paths
    files = []
    files.append(str(output_path / "ARCHITECTURE.md"))
    files.append(str(output_path / "system-context.md"))
    is_ddd = spec.system_context.methodology.lower() == "ddd"
    comp_filename = "bounded-contexts.md" if is_ddd else "components.md"
    files.append(str(output_path / comp_filename))
    files.append(str(output_path / "crosscutting-concerns.md"))
    for decision in spec.decisions:
        files.append(str(output_path / "decisions" / f"{decision.entity_id}.md"))
    return files


def _report_results(
    mode: str,
    spec: ArchSpecResult,
    files_written: list,
) -> None:
    """Print a summary report to console.

    Args:
        mode: Detected or overridden mode.
        spec: Parsed spec result.
        files_written: List of markdown file paths written.
    """
    print()
    print("=" * 60)
    print("  System Plan Complete")
    print("=" * 60)
    print()
    print(f"  Mode: {mode}")
    print()

    # Entities parsed
    print("  Entities parsed from spec:")
    sys_count = 1 if spec.system_context else 0
    print(f"    System contexts:      {sys_count}")
    print(f"    Components:           {len(spec.components)}")
    print(f"    Crosscutting concerns: {len(spec.concerns)}")
    print(f"    Architecture decisions: {len(spec.decisions)}")
    total_parsed = sys_count + len(spec.components) + len(spec.concerns) + len(spec.decisions)
    print(f"    Total:                {total_parsed}")
    print()

    # Files written
    if files_written:
        print(f"  Markdown artefacts written: {len(files_written)} files")
        for f in files_written:
            print(f"    {f}")
    else:
        print("  Markdown artefacts: none written")
    print()

    # Parse warnings
    if spec.parse_warnings:
        print(f"  Parse warnings ({len(spec.parse_warnings)}):")
        for w in spec.parse_warnings:
            print(f"    - {w}")
        print()

    print("=" * 60)
    print()


async def run_system_plan(
    description: str,
    mode: Optional[str],
    focus: str,
    no_questions: bool,
    defaults: bool,
    context_file: Optional[str],
    enable_context: bool,
) -> None:
    """Main orchestration logic for system-plan command.

    Coordinates mode detection, spec file parsing, architecture markdown
    generation, and result reporting.

    When ``context_file`` is provided, the pipeline is:
      1. Detect or override mode
      2. Parse spec file into entities
      3. Generate markdown artefacts via ArchitectureWriter
      4. Report results

    When no context file is provided, the function logs the invocation
    for the interactive Claude Code flow (handled by the command spec).

    Args:
        description: System/feature description (used as project name).
        mode: Planning mode override (setup/refine/review) or None for auto-detect.
        focus: Focus area for planning (domains/services/decisions/crosscutting/all).
        no_questions: Skip clarifying questions.
        defaults: Use sensible defaults.
        context_file: Path to structured architecture spec file.
        enable_context: Retained for CLI compatibility; knowledge-graph
            persistence was retired in the fleet-memory cutover (markdown-only).
    """
    logger.info(
        f"[Planning] run_system_plan: description='{description}', "
        f"mode={mode}, focus={focus}, context_file={context_file}"
    )

    # Step 1: Detect mode (or use override). Architecture-context lookup was
    # retired in the fleet-memory cutover, so auto-detect degrades to "setup".
    if mode is not None:
        detected_mode = mode
        logger.info(f"[Planning] Mode override: {detected_mode}")
    else:
        project_id = description.lower().replace(" ", "-")
        detected_mode = await detect_mode(project_id=project_id)
        logger.info(f"[Planning] Auto-detected mode: {detected_mode}")

    print(f"Mode: {detected_mode}")

    # Step 2: Parse context file (if provided)
    if context_file is None:
        # No context file - interactive mode handled by Claude Code command spec
        logger.info(
            "[Planning] No context file provided - interactive mode "
            "(delegated to command spec)"
        )
        print(
            f"System plan initiated for '{description}' in {detected_mode} mode.\n"
            f"No --context file provided. Use --context <path> to parse "
            f"a structured architecture spec."
        )
        return

    context_path = Path(context_file)
    if not context_path.exists():
        logger.error(f"[Planning] Context file not found: {context_file}")
        print(f"Error: Context file not found: {context_file}")
        return

    print(f"Parsing: {context_file}")
    try:
        spec = parse_architecture_spec(context_path)
    except Exception as e:
        logger.error(f"[Planning] Failed to parse spec file: {e}")
        print(f"Error: Failed to parse spec file: {e}")
        return

    if spec.parse_warnings:
        for warning in spec.parse_warnings:
            logger.warning(f"[Planning] Parse warning: {warning}")

    # Step 3: Generate markdown artefacts
    print("Generating architecture markdown...")
    files_written = _write_artefacts(spec, _DEFAULT_OUTPUT_DIR)

    # Step 4: Report results
    _report_results(
        mode=detected_mode,
        spec=spec,
        files_written=files_written,
    )


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "run_system_plan",
]
