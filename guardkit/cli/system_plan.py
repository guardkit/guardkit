"""
System-plan CLI command.

This module provides the Click command for architecture planning with
optional Graphiti knowledge context integration.

Example:
    $ guardkit system-plan "Build payment processing system"
    $ guardkit system-plan "Add order management" --mode=refine
    $ guardkit system-plan "Review auth system" --mode=review --focus=services
"""

import asyncio
import logging
from typing import Optional, Sequence

import click
from rich.console import Console

from guardkit.cli.decorators import handle_cli_errors

console = Console()
logger = logging.getLogger(__name__)


class ChoiceWithLegacyError(click.Choice):
    """Custom Choice type that uses legacy error message format.

    This ensures consistent error messages across Click versions,
    producing "Invalid choice" instead of "Invalid value" for compatibility.
    """

    def fail(
        self,
        message: str,
        param: Optional[click.Parameter] = None,
        ctx: Optional[click.Context] = None,
    ) -> None:
        """Override to produce legacy "invalid choice" error format."""
        # Create error message with "invalid choice" phrasing
        choices_str = ", ".join(f"'{c}'" for c in self.choices)
        raise click.BadParameter(
            f"Invalid choice. Valid options are: {choices_str}",
            ctx=ctx,
            param=param,
        )


def validate_mutually_exclusive(ctx, no_questions: bool, defaults: bool) -> None:
    """Validate that --no-questions and --defaults are mutually exclusive.

    Args:
        ctx: Click context
        no_questions: Value of --no-questions flag
        defaults: Value of --defaults flag

    Raises:
        click.UsageError: If both flags are provided
    """
    if no_questions and defaults:
        raise click.UsageError(
            "--no-questions and --defaults are mutually exclusive and cannot be used together."
        )


@click.command("system-plan")
@click.argument("description")
@click.option(
    "--mode",
    type=ChoiceWithLegacyError(["setup", "refine", "review"], case_sensitive=False),
    default=None,
    help="Planning mode (auto-detected if not provided)",
)
@click.option(
    "--focus",
    type=ChoiceWithLegacyError(
        ["domains", "services", "decisions", "crosscutting", "all"],
        case_sensitive=False,
    ),
    default="all",
    help="Focus area for planning (default: all)",
    show_default=True,
)
@click.option(
    "--no-questions",
    is_flag=True,
    default=False,
    help="Skip clarifying questions and use AI-generated defaults",
)
@click.option(
    "--defaults",
    is_flag=True,
    default=False,
    help="Use sensible defaults without prompting",
)
@click.option(
    "--context",
    type=click.Path(exists=True),
    default=None,
    help="Path to additional context file",
)
@click.option(
    "--enable-context/--no-context",
    "enable_context",
    default=True,
    help="Enable/disable Graphiti context retrieval (default: enabled)",
)
@click.pass_context
@handle_cli_errors
def system_plan(
    ctx,
    description: str,
    mode: Optional[str],
    focus: str,
    no_questions: bool,
    defaults: bool,
    context: Optional[str],
    enable_context: bool,
):
    """
    AI-assisted architecture planning for system design.

    Creates and refines system architecture documentation using interactive
    discovery or structured updates based on existing architecture knowledge.

    \b
    DESCRIPTION is a brief description of the system or feature to plan.

    \b
    Examples:
        guardkit system-plan "Build payment processing system"
        guardkit system-plan "Add order management" --mode=refine
        guardkit system-plan "Review auth system" --mode=review --focus=services

    \b
    Modes:
        setup  - Initial architecture discovery (no existing context)
        refine - Update existing architecture (existing context found)
        review - Audit existing architecture for issues

    \b
    Focus Areas:
        domains      - Focus on domain boundaries and entities
        services     - Focus on service definitions and APIs
        decisions    - Focus on ADRs and rationale
        crosscutting - Focus on crosscutting concerns
        all          - Complete architecture planning (default)

    \b
    Exit Codes:
        0: Success
        1: Task not found
        2: Orchestration error
        3: Invalid arguments
    """
    # Validate mutually exclusive flags
    validate_mutually_exclusive(ctx, no_questions, defaults)

    # Run async orchestration
    asyncio.run(
        _run_system_plan(
            description=description,
            mode=mode,
            focus=focus,
            no_questions=no_questions,
            defaults=defaults,
            context_file=context,
            enable_context=enable_context,
            ctx_obj=ctx.obj,
        )
    )


async def _run_system_plan(
    description: str,
    mode: Optional[str],
    focus: str,
    no_questions: bool,
    defaults: bool,
    context_file: Optional[str],
    enable_context: bool,
    ctx_obj: Optional[dict],
) -> None:
    """
    Main async orchestration for system-plan command.

    Args:
        description: System/feature description
        mode: Planning mode (setup/refine/review) or None for auto-detect
        focus: Focus area for planning
        no_questions: Skip clarifying questions
        defaults: Use sensible defaults
        context_file: Path to additional context file
        enable_context: Whether to enable Graphiti context
        ctx_obj: Click context object
    """
    from guardkit.planning.system_plan import run_system_plan

    await run_system_plan(
        description=description,
        mode=mode,
        focus=focus,
        no_questions=no_questions,
        defaults=defaults,
        context_file=context_file,
        enable_context=enable_context,
    )


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "system_plan",
]
