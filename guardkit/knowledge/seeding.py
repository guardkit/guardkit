"""
System context seeding module for GuardKit knowledge graph.

Seeds Graphiti with comprehensive knowledge about GuardKit - what it is,
how it works, and what feature-build is supposed to do. This provides the
"big picture" context that prevents Claude Code sessions from making
decisions in isolation.

Episode Categories:
- product_knowledge: What GuardKit is and its core philosophy
- command_workflows: How commands flow together
- quality_gate_phases: The 5-phase structure underpinning task-work
- technology_stack: Python CLI, Claude Code, SDK, worktrees
- feature_build_architecture: How feature-build orchestrates task-work
- architecture_decisions: Key design decisions
- failure_patterns: Known failures and their fixes
- component_status: What's complete/incomplete
- integration_points: How components connect
- templates: Template metadata for semantic search
- agents: Agent capabilities and boundaries
- patterns: Design pattern knowledge
- rules: Rule applicability and code examples
- failed_approaches: Failed approaches with prevention guidance (TASK-GE-004)

Usage:
    from guardkit.knowledge.seeding import seed_all_system_context
    from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig

    client = GraphitiClient(GraphitiConfig())
    await client.initialize()
    await seed_all_system_context(client)
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Version for tracking seeding updates
SEEDING_VERSION = "1.0.0"


# =============================================================================
# MARKER FILE MANAGEMENT
# =============================================================================

def get_state_dir() -> Path:
    """Get the state directory for seeding markers.

    Returns:
        Path to the .guardkit/seeding directory, created if needed.
    """
    # Use project-local .guardkit directory
    state_dir = Path.cwd() / ".guardkit" / "seeding"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def is_seeded() -> bool:
    """Check if system context has been seeded.

    Returns:
        True if seeding marker file exists, False otherwise.
    """
    marker_path = get_state_dir() / ".graphiti_seeded.json"
    return marker_path.exists()


def mark_seeded() -> None:
    """Create marker file indicating seeding is complete."""
    marker_path = get_state_dir() / ".graphiti_seeded.json"
    marker_data = {
        "seeded": True,
        "version": SEEDING_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    marker_path.write_text(json.dumps(marker_data, indent=2))
    logger.info(f"Created seeding marker at {marker_path}")


def clear_seeding_marker() -> None:
    """Remove the seeding marker file.

    Safe to call even if marker doesn't exist.
    """
    marker_path = get_state_dir() / ".graphiti_seeded.json"
    if marker_path.exists():
        marker_path.unlink()
        logger.info(f"Removed seeding marker from {marker_path}")


# =============================================================================
# HELPER FUNCTION FOR EPISODE CREATION
# =============================================================================

async def _add_episodes(client, episodes: list, group_id: str, category_name: str) -> None:
    """Add multiple episodes to Graphiti with error handling.

    Automatically injects _metadata block into each episode body for tracking
    and deduplication purposes.

    Args:
        client: GraphitiClient instance
        episodes: List of (name, body_dict) tuples
        group_id: Group ID for all episodes
        category_name: Human-readable category name for logging
    """
    if not client.enabled:
        logger.debug(f"Skipping {category_name} seeding - client disabled")
        return

    for name, body in episodes:
        try:
            # Inject metadata block into body (TASK-GR-PRE-000-A)
            timestamp = datetime.now(timezone.utc).isoformat()
            body_with_metadata = {
                **body,
                "_metadata": {
                    "source": "guardkit_seeding",
                    "version": SEEDING_VERSION,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                    "source_hash": None,  # Generated content, not file-based
                    "entity_id": name,  # Use episode name as unique ID
                }
            }
            await client.add_episode(
                name=name,
                episode_body=json.dumps(body_with_metadata),
                group_id=group_id
            )
        except Exception as e:
            logger.warning(f"Failed to seed episode {name}: {e}")
            # Continue with other episodes


# =============================================================================
# 1. PRODUCT KNOWLEDGE
# =============================================================================

async def seed_product_knowledge(client) -> None:
    """Seed core product knowledge about GuardKit.

    Creates 3 episodes:
    - guardkit_overview: What GuardKit is
    - guardkit_value_proposition: Why it exists
    - guardkit_installation: How to install
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("guardkit_overview", {
            "entity_type": "product",
            "name": "GuardKit",
            "tagline": "Lightweight AI-Assisted Development with Quality Gates",
            "description": (
                "GuardKit is a lightweight, pragmatic task workflow system with built-in "
                "quality gates that prevents broken code from reaching production. It bridges "
                "the gap between AI capabilities and human oversight.\n\n"
                "Core Features:\n"
                "- Quality Gates: Architectural review (Phase 2.5) and test enforcement (Phase 4.5)\n"
                "- Simple Workflow: Create -> Work -> Complete (3 commands)\n"
                "- AI Collaboration: AI handles implementation, humans make decisions\n"
                "- No Ceremony: Minimal process, maximum productivity"
            ),
            "target_users": ["solo developers", "small teams", "AI-augmented development"],
            "competitive_differentiator": "Quality gates that prevent broken code, not just task management"
        }),
        ("guardkit_value_proposition", {
            "entity_type": "value_prop",
            "problem": "AI coding assistants can generate code quickly but often produce broken, untested, or architecturally unsound code",
            "solution": "Quality gates that enforce test coverage and architectural review before code can be marked complete",
            "key_insight": "The value is not in generating code faster, but in preventing broken code from reaching production",
            "workflow": "AI handles implementation grunt work, humans make approval decisions at checkpoints"
        }),
        ("guardkit_installation", {
            "entity_type": "installation",
            "method": "Claude Code installer",
            "command": "/project:add-guardkit or manual installation",
            "creates": [
                ".claude/commands/*.md - Slash commands",
                ".claude/agents/*.md - Subagent definitions",
                ".claude/templates/ - Stack-specific templates",
                "tasks/ - Task directory structure"
            ],
            "note": "GuardKit installs INTO a project, it's not a standalone tool"
        })
    ]

    await _add_episodes(client, episodes, "product_knowledge", "product knowledge")


