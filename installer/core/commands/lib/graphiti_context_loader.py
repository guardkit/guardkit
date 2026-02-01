"""
Graphiti Context Loader for task-work Phase Execution.

This module provides the integration layer between JobContextRetriever and
the phase_execution module. It handles:
- Checking Graphiti availability
- Loading task-specific context via JobContextRetriever
- Formatting context for agent prompts
- Sync/async compatibility for phase execution

Public API:
    is_graphiti_enabled: Check if Graphiti is configured and available
    load_task_context: Load context via JobContextRetriever (async)
    load_task_context_sync: Synchronous wrapper for load_task_context
    get_context_for_prompt: Format RetrievedContext for prompt injection
    GRAPHITI_AVAILABLE: Boolean constant indicating Graphiti availability

Example:
    from installer.core.commands.lib.graphiti_context_loader import (
        is_graphiti_enabled,
        load_task_context,
        get_context_for_prompt,
    )

    if is_graphiti_enabled():
        context = await load_task_context(
            task_id="TASK-001",
            task_data={"description": "Implement auth"},
            phase="implement"
        )
        if context:
            prompt_text = context  # Already formatted string

References:
    - TASK-GR6-005: Integrate JobContextRetriever into /task-work
    - FEAT-GR-006: Job-Specific Context Retrieval
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)

# Try to import Graphiti and JobContextRetriever
try:
    from guardkit.knowledge import get_graphiti
    from guardkit.knowledge.job_context_retriever import (
        JobContextRetriever,
        RetrievedContext,
    )
    from guardkit.knowledge.task_analyzer import TaskPhase

    GRAPHITI_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Graphiti modules not available: {e}")
    GRAPHITI_AVAILABLE = False
    get_graphiti = None
    JobContextRetriever = None
    RetrievedContext = None
    TaskPhase = None


def is_graphiti_enabled() -> bool:
    """
    Check if Graphiti is configured and available.

    Checks:
    1. GRAPHITI_AVAILABLE - modules can be imported
    2. GRAPHITI_ENABLED env var is not "false"
    3. config/graphiti.yaml exists (optional)

    Returns:
        bool: True if Graphiti is available and enabled

    Example:
        if is_graphiti_enabled():
            context = await load_task_context(...)
        else:
            # Use fallback context loading
            pass
    """
    try:
        # Check if modules are available
        if not GRAPHITI_AVAILABLE:
            return False

        # Check environment variable (allows explicit disable)
        env_enabled = os.environ.get("GRAPHITI_ENABLED", "true").lower()
        if env_enabled == "false":
            return False

        # Graphiti is available and not explicitly disabled
        return True

    except Exception as e:
        logger.debug(f"Error checking Graphiti availability: {e}")
        return False


def _get_task_phase(phase: str) -> "TaskPhase":
    """
    Map phase string to TaskPhase enum.

    Args:
        phase: Phase string (e.g., "implement", "plan", "test")

    Returns:
        TaskPhase enum value (defaults to IMPLEMENT for unknown phases)

    Example:
        task_phase = _get_task_phase("implement")
        assert task_phase == TaskPhase.IMPLEMENT
    """
    if not GRAPHITI_AVAILABLE or TaskPhase is None:
        raise RuntimeError("Graphiti modules not available")

    phase_mapping = {
        "load": TaskPhase.LOAD,
        "plan": TaskPhase.PLAN,
        "implement": TaskPhase.IMPLEMENT,
        "test": TaskPhase.TEST,
        "review": TaskPhase.REVIEW,
    }

    return phase_mapping.get(phase.lower(), TaskPhase.IMPLEMENT)


async def _get_retriever() -> "JobContextRetriever":
    """
    Get a configured JobContextRetriever instance.

    Creates a new JobContextRetriever with the Graphiti client
    obtained from get_graphiti().

    Returns:
        JobContextRetriever: Configured retriever instance

    Raises:
        Exception: If Graphiti client cannot be obtained

    Example:
        retriever = await _get_retriever()
        context = await retriever.retrieve(task, phase)
    """
    if not GRAPHITI_AVAILABLE or get_graphiti is None:
        raise RuntimeError("Graphiti modules not available")

    graphiti = await get_graphiti()
    return JobContextRetriever(graphiti)


async def load_task_context(
    task_id: str,
    task_data: Dict[str, Any],
    phase: str,
) -> Optional[str]:
    """
    Load task-specific context via JobContextRetriever.

    This function:
    1. Checks if Graphiti is enabled
    2. Gets a JobContextRetriever instance
    3. Retrieves context for the task and phase
    4. Formats the context for prompt injection

    Args:
        task_id: Task identifier (e.g., "TASK-001")
        task_data: Task data dictionary with fields like description, tech_stack
        phase: Current execution phase ("plan", "implement", "test", etc.)

    Returns:
        Formatted context string for prompt injection, or None if unavailable

    Example:
        context = await load_task_context(
            task_id="TASK-001",
            task_data={"description": "Implement auth", "tech_stack": "python"},
            phase="implement"
        )
        if context:
            prompt = f"{base_prompt}\\n\\n{context}"
    """
    if not is_graphiti_enabled():
        logger.debug("Graphiti not enabled, skipping context loading")
        return None

    try:
        # Get retriever
        retriever = await _get_retriever()

        # Build task dict with task_id
        task = dict(task_data)
        task["id"] = task_id

        # Map phase string to enum
        task_phase = _get_task_phase(phase)

        # Retrieve context
        context = await retriever.retrieve(task, task_phase)

        # Format for prompt
        return context.to_prompt()

    except Exception as e:
        logger.warning(f"Error loading task context: {e}")
        return None


def load_task_context_sync(
    task_id: str,
    task_data: Dict[str, Any],
    phase: str,
) -> Optional[str]:
    """
    Synchronous wrapper for load_task_context.

    Provides synchronous access to the async load_task_context function
    for use in non-async contexts.

    Args:
        task_id: Task identifier
        task_data: Task data dictionary
        phase: Current execution phase

    Returns:
        Formatted context string or None

    Example:
        context = load_task_context_sync(
            task_id="TASK-001",
            task_data={"description": "Test"},
            phase="implement"
        )
    """
    try:
        # Get or create event loop
        try:
            loop = asyncio.get_running_loop()
            # If we're already in an async context, can't use run_until_complete
            # Create a new loop in a thread instead
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    load_task_context(task_id, task_data, phase)
                )
                return future.result()
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            return asyncio.run(load_task_context(task_id, task_data, phase))

    except Exception as e:
        logger.warning(f"Error in sync context loading: {e}")
        return None


def get_context_for_prompt(
    context: Optional[Union["RetrievedContext", str]]
) -> str:
    """
    Format context for inclusion in agent prompts.

    Accepts either a RetrievedContext object or an already-formatted string.
    Returns empty string for None or empty context.

    Args:
        context: RetrievedContext, formatted string, or None

    Returns:
        Formatted string suitable for prompt injection

    Example:
        # From RetrievedContext
        prompt_text = get_context_for_prompt(retrieved_context)

        # Already formatted string
        prompt_text = get_context_for_prompt("## Context\\n...")

        # None
        prompt_text = get_context_for_prompt(None)  # Returns ""
    """
    if context is None:
        return ""

    # If it's already a string, return as-is
    if isinstance(context, str):
        return context

    # If it's a RetrievedContext, format it
    if GRAPHITI_AVAILABLE and RetrievedContext is not None:
        if isinstance(context, RetrievedContext):
            return context.to_prompt()

    # Unknown type - try to call to_prompt if available
    if hasattr(context, 'to_prompt'):
        return context.to_prompt()

    # Fallback - convert to string
    return str(context) if context else ""


# Module exports
__all__ = [
    "is_graphiti_enabled",
    "load_task_context",
    "load_task_context_sync",
    "get_context_for_prompt",
    "GRAPHITI_AVAILABLE",
    "_get_task_phase",
    "_get_retriever",
]
