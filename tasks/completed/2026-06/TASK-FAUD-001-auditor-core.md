---
id: TASK-FAUD-001
title: Implement feature-status auditor core module
status: completed
task_type: feature
feature_id: FEAT-FAUD
wave: 1
implementation_mode: task-work
complexity: 5
priority: medium
created: 2026-06-16T00:00:00Z
tags: [feature-audit, cli, maintenance]
---

# Task: Feature-status auditor core module

## Description

Stale `.guardkit/features/*.yaml` statuses are a real maintenance problem: a
feature YAML can say `status: planned` long after its tasks were implemented and
moved to `tasks/completed/`. Build the core logic that detects this, with no CLI
and no orchestrator changes (the CLI is TASK-FAUD-002).

Create a new module **`guardkit/orchestrator/feature_audit.py`** that scans the
feature YAMLs and infers each feature's *real* status from where its tasks live
on disk.

## Acceptance Criteria

- [ ] A `@dataclass FeatureAuditRow` with fields: `feature_id: str`,
      `declared_status: str`, `inferred_status: str`, `tasks_total: int`,
      `tasks_completed: int`, `tasks_pending: int`, `is_stale: bool`.
- [ ] A function `audit_features(repo_root: Path) -> list[FeatureAuditRow]` that:
      reads every `.guardkit/features/*.yaml`; for each task in the feature,
      classifies it as **completed** if a file matching `*<task_id>*.md` exists
      anywhere under `tasks/completed/`, else **pending**; computes
      `inferred_status` = `completed` if all tasks completed, `planned` if none
      completed, else `in_progress`; sets `is_stale = (declared_status != inferred_status)`.
      Skip YAMLs that fail to parse or have no `tasks` key (do not crash).
- [ ] A function `infer_status_for_feature(feature_dict: dict, repo_root: Path) -> str`
      usable standalone, returning the inferred status string.
- [ ] Unit tests in `tests/unit/orchestrator/test_feature_audit.py` covering:
      all-completed → `completed` + stale when declared `planned`; none-completed
      → `planned` + not stale when declared `planned`; mixed → `in_progress`;
      a malformed YAML is skipped without raising. Use a `tmp_path` fixture with
      synthetic `.guardkit/features/` + `tasks/completed/` + `tasks/backlog/`
      layouts (do NOT depend on the real repo state).

## Implementation Notes

- Pure stdlib + `yaml` + `pathlib`; no new dependencies; no changes to the
  autobuild orchestrator or any existing module.
- Task-id → file match: a task file is named like `TASK-XXX-...-slug.md` and may
  sit in `tasks/completed/<TASK-ID>/` or `tasks/completed/<folder>/`. Match by
  substring of the task id in the filename, recursively.
- Keep the module import-light so it loads fast for the CLI.
