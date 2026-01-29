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

    # Load feature overview
    from guardkit.knowledge.context_loader import load_feature_overview
    overview = await load_feature_overview("feature-build")

    # Load failed approaches for prevention (TASK-GE-004)
    from guardkit.knowledge.context_loader import load_failed_approaches
    warnings = await load_failed_approaches("subprocess task-work")
    for warning in warnings:
        print(f"Warning: {warning['symptom']}")
        print(f"Prevention: {warning['prevention']}")
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


async def load_feature_overview(feature_name: str) -> Optional["FeatureOverviewEntity"]:
    """Load feature overview for context injection.

    Queries Graphiti for the feature overview entity matching the given
    feature name. Returns the first matching result.

    Args:
        feature_name: Name/ID of the feature (e.g., "feature-build")

    Returns:
        FeatureOverviewEntity if found, None otherwise (graceful degradation)

    Example:
        overview = await load_feature_overview("feature-build")
        if overview:
            print(f"Loaded: {overview.tagline}")
    """
    # Import here to avoid circular imports
    from guardkit.knowledge.entities.feature_overview import FeatureOverviewEntity
    from datetime import datetime

    graphiti = get_graphiti()

    # Graceful degradation: return None if Graphiti unavailable
    if graphiti is None:
        logger.debug("Graphiti client is None, returning None for feature overview")
        return None

    if not graphiti.enabled:
        logger.debug("Graphiti is disabled, returning None for feature overview")
        return None

    try:
        results = await graphiti.search(
            query=f"feature_overview {feature_name}",
            group_ids=["feature_overviews"],
            num_results=1
        )

        if not results:
            logger.debug(f"No feature overview found for: {feature_name}")
            return None

        # Get the first result
        result = results[0]

        # Extract body (may be nested or direct)
        body = result.get("body", {})
        if not body or not isinstance(body, dict):
            logger.debug(f"Malformed feature overview result for: {feature_name}")
            return None

        # Check for required fields
        required_fields = [
            "id", "name", "tagline", "purpose", "what_it_is",
            "what_it_is_not", "invariants", "architecture_summary",
            "key_components", "key_decisions"
        ]

        for field in required_fields:
            if field not in body:
                logger.debug(f"Missing required field '{field}' in feature overview")
                return None

        # Parse timestamps
        created_at = body.get("created_at")
        updated_at = body.get("updated_at")

        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                created_at = datetime.now()
        else:
            created_at = datetime.now()

        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except ValueError:
                updated_at = datetime.now()
        else:
            updated_at = datetime.now()

        # Create entity from body
        return FeatureOverviewEntity(
            id=body["id"],
            name=body["name"],
            tagline=body["tagline"],
            purpose=body["purpose"],
            what_it_is=body["what_it_is"],
            what_it_is_not=body["what_it_is_not"],
            invariants=body["invariants"],
            architecture_summary=body["architecture_summary"],
            key_components=body["key_components"],
            key_decisions=body["key_decisions"],
            created_at=created_at,
            updated_at=updated_at
        )

    except Exception as e:
        logger.warning(f"Error loading feature overview for {feature_name}: {e}")
        return None


async def load_critical_adrs() -> List[Dict[str, Any]]:
    """Load critical Architecture Decision Records for context injection.

    Queries Graphiti for ADRs in the architecture_decisions group and
    returns them formatted for injection into Claude Code sessions.

    Returns:
        List of ADR dictionaries with id, title, decision, violation_symptoms, etc.
        Returns empty list if Graphiti is unavailable (graceful degradation).

    Example:
        adrs = await load_critical_adrs()
        for adr in adrs:
            print(f"ADR {adr['id']}: {adr['title']}")
    """
    graphiti = get_graphiti()

    # Graceful degradation: return empty list if Graphiti unavailable
    if graphiti is None:
        logger.debug("Graphiti client is None, returning empty list for critical ADRs")
        return []

    if not graphiti.enabled:
        logger.debug("Graphiti is disabled, returning empty list for critical ADRs")
        return []

    try:
        results = await graphiti.search(
            query="architecture_decision feature-build ADR",
            group_ids=["architecture_decisions"],
            num_results=10
        )

        if not results:
            logger.debug("No critical ADRs found in Graphiti")
            return []

        # Extract body fields from results
        adrs = []
        for result in results:
            body = result.get("body", {})
            if isinstance(body, dict) and body:
                adrs.append(body)

        return adrs

    except Exception as e:
        logger.warning(f"Error loading critical ADRs: {e}")
        return []


async def load_failed_approaches(
    query_context: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Load failed approaches for context injection.

    Queries the failed_approaches group for relevant failures and formats
    them as warnings for injection into Claude Code sessions. This helps
    prevent repeating the same mistakes.

    Args:
        query_context: Context to search for (e.g., "subprocess task-work")
        limit: Maximum number of results to return (default: 5)

    Returns:
        List of warning dictionaries with symptom, prevention, and related_adrs.
        Returns empty list if Graphiti is unavailable (graceful degradation).

    Example:
        warnings = await load_failed_approaches("subprocess task-work")
        for warning in warnings:
            print(f"Warning: {warning['symptom']}")
            print(f"Prevention: {warning['prevention']}")
    """
    # Delegate to the failed_approach_manager
    from guardkit.knowledge.failed_approach_manager import load_relevant_failures

    return await load_relevant_failures(
        query_context=query_context,
        limit=limit,
    )


async def load_role_context(role: str, context: str = "feature-build") -> Optional[str]:
    """Load role constraints for injection into session.

    Queries Graphiti for role constraints and formats them as markdown
    for injection into Player or Coach agent context.

    Args:
        role: Role name ("player" | "coach")
        context: Usage context (default: "feature-build")

    Returns:
        Formatted markdown string with role constraints, or None if
        Graphiti is unavailable or no results found.

    Example:
        context = await load_role_context("player", "feature-build")
        if context:
            print(context)  # Formatted markdown with MUST DO and MUST NOT DO
    """
    graphiti = get_graphiti()

    # Graceful degradation: return None if Graphiti unavailable
    if graphiti is None:
        logger.debug("Graphiti client is None, returning None for role context")
        return None

    if not graphiti.enabled:
        logger.debug("Graphiti is disabled, returning None for role context")
        return None

    try:
        # Query for role constraints
        results = await graphiti.search(
            query=f"role_constraint {role} {context}",
            group_ids=["role_constraints"],
            num_results=1
        )

        if not results:
            logger.debug(f"No role constraints found for: {role} in {context}")
            return None

        # Get the first result
        result = results[0]

        # Extract body
        body = result.get("body", {})
        if not body or not isinstance(body, dict):
            logger.debug(f"Malformed role constraint result for: {role}")
            return None

        # Format as markdown
        role_upper = role.upper()
        lines = []
        lines.append(f"# {role_upper} Role Constraints")
        lines.append("")

        # Primary responsibility
        if "primary_responsibility" in body:
            lines.append(f"**Primary responsibility**: {body['primary_responsibility']}")
            lines.append("")

        # MUST DO section
        if "must_do" in body and body["must_do"]:
            lines.append("## MUST DO")
            for item in body["must_do"]:
                lines.append(f"- {item}")
            lines.append("")

        # MUST NOT DO section
        if "must_not_do" in body and body["must_not_do"]:
            lines.append("## MUST NOT DO")
            for item in body["must_not_do"]:
                lines.append(f"- {item}")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"Error loading role context for {role}: {e}")
        return None
