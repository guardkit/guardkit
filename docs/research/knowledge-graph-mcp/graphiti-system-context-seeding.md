# Graphiti Knowledge Seeding: GuardKit System Context

> **Purpose**: Seed Graphiti with comprehensive knowledge about GuardKit - what it is, how it works, and what feature-build is supposed to do. This provides the "big picture" context that prevents Claude Code sessions from making decisions in isolation.
>
> **Date**: January 2025
> **Status**: Ready for Implementation
> **Related**: `graphiti-prototype-integration-plan.md`, `feature-build-crisis-memory-analysis.md`

---

## Why This Matters

The current Graphiti plan seeds knowledge about:
- ❌ What went wrong (failures)
- ❌ Decisions made (architecture)

But NOT:
- ✅ What GuardKit IS
- ✅ How the command workflow flows
- ✅ What feature-build is supposed to accomplish
- ✅ The quality gate phases
- ✅ The technology stack and integration points

Without this "big picture" context, Claude Code sessions make locally-optimal decisions that conflict with the overall system design.

---

## Episode Categories for System Context

### 1. Product Knowledge (`group_id: "product_knowledge"`)

What GuardKit is and its core philosophy.

### 2. Command Workflows (`group_id: "command_workflows"`)

How the commands flow together: `/feature-plan` → `/task-create` → `/task-work` → `/task-complete`

### 3. Quality Gate Phases (`group_id: "quality_gate_phases"`)

The 5-phase structure that underpins task-work and feature-build.

### 4. Technology Stack (`group_id: "technology_stack"`)

Python CLI, Claude Code slash commands, Claude Agents SDK, subagent markdown files.

### 5. Feature-Build Architecture (`group_id: "feature_build_architecture"`)

Specifically what feature-build does and how it orchestrates task-work.

---

## Seeding Script

