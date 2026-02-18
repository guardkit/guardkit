---
id: TASK-BOOT-0F53
title: State-aware hash persistence with outcome tracking
status: backlog
created: 2026-02-18T00:00:00Z
updated: 2026-02-18T00:00:00Z
priority: medium
tags: [autobuild, environment-bootstrap, cache, idempotency]
task_type: feature
complexity: 3
parent_review: TASK-REV-C9E5
feature_id: FEAT-BOOT
wave: 2
implementation_mode: task-work
dependencies: []
---

# Task: State-aware hash persistence with outcome tracking

## Description

The bootstrap state file at `.guardkit/bootstrap_state.json` only stores `{"content_hash": "<hex>"}` with no record of success or failure. When the content hash matches on a subsequent invocation:
- If the previous install succeeded, skip is correct
- If the previous install failed, skip is WRONG (it caches the failure)

Simply not persisting on failure would cause infinite retries when manifest content is static (e.g., manifest was correct from the start, only the source tree was incomplete).

See: `.claude/reviews/TASK-REV-C9E5-review-report.md` (Revision 3) — Recommendation 3 (R3).

## Context

Current state at `environment_bootstrap.py:503`:
```python
# Persist new state hash (even on partial failure)
self._save_state(content_hash)
```

Current state file format:
```json
{"content_hash": "<hex>"}
```

In the FEAT-BA28 case, this is moot because Wave 1 modifies `pyproject.toml` (changing the hash), so inter-wave bootstrap retries. But in scenarios where the manifest is pre-existing and correct (only the source tree is incomplete), the failed state would be cached and retries suppressed.

## Acceptance Criteria

- [ ] State file stores outcome alongside hash: `{"content_hash": "<hex>", "success": true/false, "timestamp": "<iso>"}`
- [ ] Retry logic: retry when content hash differs OR previous attempt failed with time-based cooldown
- [ ] Time-based retry for failed attempts: retry if more than N seconds since last failed attempt (N configurable, default 60s)
- [ ] Successful installs still cached normally (skip on same hash)
- [ ] Unit tests for all retry scenarios: hash change, success cache, failure retry, cooldown
- [ ] Backward compatible: gracefully handles old format `{"content_hash": "<hex>"}` (treats as success for migration)

## Implementation Notes

### State file format change

```json
{
    "content_hash": "<hex>",
    "success": false,
    "timestamp": "2026-02-18T12:34:56Z"
}
```

### Retry logic

```python
def _should_skip(self, content_hash: str) -> bool:
    saved = self._load_state()
    if not saved:
        return False  # No state, run install

    if saved.get("content_hash") != content_hash:
        return False  # Content changed, run install

    if saved.get("success", True):  # Default True for backward compat
        return True   # Previous success with same hash, skip

    # Previous failure with same hash — retry after cooldown
    last_attempt = saved.get("timestamp")
    if last_attempt:
        elapsed = (datetime.now() - datetime.fromisoformat(last_attempt)).total_seconds()
        if elapsed < self._retry_cooldown_seconds:
            return True  # Within cooldown, skip
    return False  # Cooldown expired, retry
```

### Save logic

```python
def _save_state(self, content_hash: str, success: bool) -> None:
    state = {
        "content_hash": content_hash,
        "success": success,
        "timestamp": datetime.now().isoformat(),
    }
    # ... write to file
```

### Design decision: time-based vs source_tree_hash

The review Revision 3 proposed `source_tree_hash` (SHA-256 of directory listing) as the retry trigger. Reviewer feedback preferred time-based retry as simpler to implement and debug. Time-based covers the case where waves create new directories without computing directory hashes. Either approach is valid at effort 3/10 — this task uses time-based.

## Files to Modify

| File | Changes |
|------|---------|
| `guardkit/orchestrator/environment_bootstrap.py` | `_save_state()` signature change, `_should_skip()` logic, `_retry_cooldown_seconds` config |
| `tests/unit/test_environment_bootstrap.py` | Add retry scenario tests |

## Source Review

- Review report: `.claude/reviews/TASK-REV-C9E5-review-report.md` (Revision 3)
- Evidence: `docs/reviews/autobuild-fixes/db_failed_after_env_changes.md`
