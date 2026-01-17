---
id: TASK-REV-66B4
title: Analyze /feature-build CLI errors and schema gaps
status: review_complete
task_type: review
review_mode: code-quality
review_depth: standard
created: 2025-01-06T08:00:00Z
updated: 2025-01-06T09:00:00Z
priority: high
tags: [feature-build, cli, schema, debugging]
complexity: 6
decision_required: true
review_results:
  mode: code-quality
  depth: standard
  score: 45
  findings_count: 4
  recommendations_count: 5
  decision: implement
  report_path: .claude/reviews/TASK-REV-66B4-review-report.md
  completed_at: 2026-01-06T09:00:00Z
  implementation_feature: feature-plan-schema-fix
  implementation_tasks:
    - TASK-FP-001
    - TASK-FP-002
    - TASK-FP-003
    - TASK-FP-004
    - TASK-FP-005
---

# Task: Analyze /feature-build CLI errors and schema gaps

## Description

Review the errors encountered when running `/feature-build FEAT-1682` to identify gaps between the feature YAML schema expected by the CLI and what `/feature-plan` generates. Multiple iterations were required to fix schema issues before the feature build could proceed.

## Source Evidence

The error log is captured in: `docs/reviews/feature-build/feature-build-output.md`

## Errors Identified

### Error 1: Missing `file_path` in task entries (Exit code 2)
**Location**: `guardkit/orchestrator/feature_loader.py:374`
```
KeyError: 'file_path'
```
**Root Cause**: The `_parse_task` method expects `file_path` as a required field in each task entry, but `/feature-plan` generates a separate `task_files` section instead of embedding `file_path` directly in each task.

### Error 2: Missing `status` field in task entries (Implicit)
The fix also required adding `status: pending` to each task entry.

### Error 3: Tasks not in orchestration (Exit code 3)
```
Feature validation failed for FEAT-1682:
  - Tasks not in orchestration: TASK-INFRA-005, TASK-INFRA-001, ...
```
**Root Cause**: The validator expects `orchestration.parallel_groups` but `/feature-plan` generates `execution_groups` with a different structure.

### Error 4: Invalid git reference (Exit code 2)
```
fatal: invalid reference: main
```
**Root Cause**: Worktree creation assumed `main` branch exists but repository had no commits yet. This is an edge case for fresh repositories.

## Schema Mismatch Analysis

### What `/feature-plan` generates:
```yaml
tasks:
  - id: TASK-XXX
    name: "Task Name"
    wave: 1
    dependencies: []
    implementation_mode: task-work
    testing_mode: tdd

task_files:
  - path: "tasks/backlog/.../TASK-XXX.md"

execution_groups:
  - wave: 1
    name: "Foundation"
    strategy: sequential
    tasks:
      - TASK-XXX
```

### What FeatureLoader expects:
```yaml
tasks:
  - id: TASK-XXX
    name: "Task Name"
    wave: 1
    dependencies: []
    implementation_mode: task-work
    testing_mode: tdd
    status: pending                    # Required
    file_path: "tasks/backlog/.../..."  # Required

orchestration:
  parallel_groups:
    - - TASK-XXX        # Wave 1 (list of lists)
    - - TASK-YYY
      - TASK-ZZZ        # Wave 2 parallel
```

## Files to Review

1. `guardkit/orchestrator/feature_loader.py` - FeatureLoader._parse_task() and validation logic
2. `installer/core/commands/feature-plan.md` - Feature YAML generation spec
3. `.claude/agents/autobuild-player.md` - May generate feature files
4. `guardkit/orchestrator/feature_orchestrator.py` - Validation requirements

## Questions to Answer

1. Should `/feature-plan` be updated to match CLI expectations?
2. Should FeatureLoader be made more flexible to accept both schemas?
3. Is the `task_files` section redundant if `file_path` is embedded in tasks?
4. How should fresh repositories (no commits) be handled?

## Acceptance Criteria

- [x] Root causes documented for all 4 error types
- [x] Schema gap analysis complete (generate vs. consume)
- [x] Recommended fix approach identified
- [x] Implementation tasks created if [I]mplement chosen

## Review Mode

Suggested: `--mode=code-quality --depth=standard`

## Related Files

- [docs/reviews/feature-build/feature-build-output.md](docs/reviews/feature-build/feature-build-output.md)
- [guardkit/orchestrator/feature_loader.py](guardkit/orchestrator/feature_loader.py)
- [installer/core/commands/feature-plan.md](installer/core/commands/feature-plan.md)
