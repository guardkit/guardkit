---
id: TASK-ABFIX-008
title: Fix documentation level false positives and add bootstrap fixture exclusion
task_type: feature
parent_review: TASK-REV-A17A
feature_id: FEAT-CD4C
wave: 3
implementation_mode: task-work
complexity: 3
dependencies: []
autobuild:
  enabled: true
  max_turns: 3
  mode: tdd
status: backlog
priority: low
tags: [autobuild, orchestrator, documentation-level, bootstrap]
---

# Task: Fix documentation level false positives and add bootstrap fixture exclusion

## Description

Two low-severity but noise-generating issues: (1) the documentation level constraint counts `.guardkit/` internal artifacts in the file creation count, producing false positive warnings; (2) environment bootstrap scans test fixtures (e.g., EOL MAUI workloads) that cause noisy `dotnet restore` failures every wave.

## Review Reference

From TASK-REV-A17A Finding 5 (Recs 5a, 5b) and Finding 6 (Recs 6a, 6b):
> 5a: Exclude `.guardkit/` paths from file creation count.
> 5b: Set documentation level to `standard` for feature/refactor task types.
> 6a: Add `bootstrap_ignore` patterns: Support a `.guardkit/bootstrap-ignore` file (gitignore syntax).
> 6b: Exclude `tests/fixtures/` by default from bootstrap scanning.

## Requirements

1. **Documentation level fix** (`agent_invoker.py`):
   - Exclude files under `.guardkit/` from the file creation count used for documentation level warnings
   - Optionally: set documentation level to `standard` for `feature` and `refactor` task types (instead of `minimal`)
2. **Bootstrap fixture exclusion** (`environment_bootstrap.py`):
   - Add `tests/fixtures/` to the default skip list alongside hidden directories (line ~346-365)
   - Support an optional `.guardkit/bootstrap-ignore` file with gitignore-syntax patterns for additional exclusions
3. Tests verifying:
   - `.guardkit/` files are excluded from doc level count
   - `tests/fixtures/` directories are skipped in bootstrap
   - `.guardkit/bootstrap-ignore` patterns are respected

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py` — exclude `.guardkit/` from file count
- `guardkit/orchestrator/environment_bootstrap.py` — add fixture exclusion, bootstrap-ignore
- `tests/` — tests for both fixes

## Acceptance Criteria

- [ ] `.guardkit/` files excluded from documentation level file count
- [ ] `tests/fixtures/` excluded from environment bootstrap scanning
- [ ] Optional `.guardkit/bootstrap-ignore` file supported
- [ ] No .NET restore errors from test fixture projects during bootstrap
- [ ] All existing tests pass
