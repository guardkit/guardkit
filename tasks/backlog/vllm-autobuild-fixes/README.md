# vLLM AutoBuild Fixes (FEAT-VL01)

## Problem Statement

AutoBuild feature FEAT-947C (PostgreSQL Database Integration) fails when running via vLLM with Qwen3 on Dell GB10 local hardware. 2/8 tasks succeed, 2 fail with 0% criteria verification, and 4 remaining are cancelled by `stop_on_failure`.

## Root Causes

Three verified root causes identified through deep code tracing:

1. **Path Mismatch (Bug #1)**: Qwen3 writes `player_turn_N.json` to repo root instead of worktree for some tasks. Fix 2 recovery only checks the worktree path, so completion promises are never recovered.

2. **Two-Parser Divergence (Bug #2)**: Fix 5 uses `_load_task_metadata()` (YAML frontmatter only) instead of `TaskLoader` (frontmatter + markdown body). Feature task ACs are in the markdown body, so Fix 5 always gets empty acceptance criteria and never generates synthetic promises.

3. **Git Race Condition (Bug #3)**: Parallel Wave 2+ tasks share a single worktree with no git synchronisation. `git diff HEAD` runs without locks, causing non-deterministic file attribution.

## Solution Approach

7 fixes organised into 3 sequential waves, addressing bugs from most critical to defence-in-depth:

| Wave | Tasks | Focus |
|------|-------|-------|
| 1 | VL01, VL02, VL03 | Critical bug fixes (path recovery, TaskLoader, absolute paths) |
| 2 | VL04, VL05 | Parallel safety + timeout scaling |
| 3 | VL06, VL07 | Defence-in-depth (baseline commit, semantic matching) |

## Tasks

| ID | Title | Priority | Complexity | Wave |
|----|-------|----------|------------|------|
| TASK-FIX-VL01 | Path-hardened player report recovery | High | 2 | 1 |
| TASK-FIX-VL02 | Fix 5 - Use TaskLoader for AC extraction | High | 2 | 1 |
| TASK-FIX-VL03 | Absolute paths in execution protocol | High | 2 | 1 |
| TASK-FIX-VL04 | Git operation threading lock | Medium | 3 | 2 |
| TASK-FIX-VL05 | Timeout scaling for local backends | High | 3 | 2 |
| TASK-FIX-VL06 | Per-task baseline commit hash | Low | 4 | 3 |
| TASK-FIX-VL07 | Semantic matching + enhanced synthetic promises | Medium | 5 | 3 |

## Parent Review

- **Review Task**: TASK-REV-8A94
- **Review Report**: `.claude/reviews/TASK-REV-8A94-review-report.md`
- **Failing Output**: `docs/reviews/gb10_local_autobuild/db_feature_1.md`
- **Successful Reference**: `docs/reviews/autobuild-fixes/db_finally_succeds.md`
