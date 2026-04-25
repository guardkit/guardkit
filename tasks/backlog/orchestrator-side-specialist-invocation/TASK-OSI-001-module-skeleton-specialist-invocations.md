---
id: TASK-OSI-001
title: "Module skeleton: specialist_invocations.py"
status: backlog
created: 2026-04-25T00:00:00Z
updated: 2026-04-25T00:00:00Z
priority: high
task_type: scaffolding
parent_review: TASK-REV-119C1
feature_id: FEAT-AB59
wave: 1
implementation_mode: direct
complexity: 2
dependencies: []
tags: [autobuild, orchestrator, scaffolding, OSI, F4A1-followup]
---

# Task: Module skeleton — specialist_invocations.py

## Description

Create the new `guardkit/orchestrator/specialist_invocations.py` module that
will house the orchestrator-side specialist runners for AutoBuild Phases 4
and 5. This task creates the module skeleton with the result dataclass and
the shared `run_specialist` helper. The actual specialist runners are
delivered in TASK-OSI-004 and TASK-OSI-005.

The module separates orchestrator-side specialist logic from `AgentInvoker`'s
existing surface, reusing `AgentInvoker._invoke_with_role` via composition
rather than duplicating SDK invocation logic.

## Acceptance Criteria

- [ ] Module exists at `guardkit/orchestrator/specialist_invocations.py`.
- [ ] Exports `SpecialistInvocationResult` dataclass with fields:
      `specialist_name: str`, `phase: str`, `status: Literal["passed",
      "failed", "skipped"]`, `duration_seconds: float`, `result_file:
      Optional[Path]`, `error: Optional[str]`.
- [ ] Exports `run_specialist` async function with signature
      `(specialist_name: str, worktree_path: Path, task_id: str,
      sdk_timeout: int, prompt: str, allowed_tools: list[str],
      agent_invoker: AgentInvoker) -> SpecialistInvocationResult`.
- [ ] `run_specialist` body delegates to
      `AgentInvoker._invoke_with_role` via composition (no duplication of
      SDK invocation logic) and returns a populated
      `SpecialistInvocationResult`.
- [ ] On exception or timeout, `run_specialist` calls
      `AgentInvoker._kill_child_claude_processes` in a try/finally and
      returns `status="failed"` with `error` populated — NEVER raises.
- [ ] Module has a top-level docstring naming this task and TASK-REV-119C1.
- [ ] All modified files pass project-configured lint/format checks with
      zero errors.

## Implementation Notes

- The runner should accept a `cancellation_event` and forward it to
  `_invoke_with_role` so the existing per-turn cancellation path fires.
- Reference: `guardkit/orchestrator/agent_invoker.py:2191`
  (`_invoke_with_role` signature) and line 1064
  (`_kill_child_claude_processes`).
- This module is a primary deliverable function per
  `.claude/rules/anti-stub.md` — `run_specialist` body MUST contain real
  delegation logic, not `pass` or `NotImplementedError`.

## Notes

- Wave 1, parallel-safe with TASK-OSI-002 and TASK-OSI-003.
- Sets up the contract that TASK-OSI-004 and TASK-OSI-005 fulfill.
