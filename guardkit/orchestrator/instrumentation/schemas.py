"""Pydantic v2 event schema models for AutoBuild instrumentation.

This module defines the structured contract for every event emitted during
an AutoBuild run. All downstream tasks (collectors, dashboards, cost calculators)
consume these models.

Architecture:
    BaseEvent
    ├── LLMCallEvent          (every model invocation)
    ├── ToolExecEvent          (every shell/tool invocation)
    ├── TaskStartedEvent       (task.started)
    ├── TaskCompletedEvent     (task.completed)
    ├── TaskFailedEvent        (task.failed)
    ├── WaveCompletedEvent     (wave completion metrics)
    ├── FeatureCheckAttemptEvent (one failed whole-feature check attempt)
    └── GraphitiQueryEvent     (knowledge graph queries)

Controlled Vocabularies:
    - AgentRole: player | coach | resolver | router
    - FailureCategory: knowledge_gap | context_missing | spec_ambiguity | ...
    - PromptProfile: digest_only | digest+graphiti | digest+rules_bundle | ...
    - LLMProvider: anthropic | openai | local-vllm
    - LLMCallStatus: ok | error
    - LLMCallErrorType: rate_limited | timeout | tool_error | other
    - GraphitiQueryType: context_loader | nearest_neighbours | adr_lookup
    - GraphitiStatus: ok | error
    - FeatureCheckFailureKind: exit_nonzero | timed_out | could_not_start | missing_twins

Example:
    >>> from guardkit.orchestrator.instrumentation.schemas import LLMCallEvent
    >>> event = LLMCallEvent(
    ...     run_id="run-abc-123",
    ...     task_id="TASK-001",
    ...     agent_role="player",
    ...     attempt=1,
    ...     timestamp="2026-03-02T12:00:00Z",
    ...     provider="anthropic",
    ...     model="claude-sonnet-4-20250514",
    ...     input_tokens=1000,
    ...     output_tokens=500,
    ...     latency_ms=1234.5,
    ...     prompt_profile="digest_only",
    ...     status="ok",
    ... )
    >>> event.schema_version
    '1.0.0'
    >>> dumped = event.model_dump()
    >>> dumped["provider"]
    'anthropic'
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Controlled Vocabulary Types
# ============================================================================

AgentRole = Literal["player", "coach", "resolver", "router", "specialist"]
"""Valid agent roles in the AutoBuild system.

``specialist`` (13 October 2026) labels an orchestrator-run specialist such
as the code reviewer, whose permission role is ``player`` or ``coach`` but
which is neither; its name goes in ``LLMCallEvent.agent_name``."""

FailureCategory = Literal[
    "knowledge_gap",
    "context_missing",
    "spec_ambiguity",
    "test_failure",
    "env_failure",
    "dependency_issue",
    "rate_limit",
    "timeout",
    "tool_error",
    "other",
]
"""Controlled vocabulary for task failure reasons."""

PromptProfile = Literal[
    "digest_only",
    "digest+graphiti",
    "digest+rules_bundle",
    "digest+graphiti+rules_bundle",
]
"""Controlled vocabulary for prompt composition profiles."""

LLMProvider = Literal["anthropic", "openai", "local-vllm"]
"""Supported LLM providers."""

LLMCallStatus = Literal["ok", "error"]
"""LLM call outcome status."""

LLMCallErrorType = Literal["rate_limited", "timeout", "tool_error", "other"]
"""Types of LLM call errors."""

GraphitiQueryType = Literal["context_loader", "nearest_neighbours", "adr_lookup"]
"""Types of Graphiti knowledge graph queries."""

GraphitiStatus = Literal["ok", "error"]
"""Graphiti query outcome status."""

FeatureCheckFailureKind = Literal[
    "exit_nonzero", "timed_out", "could_not_start", "missing_twins"
]
"""How one attempt of the project's whole-feature check failed.

