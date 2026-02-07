"""
Failed approach capture and management.

This module provides functionality for capturing failed approaches
as episodes in Graphiti. All operations are designed for graceful
degradation - they will succeed even when Graphiti is unavailable.

Public API:
    FAILED_APPROACHES_GROUP_ID: Group ID for failed approaches in Graphiti
    capture_failed_approach: Capture a failed approach as an episode
    load_relevant_failures: Load failures relevant to current context
    increment_occurrence: Increment occurrence count for a failure
    FailedApproachManager: Class-based interface for failure management

Example Usage:
    from guardkit.knowledge.failed_approach_manager import (
        capture_failed_approach,
        load_relevant_failures,
        FAILED_APPROACHES_GROUP_ID,
    )

    # Capture a new failure
    failure = await capture_failed_approach(
        approach="Using subprocess.run() to invoke guardkit task-work",
        symptom="subprocess.CalledProcessError: Command not found",
        root_cause="CLI command doesn't exist - task-work is a slash command",
        fix_applied="Use SDK query() to invoke '/task-work TASK-XXX'",
        prevention="Check ADR-FB-001 before implementing task-work invocation",
        context="feature-build",
        related_adrs=["ADR-FB-001"],
        severity=Severity.CRITICAL
    )

    # Load relevant failures for context
    warnings = await load_relevant_failures(
        query_context="subprocess task-work invocation"
    )
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from guardkit.knowledge.graphiti_client import get_graphiti
from guardkit.knowledge.entities.failed_approach import (
    FailedApproachEpisode,
    Severity,
)

logger = logging.getLogger(__name__)

# Group ID for failed approaches in Graphiti
FAILED_APPROACHES_GROUP_ID = "failed_approaches"


def _generate_failure_id(approach: str) -> str:
    """Generate a unique failure ID from approach hash.

    Creates a deterministic ID based on the approach text, so the
    same approach will always generate the same ID.

    Args:
        approach: The approach text to hash

    Returns:
        Unique ID in format FAIL-XXXXXXXX (8 uppercase hex chars)
    """
    approach_hash = hashlib.sha256(approach.encode()).hexdigest()[:8]
    return f"FAIL-{approach_hash.upper()}"


async def capture_failed_approach(
    approach: str,
    symptom: str,
    root_cause: str,
    fix_applied: str,
    prevention: str,
    context: str,
    task_id: Optional[str] = None,
    feature_id: Optional[str] = None,
    file_path: Optional[str] = None,
    related_adrs: Optional[List[str]] = None,
    similar_failures: Optional[List[str]] = None,
    severity: Severity = Severity.MEDIUM,
    time_to_fix_minutes: Optional[int] = None,
) -> FailedApproachEpisode:
    """Capture a failed approach as an episode in Graphiti.

    Creates a FailedApproachEpisode instance and stores it in Graphiti
    as an episode. Gracefully degrades if Graphiti is unavailable -
    still returns the created FailedApproachEpisode.

    Args:
        approach: What was tried (the failed approach)
        symptom: What went wrong (error message or behavior)
        root_cause: Why it failed (underlying reason)
        fix_applied: How it was resolved (what worked instead)
        prevention: How to avoid in future (key for learning)
        context: Where this happened (feature-build, task-work, etc.)
        task_id: Task ID where this occurred (optional)
        feature_id: Feature ID where this occurred (optional)
        file_path: File path involved if relevant (optional)
        related_adrs: List of ADR IDs to check (optional)
        similar_failures: List of related failure IDs (optional)
        severity: How severe is this failure (default: MEDIUM)
        time_to_fix_minutes: How long to resolve in minutes (optional)

    Returns:
        FailedApproachEpisode with generated ID and all fields populated

    Example:
        failure = await capture_failed_approach(
            approach="Using subprocess for task-work",
            symptom="Command not found error",
            root_cause="CLI doesn't exist",
            fix_applied="Use SDK query()",
            prevention="Check ADR-FB-001",
            context="feature-build",
            severity=Severity.CRITICAL
        )
    """
    # Generate unique ID from approach hash
    failure_id = _generate_failure_id(approach)

    # Handle None for list fields
    if related_adrs is None:
        related_adrs = []
    if similar_failures is None:
        similar_failures = []

    # Create FailedApproachEpisode instance
    failure = FailedApproachEpisode(
        id=failure_id,
        approach=approach,
        symptom=symptom,
        root_cause=root_cause,
        fix_applied=fix_applied,
        prevention=prevention,
        context=context,
        task_id=task_id,
        feature_id=feature_id,
        file_path=file_path,
        related_adrs=related_adrs,
        similar_failures=similar_failures,
        severity=severity,
        time_to_fix_minutes=time_to_fix_minutes,
    )

    # Generate episode body
    episode_body = failure.to_episode_body()

    # Create episode name
    episode_name = f"failed_approach_{failure.id}"

    # Attempt to store in Graphiti (graceful degradation)
    client = get_graphiti()

    if client is None:
        logger.debug("Graphiti client not initialized, skipping episode creation")
        return failure

    if not client.enabled:
        logger.debug("Graphiti client disabled, skipping episode creation")
        return failure

    try:
        await client.add_episode(
            name=episode_name,
            episode_body=json.dumps(episode_body),
            group_id=FAILED_APPROACHES_GROUP_ID,
            source="auto_captured",
            entity_type="failed_approach"
        )
        logger.info(f"Captured failed approach {failure_id}")
    except Exception as e:
        logger.warning(f"Failed to store failed approach in Graphiti: {e}")

    return failure


async def load_relevant_failures(
    query_context: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Load failed approaches relevant to current context.

    Queries Graphiti for failed approaches that match the given context
    and formats them as warnings with symptom, prevention, and related ADRs.

    Args:
        query_context: Context to search for (e.g., "subprocess task-work")
        limit: Maximum number of results to return (default: 5)

    Returns:
        List of warning dictionaries with symptom, prevention, and related_adrs.
        Returns empty list if Graphiti is unavailable (graceful degradation).

    Example:
        warnings = await load_relevant_failures(
            query_context="subprocess task-work invocation"
        )
        for warning in warnings:
            print(f"Warning: {warning['symptom']}")
            print(f"Prevention: {warning['prevention']}")
    """
    client = get_graphiti()

    if client is None:
        logger.debug("Graphiti client not initialized, returning empty list")
        return []

    if not client.enabled:
        logger.debug("Graphiti client disabled, returning empty list")
        return []

    try:
        results = await client.search(
            query=f"failed approach {query_context}",
            group_ids=[FAILED_APPROACHES_GROUP_ID],
            num_results=limit,
        )

        # Format as warnings
        warnings = []
        for result in results:
            body = result.get("body", {})
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except json.JSONDecodeError:
                    continue

            warnings.append({
                "symptom": body.get("symptom", ""),
                "prevention": body.get("prevention", ""),
                "related_adrs": body.get("related_adrs", []),
            })

        return warnings[:limit]

    except Exception as e:
        logger.warning(f"Failed to load failures from Graphiti: {e}")
        return []


