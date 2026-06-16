---
id: TASK-FAUD-002
title: Add `guardkit feature audit` CLI subcommand with --fix
status: backlog
task_type: feature
feature_id: FEAT-FAUD
wave: 2
implementation_mode: task-work
complexity: 4
priority: medium
created: 2026-06-16T00:00:00Z
depends_on: [TASK-FAUD-001]
tags: [feature-audit, cli]
---

# Task: `guardkit feature audit` CLI subcommand

## Description

Expose the auditor from TASK-FAUD-001 as a CLI subcommand under the existing
`guardkit feature` command group (`guardkit/cli/feature.py`), with table output
and an optional `--fix` to reconcile stale YAML statuses.

## Acceptance Criteria

- [ ] `guardkit feature audit` prints a table (one row per feature) with columns:
      Feature, Declared, Inferred, Tasks (completed/total), Stale?. Uses
      `audit_features()` from `guardkit/orchestrator/feature_audit.py`.
- [ ] Stale rows are visually flagged (e.g. a `⚠` / `STALE` marker); a summary
      line prints the count of stale features.
- [ ] `guardkit feature audit --fix` rewrites the `status:` field of each stale
      feature YAML to its `inferred_status`, preserving the rest of the YAML
      (load → set `status` → dump), and prints what it changed. Without `--fix`
      it is read-only.
- [ ] Exit code is `0` when no stale features, `1` when stale features exist and
      `--fix` was NOT passed (so it can gate CI); `0` after a successful `--fix`.
- [ ] Tests in `tests/unit/cli/test_feature_audit_cli.py` (or alongside the
      existing feature-CLI tests) covering: read-only table output; `--fix`
      mutates a synthetic stale YAML to the inferred status; exit codes. Use a
      `tmp_path` / CliRunner fixture, not the real repo.

## Implementation Notes

- Add the subcommand to the existing `feature` Click group in
  `guardkit/cli/feature.py` (do not create a new top-level command). If that
  group does not exist, add it minimally and register it in `guardkit/cli/main.py`.
- Reuse `audit_features()` — no audit logic in the CLI layer.
- For `--fix`, round-trip the YAML with `yaml.safe_load` / `yaml.safe_dump`
  (accept key reordering; do not hand-edit text).
