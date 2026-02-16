---
id: TASK-ABF-002
title: Fix output override to merge instead of replace file lists
status: completed
created: 2026-02-16T00:00:00Z
updated: 2026-02-16T16:30:00Z
completed: 2026-02-16T16:30:00Z
completed_location: tasks/completed/TASK-ABF-002/
previous_state: in_review
state_transition_reason: "All quality gates passed - task completed"
priority: high
tags: [autobuild, bug-fix, data-quality, agent-invoker]
task_type: feature
complexity: 3
parent_review: TASK-REV-F3BE
feature_id: FEAT-ABF
wave: 1
implementation_mode: task-work
dependencies: []
test_results:
  status: passed
  tests_total: 381
  tests_passed: 381
  tests_failed: 0
  last_run: 2026-02-16T16:05:00Z
organized_files:
  - TASK-ABF-002-fix-output-override-merge.md
---

# Task: Fix output override to merge instead of replace file lists

## Description

Change the output override at `agent_invoker.py:1568-1575` from replacing `files_created`/`files_modified` to merging (union) with existing git-enriched values. Currently, when the Player's SDK output contains `files_created` or `files_modified`, it completely overwrites the git-enriched lists, losing any files detected by `_detect_git_changes`.

## Context

From review TASK-REV-F3BE (Finding 1, additional complication): After `_detect_git_changes` enriches the player report with git-detected files (line 1517-1558), the code at lines 1568-1575 checks if the Player's `task_work_result.output` also has file lists and replaces the enriched data. This contradicts the TASK-FIX-PIPELINE intent documented at line 1517-1518 which explicitly states the goal is to "capture changes even if task_work_results.json has empty arrays."

## Acceptance Criteria

- [x] `files_created` from SDK output is merged (union) with git-enriched `files_created`
- [x] `files_modified` from SDK output is merged (union) with git-enriched `files_modified`
- [x] Result lists are sorted and deduplicated
- [x] When SDK output has no file lists, git-enriched data is preserved (existing behavior)
- [x] When git enrichment has no data, SDK output files are used (existing behavior)
- [x] New unit test: git-enriched files survive SDK output override
- [x] New unit test: SDK output files are included alongside git-enriched files
- [x] Existing tests pass without modification

## Key Files

- `guardkit/orchestrator/agent_invoker.py` (lines 1568-1575) - The fix location
- `guardkit/orchestrator/agent_invoker.py` (lines 1517-1558) - Git enrichment context

## Implementation Guidance

```python
# Current code (agent_invoker.py ~line 1572):
if "files_modified" in output:
    report["files_modified"] = output["files_modified"]
if "files_created" in output:
    report["files_created"] = output["files_created"]

# Fixed code:
if "files_modified" in output:
    existing = set(report.get("files_modified", []))
    report["files_modified"] = sorted(list(existing | set(output["files_modified"])))
if "files_created" in output:
    existing = set(report.get("files_created", []))
    report["files_created"] = sorted(list(existing | set(output["files_created"])))
```

## Test Execution Log
[Automatically populated by /task-work]
