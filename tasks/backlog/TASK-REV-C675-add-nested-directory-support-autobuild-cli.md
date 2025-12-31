---
id: TASK-REV-C675
title: Add nested task directory support to AutoBuild CLI
status: review_complete
task_type: review
created: 2025-12-31T11:00:00Z
updated: 2025-12-31T12:00:00Z
priority: high
tags: [autobuild, cli, feature-plan, nested-directories]
complexity: 6
review_mode: architectural
review_depth: standard
review_results:
  mode: architectural
  depth: standard
  score: 72
  findings_count: 5
  recommendations_count: 4
  decision: implement
  report_path: .claude/reviews/TASK-REV-C675-review-report.md
  completed_at: 2025-12-31T12:00:00Z
  implementation_feature: nested-directory-support
  implementation_tasks:
    - TASK-NDS-001
    - TASK-NDS-002
    - TASK-NDS-003
---

# Review: Add Nested Task Directory Support to AutoBuild CLI

## Problem Statement

The `/feature-plan` command creates tasks in nested feature subfolders:
```
tasks/backlog/application-infrastructure/
├── TASK-INFRA-001-project-structure-configuration.md
├── TASK-INFRA-002-database-infrastructure.md
└── ... (8 tasks total)
```

However, the AutoBuild CLI (`guardkit autobuild task TASK-XXX`) only searches the root of `tasks/backlog/`, `tasks/in_progress/`, etc. - it doesn't recursively search subdirectories.

This causes the CLI to fail to find tasks created by `/feature-plan`, forcing users to choose workarounds like:
- Moving task files to flat structure
- Using Task tool fallback
- Executing tasks directly without Player-Coach

## User Impact

When running `/feature-build FEAT-B3F8` or `guardkit autobuild task TASK-INFRA-001`:
- Tasks in `tasks/backlog/application-infrastructure/` are not found
- User is presented with fallback options instead of seamless execution
- Breaks the intended `/feature-plan` → `/feature-build` workflow

## Review Objectives

1. **Analyze current task discovery logic** in AutoBuild CLI
2. **Identify all locations** where task paths are resolved
3. **Evaluate implementation approaches**:
   - Recursive directory search
   - Feature YAML manifest lookup
   - Hybrid approach
4. **Assess impact** on existing functionality
5. **Recommend implementation approach** with minimal regression risk

## Scope

### In Scope
- AutoBuild CLI task discovery (`guardkit autobuild task`)
- Feature-level autobuild (`/feature-build FEAT-XXX`)
- Task path resolution in Python SDK integration
- Worktree creation with nested paths

### Out of Scope
- Changes to `/feature-plan` output structure
- Changes to `/task-work` or `/task-complete` commands
- PM tool integration changes

## Key Files to Review

1. **CLI Entry Point**: `scripts/autobuild-cli.py` or similar
2. **Task Discovery**: Any `find_task()`, `locate_task()`, or similar functions
3. **Feature YAML**: `.guardkit/features/FEAT-XXX.yaml` structure
4. **SDK Integration**: Player/Coach agent task loading

## Expected Deliverables

1. Architecture analysis of current task discovery
2. Comparison of implementation approaches
3. Recommended approach with rationale
4. Risk assessment
5. Implementation task breakdown (if [I]mplement chosen)

## Acceptance Criteria

- [ ] Current task discovery logic fully documented
- [ ] All affected code locations identified
- [ ] At least 2 implementation approaches compared
- [ ] Recommendation includes backward compatibility assessment
- [ ] Implementation breakdown ready if proceeding

## Context

Screenshot from user shows the fallback prompt:
```
The guardkit autobuild CLI doesn't support nested task directories
(tasks are in tasks/backlog/application-infrastructure/).
How would you like to proceed with FEAT-B3F8 (8 tasks, 4 waves)?

○ Move task files to flat structure
○ Use Task tool fallback
○ Execute tasks directly without Player-Coach
○ Other
```

This review will determine how to eliminate this friction point.
