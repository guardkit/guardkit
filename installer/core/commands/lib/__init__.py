"""
Command support library for GuardKit workflow commands.

This package provides shared utilities consumed by the runtime orchestrator
(guardkit.orchestrator.*) and by CLI-exposed scripts listed in
installer/core/commands/bin-entries.txt.

The surface intentionally stays small: most orchestration logic lives in
guardkit/orchestrator/ or is driven by Claude inside slash-command prose.
Modules here are library helpers, not entry points.
"""

# Error message formatters (TASK-003E Phase 5 Day 2)
from .error_messages import (
    format_file_error,
    format_validation_error,
    format_calculation_error,
)

# Greenfield Q&A Session (TASK-001B)
from .greenfield_qa_session import (
    GreenfieldAnswers,
    TemplateInitQASession,
)

# Agent Discovery (TASK-HAI-005, TASK-ENF2)
from .agent_discovery import (
    discover_agents,
    discover_agent_with_source,
    get_agent_by_name,
    list_discoverable_agents,
    get_agents_by_stack,
    validate_discovery_metadata,
    VALID_STACKS,
    VALID_PHASES,
)

# Agent Invocation Tracker (TASK-ENF2)
from .agent_invocation_tracker import (
    AgentInvocationTracker,
)

# Agent Invocation Validator (TASK-ENF1, TASK-FIX-RWOP1.3.1)
# ValidationError here is the agent-invocation validator's exception, bound at
# package level so AgentInvoker._write_task_work_results can catch it via the
# stable public surface.
from .agent_invocation_validator import (
    validate_agent_invocations,
    ValidationError,
)

__version__ = "1.1.0"

__all__ = [
    # Error message formatters
    "format_file_error",
    "format_validation_error",
    "format_calculation_error",

    # Greenfield Q&A Session
    "GreenfieldAnswers",
    "TemplateInitQASession",

    # Agent Discovery
    "discover_agents",
    "discover_agent_with_source",
    "get_agent_by_name",
    "list_discoverable_agents",
    "get_agents_by_stack",
    "validate_discovery_metadata",
    "VALID_STACKS",
    "VALID_PHASES",

    # Agent Invocation Tracker
    "AgentInvocationTracker",

    # Agent Invocation Validator
    "validate_agent_invocations",
    "ValidationError",
]
