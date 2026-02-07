"""
Command workflows seeding for GuardKit knowledge graph.

Seeds knowledge about command workflows and how they connect into Graphiti
for context-aware AI assistance.
"""

import logging

from guardkit.knowledge.seed_helpers import _add_episodes

logger = logging.getLogger(__name__)


async def seed_command_workflows(client) -> None:
    """Seed knowledge about command workflows and how they connect.

    Creates 7 episodes covering all major commands and their workflows.

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("workflow_overview", {
            "entity_type": "workflow",
            "name": "Core GuardKit Workflow",
            "summary": "Create -> Work -> Complete (with quality gates)",
            "commands_in_order": [
                "/task-create - Create a new task",
                "/task-work - Implement the task with quality gates",
                "/task-complete - Mark task done after review"
            ],
            "alternative_flows": [
                "Feature flow: /feature-plan -> /feature-build -> /task-complete (bulk)",
                "Review flow: /task-create task_type:review -> /task-review -> /task-complete",
                "Design-first: /task-work --design-only -> approve -> /task-work --implement-only"
            ]
        }),
        ("command_task_create", {
            "entity_type": "command",
            "name": "/task-create",
            "purpose": "Create a new task with auto-generated ID and frontmatter",
            "syntax": '/task-create "Title" [priority:high|medium|low] [task_type:implementation|review]',
            "creates": "tasks/backlog/TASK-XXXX-title-slug.md",
            "id_format": "TASK-XXXX (4 hex chars from hash)",
            "outputs": "Task markdown file with YAML frontmatter"
        }),
        ("command_task_work", {
            "entity_type": "command",
            "name": "/task-work",
            "purpose": "Implement a task through the 5-phase quality gate workflow",
            "syntax": "/task-work TASK-XXX [--mode=standard|tdd|bdd] [--design-only|--implement-only] [--micro]",
            "phases_executed": "Phase 1 (Load) -> Phase 2 (Plan) -> Phase 2.5 (Review) -> Phase 3 (Implement) -> Phase 4 (Test) -> Phase 5 (Review)",
            "key_flags": {
                "--design-only": "Stop at Phase 2.8 checkpoint, save implementation plan",
                "--implement-only": "Start at Phase 3, requires approved plan from --design-only",
                "--micro": "Streamlined workflow for trivial tasks (skip planning phases)",
                "--mode=tdd": "Test-driven development (write tests first)"
            },
            "critical_requirement": "Must be run from PROJECT ROOT directory, not GuardKit directory"
        }),
        ("command_task_complete", {
            "entity_type": "command",
            "name": "/task-complete",
            "purpose": "Mark task as complete after human review",
            "syntax": "/task-complete TASK-XXX",
            "actions": [
                "Move task file to tasks/completed/YYYY-MM/",
                "Update task status in frontmatter",
                "Generate completion summary"
            ],
            "prerequisite": "Task should have passed quality gates via /task-work or /feature-build"
        }),
        ("command_feature_plan", {
            "entity_type": "command",
            "name": "/feature-plan",
            "purpose": "Plan a feature and auto-generate subtasks with dependency ordering",
            "syntax": '/feature-plan "feature description"',
            "workflow": [
                "1. Create review task automatically",
                "2. Execute architectural review",
                "3. Present decision checkpoint [A]ccept/[R]evise/[I]mplement/[C]ancel",
                "4. On [I]mplement: Generate feature YAML and task markdown files"
            ],
            "outputs": {
                "feature_yaml": ".guardkit/features/FEAT-XXXX.yaml",
                "task_files": "tasks/backlog/{feature-slug}/TASK-XXX-*.md"
            },
            "enables": "/feature-build for autonomous implementation"
        }),
        ("command_feature_build", {
            "entity_type": "command",
            "name": "/feature-build",
            "purpose": "Autonomous task implementation using Player-Coach adversarial workflow",
            "syntax": "/feature-build TASK-XXX or /feature-build FEAT-XXX",
            "workflow": [
                "1. Create isolated git worktree",
                "2. Run Player-Coach dialectical loop",
                "3. Player implements via task-work delegation",
                "4. Coach validates independently",
                "5. Iterate until approval or max turns",
                "6. Preserve worktree for human review (never auto-merge)"
            ],
            "key_principle": "Player delegates to /task-work, does NOT implement directly"
        }),
        ("workflow_feature_to_build", {
            "entity_type": "workflow",
            "name": "Feature Planning to Build Flow",
            "description": "Complete flow from feature idea to implemented code",
            "steps": [
                "1. /feature-plan 'add OAuth2 authentication'",
                "2. /feature-build FEAT-A1B2",
                "3. Review worktree: cd .guardkit/worktrees/FEAT-A1B2 && git diff main",
                "4. Merge: git checkout main && git merge autobuild/FEAT-A1B2",
                "5. /task-complete TASK-001 TASK-002 (bulk complete)"
            ],
            "benefits": [
                "Zero manual task creation",
                "Automatic dependency ordering",
                "Parallel execution where possible",
                "Human review before merge"
            ]
        })
    ]

    await _add_episodes(client, episodes, "command_workflows", "command workflows", entity_type="command_workflow")
