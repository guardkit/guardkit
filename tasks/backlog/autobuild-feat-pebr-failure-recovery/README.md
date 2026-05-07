# AutoBuild FEAT-PEBR Failure-Recovery Fixes

**Parent review**: [TASK-REV-PEBR-001](../../../../forge/tasks/backlog/forge-autobuild-runner-pipeline-emitter-bridge/TASK-REV-PEBR-001-analyse-autobuild-failed-run-1.md)
(in the **forge** repo)
**Review report**: [docs/reviews/FEAT-PEBR-failed-run-1-analysis.md](../../../../forge/docs/reviews/FEAT-PEBR-failed-run-1-analysis.md)
(in the **forge** repo)
**Status**: Backlog
**Created**: 2026-05-07

## Problem Statement

The first `guardkit autobuild feature FEAT-PEBR` run terminated in
`UNRECOVERABLE_STALL` after 3 turns on Wave 1 / TASK-FRR-PEB-001.
The Player produced a clean implementation (80/80 unit tests passing,
ruff clean, all 6 ACs reported with evidence), but the Coach gate
deterministically failed every turn, criteria_passed locked at 0/6,
and the stall detector exited the loop.

The review traced this to a **deterministic 5-stage chain entirely
inside GuardKit**:

1. Stub plan on disk (no `## Files to Create` sections) →
   `PlanAuditor` returns `skipped=True`.
2. AC-fallback fires:
   `AgentInvoker._scan_ac_for_missing_paths` extracts file-like tokens
   from AC text. Bare basenames like `pipeline_consumer.py` fail the
   `(worktree_path / basename).exists()` check.
3. Verdict `{status: "violation", severity: "high",
   missing_files: ["pipeline_consumer.py"]}` is written to
   `task_work_results.plan_audit`, overriding the Player's self-report.
4. Coach reads `plan_audit.violations > 0` →
   `_feedback_from_gates` short-circuits, never running
   `_validate_requirements` →
   `validation_results.requirements: null`.
5. `_count_criteria_passed` falls back to an empty
   `acceptance_criteria_verification.criteria_results` → returns 0.
   Stall detector trips on 3 turns of identical signature + 0
   criteria → unrecoverable.

Each stage is independently fixable; landing **any one** of #1, #2,
or providing an explicit plan (forge-side TASK-FRR-PEB-FM-001) breaks
the chain.

## Solution Approach

Land six fixes in two waves:

### Wave 1 — disjoint files, parallel-safe

| Task | Priority | File | What |
|------|----------|------|------|
| [TASK-GK-AC-001](TASK-GK-AC-001-dont-flag-bare-basenames-in-ac-scanner.md) | **P0** | `agent_invoker.py:6028-6094` | Don't flag bare basenames as missing — primary fix |
| [TASK-GK-CR-001](TASK-GK-CR-001-populate-requirements-on-coach-gate-fail.md) | **P0** | `coach_validator.py:1080-1086` | Populate requirements on gate-fail short-circuit — defence-in-depth |
| [TASK-GK-PA-001](TASK-GK-PA-001-plan-audit-modify-vs-create-comparison.md) | P1 | `plan_audit.py:177-208, 420-458` | Compare files_to_modify against git-modified set |
| [TASK-GK-PROF-001](TASK-GK-PROF-001-template-aware-profile-expected-phases.md) | P2 | profile config | Derive phase-3 specialist from template's installed agent set |

### Wave 2 — rebase Wave 1

| Task | Priority | File | Rebase target |
|------|----------|------|---------------|
| [TASK-GK-FB-001](TASK-GK-FB-001-surface-must-fix-first-in-feedback-summary.md) | P2 | `coach_validator.py` + `autobuild.py` | rebase CR's coach_validator changes |
| [TASK-GK-DOC-001](TASK-GK-DOC-001-exclude-autobuild-artefacts-from-doc-level-counter.md) | P2 | `agent_invoker.py:6598-6649` | rebase AC's agent_invoker changes |

## Sibling task in the forge repo

[TASK-FRR-PEB-FM-001](../../../../forge/tasks/backlog/forge-autobuild-runner-pipeline-emitter-bridge/TASK-FRR-PEB-FM-001-add-explicit-files-sections-and-reclassify.md)
in the forge repo provides a **fast workaround**: by adding explicit
`## Files to Create` and `## Files to Modify` sections to the
TASK-FRR-PEB-001 (and 002-014) task bodies, `PlanAuditor` consumes
the explicit plan and never falls through to the AC-fallback scanner.
This unblocks FEAT-PEBR's `--resume` without any GuardKit code change
landing — useful if the GK fixes are not Tuesday-deliverable.

## Unblock criteria

The minimum unblock set is **any one of**:
- TASK-GK-AC-001
- TASK-GK-CR-001
- TASK-FRR-PEB-FM-001 (forge-side workaround)

The recommended set (defence-in-depth across all five stages) is
**all four of**:
- TASK-GK-AC-001 (P0)
- TASK-GK-CR-001 (P0)
- TASK-GK-PA-001 (P1)
- TASK-FRR-PEB-FM-001 (forge — P1, also serves as Tuesday-workaround)

P2 items (FB / DOC / PROF) can ship after the unblock and do not gate
the FEAT-PEBR resume.

## Verification

After landing the unblock set, in the forge repo:

```bash
guardkit autobuild feature FEAT-PEBR --resume
```

Expected: Wave 1 / TASK-FRR-PEB-001 turns to APPROVED in 1 turn,
criteria_met=6, decision=approve, run continues to wave 2.

The preserved worktree at
`forge/.guardkit/worktrees/FEAT-PEBR/` is the verification fixture —
do not delete it until the resume succeeds.

## Completion

When the unblock set is in `completed/`:
- `/task-complete TASK-REV-PEBR-001` (in the forge repo) once the
  FEAT-PEBR resume succeeds.
- Capture feature-level outcome to Graphiti under
  `guardkit__task_outcomes` referencing TASK-REV-PEBR-001 as the
  parent review.
