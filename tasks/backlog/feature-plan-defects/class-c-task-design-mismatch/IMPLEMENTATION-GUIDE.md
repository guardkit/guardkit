# Implementation Guide — Class C task-design mismatch

This guide is for whichever operator/agent picks up the workstream.
Read [README.md](README.md) first for the problem statement and
solution shape.

## Wave plan

### Wave 1 — Foundations (parallel)

Two independent edits, no shared state. Both can start immediately.

| Task | Why first | Notes |
|---|---|---|
| **TASK-FPTC-001** — detector + prompt | Highest user-visible value; prevents new bad plans from being authored. | Pure prompt-engineering edit to `feature-plan.md` + a contract test. No Python implementation. |
| **TASK-FPTC-002** — enum + profile | Cheapest unblock for Wave 2. | ~1h. The `DECLARATIVE` profile in `task_types.py` is the closest template — copy and flip the test/coverage flags off. |

**Conductor**: run as `feature-plan-defects-wave1-1` and
`feature-plan-defects-wave1-2` worktrees. Touchpoints:
- FPTC-001: `installer/core/commands/feature-plan.md`,
  `tests/integration/commands/test_feature_plan_detector_rules.py`
- FPTC-002: `guardkit/models/task_types.py`,
  `guardkit/orchestrator/feature_loader.py`,
  `tests/unit/models/...`, `tests/unit/orchestrator/...`

No file overlap → genuinely parallel.

### Wave 2 — Enforcement (parallel)

Both consume the `OPERATOR_HANDOFF` enum from FPTC-002.

| Task | Notes |
|---|---|
| **TASK-FPTC-003** — orchestrator skip | The dispatch site in `feature_orchestrator.py` is the earliest possible check. Skip Player+Coach entirely — do not allocate worktrees, do not start Player. Record deferred outcome shape per the contract block in TASK-FPTC-003. |
| **TASK-FPTC-004** — validator+loader | Branch on `task_type == OPERATOR_HANDOFF` at top of CoachValidator entry point. May be a no-op for FeatureLoader if it already accepts tasks without strict AC presence. |

**Coordination point**: both tasks reference a "deferred outcome
record shape." Pick the shape in TASK-FPTC-003 (it's the producer)
and have TASK-FPTC-004 read from the same source. Suggested:
```python
{"task_id": "...", "outcome": "deferred", "reason": "..."}
```
But the actual shape should match whatever existing progress-log /
state-file mechanism `feature_orchestrator` already uses — read the
file before deciding.

**Conductor**: `feature-plan-defects-wave2-1` and `-wave2-2`. Both
touch `guardkit/orchestrator/` but different files (orchestrator vs
quality_gates/coach_validator + feature_loader). No real conflict.

### Wave 3 — Polish (parallel — 2 tasks)

| Task | Notes |
|---|---|
| **TASK-FPTC-005** — feature-complete checklist | Reads deferred outcomes from Wave 2's record shape. Surface in merge summary + plan summary. |
| **TASK-FPTC-006** — detector tests vs reproducers | Pure test code. Verbatim AC fixtures from TASK-GR-SEED + TASK-GR-DEMO + 3 false-positive guards. |

**Conductor**: `feature-plan-defects-wave3-1`, `-wave3-2`. No file overlap.

### Wave 4 — Consolidation (solo)

| Task | Notes |
|---|---|
| **TASK-FPTC-007** — docs + folder consolidation | Depends on all six prior tasks (cross-links them in the new classification guide). Solo wave because the scope is small (~1h) and serialisation is required. |

**Conductor**: `feature-plan-defects-wave4-1`. Single worktree; runs after Wave 3 completes.

## Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| FPTC-001 prompt rules under-cover the strong signal space (false negatives) | Medium | FPTC-006 is the hard gate. If it fails for either reproducer, prompt is incomplete. |
| Existing CoachValidator has implicit assumptions that ACs are non-empty | Low-medium | FPTC-004 has a regression-guard AC asserting non-operator-handoff types still pass. Run full unit-test suite before merge. |
| The `feature_orchestrator` deferred-state field name diverges between FPTC-003 and FPTC-005 | Medium | Coordination point called out explicitly. The README and FPTC-003's contract block both spell out the suggested shape; FPTC-005 reads it. |
| Folder rename in FPTC-007 disturbs existing FPSG task IDs | Low | AC-FPTC-007-01 explicitly forbids ID changes — only folder layout changes. Use `git mv`. |
| The "Required operator follow-up" template bloats task files | Low | FPTC-001 specifies 3-5 lines max for the template. |

## Quality gates

Each task ships under standard `/task-work` quality gates (Phase
2.5 architectural review, Phase 4 tests, Phase 4.5 enforcement,
Phase 5 code review). Per the parent review's findings:

- **FPTC-001, 005, 007** are primarily `.md` edits — Phase 2.5 may
  pass quickly (no architectural decisions to review). Use
  `--intensity=light`.
- **FPTC-002** is a one-line enum + profile addition — `--intensity=minimal`
  or `--micro`.
- **FPTC-003, 004** are the structural changes — `--intensity=standard`
  required.
- **FPTC-006** is test-only — `--intensity=light`.

## Merge strategy

Either:
- **Single PR** (recommended): all 7 tasks under one feature merge via
  `/feature-build` → `/feature-complete`. Cleanest history; one
  reviewer can validate the complete contract.
- **Per-wave PRs**: viable but adds 3 PRs of overhead and tempts
  someone to merge Wave 1 without Wave 2's enforcement layer.

## Verification (post-merge)

After `/feature-complete`:

1. Construct a feature with one operator-handoff task and run
   `/feature-build` against it — the task should be reported
   deferred without any Player/Coach invocation.
2. Run `/feature-plan` against a description containing live-infra
   verbs — verify the agent prompts for the operator_handoff
   classification.
3. Inspect the `/feature-complete` merge summary — verify the
   "Required operator follow-up" section appears and lists the
   deferred task with its ACs.

## See also

- Parent review: [`TASK-REV-AUTM`](../../TASK-REV-AUTM-decide-how-feature-plan-handles-autobuild-unsuitable-tasks.md)
- Decision report: [`.claude/reviews/TASK-REV-AUTM-review-report.md`](../../../../.claude/reviews/TASK-REV-AUTM-review-report.md)
- Sibling Class A/B workstream: [`feature-plan-smoke-gate-validation/`](../../feature-plan-smoke-gate-validation/)
- Sibling complete (orthogonal): [`coach-validator-ac-id-matching/`](../../../completed/2026-05/coach-validator-ac-id-matching/)
- Real-world incidents:
  - `appmilla_github/study-tutor/docs/history/autobuild-FEAT-FD32-failed-after-raising-floor-history.md` (SEED reproducer)
  - `appmilla_github/study-tutor/docs/history/autobuild-FEAT-FD32-failed-yet-again-history.md` (DEMO reproducer)
