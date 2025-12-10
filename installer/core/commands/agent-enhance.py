#!/usr/bin/env python3
"""
/agent-enhance Command

Enhance a single agent with template-specific content.

TASK-PHASE-8-INCREMENTAL: Incremental Agent Enhancement Workflow
"""

import sys
from pathlib import Path
from typing import Optional, Tuple
import logging
import argparse

# === BEGIN: Repository Root Resolution ===
# Ensure repository root is in sys.path for installer.* imports
# This allows the script to work when executed via symlink from any directory
def _add_repo_to_path():
    """Add repository root to sys.path if not already present."""
    script_path = Path(__file__).resolve()
    # From: /path/to/guardkit/installer/core/commands/agent-enhance.py
    # To:   /path/to/guardkit/
    # Navigate: commands/ -> global/ -> installer/ -> guardkit/ (4 levels up)
    repo_root = script_path.parent.parent.parent.parent
    repo_root_str = str(repo_root)

    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

_add_repo_to_path()
# === END: Repository Root Resolution ===

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def resolve_strategy(args: argparse.Namespace) -> str:
    """
    Resolve strategy from boolean flags.

    Precedence:
    1. Conflicting flags (--hybrid --static) → error
    2. --static → "static"
    3. --hybrid → "hybrid"
    4. Default → "ai"

    Args:
        args: Parsed command-line arguments

    Returns:
        Strategy string: "ai", "hybrid", or "static"

    Raises:
        SystemExit: If conflicting flags are provided
    """
    if args.hybrid and args.static:
        print("Error: Cannot use both --hybrid and --static flags. Choose one strategy.",
              file=sys.stderr)
        print("\nAvailable strategies:", file=sys.stderr)
        print("  (default)    AI-powered enhancement (best quality)", file=sys.stderr)
        print("  --hybrid     AI with static fallback (reliable)", file=sys.stderr)
        print("  --static     Template-based only (fastest)", file=sys.stderr)
        sys.exit(1)

    if args.static:
        return "static"
    elif args.hybrid:
        return "hybrid"
    else:
        return "ai"  # Default


def format_success_message(agent_name: str, strategy: str) -> str:
    """
    Format success message with strategy information.

    Args:
        agent_name: Name of the enhanced agent
        strategy: Strategy used ("ai", "hybrid", "static")

    Returns:
        Formatted success message
    """
    strategy_label = {
        "ai": "AI strategy",
        "hybrid": "hybrid strategy (AI with fallback)",
        "static": "static strategy"
    }
    return f"✓ Enhanced {agent_name} using {strategy_label[strategy]}"


def main(args: list[str]) -> int:
    """
    Main entry point for /agent-enhance command.

    Args:
        args: Command-line arguments (excluding program name)

    Returns:
        Exit code (0=success, 1=not found, 2=template error, 3=enhancement error,
                   4=validation error, 5=permission error)
    """
    # Parse arguments
    parser = argparse.ArgumentParser(
        prog="agent-enhance",
        description="Enhance a single agent with template-specific content"
    )
    parser.add_argument(
        "agent_path",
        help="Agent path (template-dir/agent-name or /path/to/agent.md)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be enhanced without applying"
    )
    parser.add_argument(
        "--hybrid",
        action="store_true",
        help="Use AI with fallback to static (production-safe)"
    )
    parser.add_argument(
        "--static",
        action="store_true",
        help="Use keyword matching only (fast, offline)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed enhancement process"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint after agent invocation"
    )
    parser.add_argument(
        "--no-split",
        action="store_true",
        help="Create single file (disable progressive disclosure split)"
    )

    parsed_args = parser.parse_args(args)

    # Resolve strategy from flags
    strategy = resolve_strategy(parsed_args)

    # Set log level based on verbose flag
    if parsed_args.verbose:
        logger.setLevel(logging.DEBUG)

    # Resolve agent file and template directory
    try:
        agent_file, template_dir = resolve_paths(parsed_args.agent_path)
    except ValueError as e:
        logger.error(f"✗ Path resolution failed: {e}")
        return 1

    if not agent_file.exists():
        logger.error(f"✗ Agent file not found: {agent_file}")
        return 1

    if not template_dir.exists():
        logger.error(f"✗ Template directory not found: {template_dir}")
        return 2

    # Import enhancer and orchestrator (lazy import to avoid unnecessary loading)
    try:
        import importlib
        _enhancer_module = importlib.import_module(
            'installer.core.lib.agent_enhancement.enhancer'
        )
        SingleAgentEnhancer = _enhancer_module.SingleAgentEnhancer
        ValidationError = _enhancer_module.ValidationError

        _orchestrator_module = importlib.import_module(
            'installer.core.lib.agent_enhancement.orchestrator'
        )
        AgentEnhanceOrchestrator = _orchestrator_module.AgentEnhanceOrchestrator
    except ImportError as e:
        logger.error(f"✗ Failed to import enhancement module: {e}")
        logger.error("   This may indicate the shared modules are not yet implemented.")
        return 3

    # Create enhancer
    enhancer = SingleAgentEnhancer(
        strategy=strategy,
        dry_run=parsed_args.dry_run,
        verbose=parsed_args.verbose
    )

    # TASK-FIX-DBFA: Determine split preference
    split_output = not parsed_args.no_split

    # Create orchestrator wrapper with split preference
    orchestrator = AgentEnhanceOrchestrator(
        enhancer=enhancer,
        resume=parsed_args.resume,
        verbose=parsed_args.verbose,
        split_output=split_output  # TASK-FIX-DBFA
    )

    # Enhance agent with orchestrator
    try:
        logger.info(f"Enhancing {agent_file.name}...")

        result = orchestrator.run(
            agent_file=agent_file,
            template_dir=template_dir
        )

        if result.success:
            logger.info(format_success_message(agent_file.name, strategy))
            logger.info(f"  Sections added: {len(result.sections)}")
            logger.info(f"  Templates referenced: {len(result.templates)}")
            logger.info(f"  Code examples: {len(result.examples)}")

            # TASK-FIX-DBFA: Report split status
            if result.split_output and result.extended_file:
                logger.info(f"  Split output: ✓ (core + extended files)")
                logger.info(f"    Core: {result.core_file.name if result.core_file else 'N/A'}")
                logger.info(f"    Extended: {result.extended_file.name if result.extended_file else 'N/A'}")
            elif not split_output:
                logger.info(f"  Split output: ✗ (--no-split flag)")
            else:
                logger.info(f"  Split output: ✗ (single file)")

            # TASK-ENF-P0-4: Validate discovery metadata
            if not parsed_args.dry_run:
                validate_discovery_metadata_after_enhancement(agent_file)

            if parsed_args.dry_run:
                logger.info("\n[DRY RUN] Changes not applied")
                print("\n--- Preview ---")
                print(result.diff)

            return 0
        else:
            logger.error(f"✗ Enhancement failed: {result.error}")
            return 3

    except ValidationError as e:
        logger.error(f"✗ Validation failed: {e}")
        return 4

    except PermissionError as e:
        logger.error(f"✗ Cannot write to agent file: {e}")
        return 5

    except Exception as e:
        logger.exception(f"✗ Unexpected error: {e}")
        return 3


