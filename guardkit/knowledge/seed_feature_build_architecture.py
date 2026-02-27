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

    Creates 8 episodes covering the Player-Coach pattern and delegation.

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
                "Create criteria_verification entry for each completion_promise (criterion_id tracking)",
                "Factor in Honesty Verification results (honesty_score from CoachVerifier)",
                "Validate against Gherkin scenarios when available (from /feature-spec)",
                "Validate against Assumptions Manifest when available",
                "Either APPROVE or provide FEEDBACK"
            ],
            "promise_verification": {
                "description": "Structured tracking of acceptance criteria completion",
                "schema": "criteria_verification array with criterion_id, result (verified/rejected), notes",
                "rule": "APPROVE only if ALL criteria verified; FEEDBACK if ANY rejected"
            },
            "honesty_verification": {
                "description": "Pre-validated by CoachVerifier before Coach is invoked",
                "flow": "Player Report -> CoachVerifier -> Honesty Context -> Coach",
                "honesty_score": "0.0 to 1.0 (1.0 = all claims verified)",
                "discrepancy_types": ["test_result (critical)", "file_existence (critical)", "test_count (warning)"],
                "rule": "honesty_score < 0.5 = MUST provide feedback; < 0.8 with critical discrepancies = strongly consider feedback"
            }
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
        }),
        ("feature_build_assumptions_flow", {
            "entity_type": "architecture",
            "name": "Assumptions Manifest Pipeline",
            "description": "How /feature-spec assumptions flow through the AutoBuild pipeline",
            "flow": [
                "1. /feature-spec generates _assumptions.yaml with confidence levels (high/medium/low)",
                "2. Human reviews assumptions during Gherkin curation (Phase 5)",
                "3. /feature-plan reads assumptions, flags low-confidence in task metadata",
                "4. AutoBuild Player reads assumptions as Graphiti context",
                "5. Coach validates implementation against BOTH Gherkin AND assumptions manifest",
                "6. If Player silently changed an assumption, Coach detects divergence"
            ],
            "gating_rules": {
                "high_confidence": "Auto-proceed",
                "medium_confidence": "Coach reviews, may auto-approve",
                "low_confidence": "Mandatory human review before implementation"
            },
            "key_insight": "Assumptions are defence-in-depth Layer 1 - they reduce ambiguity upstream before AutoBuild begins",
            "integration_with_coach": "Coach reads _assumptions.yaml alongside .feature file to detect divergence from specification"
        })
    ]

    await _add_episodes(client, episodes, "feature_build_architecture", "feature-build architecture", entity_type="feature_build_architecture")
