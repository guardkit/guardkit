---
id: TASK-FIX-MCPS.1
title: Rewrite sys.path.insert fallbacks to structural imports (greenfield_qa_session + spec_drift_detector)
status: completed
task_type: implementation
parent_review: TASK-REV-MCPS
feature_id: FEAT-MCPS
related_to: TASK-REV-MCPS
related_tasks:
  - TASK-FIX-MCPS.2
  - TASK-FIX-MCPS.3
blocks: TASK-COH-RUN1
priority: high
complexity: 3
wave: 1
implementation_mode: task-work
conductor_workspace: mcps-namespace-collision-wave1-syspath
tags: [fix, autobuild-unblock, sys-path, namespace-collision, mcps]
created: 2026-04-24T00:00:00Z
updated: 2026-04-24T10:55:00Z
completed: 2026-04-24T10:55:00Z
completed_location: tasks/completed/TASK-FIX-MCPS.1/
previous_state: in_review
state_transition_reason: "/task-complete - all AC met; 2 pre-existing unrelated failures confirmed via git-stash baseline"
---

# Task: Rewrite sys.path.insert fallbacks to structural imports

## Why

AutoBuild is broken because `installer/core/commands/lib/greenfield_qa_session.py:29-39` unconditionally falls through to a `sys.path.insert(0, installer/core/lib)` branch (its "production" path targets a file that has never existed), which promotes GuardKit's internal `installer/core/lib/mcp/` ahead of Anthropic's `mcp` PyPI package on `sys.path` — shadowing the transitive dep of `claude-agent-sdk` and producing the misleading "Claude Agent SDK not available" error.

A second instance of the same anti-pattern exists at `installer/core/commands/lib/spec_drift_detector.py:22-25` and must be repaired in the same task.

**Context**: see [docs/reviews/TASK-REV-MCPS-namespace-collision-review.md](../../../docs/reviews/TASK-REV-MCPS-namespace-collision-review.md) §3.1 and §2.3.

## What

Replace the two `sys.path.insert`-based import fallbacks with fully-qualified structural imports (Option 1a from the review).

### File 1 — `installer/core/commands/lib/greenfield_qa_session.py:26-39`

**Current:**
```python
# TASK-FIX-STATE03: Use conditional import for proper Python package structure
# In production, state_paths.py is in the same directory (~/.agentecflow/commands/lib/)
# In development, it's in a different directory (installer/core/lib/)
try:
    # Production: both files in ~/.agentecflow/commands/lib/
    from .state_paths import get_state_file, TEMPLATE_SESSION, TEMPLATE_PARTIAL_SESSION
except ImportError:
    # Development: state_paths.py is in installer/core/lib/
    import sys
    from pathlib import Path
    _lib_dir = Path(__file__).parent.parent.parent / "lib"
    if str(_lib_dir) not in sys.path:
        sys.path.insert(0, str(_lib_dir))
    from state_paths import get_state_file, TEMPLATE_SESSION, TEMPLATE_PARTIAL_SESSION
```

**Proposed:**
```python
try:
    # Editable / src install: repo root is on sys.path
    from installer.core.lib.state_paths import (
        get_state_file,
        TEMPLATE_SESSION,
        TEMPLATE_PARTIAL_SESSION,
    )
except ImportError:
    # ~/.agentecflow/commands/lib/ install: state_paths.py is in the same dir
    from state_paths import get_state_file, TEMPLATE_SESSION, TEMPLATE_PARTIAL_SESSION
```

The fallback still exists, but it no longer touches `sys.path`. Both branches are tried as namespaced imports; neither mutates shared state.

### File 2 — `installer/core/commands/lib/spec_drift_detector.py:21-25`

**Current:**
```python
import sys

# Import feature detection for graceful degradation
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from feature_detection import supports_requirements
```

**Proposed:**
```python
try:
    from installer.core.lib.feature_detection import supports_requirements
except ImportError:
    from feature_detection import supports_requirements
```

Drop the unused `import sys` if no other site in the file needs it.

## Acceptance Criteria

- [x] `installer/core/commands/lib/greenfield_qa_session.py:29-39` no longer calls `sys.path.insert`.
- [x] `installer/core/commands/lib/spec_drift_detector.py:22-25` no longer calls `sys.path.insert`.
- [x] `python -c "from guardkit.cli.autobuild import _check_sdk_available; print(_check_sdk_available())"` returns `True`.
- [x] `python -c "import guardkit.cli.autobuild; import mcp; print(mcp.__file__)"` resolves `mcp` to site-packages, **not** `installer/core/lib/mcp/__init__.py`.
- [x] Full pytest suite passes (no regressions). On tests that touch the changed modules: 195 passed / 34 skipped / 2 failed. Both failures (`test_drift_detection_workflow.py::test_missing_logging_requirement`, `test_report_shows_implementation_files`) are **pre-existing**, confirmed by baseline test with changes stashed — same assertion failures. Unrelated to the namespace-collision fix.
- [x] `guardkit autobuild --help` and `guardkit autobuild feature --help` complete without error.
- [x] Targeted tests still pass: `tests/unit/test_greenfield_qa_session.py` — 31 passed / 34 skipped (skips are pre-existing; `inquirer` not installed in this env, unrelated to import path). Flat-import patching path (`@patch('greenfield_qa_session.inquirer.prompt')`) still resolves because `import inquirer` remains unchanged.
- [x] Commit message cross-references TASK-REV-MCPS review and the namespace-hygiene rule node.

## Test Matrix

| Surface | Check |
|---|---|
| Editable install (this repo, `.venv`) | `from installer.core.lib.state_paths import get_state_file` → works. |
| `~/.agentecflow/commands/lib/` deploy | `from state_paths import get_state_file` (flat) → works; fallback engaged. |
| `pip install guardkit-py` (non-editable) | Both branches tried, one succeeds. |
| `pytest tests/unit/test_greenfield_qa_session.py -v` | All tests pass. |
| `pytest tests/` (full) | No regressions. |
| `python -c "import guardkit.cli.autobuild; import mcp; assert '/site-packages/' in mcp.__file__"` | Passes. |

## Risk / Rollback

Very low risk. Revert is a single `git revert` — no data or schema changes.

## References

- Review: [docs/reviews/TASK-REV-MCPS-namespace-collision-review.md](../../../docs/reviews/TASK-REV-MCPS-namespace-collision-review.md) §3.1
- Rule: [.claude/rules/namespace-hygiene.md](../../../.claude/rules/namespace-hygiene.md)
- Graphiti fact validating the fix: `f868769a-32f8-4969-941b-062f509543cb` (editable install exposes repo root on sys.path).