```python
"""
guardkit/knowledge/seed_system_context.py

Seeds Graphiti with comprehensive GuardKit system knowledge.
Run this ONCE after setting up Graphiti to establish baseline context.
"""

import asyncio
import json
from datetime import datetime, timezone

from .graphiti_client import init_graphiti, get_graphiti


async def seed_all_system_context():
    """Seed all system context into Graphiti."""
    
    await init_graphiti()
    graphiti = get_graphiti()
    
    if not graphiti.enabled:
        print("Graphiti not enabled, skipping seeding")
        return
    
    print("Seeding GuardKit system context...")
    
    # Seed in order of importance
    await seed_product_knowledge(graphiti)
    await seed_command_workflows(graphiti)
    await seed_quality_gate_phases(graphiti)
    await seed_technology_stack(graphiti)
    await seed_feature_build_architecture(graphiti)
    await seed_known_issues(graphiti)
    
    # Seed template/agent/pattern/rule knowledge
    await seed_template_knowledge(graphiti)
    await seed_agent_knowledge(graphiti)
    await seed_pattern_knowledge(graphiti)
    await seed_rule_knowledge(graphiti)
    
    print("✓ System context seeding complete")


# =============================================================================
# 1. PRODUCT KNOWLEDGE
# =============================================================================

async def seed_product_knowledge(graphiti):
    """Seed core product knowledge about GuardKit."""
    
    episodes = [
        {
            "name": "guardkit_overview",
            "body": {
                "entity_type": "product",
                "name": "GuardKit",
                "tagline": "Lightweight AI-Assisted Development with Quality Gates",
                "description": """
GuardKit is a lightweight, pragmatic task workflow system with built-in quality gates 
that prevents broken code from reaching production. It bridges the gap between AI 
capabilities and human oversight.

Core Features:
- Quality Gates: Architectural review (Phase 2.5) and test enforcement (Phase 4.5)
- Simple Workflow: Create → Work → Complete (3 commands)
- AI Collaboration: AI handles implementation, humans make decisions
- No Ceremony: Minimal process, maximum productivity

Core Principles:
1. Quality First: Never compromise on test coverage or architecture
2. Pragmatic Approach: Right amount of process for task complexity
3. AI/Human Collaboration: AI does heavy lifting, humans make decisions
4. Zero Ceremony: No unnecessary documentation or process
5. Fail Fast: Block bad code early, don't let it reach production
""",
                "target_users": ["solo developers", "small teams", "AI-augmented development"],
                "competitive_differentiator": "Quality gates that prevent broken code, not just task management"
            },
            "group_id": "product_knowledge"
        },
        {
            "name": "guardkit_value_proposition",
            "body": {
                "entity_type": "value_prop",
                "problem": "AI coding assistants can generate code quickly but often produce broken, untested, or architecturally unsound code",
                "solution": "Quality gates that enforce test coverage and architectural review before code can be marked complete",
                "key_insight": "The value is not in generating code faster, but in preventing broken code from reaching production",
                "workflow": "AI handles implementation grunt work, humans make approval decisions at checkpoints"
            },
            "group_id": "product_knowledge"
        },
        {
            "name": "guardkit_installation",
            "body": {
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
            },
            "group_id": "product_knowledge"
        }
    ]
    
    for ep in episodes:
        await graphiti.add_episode(
            name=ep["name"],
            episode_body=json.dumps(ep["body"]),
            group_id=ep["group_id"]
        )
    
    print(f"  ✓ Seeded {len(episodes)} product knowledge episodes")


# =============================================================================
# 2. COMMAND WORKFLOWS
# =============================================================================

async def seed_command_workflows(graphiti):
    """Seed knowledge about command workflows and how they connect."""
    
    episodes = [
        {
            "name": "workflow_overview",
            "body": {
                "entity_type": "workflow",
                "name": "Core GuardKit Workflow",
                "summary": "Create → Work → Complete (with quality gates)",
                "commands_in_order": [
                    "/task-create - Create a new task",
                    "/task-work - Implement the task with quality gates",
                    "/task-complete - Mark task done after review"
                ],
                "alternative_flows": [
                    "Feature flow: /feature-plan → /feature-build → /task-complete (bulk)",
                    "Review flow: /task-create task_type:review → /task-review → /task-complete",
                    "Design-first: /task-work --design-only → approve → /task-work --implement-only"
                ]
            },
            "group_id": "command_workflows"
        },
        {
            "name": "command_task_create",
            "body": {
                "entity_type": "command",
                "name": "/task-create",
                "purpose": "Create a new task with auto-generated ID and frontmatter",
                "syntax": '/task-create "Title" [priority:high|medium|low] [task_type:implementation|review]',
                "creates": "tasks/backlog/TASK-XXXX-title-slug.md",
                "id_format": "TASK-XXXX (4 hex chars from hash)",
                "outputs": "Task markdown file with YAML frontmatter"
            },
            "group_id": "command_workflows"
        },
        {
            "name": "command_task_work",
            "body": {
                "entity_type": "command",
                "name": "/task-work",
                "purpose": "Implement a task through the 5-phase quality gate workflow",
                "syntax": "/task-work TASK-XXX [--mode=standard|tdd|bdd] [--design-only|--implement-only] [--micro]",
                "phases_executed": "Phase 1 (Load) → Phase 2 (Plan) → Phase 2.5 (Review) → Phase 3 (Implement) → Phase 4 (Test) → Phase 5 (Review)",
                "key_flags": {
                    "--design-only": "Stop at Phase 2.8 checkpoint, save implementation plan",
                    "--implement-only": "Start at Phase 3, requires approved plan from --design-only",
                    "--micro": "Streamlined workflow for trivial tasks (skip planning phases)",
                    "--mode=tdd": "Test-driven development (write tests first)"
                },
                "outputs": "Implemented code, tests, documentation based on task requirements",
                "critical_requirement": "Must be run from PROJECT ROOT directory, not GuardKit directory"
            },
            "group_id": "command_workflows"
        },
        {
            "name": "command_task_complete",
            "body": {
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
            },
            "group_id": "command_workflows"
        },
        {
            "name": "command_feature_plan",
            "body": {
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
                    "task_files": "tasks/backlog/{feature-slug}/TASK-XXX-*.md",
                    "readme": "tasks/backlog/{feature-slug}/README.md",
                    "guide": "tasks/backlog/{feature-slug}/IMPLEMENTATION-GUIDE.md"
                },
                "enables": "/feature-build for autonomous implementation"
            },
            "group_id": "command_workflows"
        },
        {
            "name": "command_feature_build",
            "body": {
                "entity_type": "command",
                "name": "/feature-build",
                "purpose": "Autonomous task implementation using Player-Coach adversarial workflow",
                "syntax": "/feature-build TASK-XXX or /feature-build FEAT-XXX",
                "modes": {
                    "single_task": "TASK-XXX - Build one task",
                    "feature": "FEAT-XXX - Build all tasks in feature with dependency ordering"
                },
                "workflow": [
                    "1. Create isolated git worktree",
                    "2. Run Player-Coach dialectical loop",
                    "3. Player implements via task-work delegation",
                    "4. Coach validates independently",
                    "5. Iterate until approval or max turns",
                    "6. Preserve worktree for human review (never auto-merge)"
                ],
                "key_principle": "Player delegates to /task-work, does NOT implement directly",
                "outputs": {
                    "worktree": ".guardkit/worktrees/TASK-XXX/ or .guardkit/worktrees/FEAT-XXX/",
                    "branch": "autobuild/TASK-XXX or autobuild/FEAT-XXX",
                    "reports": ".guardkit/autobuild/{id}/player_turn_N.json, coach_turn_N.json"
                }
            },
            "group_id": "command_workflows"
        },
        {
            "name": "workflow_feature_to_build",
            "body": {
                "entity_type": "workflow",
                "name": "Feature Planning to Build Flow",
                "description": "Complete flow from feature idea to implemented code",
                "steps": [
                    "1. /feature-plan 'add OAuth2 authentication'",
                    "   → Creates FEAT-A1B2.yaml + 5 task markdown files",
                    "2. /feature-build FEAT-A1B2",
                    "   → Creates worktree, executes tasks in wave order",
                    "   → Player-Coach loop for each task",
                    "3. Review worktree: cd .guardkit/worktrees/FEAT-A1B2 && git diff main",
                    "4. Merge: git checkout main && git merge autobuild/FEAT-A1B2",
                    "5. /task-complete TASK-001 TASK-002 TASK-003 (bulk complete)",
                    "6. Cleanup: guardkit worktree cleanup FEAT-A1B2"
                ],
                "benefits": [
                    "Zero manual task creation",
                    "Automatic dependency ordering",
                    "Parallel execution where possible",
                    "Human review before merge"
                ]
            },
            "group_id": "command_workflows"
        }
    ]
    
    for ep in episodes:
        await graphiti.add_episode(
            name=ep["name"],
            episode_body=json.dumps(ep["body"]),
            group_id=ep["group_id"]
        )
    
    print(f"  ✓ Seeded {len(episodes)} command workflow episodes")


# =============================================================================
# 3. QUALITY GATE PHASES
# =============================================================================

async def seed_quality_gate_phases(graphiti):
    """Seed knowledge about the 5-phase quality gate structure."""
    
    episodes = [
        {
            "name": "phases_overview",
            "body": {
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
            },
            "group_id": "quality_gate_phases"
        },
        {
            "name": "phase_1_load",
            "body": {
                "entity_type": "phase",
                "phase_number": "1",
                "name": "Load Task Context",
                "purpose": "Load task file, detect stack, gather requirements",
                "actions": [
                    "Read task markdown from tasks/",
                    "Parse YAML frontmatter",
                    "Detect project technology stack",
                    "Load linked requirements (if require-kit installed)",
                    "Identify acceptance criteria"
                ],
                "outputs": "Task context loaded into session"
            },
            "group_id": "quality_gate_phases"
        },
        {
            "name": "phase_1_6_clarification",
            "body": {
                "entity_type": "phase",
                "phase_number": "1.6",
                "name": "Clarifying Questions",
                "purpose": "Ask user for clarification on ambiguous requirements",
                "gating": "Only runs if requirements are ambiguous",
                "skip_with": "--no-questions flag",
                "outputs": "Clarification answers stored in task frontmatter"
            },
            "group_id": "quality_gate_phases"
        },
        {
            "name": "phase_2_planning",
            "body": {
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
            },
            "group_id": "quality_gate_phases"
        },
        {
            "name": "phase_2_5_review",
            "body": {
                "entity_type": "phase",
                "phase_number": "2.5",
                "name": "Architectural Review + Pattern Suggestions",
                "purpose": "Review plan for architectural soundness",
                "subphases": {
                    "2.5A": "Pattern Suggestions - Suggest applicable design patterns",
                    "2.5B": "Architectural Review - Check SOLID, DRY, YAGNI compliance"
                },
                "agents_used": ["pattern-suggester", "architectural-reviewer"],
                "can_block": True,
                "block_conditions": "Major SOLID/DRY/YAGNI violations"
            },
            "group_id": "quality_gate_phases"
        },
        {
            "name": "phase_2_7_complexity",
            "body": {
                "entity_type": "phase",
                "phase_number": "2.7",
                "name": "Complexity Evaluation",
                "purpose": "Score task complexity 1-10 for process scaling",
                "scoring": {
                    "1-3": "Simple - may use --micro mode",
                    "4-6": "Medium - standard workflow",
                    "7-10": "Complex - may need splitting or extra review"
                },
                "affects": "Documentation level, test depth, review rigor"
            },
            "group_id": "quality_gate_phases"
        },
        {
            "name": "phase_2_8_checkpoint",
            "body": {
                "entity_type": "phase",
                "phase_number": "2.8",
                "name": "Human Checkpoint",
                "purpose": "Human approval of implementation plan before coding",
                "actions": [
                    "Display implementation plan summary",
                    "Present decision options: [A]pprove / [R]evise / [S]kip",
                    "If Approve: Proceed to Phase 3",
                    "If Revise: Return to Phase 2 with feedback",
                    "If Skip: Abort task-work"
                ],
                "critical": "This is the last stop before implementation begins",
                "design_only_stops_here": "--design-only flag stops at this phase"
            },
            "group_id": "quality_gate_phases"
        },
        {
            "name": "phase_3_implementation",
            "body": {
                "entity_type": "phase",
                "phase_number": "3",
                "name": "Implementation",
                "purpose": "Execute the implementation plan",
                "actions": [
                    "Create/modify files per plan",
                    "Write production code",
                    "Write tests (TDD: tests first, Standard: code first)",
                    "Run stack-specific specialist agent"
                ],
                "agents_used": ["Stack-specific specialist (e.g., fastapi-specialist, react-specialist)"],
                "implement_only_starts_here": "--implement-only flag starts at this phase"
            },
            "group_id": "quality_gate_phases"
        },
        {
            "name": "phase_4_testing",
            "body": {
                "entity_type": "phase",
                "phase_number": "4",
                "name": "Testing",
                "purpose": "Run tests and verify coverage",
                "actions": [
                    "Execute test suite",
                    "Check coverage threshold",
                    "Verify all acceptance criteria testable"
                ],
                "agents_used": ["test-orchestrator"],
                "thresholds": {
                    "coverage": "80% minimum (configurable)",
                    "tests_passing": "100% required"
                }
            },
            "group_id": "quality_gate_phases"
        },
        {
            "name": "phase_4_5_fixloop",
            "body": {
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
                "failure_handling": "If still failing after 3 iterations, task is blocked",
                "critical": "This prevents broken code from passing quality gates"
            },
            "group_id": "quality_gate_phases"
        },
        {
            "name": "phase_5_review",
            "body": {
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
                ],
                "agents_used": ["code-reviewer"]
            },
            "group_id": "quality_gate_phases"
        },
        {
            "name": "phase_5_5_audit",
            "body": {
                "entity_type": "phase",
                "phase_number": "5.5",
                "name": "Plan Audit",
                "purpose": "Verify implementation matches plan",
                "actions": [
                    "Compare implemented files to planned files",
                    "Verify all acceptance criteria addressed",
                    "Check for scope creep"
                ],
                "note": "Skipped in --micro mode (no plan to audit)"
            },
            "group_id": "quality_gate_phases"
        }
    ]
    
    for ep in episodes:
        await graphiti.add_episode(
            name=ep["name"],
            episode_body=json.dumps(ep["body"]),
            group_id=ep["group_id"]
        )
    
    print(f"  ✓ Seeded {len(episodes)} quality gate phase episodes")


# =============================================================================
# 4. TECHNOLOGY STACK
# =============================================================================

async def seed_technology_stack(graphiti):
    """Seed knowledge about GuardKit's technology stack and integrations."""
    
    episodes = [
        {
            "name": "tech_stack_overview",
            "body": {
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
            },
            "group_id": "technology_stack"
        },
        {
            "name": "tech_claude_code_commands",
            "body": {
                "entity_type": "technology",
                "name": "Claude Code Slash Commands",
                "location": ".claude/commands/*.md",
                "how_they_work": "Markdown files that Claude Code loads as available commands",
                "execution": "User types /command-name, Claude Code reads the markdown and follows instructions",
                "key_files": [
                    "task-create.md", "task-work.md", "task-complete.md",
                    "feature-plan.md", "feature-build.md", "task-review.md"
                ],
                "note": "Commands can invoke other commands or delegate to Python CLI"
            },
            "group_id": "technology_stack"
        },
        {
            "name": "tech_python_cli",
            "body": {
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
                    "guardkit/orchestrator/agent_invoker.py": "AgentInvoker - SDK invocation",
                    "guardkit/orchestrator/quality_gates/": "Quality gate implementations"
                },
                "note": "CLI provides tested orchestration that slash commands can delegate to"
            },
            "group_id": "technology_stack"
        },
        {
            "name": "tech_claude_agents_sdk",
            "body": {
                "entity_type": "technology",
                "name": "Claude Agents SDK",
                "import": "from claude_agent_sdk import query, ClaudeAgentOptions",
                "key_function": "query() - invokes Claude with options",
                "capabilities": [
                    "Fresh context per call (no cross-contamination)",
                    "Tool restrictions via allowed_tools parameter",
                    "Permission modes (acceptEdits, bypassPermissions)",
                    "Structured output via output_format parameter",
                    "Working directory specification via cwd parameter"
                ],
                "critical_insight": "query() can invoke slash commands directly by including them in the prompt",
                "example": 'query(prompt="/task-work TASK-XXX --implement-only", cwd=worktree_path)'
            },
            "group_id": "technology_stack"
        },
        {
            "name": "tech_subagents",
            "body": {
                "entity_type": "technology",
                "name": "Subagent Markdown Files",
                "location": ".claude/agents/*.md",
                "purpose": "Define specialized AI agents for specific tasks",
                "key_agents": [
                    "autobuild-player.md - Implements code in feature-build",
                    "autobuild-coach.md - Validates implementation in feature-build",
                    "code-reviewer.md - Reviews code quality",
                    "test-orchestrator.md - Manages test execution",
                    "architectural-reviewer.md - Reviews architecture",
                    "pattern-suggester.md - Suggests design patterns",
                    "{stack}-specialist.md - Stack-specific implementation"
                ],
                "invocation": "Claude reads agent file and adopts that persona/instructions"
            },
            "group_id": "technology_stack"
        },
        {
            "name": "tech_git_worktrees",
            "body": {
                "entity_type": "technology",
                "name": "Git Worktrees for Isolation",
                "location": ".guardkit/worktrees/",
                "purpose": "Isolated environments for autonomous implementation",
                "how_used": [
                    "feature-build creates worktree before implementation",
                    "All changes happen in worktree, not main repo",
                    "Human reviews worktree before merging",
                    "Worktrees preserved for debugging if needed"
                ],
                "naming": {
                    "single_task": ".guardkit/worktrees/TASK-XXX/",
                    "feature": ".guardkit/worktrees/FEAT-XXX/"
                },
                "branch_naming": "autobuild/TASK-XXX or autobuild/FEAT-XXX"
            },
            "group_id": "technology_stack"
        },
        {
            "name": "tech_state_management",
            "body": {
                "entity_type": "technology",
                "name": "State Management",
                "task_state": {
                    "location": "tasks/*/TASK-XXX-*.md frontmatter",
                    "fields": ["status", "priority", "requirements", "acceptance_criteria", "autobuild_state"]
                },
                "feature_state": {
                    "location": ".guardkit/features/FEAT-XXX.yaml",
                    "fields": ["id", "name", "status", "tasks", "orchestration"]
                },
                "autobuild_state": {
                    "purpose": "Track Player-Coach turns for resume capability",
                    "fields": ["current_turn", "max_turns", "worktree_path", "turns[]"]
                },
                "artifacts": {
                    "location": ".guardkit/autobuild/{task_id}/",
                    "files": ["player_turn_N.json", "coach_turn_N.json", "task_work_results.json"]
                }
            },
            "group_id": "technology_stack"
        }
    ]
    
    for ep in episodes:
        await graphiti.add_episode(
            name=ep["name"],
            episode_body=json.dumps(ep["body"]),
            group_id=ep["group_id"]
        )
    
    print(f"  ✓ Seeded {len(episodes)} technology stack episodes")


# =============================================================================
# 5. FEATURE-BUILD ARCHITECTURE
# =============================================================================

async def seed_feature_build_architecture(graphiti):
    """Seed detailed knowledge about feature-build architecture."""
    
    episodes = [
        {
            "name": "feature_build_overview",
            "body": {
                "entity_type": "architecture",
                "name": "Feature-Build Architecture",
                "purpose": "Autonomous task implementation with quality assurance via adversarial Player-Coach pattern",
                "key_insight": "Player DELEGATES to task-work, does NOT implement directly. This achieves 100% code reuse of quality gates.",
                "modes": {
                    "single_task": "/feature-build TASK-XXX",
                    "feature": "/feature-build FEAT-XXX"
                }
            },
            "group_id": "feature_build_architecture"
        },
        {
            "name": "feature_build_three_phases",
            "body": {
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
            },
            "group_id": "feature_build_architecture"
        },
        {
            "name": "feature_build_player_agent",
            "body": {
                "entity_type": "agent",
                "name": "AutoBuild Player Agent",
                "file": ".claude/agents/autobuild-player.md",
                "purpose": "Implement task by delegating to task-work",
                "critical_behavior": "Player MUST delegate to /task-work, NOT implement directly",
                "delegation_pattern": "/task-work TASK-XXX --implement-only --mode=tdd",
                "tools_available": ["Read", "Write", "Edit", "Bash"],
                "outputs": {
                    "code": "Implementation in worktree",
                    "report": "player_turn_N.json with structured status"
                },
                "why_delegate": "100% code reuse of quality gates (Phase 3-5.5)"
            },
            "group_id": "feature_build_architecture"
        },
        {
            "name": "feature_build_coach_agent",
            "body": {
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
                ],
                "outputs": {
                    "decision": "APPROVE or FEEDBACK",
                    "report": "coach_turn_N.json"
                }
            },
            "group_id": "feature_build_architecture"
        },
        {
            "name": "feature_build_task_work_delegation",
            "body": {
                "entity_type": "architecture",
                "name": "Task-Work Delegation Architecture",
                "description": "How AutoBuild delegates to task-work for 100% quality gate reuse",
                "flow": {
                    "pre_loop": {
                        "command": "/task-work TASK-XXX --design-only",
                        "phases_executed": "1.6 (Clarification) → 2 (Planning) → 2.5 (Review) → 2.8 (Checkpoint)",
                        "outputs": "implementation_plan.md"
                    },
                    "player_turn": {
                        "command": "/task-work TASK-XXX --implement-only --mode=tdd",
                        "phases_executed": "3 (Implement) → 4 (Test) → 4.5 (Fix Loop) → 5 (Review) → 5.5 (Audit)",
                        "outputs": "task_work_results.json with quality gate results"
                    }
                },
                "invocation_method": "SDK query() with prompt containing slash command",
                "NOT_subprocess": "Do NOT use subprocess.run(['guardkit', 'task-work', ...]) - CLI doesn't have this command"
            },
            "group_id": "feature_build_architecture"
        },
        {
            "name": "feature_build_file_locations",
            "body": {
                "entity_type": "architecture",
                "name": "Feature-Build File Locations",
                "critical_paths": {
                    "worktree": {
                        "single_task": ".guardkit/worktrees/TASK-XXX/",
                        "feature": ".guardkit/worktrees/FEAT-XXX/"
                    },
                    "artifacts": {
                        "pattern": ".guardkit/autobuild/{task_id}/",
                        "in_worktree": ".guardkit/worktrees/{worktree_id}/.guardkit/autobuild/{task_id}/"
                    },
                    "task_work_results": ".guardkit/autobuild/{task_id}/task_work_results.json",
                    "implementation_plan": ".claude/task-plans/TASK-XXX-implementation-plan.md"
                },
                "critical_rule_feature_mode": "In feature mode, paths use FEAT-XXX worktree ID, not individual TASK-XXX IDs"
            },
            "group_id": "feature_build_architecture"
        },
        {
            "name": "feature_build_feature_yaml_schema",
            "body": {
                "entity_type": "schema",
                "name": "Feature YAML Schema",
                "location": ".guardkit/features/FEAT-XXX.yaml",
                "required_fields": {
                    "feature_level": ["id", "name", "tasks", "orchestration"],
                    "task_level": ["id", "file_path"],
                    "orchestration_level": ["parallel_groups"]
                },
                "critical_field": "file_path - each task MUST have path to its markdown file",
                "parallel_groups_format": "List of lists - each inner list is a wave of parallel tasks"
            },
            "group_id": "feature_build_architecture"
        }
    ]
    
    for ep in episodes:
        await graphiti.add_episode(
            name=ep["name"],
            episode_body=json.dumps(ep["body"]),
            group_id=ep["group_id"]
        )
    
    print(f"  ✓ Seeded {len(episodes)} feature-build architecture episodes")


# =============================================================================
# 6. KNOWN ISSUES (from crisis analysis)
# =============================================================================

async def seed_known_issues(graphiti):
    """Seed known issues and their fixes from the feature-build crisis."""
    
    episodes = [
        {
            "name": "issue_sdk_not_subprocess",
            "body": {
                "issue_type": "architecture_decision",
                "decision": "Use SDK query() for task-work invocation",
                "not": "subprocess to guardkit CLI",
                "rationale": "CLI command 'guardkit task-work' does not exist. SDK query() can invoke slash commands directly.",
                "correct_pattern": 'query(prompt="/task-work TASK-XXX --implement-only", cwd=worktree_path)',
                "wrong_pattern": 'subprocess.run(["guardkit", "task-work", task_id])'
            },
            "group_id": "architecture_decisions"
        },
        {
            "name": "issue_feature_mode_paths",
            "body": {
                "issue_type": "architecture_decision",
                "decision": "In feature mode, paths use FEAT-XXX worktree ID",
                "not": "individual TASK-XXX IDs for worktree paths",
                "rationale": "Feature mode uses a shared worktree for all tasks. Task IDs are for task management, not filesystem paths.",
                "correct_pattern": ".guardkit/worktrees/FEAT-XXX/.guardkit/autobuild/TASK-XXX/",
                "wrong_pattern": ".guardkit/worktrees/TASK-XXX/.guardkit/autobuild/TASK-XXX/"
            },
            "group_id": "architecture_decisions"
        },
        {
            "name": "issue_preloop_must_invoke",
            "body": {
                "issue_type": "architecture_decision",
                "decision": "Pre-loop must invoke /task-work --design-only to generate implementation plan",
                "not": "return mock data from stub implementation",
                "rationale": "Player expects implementation_plan.md to exist. Pre-loop must actually run the design phases.",
                "component": "TaskWorkInterface.execute_design_phase()",
                "status": "stub returns mock data, needs real SDK integration"
            },
            "group_id": "architecture_decisions"
        },
        {
            "name": "failure_subprocess_to_cli",
            "body": {
                "issue_type": "failure_pattern",
                "symptom": "subprocess.CalledProcessError or 'command not found' for guardkit task-work",
                "root_cause": "guardkit task-work CLI command does not exist",
                "fix": "Use SDK query() with slash command in prompt instead of subprocess"
            },
            "group_id": "failure_patterns"
        },
        {
            "name": "failure_wrong_worktree_path",
            "body": {
                "issue_type": "failure_pattern",
                "symptom": "Task-work results not found at .guardkit/worktrees/TASK-XXX/.../task_work_results.json",
                "root_cause": "Path uses task ID instead of feature worktree ID in feature mode",
                "fix": "Use feature_worktree_id (FEAT-XXX) for path construction in feature mode"
            },
            "group_id": "failure_patterns"
        },
        {
            "name": "failure_mock_preloop_data",
            "body": {
                "issue_type": "failure_pattern",
                "symptom": "Pre-loop returns hardcoded complexity=5, arch_score=80 instead of real values",
                "root_cause": "TaskWorkInterface.execute_design_phase() is stub that returns mock data",
                "fix": "Implement execute_design_phase() with real SDK query() to /task-work --design-only"
            },
            "group_id": "failure_patterns"
        },
        {
            "name": "failure_no_implementation_plan",
            "body": {
                "issue_type": "failure_pattern",
                "symptom": "Player fails with 'implementation plan not found'",
                "root_cause": "Pre-loop didn't actually run design phases, so plan wasn't created",
                "fix": "Ensure pre-loop invokes /task-work --design-only which creates the plan",
                "chain": "Pre-loop mock → No plan created → Player can't read plan → Failure"
            },
            "group_id": "failure_patterns"
        },
        {
            "name": "component_taskwork_interface",
            "body": {
                "issue_type": "component_status",
                "component": "TaskWorkInterface",
                "method": "execute_design_phase",
                "status": "stub",
                "notes": "Returns mock data (complexity=5, arch_score=80). Needs SDK query() integration to invoke /task-work --design-only."
            },
            "group_id": "component_status"
        },
        {
            "name": "component_agent_invoker_delegation",
            "body": {
                "issue_type": "component_status",
                "component": "AgentInvoker",
                "method": "_invoke_task_work_implement",
                "status": "incorrect",
                "problem": "Uses subprocess to non-existent CLI command",
                "needs": "SDK query() with slash command in prompt"
            },
            "group_id": "component_status"
        },
        {
            "name": "integration_autobuild_to_taskwork",
            "body": {
                "issue_type": "integration_point",
                "name": "autobuild_to_taskwork",
                "connects": ["AutoBuildOrchestrator", "task-work slash command"],
                "correct_protocol": "sdk_query",
                "correct_pattern": 'query("/task-work TASK-XXX --implement-only", cwd=worktree_path)',
                "wrong_protocol": "subprocess",
                "wrong_pattern": 'subprocess.run(["guardkit", "task-work", ...])'
            },
            "group_id": "integration_points"
        },
        {
            "name": "integration_coach_result_path",
            "body": {
                "issue_type": "integration_point",
                "name": "coach_result_path",
                "connects": ["CoachValidator", "task_work_results.json"],
                "correct_pattern": ".guardkit/worktrees/FEAT-XXX/.guardkit/autobuild/TASK-XXX/task_work_results.json",
                "wrong_pattern": ".guardkit/worktrees/TASK-XXX/.guardkit/autobuild/TASK-XXX/task_work_results.json",
                "rule": "Use feature worktree ID in feature mode, task ID in single-task mode"
            },
            "group_id": "integration_points"
        }
    ]
    
    for ep in episodes:
        await graphiti.add_episode(
            name=ep["name"],
            episode_body=json.dumps(ep["body"]),
            group_id=ep["group_id"]
        )
    
    print(f"  ✓ Seeded {len(episodes)} known issue episodes")


# =============================================================================
# 7. TEMPLATES, AGENTS, RULES, PATTERNS
# =============================================================================

async def seed_template_knowledge(graphiti):
    """Seed template metadata for semantic search across templates."""
    
    episodes = [
        # FastAPI Python Template
        {
            "name": "template_fastapi_python",
            "body": {
                "entity_type": "template",
                "id": "fastapi-python",
                "name": "Python FastAPI Backend",
                "description": "Production-ready FastAPI template based on best practices from 12k+ star repository. Features Netflix Dispatch-inspired structure, dependency injection, async patterns, and comprehensive testing.",
                "language": "Python",
                "language_version": ">=3.9",
                "frameworks": [
                    {"name": "FastAPI", "version": ">=0.104.0", "purpose": "web_framework"},
                    {"name": "SQLAlchemy", "version": ">=2.0.0", "purpose": "database_orm"},
                    {"name": "Pydantic", "version": ">=2.0.0", "purpose": "data_validation"},
                    {"name": "Alembic", "version": ">=1.12.0", "purpose": "database_migrations"},
                    {"name": "pytest", "version": ">=7.4.0", "purpose": "testing"}
                ],
                "architecture": "Layered (Netflix Dispatch-inspired)",
                "patterns": [
                    "Dependency Injection",
                    "Repository Pattern",
                    "CRUD Base Classes",
                    "Pydantic Schema Validation",
                    "Async/Await Patterns",
                    "Database Session Management",
                    "API Versioning",
                    "Error Handling with HTTPException"
                ],
                "layers": ["api", "core", "crud", "db", "models", "schemas", "services"],
                "tags": ["python", "fastapi", "api", "backend", "rest", "async", "sqlalchemy", "pydantic"],
                "quality_scores": {
                    "solid_compliance": 90,
                    "dry_compliance": 85,
                    "yagni_compliance": 88,
                    "test_coverage": 85,
                    "documentation": 90
                },
                "complexity": 7,
                "production_ready": True
            },
            "group_id": "templates"
        },
        # React TypeScript Template
        {
            "name": "template_react_typescript",
            "body": {
                "entity_type": "template",
                "id": "react-typescript",
                "name": "React TypeScript Frontend",
                "description": "Modern React frontend with TypeScript, featuring component patterns, API integration, MSW mocking, and comprehensive testing.",
                "language": "TypeScript",
                "language_version": ">=5.0",
                "frameworks": [
                    {"name": "React", "version": ">=18.0.0", "purpose": "ui_framework"},
                    {"name": "TypeScript", "version": ">=5.0.0", "purpose": "type_safety"},
                    {"name": "MSW", "version": ">=2.0.0", "purpose": "api_mocking"},
                    {"name": "Vitest", "version": ">=1.0.0", "purpose": "testing"}
                ],
                "patterns": [
                    "Component Composition",
                    "Custom Hooks",
                    "API Layer Abstraction",
                    "MSW Mock Handlers",
                    "TypeScript Strict Mode"
                ],
                "layers": ["components", "api", "hooks", "routes", "mocks"],
                "tags": ["react", "typescript", "frontend", "spa", "msw", "testing"],
                "quality_scores": {
                    "solid_compliance": 85,
                    "dry_compliance": 80,
                    "yagni_compliance": 85,
                    "test_coverage": 80,
                    "documentation": 85
                },
                "complexity": 6,
                "production_ready": True
            },
            "group_id": "templates"
        },
        # NextJS Fullstack Template
        {
            "name": "template_nextjs_fullstack",
            "body": {
                "entity_type": "template",
                "id": "nextjs-fullstack",
                "name": "Next.js Fullstack",
                "description": "Full-stack Next.js application with App Router, Server Actions, Prisma ORM, and comprehensive testing including E2E.",
                "language": "TypeScript",
                "language_version": ">=5.0",
                "frameworks": [
                    {"name": "Next.js", "version": ">=14.0.0", "purpose": "fullstack_framework"},
                    {"name": "Prisma", "version": ">=5.0.0", "purpose": "database_orm"},
                    {"name": "Playwright", "version": ">=1.40.0", "purpose": "e2e_testing"}
                ],
                "patterns": [
                    "Server Components",
                    "Server Actions",
                    "App Router",
                    "Prisma Schema",
                    "E2E Testing"
                ],
                "layers": ["app", "components", "actions", "lib", "prisma"],
                "tags": ["nextjs", "typescript", "fullstack", "prisma", "react", "server-components"],
                "quality_scores": {
                    "solid_compliance": 85,
                    "dry_compliance": 82,
                    "yagni_compliance": 80,
                    "test_coverage": 85,
                    "documentation": 88
                },
                "complexity": 8,
                "production_ready": True
            },
            "group_id": "templates"
        }
    ]
    
    for ep in episodes:
        await graphiti.add_episode(
            name=ep["name"],
            episode_body=json.dumps(ep["body"]),
            group_id=ep["group_id"]
        )
    
    print(f"  ✓ Seeded {len(episodes)} template episodes")


async def seed_agent_knowledge(graphiti):
    """Seed agent metadata for semantic search across agents."""
    
    episodes = [
        # FastAPI Specialist
        {
            "name": "agent_fastapi_specialist",
            "body": {
                "entity_type": "agent",
                "id": "fastapi-specialist",
                "name": "FastAPI Specialist",
                "template_id": "fastapi-python",
                "role": "Implements FastAPI routes, dependencies, and middleware",
                "capabilities": [
                    "API endpoint implementation",
                    "Dependency injection patterns",
                    "Middleware configuration",
                    "Request/response handling",
                    "OpenAPI documentation",
                    "CORS configuration"
                ],
                "technologies": ["FastAPI", "Pydantic", "Starlette", "Uvicorn"],
                "file_patterns": ["router.py", "dependencies.py", "main.py", "middleware.py"],
                "always_do": [
                    "Use async def for I/O-bound routes",
                    "Define response_model for type safety",
                    "Use Depends() for dependency injection",
                    "Add OpenAPI tags and descriptions"
                ],
                "never_do": [
                    "Use blocking I/O in async routes",
                    "Store state in global variables",
                    "Skip request validation"
                ],
                "ask_before": [
                    "Adding new middleware",
                    "Changing authentication scheme",
                    "Modifying CORS configuration"
                ]
            },
            "group_id": "agents"
        },
        # FastAPI Database Specialist
        {
            "name": "agent_fastapi_database_specialist",
            "body": {
                "entity_type": "agent",
                "id": "fastapi-database-specialist",
                "name": "FastAPI Database Specialist",
                "template_id": "fastapi-python",
                "role": "Implements database models, CRUD operations, and migrations",
                "capabilities": [
                    "SQLAlchemy model design",
                    "Async database operations",
                    "Alembic migration creation",
                    "Relationship mapping",
                    "Query optimization",
                    "Connection pool configuration"
                ],
                "technologies": ["SQLAlchemy", "Alembic", "asyncpg", "PostgreSQL"],
                "file_patterns": ["models.py", "crud.py", "session.py", "alembic/versions/*.py"],
                "always_do": [
                    "Use async session for database operations",
                    "Create Alembic migration for schema changes",
                    "Define relationships explicitly",
                    "Use CRUD base class for common operations"
                ],
                "never_do": [
                    "Use synchronous database calls in async context",
                    "Modify database schema without migration",
                    "Hardcode connection strings"
                ],
                "ask_before": [
                    "Changing database schema",
                    "Adding new indexes",
                    "Modifying relationships"
                ]
            },
            "group_id": "agents"
        },
        # Test Orchestrator
        {
            "name": "agent_test_orchestrator",
            "body": {
                "entity_type": "agent",
                "id": "test-orchestrator",
                "name": "Test Orchestrator",
                "template_id": "default",
                "role": "Orchestrates test execution and validates coverage",
                "capabilities": [
                    "Test suite execution",
                    "Coverage measurement",
                    "Test fixture management",
                    "Async test patterns",
                    "Mock configuration"
                ],
                "technologies": ["pytest", "pytest-asyncio", "pytest-cov", "httpx"],
                "file_patterns": ["test_*.py", "*_test.py", "conftest.py"],
                "always_do": [
                    "Run full test suite before completion",
                    "Check coverage threshold (80% minimum)",
                    "Use fixtures for test isolation",
                    "Mark async tests with @pytest.mark.asyncio"
                ],
                "never_do": [
                    "Skip failing tests without investigation",
                    "Ignore coverage drops",
                    "Leave test database in dirty state"
                ],
                "ask_before": [
                    "Lowering coverage threshold",
                    "Skipping integration tests"
                ]
            },
            "group_id": "agents"
        },
        # Code Reviewer
        {
            "name": "agent_code_reviewer",
            "body": {
                "entity_type": "agent",
                "id": "code-reviewer",
                "name": "Code Reviewer",
                "template_id": "default",
                "role": "Reviews code for quality, SOLID principles, and best practices",
                "capabilities": [
                    "SOLID principle validation",
                    "DRY analysis",
                    "YAGNI assessment",
                    "Security review",
                    "Code style enforcement",
                    "Complexity analysis"
                ],
                "technologies": [],
                "file_patterns": ["*.py", "*.ts", "*.tsx", "*.js", "*.jsx"],
                "always_do": [
                    "Check SOLID compliance",
                    "Identify code duplication",
                    "Review error handling",
                    "Validate type annotations"
                ],
                "never_do": [
                    "Approve code with obvious security issues",
                    "Skip review of complex logic",
                    "Ignore test coverage gaps"
                ],
                "ask_before": [
                    "Approving breaking changes",
                    "Accepting technical debt"
                ]
            },
            "group_id": "agents"
        },
        # Architectural Reviewer
        {
            "name": "agent_architectural_reviewer",
            "body": {
                "entity_type": "agent",
                "id": "architectural-reviewer",
                "name": "Architectural Reviewer",
                "template_id": "default",
                "role": "Reviews implementation plans for architectural soundness",
                "capabilities": [
                    "Architecture pattern validation",
                    "Layer boundary enforcement",
                    "Dependency analysis",
                    "Scalability assessment",
                    "Integration point review"
                ],
                "technologies": [],
                "file_patterns": [],
                "always_do": [
                    "Validate layer boundaries",
                    "Check for circular dependencies",
                    "Assess scalability implications",
                    "Review error propagation"
                ],
                "never_do": [
                    "Approve plans with circular dependencies",
                    "Skip review of external integrations",
                    "Ignore security boundaries"
                ],
                "ask_before": [
                    "Approving new external dependencies",
                    "Changing architectural patterns"
                ]
            },
            "group_id": "agents"
        },
        # AutoBuild Player
        {
            "name": "agent_autobuild_player",
            "body": {
                "entity_type": "agent",
                "id": "autobuild-player",
                "name": "AutoBuild Player Agent",
                "template_id": "default",
                "role": "Implements tasks by delegating to task-work in Player-Coach pattern",
                "capabilities": [
                    "Task-work delegation",
                    "Implementation reporting",
                    "Quality gate monitoring",
                    "Worktree management"
                ],
                "technologies": ["Claude Agents SDK"],
                "file_patterns": [],
                "always_do": [
                    "Delegate to /task-work --implement-only",
                    "Work in isolated worktree",
                    "Create structured implementation report",
                    "Report quality gate results"
                ],
                "never_do": [
                    "Implement directly without task-work",
                    "Modify files outside worktree",
                    "Skip quality gates"
                ],
                "critical_note": "Player MUST delegate to /task-work, NOT implement directly"
            },
            "group_id": "agents"
        },
        # AutoBuild Coach
        {
            "name": "agent_autobuild_coach",
            "body": {
                "entity_type": "agent",
                "id": "autobuild-coach",
                "name": "AutoBuild Coach Agent",
                "template_id": "default",
                "role": "Validates Player implementations in Player-Coach pattern",
                "capabilities": [
                    "Implementation validation",
                    "Independent test execution",
                    "Acceptance criteria verification",
                    "Feedback generation"
                ],
                "technologies": [],
                "file_patterns": [],
                "always_do": [
                    "Read task_work_results.json",
                    "Run tests independently",
                    "Verify acceptance criteria",
                    "Provide specific actionable feedback"
                ],
                "never_do": [
                    "Modify any files (read-only access)",
                    "Trust Player's test results blindly",
                    "Approve without running tests"
                ],
                "critical_note": "Coach has READ-ONLY access, validates but cannot modify"
            },
            "group_id": "agents"
        }
    ]
    
    for ep in episodes:
        await graphiti.add_episode(
            name=ep["name"],
            episode_body=json.dumps(ep["body"]),
            group_id=ep["group_id"]
        )
    
    print(f"  ✓ Seeded {len(episodes)} agent episodes")


async def seed_pattern_knowledge(graphiti):
    """Seed design pattern knowledge for cross-template queries."""
    
    episodes = [
        {
            "name": "pattern_dependency_injection",
            "body": {
                "entity_type": "pattern",
                "id": "dependency_injection",
                "name": "Dependency Injection",
                "category": "structural",
                "description": "A technique where dependencies are provided to a component rather than created by the component itself, enabling loose coupling and testability.",
                "benefits": [
                    "Loose coupling between components",
                    "Easy unit testing with mocks",
                    "Flexible configuration",
                    "Single Responsibility adherence"
                ],
                "use_when": [
                    "Components need external resources (DB, cache, APIs)",
                    "You want to swap implementations",
                    "Testing requires mocking dependencies"
                ],
                "avoid_when": [
                    "Simple scripts with no complex dependencies",
                    "Performance-critical tight loops"
                ],
                "examples": {
                    "fastapi": "def get_db() -> Generator:\n    db = SessionLocal()\n    try:\n        yield db\n    finally:\n        db.close()\n\n@router.get('/users')\ndef get_users(db: Session = Depends(get_db)):\n    return db.query(User).all()",
                    "react": "const UserContext = createContext<UserService>(null);\n\nfunction UserProvider({ children }) {\n  const service = new UserService();\n  return <UserContext.Provider value={service}>{children}</UserContext.Provider>;\n}"
                },
                "templates_using": ["fastapi-python", "nextjs-fullstack"]
            },
            "group_id": "patterns"
        },
        {
            "name": "pattern_repository",
            "body": {
                "entity_type": "pattern",
                "id": "repository_pattern",
                "name": "Repository Pattern",
                "category": "data_access",
                "description": "Abstracts data access logic into dedicated classes, separating business logic from data storage details.",
                "benefits": [
                    "Clean separation of concerns",
                    "Easy to swap data sources",
                    "Centralized query logic",
                    "Testable with in-memory implementations"
                ],
                "use_when": [
                    "Multiple data sources possible",
                    "Complex query logic",
                    "Need consistent data access patterns"
                ],
                "avoid_when": [
                    "Simple CRUD with no complex queries",
                    "Tight deadline with simple requirements"
                ],
                "examples": {
                    "fastapi": "class UserRepository:\n    def __init__(self, db: Session):\n        self.db = db\n    \n    def get_by_id(self, user_id: int) -> User | None:\n        return self.db.query(User).filter(User.id == user_id).first()\n    \n    def get_active(self) -> list[User]:\n        return self.db.query(User).filter(User.is_active == True).all()"
                },
                "templates_using": ["fastapi-python"]
            },
            "group_id": "patterns"
        },
        {
            "name": "pattern_crud_base",
            "body": {
                "entity_type": "pattern",
                "id": "crud_base_classes",
                "name": "CRUD Base Classes",
                "category": "data_access",
                "description": "Generic base classes that provide standard Create, Read, Update, Delete operations, reducing boilerplate.",
                "benefits": [
                    "DRY - eliminate repetitive CRUD code",
                    "Consistent API across entities",
                    "Type-safe with generics",
                    "Easy to extend for custom operations"
                ],
                "use_when": [
                    "Multiple entities need similar CRUD operations",
                    "Want consistent data access patterns",
                    "Using ORM with similar entity shapes"
                ],
                "avoid_when": [
                    "Only 1-2 simple entities",
                    "Entities have wildly different access patterns"
                ],
                "examples": {
                    "fastapi": "class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):\n    def __init__(self, model: Type[ModelType]):\n        self.model = model\n    \n    async def get(self, db: AsyncSession, id: int) -> ModelType | None:\n        result = await db.execute(select(self.model).where(self.model.id == id))\n        return result.scalar_one_or_none()"
                },
                "templates_using": ["fastapi-python"]
            },
            "group_id": "patterns"
        },
        {
            "name": "pattern_server_components",
            "body": {
                "entity_type": "pattern",
                "id": "server_components",
                "name": "Server Components",
                "category": "rendering",
                "description": "React components that render on the server, reducing client-side JavaScript and enabling direct database access.",
                "benefits": [
                    "Reduced client bundle size",
                    "Direct database/API access",
                    "Better SEO",
                    "Faster initial page load"
                ],
                "use_when": [
                    "Component doesn't need interactivity",
                    "Data fetching from server",
                    "SEO is important"
                ],
                "avoid_when": [
                    "Component needs client state",
                    "Using browser APIs",
                    "Real-time updates needed"
                ],
                "examples": {
                    "nextjs": "// app/users/page.tsx (Server Component by default)\nexport default async function UsersPage() {\n  const users = await prisma.user.findMany();\n  return (\n    <ul>\n      {users.map(user => <li key={user.id}>{user.name}</li>)}\n    </ul>\n  );\n}"
                },
                "templates_using": ["nextjs-fullstack"]
            },
            "group_id": "patterns"
        },
        {
            "name": "pattern_server_actions",
            "body": {
                "entity_type": "pattern",
                "id": "server_actions",
                "name": "Server Actions",
                "category": "data_mutation",
                "description": "Next.js pattern for handling form submissions and data mutations directly on the server.",
                "benefits": [
                    "No API routes needed for mutations",
                    "Progressive enhancement",
                    "Type-safe form handling",
                    "Automatic revalidation"
                ],
                "use_when": [
                    "Form submissions",
                    "Data mutations",
                    "Want to avoid client-side state"
                ],
                "avoid_when": [
                    "Need complex client-side logic",
                    "Real-time updates",
                    "External API calls that need client context"
                ],
                "examples": {
                    "nextjs": "// app/actions/user.ts\n'use server'\n\nexport async function createUser(formData: FormData) {\n  const name = formData.get('name') as string;\n  await prisma.user.create({ data: { name } });\n  revalidatePath('/users');\n}"
                },
                "templates_using": ["nextjs-fullstack"]
            },
            "group_id": "patterns"
        },
        {
            "name": "pattern_player_coach",
            "body": {
                "entity_type": "pattern",
                "id": "player_coach_adversarial",
                "name": "Player-Coach Adversarial Pattern",
                "category": "agent_orchestration",
                "description": "GuardKit's adversarial cooperation pattern where a Player agent implements and a Coach agent validates, iterating until approval.",
                "benefits": [
                    "Quality assurance through independent validation",
                    "Iterative improvement via feedback",
                    "Trust but verify approach",
                    "Clear separation of implementation and review"
                ],
                "use_when": [
                    "Autonomous task implementation",
                    "Need quality assurance without human in loop",
                    "Tasks have clear acceptance criteria"
                ],
                "avoid_when": [
                    "Simple tasks that don't need review",
                    "Exploratory work without clear criteria",
                    "Time-critical tasks"
                ],
                "structure": {
                    "player": "Implements by delegating to task-work, full file access",
                    "coach": "Validates independently, read-only access",
                    "loop": "Player implements → Coach validates → Feedback or Approve",
                    "max_turns": 5
                },
                "templates_using": ["guardkit-default"]
            },
            "group_id": "patterns"
        }
    ]
    
    for ep in episodes:
        await graphiti.add_episode(
            name=ep["name"],
            episode_body=json.dumps(ep["body"]),
            group_id=ep["group_id"]
        )
    
    print(f"  ✓ Seeded {len(episodes)} pattern episodes")


async def seed_rule_knowledge(graphiti):
    """Seed rule metadata for semantic search across rules."""
    
    episodes = [
        {
            "name": "rule_fastapi_code_style",
            "body": {
                "entity_type": "rule",
                "id": "fastapi-python_code-style",
                "name": "Python Code Style",
                "template_id": "fastapi-python",
                "path_patterns": ["**/*.py"],
                "topics": [
                    "naming conventions",
                    "module structure",
                    "class patterns",
                    "function patterns",
                    "configuration management"
                ],
                "key_rules": [
                    "Use snake_case for functions and variables",
                    "Use PascalCase for classes",
                    "Use PascalCase with type suffix for Pydantic schemas (UserCreate, UserUpdate)",
                    "Use get_ prefix for dependency functions",
                    "Standard file names: router.py, schemas.py, models.py, crud.py, service.py"
                ],
                "code_examples": [
                    {"pattern": "Pydantic schema naming", "example": "class UserCreate(BaseModel): pass"},
                    {"pattern": "Dependency function", "example": "def get_db(): yield session"},
                    {"pattern": "SQLAlchemy model", "example": "class User(Base): __tablename__ = 'users'"}
                ]
            },
            "group_id": "rules"
        },
        {
            "name": "rule_fastapi_async",
            "body": {
                "entity_type": "rule",
                "id": "fastapi-python_async-patterns",
                "name": "Async Patterns",
                "template_id": "fastapi-python",
                "path_patterns": ["**/*.py"],
                "topics": [
                    "async/await",
                    "non-blocking I/O",
                    "database sessions",
                    "HTTP clients"
                ],
                "key_rules": [
                    "Use async def for I/O-bound routes",
                    "Never use blocking I/O in async routes",
                    "Use asyncio.sleep() not time.sleep() in async context",
                    "Use async database sessions (AsyncSession)",
                    "Use httpx for async HTTP requests"
                ],
                "anti_patterns": [
                    {"bad": "time.sleep(10) in async route", "good": "await asyncio.sleep(10)"},
                    {"bad": "requests.get() in async route", "good": "await httpx.get()"}
                ]
            },
            "group_id": "rules"
        },
        {
            "name": "rule_fastapi_testing",
            "body": {
                "entity_type": "rule",
                "id": "fastapi-python_testing",
                "name": "Testing Patterns",
                "template_id": "fastapi-python",
                "path_patterns": ["tests/**/*.py", "**/test_*.py"],
                "topics": [
                    "pytest",
                    "async testing",
                    "fixtures",
                    "database testing",
                    "API testing"
                ],
                "key_rules": [
                    "Use @pytest.mark.asyncio for async tests",
                    "Use httpx.AsyncClient for API testing",
                    "Override get_db dependency with test database",
                    "Use factory fixtures for test data",
                    "Clean up test database after each test"
                ],
                "coverage_requirements": {
                    "minimum_line": 80,
                    "minimum_branch": 75
                }
            },
            "group_id": "rules"
        },
        {
            "name": "rule_react_component_patterns",
            "body": {
                "entity_type": "rule",
                "id": "react-typescript_components",
                "name": "React Component Patterns",
                "template_id": "react-typescript",
                "path_patterns": ["**/*.tsx", "**/*.jsx"],
                "topics": [
                    "component structure",
                    "hooks",
                    "props typing",
                    "state management"
                ],
                "key_rules": [
                    "Use function components with hooks",
                    "Define prop types with interfaces",
                    "Extract custom hooks for reusable logic",
                    "Use TypeScript strict mode",
                    "Prefer composition over inheritance"
                ]
            },
            "group_id": "rules"
        }
    ]
    
    for ep in episodes:
        await graphiti.add_episode(
            name=ep["name"],
            episode_body=json.dumps(ep["body"]),
            group_id=ep["group_id"]
        )
    
    print(f"  ✓ Seeded {len(episodes)} rule episodes")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    asyncio.run(seed_all_system_context())
```

