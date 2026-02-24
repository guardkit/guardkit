---
id: TASK-FIX-g7h8
title: Align AgentInvoker model fields and make Coach test model configurable
status: completed
task_type: implementation
created: 2026-02-23T00:00:00Z
updated: 2026-02-24T00:00:00Z
completed: 2026-02-24T00:00:00Z
priority: medium
tags: [autobuild, agent-invoker, coach, model-config, refactor]
complexity: 3
parent_review: TASK-REV-ED10
feature_id: FEAT-7a2e
wave: 2
implementation_mode: task-work
dependencies: [TASK-FIX-f1a2]
test_results:
  status: passed
  tests_total: 401
  tests_passed: 401
  tests_failed: 0
---

# Task: Align AgentInvoker model fields and make Coach test model configurable

## Problem Statement

`AgentInvoker.__init__` stores `player_model` and `coach_model` instance fields (both defaulting to
`"claude-sonnet-4-5-20250929"`), but neither is passed to `ClaudeAgentOptions` in the task-work
delegation path. These fields are vestigial and create false confidence that model selection is
centrally controlled — when in fact the Player uses the bundled CLI default and the Coach SDK test
path (before TASK-FIX-f1a2) used a hardcoded Haiku model.

Additionally, if the Coach SDK test model should differ from the Player model (e.g. for cost
reasons on the real Anthropic API), this should be configurable via an environment variable rather
than hardcoded.

## Acceptance Criteria

- [ ] `AgentInvoker.player_model` and `AgentInvoker.coach_model` are either:
  - (a) Removed with a clear comment that model selection is delegated to the CLI default, OR
  - (b) Wired through to `ClaudeAgentOptions` in all SDK invocation paths and documented
- [ ] Coach SDK test model is read from `GUARDKIT_COACH_TEST_MODEL` environment variable when set,
      otherwise left unspecified (inheriting CLI default), rather than hardcoded
- [ ] A docstring or inline comment explains the model selection strategy for both paths
- [ ] Existing unit tests pass
- [ ] No functional behaviour change when env var is unset

## Implementation Notes

### Option A (Recommended): Remove vestigial fields

```python
# agent_invoker.py — __init__
# REMOVED: self.player_model = ... and self.coach_model = ...
# Model selection is delegated to the bundled claude CLI default.
# The CLI default (currently claude-sonnet-4-6) must match the vLLM SERVED_MODEL_NAME.
# See docs/guides/simple-local-autobuild.md for configuration details.
```

### Optional: GUARDKIT_COACH_TEST_MODEL env var (coach_validator.py)

```python
import os

def _get_coach_test_model(self) -> Optional[str]:
    """Return the model for Coach SDK test invocations, or None to use CLI default."""
    return os.environ.get("GUARDKIT_COACH_TEST_MODEL") or None

# In _run_tests_via_sdk():
model = self._get_coach_test_model()
options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=["Bash"],
    permission_mode="bypassPermissions",
    max_turns=1,
    **({"model": model} if model else {}),
)
```

This allows operators to set `GUARDKIT_COACH_TEST_MODEL=claude-haiku-4-5-20251001` when using
the real Anthropic API (to reduce cost) while defaulting to the CLI default (which works with
vLLM) when the env var is not set.

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py`
  - `__init__()`: remove or document `player_model`/`coach_model` fields
- `guardkit/orchestrator/quality_gates/coach_validator.py`
  - `_run_tests_via_sdk()`: add optional env var support for model selection
  - New private method: `_get_coach_test_model()`

## Test Plan

- Unit test: `GUARDKIT_COACH_TEST_MODEL` set → model passed to `ClaudeAgentOptions`
- Unit test: `GUARDKIT_COACH_TEST_MODEL` unset → no `model=` in `ClaudeAgentOptions`
- Verify vestigial fields removed without breaking existing tests
