---
id: TASK-FIX-f1a2
title: Fix Coach SDK model mismatch and add non-Anthropic base URL bypass
status: completed
task_type: implementation
created: 2026-02-23T00:00:00Z
updated: 2026-02-24T00:00:00Z
completed: 2026-02-24T00:00:00Z
priority: critical
tags: [autobuild, vllm, coach, sdk, model-name, gb10]
complexity: 2
parent_review: TASK-REV-ED10
feature_id: FEAT-7a2e
wave: 1
implementation_mode: task-work
dependencies: []
test_results:
  status: passed
  total_tests: 234
  passed: 234
  failed: 0
  coverage: null
---

# Task: Fix Coach SDK model mismatch and add non-Anthropic base URL bypass

## Problem Statement

The Coach Validator's `_run_tests_via_sdk()` hardcodes `model="claude-haiku-4-5-20251001"` in its
`ClaudeAgentOptions`. When running against a local vLLM server (via `ANTHROPIC_BASE_URL`), vLLM
only serves `claude-sonnet-4-6` and immediately rejects the request with `invalid_request`. This
causes the same error on every Coach turn, producing an `UNRECOVERABLE_STALL` that terminates the
autobuild run even when the Player's implementation is correct.

This is the root cause of the FEAT-EC3C stall on the GB10 machine (confirmed in TASK-REV-ED10).

The Player SDK path already uses the correct pattern: no explicit `model=` in `ClaudeAgentOptions`,
letting the bundled `claude` CLI default to `claude-sonnet-4-6`, which matches the vLLM alias. The
Coach must be updated to use the same pattern.

A belt-and-suspenders fix (R2) is also included: detect when `ANTHROPIC_BASE_URL` points to a
non-Anthropic server and bypass the SDK-based test path entirely, falling back to subprocess.

## Acceptance Criteria

- [ ] `ClaudeAgentOptions` in `_run_tests_via_sdk()` no longer specifies an explicit `model=`
      parameter (equivalent to the Player SDK path in `agent_invoker.py`)
- [ ] A `_is_custom_api_base()` helper (or equivalent inline check) is added to
      `run_independent_tests()` that returns `True` when `ANTHROPIC_BASE_URL` is set and does not
      contain `api.anthropic.com`
- [ ] `use_sdk` in `run_independent_tests()` is `False` when `_is_custom_api_base()` is `True`
- [ ] Existing unit tests for `coach_validator.py` pass
- [ ] When `ANTHROPIC_BASE_URL=http://localhost:8000`, `use_sdk` is `False` and subprocess path
      is used (verifiable via test or manual check)
- [ ] When `ANTHROPIC_BASE_URL` is unset, `use_sdk` remains `True` (default Anthropic API path
      unchanged)

## Implementation Notes

### R1: Remove `model=` from `ClaudeAgentOptions` (coach_validator.py line ~1046-1054)

Current code:
```python
options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=["Bash"],
    permission_mode="bypassPermissions",
    max_turns=1,
    model="claude-haiku-4-5-20251001",   # ← REMOVE THIS LINE
)
```

Updated code (no model= — same as Player path in agent_invoker.py):
```python
options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=["Bash"],
    permission_mode="bypassPermissions",
    max_turns=1,
    # No model= — delegate to bundled CLI default (currently claude-sonnet-4-6)
    # This matches the Player SDK path and works with both Anthropic API and vLLM
)
```

### R2: Detect non-Anthropic base URL (coach_validator.py — run_independent_tests)

Add a helper and update the `use_sdk` guard:

```python
def _is_custom_api_base(self) -> bool:
    """Return True when ANTHROPIC_BASE_URL points to a non-Anthropic endpoint (e.g. vLLM)."""
    import os
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    return bool(base_url) and "api.anthropic.com" not in base_url

# In run_independent_tests():
use_sdk = (
    self._coach_test_execution == "sdk"
    and not requires_infra
    and not self._is_custom_api_base()   # NEW: skip SDK for vLLM / custom endpoints
)
```

## Files to Modify

- `guardkit/orchestrator/quality_gates/coach_validator.py`
  - `_run_tests_via_sdk()` (~line 1046): remove `model=` parameter
  - `_is_custom_api_base()` (new helper method)
  - `run_independent_tests()` (~line 1163): update `use_sdk` condition

## Test Plan

- Verify unit tests in `tests/unit/` for `coach_validator.py` still pass
- Add/update test cases:
  - `ANTHROPIC_BASE_URL=http://localhost:8000` → `_is_custom_api_base()` returns `True`
  - `ANTHROPIC_BASE_URL=https://api.anthropic.com` → returns `False`
  - `ANTHROPIC_BASE_URL` unset → returns `False`
  - `use_sdk=False` when custom base URL set