---

## Updated Group ID Summary

After seeding, these group IDs will be populated:

| Group ID | Episodes | Purpose |
|----------|----------|---------|
| `product_knowledge` | 3 | What GuardKit is |
| `command_workflows` | 7 | How commands work and flow |
| `quality_gate_phases` | 12 | The 5-phase structure |
| `technology_stack` | 7 | Python, SDK, worktrees, etc. |
| `feature_build_architecture` | 7 | Specific feature-build design |
| `architecture_decisions` | 3 | Key design decisions |
| `failure_patterns` | 4 | Known failures and fixes |
| `component_status` | 2 | Incomplete component tracking |
| `integration_points` | 2 | How components connect |
| `templates` | 3 | Template metadata for semantic search |
| `agents` | 7 | Agent capabilities and boundaries |
| `patterns` | 6 | Design pattern knowledge with examples |
| `rules` | 4 | Rule metadata and code examples |

**Total: ~67 episodes** providing comprehensive system context including templates, agents, patterns, and rules.

---

## Usage

### Initial Seeding (Run Once)

```bash
# Start Graphiti
./scripts/start_graphiti.sh

# Run seeding script
cd guardkit
python -m guardkit.knowledge.seed_system_context
```

### Verification

```python
# Verify seeding worked
from guardkit.knowledge.graphiti_client import get_graphiti

graphiti = get_graphiti()

# Query product knowledge
results = await graphiti.search(
    query="What is GuardKit?",
    group_ids=["product_knowledge"],
    num_results=3
)
print(results)

# Query feature-build architecture
results = await graphiti.search(
    query="How does Player delegate to task-work?",
    group_ids=["feature_build_architecture"],
    num_results=3
)
print(results)

# Query known issues
results = await graphiti.search(
    query="subprocess CLI error",
    group_ids=["failure_patterns", "architecture_decisions"],
    num_results=5
)
print(results)
```

