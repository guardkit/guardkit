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

    Creates 19 episodes covering all major commands and their workflows.

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
        }),
        ("command_task_review", {
            "entity_type": "command",
            "name": "/task-review",
            "purpose": "Structured analysis and decision-making for task reviews",
            "syntax": "/task-review TASK-XXX [--mode=MODE] [--depth=DEPTH]",
            "modes": [
                "architectural - Architecture and design review",
                "code-quality - Code quality and best practices",
                "decision - Decision analysis and recommendations",
                "security - Security-focused review",
                "technical-debt - Technical debt assessment"
            ],
            "depth_options": ["quick", "standard", "comprehensive"],
            "decision_checkpoint": "[A]ccept / [R]evise / [I]mplement / [C]ancel",
            "outputs": "Review report with findings and recommendations"
        }),
        ("command_task_refine", {
            "entity_type": "command",
            "name": "/task-refine",
            "purpose": "Iterative code refinement based on review feedback",
            "syntax": "/task-refine TASK-XXX",
            "workflow": [
                "1. Load task and existing implementation",
                "2. Apply refinement suggestions from review",
                "3. Re-run quality gates",
                "4. Update task state"
            ],
            "prerequisite": "Task should have review feedback to refine against"
        }),
        ("command_task_status", {
            "entity_type": "command",
            "name": "/task-status",
            "purpose": "View task progress dashboard with epic and feature context",
            "syntax": "/task-status [TASK-XXX]",
            "features": [
                "Individual task status with phase progress",
                "Feature-level progress rollup",
                "Epic-level progress overview",
                "Quality gate status summary"
            ],
            "outputs": "Progress dashboard with state, quality gates, and context"
        }),
        ("command_feature_complete", {
            "entity_type": "command",
            "name": "/feature-complete",
            "purpose": "Merge and archive AutoBuild results for completed features",
            "syntax": "/feature-complete TASK-XXX [--dry-run] [--verify]",
            "actions": [
                "Verify all feature tasks are complete",
                "Merge AutoBuild worktree to main branch",
                "Archive feature artifacts",
                "Update feature status"
            ],
            "key_flags": {
                "--dry-run": "Preview merge without executing",
                "--verify": "Run verification checks before merge"
            }
        }),
        ("command_debug", {
            "entity_type": "command",
            "name": "/debug",
            "purpose": "Systematic bug investigation and root cause analysis",
            "syntax": "/debug",
            "workflow": [
                "1. Collect error context and reproduction steps",
                "2. Analyze error patterns and stack traces",
                "3. Identify root cause through systematic investigation",
                "4. Propose and validate fix"
            ],
            "outputs": "Root cause analysis with recommended fix"
        }),
        ("command_system_overview", {
            "entity_type": "command",
            "name": "/system-overview",
            "purpose": "Architecture summary showing project structure and components",
            "syntax": "/system-overview [--verbose] [--section=SECTION]",
            "sections": [
                "Architecture - Component relationships and data flow",
                "Stack - Technology stack and dependencies",
                "Structure - Project directory layout",
                "Workflows - Key development workflows"
            ],
            "outputs": "Comprehensive architecture summary"
        }),
        ("command_impact_analysis", {
            "entity_type": "command",
            "name": "/impact-analysis",
            "purpose": "Pre-task architecture validation and change impact assessment",
            "syntax": "/impact-analysis TASK-XXX [--depth=DEPTH]",
            "analysis_areas": [
                "Files and components affected by the change",
                "Dependency chain impact",
                "Risk assessment (breaking changes, data migrations)",
                "Test coverage implications"
            ],
            "outputs": "Impact report with risk level and affected components"
        }),
        ("command_context_switch", {
            "entity_type": "command",
            "name": "/context-switch",
            "purpose": "Multi-project navigation for switching between codebases",
            "syntax": "/context-switch [project-name]",
            "features": [
                "Save current project context",
                "Load target project context",
                "Restore settings and state",
                "Cross-project knowledge sharing via Graphiti"
            ],
            "outputs": "Context switched with project settings loaded"
        }),
        ("cli_guardkit_review", {
            "entity_type": "command",
            "name": "guardkit review",
            "purpose": "CLI command for task review with optional knowledge capture",
            "syntax": "guardkit review TASK-XXX [--mode=MODE] [--depth=DEPTH] [--capture-knowledge] [--enable-context/--no-context]",
            "key_flags": {
                "--capture-knowledge / -ck": "Trigger knowledge capture after review completes",
                "--mode": "Review mode (architectural, code-quality, decision, security, technical-debt)",
                "--depth": "Review depth (quick, standard, comprehensive)",
                "--enable-context/--no-context": "Enable/disable Graphiti context retrieval"
            },
            "note": "When --no-context is set, --capture-knowledge is automatically suppressed"
        }),
        ("cli_guardkit_graphiti", {
            "entity_type": "command",
            "name": "guardkit graphiti",
            "purpose": "Knowledge graph management CLI with subcommands",
            "subcommands": {
                "seed": "Seed system context into Graphiti (--force to re-seed)",
                "status": "Show connection status and episode counts (--verbose for all groups)",
                "verify": "Run test queries to verify seeded knowledge",
                "capture": "Interactive Q&A knowledge capture (--interactive --focus AREA)",
                "search": "Search knowledge graph ('query' --group GROUP --limit N)",
                "show": "Show details of specific knowledge by ID",
                "list": "List all knowledge in a category (features, adrs, patterns, constraints, all)",
                "clear": "Clear knowledge graph data (--confirm required, --dry-run for preview)",
                "add-context": "Add context from files (PATH --type TYPE --pattern GLOB)"
            }
        }),
        ("workflow_review_to_implement", {
            "entity_type": "workflow",
            "name": "Review to Implementation Flow",
            "description": "Flow from task review through decision checkpoint to implementation",
            "steps": [
                "1. /task-create 'Title' task_type:review",
                "2. /task-review TASK-REV-XXX --mode=architectural",
                "3. Decision checkpoint: [A]ccept/[R]evise/[I]mplement/[C]ancel",
                "4. On [I]mplement: Auto-creates implementation task(s) with parent_review link",
                "5. /task-work TASK-FIX-XXX (implementation task from review)"
            ],
            "key_concept": "parent_review field in task frontmatter provides traceability from review to implementation"
        }),
        ("workflow_design_first", {
            "entity_type": "workflow",
            "name": "Design-First Workflow",
            "description": "Split design and implementation into separate sessions",
            "steps": [
                "1. /task-work TASK-XXX --design-only (Phases 1-2.8)",
                "2. Task moves to design_approved state with saved plan",
                "3. Human reviews implementation plan in docs/state/TASK-XXX/",
                "4. /task-work TASK-XXX --implement-only (Phases 3-5)",
                "5. Task proceeds through implementation using approved design"
            ],
            "use_cases": [
                "Complex tasks (complexity >= 7) requiring upfront design approval",
                "Multi-day tasks where design and implementation happen on different days",
                "Architect-led design with developer-led implementation"
            ]
        })
    ]

    await _add_episodes(client, episodes, "command_workflows", "command workflows", entity_type="command_workflow")
