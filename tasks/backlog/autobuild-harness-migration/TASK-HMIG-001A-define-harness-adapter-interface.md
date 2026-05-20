---
id: TASK-HMIG-001A
title: Define HarnessAdapter interface (guardkit-side ABC)
status: backlog
task_type: implementation
created: 2026-05-19T20:30:00Z
updated: 2026-05-19T20:30:00Z
priority: critical
complexity: 3
deadline: 2026-06-15
parent_review: TASK-REV-HMIG
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 1
parallel_group: 1A
implementation_mode: task-work
intensity: standard
effort_hours: 2
depends_on: []
cross_repo:
  pairs_with: TASK-HMIG-001B  # implementation in guardkitfactory
  notes: This task defines only the ABC. The LangGraphHarness implementation lives in guardkitfactory (TASK-HMIG-001B). ClaudeSDKHarness (legacy) will implement this interface in TASK-HMIG-006.
falsifier: "Unit test in guardkit verifies the ABC has the required signatures (invoke + session_id + supports_resume); a deliberately-incomplete subclass raises TypeError on instantiation. Cross-repo smoke: `pip install -e ../guardkitfactory && python -c 'from guardkitfactory.harness import LangGraphHarness; from guardkit.orchestrator.harness import HarnessAdapter; assert issubclass(LangGraphHarness, HarnessAdapter)'` succeeds (this becomes runnable once TASK-HMIG-001B is also done)."
tags:
  - autobuild
  - harness
  - langgraph-migration
  - cross-repo
---

# Task: Define HarnessAdapter interface (guardkit-side ABC)

## Description

Create the `HarnessAdapter` abstract base class in `guardkit` so that both
`ClaudeSDKHarness` (legacy, will be added in TASK-HMIG-006) and
`LangGraphHarness` (new, implemented in `guardkitfactory` via TASK-HMIG-001B)
can implement it. This task is the smallest possible unit of the cross-repo
boundary and intentionally ships nothing else.

The ABC is consumed by `agent_invoker._invoke_with_role` (refactored in
TASK-HMIG-006) to dispatch through either substrate based on the
`GUARDKIT_HARNESS=sdk|langgraph` env var.

## Acceptance Criteria

- [ ] AC-001: New module `guardkit/orchestrator/harness/__init__.py` (re-exports
      `HarnessAdapter` and `HarnessEvent`).
- [ ] AC-002: New module `guardkit/orchestrator/harness/adapter.py` defining:
  - `HarnessAdapter(ABC)` with abstract method
    `async def invoke(self, prompt: str, role: str, tools: list, cwd: Path, *, timeout_seconds: int) -> AsyncIterator[HarnessEvent]`
  - Properties `session_id: str | None` and `supports_resume: bool`.
- [ ] AC-003: `HarnessEvent` dataclass / TypedDict with discriminated-union
      shape covering at least: `assistant_message`, `tool_use`, `tool_result`,
      `result_message` (mirrors what SDK message types currently emit; see
      review §3.5 for the OUT contract).
- [ ] AC-004: Module docstring explicitly states the cross-repo contract: the
      `LangGraphHarness` lives in `guardkitfactory` and is imported by
      `agent_invoker.py` only after the cutover flag is set.
- [ ] AC-005: Unit test at `tests/orchestrator/harness/test_adapter_interface.py`:
  - Instantiating `HarnessAdapter` directly raises `TypeError` (it's abstract).
  - A deliberately-incomplete subclass (missing `invoke`) also raises `TypeError`.
  - A trivial fake subclass implementing `invoke` instantiates cleanly and the
    `session_id` / `supports_resume` properties return their default values.
- [ ] AC-006: No imports from `claude_agent_sdk`, `anthropic`, or
      `guardkitfactory` in this module — it's pure abstract surface.

## Implementation Notes

- This task is intentionally small (~2h) to act as the cross-repo coordination
  point. Once landed, TASK-HMIG-001B (in guardkitfactory) can target this
  concrete ABC.
- The `HarnessEvent` taxonomy is informed by the touch-point map in review §4
  and the message-handling code at `guardkit/orchestrator/agent_invoker.py:2542-2613`.
  Keep the taxonomy tight — only add events that downstream consumers
  actually read.
- Do NOT add a `ClaudeSDKHarness` implementation in this task. That happens
  in TASK-HMIG-006 alongside the `agent_invoker` refactor.

## References

- Review §2.4 — C4 Code-level diagram showing the `HarnessAdapter` interface and both implementations
- Review §3.2-§3.5 — what the current SDK boundary passes IN and expects OUT
- Review §14.8 — Revision 2 (D-01) explaining why the implementation lives in `guardkitfactory`
- Pair: `~/Projects/appmilla_github/guardkitfactory/tasks/backlog/autobuild-harness-migration/TASK-HMIG-001B-implement-langgraph-harness-skeleton.md`

## Notes

This task is the cleanest "ratchet point" in Wave 1: once the ABC is landed
and merged in guardkit, the guardkitfactory side has a stable target to
implement against. No work in this task touches the SDK seam.
