"""Tests for AutoBuild instrumentation event schema Pydantic models.

Covers all 7 event model classes, controlled vocabularies, validation,
serialization, inheritance, and boundary values.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from guardkit.orchestrator.instrumentation.schemas import (
    BaseEvent,
    LLMCallEvent,
    ToolExecEvent,
    TaskStartedEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
    WaveCompletedEvent,
    GraphitiQueryEvent,
    AgentRole,
    FailureCategory,
    PromptProfile,
    LLMProvider,
    LLMCallStatus,
    LLMCallErrorType,
    GraphitiQueryType,
    GraphitiStatus,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def base_fields() -> dict:
    """Minimal valid fields for BaseEvent-derived models."""
    return {
        "run_id": "run-abc-123",
        "task_id": "TASK-001",
        "agent_role": "player",
        "attempt": 1,
        "timestamp": "2026-03-02T12:00:00Z",
    }


@pytest.fixture
def valid_llm_call(base_fields: dict) -> dict:
    """Minimal valid LLMCallEvent fields."""
    return {
        **base_fields,
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "input_tokens": 1000,
        "output_tokens": 500,
        "latency_ms": 1234.5,
        "prompt_profile": "digest_only",
        "status": "ok",
    }


@pytest.fixture
def valid_tool_exec(base_fields: dict) -> dict:
    """Minimal valid ToolExecEvent fields."""
    return {
        **base_fields,
        "tool_name": "bash",
        "cmd": "pytest tests/ -v",
        "exit_code": 0,
        "latency_ms": 5000.0,
        "stdout_tail": "All tests passed",
        "stderr_tail": "",
    }


@pytest.fixture
def valid_task_started(base_fields: dict) -> dict:
    """Valid TaskStartedEvent fields."""
    return {**base_fields}


@pytest.fixture
def valid_task_completed(base_fields: dict) -> dict:
    """Valid TaskCompletedEvent fields."""
    return {
        **base_fields,
        "turn_count": 3,
        "diff_stats": "+50 -10",
        "verification_status": "verified",
        "prompt_profile": "digest+graphiti",
    }


@pytest.fixture
def valid_task_failed(base_fields: dict) -> dict:
    """Valid TaskFailedEvent fields."""
    return {
        **base_fields,
        "failure_category": "test_failure",
    }


@pytest.fixture
def valid_wave_completed(base_fields: dict) -> dict:
    """Valid WaveCompletedEvent fields."""
    return {
        **base_fields,
        "wave_id": "wave-1",
        "worker_count": 4,
        "queue_depth_start": 10,
        "queue_depth_end": 0,
        "tasks_completed": 8,
        "task_failures": 2,
        "rate_limit_count": 1,
    }


@pytest.fixture
def valid_graphiti_query(base_fields: dict) -> dict:
    """Valid GraphitiQueryEvent fields."""
    return {
        **base_fields,
        "query_type": "context_loader",
        "items_returned": 5,
        "tokens_injected": 2000,
        "latency_ms": 150.0,
        "status": "ok",
    }


# ============================================================================
# BaseEvent Tests
# ============================================================================


class TestBaseEvent:
    """Tests for BaseEvent abstract base model."""

    def test_schema_version_default(self, base_fields: dict) -> None:
        """schema_version defaults to '1.0.0'."""
        event = LLMCallEvent(
            **base_fields,
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=100,
            output_tokens=50,
            latency_ms=100.0,
            prompt_profile="digest_only",
            status="ok",
        )
        assert event.schema_version == "1.0.0"

    def test_feature_id_optional(self, base_fields: dict) -> None:
        """feature_id is optional and defaults to None."""
        event = LLMCallEvent(
            **base_fields,
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=100,
            output_tokens=50,
            latency_ms=100.0,
            prompt_profile="digest_only",
            status="ok",
        )
        assert event.feature_id is None

    def test_feature_id_provided(self, base_fields: dict) -> None:
        """feature_id can be explicitly provided."""
        event = LLMCallEvent(
            **base_fields,
            feature_id="FEAT-ABC",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=100,
            output_tokens=50,
            latency_ms=100.0,
            prompt_profile="digest_only",
            status="ok",
        )
        assert event.feature_id == "FEAT-ABC"

    def test_missing_run_id_rejected(self, base_fields: dict) -> None:
        """Missing run_id raises ValidationError."""
        del base_fields["run_id"]
        with pytest.raises(ValidationError) as exc_info:
            LLMCallEvent(
                **base_fields,
                provider="anthropic",
                model="claude-sonnet-4-20250514",
                input_tokens=100,
                output_tokens=50,
                latency_ms=100.0,
                prompt_profile="digest_only",
                status="ok",
            )
        assert "run_id" in str(exc_info.value)

    def test_missing_task_id_rejected(self, base_fields: dict) -> None:
        """Missing task_id raises ValidationError."""
        del base_fields["task_id"]
        with pytest.raises(ValidationError) as exc_info:
            LLMCallEvent(
                **base_fields,
                provider="anthropic",
                model="claude-sonnet-4-20250514",
                input_tokens=100,
                output_tokens=50,
                latency_ms=100.0,
                prompt_profile="digest_only",
                status="ok",
            )
        assert "task_id" in str(exc_info.value)

    def test_invalid_agent_role_rejected(self, base_fields: dict) -> None:
        """Invalid agent_role value raises ValidationError."""
        base_fields["agent_role"] = "wizard"
        with pytest.raises(ValidationError) as exc_info:
            LLMCallEvent(
                **base_fields,
                provider="anthropic",
                model="claude-sonnet-4-20250514",
                input_tokens=100,
                output_tokens=50,
                latency_ms=100.0,
                prompt_profile="digest_only",
                status="ok",
            )
        # Should list valid roles in the error
        error_str = str(exc_info.value)
        assert "agent_role" in error_str

    def test_all_valid_agent_roles(self, base_fields: dict) -> None:
        """All defined agent roles are accepted."""
        for role in ["player", "coach", "resolver", "router"]:
            base_fields["agent_role"] = role
            event = LLMCallEvent(
                **base_fields,
                provider="anthropic",
                model="claude-sonnet-4-20250514",
                input_tokens=100,
                output_tokens=50,
                latency_ms=100.0,
                prompt_profile="digest_only",
                status="ok",
            )
            assert event.agent_role == role

    def test_attempt_must_be_positive(self, base_fields: dict) -> None:
        """Attempt must be >= 1 (1-indexed)."""
        base_fields["attempt"] = 0
        with pytest.raises(ValidationError) as exc_info:
            LLMCallEvent(
                **base_fields,
                provider="anthropic",
                model="claude-sonnet-4-20250514",
                input_tokens=100,
                output_tokens=50,
                latency_ms=100.0,
                prompt_profile="digest_only",
                status="ok",
            )
        assert "attempt" in str(exc_info.value)

    def test_attempt_one_is_valid(self, base_fields: dict) -> None:
        """Attempt=1 is the minimum valid value."""
        base_fields["attempt"] = 1
        event = LLMCallEvent(
            **base_fields,
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=100,
            output_tokens=50,
            latency_ms=100.0,
            prompt_profile="digest_only",
            status="ok",
        )
        assert event.attempt == 1

    def test_model_dump_serialization(self, valid_llm_call: dict) -> None:
        """model_dump() produces a serializable dictionary."""
        event = LLMCallEvent(**valid_llm_call)
        dumped = event.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["run_id"] == "run-abc-123"
        assert dumped["schema_version"] == "1.0.0"
        assert dumped["agent_role"] == "player"

    def test_common_fields_inherited(self, valid_llm_call: dict) -> None:
        """All BaseEvent fields are present on child models."""
        event = LLMCallEvent(**valid_llm_call)
        assert hasattr(event, "run_id")
        assert hasattr(event, "feature_id")
        assert hasattr(event, "task_id")
        assert hasattr(event, "agent_role")
        assert hasattr(event, "attempt")
        assert hasattr(event, "timestamp")
        assert hasattr(event, "schema_version")


# ============================================================================
# LLMCallEvent Tests
# ============================================================================


class TestLLMCallEvent:
    """Tests for LLMCallEvent model."""

    def test_valid_creation(self, valid_llm_call: dict) -> None:
        """Valid LLMCallEvent is created successfully."""
        event = LLMCallEvent(**valid_llm_call)
        assert event.provider == "anthropic"
        assert event.model == "claude-sonnet-4-20250514"
        assert event.input_tokens == 1000
        assert event.output_tokens == 500
        assert event.latency_ms == 1234.5

    def test_all_providers_valid(self, valid_llm_call: dict) -> None:
        """All defined provider values are accepted."""
        for provider in ["anthropic", "openai", "local-vllm"]:
            valid_llm_call["provider"] = provider
            event = LLMCallEvent(**valid_llm_call)
            assert event.provider == provider

    def test_invalid_provider_rejected(self, valid_llm_call: dict) -> None:
        """Invalid provider value raises ValidationError."""
        valid_llm_call["provider"] = "google"
        with pytest.raises(ValidationError) as exc_info:
            LLMCallEvent(**valid_llm_call)
        assert "provider" in str(exc_info.value)

    def test_zero_input_tokens_valid(self, valid_llm_call: dict) -> None:
        """Zero input_tokens is valid and produces a structurally valid event."""
        valid_llm_call["input_tokens"] = 0
        event = LLMCallEvent(**valid_llm_call)
        assert event.input_tokens == 0
        # Verify full serialization works
        dumped = event.model_dump()
        assert dumped["input_tokens"] == 0

    def test_zero_output_tokens_valid(self, valid_llm_call: dict) -> None:
        """Zero output_tokens is valid."""
        valid_llm_call["output_tokens"] = 0
        event = LLMCallEvent(**valid_llm_call)
        assert event.output_tokens == 0

    def test_negative_tokens_rejected(self, valid_llm_call: dict) -> None:
        """Negative token counts are rejected."""
        valid_llm_call["input_tokens"] = -1
        with pytest.raises(ValidationError) as exc_info:
            LLMCallEvent(**valid_llm_call)
        assert "input_tokens" in str(exc_info.value)

    def test_negative_output_tokens_rejected(self, valid_llm_call: dict) -> None:
        """Negative output_tokens are rejected."""
        valid_llm_call["output_tokens"] = -5
        with pytest.raises(ValidationError) as exc_info:
            LLMCallEvent(**valid_llm_call)
        assert "output_tokens" in str(exc_info.value)

    def test_ttft_ms_optional(self, valid_llm_call: dict) -> None:
        """ttft_ms defaults to None."""
        event = LLMCallEvent(**valid_llm_call)
        assert event.ttft_ms is None

    def test_ttft_ms_provided(self, valid_llm_call: dict) -> None:
        """ttft_ms can be explicitly provided."""
        valid_llm_call["ttft_ms"] = 250.5
        event = LLMCallEvent(**valid_llm_call)
        assert event.ttft_ms == 250.5

    def test_prefix_cache_hit_optional(self, valid_llm_call: dict) -> None:
        """prefix_cache_hit defaults to None."""
        event = LLMCallEvent(**valid_llm_call)
        assert event.prefix_cache_hit is None

    def test_prefix_cache_estimated_default(self, valid_llm_call: dict) -> None:
        """prefix_cache_estimated defaults to False."""
        event = LLMCallEvent(**valid_llm_call)
        assert event.prefix_cache_estimated is False

    def test_context_bytes_optional(self, valid_llm_call: dict) -> None:
        """context_bytes defaults to None."""
        event = LLMCallEvent(**valid_llm_call)
        assert event.context_bytes is None

    def test_all_prompt_profiles(self, valid_llm_call: dict) -> None:
        """All defined prompt_profile values are accepted."""
        for profile in [
            "digest_only",
            "digest+graphiti",
            "digest+rules_bundle",
            "digest+graphiti+rules_bundle",
        ]:
            valid_llm_call["prompt_profile"] = profile
            event = LLMCallEvent(**valid_llm_call)
            assert event.prompt_profile == profile

    def test_invalid_prompt_profile_rejected(self, valid_llm_call: dict) -> None:
        """Invalid prompt_profile raises ValidationError."""
        valid_llm_call["prompt_profile"] = "custom_profile"
        with pytest.raises(ValidationError) as exc_info:
            LLMCallEvent(**valid_llm_call)
        assert "prompt_profile" in str(exc_info.value)

    def test_status_ok(self, valid_llm_call: dict) -> None:
        """Status 'ok' is valid."""
        valid_llm_call["status"] = "ok"
        event = LLMCallEvent(**valid_llm_call)
        assert event.status == "ok"

    def test_status_error(self, valid_llm_call: dict) -> None:
        """Status 'error' is valid."""
        valid_llm_call["status"] = "error"
        event = LLMCallEvent(**valid_llm_call)
        assert event.status == "error"

    def test_invalid_status_rejected(self, valid_llm_call: dict) -> None:
        """Invalid status raises ValidationError."""
        valid_llm_call["status"] = "warning"
        with pytest.raises(ValidationError) as exc_info:
            LLMCallEvent(**valid_llm_call)
        assert "status" in str(exc_info.value)

    def test_error_type_optional(self, valid_llm_call: dict) -> None:
        """error_type defaults to None."""
        event = LLMCallEvent(**valid_llm_call)
        assert event.error_type is None

    def test_all_error_types(self, valid_llm_call: dict) -> None:
        """All defined error_type values are accepted."""
        for error_type in ["rate_limited", "timeout", "tool_error", "other"]:
            valid_llm_call["error_type"] = error_type
            event = LLMCallEvent(**valid_llm_call)
            assert event.error_type == error_type

    def test_invalid_error_type_rejected(self, valid_llm_call: dict) -> None:
        """Invalid error_type raises ValidationError."""
        valid_llm_call["error_type"] = "unknown_error"
        with pytest.raises(ValidationError) as exc_info:
            LLMCallEvent(**valid_llm_call)
        assert "error_type" in str(exc_info.value)

    def test_model_dump_all_fields(self, valid_llm_call: dict) -> None:
        """model_dump includes all fields."""
        valid_llm_call["ttft_ms"] = 200.0
        valid_llm_call["prefix_cache_hit"] = True
        valid_llm_call["prefix_cache_estimated"] = True
        valid_llm_call["context_bytes"] = 4096
        valid_llm_call["error_type"] = "rate_limited"
        event = LLMCallEvent(**valid_llm_call)
        dumped = event.model_dump()
        assert dumped["ttft_ms"] == 200.0
        assert dumped["prefix_cache_hit"] is True
        assert dumped["prefix_cache_estimated"] is True
        assert dumped["context_bytes"] == 4096
        assert dumped["error_type"] == "rate_limited"


# ============================================================================
# ToolExecEvent Tests
# ============================================================================


class TestToolExecEvent:
    """Tests for ToolExecEvent model."""

    def test_valid_creation(self, valid_tool_exec: dict) -> None:
        """Valid ToolExecEvent is created successfully."""
        event = ToolExecEvent(**valid_tool_exec)
        assert event.tool_name == "bash"
        assert event.cmd == "pytest tests/ -v"
        assert event.exit_code == 0
        assert event.latency_ms == 5000.0
        assert event.stdout_tail == "All tests passed"
        assert event.stderr_tail == ""

    def test_negative_exit_code_valid(self, valid_tool_exec: dict) -> None:
        """Negative exit codes are valid (signal kills)."""
        valid_tool_exec["exit_code"] = -9
        event = ToolExecEvent(**valid_tool_exec)
        assert event.exit_code == -9

    def test_empty_stdout_valid(self, valid_tool_exec: dict) -> None:
        """Empty stdout_tail is valid."""
        valid_tool_exec["stdout_tail"] = ""
        event = ToolExecEvent(**valid_tool_exec)
        assert event.stdout_tail == ""

    def test_empty_stderr_valid(self, valid_tool_exec: dict) -> None:
        """Empty stderr_tail is valid."""
        valid_tool_exec["stderr_tail"] = ""
        event = ToolExecEvent(**valid_tool_exec)
        assert event.stderr_tail == ""

    def test_model_dump_serialization(self, valid_tool_exec: dict) -> None:
        """model_dump() includes all ToolExecEvent fields."""
        event = ToolExecEvent(**valid_tool_exec)
        dumped = event.model_dump()
        assert dumped["tool_name"] == "bash"
        assert dumped["cmd"] == "pytest tests/ -v"
        assert dumped["exit_code"] == 0
        assert "run_id" in dumped  # base fields present

    def test_inherits_base_event(self, valid_tool_exec: dict) -> None:
        """ToolExecEvent inherits BaseEvent fields."""
        event = ToolExecEvent(**valid_tool_exec)
        assert event.run_id == "run-abc-123"
        assert event.schema_version == "1.0.0"
        assert event.agent_role == "player"


# ============================================================================
# TaskStartedEvent Tests
# ============================================================================


class TestTaskStartedEvent:
    """Tests for TaskStartedEvent model."""

    def test_valid_creation(self, valid_task_started: dict) -> None:
        """Valid TaskStartedEvent is created with base fields only."""
        event = TaskStartedEvent(**valid_task_started)
        assert event.run_id == "run-abc-123"
        assert event.task_id == "TASK-001"
        assert event.attempt == 1

    def test_inherits_base_event(self, valid_task_started: dict) -> None:
        """TaskStartedEvent inherits BaseEvent fields."""
        event = TaskStartedEvent(**valid_task_started)
        assert event.schema_version == "1.0.0"
        assert event.agent_role == "player"

    def test_model_dump_serialization(self, valid_task_started: dict) -> None:
        """model_dump() works for TaskStartedEvent."""
        event = TaskStartedEvent(**valid_task_started)
        dumped = event.model_dump()
        assert dumped["task_id"] == "TASK-001"
        assert dumped["attempt"] == 1


# ============================================================================
# TaskCompletedEvent Tests
# ============================================================================


class TestTaskCompletedEvent:
    """Tests for TaskCompletedEvent model."""

    def test_valid_creation(self, valid_task_completed: dict) -> None:
        """Valid TaskCompletedEvent is created successfully."""
        event = TaskCompletedEvent(**valid_task_completed)
        assert event.turn_count == 3
        assert event.diff_stats == "+50 -10"
        assert event.verification_status == "verified"
        assert event.prompt_profile == "digest+graphiti"

    def test_valid_prompt_profiles(self, valid_task_completed: dict) -> None:
        """All prompt_profile values accepted in TaskCompletedEvent."""
        for profile in [
            "digest_only",
            "digest+graphiti",
            "digest+rules_bundle",
            "digest+graphiti+rules_bundle",
        ]:
            valid_task_completed["prompt_profile"] = profile
            event = TaskCompletedEvent(**valid_task_completed)
            assert event.prompt_profile == profile

    def test_invalid_prompt_profile_rejected(self, valid_task_completed: dict) -> None:
        """Invalid prompt_profile in TaskCompletedEvent raises ValidationError."""
        valid_task_completed["prompt_profile"] = "invalid_profile"
        with pytest.raises(ValidationError) as exc_info:
            TaskCompletedEvent(**valid_task_completed)
        assert "prompt_profile" in str(exc_info.value)

    def test_model_dump_serialization(self, valid_task_completed: dict) -> None:
        """model_dump() includes all TaskCompletedEvent fields."""
        event = TaskCompletedEvent(**valid_task_completed)
        dumped = event.model_dump()
        assert dumped["turn_count"] == 3
        assert dumped["diff_stats"] == "+50 -10"
        assert dumped["verification_status"] == "verified"
        assert dumped["prompt_profile"] == "digest+graphiti"

    def test_inherits_base_event(self, valid_task_completed: dict) -> None:
        """TaskCompletedEvent inherits BaseEvent fields."""
        event = TaskCompletedEvent(**valid_task_completed)
        assert event.schema_version == "1.0.0"
        assert event.run_id == "run-abc-123"


# ============================================================================
# TaskFailedEvent Tests
# ============================================================================


class TestTaskFailedEvent:
    """Tests for TaskFailedEvent model."""

    def test_valid_creation(self, valid_task_failed: dict) -> None:
        """Valid TaskFailedEvent is created successfully."""
        event = TaskFailedEvent(**valid_task_failed)
        assert event.failure_category == "test_failure"

    def test_all_failure_categories(self, valid_task_failed: dict) -> None:
        """All defined failure_category values are accepted."""
        categories = [
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
        for category in categories:
            valid_task_failed["failure_category"] = category
            event = TaskFailedEvent(**valid_task_failed)
            assert event.failure_category == category

    def test_invalid_failure_category_rejected(self, valid_task_failed: dict) -> None:
        """Invalid failure_category raises ValidationError."""
        valid_task_failed["failure_category"] = "magic_failure"
        with pytest.raises(ValidationError) as exc_info:
            TaskFailedEvent(**valid_task_failed)
        assert "failure_category" in str(exc_info.value)

    def test_model_dump_serialization(self, valid_task_failed: dict) -> None:
        """model_dump() includes failure_category."""
        event = TaskFailedEvent(**valid_task_failed)
        dumped = event.model_dump()
        assert dumped["failure_category"] == "test_failure"

    def test_inherits_base_event(self, valid_task_failed: dict) -> None:
        """TaskFailedEvent inherits BaseEvent fields."""
        event = TaskFailedEvent(**valid_task_failed)
        assert event.schema_version == "1.0.0"
        assert event.task_id == "TASK-001"


# ============================================================================
# WaveCompletedEvent Tests
# ============================================================================


class TestWaveCompletedEvent:
    """Tests for WaveCompletedEvent model."""

    def test_valid_creation(self, valid_wave_completed: dict) -> None:
        """Valid WaveCompletedEvent is created successfully."""
        event = WaveCompletedEvent(**valid_wave_completed)
        assert event.wave_id == "wave-1"
        assert event.worker_count == 4
        assert event.queue_depth_start == 10
        assert event.queue_depth_end == 0
        assert event.tasks_completed == 8
        assert event.task_failures == 2
        assert event.rate_limit_count == 1

    def test_p95_optional(self, valid_wave_completed: dict) -> None:
        """p95_task_latency_ms defaults to None."""
        event = WaveCompletedEvent(**valid_wave_completed)
        assert event.p95_task_latency_ms is None

    def test_p95_provided(self, valid_wave_completed: dict) -> None:
        """p95_task_latency_ms can be provided."""
        valid_wave_completed["p95_task_latency_ms"] = 45000.0
        event = WaveCompletedEvent(**valid_wave_completed)
        assert event.p95_task_latency_ms == 45000.0

    def test_zero_values_valid(self, valid_wave_completed: dict) -> None:
        """Zero values for counts are valid."""
        valid_wave_completed["tasks_completed"] = 0
        valid_wave_completed["task_failures"] = 0
        valid_wave_completed["rate_limit_count"] = 0
        event = WaveCompletedEvent(**valid_wave_completed)
        assert event.tasks_completed == 0
        assert event.task_failures == 0
        assert event.rate_limit_count == 0

    def test_negative_worker_count_rejected(self, valid_wave_completed: dict) -> None:
        """Negative worker_count is rejected."""
        valid_wave_completed["worker_count"] = -1
        with pytest.raises(ValidationError) as exc_info:
            WaveCompletedEvent(**valid_wave_completed)
        assert "worker_count" in str(exc_info.value)

    def test_negative_tasks_completed_rejected(self, valid_wave_completed: dict) -> None:
        """Negative tasks_completed is rejected."""
        valid_wave_completed["tasks_completed"] = -1
        with pytest.raises(ValidationError) as exc_info:
            WaveCompletedEvent(**valid_wave_completed)
        assert "tasks_completed" in str(exc_info.value)

    def test_model_dump_serialization(self, valid_wave_completed: dict) -> None:
        """model_dump() includes all WaveCompletedEvent fields."""
        event = WaveCompletedEvent(**valid_wave_completed)
        dumped = event.model_dump()
        assert dumped["wave_id"] == "wave-1"
        assert dumped["worker_count"] == 4
        assert "run_id" in dumped  # base fields present

    def test_inherits_base_event(self, valid_wave_completed: dict) -> None:
        """WaveCompletedEvent inherits BaseEvent fields."""
        event = WaveCompletedEvent(**valid_wave_completed)
        assert event.schema_version == "1.0.0"
        assert event.agent_role == "player"


# ============================================================================
# GraphitiQueryEvent Tests
# ============================================================================


class TestGraphitiQueryEvent:
    """Tests for GraphitiQueryEvent model."""

    def test_valid_creation(self, valid_graphiti_query: dict) -> None:
        """Valid GraphitiQueryEvent is created successfully."""
        event = GraphitiQueryEvent(**valid_graphiti_query)
        assert event.query_type == "context_loader"
        assert event.items_returned == 5
        assert event.tokens_injected == 2000
        assert event.latency_ms == 150.0
        assert event.status == "ok"

    def test_all_query_types(self, valid_graphiti_query: dict) -> None:
        """All defined query_type values are accepted."""
        for qtype in ["context_loader", "nearest_neighbours", "adr_lookup"]:
            valid_graphiti_query["query_type"] = qtype
            event = GraphitiQueryEvent(**valid_graphiti_query)
            assert event.query_type == qtype

    def test_invalid_query_type_rejected(self, valid_graphiti_query: dict) -> None:
        """Invalid query_type raises ValidationError."""
        valid_graphiti_query["query_type"] = "full_text_search"
        with pytest.raises(ValidationError) as exc_info:
            GraphitiQueryEvent(**valid_graphiti_query)
        assert "query_type" in str(exc_info.value)

    def test_status_ok_and_error(self, valid_graphiti_query: dict) -> None:
        """Both 'ok' and 'error' status values are accepted."""
        for status in ["ok", "error"]:
            valid_graphiti_query["status"] = status
            event = GraphitiQueryEvent(**valid_graphiti_query)
            assert event.status == status

    def test_invalid_status_rejected(self, valid_graphiti_query: dict) -> None:
        """Invalid status raises ValidationError."""
        valid_graphiti_query["status"] = "pending"
        with pytest.raises(ValidationError) as exc_info:
            GraphitiQueryEvent(**valid_graphiti_query)
        assert "status" in str(exc_info.value)

    def test_zero_items_returned_valid(self, valid_graphiti_query: dict) -> None:
        """Zero items_returned is valid."""
        valid_graphiti_query["items_returned"] = 0
        event = GraphitiQueryEvent(**valid_graphiti_query)
        assert event.items_returned == 0

    def test_negative_items_returned_rejected(self, valid_graphiti_query: dict) -> None:
        """Negative items_returned is rejected."""
        valid_graphiti_query["items_returned"] = -1
        with pytest.raises(ValidationError) as exc_info:
            GraphitiQueryEvent(**valid_graphiti_query)
        assert "items_returned" in str(exc_info.value)

    def test_model_dump_serialization(self, valid_graphiti_query: dict) -> None:
        """model_dump() includes all GraphitiQueryEvent fields."""
        event = GraphitiQueryEvent(**valid_graphiti_query)
        dumped = event.model_dump()
        assert dumped["query_type"] == "context_loader"
        assert dumped["items_returned"] == 5
        assert dumped["tokens_injected"] == 2000

    def test_inherits_base_event(self, valid_graphiti_query: dict) -> None:
        """GraphitiQueryEvent inherits BaseEvent fields."""
        event = GraphitiQueryEvent(**valid_graphiti_query)
        assert event.schema_version == "1.0.0"
        assert event.run_id == "run-abc-123"


# ============================================================================
# Cross-Event Validation Tests
# ============================================================================


class TestCrossEventValidation:
    """Tests for cross-cutting validation behaviors."""

    def test_all_events_have_schema_version(self, base_fields: dict) -> None:
        """All event types include schema_version field."""
        events = [
            TaskStartedEvent(**base_fields),
            TaskCompletedEvent(
                **base_fields,
                turn_count=1,
                diff_stats="",
                verification_status="verified",
                prompt_profile="digest_only",
            ),
            TaskFailedEvent(**base_fields, failure_category="other"),
            LLMCallEvent(
                **base_fields,
                provider="anthropic",
                model="m",
                input_tokens=0,
                output_tokens=0,
                latency_ms=0.0,
                prompt_profile="digest_only",
                status="ok",
            ),
            ToolExecEvent(
                **base_fields,
                tool_name="t",
                cmd="c",
                exit_code=0,
                latency_ms=0.0,
                stdout_tail="",
                stderr_tail="",
            ),
            WaveCompletedEvent(
                **base_fields,
                wave_id="w",
                worker_count=0,
                queue_depth_start=0,
                queue_depth_end=0,
                tasks_completed=0,
                task_failures=0,
                rate_limit_count=0,
            ),
            GraphitiQueryEvent(
                **base_fields,
                query_type="context_loader",
                items_returned=0,
                tokens_injected=0,
                latency_ms=0.0,
                status="ok",
            ),
        ]
        for event in events:
            assert event.schema_version == "1.0.0", (
                f"{type(event).__name__} missing schema_version"
            )

    def test_all_events_support_model_dump(self, base_fields: dict) -> None:
        """All event types support model_dump() for JSON serialization."""
        events = [
            TaskStartedEvent(**base_fields),
            TaskCompletedEvent(
                **base_fields,
                turn_count=1,
                diff_stats="",
                verification_status="verified",
                prompt_profile="digest_only",
            ),
            TaskFailedEvent(**base_fields, failure_category="other"),
            LLMCallEvent(
                **base_fields,
                provider="anthropic",
                model="m",
                input_tokens=0,
                output_tokens=0,
                latency_ms=0.0,
                prompt_profile="digest_only",
                status="ok",
            ),
            ToolExecEvent(
                **base_fields,
                tool_name="t",
                cmd="c",
                exit_code=0,
                latency_ms=0.0,
                stdout_tail="",
                stderr_tail="",
            ),
            WaveCompletedEvent(
                **base_fields,
                wave_id="w",
                worker_count=0,
                queue_depth_start=0,
                queue_depth_end=0,
                tasks_completed=0,
                task_failures=0,
                rate_limit_count=0,
            ),
            GraphitiQueryEvent(
                **base_fields,
                query_type="context_loader",
                items_returned=0,
                tokens_injected=0,
                latency_ms=0.0,
                status="ok",
            ),
        ]
        for event in events:
            dumped = event.model_dump()
            assert isinstance(dumped, dict), (
                f"{type(event).__name__} model_dump() did not return dict"
            )
            assert "run_id" in dumped
            assert "task_id" in dumped
            assert "schema_version" in dumped

    def test_all_events_reject_missing_required_fields(self) -> None:
        """All event types reject creation with missing required fields."""
        with pytest.raises(ValidationError):
            LLMCallEvent()  # type: ignore[call-arg]
        with pytest.raises(ValidationError):
            ToolExecEvent()  # type: ignore[call-arg]
        with pytest.raises(ValidationError):
            TaskStartedEvent()  # type: ignore[call-arg]
        with pytest.raises(ValidationError):
            TaskCompletedEvent()  # type: ignore[call-arg]
        with pytest.raises(ValidationError):
            TaskFailedEvent()  # type: ignore[call-arg]
        with pytest.raises(ValidationError):
            WaveCompletedEvent()  # type: ignore[call-arg]
        with pytest.raises(ValidationError):
            GraphitiQueryEvent()  # type: ignore[call-arg]

    def test_zero_input_tokens_full_event(self, base_fields: dict) -> None:
        """Zero input_tokens produces a fully valid, serializable LLMCallEvent."""
        event = LLMCallEvent(
            **base_fields,
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=0,
            output_tokens=0,
            latency_ms=100.0,
            prompt_profile="digest_only",
            status="ok",
        )
        dumped = event.model_dump()
        assert dumped["input_tokens"] == 0
        assert dumped["output_tokens"] == 0
        assert isinstance(dumped, dict)
        # Verify JSON serializable
        import json
        json_str = json.dumps(dumped)
        assert json_str  # non-empty
