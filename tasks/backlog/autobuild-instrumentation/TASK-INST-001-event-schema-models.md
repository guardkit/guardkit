---
id: TASK-INST-001
title: Define event schema Pydantic models
task_type: scaffolding
parent_review: TASK-REV-2FE2
feature_id: FEAT-INST
wave: 1
implementation_mode: task-work
complexity: 4
dependencies: []
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-CF57
  base_branch: main
  started_at: '2026-03-02T21:52:00.023086'
  last_updated: '2026-03-02T21:56:57.789383'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-03-02T21:52:00.023086'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Define Event Schema Pydantic Models

## Description

Create the foundational Pydantic v2 models for all AutoBuild instrumentation events. These models define the structured contract for every event emitted during an AutoBuild run and are consumed by all downstream tasks.

## Requirements

### Event Models

1. **BaseEvent** — Abstract base with common fields:
   - `run_id: str` (non-null)
   - `feature_id: Optional[str]`
   - `task_id: str`
   - `agent_role: Literal["player", "coach", "resolver", "router"]`
   - `attempt: int` (1-indexed)
   - `timestamp: str` (ISO 8601)
   - `schema_version: str` (default "1.0.0")

2. **LLMCallEvent** — Every model invocation:
   - `provider: Literal["anthropic", "openai", "local-vllm"]`
   - `model: str`
   - `input_tokens: int` (>= 0)
   - `output_tokens: int` (>= 0)
   - `latency_ms: float` (non-null)
   - `ttft_ms: Optional[float]`
   - `prefix_cache_hit: Optional[bool]`
   - `prefix_cache_estimated: bool` (default False)
   - `context_bytes: Optional[int]`
   - `prompt_profile: str` (from controlled vocabulary)
   - `status: Literal["ok", "error"]`
   - `error_type: Optional[Literal["rate_limited", "timeout", "tool_error", "other"]]`

3. **ToolExecEvent** — Every shell/tool invocation:
   - `tool_name: str`
   - `cmd: str` (redacted)
   - `exit_code: int`
   - `latency_ms: float`
   - `stdout_tail: str` (truncated)
   - `stderr_tail: str` (truncated)

4. **TaskStartedEvent** / **TaskCompletedEvent** / **TaskFailedEvent**:
   - `task.started`: attempt field
   - `task.completed`: turn_count, diff_stats, verification_status, prompt_profile
   - `task.failed`: failure_category from controlled vocabulary

5. **WaveCompletedEvent**:
   - `wave_id: str`
   - `worker_count: int`
   - `queue_depth_start: int`
   - `queue_depth_end: int`
   - `tasks_completed: int`
   - `task_failures: int`
   - `rate_limit_count: int`
   - `p95_task_latency_ms: Optional[float]`

6. **GraphitiQueryEvent**:
   - `query_type: Literal["context_loader", "nearest_neighbours", "adr_lookup"]`
   - `items_returned: int`
   - `tokens_injected: int`
   - `latency_ms: float`
   - `status: Literal["ok", "error"]`

### Controlled Vocabularies

- **failure_category**: `knowledge_gap`, `context_missing`, `spec_ambiguity`, `test_failure`, `env_failure`, `dependency_issue`, `rate_limit`, `timeout`, `tool_error`, `other`
- **prompt_profile**: `digest_only`, `digest+graphiti`, `digest+rules_bundle`, `digest+graphiti+rules_bundle`
- **agent_role**: `player`, `coach`, `resolver`, `router`

### Validation

- Events with missing required fields MUST be rejected with clear error messages
- Events with invalid controlled vocabulary values MUST be rejected
- Events with unrecognised `agent_role` MUST be rejected listing valid roles
- Zero `input_tokens` is valid and should produce a structurally valid event

## Acceptance Criteria

- [ ] All 7 event model classes defined with Pydantic v2
- [ ] Controlled vocabularies enforced via Literal types
- [ ] BaseEvent provides common fields inherited by all events
- [ ] Invalid events rejected with descriptive ValidationError messages
- [ ] schema_version field present on all events (default "1.0.0")
- [ ] Models support model_dump() for JSON serialization
- [ ] Zero input_tokens produces valid LLMCallEvent
- [ ] Unit tests cover all event types, valid/invalid cases, boundary values

## File Location

`guardkit/orchestrator/instrumentation/schemas.py`

## Test Location

`tests/orchestrator/instrumentation/test_schemas.py`
