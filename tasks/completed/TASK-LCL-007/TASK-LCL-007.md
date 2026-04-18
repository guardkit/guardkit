---
id: TASK-LCL-007
title: Evaluator SubAgent post-construction tool-inventory assertion
status: completed
created: 2026-04-18T00:00:00Z
updated: 2026-04-18T00:00:00Z
completed: 2026-04-18T00:00:00Z
completed_location: tasks/completed/TASK-LCL-007/
priority: high
tags: [templates, langchain-deepagents-orchestrator, tool-separation, les1-port-parity]
parent_review: TASK-REV-LES1
feature_id: FEAT-LTL1
implementation_mode: task-work
wave: 2
conductor_workspace: langchain-template-lessons-wave2-4
complexity: 5
---

# Task: Evaluator SubAgent post-construction tool-inventory assertion

## Description

The orchestrator template declares the Evaluator SubAgent with
`tools=[]` and a description that states "Has no tools — evaluation is
purely reasoning-based." DeepAgents' `SubAgentMiddleware` spawns child
agents that inherit the framework's middleware-tool injection; the
`tools=[]` parameter only controls *user*-provided tools. Middleware tools
(`write_file`, `edit_file`, `execute`, `write_todos`) are still injected.
This is the **same** F2 bug class that TASK-REV-32D2 identified on
`create_deep_agent(tools=[])` in the adversarial-cooperation templates.

Add a factory-level assertion that the Evaluator subagent, as actually
produced by the framework, has zero tools. Fail loud at construction — not
at runtime.

## Evidence

`langchain-deepagents-orchestrator/templates/other/agents/agents.py.template:67-98` —
`evaluator_subagent()` returns a `SubAgent` TypedDict. `create_orchestrator()`
lines 171-175 passes this spec into `create_deep_agent(subagents=[...])`.
No post-construction check anywhere.

## Acceptance Criteria

- [ ] After the orchestrator is compiled, assert the Evaluator's realised tool inventory is exactly `set()`.
- [ ] Assertion lives in `create_orchestrator()` or a new `_validate_subagent_tools()` helper invoked from there.
- [ ] Implementation uses either (a) an `assert_tool_inventory()` helper ported from base `lib/factory_guards.py` (preferred — single source of truth), or (b) a new orchestrator-template-local helper if cross-template vendoring is too heavy.
- [ ] If using option (a), vendor `factory_guards.assert_tool_inventory` + `ToolLeakageError` into `langchain-deepagents-orchestrator/templates/other/lib/factory_guards.py.template` — **must not** depend on `langchain-deepagents` being installed (the orchestrator template is standalone).
- [ ] Implementer and Builder subagents also get inventory assertions (Implementer's allowlist = `{analyse_context, plan_pipeline, execute_command, verify_output}`; Builder is async-remote and skipped).
- [ ] Add a `patterns/tool-delegation.md` rule to the orchestrator template describing the contract (short — one page, can cross-reference the base template's version).
- [ ] Add a unit test that patches `create_deep_agent` to produce a mock Evaluator with an injected extra tool — the `create_orchestrator()` call MUST raise `ToolLeakageError` with a clear diff.

## Files

- `installer/core/templates/langchain-deepagents-orchestrator/templates/other/agents/agents.py.template`
- `installer/core/templates/langchain-deepagents-orchestrator/templates/other/lib/factory_guards.py.template` (new — option a)
- `installer/core/templates/langchain-deepagents-orchestrator/.claude/rules/patterns/tool-delegation.md` (new)
- Tests

## Implementation Notes

- Consider whether the orchestrator template should instead start to `extends: langchain-deepagents` to reuse its `lib/factory_guards.py` directly. That's a larger refactor — not in scope here. **This task vendors a minimal copy and flags a future-work followup.**
- The realised tool inventory on a SubAgent might not be directly accessible via `subagent.tools` — may need to introspect the compiled graph. Document the introspection approach found in the task.

## Interface Contract

The assertion raises `ToolLeakageError` (same type as base template) with a
`Tool inventory mismatch: unexpected=...; missing=...` message shape so
that downstream logging / alerting can parse it consistently across
templates.

## Links

- Review: [TASK-REV-LES1 report §HIGH-1](../../../.claude/reviews/TASK-REV-LES1-review-report.md)
- LES1 §2 PORT / §6 cross-surface parity audit
- Base `lib/factory_guards.py` for reference implementation
