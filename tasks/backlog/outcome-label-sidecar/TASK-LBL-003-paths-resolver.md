---
id: TASK-LBL-003
title: "paths.py: live-worktree vs archive-home sidecar target resolver"
status: backlog
created: 2026-07-10T12:40:00Z
updated: 2026-07-10T12:40:00Z
priority: high
task_type: feature
parent_review: TASK-REV-3359
feature_id: FEAT-0D1C
wave: 2
implementation_mode: direct
complexity: 3
dependencies: [TASK-LBL-001]
tags: [observability, labels, obs-6, 80fe-archive-seam]
---

# Task: paths.py — live-worktree vs archive-home sidecar target resolver

## Description

Add `guardkit/labels/paths.py` resolving WHERE a label record lands: the live
`.guardkit/autobuild/{task_id}/` evidence directory when it exists, otherwise
the durable 80FE archive home (dispositions frequently land AFTER
`WorktreeManager.cleanup()` has archived and pruned the worktree — reviews are
post-merge).

## Critical constraints (from TASK-REV-3359 findings F1/F2)

1. **Share the archiver's acquisition path — do not reimplement it.** Import
   `get_archive_root_from_env` from `guardkit.worktrees.archive`
   (`archive.py:364-374`) and mirror its `~/.guardkit/archive/<repo-name>/`
   fallback (`archive.py:82-93`). Hard-coding the env-var name or default path
   here is the exact divergence
   `.claude/rules/cli-wrapper-shares-client-acquisition-path.md` forbids.
2. **Archive layout is nested**: `archive_root/<feature_or_task_id>/<task_id>/…`
   (`archive.py:194-195` + `manager.py:544-547`). Solo task:
   `archive_root/TASK-X/TASK-X/`. Feature worktree: `archive_root/FEAT-Y/TASK-X/`.
   The resolver must search both shapes: direct `<task_id>/<task_id>/` and a
   scan of `archive_root/*/<task_id>/`.
3. **The task id is a join key, not a write primitive**: reject task ids failing
   `^[A-Za-z0-9._-]+$` before any path construction (defence in depth on top of
   the LBL-001 schema validator) — no write may land outside the evidence home.

## Environment-variable surface (hermetic-env contract)

This module reads exactly one environment variable: **`GUARDKIT_ARCHIVE_ROOT`**
(via the shared `get_archive_root_from_env`). Every test exercising archive
resolution MUST pin it with `monkeypatch.setenv`/`delenv` — a test whose outcome
depends on the ambient value is not a test of this code.

## Deliverables

- `guardkit/labels/paths.py`:
  - `resolve_label_target(task_id: str, repo_root: Path) -> LabelTarget`
  - `LabelTarget` dataclass: `directory: Path`, `location: Literal["live", "archive"]`,
    `error: Optional[str]` (unresolvable → error populated; caller degrades
    non-blocking, per the fail-open posture).
  - Live check: `repo_root/.guardkit/autobuild/{task_id}/` exists → use it.
  - Archive fallback: resolve archive root (shared helper), search the two
    nesting shapes; if the task has no archived evidence dir either, create
    `archive_root/<task_id>/<task_id>/` so post-archival labels still have a
    durable home joinable by task_id.

## Acceptance Criteria

- [ ] Live evidence dir present → returns it with location="live"
- [ ] Live dir absent, archived copy present (both solo and feature-nested shapes) → returns the archived dir with location="archive"
- [ ] GUARDKIT_ARCHIVE_ROOT override is honoured via the SHARED helper (assert by monkeypatching the env var, not by duplicating the default path)
- [ ] Task id containing path separators or ".." returns an error result; no directory outside the evidence/archive home is touched or created
- [ ] Unreachable/unwritable archive root returns an error result without raising
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Test Requirements

- [ ] Unit tests in `tests/unit/labels/test_paths.py` using tmp_path fixtures for repo root and archive root; every archive test pins GUARDKIT_ARCHIVE_ROOT hermetically
