# DEC — Vendor `factory_guards.py` into the orchestrator template rather than import from base

**Status:** ACCEPTED (implemented) · **Date:** 2026-04-18 · **Task:** TASK-LCL-007 · **Commit:** `dbc47bc51`

## Context

TASK-LCL-007 (feature FEAT-LTL1, "langchain-template-lessons", Wave 2) added a
post-construction tool-inventory assertion for the orchestrator template's
Evaluator SubAgent. The Evaluator is declared with `tools=[]` and a description
stating "evaluation is purely reasoning-based", but DeepAgents'
`SubAgentMiddleware` compiles subagents into sub-graphs that inherit the
framework's middleware-tool injection (`write_file`, `edit_file`, `execute`,
`write_todos`). The `tools=[]` spec parameter only controls *user*-provided
tools, so those middleware tools can still leak in. This is the same
TASK-REV-32D2 F2 bug class the base `langchain-deepagents` template already
guards against with `assert_tool_inventory()` + `ToolLeakageError` in
`lib/factory_guards.py`.

The base template's guard was the obvious source of that assertion, but the
orchestrator template is standalone — it does **not** declare
`extends: langchain-deepagents` overlay inheritance — so it cannot import from
the base template's `lib/`. The decision was whether to make the orchestrator
template depend on the base template being installed, or to duplicate the guard.

## Decision

Vendor a standalone, stdlib-only copy of the guard surface (`ToolLeakageError`
+ `assert_tool_inventory`) into
`installer/core/templates/langchain-deepagents-orchestrator/templates/other/lib/factory_guards.py.template`,
rather than importing it from the base `langchain-deepagents` template. The
vendored copy must keep the error type name (`ToolLeakageError`) and the message
shape (`"Tool inventory mismatch: unexpected=...; missing=..."`) in sync with
the base template so downstream logging/alerting can parse leakage reports
consistently across template families.

## Rationale

- **Independent renderability.** The orchestrator template is standalone; a
  consumer should not be forced to install the base `langchain-deepagents`
  template just to get the orchestrator's tool-leakage guard. Vendoring keeps
  the two templates independently renderable.
- **Stdlib-only, low cost.** The guard is a single exception class and one pure
  function — no third-party dependency, cheap to duplicate.
- **Deferred the larger refactor.** Switching the orchestrator template to
  `extends: langchain-deepagents` (which would restore a single source of truth)
  is a much bigger change and was explicitly out of scope for TASK-LCL-007.

**Trade-off:** two copies of `ToolLeakageError` now exist and must stay in sync
on the error-message shape. This is flagged in the vendored file's module
docstring and in the orchestrator template's `patterns/tool-delegation.md`.

## Consequences / Implementation

- Vendored guard:
  `installer/core/templates/langchain-deepagents-orchestrator/templates/other/lib/factory_guards.py.template`
  — `ToolLeakageError` (class) and `assert_tool_inventory()`; docstring records
  it is vendored from the base template and names the future-work delete path.
- Base source of truth:
  `installer/core/templates/langchain-deepagents/lib/factory_guards.py`
  (`ToolLeakageError`, `assert_tool_inventory`).
- Realised-inventory enforcement lives in the orchestrator's factory:
  `templates/other/agents/agents.py.template` imports the vendored guard
  (`from lib.factory_guards import ToolLeakageError, assert_tool_inventory`) and
  `create_orchestrator()` calls `_validate_subagent_tools(graph, "implementer",
  IMPLEMENTER_ALLOWED_TOOLS)` and `_validate_subagent_tools(graph, "evaluator",
  EVALUATOR_ALLOWED_TOOLS)` (with `EVALUATOR_ALLOWED_TOOLS = set()`) at factory
  exit, failing loud at construction. The Builder subagent is async-remote and
  skipped.
- Contract documented in
  `installer/core/templates/langchain-deepagents-orchestrator/.claude/rules/patterns/tool-delegation.md`,
  which records the vendoring decision and its future-work reversal condition.

**Future work:** if the orchestrator template is ever refactored to adopt
`extends: langchain-deepagents`, delete the vendored copy and import from the
base template's `lib/factory_guards.py` — do not carry two diverging copies.

## References

- Task: `tasks/completed/TASK-LCL-007/TASK-LCL-007.md`
- Commit: `dbc47bc51` ("Apply lessons learned from the specialist agent to the templates", 2026-04-18)
- Vendored guard: `installer/core/templates/langchain-deepagents-orchestrator/templates/other/lib/factory_guards.py.template`
- Base guard (source of truth): `installer/core/templates/langchain-deepagents/lib/factory_guards.py`
- Factory enforcement: `installer/core/templates/langchain-deepagents-orchestrator/templates/other/agents/agents.py.template`
- Pattern rule: `installer/core/templates/langchain-deepagents-orchestrator/.claude/rules/patterns/tool-delegation.md`
- Review origin: `TASK-REV-LES1` §HIGH-1; TASK-REV-32D2 F2 bug class
