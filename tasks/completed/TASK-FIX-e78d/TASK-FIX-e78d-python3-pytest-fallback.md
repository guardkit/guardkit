---
id: TASK-FIX-e78d
title: Fix python3 fallback in coach_verification test detection
status: completed
task_type: feature
created: 2026-02-23T00:00:00Z
updated: 2026-02-23T00:00:00Z
completed: 2026-02-23T00:00:00Z
priority: medium
tags: [bug, autobuild, test-detection, ubuntu, python3]
complexity: 2
parent_review: TASK-REV-GB10
feature_id: FEAT-GB10-fixes
completed_location: tasks/completed/TASK-FIX-e78d/
---

# Task: Fix python3 fallback in coach_verification test detection

## Description

The test detection fallback in `coach_verification.py` hardcodes `"python"` as the Python
interpreter command. On Ubuntu/Debian (and the GB10 ProMax), `python` is not in PATH by
default — only `python3`. This causes the pytest fallback to fail with `FileNotFoundError`,
reporting `0 tests, failed` even when test files exist and `python3 -m pytest` would succeed.

**Affected path** (`coach_verification.py:276–288`):
```python
except FileNotFoundError:
    logger.warning("pytest not found, trying python -m pytest")
    try:
        fallback_cmd = ["python", "-m", "pytest", ...]  # ← "python" fails on Ubuntu
```

## Acceptance Criteria

- [x] `coach_verification.py` fallback uses `"python3"` first, then `"python"` as a
      secondary fallback so it works on both Ubuntu (python3 only) and other systems
- [x] A `FileNotFoundError` from the `python3` fallback is caught and falls through to
      `"python"` before giving up
- [x] Existing tests pass unchanged

## Implementation Notes

Change the fallback from a single attempt to a loop over candidates:

```python
except FileNotFoundError:
    logger.warning("pytest not found, trying python -m pytest")
    test_result = None
    for python_cmd in ["python3", "python"]:
        try:
            fallback_cmd = [python_cmd, "-m", "pytest", "--tb=no", "-q"]
            if test_paths:
                fallback_cmd.extend(test_paths)
            result = subprocess.run(
                fallback_cmd,
                cwd=self.worktree_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
            test_result = TestResult(
                passed=result.returncode == 0,
                test_count=self._parse_pytest_count(result.stdout),
                output=result.stdout,
            )
            break
        except FileNotFoundError:
            continue
    if test_result is None:
        logger.error("Failed to run tests: neither python3 nor python found")
        test_result = TestResult(passed=False, test_count=0, output="")
```

## Files Changed

- `guardkit/orchestrator/coach_verification.py` — fallback loop at lines 276–301

## Related

- Review: `TASK-REV-GB10`
- Source: `docs/reviews/gb10_local_autobuild/api_feature_1.md` lines 104–106
- Symptom: `0 tests, failed` on GB10 despite scaffold files being created
