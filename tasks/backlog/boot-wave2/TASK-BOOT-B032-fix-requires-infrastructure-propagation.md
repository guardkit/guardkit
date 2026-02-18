---
id: TASK-BOOT-B032
title: Fix requires_infrastructure propagation through orchestrate()
status: backlog
created: 2026-02-18T00:00:00Z
updated: 2026-02-18T00:00:00Z
priority: critical
tags: [autobuild, environment-bootstrap, propagation-fix, root-cause-fix]
task_type: feature
complexity: 3
parent_review: TASK-REV-C9E5
feature_id: FEAT-BOOT
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Fix requires_infrastructure propagation through orchestrate()

## Description

The `AutoBuildOrchestrator.orchestrate()` method does not accept `requires_infrastructure` as a parameter. It loads the value independently from task `.md` frontmatter, which lacks the field when invoked via `FeatureOrchestrator`. The caller (`FeatureOrchestrator._execute_task()`) has the correct value from the feature YAML but has no way to pass it through.

This propagation gap causes two failures:
1. **Docker lifecycle blocked**: `requires_infra=[]` at `coach_validator.py:1172` prevents container startup
2. **Conditional approval blocked**: `bool([])` at `coach_validator.py:623` short-circuits the 5-condition AND

See: `.claude/reviews/TASK-REV-C9E5-review-report.md` (Revision 3) — Finding 3 (F3) and Recommendation 1 (R1).

## Context

Evidence trace (verified line-by-line):
- `feature_orchestrator.py:1521-1526` — `orchestrate()` call, no `requires_infrastructure` argument
- `autobuild.py:676-683` — `orchestrate()` signature, no `requires_infrastructure` parameter
- `autobuild.py:738-750` — loads from task `.md` frontmatter (absent → None → [])
- `autobuild.py:3582-3586` — constructs task dict with `requires_infrastructure or []`
- `coach_validator.py:617-626` — `bool([])` is False, conditional approval blocked

## Risk Note

R1 unblocks the Docker lifecycle path, but this path has never been exercised in a real autobuild run (Finding 9). Fixing the propagation gap may surface new failures in Docker container startup, readiness checks, or environment variable propagation. This risk is mitigated by the conditional approval fallback: if Docker isn't available, the test is conditionally approved rather than stalling.

**R1 alone changes the outcome from "stall" to "conditional approval (test skip)" — not to "tests pass".** For actual test execution, R2 (TASK-BOOT-F632) is also required.

## Acceptance Criteria

- [ ] `orchestrate()` method accepts `requires_infrastructure: Optional[List[str]] = None` parameter
- [ ] Precedence logic: explicit parameter > frontmatter > empty list
- [ ] `FeatureOrchestrator._execute_task()` passes `requires_infrastructure` from `FeatureTask` model to `orchestrate()`
- [ ] `_invoke_coach_safely()` receives correct `requires_infrastructure` value in task dict
- [ ] Existing single-task mode (no feature orchestrator) still works via frontmatter fallback
- [ ] Unit tests verify propagation with and without explicit parameter
- [ ] Unit tests verify frontmatter fallback when parameter is None

## Implementation Notes

### orchestrate() signature change

```
BEFORE: orchestrate(task_id, requirements, acceptance_criteria, base_branch="main", task_file_path=None)
AFTER:  orchestrate(task_id, requirements, acceptance_criteria, base_branch="main", task_file_path=None, requires_infrastructure=None)
```

### Precedence logic inside orchestrate()

```python
# If caller provides requires_infrastructure, use it (feature YAML source)
if requires_infrastructure is not None:
    self._requires_infrastructure = requires_infrastructure
else:
    # Fallback to frontmatter (single-task mode)
    ri = frontmatter.get("requires_infrastructure")
    if isinstance(ri, list):
        self._requires_infrastructure = ri
    else:
        self._requires_infrastructure = []
```

### _execute_task() call site change

```python
# feature_orchestrator.py:1521
result = task_orchestrator.orchestrate(
    task_id=task.id,
    requirements=task_data["requirements"],
    acceptance_criteria=task_data["acceptance_criteria"],
    task_file_path=task_data.get("file_path"),
    requires_infrastructure=task.requires_infrastructure,  # NEW
)
```

## Files to Modify

| File | Changes |
|------|---------|
| `guardkit/orchestrator/autobuild.py` | Add `requires_infrastructure` param to `orchestrate()`, precedence logic |
| `guardkit/orchestrator/feature_orchestrator.py` | Pass `requires_infrastructure` in `_execute_task()` call |
| `tests/unit/test_requires_infra_propagation.py` | NEW: unit tests for propagation |

## Source Review

- Review report: `.claude/reviews/TASK-REV-C9E5-review-report.md` (Revision 3)
- Evidence: `docs/reviews/autobuild-fixes/db_failed_after_env_changes.md`
