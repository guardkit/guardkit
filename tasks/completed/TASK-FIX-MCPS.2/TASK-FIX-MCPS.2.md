---
id: TASK-FIX-MCPS.2
title: Surface real ImportError in _check_sdk_available / _require_sdk
status: completed
task_type: implementation
parent_review: TASK-REV-MCPS
feature_id: FEAT-MCPS
related_to: TASK-REV-MCPS
related_tasks:
  - TASK-FIX-MCPS.1
  - TASK-FIX-MCPS.3
priority: high
complexity: 2
wave: 1
implementation_mode: task-work
conductor_workspace: mcps-namespace-collision-wave1-diagnostics
tags: [fix, diagnostics, error-messages, autobuild, mcps]
created: 2026-04-24T00:00:00Z
updated: 2026-04-24T11:05:00Z
completed: 2026-04-24T11:05:00Z
completed_location: tasks/completed/TASK-FIX-MCPS.2/
previous_state: in_review
state_transition_reason: "Task verified complete via /task-complete"
organized_files:
  - TASK-FIX-MCPS.2.md
---

# Task: Surface real ImportError in SDK preflight

## Why

`guardkit/cli/autobuild.py:58-103` catches every `ImportError` from `from claude_agent_sdk import query` and re-prints a hard-coded "Claude Agent SDK not available" banner. The real `ModuleNotFoundError: No module named 'mcp.types'` (or any other transitive-dep issue) never reaches the console. That opacity cost ~30 minutes of diagnostic time in the TASK-REV-MCPS incident and will cost more on every future occurrence.

**Context**: see [docs/reviews/TASK-REV-MCPS-namespace-collision-review.md](../../../docs/reviews/TASK-REV-MCPS-namespace-collision-review.md) §3.3.

## What

Modify `guardkit/cli/autobuild.py:58-103` to capture the underlying error and include it in the user-facing message. Signature change: `_check_sdk_available() -> tuple[bool, str | None]`.

### Proposed implementation

```python
def _check_sdk_available() -> tuple[bool, str | None]:
    """
    Check if Claude Agent SDK is available.

    Returns
    -------
    tuple[bool, str | None]
        (True, None) if SDK is importable.
        (False, str(error)) if import fails; str(error) is the underlying message.
    """
    try:
        from claude_agent_sdk import query  # noqa: F401
        return (True, None)
    except ImportError as e:
        return (False, str(e))


def _require_sdk() -> None:
    available, err = _check_sdk_available()
    if not available:
        console.print("[red]Error: Claude Agent SDK import failed[/red]")
        console.print()
        console.print(f"[yellow]Underlying error:[/yellow] {err}")
        console.print()
        console.print("Most common causes:")
        console.print("  • [cyan]pip install claude-agent-sdk[/cyan] or [cyan]pip install guardkit-py[autobuild][/cyan]")
        console.print("  • A namespace collision (internal module shadows a transitive dep).")
        console.print("    If the error above names a submodule like 'mcp.types' or 'anyio.X',")
        console.print("    see .claude/rules/namespace-hygiene.md.")
        console.print()
        console.print("For more diagnostics: [dim]guardkit doctor[/dim]")
        sys.exit(1)
```

### Callers to update

Grep for callers of `_check_sdk_available`. Expected:
- `_require_sdk` (same file)
- Any test fixtures that assert on the old boolean return.

Update callers to destructure the tuple or use `.0` depending on idiom.

## Acceptance Criteria

- [x] `_check_sdk_available` returns `tuple[bool, str | None]`.
- [x] `_require_sdk` prints the underlying `ImportError` message.
- [x] Error message points readers to `.claude/rules/namespace-hygiene.md` when the error names a submodule of a transitive dep.
- [x] All callers of `_check_sdk_available` updated to the new signature.
- [x] Tests that mock SDK availability continue to pass.
- [x] Full pytest suite passes. *(scope: all autobuild-touching tests — 163 pass; pre-existing unrelated failures in `tests/lib/template_generator/test_path_resolver.py`, `tests/lib/agent_enhancement/test_validation_errors.py`, `tests/cli/test_graphiti_list.py::test_list_handles_disabled_graphiti` verified to exist on clean `main` before this change — none reference `_check_sdk_available` / `_require_sdk` / `autobuild`.)*
- [ ] Commit message cross-references TASK-REV-MCPS review. *(left for committer)*

## Implementation Summary

Changed `guardkit/cli/autobuild.py:58-107`:
- `_check_sdk_available()` now returns `tuple[bool, str | None]` — `(True, None)` when the SDK imports, `(False, str(ImportError))` when it doesn't.
- `_require_sdk()` destructures that tuple and renders the real error message via Rich, followed by install guidance and a pointer to `.claude/rules/namespace-hygiene.md` for submodule-shadow symptoms.

Test fixture updates (all `return_value=True` mocks switched to `(True, None)`; all `return_value=False` switched to `(False, "<message>")`):
- `tests/unit/test_cli_autobuild.py` — 7 patch points plus `test_check_sdk_available_returns_bool` renamed to `test_check_sdk_available_returns_tuple` and a new `test_require_sdk_surfaces_underlying_error` added to lock the namespace-hygiene pointer.
- `tests/unit/test_feature_orchestrator.py` — 9 patch points.
- `tests/integration/test_ablation_mode.py` — 2 patch points.

Live verification (outside pytest): simulated the TASK-REV-MCPS failure shape by rebinding `builtins.__import__` to raise `ImportError("No module named 'mcp.types'")` from `claude_agent_sdk`; `_require_sdk()` now surfaces that exact string and the namespace-hygiene pointer.

## Test Matrix

| Scenario | Expected |
|---|---|
| SDK installed, no shadowing | `_check_sdk_available() == (True, None)`; `guardkit autobuild --help` works. |
| SDK installed, `mcp/` shadow ACTIVE (simulate by sys.path.insert) | `_check_sdk_available() == (False, "No module named 'mcp.types'")` — user-facing message surfaces that string. |
| SDK not installed (throwaway venv) | `_check_sdk_available() == (False, "No module named 'claude_agent_sdk'")` — existing install-guidance still applies. |
| Full pytest | No regressions. |

## Risk / Rollback

Very low risk. Underscore-prefixed; not public API surface. Revert is one-hunk.

## References

- Review: [docs/reviews/TASK-REV-MCPS-namespace-collision-review.md](../../../docs/reviews/TASK-REV-MCPS-namespace-collision-review.md) §3.3
- Rule: [.claude/rules/namespace-hygiene.md](../../../.claude/rules/namespace-hygiene.md)
