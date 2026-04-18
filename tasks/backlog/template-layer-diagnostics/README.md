# Feature: Template Layer Diagnostics (TASK-REV-A925 follow-ups)

**Feature ID**: FEAT-A925
**Parent review**: [TASK-REV-A925](../../in_review/TASK-REV-A925-orchestrator-template-scaffold-rendering-gap.md)
**Review report**: [.claude/reviews/TASK-REV-A925-review-report.md](../../../.claude/reviews/TASK-REV-A925-review-report.md)
**Created**: 2026-04-18
**Priority**: High (INIT-D4E7), Medium (SMK-B3A1, DOC-9F2C)

## Problem

TASK-REV-A925 investigated a Forge-init incident where `guardkit init
langchain-deepagents-orchestrator` reported success but produced no
`pyproject.toml`, `AGENTS.md`, `agent.py`, or `langgraph.json`. The review
found the filed BLOCKER framing (resolver bug, manifest gap, LCL-003
regression) was incorrect — `guardkit init` is a deliberate config-layer
installer that does not render scaffold files for *any* template, and
LCL-003 explicitly does not cover that code path. The architectural
close-out (wiring the pattern layer into the AutoBuild Player) is already
in flight as FEAT-1A5E.

That left three narrow, legitimate gaps identified by the review but
outside FEAT-1A5E's scope:

1. **Diagnostic trail (R2)** — `guardkit init` summary does not surface
   that a template ships a pattern layer, so users discover the
   config/pattern split in a broken downstream consumer.
2. **LCL-003 scope debt (R3)** — the smoke test covers only
   `langchain-deepagents`; its completion notes defer `-orchestrator`
   and `-weighted-evaluation` as mechanical follow-up.
3. **User-facing doc gap (R5a)** — the two-layer model is documented
   only in review reports; users have no guide to consult. The
   comprehensive doc (TASK-DOC-C3D7) is correctly deferred until
   FEAT-1A5E lands, but an MVP guide closes the immediate expectation
   gap.

## Solution

Three coordinated tasks, plus two out-of-feature items:

1. **TASK-INIT-D4E7 (HIGH, Wave 1)** — Add pattern-layer file count to
   `guardkit init` summary.
2. **TASK-SMK-B3A1 (MEDIUM, Wave 1)** — Extend LCL-003 smoke test for
   `-orchestrator` and `-weighted-evaluation` variants.
3. **TASK-DOC-9F2C (MEDIUM, Wave 2, depends on INIT-D4E7)** — Publish
   user-facing `docs/guides/template-two-layer-model.md`.

### Out of this feature (tracked elsewhere)

- **R1 (Forge unblock)** — hand-scaffold four files in the Forge repo.
  Not a GuardKit change; filed in the Forge repo by the user.
- **R4 (`guardkit render` command)** — design spike scoped via
  `/feature-plan`, separate feature. Genuinely open capability decision.
- **FEAT-1A5E** — Template Pattern Layer for AutoBuild, already in
  [tasks/backlog/template-pattern-layer/](../template-pattern-layer/).
  Independent track; closes the architectural hole proper.
- **R6 (rejected)** — resolver fix and manifest-enforcement ACs from
  the filed task; architecturally incorrect per TASK-REV-A925 F1.

## Scope note

This feature is the **narrow, legitimate subset** of TASK-REV-A925's
recommendations. It does not:

- Reverse the config-layer-only decision (TASK-INST-010, 2026-03-02)
- Duplicate FEAT-1A5E's pattern-layer consumer wiring
- Pre-decide whether `guardkit render` should be built (R4 is a
  separate design spike)

## Execution strategy

| Wave | Tasks | Parallelism | Owner notes |
|------|-------|-------------|-------------|
| 1 | TASK-INIT-D4E7, TASK-SMK-B3A1 | Parallel (different files, no deps) | Both can be picked up by `/task-work` independently. |
| 2 | TASK-DOC-9F2C | Single (depends on INIT-D4E7 for tip link target) | Land after INIT-D4E7 so the cross-reference is coherent, though forward-reference is acceptable. |

See [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) for task ordering
and validation steps.