# =============================================================================
# 2. COMMAND WORKFLOWS
# =============================================================================

async def seed_command_workflows(client) -> None:
    """Seed knowledge about command workflows and how they connect.

    Creates 7 episodes covering all major commands and their workflows.
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

    await _add_episodes(client, episodes, "command_workflows", "command workflows")


# =============================================================================
# 3. QUALITY GATE PHASES
# =============================================================================

async def seed_quality_gate_phases(client) -> None:
    """Seed knowledge about the 5-phase quality gate structure.

    Creates 12 episodes covering all phases from 1 through 5.5.
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("phases_overview", {
            "entity_type": "architecture",
            "name": "Quality Gate Phases",
            "description": "task-work executes through 5 major phases with quality gates",
            "phases": [
                "Phase 1: Load Task Context",
                "Phase 2: Implementation Planning",
                "Phase 2.5: Architectural Review + Pattern Suggestions",
                "Phase 2.7: Complexity Evaluation",
                "Phase 2.8: Human Checkpoint (design approval)",
                "Phase 3: Implementation",
                "Phase 4: Testing",
                "Phase 4.5: Fix Loop (up to 3 iterations)",
                "Phase 5: Code Review",
                "Phase 5.5: Plan Audit"
            ],
            "critical_gates": [
                "Phase 2.5B: Architectural review blocks if SOLID/DRY/YAGNI violated",
                "Phase 2.8: Human must approve plan before implementation",
                "Phase 4.5: Tests must pass, coverage must meet threshold",
                "Phase 5: Code review must pass quality checks"
            ]
        }),
        ("phase_1_load", {
            "entity_type": "phase",
            "phase_number": "1",
            "name": "Load Task Context",
            "purpose": "Load task file, detect stack, gather requirements",
            "actions": [
                "Read task markdown from tasks/",
                "Parse YAML frontmatter",
                "Detect project technology stack",
                "Identify acceptance criteria"
            ]
        }),
        ("phase_1_6_clarification", {
            "entity_type": "phase",
            "phase_number": "1.6",
            "name": "Clarifying Questions",
            "purpose": "Ask user for clarification on ambiguous requirements",
            "gating": "Only runs if requirements are ambiguous",
            "skip_with": "--no-questions flag"
        }),
        ("phase_2_planning", {
            "entity_type": "phase",
            "phase_number": "2",
            "name": "Implementation Planning",
            "purpose": "Create detailed implementation plan",
            "actions": [
                "Analyze requirements and acceptance criteria",
                "Design solution approach",
                "Identify files to create/modify",
                "Plan test strategy",
                "Estimate complexity"
            ],
            "outputs": "implementation_plan.md in .claude/task-plans/"
        }),
        ("phase_2_5_review", {
            "entity_type": "phase",
            "phase_number": "2.5",
            "name": "Architectural Review + Pattern Suggestions",
            "purpose": "Review plan for architectural soundness",
            "subphases": {
                "2.5A": "Pattern Suggestions - Suggest applicable design patterns",
                "2.5B": "Architectural Review - Check SOLID, DRY, YAGNI compliance"
            },
            "can_block": True,
            "block_conditions": "Major SOLID/DRY/YAGNI violations"
        }),
        ("phase_2_7_complexity", {
            "entity_type": "phase",
            "phase_number": "2.7",
            "name": "Complexity Evaluation",
            "purpose": "Score task complexity 1-10 for process scaling",
            "scoring": {
                "1-3": "Simple - may use --micro mode",
                "4-6": "Medium - standard workflow",
                "7-10": "Complex - may need splitting or extra review"
            }
        }),
        ("phase_2_8_checkpoint", {
            "entity_type": "phase",
            "phase_number": "2.8",
            "name": "Human Checkpoint",
            "purpose": "Human approval of implementation plan before coding",
            "actions": [
                "Display implementation plan summary",
                "Present decision options: [A]pprove / [R]evise / [S]kip",
                "If Approve: Proceed to Phase 3",
                "If Revise: Return to Phase 2 with feedback"
            ],
            "critical": "This is the last stop before implementation begins",
            "design_only_stops_here": "--design-only flag stops at this phase"
        }),
        ("phase_3_implementation", {
            "entity_type": "phase",
            "phase_number": "3",
            "name": "Implementation",
            "purpose": "Execute the implementation plan",
            "actions": [
                "Create/modify files per plan",
                "Write production code",
                "Write tests (TDD: tests first, Standard: code first)"
            ],
            "implement_only_starts_here": "--implement-only flag starts at this phase"
        }),
        ("phase_4_testing", {
            "entity_type": "phase",
            "phase_number": "4",
            "name": "Testing",
            "purpose": "Run tests and verify coverage",
            "actions": [
                "Execute test suite",
                "Check coverage threshold",
                "Verify all acceptance criteria testable"
            ],
            "thresholds": {
                "coverage": "80% minimum (configurable)",
                "tests_passing": "100% required"
            }
        }),
        ("phase_4_5_fixloop", {
            "entity_type": "phase",
            "phase_number": "4.5",
            "name": "Fix Loop",
            "purpose": "Iterate to fix failing tests or coverage gaps",
            "max_iterations": 3,
            "actions": [
                "If tests fail: Analyze failure, apply fix, re-run",
                "If coverage low: Add tests, re-run",
                "Repeat until pass or max iterations"
            ],
            "failure_handling": "If still failing after 3 iterations, task is blocked"
        }),
        ("phase_5_review", {
            "entity_type": "phase",
            "phase_number": "5",
            "name": "Code Review",
            "purpose": "Review implemented code for quality",
            "checks": [
                "SOLID principles adherence",
                "DRY (no duplication)",
                "YAGNI (no over-engineering)",
                "Code style and conventions",
                "Security considerations"
            ]
        }),
        ("phase_5_5_audit", {
            "entity_type": "phase",
            "phase_number": "5.5",
            "name": "Plan Audit",
            "purpose": "Verify implementation matches plan",
            "actions": [
                "Compare implemented files to planned files",
                "Verify all acceptance criteria addressed",
                "Check for scope creep"
            ]
        })
    ]

    await _add_episodes(client, episodes, "quality_gate_phases", "quality gate phases")


