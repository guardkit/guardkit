"""
Task outcome capture and management.

This module provides functionality for capturing task outcomes
as episodes in the knowledge-memory backend (fleet-memory; formerly
Graphiti). All operations are designed for graceful degradation - they
will succeed even when the memory backend is unavailable.

Public API:
    capture_task_outcome: Capture a task outcome as an episode
    capture_task_outcome_verified: The same write, but the caller is told
        whether the episode was actually published to the broker
    OutcomeCapture: What one capture attempt achieved
    OutcomeManager: Class-based interface for outcome management

Example:
    from guardkit.knowledge.outcome_manager import capture_task_outcome
    from guardkit.knowledge.entities.outcome import OutcomeType

    outcome_id = await capture_task_outcome(
        outcome_type=OutcomeType.TASK_COMPLETED,
        task_id="TASK-1234",
        task_title="Implement OAuth2",
        task_requirements="Add OAuth2 authentication",
        success=True,
        summary="Successfully implemented OAuth2 with PKCE"
    )
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional, List, NamedTuple

from guardkit.knowledge.fleet_memory_client import get_memory_client
from guardkit.knowledge.entities.outcome import OutcomeType, TaskOutcome

logger = logging.getLogger(__name__)

# Group ID for task outcomes in the memory backend
TASK_OUTCOMES_GROUP_ID = "task_outcomes"


class OutcomeCapture(NamedTuple):
    """What one capture attempt actually achieved.

    ``outcome_id`` is always generated, even when nothing is written — it is
    the local name for this outcome, not proof of a write.

    ``episode_key`` says the episode was HANDED TO THE BROKER, and that is the
    strongest thing this seam can honestly claim. It is ``None`` whenever the
    publish did not happen: memory off, the client missing, the group unmapped,
    the broker unreachable, the episode unbuildable, the publish refused. The
    memory client is fail-open by design (a store that is down must never break
    a build), so a caller that wants to say anything out loud has to read this
    field — the absence of an exception proves nothing.

    WHAT ``episode_key`` IS NOT — read this before writing a log line about it.
    It is NOT a receipt from the store. It is the episode's deterministic
    NATURAL KEY (``"{payload_type}:{project}:{identifier}"``), computed LOCALLY
    from the payload before anything is sent
    (``fleet_memory_payloads.build_memory_episode`` sets ``episode_id`` to it,
    and ``FleetMemoryClient.add_episode`` echoes that same string back). The
    publish beneath it is core NATS — ``NATSClient.publish_episode`` calls
    ``nc.publish(...)`` with no JetStream ack and no round trip to the store —
    so a successful publish means the bytes left this process, nothing more.

    Which means these three failures ALL still produce a non-``None``
    ``episode_key``: a dark relay, a stream that is unmapped or full, and a
    relay-side validation refusal. Store-side landing is a DIFFERENT question
    with a different answer: fleet-memory's own liveness fence (see
    ``docs/ways-of-working/memory-reconnection-shipped-2026-08-03.md``), which
    exists precisely because a working relay and a dead one look identical from
    the publisher's side. Do not make this field answer it.

    Attributes:
        outcome_id: Local outcome id, format ``OUT-XXXXXXXX``. Always present.
        episode_key: The locally-minted natural key, echoed back when the
            episode was published to the broker; else ``None``.
        detail: Plain-language reason when nothing was published, else ``None``.
    """

    outcome_id: str
    episode_key: Optional[str] = None
    detail: Optional[str] = None

    @property
    def published(self) -> bool:
        """True only when the episode was published to the broker.

        NOT "the store has it" — see the class docstring. This deliberately
        does not carry the word "stored": the seam cannot see the store.
        """
        return self.episode_key is not None


def _generate_outcome_id() -> str:
    """Generate a unique outcome ID.

    Returns:
        Unique ID in format OUT-XXXXXXXX (8 uppercase hex chars)
    """
    return f"OUT-{uuid.uuid4().hex[:8].upper()}"


async def capture_task_outcome(
    outcome_type: OutcomeType,
    task_id: str,
    task_title: str,
    task_requirements: str,
    success: bool,
    summary: str,
    approach_used: Optional[str] = None,
    patterns_used: Optional[List[str]] = None,
    problems_encountered: Optional[List[str]] = None,
    lessons_learned: Optional[List[str]] = None,
    tests_written: Optional[int] = None,
    test_coverage: Optional[float] = None,
    review_cycles: Optional[int] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    duration_minutes: Optional[int] = None,
    feature_id: Optional[str] = None,
    related_adr_ids: Optional[List[str]] = None,
) -> str:
    """Capture a task outcome as an episode in the memory backend.

    Creates a TaskOutcome instance and publishes it to the memory backend as an
    episode. Gracefully degrades if the memory backend is unavailable - still
    returns the generated outcome ID.

    NOTE: the returned id says only that an outcome was NAMED, never that it
    was PUBLISHED — this function returns the same id whether the publish
    happened or the broker was unreachable. A caller that needs to know whether
    the episode was handed to the broker must use
    ``capture_task_outcome_verified``. Neither function can tell you the STORE
    has it; nothing on this path reads the store back.

    Args:
        outcome_type: Type of outcome from OutcomeType enum
        task_id: Task ID that this outcome belongs to
        task_title: Human-readable title of the task
        task_requirements: Original task requirements/description
        success: Whether the outcome was successful
        summary: Brief summary of the outcome
        approach_used: Description of the approach taken (optional)
        patterns_used: List of design patterns applied (optional)
        problems_encountered: List of problems faced (optional)
        lessons_learned: List of lessons learned (optional)
        tests_written: Number of tests written (optional)
        test_coverage: Test coverage percentage (optional)
        review_cycles: Number of review cycles (optional)
        started_at: When work started (optional)
        completed_at: When work completed (optional)
        duration_minutes: Total duration in minutes (optional)
        feature_id: Related feature ID if applicable (optional)
        related_adr_ids: List of related ADR IDs (optional)

    Returns:
        Unique outcome ID in format OUT-XXXXXXXX

    Example:
        outcome_id = await capture_task_outcome(
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-1234",
            task_title="Implement OAuth2",
            task_requirements="Add OAuth2 authentication",
            success=True,
            summary="Successfully implemented"
        )
    """
    capture = await capture_task_outcome_verified(
        outcome_type=outcome_type,
        task_id=task_id,
        task_title=task_title,
        task_requirements=task_requirements,
        success=success,
        summary=summary,
        approach_used=approach_used,
        patterns_used=patterns_used,
        problems_encountered=problems_encountered,
        lessons_learned=lessons_learned,
        tests_written=tests_written,
        test_coverage=test_coverage,
        review_cycles=review_cycles,
        started_at=started_at,
        completed_at=completed_at,
        duration_minutes=duration_minutes,
        feature_id=feature_id,
        related_adr_ids=related_adr_ids,
    )
    return capture.outcome_id


async def capture_task_outcome_verified(
    outcome_type: OutcomeType,
    task_id: str,
    task_title: str,
    task_requirements: str,
    success: bool,
    summary: str,
    approach_used: Optional[str] = None,
    patterns_used: Optional[List[str]] = None,
    problems_encountered: Optional[List[str]] = None,
    lessons_learned: Optional[List[str]] = None,
    tests_written: Optional[int] = None,
    test_coverage: Optional[float] = None,
    review_cycles: Optional[int] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    duration_minutes: Optional[int] = None,
    feature_id: Optional[str] = None,
    related_adr_ids: Optional[List[str]] = None,
) -> OutcomeCapture:
    """Capture a task outcome and report whether it reached the broker.

    Same write as ``capture_task_outcome``, same graceful degradation — no
    exception ever escapes to the caller. The difference is honesty about the
    result: the returned ``OutcomeCapture`` carries the episode's key when the
    episode was published and ``None`` when it was not, so a caller can log a
    publish only when one really happened.

    This exists because the write path below it is fail-open all the way down.
    ``FleetMemoryClient.add_episode`` swallows every error and returns ``None``,
    so "no exception" is not evidence of a publish, and a caller that treats it
    as evidence prints a green line about an episode nobody sent.

    THE LIMIT OF THIS VERIFICATION, stated plainly: it reaches the broker and
    stops. ``episode_key`` is the deterministic natural key minted locally
    before the send, not a receipt from the store, and the publish under it is
    core NATS with no ack. So "published" is TRUE and "the store has it" is
    UNKNOWN — a dark relay or a refused ingest both look like success here.
    Store-side landing is fleet-memory's liveness fence's question, not this
    function's. See ``OutcomeCapture`` for the full statement.

    Args:
        Same as ``capture_task_outcome``.

    Returns:
        OutcomeCapture: ``outcome_id`` always; ``episode_key`` only on publish.

    Example:
        capture = await capture_task_outcome_verified(...)
        if capture.published:
            print(f"sent to memory as: {capture.episode_key}")
    """
    # Generate unique ID
    outcome_id = _generate_outcome_id()

    # Create TaskOutcome instance
    outcome = TaskOutcome(
        id=outcome_id,
        outcome_type=outcome_type,
        task_id=task_id,
        task_title=task_title,
        task_requirements=task_requirements,
        success=success,
        summary=summary,
        approach_used=approach_used,
        patterns_used=patterns_used,
        problems_encountered=problems_encountered,
        lessons_learned=lessons_learned,
        tests_written=tests_written,
        test_coverage=test_coverage,
        review_cycles=review_cycles,
        started_at=started_at,
        completed_at=completed_at,
        duration_minutes=duration_minutes,
        feature_id=feature_id,
        related_adr_ids=related_adr_ids,
    )

    # Generate episode body
    episode_body = outcome.to_episode_body()

    # Create episode name
    episode_name = f"{outcome_id}: {task_id} - {task_title}"

    # Attempt to publish via memory client (graceful degradation)
    # Routes through factory: graphiti | fleet_memory | dual (TASK-MEM08-004)
    client = get_memory_client()

    if client is None:
        logger.debug("[Memory] Client unavailable, skipping outcome capture")
        return OutcomeCapture(outcome_id, None, "the memory client is unavailable")

    if not client.enabled:
        logger.debug("[Memory] Client disabled, skipping outcome capture")
        return OutcomeCapture(outcome_id, None, "memory is off")

    try:
        episode_key = await client.add_episode(
            name=episode_name,
            episode_body=json.dumps(episode_body),
            group_id=TASK_OUTCOMES_GROUP_ID,
            source="auto_captured",
            entity_type="task_outcome"
        )
    except Exception as e:
        logger.warning(f"[Memory] Failed to publish outcome {outcome_id}: {e}")
        return OutcomeCapture(
            outcome_id, None, f"the writer raised {type(e).__name__}: {e}"
        )

    if episode_key is None:
        # The client is fail-open: it has already logged the real reason.
        logger.warning(
            f"[Memory] Outcome {outcome_id} for {task_id} was NOT published — "
            f"the memory writer accepted the call but sent nothing (see the "
            f"fleet-memory warning above for why)."
        )
        return OutcomeCapture(
            outcome_id, None, "the memory writer published nothing"
        )

    # ``episode_key`` here is the natural key the payload builder minted
    # locally, echoed back after a core-NATS publish with no ack. It proves the
    # send, not the landing. See ``OutcomeCapture``.
    logger.info(
        f"[Memory] Published task outcome {outcome_id} for {task_id} "
        f"to the broker as {episode_key}"
    )
    return OutcomeCapture(outcome_id, str(episode_key))


class OutcomeManager:
    """Class-based interface for outcome management.

    Provides a stateful interface for managing task outcomes.
    This class wraps the module-level functions for convenience.

    Example:
        manager = OutcomeManager()
        outcome_id = await manager.capture(
            outcome_type=OutcomeType.TASK_COMPLETED,
            task_id="TASK-1234",
            task_title="Implement OAuth2",
            task_requirements="Add OAuth2",
            success=True,
            summary="Done"
        )
    """

    async def capture(
        self,
        outcome_type: OutcomeType,
        task_id: str,
        task_title: str,
        task_requirements: str,
        success: bool,
        summary: str,
        **kwargs,
    ) -> str:
        """Capture a task outcome.

        Delegates to capture_task_outcome function.

        Args:
            outcome_type: Type of outcome from OutcomeType enum
            task_id: Task ID that this outcome belongs to
            task_title: Human-readable title of the task
            task_requirements: Original task requirements/description
            success: Whether the outcome was successful
            summary: Brief summary of the outcome
            **kwargs: Additional optional fields

        Returns:
            Unique outcome ID in format OUT-XXXXXXXX
        """
        return await capture_task_outcome(
            outcome_type=outcome_type,
            task_id=task_id,
            task_title=task_title,
            task_requirements=task_requirements,
            success=success,
            summary=summary,
            **kwargs,
        )
