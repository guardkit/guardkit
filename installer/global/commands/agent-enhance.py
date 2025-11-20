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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


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
        "--strategy",
        choices=["ai", "static", "hybrid"],
        default="ai",
        help="Enhancement strategy (default: ai)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed enhancement process"
    )

    parsed_args = parser.parse_args(args)

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

    # Import enhancer (lazy import to avoid unnecessary loading)
    try:
        import importlib
        _enhancer_module = importlib.import_module(
            'installer.global.lib.agent_enhancement.enhancer'
        )
        SingleAgentEnhancer = _enhancer_module.SingleAgentEnhancer
        ValidationError = _enhancer_module.ValidationError
    except ImportError as e:
        logger.error(f"✗ Failed to import enhancement module: {e}")
        logger.error("   This may indicate the shared modules are not yet implemented.")
        return 3

    # Create enhancer
    enhancer = SingleAgentEnhancer(
        strategy=parsed_args.strategy,
        dry_run=parsed_args.dry_run,
        verbose=parsed_args.verbose
    )

    # Enhance agent
    try:
        logger.info(f"Enhancing {agent_file.name}...")

        result = enhancer.enhance(
            agent_file=agent_file,
            template_dir=template_dir
        )

        if result.success:
            logger.info(f"✓ Enhanced {agent_file.name}")
            logger.info(f"  Sections added: {len(result.sections)}")
            logger.info(f"  Templates referenced: {len(result.templates)}")
            logger.info(f"  Code examples: {len(result.examples)}")

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
            template_dir = Path("installer/global/templates") / template_name

        agent_file = template_dir / "agents" / f"{agent_name}.md"
        return (agent_file, template_dir)

    else:
        raise ValueError(
            f"Invalid agent path format: {agent_path_str}\n"
            "Expected: 'template-dir/agent-name' or '/path/to/agent.md'"
        )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
