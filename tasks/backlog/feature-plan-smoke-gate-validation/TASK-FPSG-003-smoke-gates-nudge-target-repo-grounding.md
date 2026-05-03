---
id: TASK-FPSG-003
title: "smoke_gates_nudge: ground example block in target repo's actual tests/ subdirs (L3c)"
status: completed
created: 2026-05-02T13:30:00Z
updated: 2026-05-02T14:30:00Z
completed: 2026-05-02T14:30:00Z
completed_location: tasks/backlog/feature-plan-smoke-gate-validation/
completion_note: "Kept in feature folder for /feature-complete to archive with siblings (FPSG-001/002/004/005)."
priority: medium
task_type: enhancement
implementation_mode: direct
tags:
  - smoke-gates-nudge
  - generate-feature-yaml
  - smoke-gate
  - cross-repo-followup
  - feature-plan-smoke-gate-validation
complexity: 2
estimated_minutes: 60
parent_review: appmilla_github/forge/TASK-REV-DEA8
parent_feature: feature-plan-smoke-gate-validation
wave: 1
dependencies: []
---

# Task: smoke_gates_nudge — inject target repo's actual `tests/` subdirs

## Description

When `generate-feature-yaml --discover` runs without a `smoke_gates`
block in the feature YAML, the existing
`installer/core/commands/lib/smoke_gates_nudge.py` prints a banner
with a generic example:

```
    smoke_gates:
      after_wave: [2, 3]
      command: |
        set -e
        pytest tests/smoke -x
      ...
```

`tests/smoke` is a placeholder. The agent reading this banner has no
authoritative grounding in the target repo's actual `tests/` tree, so
it falls back to whatever shape it already has in context — which in
TASK-REV-DEA8 was a guardkit-shaped `tests/cli/` from sibling task
notes.

This task replaces the generic placeholder with a discovered listing
of the target repo's actual `tests/` subdirectories.

## Acceptance Criteria

- [x] **New helper** `discover_test_roots(repo_root: Path) -> list[str]`
      in `smoke_gates_nudge.py` (or shared with L3b's
      `pytest_argv.py`). Returns sorted list of immediate
      subdirectories of `<repo_root>/tests/`. If `tests/` does not
      exist, returns `[]`.
- [x] **Banner enhanced** — when at least one test root is
      discovered, the banner prints them above the example block:
      ```
      ℹ️  Feature-level smoke gates (R3) not configured
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        Available test roots in this repo (use these, not invented paths):
          tests/forge        tests/integration   tests/unit
          tests/bdd          tests/dockerfile    tests/hardening

      To activate: ...
          smoke_gates:
            after_wave: [2, 3]
            command: |
              set -e
              pytest tests/forge tests/integration -x      # uses discovered roots
            ...
      ```
- [x] **Fallback** — if `tests/` doesn't exist or is empty, fall back
      to the current generic `pytest tests/smoke -x` placeholder
      (with a note: "no `tests/` directory discovered — use the path
      that holds your test suite").
- [x] **Schema-pinned test still passes** —
      `tests/unit/commands/test_smoke_gates_nudge.py::test_notice_example_validates_against_smoke_gates_schema`
      remains green (the example block still validates against the
      `SmokeGates` Pydantic model).

## Test Requirements

- [x] Unit test against tmp_path repo with
      `tests/forge/`, `tests/unit/` → banner contains both names in
      the "Available test roots" section.
- [x] Unit test against tmp_path repo with no `tests/` → banner falls
      back to generic placeholder.
- [x] Existing schema-pinned test still passes.

## Implementation Notes

- Use `Path.iterdir()` with `is_dir()` filter. Skip `__pycache__`,
  `.pytest_cache`, `node_modules`, and any directory starting with `.`.
- Sort alphabetically for stable banner output.
- Cap at ~12 roots in the banner output to avoid excessive width;
  if more, truncate with "…".

## Files

- `installer/core/commands/lib/smoke_gates_nudge.py` — primary edit
- `tests/unit/commands/test_smoke_gates_nudge.py` — extend
