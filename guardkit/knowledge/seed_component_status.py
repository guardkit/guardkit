"""
Component status seeding for GuardKit knowledge graph.

Seeds component status tracking into Graphiti for context-aware AI assistance.
"""

import logging

from guardkit.knowledge.seed_helpers import _add_episodes

logger = logging.getLogger(__name__)


async def seed_component_status(client) -> None:
    """Seed component status tracking.

    Creates 6 episodes covering key component implementation status.

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("component_taskwork_interface", {
            "issue_type": "component_status",
            "component": "TaskWorkInterface",
            "method": "execute_design_phase",
            "status": "implemented",
            "notes": "Full SDK integration via claude_agent_sdk.query(). Invokes /task-work --design-only with proper ContentBlock iteration (TextBlock, ToolUseBlock, ToolResultBlock). Includes regex-based output parsing for plan path, complexity score, architectural review scores (SOLID/DRY/YAGNI), and checkpoint results. Subprocess fallback if SDK unavailable. Comprehensive error handling for TimeoutError, CLINotFoundError, ProcessError, CLIJSONDecodeError."
        }),
        ("component_agent_invoker_delegation", {
            "issue_type": "component_status",
            "component": "AgentInvoker",
            "method": "_invoke_task_work_implement",
            "status": "implemented",
            "notes": "Full SDK integration via claude_agent_sdk.query() with /task-work {task_id} --implement-only. Uses TaskWorkStreamParser for incremental stream processing of quality gate metrics (tests, coverage, phases, file tracking). Proper ContentBlock iteration matching TaskWorkInterface pattern. Writes task_work_results.json for Coach validation. Includes heartbeat logging, rate limit detection, and failure result writing on all error paths."
        }),
        ("component_agent_invoker_player", {
            "issue_type": "component_status",
            "component": "AgentInvoker",
            "method": "invoke_player",
            "status": "implemented",
            "notes": "Supports three invocation paths: task-work delegation (via _invoke_task_work_implement), direct mode (via _invoke_player_direct for implementation_mode=direct tasks), and legacy SDK (via _invoke_with_role). Routes based on implementation_mode frontmatter. Writes turn context, Coach feedback, and Player reports for all paths."
        }),
        ("component_agent_invoker_coach", {
            "issue_type": "component_status",
            "component": "AgentInvoker",
            "method": "invoke_coach",
            "status": "implemented",
            "notes": "Read-only SDK invocation (Read, Bash, Grep, Glob only) with bypassPermissions. Includes pre-invocation honesty verification of Player claims via CoachVerifier. Tracks discrepancies and honesty scores. Validates Coach decision schema (approve/feedback)."
        }),
        ("component_stream_parser", {
            "issue_type": "component_status",
            "component": "TaskWorkStreamParser",
            "method": "parse_message",
            "status": "implemented",
            "notes": "Stateful incremental parser for task-work SDK streams. Extracts: phase markers/completion, test pass/fail counts (pytest patterns), coverage percentage, quality gate status, file modifications (regex + tool invocation tracking for Write/Edit), architectural review scores (SOLID/DRY/YAGNI). Accumulates results across multiple stream messages with set-based deduplication."
        }),
        ("component_security_review", {
            "issue_type": "component_status",
            "component": "TaskWorkInterface",
            "method": "execute_security_review",
            "status": "implemented",
            "notes": "Phase 2.5C security review via SecurityReviewer. Runs on worktree with configurable SecurityConfig. Persists results for Coach verification. Returns SecurityReviewResult with critical finding count and blocking decision."
        })
    ]

    await _add_episodes(client, episodes, "component_status", "component status", entity_type="component_status")