# =============================================================================
# 4. TECHNOLOGY STACK
# =============================================================================

async def seed_technology_stack(client) -> None:
    """Seed knowledge about GuardKit's technology stack.

    Creates 7 episodes covering all major technology components.
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("tech_stack_overview", {
            "entity_type": "architecture",
            "name": "GuardKit Technology Stack",
            "layers": {
                "user_interface": "Claude Code slash commands (markdown files)",
                "orchestration": "Python CLI (guardkit-py) + AutoBuildOrchestrator",
                "ai_invocation": "Claude Agents SDK (query() function)",
                "agent_definitions": "Markdown files in .claude/agents/",
                "state_management": "Task frontmatter YAML + feature YAML files",
                "isolation": "Git worktrees for safe execution"
            }
        }),
        ("tech_claude_code_commands", {
            "entity_type": "technology",
            "name": "Claude Code Slash Commands",
            "location": ".claude/commands/*.md",
            "how_they_work": "Markdown files that Claude Code loads as available commands",
            "execution": "User types /command-name, Claude Code reads the markdown and follows instructions",
            "key_files": [
                "task-create.md", "task-work.md", "task-complete.md",
                "feature-plan.md", "feature-build.md", "task-review.md"
            ]
        }),
        ("tech_python_cli", {
            "entity_type": "technology",
            "name": "GuardKit Python CLI",
            "package": "guardkit-py",
            "commands": [
                "guardkit autobuild task TASK-XXX",
                "guardkit autobuild feature FEAT-XXX",
                "guardkit worktree cleanup TASK-XXX"
            ],
            "key_modules": {
                "guardkit/orchestrator/autobuild.py": "AutoBuildOrchestrator - main orchestration",
                "guardkit/orchestrator/agent_invoker.py": "AgentInvoker - SDK invocation"
            }
        }),
        ("tech_claude_agents_sdk", {
            "entity_type": "technology",
            "name": "Claude Agents SDK",
            "import": "from claude_agent_sdk import query, ClaudeAgentOptions",
            "key_function": "query() - invokes Claude with options",
            "capabilities": [
                "Fresh context per call (no cross-contamination)",
                "Tool restrictions via allowed_tools parameter",
                "Structured output via output_format parameter",
                "Working directory specification via cwd parameter"
            ],
            "critical_insight": "query() can invoke slash commands directly by including them in the prompt"
        }),
        ("tech_subagents", {
            "entity_type": "technology",
            "name": "Subagent Markdown Files",
            "location": ".claude/agents/*.md",
            "purpose": "Define specialized AI agents for specific tasks",
            "key_agents": [
                "autobuild-player.md - Implements code in feature-build",
                "autobuild-coach.md - Validates implementation in feature-build",
                "code-reviewer.md - Reviews code quality",
                "test-orchestrator.md - Manages test execution"
            ]
        }),
        ("tech_git_worktrees", {
            "entity_type": "technology",
            "name": "Git Worktrees for Isolation",
            "location": ".guardkit/worktrees/",
            "purpose": "Isolated environments for autonomous implementation",
            "how_used": [
                "feature-build creates worktree before implementation",
                "All changes happen in worktree, not main repo",
                "Human reviews worktree before merging"
            ],
            "naming": {
                "single_task": ".guardkit/worktrees/TASK-XXX/",
                "feature": ".guardkit/worktrees/FEAT-XXX/"
            }
        }),
        ("tech_state_management", {
            "entity_type": "technology",
            "name": "State Management",
            "task_state": {
                "location": "tasks/*/TASK-XXX-*.md frontmatter",
                "fields": ["status", "priority", "requirements", "acceptance_criteria"]
            },
            "feature_state": {
                "location": ".guardkit/features/FEAT-XXX.yaml",
                "fields": ["id", "name", "status", "tasks", "orchestration"]
            },
            "artifacts": {
                "location": ".guardkit/autobuild/{task_id}/",
                "files": ["player_turn_N.json", "coach_turn_N.json", "task_work_results.json"]
            }
        })
    ]

    await _add_episodes(client, episodes, "technology_stack", "technology stack")


# =============================================================================
# 5. FEATURE-BUILD ARCHITECTURE
# =============================================================================

async def seed_feature_build_architecture(client) -> None:
    """Seed detailed knowledge about feature-build architecture.

    Creates 7 episodes covering the Player-Coach pattern and delegation.
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

    await _add_episodes(client, episodes, "feature_build_architecture", "feature-build architecture")


