"""
Integration points seeding for GuardKit knowledge graph.

Seeds integration point documentation into Graphiti for context-aware
AI assistance.
"""

import logging

from guardkit.knowledge.seed_helpers import _add_episodes

logger = logging.getLogger(__name__)


async def seed_integration_points(client) -> None:
    """Seed integration point documentation.

    Creates 3 episodes covering component connections.

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("integration_autobuild_to_taskwork", {
            "issue_type": "integration_point",
            "name": "autobuild_to_taskwork",
            "connects": ["AutoBuildOrchestrator", "task-work slash command"],
            "correct_protocol": "sdk_query",
            "correct_pattern": 'query("/task-work TASK-XXX --implement-only", cwd=worktree_path)',
            "wrong_protocol": "subprocess",
            "wrong_pattern": 'subprocess.run(["guardkit", "task-work", ...])'
        }),
        ("integration_coach_result_path", {
            "issue_type": "integration_point",
            "name": "coach_result_path",
            "connects": ["CoachValidator", "task_work_results.json"],
            "correct_pattern": ".guardkit/worktrees/FEAT-XXX/.guardkit/autobuild/TASK-XXX/task_work_results.json",
            "wrong_pattern": ".guardkit/worktrees/TASK-XXX/.guardkit/autobuild/TASK-XXX/task_work_results.json",
            "rule": "Use feature worktree ID in feature mode, task ID in single-task mode"
        }),
        ("integration_feature_spec_to_plan", {
            "issue_type": "integration_point",
            "name": "feature_spec_to_feature_plan",
            "connects": ["/feature-spec", "/feature-plan", "AutoBuild Coach"],
            "correct_pattern": "/feature-plan 'Feature' --context features/{name}/{name}_summary.md",
            "outputs_produced": {
                "feature_file": "features/{name}/{name}.feature - consumed by Coach during AutoBuild",
                "assumptions_manifest": "features/{name}/{name}_assumptions.yaml - consumed by Coach for divergence detection",
                "summary": "features/{name}/{name}_summary.md - consumed by /feature-plan as structured context"
            },
            "rule": "/feature-plan reads _summary.md for task decomposition; Coach reads .feature and _assumptions.yaml during AutoBuild validation"
        })
    ]

    await _add_episodes(client, episodes, "integration_points", "integration points", entity_type="integration_point")
