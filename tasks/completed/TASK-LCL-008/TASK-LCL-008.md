---
id: TASK-LCL-008
title: Extract session_logging + retry_context helpers into base lib/
status: completed
created: 2026-04-18T00:00:00Z
updated: 2026-04-18T00:00:00Z
completed: 2026-04-18T00:00:00Z
completed_location: tasks/completed/TASK-LCL-008/
priority: high
tags: [templates, langchain-deepagents, shared-infra, les1-ac-discipline]
parent_review: TASK-REV-LES1
feature_id: FEAT-LTL1
implementation_mode: task-work
wave: 3
conductor_workspace: langchain-template-lessons-wave3-1
complexity: 6
---

# Task: Extract session_logging + retry_context helpers into base lib/

## Description

The weighted-evaluation template's `scaffold/orchestrator.py.j2` hosts three
post-specialist-agent hardening helpers that landed in commit `dfa8090d`
but live only in that one template:

- `_write_session_log()` — unconditional diagnostic logging (prevents Category A bugs)
- `_build_context_manifest()` — retry input preservation (prevents Category C bugs)
- `_configure_logging(force=True)` — logger-handler-conflict fix (Category A)

The orchestrator template has **none** of these. Any future
langchain-deepagents-derivative template will reinvent them.

Promote these helpers into base `lib/` so weighted-eval can import them
(via `extends` overlay) and orchestrator can vendor a copy.

## Evidence

- Helpers currently at `installer/core/templates/langchain-deepagents-weighted-evaluation/scaffold/orchestrator.py.j2:425-568`.
- Not present in `langchain-deepagents/lib/` or `langchain-deepagents-orchestrator/templates/`.

## Acceptance Criteria

- [x] New `installer/core/templates/langchain-deepagents/lib/session_logging.py` exporting `write_session_log(target_id, result, log_dir="session-logs")`. Accepts any object with `success`, `attempts`, `error`, and optional `verdict` — work from a Protocol (or duck-typed) contract, not a concrete `PipelineResult` import (so the base can ship it without depending on weighted-eval types).
- [x] New `installer/core/templates/langchain-deepagents/lib/retry_context.py` exporting `build_context_manifest(target, context)` and `build_retry_input(player_content, issues, context_manifest=None)`.
- [x] `lib/__init__.py` re-exports the public API for both modules.
- [x] Weighted-eval `scaffold/orchestrator.py.j2` is refactored to import from `lib/session_logging.py` and `lib/retry_context.py` instead of defining them inline. Behaviour preserved — all existing `test_orchestrator.py` / `test_scaffold.py` cases pass unchanged (144 tests ✓).
- [x] Orchestrator template vendors these two files (copy into `langchain-deepagents-orchestrator/templates/other/lib/`) — since the orchestrator template does not `extends` the base, vendoring is the only option. Mark vendored files with a clear header comment citing the base as source-of-truth.
- [x] Tests ported from weighted-eval's existing tests for these helpers into `tests/templates/langchain-deepagents/` (existing base-template test layout). 37 tests ✓.
- [x] `_configure_logging(force=True)` exposed as `configure_logging(debug=False, verbose=False)` in `lib/__init__.py` as well.
- [x] A short pattern rule `patterns/session-logs-and-retry-context.md` in the base, describing when to call each helper.

## Files

**Base (new):**
- `installer/core/templates/langchain-deepagents/lib/session_logging.py`
- `installer/core/templates/langchain-deepagents/lib/retry_context.py`
- `installer/core/templates/langchain-deepagents/lib/__init__.py` (edit — add exports)
- `installer/core/templates/langchain-deepagents/.claude/rules/patterns/session-logs-and-retry-context.md` (new)

**Weighted-eval (edit):**
- `installer/core/templates/langchain-deepagents-weighted-evaluation/scaffold/orchestrator.py.j2`

**Orchestrator (new — vendor):**
- `installer/core/templates/langchain-deepagents-orchestrator/templates/other/lib/session_logging.py.template`
- `installer/core/templates/langchain-deepagents-orchestrator/templates/other/lib/retry_context.py.template`

**Tests:**
- Base lib tests (pattern matches existing base test layout)

## Interface Contract

Public API (all three modules):

```python
# lib/session_logging.py
def write_session_log(
    target_id: str,
    result: Any,  # duck-typed: needs .success, .attempts, .error, optional .verdict
    log_dir: str | pathlib.Path = "session-logs",
) -> pathlib.Path | None: ...

# lib/retry_context.py
def build_context_manifest(target: dict[str, Any], context: str) -> str: ...
def build_retry_input(
    player_content: str,
    issues: list[str],
    *,
    context_manifest: str | None = None,
) -> dict: ...

# lib/__init__.py (new exports)
from .session_logging import write_session_log
from .retry_context import build_context_manifest, build_retry_input
```

Downstream consumers (weighted-eval + orch) import from these paths. Any
signature change requires updating both consumers.

## Dependencies

Independent of Wave 2 tasks — different files. Can run in parallel with
LCL-004..LCL-007.

## Links

- Review: [TASK-REV-LES1 report §HIGH-4, §"Shared-Infrastructure Work" #3](../../../.claude/reviews/TASK-REV-LES1-review-report.md)
- Weighted-eval `scaffold/orchestrator.py.j2:425-568` for source material