# =============================================================================
# 6. ARCHITECTURE DECISIONS
# =============================================================================

async def seed_architecture_decisions(client) -> None:
    """Seed key architecture decisions.

    Creates 3 episodes covering critical design decisions.
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

    await _add_episodes(client, episodes, "architecture_decisions", "architecture decisions")


# =============================================================================
# 7. FAILURE PATTERNS
# =============================================================================

async def seed_failure_patterns(client) -> None:
    """Seed known failure patterns and their fixes.

    Creates 4 episodes covering common failures.
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

    await _add_episodes(client, episodes, "failure_patterns", "failure patterns")


# =============================================================================
# 8. COMPONENT STATUS
# =============================================================================

async def seed_component_status(client) -> None:
    """Seed component status tracking.

    Creates 2 episodes covering incomplete components.
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("component_taskwork_interface", {
            "issue_type": "component_status",
            "component": "TaskWorkInterface",
            "method": "execute_design_phase",
            "status": "stub",
            "notes": "Returns mock data (complexity=5, arch_score=80). Needs SDK query() integration to invoke /task-work --design-only."
        }),
        ("component_agent_invoker_delegation", {
            "issue_type": "component_status",
            "component": "AgentInvoker",
            "method": "_invoke_task_work_implement",
            "status": "incorrect",
            "problem": "Uses subprocess to non-existent CLI command",
            "needs": "SDK query() with slash command in prompt"
        })
    ]

    await _add_episodes(client, episodes, "component_status", "component status")


# =============================================================================
# 9. INTEGRATION POINTS
# =============================================================================

async def seed_integration_points(client) -> None:
    """Seed integration point documentation.

    Creates 2 episodes covering component connections.
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
        })
    ]

    await _add_episodes(client, episodes, "integration_points", "integration points")