def validate_discovery_metadata_after_enhancement(agent_file: Path) -> None:
    """
    Validate discovery metadata after agent enhancement (TASK-ENF-P0-4: FR1, FR3).

    Checks enhanced agent for required discovery metadata and reports
    missing fields. Does not block on missing metadata (graceful degradation).

    Args:
        agent_file: Path to enhanced agent file
    """
    try:
        # Import validation function
        import importlib
        _discovery_module = importlib.import_module(
            'installer.core.commands.lib.agent_discovery'
        )
        _extract_metadata = _discovery_module._extract_metadata
        validate_discovery_metadata = _discovery_module.validate_discovery_metadata
    except ImportError as e:
        logger.debug(f"Agent discovery not available: {e}")
        return

    # Extract metadata from enhanced agent
    metadata = _extract_metadata(agent_file, source="local", priority=1)

    if metadata is None:
        logger.warning(f"⚠️  Could not read metadata from {agent_file.name}")
        return

    # Validate metadata
    is_valid, errors = validate_discovery_metadata(metadata)

    if not is_valid:
        logger.warning(f"\n⚠️  Agent metadata incomplete:")
        for error in errors:
            logger.warning(f"    - {error}")
        logger.info(f"\n💡 Tip: Re-run enhancement with AI strategy for metadata generation")
    else:
        logger.info(f"✓ Discovery metadata validated successfully")


def resolve_paths(agent_path_str: str) -> Tuple[Path, Path]:
    """
    Resolve agent file and template directory from input path.

    Handles two formats:
    1. "template-dir/agent-name" (relative, slash-separated)
    2. "/absolute/path/to/agent.md" (absolute path)

    Args:
        agent_path_str: Input path string

    Returns:
        (agent_file, template_dir) tuple

    Raises:
        ValueError: If path format is invalid

    Examples:
        >>> resolve_paths("react-typescript/testing-specialist")
        (Path("~/.agentecflow/templates/react-typescript/agents/testing-specialist.md"),
         Path("~/.agentecflow/templates/react-typescript"))

        >>> resolve_paths("/tmp/my-template/agents/api-specialist.md")
        (Path("/tmp/my-template/agents/api-specialist.md"),
         Path("/tmp/my-template"))
    """
    agent_path = Path(agent_path_str)

    if agent_path.is_absolute() and agent_path.exists():
        # Absolute path format
        agent_file = agent_path
        template_dir = agent_file.parent.parent  # agents/ -> template/
        return (agent_file, template_dir)

    elif "/" in agent_path_str:
        # Relative "template/agent" format
        parts = agent_path_str.split("/")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid agent path format: {agent_path_str}\n"
                "Expected: 'template-dir/agent-name' or '/path/to/agent.md'"
            )

        template_name = parts[0]
        agent_name = parts[1]

        # Look in global templates first
        template_dir = Path.home() / ".agentecflow" / "templates" / template_name
        if not template_dir.exists():
            # Look in repository templates
            template_dir = Path("installer/core/templates") / template_name

        agent_file = template_dir / "agents" / f"{agent_name}.md"
        return (agent_file, template_dir)

    else:
        raise ValueError(
            f"Invalid agent path format: {agent_path_str}\n"
            "Expected: 'template-dir/agent-name' or '/path/to/agent.md'"
        )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