Chosen by central code from its own branches, never from the command's output.
"""


# ============================================================================
# Base Event Model
# ============================================================================


class BaseEvent(BaseModel):
    """Abstract base event with common fields for all instrumentation events.

    All event models inherit from this base, ensuring consistent structure
    across the instrumentation pipeline.

    Attributes:
        run_id: Unique identifier for the AutoBuild run.
        feature_id: Optional feature identifier (e.g., "FEAT-ABC").
        task_id: Task identifier (e.g., "TASK-001").
        agent_role: Role of the agent emitting the event.
        attempt: 1-indexed attempt number within the task.
        timestamp: ISO 8601 formatted timestamp.
        schema_version: Event schema version for forward compatibility.
    """

    run_id: str = Field(description="Unique identifier for the AutoBuild run")
    feature_id: Optional[str] = Field(
        None, description="Optional feature identifier"
    )
    task_id: str = Field(description="Task identifier (e.g., 'TASK-001')")
    agent_role: AgentRole = Field(
        description="Role of the agent: player, coach, resolver, router"
    )
    attempt: int = Field(
        ge=1, description="1-indexed attempt number within the task"
    )
    timestamp: str = Field(description="ISO 8601 formatted timestamp")
    schema_version: str = Field(
        default="1.0.0",
        description="Event schema version for forward compatibility",
    )


# ============================================================================
# LLM Call Event
# ============================================================================


class LLMCallEvent(BaseEvent):
    """Event emitted for every LLM model invocation.

    Captures token usage, latency, caching information, and error details
    for cost tracking and performance analysis.

    Attributes:
        provider: LLM provider (anthropic, openai, local-vllm).
        model: Model identifier string.
        input_tokens: Number of input tokens (>= 0).
        output_tokens: Number of output tokens (>= 0).
        latency_ms: Total latency in milliseconds.
        ttft_ms: Optional time-to-first-token in milliseconds.
        prefix_cache_hit: Optional flag for prefix cache hit.
        prefix_cache_estimated: Whether cache hit was estimated (default False).
        context_bytes: Optional context size in bytes.
        prompt_profile: Prompt composition profile from controlled vocabulary.
        status: Call outcome (ok or error).
        error_type: Optional error classification when status is 'error'.
        agent_name: Optional name of the agent within its role (for a
            ``specialist``, the specialist's name, e.g. ``code-reviewer``).
    """

    provider: LLMProvider = Field(
        description="LLM provider: anthropic, openai, local-vllm"
    )
    model: str = Field(description="Model identifier string")
    input_tokens: int = Field(
        ge=0, description="Number of input tokens (>= 0)"
    )
    output_tokens: int = Field(
        ge=0, description="Number of output tokens (>= 0)"
    )
    latency_ms: float = Field(description="Total latency in milliseconds")
    ttft_ms: Optional[float] = Field(
        None, description="Time-to-first-token in milliseconds"
    )
    prefix_cache_hit: Optional[bool] = Field(
        None, description="Whether prefix cache was hit"
    )
    prefix_cache_estimated: bool = Field(
        default=False,
        description="Whether cache hit was estimated rather than confirmed",
    )
    context_bytes: Optional[int] = Field(
        None, description="Context size in bytes"
    )
    prompt_profile: PromptProfile = Field(
        description="Prompt composition profile from controlled vocabulary"
    )
    status: LLMCallStatus = Field(description="Call outcome: ok or error")
    error_type: Optional[LLMCallErrorType] = Field(
        None,
        description="Error classification when status is 'error'",
    )
    agent_name: Optional[str] = Field(
        None,
        description="Name of the agent within its role, e.g. a specialist's name",
    )


# ============================================================================
# Tool Execution Event
# ============================================================================


class ToolExecEvent(BaseEvent):
    """Event emitted for every shell or tool invocation.

    Captures command details, exit codes, and truncated output for
    debugging and audit trails.

    Attributes:
        tool_name: Name of the tool invoked.
        cmd: Command string (should be redacted for security).
        exit_code: Process exit code (can be negative for signal kills).
        latency_ms: Execution latency in milliseconds.
        stdout_tail: Truncated tail of stdout output.
        stderr_tail: Truncated tail of stderr output.
    """

    tool_name: str = Field(description="Name of the tool invoked")
    cmd: str = Field(description="Command string (redacted)")
    exit_code: int = Field(description="Process exit code")
    latency_ms: float = Field(description="Execution latency in milliseconds")
    stdout_tail: str = Field(description="Truncated tail of stdout output")
    stderr_tail: str = Field(description="Truncated tail of stderr output")


# ============================================================================
# Task Lifecycle Events
# ============================================================================


class TaskStartedEvent(BaseEvent):
    """Event emitted when a task begins execution.

    Uses the attempt field from BaseEvent to track which attempt this is.
    """


class TaskCompletedEvent(BaseEvent):
    """Event emitted when a task completes successfully.

    Captures completion metrics including turn count, diff statistics,
    verification outcome, and prompt profile used.

    Attributes:
        turn_count: Number of player-coach turns taken.
        diff_stats: Summary of code changes (e.g., "+50 -10").
        verification_status: Coach verification outcome.
        prompt_profile: Prompt composition profile used for the task.
    """

    turn_count: int = Field(description="Number of player-coach turns taken")
    diff_stats: str = Field(
        description="Summary of code changes (e.g., '+50 -10')"
    )
    verification_status: str = Field(description="Coach verification outcome")
    prompt_profile: PromptProfile = Field(
        description="Prompt composition profile used for the task"
    )


class TaskFailedEvent(BaseEvent):
    """Event emitted when a task fails.

    Captures the failure reason using a controlled vocabulary to enable
    automated failure analysis and categorization.

    Attributes:
        failure_category: Reason for failure from controlled vocabulary.
    """

    failure_category: FailureCategory = Field(
        description="Failure reason from controlled vocabulary"
    )


# ============================================================================
# Wave Completed Event
# ============================================================================


class WaveCompletedEvent(BaseEvent):
    """Event emitted when a parallel execution wave completes.

    Captures wave-level metrics for capacity planning and performance
    analysis across parallel task execution.

    Attributes:
        wave_id: Unique identifier for the wave.
        worker_count: Number of concurrent workers in the wave.
        queue_depth_start: Queue depth at wave start.
        queue_depth_end: Queue depth at wave end.
        tasks_completed: Number of tasks that completed successfully.
        task_failures: Number of tasks that failed.
        rate_limit_count: Number of rate-limit events during the wave.
        p95_task_latency_ms: Optional 95th percentile task latency.
    """

    wave_id: str = Field(description="Unique identifier for the wave")
    worker_count: int = Field(
        ge=0, description="Number of concurrent workers in the wave"
    )
    queue_depth_start: int = Field(
        ge=0, description="Queue depth at wave start"
    )
    queue_depth_end: int = Field(ge=0, description="Queue depth at wave end")
    tasks_completed: int = Field(
        ge=0, description="Number of tasks that completed successfully"
    )
    task_failures: int = Field(
        ge=0, description="Number of tasks that failed"
    )
    rate_limit_count: int = Field(
        ge=0, description="Number of rate-limit events during the wave"
    )
    p95_task_latency_ms: Optional[float] = Field(
        None, description="95th percentile task latency in milliseconds"
    )


# ============================================================================
# Feature Check Attempt Event
# ============================================================================


class FeatureCheckAttemptEvent(BaseEvent):
    """Event emitted when one attempt of the whole-feature check fails.

    Emitted as soon as the attempt fails, before any repair round, so a
    failure is visible while the build is still running (13 October 2026,
    build FEAT-1F44: a failure sat unrecorded for 50 minutes).

    It carries no text from the project. The declared command and the check's
    output can both hold a credential, so every field here is a fixed word, a
    number, a true/false value or a git commit id. The full output stays where
    it already was: the final record and the Player's feedback.

    Attributes:
        check_attempt: 1-indexed attempt of the whole-feature check.
        failure_kind: How the attempt failed, from a fixed list.
        exit_code: The command's exit status; None when it never ran or
            never started.
        timed_out: Whether the attempt was cut off by its time limit.
        duration_seconds: How long the command ran.
        candidate_sha: The commit checked, or ``unknown``.
        wave_number: The wave a repair round would re-enter.
        repair_follows: Whether a repair round follows this attempt.
        stdout_bytes: Size of the command's standard output.
        stdout_lines: Line count of the command's standard output.
        stderr_bytes: Size of the command's standard error.
        stderr_lines: Line count of the command's standard error.
    """

    check_attempt: int = Field(
        ge=1, description="1-indexed attempt of the whole-feature check"
    )
    failure_kind: FeatureCheckFailureKind = Field(
        description="How the attempt failed, from a fixed list"
    )
    exit_code: Optional[int] = Field(
        None, description="Exit status; None when the command did not run"
    )
    timed_out: bool = Field(description="Whether the attempt timed out")
    duration_seconds: float = Field(
        ge=0, description="How long the command ran, in seconds"
    )
    candidate_sha: str = Field(
        pattern=r"^(?:[0-9a-f]{7,64}|unknown)$",
        description="The commit checked (hex), or 'unknown'",
    )
    wave_number: int = Field(
        ge=0, description="The wave a repair round would re-enter"
    )
    repair_follows: bool = Field(
        description="Whether a repair round follows this attempt"
    )
    stdout_bytes: int = Field(ge=0, description="Bytes of standard output")
    stdout_lines: int = Field(ge=0, description="Lines of standard output")
    stderr_bytes: int = Field(ge=0, description="Bytes of standard error")
    stderr_lines: int = Field(ge=0, description="Lines of standard error")


# ============================================================================
# Graphiti Query Event
# ============================================================================


class GraphitiQueryEvent(BaseEvent):
    """Event emitted for knowledge graph queries via Graphiti.

    Captures query type, results, token impact, and performance for
    knowledge retrieval optimization.

    Attributes:
        query_type: Type of Graphiti query from controlled vocabulary.
        items_returned: Number of items returned by the query.
        tokens_injected: Number of tokens injected into context.
        latency_ms: Query latency in milliseconds.
        status: Query outcome (ok or error).
    """

    query_type: GraphitiQueryType = Field(
        description="Type of Graphiti query from controlled vocabulary"
    )
    items_returned: int = Field(
        ge=0, description="Number of items returned by the query"
    )
    tokens_injected: int = Field(
        ge=0, description="Number of tokens injected into context"
    )
    latency_ms: float = Field(description="Query latency in milliseconds")
    status: GraphitiStatus = Field(description="Query outcome: ok or error")


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Base
    "BaseEvent",
    # Events
    "LLMCallEvent",
    "ToolExecEvent",
    "TaskStartedEvent",
    "TaskCompletedEvent",
    "TaskFailedEvent",
    "WaveCompletedEvent",
    "FeatureCheckAttemptEvent",
    "GraphitiQueryEvent",
    # Controlled vocabularies
    "AgentRole",
    "FailureCategory",
    "PromptProfile",
    "LLMProvider",
    "LLMCallStatus",
    "LLMCallErrorType",
    "GraphitiQueryType",
    "GraphitiStatus",
    "FeatureCheckFailureKind",
]
