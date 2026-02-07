"""
Architecture decisions seeding for GuardKit knowledge graph.

Seeds key architecture decisions into Graphiti for context-aware AI assistance.
"""

import logging

from guardkit.knowledge.seed_helpers import _add_episodes

logger = logging.getLogger(__name__)


async def seed_architecture_decisions(client) -> None:
    """Seed key architecture decisions.

    Creates 3 episodes covering critical design decisions.

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("issue_sdk_not_subprocess", {
            "issue_type": "architecture_decision",
            "decision": "Use SDK query() for task-work invocation",
            "not": "subprocess to guardkit CLI",
            "rationale": "CLI command 'guardkit task-work' does not exist. SDK query() can invoke slash commands directly.",
            "correct_pattern": 'query(prompt="/task-work TASK-XXX --implement-only", cwd=worktree_path)',
            "wrong_pattern": 'subprocess.run(["guardkit", "task-work", task_id])'
        }),
        ("issue_feature_mode_paths", {
            "issue_type": "architecture_decision",
            "decision": "In feature mode, paths use FEAT-XXX worktree ID",
            "not": "individual TASK-XXX IDs for worktree paths",
            "rationale": "Feature mode uses a shared worktree for all tasks. Task IDs are for task management, not filesystem paths.",
            "correct_pattern": ".guardkit/worktrees/FEAT-XXX/.guardkit/autobuild/TASK-XXX/",
            "wrong_pattern": ".guardkit/worktrees/TASK-XXX/.guardkit/autobuild/TASK-XXX/"
        }),
        ("issue_preloop_must_invoke", {
            "issue_type": "architecture_decision",
            "decision": "Pre-loop must invoke /task-work --design-only to generate implementation plan",
            "not": "return mock data from stub implementation",
            "rationale": "Player expects implementation_plan.md to exist. Pre-loop must actually run the design phases.",
            "component": "TaskWorkInterface.execute_design_phase()",
            "status": "stub returns mock data, needs real SDK integration"
        })
    ]

    await _add_episodes(client, episodes, "architecture_decisions", "architecture decisions", entity_type="architecture_decision")
