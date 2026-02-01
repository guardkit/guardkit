"""
Turn state operations for cross-turn learning.

This module provides functions for capturing turn state at the end of each
feature-build turn and loading previous turn context for turn continuation.
These operations enable cross-turn learning by storing and retrieving
structured turn data from Graphiti.

Public API:
    capture_turn_state: Store turn state in Graphiti
    load_turn_continuation_context: Load previous turn summary for context

Example:
    from guardkit.knowledge.turn_state_operations import (
        capture_turn_state,
        load_turn_continuation_context
    )
    from guardkit.knowledge.entities.turn_state import TurnStateEntity, TurnMode
    from guardkit.knowledge.graphiti_client import get_graphiti

    # Capture turn state
    graphiti = get_graphiti()
    turn_state = TurnStateEntity(...)
    await capture_turn_state(graphiti, turn_state)

    # Load previous turn context
    context = await load_turn_continuation_context(
        graphiti,
        feature_id="FEAT-GE",
        task_id="TASK-GE-001",
        current_turn=2
    )
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from guardkit.knowledge.entities.turn_state import TurnStateEntity, TurnMode
from guardkit.knowledge.graphiti_client import get_graphiti

logger = logging.getLogger(__name__)


async def capture_turn_state(
    graphiti_client,
    entity: TurnStateEntity
) -> None:
    """Capture turn state at end of feature-build turn.

    Stores the turn state entity in Graphiti for later retrieval.
    Supports graceful degradation - if Graphiti is unavailable or
    an error occurs, the function returns without raising exceptions.

    Args:
        graphiti_client: Graphiti client instance (can be None)
        entity: TurnStateEntity containing the turn state to capture

    Returns:
        None

    Raises:
        No exceptions are raised - all errors are caught and logged.

    Example:
        from guardkit.knowledge.graphiti_client import get_graphiti
        from guardkit.knowledge.entities.turn_state import TurnStateEntity, TurnMode
        from datetime import datetime

        graphiti = get_graphiti()
        entity = TurnStateEntity(
            id="TURN-FEAT-GE-1",
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Implemented feature",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=datetime.now(),
            completed_at=datetime.now()
        )
        await capture_turn_state(graphiti, entity)
    """
    # Graceful degradation: return early if client is None
    if graphiti_client is None:
        logger.debug("Graphiti client is None, skipping turn state capture")
        return

    # Graceful degradation: return early if client is disabled
    if not graphiti_client.enabled:
        logger.debug("Graphiti is disabled, skipping turn state capture")
        return

    try:
        # Serialize entity to JSON
        episode_body = entity.to_episode_body()
        content = json.dumps(episode_body)

        # Generate episode name matching acceptance criteria format:
        # turn_{feature_id}_{task_id}_turn{N}
        episode_name = f"turn_{entity.feature_id}_{entity.task_id}_turn{entity.turn_number}"

        # Add episode to Graphiti
        await graphiti_client.add_episode(
            name=episode_name,
            content=content,
            group_id="turn_states",
            source_description=f"Turn state capture for {entity.task_id} turn {entity.turn_number}"
        )

        logger.info(f"Captured turn state: {entity.id}")

    except Exception as e:
        # Graceful degradation: log and continue
        logger.warning(f"Error capturing turn state {entity.id}: {e}")


async def load_turn_continuation_context(
    graphiti_client,
    feature_id: str,
    task_id: str,
    current_turn: int
) -> Optional[str]:
    """Load context for Turn N when N > 1.

    Queries Graphiti for the previous turn's state and formats it as
    actionable context for the current turn. Returns None for turn 1
    (no previous turn to learn from) or if Graphiti is unavailable.

    Args:
        graphiti_client: Graphiti client instance (can be None)
        feature_id: Feature identifier (e.g., "FEAT-GE")
        task_id: Task identifier (e.g., "TASK-GE-001")
        current_turn: Current turn number (1-indexed)

    Returns:
        Formatted markdown string with previous turn summary, or None if:
        - current_turn is 1 (no previous turn)
        - Graphiti is unavailable or disabled
        - No previous turn found
        - An error occurs during retrieval

    Example:
        from guardkit.knowledge.graphiti_client import get_graphiti

        graphiti = get_graphiti()
        context = await load_turn_continuation_context(
            graphiti,
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            current_turn=2
        )

        if context:
            # Inject into Player prompt
            prompt = f"## Previous Turn Context\\n{context}\\n\\n## Your Task..."
    """
    # No previous turn for turn 1
    if current_turn <= 1:
        logger.debug("Turn 1 has no previous turn to load")
        return None

    # Graceful degradation: return None if client is None
    if graphiti_client is None:
        logger.debug("Graphiti client is None, returning None for turn context")
        return None

    # Graceful degradation: return None if client is disabled
    if not graphiti_client.enabled:
        logger.debug("Graphiti is disabled, returning None for turn context")
        return None

    try:
        # Query for previous turn state
        prev_turn_num = current_turn - 1
        query = f"turn_state {task_id} turn {prev_turn_num}"

        results = await graphiti_client.search(
            query=query,
            group_ids=["turn_states"]
        )

        if not results:
            logger.debug(f"No previous turn found for {task_id} turn {prev_turn_num}")
            return None

        # Get the first result
        result = results[0]
        body = result.get("body", {})

        if not body or not isinstance(body, dict):
            logger.debug(f"Malformed turn state result for {task_id}")
            return None

        # Format as actionable context
        context_lines = [
            f"## Previous Turn Summary (Turn {prev_turn_num})",
            f"**What was attempted**: {body.get('player_summary', 'Unknown')}",
            f"**Player decision**: {body.get('player_decision', 'Unknown')}",
            f"**Coach decision**: {body.get('coach_decision', 'Unknown')}",
        ]

        # Include coach feedback if present
        coach_feedback = body.get('coach_feedback')
        if coach_feedback:
            context_lines.append(f"**Coach feedback**: {coach_feedback}")

        # Include blockers if present
        blockers = body.get('blockers_found', [])
        if blockers:
            blockers_str = ", ".join(blockers)
            context_lines.append(f"**Blockers found**: {blockers_str}")

        # Include lessons learned
        lessons = body.get('lessons_from_turn', [])
        if lessons:
            lessons_str = "; ".join(lessons)
            context_lines.append(f"**Lessons learned**: {lessons_str}")

        # Include suggested next focus
        next_focus = body.get('what_to_try_next')
        if next_focus:
            context_lines.append(f"**Suggested focus for this turn**: {next_focus}")

        # Include acceptance criteria status
        ac_status = body.get('acceptance_criteria_status', {})
        if ac_status:
            context_lines.append("")
            context_lines.append("**Acceptance Criteria Status**:")
            for criterion, status in ac_status.items():
                if status == "completed":
                    icon = "✓"
                elif status == "rejected" or status == "failed":
                    icon = "✗"
                else:
                    icon = "○"
                context_lines.append(f"  {icon} {criterion}: {status}")

        return "\n".join(context_lines)

    except Exception as e:
        logger.warning(f"Error loading turn continuation context: {e}")
        return None


def create_turn_state_from_autobuild(
    feature_id: str,
    task_id: str,
    turn_number: int,
    player_summary: str,
    player_decision: str,
    coach_decision: str,
    coach_feedback: Optional[str] = None,
    mode: TurnMode = TurnMode.CONTINUING_WORK,
    blockers_found: Optional[List[str]] = None,
    progress_summary: str = "",
    acceptance_criteria_status: Optional[Dict[str, str]] = None,
    files_modified: Optional[List[str]] = None,
    tests_passed: Optional[int] = None,
    tests_failed: Optional[int] = None,
    coverage: Optional[float] = None,
    arch_score: Optional[int] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    duration_seconds: Optional[int] = None,
    lessons_from_turn: Optional[List[str]] = None,
    what_to_try_next: Optional[str] = None,
) -> TurnStateEntity:
    """Create TurnStateEntity from AutoBuild turn data.

    This is a convenience factory function for creating TurnStateEntity
    instances from AutoBuild orchestrator data. It generates the ID and
    provides sensible defaults for optional fields.

    Args:
        feature_id: Feature identifier (e.g., "FEAT-GE")
        task_id: Task identifier (e.g., "TASK-GE-001")
        turn_number: Turn number (1-indexed)
        player_summary: What Player implemented/attempted
        player_decision: Player's decision ("implemented" | "failed" | "blocked")
        coach_decision: Coach's decision ("approved" | "feedback" | "rejected")
        coach_feedback: Specific feedback if not approved
        mode: Turn mode (default: CONTINUING_WORK)
        blockers_found: List of blockers (default: empty list)
        progress_summary: Brief progress description
        acceptance_criteria_status: AC status dict (default: empty)
        files_modified: List of files created/modified (default: empty list)
        tests_passed: Number of tests passed
        tests_failed: Number of tests failed
        coverage: Test coverage percentage
        arch_score: Architectural review score
        started_at: Turn start time (default: now)
        completed_at: Turn end time (default: now)
        duration_seconds: Turn duration
        lessons_from_turn: Lessons learned (default: empty list)
        what_to_try_next: Suggested next focus

    Returns:
        TurnStateEntity ready for capture

    Example:
        from guardkit.knowledge.turn_state_operations import (
            create_turn_state_from_autobuild,
            capture_turn_state,
        )
        from guardkit.knowledge.entities.turn_state import TurnMode
        from guardkit.knowledge.graphiti_client import get_graphiti

        # After AutoBuild turn completes
        entity = create_turn_state_from_autobuild(
            feature_id="FEAT-GE",
            task_id="TASK-GE-001",
            turn_number=1,
            player_summary="Implemented OAuth2 authentication",
            player_decision="implemented",
            coach_decision="feedback",
            coach_feedback="Add session caching",
            mode=TurnMode.FRESH_START,
        )

        graphiti = get_graphiti()
        await capture_turn_state(graphiti, entity)
    """
    now = datetime.now()

    return TurnStateEntity(
        id=f"TURN-{feature_id}-{turn_number}",
        feature_id=feature_id,
        task_id=task_id,
        turn_number=turn_number,
        player_summary=player_summary,
        player_decision=player_decision,
        coach_decision=coach_decision,
        coach_feedback=coach_feedback,
        mode=mode,
        blockers_found=blockers_found or [],
        progress_summary=progress_summary,
        acceptance_criteria_status=acceptance_criteria_status or {},
        files_modified=files_modified or [],
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        coverage=coverage,
        arch_score=arch_score,
        started_at=started_at or now,
        completed_at=completed_at or now,
        duration_seconds=duration_seconds,
        lessons_from_turn=lessons_from_turn or [],
        what_to_try_next=what_to_try_next,
    )