---

## Context Loading Enhancement

Update `load_critical_context()` to include system context:

```python
async def load_critical_context() -> CriticalContext:
    """Load must-know context at session start."""
    
    graphiti = get_graphiti()
    
    # 1. System context - What we're building
    system_context = await graphiti.search(
        query="GuardKit feature-build task-work workflow",
        group_ids=["product_knowledge", "command_workflows", "feature_build_architecture"],
        num_results=10
    )
    
    # 2. Quality gates - How quality is enforced
    quality_gates = await graphiti.search(
        query="quality gate phases",
        group_ids=["quality_gate_phases"],
        num_results=5
    )
    
    # 3. Architecture decisions - How things SHOULD work
    decisions = await graphiti.search(
        query="architecture decision integration protocol",
        group_ids=["architecture_decisions"],
        num_results=10
    )
    
    # 4. Failure patterns - What NOT to do
    failures = await graphiti.search(
        query="failure error bug pattern",
        group_ids=["failure_patterns", "failed_approaches"],
        num_results=10
    )
    
    # 5. Component status - What's incomplete
    incomplete = await graphiti.search(
        query="stub partial not_implemented incomplete",
        group_ids=["component_status"],
        num_results=10
    )
    
    # 6. Integration points - How components connect
    integrations = await graphiti.search(
        query="integration connects protocol",
        group_ids=["integration_points"],
        num_results=10
    )
    
    return CriticalContext(
        system_context=system_context,
        quality_gates=quality_gates,
        decisions=decisions,
        failures=failures,
        incomplete=incomplete,
        integrations=integrations
    )
```

