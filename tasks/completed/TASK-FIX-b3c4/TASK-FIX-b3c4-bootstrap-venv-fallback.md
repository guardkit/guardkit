---
id: TASK-FIX-b3c4
title: Fix environment bootstrap PEP 668 failure with virtualenv fallback
status: completed
task_type: implementation
created: 2026-02-23T00:00:00Z
updated: 2026-02-24T00:00:00Z
completed: 2026-02-24T00:00:00Z
priority: high
tags: [autobuild, environment-bootstrap, pep668, venv, gb10]
complexity: 4
parent_review: TASK-REV-ED10
feature_id: FEAT-7a2e
wave: 1
implementation_mode: task-work
dependencies: []
completed_location: tasks/completed/TASK-FIX-b3c4/
test_results:
  status: passed
  total: 127
  passed: 127
  failed: 0
  new_tests: 21
---

# Task: Fix environment bootstrap PEP 668 failure with virtualenv fallback

## Problem Statement

`EnvironmentBootstrapper` generates pip install commands using `sys.executable` (which is
`/usr/bin/python3` on Debian/Ubuntu). Modern Debian/Ubuntu systems enforce PEP 668
("externally managed environment"), refusing pip installs into the system Python without
`--break-system-packages`. No virtualenv fallback exists.

In the GB10 autobuild run (FEAT-EC3C), all 6 bootstrap installs failed with exit code 1
and `externally-managed-environment` stderr. The bootstrap reported `0/6` successes.

While this was NOT the proximate cause of the FEAT-EC3C stall (that was the Coach SDK model
mismatch — see TASK-FIX-f1a2), it is a real failure that will block any test execution path
that relies on the bootstrapped packages being importable via the system Python.

## Acceptance Criteria

- [x] When a pip install fails with `externally-managed-environment` in stderr, the bootstrapper
      detects this and creates a project-local virtualenv at `.guardkit/venv/`
- [x] Failed installs are retried using the venv Python
- [x] The venv path is stored in the bootstrap state file so subsequent runs use it
- [x] The bootstrapper logs a clear message when falling back to venv (e.g.
      `"PEP 668: falling back to virtualenv at .guardkit/venv/"`)
- [x] On a system without PEP 668 restrictions, behaviour is unchanged
- [x] Existing unit tests pass
- [x] New test covers the PEP 668 detection + venv fallback path

## Implementation Notes

### PEP 668 detection

Inspect stderr of failed pip commands for the sentinel string:
```python
PEP668_SENTINEL = "externally-managed-environment"

def _is_pep668_error(self, stderr: str) -> bool:
    return PEP668_SENTINEL in stderr
```

### Venv fallback strategy

On first PEP 668 failure:
1. Create `.guardkit/venv/` using `python3 -m venv .guardkit/venv`
2. Update `self._venv_python` to `.guardkit/venv/bin/python`
3. Retry all failed installs using the venv Python
4. Store venv path in state file for subsequent runs

```python
def _create_venv(self, project_root: Path) -> Path:
    venv_path = project_root / ".guardkit" / "venv"
    subprocess.run(
        ["python3", "-m", "venv", str(venv_path)],
        check=True
    )
    return venv_path / "bin" / "python"
```

### State persistence

The `BootstrapResult` or equivalent state should track:
```python
venv_python: Optional[str] = None  # path to venv python if created
```

### Files to Modify

- `guardkit/orchestrator/environment_bootstrap.py`
  - `_python_dep_commands()`: accept optional venv_python override
  - `_run_single_command()` or `_run_install()`: detect PEP 668 and trigger venv creation
  - `BootstrapResult` (or state dataclass): add `venv_python` field
  - New private methods: `_is_pep668_error()`, `_create_venv()`

## Test Plan

- Unit test: `_is_pep668_error()` with PEP 668 stderr → `True`; other stderr → `False`
- Unit test: Mock pip failure with PEP 668 error → venv is created and install retried
- Unit test: State file includes `venv_python` after venv creation
- Unit test: Normal pip install (no PEP 668) → no venv created, behaviour unchanged