async def increment_occurrence(failure_id: str) -> Optional[FailedApproachEpisode]:
    """Increment occurrence count for an existing failure.

    Searches for an existing failure by ID, increments its occurrence
    count, updates the last_occurred timestamp, and stores the updated
    version in Graphiti.

    Args:
        failure_id: The failure ID to increment (e.g., "FAIL-A1B2C3D4")

    Returns:
        Updated FailedApproachEpisode with incremented count, or None if
        the failure was not found or Graphiti is unavailable.

    Example:
        updated = await increment_occurrence("FAIL-A1B2C3D4")
        if updated:
            print(f"Occurrence count: {updated.occurrences}")
    """
    client = get_graphiti()

    if client is None:
        logger.debug("Graphiti client not initialized, cannot increment")
        return None

    if not client.enabled:
        logger.debug("Graphiti client disabled, cannot increment")
        return None

    try:
        # Search for the failure by ID
        results = await client.search(
            query=f"failed_approach id:{failure_id}",
            group_ids=[FAILED_APPROACHES_GROUP_ID],
            num_results=1,
        )

        if not results:
            logger.debug(f"Failure {failure_id} not found")
            return None

        # Parse the body
        body = results[0].get("body", {})
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse body for {failure_id}")
                return None

        # Parse severity
        severity_value = body.get("severity", "medium")
        try:
            severity = Severity(severity_value)
        except ValueError:
            severity = Severity.MEDIUM

        # Parse timestamps
        first_occurred_str = body.get("first_occurred")
        last_occurred_str = body.get("last_occurred")

        if first_occurred_str:
            try:
                first_occurred = datetime.fromisoformat(
                    first_occurred_str.replace("Z", "+00:00")
                )
            except ValueError:
                first_occurred = datetime.now()
        else:
            first_occurred = datetime.now()

        # Create updated failure with incremented occurrence
        updated_failure = FailedApproachEpisode(
            id=body.get("id", failure_id),
            approach=body.get("approach", ""),
            symptom=body.get("symptom", ""),
            root_cause=body.get("root_cause", ""),
            fix_applied=body.get("fix_applied", ""),
            prevention=body.get("prevention", ""),
            context=body.get("context", ""),
            task_id=body.get("task_id"),
            feature_id=body.get("feature_id"),
            file_path=body.get("file_path"),
            related_adrs=body.get("related_adrs", []),
            similar_failures=body.get("similar_failures", []),
            occurrences=body.get("occurrences", 1) + 1,  # Increment!
            first_occurred=first_occurred,
            last_occurred=datetime.now(),  # Update to now
            severity=severity,
            time_to_fix_minutes=body.get("time_to_fix_minutes"),
        )

        # Store updated version
        episode_body = updated_failure.to_episode_body()
        episode_name = f"failed_approach_{updated_failure.id}"

        await client.add_episode(
            name=episode_name,
            episode_body=json.dumps(episode_body),
            group_id=FAILED_APPROACHES_GROUP_ID,
            source="auto_captured",
            entity_type="failed_approach"
        )

        logger.info(f"Incremented occurrence for {failure_id} to {updated_failure.occurrences}")
        return updated_failure

    except Exception as e:
        logger.warning(f"Failed to increment occurrence for {failure_id}: {e}")
        return None