---

## What This Enables

With this comprehensive seeding, Claude Code sessions will have context about:

1. **What GuardKit is** - Not just a task manager, but a quality gate system
2. **The workflow** - How `/feature-plan` → `/feature-build` → `/task-complete` flow
3. **The phases** - Why Phase 2.8 exists, what Phase 4.5 does
4. **The delegation** - Player delegates to task-work, doesn't implement directly
5. **The technology** - SDK query() not subprocess, worktrees for isolation
6. **The known issues** - What's broken and how to fix it

This prevents the "decision in isolation" problem where each session makes locally-optimal choices that conflict with the overall system design.

---

## Template, Agent, and Rule Knowledge Seeding

In addition to system context, we seed knowledge about templates, agents, rules, and patterns. This enables semantic search across development knowledge.

### New Group IDs

| Group ID | Purpose |
|----------|--------|
| `templates` | Template metadata for stack selection |
| `agents` | Agent capabilities and boundaries |
| `rules` | Rule applicability and code examples |
| `patterns` | Design pattern knowledge |

### Seeding Script Addition

```python
# =============================================================================
# 7. TEMPLATE KNOWLEDGE
# =============================================================================

async def seed_template_knowledge(graphiti):
    """Seed knowledge about available templates."""
    
    episodes = [
        {
            "name": "template_fastapi_python",
            "body": {
                "entity_type": "template",
                "id": "fastapi-python",
                "name": "Python FastAPI Backend",
                "description": "Production-ready FastAPI template based on best practices from 12k+ star repository. Features Netflix Dispatch-inspired structure, dependency injection, async patterns, and comprehensive testing.",
                "language": "Python",
                "language_version": ">=3.9",
                "frameworks": [
                    {"name": "FastAPI", "version": ">=0.104.0", "purpose": "web_framework"},
                    {"name": "SQLAlchemy", "version": ">=2.0.0", "purpose": "database_orm"},
                    {"name": "Pydantic", "version": ">=2.0.0", "purpose": "data_validation"},
                    {"name": "Alembic", "version": ">=1.12.0", "purpose": "database_migrations"},
                    {"name": "pytest", "version": ">=7.4.0", "purpose": "testing"}
                ],
                "architecture": "Layered (Netflix Dispatch-inspired)",
                "patterns": [
                    "Dependency Injection",
                    "Repository Pattern",
                    "CRUD Base Classes",
                    "Pydantic Schema Validation",
                    "Async/Await Patterns",
                    "Database Session Management"
                ],
                "layers": ["api", "core", "crud", "db", "models", "schemas", "services"],
                "quality_scores": {
                    "solid_compliance": 90,
                    "dry_compliance": 85,
                    "yagni_compliance": 88,
                    "test_coverage": 85
                },
                "complexity": 7,
                "production_ready": True,
                "tags": ["python", "fastapi", "api", "backend", "rest", "async", "sqlalchemy"]
            },
            "group_id": "templates"
        },
        {
            "name": "template_react_typescript",
            "body": {
                "entity_type": "template",
                "id": "react-typescript",
                "name": "React TypeScript Frontend",
                "description": "Modern React frontend with TypeScript, featuring hooks, context, and comprehensive testing with React Testing Library.",
                "language": "TypeScript",
                "language_version": ">=5.0",
                "frameworks": [
                    {"name": "React", "version": ">=18.0", "purpose": "ui_framework"},
                    {"name": "Vite", "version": ">=5.0", "purpose": "build_tool"},
                    {"name": "React Router", "version": ">=6.0", "purpose": "routing"},
                    {"name": "TanStack Query", "version": ">=5.0", "purpose": "data_fetching"},
                    {"name": "Vitest", "version": ">=1.0", "purpose": "testing"}
                ],
                "patterns": [
                    "Component Composition",
                    "Custom Hooks",
                    "Context API",
                    "Error Boundaries",
                    "Suspense for Data Fetching"
                ],
                "layers": ["components", "hooks", "api", "routes", "utils"],
                "quality_scores": {
                    "solid_compliance": 85,
                    "dry_compliance": 88,
                    "test_coverage": 80
                },
                "complexity": 6,
                "production_ready": True,
                "tags": ["react", "typescript", "frontend", "spa", "vite"]
            },
            "group_id": "templates"
        },
        {
            "name": "template_nextjs_fullstack",
            "body": {
                "entity_type": "template",
                "id": "nextjs-fullstack",
                "name": "Next.js Fullstack Application",
                "description": "Full-stack Next.js with App Router, Server Components, Server Actions, and Prisma ORM.",
                "language": "TypeScript",
                "frameworks": [
                    {"name": "Next.js", "version": ">=14.0", "purpose": "fullstack_framework"},
                    {"name": "Prisma", "version": ">=5.0", "purpose": "database_orm"},
                    {"name": "NextAuth", "version": ">=5.0", "purpose": "authentication"}
                ],
                "patterns": [
                    "Server Components",
                    "Server Actions",
                    "Streaming with Suspense",
                    "Parallel Routes",
                    "Intercepting Routes"
                ],
                "layers": ["app", "components", "lib", "prisma", "actions"],
                "complexity": 8,
                "production_ready": True,
                "tags": ["nextjs", "react", "fullstack", "typescript", "prisma"]
            },
            "group_id": "templates"
        },
        {
            "name": "template_selection_guidance",
            "body": {
                "entity_type": "guidance",
                "topic": "template_selection",
                "rules": [
                    "For Python REST APIs, prefer fastapi-python over Flask",
                    "For React frontends, prefer react-typescript with Vite",
                    "For fullstack with SSR, prefer nextjs-fullstack",
                    "For monorepos with separate frontend/backend, prefer react-fastapi-monorepo"
                ],
                "decision_factors": [
                    "Team familiarity with framework",
                    "Performance requirements (async vs sync)",
                    "Deployment target (serverless, container, traditional)",
                    "Database requirements (SQL vs NoSQL)"
                ]
            },
            "group_id": "templates"
        }
    ]
    
    for ep in episodes:
        await graphiti.add_episode(
            name=ep["name"],
            episode_body=json.dumps(ep["body"]),
            group_id=ep["group_id"]
        )
    
    print(f"  ✓ Seeded {len(episodes)} template knowledge episodes")


# =============================================================================
# 8. AGENT KNOWLEDGE
# =============================================================================

async def seed_agent_knowledge(graphiti):
    """Seed knowledge about available agents and their capabilities."""
    
    episodes = [
        {
            "name": "agent_fastapi_specialist",
            "body": {
                "entity_type": "agent",
                "id": "fastapi-specialist",
                "name": "FastAPI Specialist",
                "role": "Implements FastAPI routes, dependencies, and middleware",
                "template_id": "fastapi-python",
                "capabilities": [
                    "API route implementation",
                    "Dependency injection patterns",
                    "Request/response schemas",
                    "Middleware configuration",
                    "OpenAPI documentation"
                ],
                "technologies": ["FastAPI", "Pydantic", "Starlette"],
                "file_patterns": ["router.py", "dependencies.py", "schemas.py"],
                "always_do": [
                    "Use async def for I/O-bound routes",
                    "Validate input with Pydantic models",
                    "Use dependency injection for shared resources",
                    "Return appropriate HTTP status codes"
                ],
                "never_do": [
                    "Use global state for request-scoped data",
                    "Block event loop with sync I/O in async routes",
                    "Skip input validation"
                ],
                "ask_before": [
                    "Adding new middleware",
                    "Changing authentication scheme",
                    "Modifying API versioning strategy"
                ]
            },
            "group_id": "agents"
        },
        {
            "name": "agent_fastapi_database_specialist",
            "body": {
                "entity_type": "agent",
                "id": "fastapi-database-specialist",
                "name": "FastAPI Database Specialist",
                "role": "Implements SQLAlchemy models, CRUD operations, and Alembic migrations",
                "template_id": "fastapi-python",
                "capabilities": [
                    "SQLAlchemy model design",
                    "Async database sessions",
                    "CRUD operation implementation",
                    "Alembic migration creation",
                    "Query optimization"
                ],
                "technologies": ["SQLAlchemy", "Alembic", "asyncpg", "PostgreSQL"],
                "file_patterns": ["models.py", "crud.py", "db/session.py", "alembic/versions/*.py"],
                "always_do": [
                    "Use async session for database operations",
                    "Create migrations for schema changes",
                    "Use generic CRUD base classes",
                    "Add proper indexes for query patterns"
                ],
                "never_do": [
                    "Commit sessions in CRUD methods (let caller control transaction)",
                    "Use raw SQL without parameterization",
                    "Skip foreign key constraints"
                ]
            },
            "group_id": "agents"
        },
        {
            "name": "agent_react_specialist",
            "body": {
                "entity_type": "agent",
                "id": "react-specialist",
                "name": "React Specialist",
                "role": "Implements React components, hooks, and state management",
                "template_id": "react-typescript",
                "capabilities": [
                    "Functional component implementation",
                    "Custom hook creation",
                    "State management with Context",
                    "Performance optimization",
                    "Accessibility implementation"
                ],
                "technologies": ["React", "TypeScript", "TanStack Query"],
                "file_patterns": ["*.tsx", "hooks/*.ts", "components/*.tsx"],
                "always_do": [
                    "Use TypeScript for all components",
                    "Extract reusable logic into custom hooks",
                    "Memoize expensive computations",
                    "Add aria labels for accessibility"
                ],
                "never_do": [
                    "Use class components (prefer functional)",
                    "Mutate state directly",
                    "Ignore TypeScript errors"
                ]
            },
            "group_id": "agents"
        },
        {
            "name": "agent_test_orchestrator",
            "body": {
                "entity_type": "agent",
                "id": "test-orchestrator",
                "name": "Test Orchestrator",
                "role": "Manages test execution, coverage verification, and test strategy",
                "template_id": "default",
                "capabilities": [
                    "Test suite execution",
                    "Coverage analysis",
                    "Test strategy selection",
                    "Fixture management",
                    "Test isolation verification"
                ],
                "technologies": ["pytest", "Vitest", "Jest", "coverage.py"],
                "always_do": [
                    "Run tests in isolation",
                    "Verify coverage meets threshold",
                    "Report failures with actionable details",
                    "Clean up test artifacts"
                ],
                "never_do": [
                    "Skip tests without explicit approval",
                    "Accept coverage below threshold",
                    "Leave test database in dirty state"
                ],
                "coverage_thresholds": {
                    "minimum_line": 80,
                    "minimum_branch": 75
                }
            },
            "group_id": "agents"
        },
        {
            "name": "agent_code_reviewer",
            "body": {
                "entity_type": "agent",
                "id": "code-reviewer",
                "name": "Code Reviewer",
                "role": "Reviews code for quality, patterns, and best practices",
                "template_id": "default",
                "capabilities": [
                    "SOLID principle verification",
                    "DRY violation detection",
                    "YAGNI assessment",
                    "Security pattern review",
                    "Performance anti-pattern detection"
                ],
                "checks": [
                    "Single Responsibility Principle",
                    "Open/Closed Principle",
                    "Liskov Substitution Principle",
                    "Interface Segregation Principle",
                    "Dependency Inversion Principle",
                    "Don't Repeat Yourself",
                    "You Aren't Gonna Need It"
                ],
                "severity_levels": ["critical", "warning", "suggestion"]
            },
            "group_id": "agents"
        },
        {
            "name": "agent_autobuild_player",
            "body": {
                "entity_type": "agent",
                "id": "autobuild-player",
                "name": "AutoBuild Player",
                "role": "Implements tasks by delegating to task-work in feature-build workflow",
                "template_id": "default",
                "capabilities": [
                    "Task-work delegation",
                    "Implementation status reporting",
                    "Quality gate monitoring",
                    "Worktree management"
                ],
                "critical_behavior": "Player MUST delegate to /task-work --implement-only, NOT implement directly",
                "delegation_pattern": "/task-work TASK-XXX --implement-only --mode=tdd",
                "tools_available": ["Read", "Write", "Edit", "Bash"],
                "outputs": ["player_turn_N.json", "implementation in worktree"]
            },
            "group_id": "agents"
        },
        {
            "name": "agent_autobuild_coach",
            "body": {
                "entity_type": "agent",
                "id": "autobuild-coach",
                "name": "AutoBuild Coach",
                "role": "Validates Player implementation independently in feature-build workflow",
                "template_id": "default",
                "capabilities": [
                    "Independent test execution",
                    "Acceptance criteria validation",
                    "Quality gate verification",
                    "Feedback generation"
                ],
                "critical_behavior": "Coach has READ-ONLY access - validates but cannot modify",
                "tools_available": ["Read", "Bash (read-only commands)"],
                "decisions": ["APPROVE", "FEEDBACK"],
                "outputs": ["coach_turn_N.json"]
            },
            "group_id": "agents"
        }
    ]
    
    for ep in episodes:
        await graphiti.add_episode(
            name=ep["name"],
            episode_body=json.dumps(ep["body"]),
            group_id=ep["group_id"]
        )
    
    print(f"  ✓ Seeded {len(episodes)} agent knowledge episodes")


# =============================================================================
# 9. PATTERN KNOWLEDGE
# =============================================================================

async def seed_pattern_knowledge(graphiti):
    """Seed knowledge about design patterns and their applications."""
    
    episodes = [
        {
            "name": "pattern_dependency_injection",
            "body": {
                "entity_type": "pattern",
                "id": "dependency_injection",
                "name": "Dependency Injection",
                "category": "structural",
                "description": "A technique where an object receives its dependencies from external sources rather than creating them internally.",
                "benefits": [
                    "Improved testability through mock injection",
                    "Loose coupling between components",
                    "Easier configuration management",
                    "Better separation of concerns"
                ],
                "use_when": [
                    "Components need external resources (database, cache, APIs)",
                    "Testing requires mock implementations",
                    "Configuration varies between environments"
                ],
                "avoid_when": [
                    "Simple scripts with no testing requirements",
                    "Over-engineering simple CRUD operations"
                ],
                "examples": {
                    "fastapi": "def get_db() -> Generator:\n    db = SessionLocal()\n    try:\n        yield db\n    finally:\n        db.close()",
                    "react": "const UserContext = createContext<User | null>(null);\nconst user = useContext(UserContext);"
                },
                "used_by_templates": ["fastapi-python", "react-typescript", "nextjs-fullstack"]
            },
            "group_id": "patterns"
        },
        {
            "name": "pattern_repository",
            "body": {
                "entity_type": "pattern",
                "id": "repository_pattern",
                "name": "Repository Pattern",
                "category": "data_access",
                "description": "Mediates between the domain and data mapping layers using a collection-like interface for accessing domain objects.",
                "benefits": [
                    "Abstraction over data access",
                    "Centralized query logic",
                    "Easier unit testing with mock repositories",
                    "Database-agnostic domain layer"
                ],
                "use_when": [
                    "Multiple data sources exist",
                    "Complex query logic needs encapsulation",
                    "Domain layer should be database-agnostic"
                ],
                "examples": {
                    "fastapi": "class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):\n    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]:\n        result = await db.execute(select(self.model).where(self.model.id == id))\n        return result.scalar_one_or_none()"
                },
                "used_by_templates": ["fastapi-python"]
            },
            "group_id": "patterns"
        },
        {
            "name": "pattern_crud_base",
            "body": {
                "entity_type": "pattern",
                "id": "crud_base_classes",
                "name": "CRUD Base Classes",
                "category": "code_reuse",
                "description": "Generic base classes that provide standard Create, Read, Update, Delete operations for any entity type.",
                "benefits": [
                    "DRY - no repeated CRUD code per entity",
                    "Consistent API across all entities",
                    "Easy to extend with custom methods",
                    "Type-safe with generics"
                ],
                "implementation_notes": [
                    "Use Python generics (Generic[T]) for type safety",
                    "Session management should be caller's responsibility",
                    "Provide hooks for pre/post operations"
                ],
                "used_by_templates": ["fastapi-python"]
            },
            "group_id": "patterns"
        },
        {
            "name": "pattern_player_coach",
            "body": {
                "entity_type": "pattern",
                "id": "player_coach",
                "name": "Player-Coach Adversarial Pattern",
                "category": "agentic",
                "description": "An adversarial AI pattern where one agent (Player) implements while another (Coach) validates independently, creating a dialectical loop that converges on quality.",
                "benefits": [
                    "Independent validation catches issues Player missed",
                    "Adversarial relationship prevents collusion",
                    "Iterative refinement improves quality",
                    "Human only reviews approved implementations"
                ],
                "key_principles": [
                    "Player and Coach have asymmetric capabilities (Player: write, Coach: read-only)",
                    "Coach runs tests independently (trust but verify)",
                    "Loop continues until Coach approves or max turns",
                    "Never auto-merge - human review required"
                ],
                "guardkit_implementation": "feature-build command with autobuild-player.md and autobuild-coach.md agents",
                "used_by_templates": ["default"]
            },
            "group_id": "patterns"
        },
        {
            "name": "pattern_quality_gates",
            "body": {
                "entity_type": "pattern",
                "id": "quality_gates",
                "name": "Quality Gates Pattern",
                "category": "workflow",
                "description": "Mandatory checkpoints in a workflow that must pass before proceeding, ensuring quality standards are met at each stage.",
                "benefits": [
                    "Prevents broken code from reaching later stages",
                    "Provides clear go/no-go decision points",
                    "Documents quality requirements explicitly",
                    "Enables automated enforcement"
                ],
                "guardkit_gates": [
                    "Phase 2.5B: Architectural review (SOLID/DRY/YAGNI)",
                    "Phase 2.8: Human approval of implementation plan",
                    "Phase 4.5: Test pass + coverage threshold",
                    "Phase 5: Code review quality checks"
                ],
                "key_principle": "Gates must execute deterministically, not left to AI discretion"
            },
            "group_id": "patterns"
        }
    ]
    
    for ep in episodes:
        await graphiti.add_episode(
            name=ep["name"],
            episode_body=json.dumps(ep["body"]),
            group_id=ep["group_id"]
        )
    
    print(f"  ✓ Seeded {len(episodes)} pattern knowledge episodes")


# =============================================================================
# 10. RULE KNOWLEDGE
# =============================================================================

async def seed_rule_knowledge(graphiti):
    """Seed knowledge about rules and their applicability."""
    
    episodes = [
        {
            "name": "rule_python_async",
            "body": {
                "entity_type": "rule",
                "id": "python_async_patterns",
                "name": "Python Async Patterns",
                "template_id": "fastapi-python",
                "path_patterns": ["**/*.py"],
                "topics": ["async", "await", "event loop", "concurrency"],
                "key_rules": [
                    "Use async def for I/O-bound operations",
                    "Never use time.sleep() in async routes - use asyncio.sleep()",
                    "Use sync def for CPU-bound operations (runs in thread pool)",
                    "Don't block event loop with synchronous I/O"
                ],
                "code_examples": [
                    {
                        "bad": "@router.get('/bad')\nasync def bad_route():\n    time.sleep(10)  # Blocks entire application!",
                        "good": "@router.get('/good')\nasync def good_route():\n    await asyncio.sleep(10)  # Non-blocking"
                    }
                ]
            },
            "group_id": "rules"
        },
        {
            "name": "rule_python_naming",
            "body": {
                "entity_type": "rule",
                "id": "python_naming_conventions",
                "name": "Python Naming Conventions",
                "template_id": "fastapi-python",
                "path_patterns": ["**/*.py"],
                "topics": ["naming", "conventions", "style"],
                "key_rules": [
                    "Classes use PascalCase (User, ProductService)",
                    "Functions use snake_case (get_user_by_id)",
                    "Modules use snake_case (user_service.py)",
                    "Constants use UPPER_SNAKE_CASE (MAX_RETRY_COUNT)",
                    "Pydantic schemas use PascalCase with type suffix (UserCreate, UserUpdate, UserPublic)",
                    "Dependencies use get_ prefix (get_db, get_current_user)"
                ]
            },
            "group_id": "rules"
        },
        {
            "name": "rule_react_components",
            "body": {
                "entity_type": "rule",
                "id": "react_component_patterns",
                "name": "React Component Patterns",
                "template_id": "react-typescript",
                "path_patterns": ["**/*.tsx", "**/*.jsx"],
                "topics": ["components", "hooks", "state"],
                "key_rules": [
                    "Use functional components (never class components)",
                    "Extract reusable logic into custom hooks",
                    "Co-locate component, styles, and tests",
                    "Use TypeScript interfaces for props",
                    "Memoize expensive computations with useMemo",
                    "Memoize callbacks with useCallback when passing to children"
                ],
                "code_examples": [
                    {
                        "pattern": "Custom Hook",
                        "example": "function useUser(id: string) {\n  const [user, setUser] = useState<User | null>(null);\n  useEffect(() => { fetchUser(id).then(setUser); }, [id]);\n  return user;\n}"
                    }
                ]
            },
            "group_id": "rules"
        },
        {
            "name": "rule_testing_general",
            "body": {
                "entity_type": "rule",
                "id": "testing_best_practices",
                "name": "Testing Best Practices",
                "template_id": "default",
                "path_patterns": ["**/test_*.py", "**/*.test.ts", "**/*.test.tsx", "**/*.spec.ts"],
                "topics": ["testing", "coverage", "fixtures", "mocks"],
                "key_rules": [
                    "Each test should test ONE thing",
                    "Use descriptive test names (test_user_creation_fails_with_invalid_email)",
                    "Arrange-Act-Assert pattern",
                    "Isolate tests - no shared mutable state",
                    "Mock external dependencies, not internal implementation",
                    "Minimum 80% line coverage, 75% branch coverage"
                ],
                "coverage_thresholds": {
                    "line": 80,
                    "branch": 75
                }
            },
            "group_id": "rules"
        }
    ]
    
    for ep in episodes:
        await graphiti.add_episode(
            name=ep["name"],
            episode_body=json.dumps(ep["body"]),
            group_id=ep["group_id"]
        )
    
    print(f"  ✓ Seeded {len(episodes)} rule knowledge episodes")


# =============================================================================
# UPDATED MAIN ENTRY POINT
# =============================================================================

async def seed_all_system_context():
    """Seed all system context into Graphiti."""
    
    await init_graphiti()
    graphiti = get_graphiti()
    
    if not graphiti.enabled:
        print("Graphiti not enabled, skipping seeding")
        return
    
    print("Seeding GuardKit system context...")
    
    # Core system context
    await seed_product_knowledge(graphiti)
    await seed_command_workflows(graphiti)
    await seed_quality_gate_phases(graphiti)
    await seed_technology_stack(graphiti)
    await seed_feature_build_architecture(graphiti)
    await seed_known_issues(graphiti)
    
    # Template, agent, pattern, and rule knowledge
    await seed_template_knowledge(graphiti)
    await seed_agent_knowledge(graphiti)
    await seed_pattern_knowledge(graphiti)
    await seed_rule_knowledge(graphiti)
    
    print("✓ System context seeding complete")
    print("")
    print("Group IDs populated:")
    print("  - product_knowledge")
    print("  - command_workflows")
    print("  - quality_gate_phases")
    print("  - technology_stack")
    print("  - feature_build_architecture")
    print("  - architecture_decisions")
    print("  - failure_patterns")
    print("  - component_status")
    print("  - integration_points")
    print("  - templates")
    print("  - agents")
    print("  - patterns")
    print("  - rules")
```

