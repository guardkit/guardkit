"""
Failure patterns seeding for GuardKit knowledge graph.

Seeds known failure patterns and their fixes into Graphiti for context-aware
AI assistance.
"""

import logging

from guardkit.knowledge.seed_helpers import _add_episodes

logger = logging.getLogger(__name__)


async def seed_failure_patterns(client) -> None:
    """Seed known failure patterns and their fixes.

    Creates 4 episodes covering common failures.

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("failure_subprocess_to_cli", {
            "issue_type": "failure_pattern",
            "symptom": "subprocess.CalledProcessError or 'command not found' for guardkit task-work",
            "root_cause": "guardkit task-work CLI command does not exist",
            "fix": "Use SDK query() with slash command in prompt instead of subprocess"
        }),
        ("failure_wrong_worktree_path", {
            "issue_type": "failure_pattern",
            "symptom": "Task-work results not found at .guardkit/worktrees/TASK-XXX/.../task_work_results.json",
            "root_cause": "Path uses task ID instead of feature worktree ID in feature mode",
            "fix": "Use feature_worktree_id (FEAT-XXX) for path construction in feature mode"
        }),
        ("failure_mock_preloop_data", {
            "issue_type": "failure_pattern",
            "symptom": "Pre-loop returns hardcoded complexity=5, arch_score=80 instead of real values",
            "root_cause": "TaskWorkInterface.execute_design_phase() is stub that returns mock data",
            "fix": "Implement execute_design_phase() with real SDK query() to /task-work --design-only"
        }),
        ("failure_no_implementation_plan", {
            "issue_type": "failure_pattern",
            "symptom": "Player fails with 'implementation plan not found'",
            "root_cause": "Pre-loop didn't actually run design phases, so plan wasn't created",
            "fix": "Ensure pre-loop invokes /task-work --design-only which creates the plan",
            "chain": "Pre-loop mock -> No plan created -> Player can't read plan -> Failure"
        })
    ]

    await _add_episodes(client, episodes, "failure_patterns", "failure patterns", entity_type="failure_pattern")
