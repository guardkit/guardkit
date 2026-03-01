---
id: TASK-EVAL-004
title: "Implement EvalAgentInvoker mirroring agent_invoker.py patterns"
task_type: feature
parent_review: TASK-REV-EAE8
feature_id: FEAT-GKVV
status: pending
created: 2026-03-01T00:00:00Z
priority: high
tags: [eval-runner, agent-invoker, sdk]
complexity: 5
wave: 2
implementation_mode: task-work
dependencies:
  - TASK-EVAL-002
---

# Task: Implement EvalAgentInvoker Mirroring agent_invoker.py Patterns

## Description

Implement the eval agent invoker that runs Claude Agent SDK in sandboxed workspaces. This component mirrors `guardkit/orchestrator/agent_invoker.py` exactly — same SDK patterns, same timeout handling, same heartbeat, same error handling.

## Acceptance Criteria

- [ ] `EvalAgentInvoker` wraps `claude_agent_sdk.query()` with eval-specific configuration
- [ ] SDK invocation mirrors `_invoke_with_role()` from `agent_invoker.py`
- [ ] `detect_timeout_multiplier()` imported from existing `agent_invoker.py` — 4x for local vLLM
- [ ] Per-arm timeout calculated as `(brief.setup.timeout_minutes * 60 / 2) * detect_timeout_multiplier()`
- [ ] `async_heartbeat()` imported from existing `agent_invoker.py` — 30s interval
- [ ] `check_assistant_message_error()` imported from `sdk_utils.py` — SDK bug #472 defense
- [ ] `_install_sdk_cleanup_handler()` imported from existing `agent_invoker.py`
- [ ] Max turns per arm respects `brief.setup.max_turns_per_arm` (default 100)
- [ ] Arm reaching max_turns stops gracefully — records what was produced, NOT marked as errored
- [ ] Agent runs within sandboxed workspace directory only — no commands execute outside workspace
- [ ] `Trajectory` dataclass accumulates SDK stream content for judge consumption
- [ ] Agent errors captured and recorded — do not propagate as exceptions
- [ ] `permission_mode="acceptEdits"` (same as AutoBuild Player)
- [ ] Unit tests for timeout calculation, multiplier detection, error handling, turn limits

## Technical Context

- Location: `guardkit/eval/agent_invoker.py` (new module)
- Source patterns: `guardkit/orchestrator/agent_invoker.py` (import directly where possible)
- Source patterns: `guardkit/orchestrator/sdk_utils.py` (import `check_assistant_message_error`)
- Design reference: `docs/research/eval-runner/eval-runner-architecture.md` (Section 2)
- Arm instructions: `docs/research/eval-runner/eval-runner-guardkit-vs-vanilla.md` (Section 6)

## BDD Scenario Coverage

- Boundary: Arm execution respects per-arm timeout (total_timeout / 2)
- Boundary: Arm execution stops at max_turns_per_arm limit (not marked as errored)
- Edge case: Timeout multiplier applied for local vLLM (4x)
- Edge case: Brief with unsafe agent instructions is sandboxed
- Edge case: GuardKit arm failure does not abort vanilla arm

## Implementation Notes

[Space for implementation details]

## Test Execution Log

[Automatically populated by /task-work]
