"""
Technology stack seeding for GuardKit knowledge graph.

Seeds knowledge about GuardKit's technology stack into Graphiti for
context-aware AI assistance.
"""

import logging

from guardkit.knowledge.seed_helpers import _add_episodes

logger = logging.getLogger(__name__)


async def seed_technology_stack(client) -> None:
    """Seed knowledge about GuardKit's technology stack.

    Creates 7 episodes covering all major technology components.

    Args:
        client: GraphitiClient instance
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

    await _add_episodes(client, episodes, "technology_stack", "technology stack", entity_type="technology")