---

## Updated Group ID Summary

After seeding, these group IDs will be populated:

| Group ID | Episodes | Purpose |
|----------|----------|---------|
| `product_knowledge` | 3 | What GuardKit is |
| `command_workflows` | 7 | How commands work and flow |
| `quality_gate_phases` | 12 | The 5-phase structure |
| `technology_stack` | 7 | Python, SDK, worktrees, etc. |
| `feature_build_architecture` | 7 | Specific feature-build design |
| `architecture_decisions` | 3 | Key design decisions |
| `failure_patterns` | 4 | Known failures and fixes |
| `component_status` | 2 | Incomplete component tracking |
| `integration_points` | 2 | How components connect |
| `templates` | 4 | Template metadata for selection |
| `agents` | 7 | Agent capabilities and boundaries |
| `patterns` | 5 | Design pattern knowledge |
| `rules` | 4 | Rule applicability and examples |

**Total: ~67 episodes** providing comprehensive system and development knowledge.

---

## Enhanced Context Loading

Update `load_critical_context()` to include template/agent/pattern knowledge:

```python
async def load_critical_context(task: Optional[TaskEntity] = None) -> CriticalContext:
    """Load must-know context at session start."""
    
    graphiti = get_graphiti()
    
    # ... existing system context queries ...
    
    # 7. Template knowledge (if task has stack info)
    templates = []
    if task and task.stack:
        templates = await graphiti.search(
            query=f"template {task.stack}",
            group_ids=["templates"],
            num_results=3
        )
    
    # 8. Relevant agents for this task
    agents = []
    if task:
        agents = await graphiti.search(
            query=f"agent {task.requirements}",
            group_ids=["agents"],
            num_results=5
        )
    
    # 9. Applicable patterns
    patterns = []
    if task:
        patterns = await graphiti.search(
            query=f"pattern {task.requirements}",
            group_ids=["patterns"],
            num_results=5
        )
    
    # 10. Relevant rules
    rules = []
    if task and task.file_patterns:
        rules = await graphiti.search(
            query=f"rule {' '.join(task.file_patterns)}",
            group_ids=["rules"],
            num_results=5
        )
    
    return CriticalContext(
        # ... existing fields ...
        templates=templates,
        agents=agents,
        patterns=patterns,
        rules=rules
    )
```

---

## Template/Agent Sync Hooks

Add hooks to keep Graphiti in sync when templates/agents are created or modified:

```python
# In /template-create post-processing:
async def post_template_create(template_path: Path):
    """Sync new template to Graphiti after creation."""
    await sync_template_to_graphiti(template_path)
    
    for agent_path in (template_path / "agents").glob("*.md"):
        await sync_agent_to_graphiti(agent_path, template_path.name)
    
    for rule_path in (template_path / ".claude" / "rules").rglob("*.md"):
        await sync_rule_to_graphiti(rule_path, template_path.name)

# In /agent-enhance post-processing:
async def post_agent_enhance(agent_path: Path, template_id: str):
    """Sync updated agent to Graphiti after enhancement."""
    await sync_agent_to_graphiti(agent_path, template_id)
```
