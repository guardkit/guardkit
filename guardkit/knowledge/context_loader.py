"""
Context loading module for GuardKit session initialization.

This module provides the critical context loading functionality that injects
relevant knowledge from Graphiti at the start of Claude Code sessions and commands.
This is THE feature that fixes the memory problem by ensuring sessions have
knowledge of architectural decisions, failure patterns, and quality gates.

Example Usage:
    from guardkit.knowledge.context_loader import load_critical_context

    # Load context at session start
    context = await load_critical_context(command="task-work")

    # Load context for specific task
    context = await load_critical_context(
        task_id="TASK-001",
        command="feature-build"
    )

    # Format and inject into session
    from guardkit.knowledge.context_formatter import format_context_for_injection
    context_text = format_context_for_injection(context)
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import logging

from guardkit.knowledge.graphiti_client import get_graphiti

logger = logging.getLogger(__name__)


@dataclass
class CriticalContext:
    """Context loaded at session start.

    This dataclass holds all the critical knowledge that should be injected
    into Claude Code sessions to prevent context-less decision making.

    Attributes:
        system_context: What GuardKit is and how it works
        quality_gates: How quality is enforced (phases, thresholds)
        architecture_decisions: Key design decisions (MUST FOLLOW)
        failure_patterns: Known failures to avoid (DO NOT REPEAT)
        successful_patterns: What worked well (patterns to follow)
        similar_task_outcomes: Similar tasks and their results
        relevant_adrs: Architecture Decision Records affecting this work
        applicable_patterns: Design patterns that apply to this work
        relevant_rules: Code rules and conventions for this context
    """

    # System knowledge
    system_context: List[Dict[str, Any]]
    quality_gates: List[Dict[str, Any]]

    # Decision knowledge
    architecture_decisions: List[Dict[str, Any]]

    # Learning knowledge
    failure_patterns: List[Dict[str, Any]]
    successful_patterns: List[Dict[str, Any]]

    # Task-specific (when applicable)
    similar_task_outcomes: List[Dict[str, Any]]
    relevant_adrs: List[Dict[str, Any]]

    # Template/pattern knowledge (when applicable)
    applicable_patterns: List[Dict[str, Any]]
    relevant_rules: List[Dict[str, Any]]


def _create_empty_context() -> CriticalContext:
    """Create an empty CriticalContext with all fields initialized.

    Returns:
        CriticalContext with all empty lists.
    """
    return CriticalContext(
        system_context=[],
        quality_gates=[],
        architecture_decisions=[],
        failure_patterns=[],
        successful_patterns=[],
        similar_task_outcomes=[],
        relevant_adrs=[],
        applicable_patterns=[],
        relevant_rules=[]
    )


def _filter_valid_results(results: List[Any]) -> List[Dict[str, Any]]:
    """Filter search results to only include valid dict entries.

    Args:
        results: Raw search results from Graphiti

    Returns:
        List of valid dictionary results with 'body' field.
    """
    valid = []
    for r in results:
        if r is None:
            continue
        if not isinstance(r, dict):
            continue
        # Keep even if body is None/missing - let caller handle
        valid.append(r)
    return valid


async def load_critical_context(
    task_id: Optional[str] = None,
    feature_id: Optional[str] = None,
    command: Optional[str] = None
) -> CriticalContext:
    """Load must-know context at session/command start.

    This function queries Graphiti for critical knowledge that should be
    injected into Claude Code sessions. It ensures sessions have knowledge of:
    - What GuardKit is and how it works
    - Quality gates and their requirements
    - Architecture decisions that MUST be followed
    - Failure patterns to avoid

    Args:
        task_id: Optional task ID for task-specific context
        feature_id: Optional feature ID for feature-specific context
        command: Optional command name (e.g., "task-work", "feature-build")

    Returns:
        CriticalContext with all loaded knowledge, or empty context if
        Graphiti is unavailable (graceful degradation).

    Example:
        # Load context for feature-build command
        context = await load_critical_context(command="feature-build")

        # Load context for specific task
        context = await load_critical_context(
            task_id="TASK-001",
            command="task-work"
        )
    """
    graphiti = get_graphiti()

    # Graceful degradation: return empty context if Graphiti unavailable
    if graphiti is None:
        logger.debug("Graphiti client is None, returning empty context")
        return _create_empty_context()

    if not graphiti.enabled:
        logger.debug("Graphiti is disabled, returning empty context")
        return _create_empty_context()

    try:
        # 1. Always load: System context (what GuardKit is)
        system_context = await _load_system_context(graphiti)

        # 2. Always load: Quality gates (critical for all commands)
        quality_gates = await _load_quality_gates(graphiti)

        # 3. Always load: Architecture decisions (MUST FOLLOW)
        architecture_decisions = await _load_architecture_decisions(graphiti)

        # 4. Always load: Failure patterns (DO NOT REPEAT)
        failure_patterns = await _load_failure_patterns(graphiti)

        # 5. Command-specific context
        if command == "feature-build":
            # Load feature-build specific knowledge
            fb_context = await _load_feature_build_context(graphiti)
            system_context.extend(fb_context)

        return CriticalContext(
            system_context=system_context,
            quality_gates=quality_gates,
            architecture_decisions=architecture_decisions,
            failure_patterns=failure_patterns,
            successful_patterns=[],  # Populated by Episode Capture feature
            similar_task_outcomes=[],  # Future: task similarity search
            relevant_adrs=[],  # Future: ADR search
            applicable_patterns=[],  # Future: pattern search
            relevant_rules=[]  # Future: rule search
        )

    except Exception as e:
        logger.warning(f"Error loading context from Graphiti: {e}")
        return _create_empty_context()


async def _load_system_context(graphiti) -> List[Dict[str, Any]]:
    """Load system context (what GuardKit is).

    Args:
        graphiti: GraphitiClient instance

    Returns:
        List of system context results.
    """
    try:
        results = await graphiti.search(
            query="GuardKit product workflow quality gate",
            group_ids=["product_knowledge", "command_workflows"],
            num_results=5
        )
        return _filter_valid_results(results)
    except Exception as e:
        logger.warning(f"Error loading system context: {e}")
        return []


async def _load_quality_gates(graphiti) -> List[Dict[str, Any]]:
    """Load quality gate definitions.

    Args:
        graphiti: GraphitiClient instance

    Returns:
        List of quality gate results.
    """
    try:
        results = await graphiti.search(
            query="quality gate phase approval threshold coverage",
            group_ids=["quality_gate_phases"],
            num_results=5
        )
        return _filter_valid_results(results)
    except Exception as e:
        logger.warning(f"Error loading quality gates: {e}")
        return []


async def _load_architecture_decisions(graphiti) -> List[Dict[str, Any]]:
    """Load architecture decisions (MUST FOLLOW).

    Args:
        graphiti: GraphitiClient instance

    Returns:
        List of architecture decision results.
    """
    try:
        results = await graphiti.search(
            query="architecture decision SDK subprocess worktree delegation",
            group_ids=["architecture_decisions"],
            num_results=10
        )
        return _filter_valid_results(results)
    except Exception as e:
        logger.warning(f"Error loading architecture decisions: {e}")
        return []


async def _load_failure_patterns(graphiti) -> List[Dict[str, Any]]:
    """Load failure patterns (DO NOT REPEAT).

    Args:
        graphiti: GraphitiClient instance

    Returns:
        List of failure pattern results.
    """
    try:
        results = await graphiti.search(
            query="failure error bug anti-pattern subprocess mock",
            group_ids=["failure_patterns"],
            num_results=5
        )
        return _filter_valid_results(results)
    except Exception as e:
        logger.warning(f"Error loading failure patterns: {e}")
        return []


async def _load_feature_build_context(graphiti) -> List[Dict[str, Any]]:
    """Load feature-build specific context.

    Args:
        graphiti: GraphitiClient instance

    Returns:
        List of feature-build specific results.
    """
    try:
        results = await graphiti.search(
            query="feature-build Player Coach delegation task-work SDK query",
            group_ids=["feature_build_architecture"],
            num_results=10
        )
        return _filter_valid_results(results)
    except Exception as e:
        logger.warning(f"Error loading feature-build context: {e}")
        return []
