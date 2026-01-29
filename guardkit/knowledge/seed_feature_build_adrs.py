"""
Feature Build ADR Seeding Module.

Seeds critical Architecture Decision Records (ADRs) for feature-build workflow.
These ADRs encode lessons learned from feature-build failures to prevent future
sessions from repeating the same mistakes.

ADRs Seeded:
- ADR-FB-001: Use SDK query() for task-work invocation, NOT subprocess
- ADR-FB-002: In feature mode, paths use FEAT-XXX worktree ID, NOT individual TASK-XXX IDs
- ADR-FB-003: Pre-loop phase MUST invoke /task-work --design-only, NOT return mock data

Usage:
    from guardkit.knowledge.seed_feature_build_adrs import (
        FEATURE_BUILD_ADRS,
        seed_feature_build_adrs,
    )

    # Seed ADRs to Graphiti
    client = get_graphiti()
    await seed_feature_build_adrs(client)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# =============================================================================
# FEATURE BUILD ADRS
# =============================================================================

FEATURE_BUILD_ADRS: List[Dict[str, Any]] = [
    {
        "id": "ADR-FB-001",
        "title": "Use SDK query() for task-work invocation, NOT subprocess",
        "status": "ACCEPTED",
        "context": (
            "AutoBuild Player agent needs to invoke /task-work --implement-only "
            "to delegate implementation to the full task-work quality gate pipeline. "
            "The question is how to invoke this command from Python code."
        ),
        "decision": (
            "Use Claude Agents SDK query() function to invoke slash commands directly. "
            "The SDK query() can include slash commands in the prompt text, which "
            "Claude Code will execute. Do NOT use subprocess to invoke CLI commands."
        ),
        "rationale": [
            "The guardkit CLI does not have a task-work subcommand - it is a slash command",
            "SDK query() creates fresh Claude Code sessions that can execute slash commands",
            "Subprocess to non-existent CLI commands causes CalledProcessError failures",
            "SDK invocation provides proper context and tool access for subagent execution",
            "Slash commands are the correct interface for Claude Code integration",
        ],
        "rejected_alternatives": [
            "subprocess.run(['guardkit', 'task-work', ...]) - CLI command does not exist",
            "subprocess.run(['claude', '/task-work', ...]) - Not the correct invocation pattern",
            "Direct Python function calls - Would bypass quality gates and agent infrastructure",
        ],
        "violation_symptoms": [
            "subprocess.CalledProcessError when invoking 'guardkit task-work'",
            "FileNotFoundError or 'command not found' for guardkit CLI",
            "Task-work results not generated (no task_work_results.json)",
            "Quality gates skipped or not executed",
        ],
        "related_failures": [
            "Player agent fails with subprocess error",
            "Implementation produced without quality gate verification",
        ],
        "decided_at": datetime(2025, 1, 15, tzinfo=timezone.utc).isoformat(),
        "decided_by": "feature-build-review",
        "group_id": "architecture_decisions",
    },
    {
        "id": "ADR-FB-002",
        "title": "In feature mode, paths use FEAT-XXX worktree ID, NOT individual TASK-XXX IDs",
        "status": "ACCEPTED",
        "context": (
            "Feature-build can operate in two modes: single-task mode (TASK-XXX) "
            "and feature mode (FEAT-XXX). In feature mode, multiple tasks share "
            "a single worktree. The question is what ID to use for worktree paths."
        ),
        "decision": (
            "In feature mode, all filesystem paths must use the FEAT-XXX worktree ID, "
            "not individual TASK-XXX IDs. The worktree is created once at "
            ".guardkit/worktrees/FEAT-XXX/ and all tasks execute within it."
        ),
        "rationale": [
            "Feature mode uses a shared worktree for all tasks in the feature",
            "The worktree directory is named after the feature ID, not task IDs",
            "Task IDs are used for task management and artifact subdirectories",
            "Artifacts go in .guardkit/worktrees/FEAT-XXX/.guardkit/autobuild/TASK-XXX/",
            "Using TASK-XXX for worktree paths causes FileNotFoundError",
        ],
        "rejected_alternatives": [
            "Using TASK-XXX for worktree paths - Creates separate worktrees per task",
            "Using both IDs interchangeably - Causes path confusion and file not found errors",
        ],
        "violation_symptoms": [
            "FileNotFoundError when accessing .guardkit/worktrees/TASK-XXX/",
            "Task results not found at expected paths",
            "Coach cannot find task_work_results.json after Player execution",
            "Worktree path mismatch between setup and execution phases",
        ],
        "related_failures": [
            "Coach validation fails with missing results file",
            "Player execution succeeds but artifacts written to wrong location",
        ],
        "decided_at": datetime(2025, 1, 15, tzinfo=timezone.utc).isoformat(),
        "decided_by": "feature-build-review",
        "group_id": "architecture_decisions",
    },
    {
        "id": "ADR-FB-003",
        "title": "Pre-loop phase MUST invoke /task-work --design-only, NOT return mock data",
        "status": "ACCEPTED",
        "context": (
            "The pre-loop phase of feature-build should execute design phases "
            "(Phases 1.6-2.8) before the Player-Coach loop begins. This generates "
            "the implementation plan that Player needs for implementation."
        ),
        "decision": (
            "Pre-loop MUST invoke the real /task-work --design-only slash command "
            "via SDK query() to generate the implementation plan. Never use stub "
            "implementations that return hardcoded mock data."
        ),
        "rationale": [
            "Player agent expects implementation_plan.md to exist in .claude/task-plans/",
            "The plan contains file list, test strategy, and complexity evaluation",
            "Mock data (stub returning complexity=5, arch_score=80) breaks the workflow",
            "Real design phases create artifacts that subsequent phases depend on",
            "Skipping design phase causes 'implementation plan not found' errors",
        ],
        "rejected_alternatives": [
            "Stub implementation returning mock complexity and arch scores",
            "Hardcoded implementation plan template without analysis",
            "Skip pre-loop entirely and let Player do planning",
        ],
        "violation_symptoms": [
            "Player fails with 'implementation plan not found' error",
            "Pre-loop returns hardcoded values like complexity=5, arch_score=80",
            "No .claude/task-plans/TASK-XXX-implementation-plan.md created",
            "Player attempts to implement without architectural review",
        ],
        "related_failures": [
            "TaskWorkInterface.execute_design_phase() returns mock data",
            "Missing implementation plan causes Player to fail or improvise",
        ],
        "decided_at": datetime(2025, 1, 15, tzinfo=timezone.utc).isoformat(),
        "decided_by": "feature-build-review",
        "group_id": "architecture_decisions",
    },
]


# =============================================================================
# SEEDING FUNCTION
# =============================================================================

async def seed_feature_build_adrs(client) -> None:
    """Seed feature-build ADRs into Graphiti.

    Creates episodes for each feature-build ADR to enable runtime
    retrieval and context injection during autonomous builds.

    Args:
        client: GraphitiClient instance (handles None/disabled gracefully)

    Example:
        from guardkit.knowledge import get_graphiti
        from guardkit.knowledge.seed_feature_build_adrs import seed_feature_build_adrs

        client = get_graphiti()
        await seed_feature_build_adrs(client)
    """
    # Handle None client gracefully
    if client is None:
        logger.debug("Graphiti client is None, skipping feature-build ADR seeding")
        return

    # Handle disabled client gracefully
    if not client.enabled:
        logger.debug("Graphiti is disabled, skipping feature-build ADR seeding")
        return

    # Seed each ADR as an episode
    for adr in FEATURE_BUILD_ADRS:
        # Create episode name from ADR ID
        # ADR-FB-001 -> adr_fb_001
        episode_name = adr["id"].lower().replace("-", "_")

        # Create episode body with entity_type marker
        episode_body = {
            "entity_type": "architecture_decision",
            **adr,
        }

        try:
            await client.add_episode(
                name=episode_name,
                episode_body=json.dumps(episode_body),
                group_id="architecture_decisions",
            )
            logger.info(f"Seeded feature-build ADR: {adr['id']}")
        except Exception as e:
            logger.warning(f"Failed to seed feature-build ADR {adr['id']}: {e}")
            # Continue with other ADRs
