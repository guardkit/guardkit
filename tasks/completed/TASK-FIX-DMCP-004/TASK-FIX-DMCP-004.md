---
id: TASK-FIX-DMCP-004
title: Fix synthetic report acceptance criteria loading
status: completed
task_type: feature
created: 2026-02-24T16:00:00Z
updated: 2026-02-24T20:00:00Z
completed: 2026-02-24T20:05:00Z
priority: high
tags: [autobuild, bug-fix, direct-mode, synthetic-report]
complexity: 2
parent_review: TASK-REV-CECA
feature_id: FEAT-DMCP
wave: 2
implementation_mode: direct
dependencies: [TASK-FIX-DMCP-003]
---

# Task: Fix synthetic report acceptance criteria loading

## Description

When creating synthetic reports for direct mode, `_create_synthetic_direct_mode_report` loads acceptance criteria from the task file's YAML frontmatter via `_load_task_metadata()`. However, acceptance criteria are stored in the markdown body (parsed by `spec_parser.py`), not in the YAML frontmatter. This means `acceptance_criteria = None`, and no file-existence promises are generated.

## Root Cause

At `agent_invoker.py:2662-2670`:

```python
metadata = self._load_task_metadata(task_file)  # YAML frontmatter ONLY
acceptance_criteria = metadata.get("acceptance_criteria")  # Returns None!
task_type_meta = metadata.get("task_type")
```

`_load_task_metadata` at line 1926-1948 only parses between `---` markers (YAML frontmatter).

The autobuild orchestrator correctly uses `TaskLoader.load_task()` which parses the full task spec including markdown body sections, but the agent_invoker uses the simpler YAML-only parser.

## Fix

Replace the metadata loading at `agent_invoker.py:2662-2670` with the full spec parser:

```python
try:
    from guardkit.planning.spec_parser import parse_task_spec
    task_content = task_file.read_text()
    task_spec = parse_task_spec(task_content)
    acceptance_criteria = task_spec.acceptance_criteria if task_spec else None
    # task_type still comes from frontmatter
    metadata = self._load_task_metadata(task_file)
    task_type_meta = metadata.get("task_type")
except Exception as e:
    logger.debug(f"Failed to parse task spec for synthetic promises: {e}")
    acceptance_criteria = None
    task_type_meta = None
```

Alternative: Use `TaskLoader.load_task()` if it provides both acceptance_criteria and frontmatter.

## Acceptance Criteria

1. Synthetic report generation can load acceptance criteria from task markdown body
2. File-existence promises are generated for scaffolding tasks with acceptance criteria
3. Graceful fallback if spec parsing fails (no crash, no promises generated)
4. Existing tests still pass
5. `task_type` still read from YAML frontmatter (not affected by this change)

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py` — synthetic report creation block (~line 2662-2670)

## Files NOT to Touch

- `guardkit/orchestrator/synthetic_report.py` — works correctly, no change needed
- `guardkit/planning/spec_parser.py` — works correctly, just needs to be called
