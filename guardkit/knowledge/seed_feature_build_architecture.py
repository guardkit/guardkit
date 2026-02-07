"""
Feature-build architecture seeding for GuardKit knowledge graph.

Seeds detailed knowledge about feature-build architecture, Player-Coach
pattern, and delegation into Graphiti for context-aware AI assistance.
"""

import logging

from guardkit.knowledge.seed_helpers import _add_episodes

logger = logging.getLogger(__name__)


async def seed_feature_build_architecture(client) -> None:
    """Seed detailed knowledge about feature-build architecture.

    Creates 7 episodes covering the Player-Coach pattern and delegation.

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("feature_build_overview", {
            "entity_type": "architecture",
            "name": "Feature-Build Architecture",
            "purpose": "Autonomous task implementation with quality assurance via adversarial Player-Coach pattern",
            "key_insight": "Player DELEGATES to task-work, does NOT implement directly. This achieves 100% code reuse of quality gates.",
            "modes": {
                "single_task": "/feature-build TASK-XXX",
                "feature": "/feature-build FEAT-XXX"
            }
        }),
        ("feature_build_three_phases", {
            "entity_type": "architecture",
            "name": "Feature-Build Three-Phase Pattern",
            "phases": {
                "setup": [
                    "Load task/feature file",
                    "Create isolated git worktree",
                    "Initialize branch: autobuild/{id}"
                ],
                "loop": [
                    "Pre-loop: Execute design phase via task-work --design-only",
                    "Loop: Player-Coach turns until approval or max_turns",
                    "Player: task-work --implement-only",
                    "Coach: Validate results independently"
                ],
                "finalize": [
                    "Preserve worktree (never auto-merge)",
                    "Save final state to frontmatter",
                    "Display results with next steps"
                ]
            }
        }),
        ("feature_build_player_agent", {
            "entity_type": "agent",
            "name": "AutoBuild Player Agent",
            "file": ".claude/agents/autobuild-player.md",
            "purpose": "Implement task by delegating to task-work",
            "critical_behavior": "Player MUST delegate to /task-work, NOT implement directly",
            "delegation_pattern": "/task-work TASK-XXX --implement-only --mode=tdd",
            "tools_available": ["Read", "Write", "Edit", "Bash"],
            "why_delegate": "100% code reuse of quality gates (Phase 3-5.5)"
        }),
        ("feature_build_coach_agent", {
            "entity_type": "agent",
            "name": "AutoBuild Coach Agent",
            "file": ".claude/agents/autobuild-coach.md",
            "purpose": "Validate Player's implementation independently",
            "critical_behavior": "Coach has READ-ONLY access - validates but cannot modify",
            "tools_available": ["Read", "Bash (read-only commands only)"],
            "validation_approach": [
                "Read task_work_results.json from Player's execution",
                "Run tests independently (trust but verify)",
                "Check acceptance criteria",
                "Either APPROVE or provide FEEDBACK"
            ]
        }),
        ("feature_build_task_work_delegation", {
            "entity_type": "architecture",
            "name": "Task-Work Delegation Architecture",
            "description": "How AutoBuild delegates to task-work for 100% quality gate reuse",
            "flow": {
                "pre_loop": {
                    "command": "/task-work TASK-XXX --design-only",
                    "phases_executed": "1.6 (Clarification) -> 2 (Planning) -> 2.5 (Review) -> 2.8 (Checkpoint)"
                },
                "player_turn": {
                    "command": "/task-work TASK-XXX --implement-only --mode=tdd",
                    "phases_executed": "3 (Implement) -> 4 (Test) -> 4.5 (Fix Loop) -> 5 (Review) -> 5.5 (Audit)"
                }
            },
            "invocation_method": "SDK query() with prompt containing slash command",
            "NOT_subprocess": "Do NOT use subprocess.run(['guardkit', 'task-work', ...]) - CLI doesn't have this command"
        }),
        ("feature_build_file_locations", {
            "entity_type": "architecture",
            "name": "Feature-Build File Locations",
            "critical_paths": {
                "worktree": {
                    "single_task": ".guardkit/worktrees/TASK-XXX/",
                    "feature": ".guardkit/worktrees/FEAT-XXX/"
                },
                "artifacts": {
                    "pattern": ".guardkit/autobuild/{task_id}/"
                },
                "task_work_results": ".guardkit/autobuild/{task_id}/task_work_results.json",
                "implementation_plan": ".claude/task-plans/TASK-XXX-implementation-plan.md"
            }
        }),
        ("feature_build_feature_yaml_schema", {
            "entity_type": "schema",
            "name": "Feature YAML Schema",
            "location": ".guardkit/features/FEAT-XXX.yaml",
            "required_fields": {
                "feature_level": ["id", "name", "tasks", "orchestration"],
                "task_level": ["id", "file_path"],
                "orchestration_level": ["parallel_groups"]
            },
            "critical_field": "file_path - each task MUST have path to its markdown file"
        })
    ]

    await _add_episodes(client, episodes, "feature_build_architecture", "feature-build architecture", entity_type="feature_build_architecture")