# =============================================================================
# 10. TEMPLATES
# =============================================================================

async def seed_templates(client) -> None:
    """Seed template metadata for semantic search.

    Creates 4+ episodes covering available templates.
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("template_fastapi_python", {
            "entity_type": "template",
            "id": "fastapi-python",
            "name": "Python FastAPI Backend",
            "description": "Production-ready FastAPI template based on best practices from 12k+ star repository.",
            "language": "Python",
            "frameworks": ["FastAPI", "SQLAlchemy", "Pydantic", "pytest"],
            "patterns": ["Dependency Injection", "Repository Pattern", "CRUD Base Classes"],
            "complexity": 7,
            "production_ready": True
        }),
        ("template_react_typescript", {
            "entity_type": "template",
            "id": "react-typescript",
            "name": "React TypeScript Frontend",
            "description": "Modern React frontend with TypeScript, hooks, and comprehensive testing.",
            "language": "TypeScript",
            "frameworks": ["React", "TypeScript", "MSW", "Vitest"],
            "patterns": ["Component Composition", "Custom Hooks", "API Layer Abstraction"],
            "complexity": 6,
            "production_ready": True
        }),
        ("template_nextjs_fullstack", {
            "entity_type": "template",
            "id": "nextjs-fullstack",
            "name": "Next.js Fullstack",
            "description": "Full-stack Next.js application with App Router, Server Actions, and Prisma ORM.",
            "language": "TypeScript",
            "frameworks": ["Next.js", "Prisma", "Playwright"],
            "patterns": ["Server Components", "Server Actions", "App Router"],
            "complexity": 8,
            "production_ready": True
        }),
        ("template_default", {
            "entity_type": "template",
            "id": "default",
            "name": "Language-Agnostic Default",
            "description": "Minimal template for any language/framework combination.",
            "language": "Any",
            "frameworks": [],
            "patterns": ["SOLID", "DRY", "YAGNI"],
            "complexity": 3,
            "production_ready": True
        })
    ]

    await _add_episodes(client, episodes, "templates", "templates")


# =============================================================================
# 11. AGENTS
# =============================================================================

async def seed_agents(client) -> None:
    """Seed agent metadata for semantic search.

    Creates 7+ episodes covering available agents.
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("agent_fastapi_specialist", {
            "entity_type": "agent",
            "id": "fastapi-specialist",
            "name": "FastAPI Specialist",
            "role": "Implements FastAPI routes, dependencies, and middleware",
            "capabilities": ["API endpoint implementation", "Dependency injection", "Middleware configuration"],
            "technologies": ["FastAPI", "Pydantic", "Starlette"]
        }),
        ("agent_test_orchestrator", {
            "entity_type": "agent",
            "id": "test-orchestrator",
            "name": "Test Orchestrator",
            "role": "Orchestrates test execution and validates coverage",
            "capabilities": ["Test suite execution", "Coverage measurement", "Test fixture management"],
            "technologies": ["pytest", "pytest-asyncio", "pytest-cov"]
        }),
        ("agent_code_reviewer", {
            "entity_type": "agent",
            "id": "code-reviewer",
            "name": "Code Reviewer",
            "role": "Reviews code for quality, SOLID principles, and best practices",
            "capabilities": ["SOLID validation", "DRY analysis", "YAGNI assessment", "Security review"],
            "technologies": []
        }),
        ("agent_architectural_reviewer", {
            "entity_type": "agent",
            "id": "architectural-reviewer",
            "name": "Architectural Reviewer",
            "role": "Reviews implementation plans for architectural soundness",
            "capabilities": ["Architecture pattern validation", "Layer boundary enforcement", "Dependency analysis"],
            "technologies": []
        }),
        ("agent_autobuild_player", {
            "entity_type": "agent",
            "id": "autobuild-player",
            "name": "AutoBuild Player Agent",
            "role": "Implements tasks by delegating to task-work in Player-Coach pattern",
            "capabilities": ["Task-work delegation", "Implementation reporting", "Quality gate monitoring"],
            "critical_note": "Player MUST delegate to /task-work, NOT implement directly"
        }),
        ("agent_autobuild_coach", {
            "entity_type": "agent",
            "id": "autobuild-coach",
            "name": "AutoBuild Coach Agent",
            "role": "Validates Player implementations in Player-Coach pattern",
            "capabilities": ["Implementation validation", "Independent test execution", "Acceptance criteria verification"],
            "critical_note": "Coach has READ-ONLY access, validates but cannot modify"
        }),
        ("agent_pattern_suggester", {
            "entity_type": "agent",
            "id": "pattern-suggester",
            "name": "Pattern Suggester",
            "role": "Suggests applicable design patterns during planning",
            "capabilities": ["Pattern identification", "Template-specific patterns", "Best practice recommendations"],
            "technologies": []
        })
    ]

    await _add_episodes(client, episodes, "agents", "agents")


