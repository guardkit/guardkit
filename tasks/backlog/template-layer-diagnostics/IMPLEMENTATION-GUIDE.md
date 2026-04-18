# Implementation Guide: Template Layer Diagnostics (FEAT-A925)

**Feature**: Template Layer Diagnostics — TASK-REV-A925 follow-ups
**Parent review**: [TASK-REV-A925](../../in_review/TASK-REV-A925-orchestrator-template-scaffold-rendering-gap.md)
**Review report**: [.claude/reviews/TASK-REV-A925-review-report.md](../../../.claude/reviews/TASK-REV-A925-review-report.md)

## Execution order

### Wave 1 (parallel, no cross-deps)

| Task | File | Complexity | Mode | Notes |
|------|------|------------|------|-------|
| [TASK-INIT-D4E7](./TASK-INIT-D4E7-init-pattern-layer-summary.md) | `guardkit/cli/init.py` + test | 3 | task-work | High priority (highest user-visible impact) |
| [TASK-SMK-B3A1](./TASK-SMK-B3A1-extend-lcl-003-deepagents-variants.md) | `tests/integration/test_template_render_import.py` | 5 | task-work | Medium priority; mechanical extension |

**Parallelism rationale**: different files, no shared state, independent
validation (unit test vs integration test).

### Wave 2 (single task, depends on Wave 1)

| Task | File | Complexity | Mode | Notes |
|------|------|------------|------|-------|
| [TASK-DOC-9F2C](./TASK-DOC-9F2C-two-layer-template-model.md) | `docs/guides/template-two-layer-model.md` + `CLAUDE.md` | 3 | task-work | Depends on INIT-D4E7 for tip-link target path |

## Validation steps

After each Wave completes, run:

```bash
# Wave 1 validation
pytest tests/unit/cli/test_init.py -v
pytest tests/integration/test_template_render_import.py -v

# Wave 2 validation (manual)
# 1. Render the markdown and preview
# 2. Click all links in the new guide
# 3. Run `guardkit init langchain-deepagents-orchestrator` into a scratch
#    dir and verify the tip link in the summary output resolves to the
#    new guide
```

## Entry points

To start work, from the repo root:

```bash
# Wave 1 — either or both in parallel
/task-work TASK-INIT-D4E7
/task-work TASK-SMK-B3A1

# Wave 2 — after Wave 1 merges
/task-work TASK-DOC-9F2C
```

## Coordination with other tracks

- **FEAT-1A5E (Template Pattern Layer for AutoBuild)** — independent.
  Can land in any order relative to this feature.
- **R4 design spike (`guardkit render` command)** — not filed as a task
  yet. Expected route: `/feature-plan "first-class guardkit render
  command for template pattern layer"`. No dependency on this feature,
  but DOC-9F2C's "if you need scaffold files today" section will
  reference the future `guardkit render` command by name.
- **Forge repo R1 hand-scaffold** — out-of-repo; user-owned.

## Rollback plan

All three tasks are narrow, additive, and low-risk:

- INIT-D4E7: a summary line addition; remove the helper + call site to revert.
- SMK-B3A1: data-only additions to `TEMPLATES` list + optional `.j2`
  suffix support in `_render_template`. Remove the new entries and
  revert the suffix handling to revert.
- DOC-9F2C: a new markdown file and a one-line link. Delete to revert.

No data migrations, no schema changes, no runtime behaviour changes to
`guardkit init`'s contract. Safe to land and safe to revert.
