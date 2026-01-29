"""
Failed approach seeding module for GuardKit knowledge graph.

Seeds Graphiti with initial failed approaches captured from TASK-REV-7549 analysis.
These represent known mistakes that were repeated across sessions because failures
weren't captured for future reference.

Initial Failed Approaches (from review findings):
1. FAIL-SUBPROCESS - Using subprocess.run() for task-work invocation
2. FAIL-TASK-PATH - Using TASK-XXX ID for worktree path in feature mode
3. FAIL-MOCK-PRELOOP - Pre-loop returning mock data instead of real task-work
4. FAIL-SCHEMA-MISMATCH - Writing/reading different JSON field names
5. FAIL-ALL-TESTS - Running all tests instead of task-specific in feature mode

Usage:
    from guardkit.knowledge.seed_failed_approaches import seed_failed_approaches
    from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig

    client = GraphitiClient(GraphitiConfig())
    await client.initialize()
    await seed_failed_approaches(client)
"""

import json
import logging
from typing import List

from guardkit.knowledge.entities.failed_approach import (
    FailedApproachEpisode,
    Severity,
)
from guardkit.knowledge.failed_approach_manager import FAILED_APPROACHES_GROUP_ID

logger = logging.getLogger(__name__)


def get_initial_failed_approaches() -> List[FailedApproachEpisode]:
    """Get the initial set of failed approaches to seed.

    Returns:
        List of FailedApproachEpisode instances based on TASK-REV-7549 findings.
    """
    return [
        FailedApproachEpisode(
            id="FAIL-SUBPROCESS",
            approach="Using subprocess.run() to invoke guardkit task-work",
            symptom="subprocess.CalledProcessError: Command 'guardkit task-work' not found",
            root_cause="CLI command doesn't exist - task-work is a Claude Code slash command",
            fix_applied="Use SDK query() to invoke '/task-work TASK-XXX' as a subagent",
            prevention=(
                "BEFORE implementing task-work invocation, check ADR-FB-001. "
                "If symptom contains 'subprocess' or 'Command not found', use SDK query() instead."
            ),
            context="feature-build",
            related_adrs=["ADR-FB-001"],
            severity=Severity.CRITICAL,
            occurrences=3,
        ),
        FailedApproachEpisode(
            id="FAIL-TASK-PATH",
            approach="Using TASK-XXX ID for worktree path construction",
            symptom="FileNotFoundError at .guardkit/worktrees/TASK-XXX/...",
            root_cause="In feature mode, worktree is shared and named after feature (FEAT-XXX), not individual tasks",
            fix_applied="Use feature_worktree_id for path construction",
            prevention=(
                "BEFORE constructing worktree paths, check ADR-FB-002. "
                "In feature mode, always use FEAT-XXX, never TASK-XXX."
            ),
            context="feature-build",
            related_adrs=["ADR-FB-002"],
            severity=Severity.HIGH,
            occurrences=2,
        ),
        FailedApproachEpisode(
            id="FAIL-MOCK-PRELOOP",
            approach="TaskWorkInterface.execute_design_phase() returning mock data",
            symptom="Pre-loop returns suspiciously round values (complexity=5, arch_score=80)",
            root_cause="Stub implementation returning placeholder data instead of invoking real task-work",
            fix_applied="Implement execute_design_phase() with SDK query() to '/task-work --design-only'",
            prevention=(
                "BEFORE trusting pre-loop results, verify they come from real task-work invocation. "
                "Check ADR-FB-003. Suspiciously round numbers indicate mock data."
            ),
            context="feature-build",
            related_adrs=["ADR-FB-003"],
            severity=Severity.CRITICAL,
            occurrences=2,
        ),
        FailedApproachEpisode(
            id="FAIL-SCHEMA-MISMATCH",
            approach="Writing results to 'quality_gates' but reading from 'test_results'",
            symptom="Coach can't find test results, defaults to score=0",
            root_cause="Schema mismatch between task-work writer and CoachValidator reader",
            fix_applied="Aligned schema to use 'quality_gates' consistently",
            prevention=(
                "BEFORE reading/writing shared JSON files, verify schema alignment between writer and reader. "
                "Check for existing field names in both components."
            ),
            context="feature-build",
            severity=Severity.HIGH,
            occurrences=4,
        ),
        FailedApproachEpisode(
            id="FAIL-ALL-TESTS",
            approach="Running 'pytest tests/' to verify task-specific changes",
            symptom="Unrelated test failures from other tasks in shared worktree",
            root_cause="In feature mode, tests/ contains tests from ALL tasks, not just current task",
            fix_applied="Implemented task-specific test filtering",
            prevention=(
                "BEFORE running tests in feature mode, filter to task-specific tests only. "
                "Or use --ignore patterns to exclude other task tests."
            ),
            context="feature-build",
            severity=Severity.MEDIUM,
            occurrences=4,
        ),
    ]


async def seed_failed_approaches(client, force: bool = False) -> bool:
    """Seed initial failed approaches into Graphiti.

    Args:
        client: GraphitiClient instance (required)
        force: If True, re-seed even if entries might exist

    Returns:
        True if seeding completed successfully
        False if client is disabled or None
    """
    # Handle None client
    if client is None:
        logger.warning("Failed approach seeding skipped: client is None")
        return False

    # Handle disabled client
    if not client.enabled:
        logger.warning("Failed approach seeding skipped: Graphiti client is disabled")
        return False

    logger.info("Seeding initial failed approaches...")

    initial_failures = get_initial_failed_approaches()
    success_count = 0
    error_count = 0

    for failure in initial_failures:
        try:
            episode_body = failure.to_episode_body()
            episode_name = f"failed_approach_{failure.id}"

            await client.add_episode(
                name=episode_name,
                episode_body=json.dumps(episode_body),
                group_id=FAILED_APPROACHES_GROUP_ID,
            )

            success_count += 1
            logger.debug(f"  Seeded {failure.id}")

        except Exception as e:
            error_count += 1
            logger.warning(f"  Failed to seed {failure.id}: {e}")
            # Continue with other failures

    if error_count > 0:
        logger.warning(
            f"Failed approach seeding completed with errors: "
            f"{success_count} succeeded, {error_count} failed"
        )
    else:
        logger.info(f"Successfully seeded {success_count} failed approaches")

    return error_count == 0