# =============================================================================
# 12. PATTERNS
# =============================================================================

async def seed_patterns(client) -> None:
    """Seed design pattern knowledge.

    Creates 5+ episodes covering design patterns.
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("pattern_dependency_injection", {
            "entity_type": "pattern",
            "id": "dependency_injection",
            "name": "Dependency Injection",
            "category": "structural",
            "description": "Dependencies are provided to a component rather than created by the component itself.",
            "benefits": ["Loose coupling", "Easy testing", "Flexible configuration"],
            "templates_using": ["fastapi-python", "nextjs-fullstack"]
        }),
        ("pattern_repository", {
            "entity_type": "pattern",
            "id": "repository_pattern",
            "name": "Repository Pattern",
            "category": "data_access",
            "description": "Abstracts data access logic into dedicated classes.",
            "benefits": ["Clean separation", "Easy to swap data sources", "Testable"],
            "templates_using": ["fastapi-python"]
        }),
        ("pattern_crud_base", {
            "entity_type": "pattern",
            "id": "crud_base_classes",
            "name": "CRUD Base Classes",
            "category": "data_access",
            "description": "Generic base classes for Create, Read, Update, Delete operations.",
            "benefits": ["DRY", "Consistent API", "Type-safe with generics"],
            "templates_using": ["fastapi-python"]
        }),
        ("pattern_server_components", {
            "entity_type": "pattern",
            "id": "server_components",
            "name": "Server Components",
            "category": "rendering",
            "description": "React components that render on the server.",
            "benefits": ["Reduced client bundle", "Direct database access", "Better SEO"],
            "templates_using": ["nextjs-fullstack"]
        }),
        ("pattern_player_coach", {
            "entity_type": "pattern",
            "id": "player_coach_adversarial",
            "name": "Player-Coach Adversarial Pattern",
            "category": "agent_orchestration",
            "description": "Adversarial cooperation where Player implements and Coach validates.",
            "benefits": ["Quality assurance", "Iterative improvement", "Trust but verify"],
            "templates_using": ["guardkit-default"]
        })
    ]

    await _add_episodes(client, episodes, "patterns", "patterns")


# =============================================================================
# 13. RULES
# =============================================================================

async def seed_rules(client) -> None:
    """Seed rule metadata for semantic search.

    Creates 4+ episodes covering code rules.
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("rule_fastapi_code_style", {
            "entity_type": "rule",
            "id": "fastapi-python_code-style",
            "name": "Python Code Style",
            "template_id": "fastapi-python",
            "path_patterns": ["**/*.py"],
            "topics": ["naming conventions", "module structure", "class patterns"],
            "key_rules": [
                "Use snake_case for functions and variables",
                "Use PascalCase for classes",
                "Use get_ prefix for dependency functions"
            ]
        }),
        ("rule_fastapi_async", {
            "entity_type": "rule",
            "id": "fastapi-python_async-patterns",
            "name": "Async Patterns",
            "template_id": "fastapi-python",
            "path_patterns": ["**/*.py"],
            "topics": ["async/await", "non-blocking I/O", "database sessions"],
            "key_rules": [
                "Use async def for I/O-bound routes",
                "Never use blocking I/O in async routes",
                "Use asyncio.sleep() not time.sleep() in async context"
            ]
        }),
        ("rule_fastapi_testing", {
            "entity_type": "rule",
            "id": "fastapi-python_testing",
            "name": "Testing Patterns",
            "template_id": "fastapi-python",
            "path_patterns": ["tests/**/*.py", "**/test_*.py"],
            "topics": ["pytest", "async testing", "fixtures"],
            "key_rules": [
                "Use @pytest.mark.asyncio for async tests",
                "Use httpx.AsyncClient for API testing",
                "Clean up test database after each test"
            ],
            "coverage_requirements": {
                "minimum_line": 80,
                "minimum_branch": 75
            }
        }),
        ("rule_react_component_patterns", {
            "entity_type": "rule",
            "id": "react-typescript_components",
            "name": "React Component Patterns",
            "template_id": "react-typescript",
            "path_patterns": ["**/*.tsx", "**/*.jsx"],
            "topics": ["component structure", "hooks", "props typing"],
            "key_rules": [
                "Use function components with hooks",
                "Define prop types with interfaces",
                "Extract custom hooks for reusable logic",
                "Use TypeScript strict mode"
            ]
        })
    ]

    await _add_episodes(client, episodes, "rules", "rules")