class FailedApproachManager:
    """Class-based interface for failed approach management.

    Provides a stateful interface for managing failed approaches.
    This class wraps the module-level functions for convenience.

    Example:
        manager = FailedApproachManager()

        # Capture a failure
        failure = await manager.capture(
            approach="Using subprocess",
            symptom="Command not found",
            root_cause="CLI doesn't exist",
            fix_applied="Use SDK",
            prevention="Check ADR",
            context="feature-build"
        )

        # Load relevant failures
        warnings = await manager.load_relevant("subprocess invocation")
    """

    async def capture(
        self,
        approach: str,
        symptom: str,
        root_cause: str,
        fix_applied: str,
        prevention: str,
        context: str,
        **kwargs,
    ) -> FailedApproachEpisode:
        """Capture a failed approach.

        Delegates to capture_failed_approach function.

        Args:
            approach: What was tried (the failed approach)
            symptom: What went wrong (error message or behavior)
            root_cause: Why it failed (underlying reason)
            fix_applied: How it was resolved (what worked instead)
            prevention: How to avoid in future (key for learning)
            context: Where this happened (feature-build, task-work, etc.)
            **kwargs: Additional optional fields

        Returns:
            FailedApproachEpisode with generated ID and all fields populated
        """
        return await capture_failed_approach(
            approach=approach,
            symptom=symptom,
            root_cause=root_cause,
            fix_applied=fix_applied,
            prevention=prevention,
            context=context,
            **kwargs,
        )

    async def load_relevant(
        self,
        query_context: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Load relevant failures for context.

        Delegates to load_relevant_failures function.

        Args:
            query_context: Context to search for
            limit: Maximum number of results to return

        Returns:
            List of warning dictionaries with symptom, prevention, and related_adrs
        """
        return await load_relevant_failures(
            query_context=query_context,
            limit=limit,
        )

    async def increment(self, failure_id: str) -> Optional[FailedApproachEpisode]:
        """Increment occurrence count for a failure.

        Delegates to increment_occurrence function.

        Args:
            failure_id: The failure ID to increment

        Returns:
            Updated FailedApproachEpisode or None if not found
        """
        return await increment_occurrence(failure_id)