# =============================================================================
# 14. FAILED APPROACHES (TASK-GE-004)
# =============================================================================

async def seed_quality_gate_configs_wrapper(client) -> None:
    """Seed quality gate configurations for task-type/complexity-based thresholds.

    This wraps the seed_quality_gate_configs function to match the signature
    expected by the seed_all_system_context orchestrator.

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    from guardkit.knowledge.seed_quality_gate_configs import seed_quality_gate_configs
    await seed_quality_gate_configs(client)


async def seed_failed_approaches_wrapper(client) -> None:
    """Seed initial failed approaches from TASK-REV-7549 findings.

    This wraps the seed_failed_approaches function to match the signature
    expected by the seed_all_system_context orchestrator.

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    from guardkit.knowledge.seed_failed_approaches import seed_failed_approaches
    await seed_failed_approaches(client)


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

import sys


async def seed_all_system_context(client, force: bool = False) -> bool:
    """Seed all system context into Graphiti.

    Args:
        client: GraphitiClient instance (required)
        force: If True, re-seed even if already seeded

    Returns:
        True if seeding completed (or skipped because already seeded)
        False if client is disabled or None
    """
    # Handle None client
    if client is None:
        logger.warning("Seeding skipped: client is None")
        return False

    # Handle disabled client
    if not client.enabled:
        logger.warning("Seeding skipped: Graphiti client is disabled")
        return False

    # Check if already seeded
    if is_seeded() and not force:
        logger.info("System context already seeded, skipping (use force=True to re-seed)")
        return True

    logger.info("Seeding GuardKit system context...")

    # Track partial failures but continue
    had_errors = False

    # Get the current module dynamically to support patching in tests
    # sys.modules lookup happens at runtime, allowing unittest.mock.patch to work
    seeding_module = sys.modules[__name__]

    # Seed each category with error handling
    categories = [
        ("product_knowledge", "seed_product_knowledge"),
        ("command_workflows", "seed_command_workflows"),
        ("quality_gate_phases", "seed_quality_gate_phases"),
        ("technology_stack", "seed_technology_stack"),
        ("feature_build_architecture", "seed_feature_build_architecture"),
        ("architecture_decisions", "seed_architecture_decisions"),
        ("failure_patterns", "seed_failure_patterns"),
        ("component_status", "seed_component_status"),
        ("integration_points", "seed_integration_points"),
        ("templates", "seed_templates"),
        ("agents", "seed_agents"),
        ("patterns", "seed_patterns"),
        ("rules", "seed_rules"),
        ("failed_approaches", "seed_failed_approaches_wrapper"),  # TASK-GE-004
        ("quality_gate_configs", "seed_quality_gate_configs_wrapper"),  # TASK-GE-005
    ]

    for name, fn_name in categories:
        try:
            # Dynamic lookup enables unittest.mock.patch to work
            seed_fn = getattr(seeding_module, fn_name)
            await seed_fn(client)
            logger.info(f"  Seeded {name}")
        except Exception as e:
            logger.warning(f"  Failed to seed {name}: {e}")
            had_errors = True

    # Mark as seeded even with partial failures
    try:
        mark_seeded()
    except Exception as e:
        logger.warning(f"Failed to create seeding marker: {e}")
        had_errors = True

    if had_errors:
        logger.warning("System context seeding completed with some errors")
    else:
        logger.info("System context seeding complete")

    return True
