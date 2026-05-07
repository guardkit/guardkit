# AutoBuild FEAT-PEBR Failure-Recovery Fixes (rev 2)

**Parent review**: [TASK-REV-PEBR-002](../../../../forge/tasks/backlog/forge-autobuild-runner-pipeline-emitter-bridge/TASK-REV-PEBR-002-analyse-autobuild-failed-run-2.md)
(in the **forge** repo)
**Review report**: [docs/reviews/FEAT-PEBR-failed-run-2-analysis.md](../../../../forge/docs/reviews/FEAT-PEBR-failed-run-2-analysis.md)
(in the **forge** repo)
**Predecessor**: [autobuild-feat-pebr-failure-recovery/](../autobuild-feat-pebr-failure-recovery/)
(rev-1 fixes; closed via TASK-GK-AC-001, TASK-GK-CR-001, TASK-GK-PA-001)
**Status**: Backlog
**Created**: 2026-05-07

## Problem Statement

The second `guardkit autobuild feature FEAT-PEBR` run terminated in
`MAX_TURNS_EXCEEDED` after 5 turns on Wave 3 / TASK-FRR-PEB-003. The
Player produced a clean implementation (67/67 unit tests passing,
ruff clean, 7/7 ACs verified at turn 5), but Coach gate failed every
turn on a deterministic phantom-file plan-audit violation.

The rev-1 fixes (GK-AC-001 + GK-CR-001 + GK-PA-001 + FRR-PEB-FM-001)
landed and behave as designed, but each surfaced a new failure mode
that the original review couldn't see. The rev-2 review traced the
run-2 failure to **three independent guardkit-side bugs** plus a
**typo in the forge task body** (which is the trigger):

- **Bug A — AC-fallback scanner ingests qualified prose paths.** The
  basename guard from TASK-GK-AC-001 closed bare-basename false
  positives but the scanner still reads the *entire* task body (not
  just `## Acceptance Criteria`, despite the function name). Any
  qualified prose path (`/`-containing) that doesn't exist verbatim
  is flagged. Run-2's trigger is
  `src/forge/dispatch/autobuild_async.py` on
  TASK-FRR-PEB-003 line 205 — a typo (real file is at
  `src/forge/pipeline/dispatchers/autobuild_async.py`). The scanner
  does literal-path lookups, so the typo and the scope bug compound.
  - Code: `agent_invoker.py:6054-6228`
  - Fix: **TASK-GK-PA-002**

- **Bug B — Coach `_strip_criterion_prefix` strips AC ID before
  `_extract_ac_id` extracts it.** The strip step removes
  `^AC-\d+:\s*` *before* the extractor regex runs
  (`coach_validator.py:3243-3246`). The extractor then sees text with
  no AC label, returns `None`, and Coach falls back to building lookup
  keys via `f"AC-{i+1:03d}"` (zero-padded). Players that emit natural
  `criterion_id="AC-1"` (per the task body's format) miss Coach's
  `"AC-001"` lookup key — Coach reports
  `"No completion promise for AC-001"` despite the Player providing
  one. Players adapt by turn 2 (switch to `AC-001`), producing the
  characteristic 0 → 7 jump in `criteria_met` that defeats the stall
  extender (Bug C).
  - Code: `coach_validator.py:3203-3248` (strip), `:3251-3307`
    (extract), `:3068-3122` (lookup key construction)
  - Fix: **TASK-GK-CV-001**

- **Bug C — Stall extender's uniformity check straddles the 0 → N
  transition.** When count history is `[0, 7, 7, 7, 7]` (Bug B's
  signature), the standard 3-turn check requires `counts[0] == 0`
  and the extended 5-turn check requires uniform non-zero counts
  across the full window — including turn 1's anchoring zero.
  Neither fires; the loop runs out the clock to
  `max_turns_exceeded` even though every turn after the first is a
  verbatim repeat.
  - Code: `autobuild.py:3935-4022`
  - Fix: **TASK-GK-COACH-001**

These three bugs sit on **different sides of the pipeline**:

- Bug A is on the **producer** side (AgentInvoker writes
  `task_work_results.plan_audit`).
- Bug B is on the **consumer** side (CoachValidator reads
  `task_work_results.completion_promises` and matches against the
  task's AC text).
- Bug C is on the **orchestrator** side (AutoBuildOrchestrator decides
  whether to early-exit the turn loop).

Removing any one breaks the chain *for run-2*. But for cross-feature
unblock, all three are needed because:

- Bug A re-trips on any future task with a qualified prose path
  (FRR-PEB-009, -013, -014 likely have such references).
- Bug B silently corrupts every Player's turn-1 `criteria_met` for
  every task in every feature. With Bug A fixed, this is cosmetic
  (gates pass anyway) — but still operator-visible and
  trust-eroding.
- Bug C remains a latent risk for any future plateau-after-progress
  shape on any non-criteria gate.

## Recommended Set

For cross-feature unblock, land **all four** guardkit tasks plus the
forge-side prose fix (in the forge repo):

| Task                                                              | Repo     | Priority | Status (2026-05-07) | Discovered |
|-------------------------------------------------------------------|----------|----------|---------------------|------------|
| [TASK-GK-CV-001](../../in_review/autobuild-feat-pebr-failure-recovery-rev2/TASK-GK-CV-001-fix-strip-before-extract-ac-id-bug.md) | guardkit | **P0**   | ✅ in_review (commit `ce2bf056`) | rev-2 review (run-2) |
| [TASK-GK-PA-002](../../completed/TASK-GK-PA-002/TASK-GK-PA-002.md) | guardkit | **P0**   | ✅ completed (commit `c610426c`) | rev-2 review (run-2) |
| [TASK-GK-COACH-001](../../completed/2026-05/TASK-GK-COACH-001/TASK-GK-COACH-001-plateau-aware-stall-extender.md) | guardkit | P1       | ✅ completed (commit `ddd36cbb`) | rev-2 review (run-2) |
| [TASK-GK-BS-001](./TASK-GK-BS-001-bootstrap-extras-for-smoke-gate-deps.md) | guardkit | P1       | 🔲 backlog | run-3 (smoke-gate `No module named pytest`) |
| TASK-FRR-PEB-FM-002 (in **forge** repo) | forge    | **P0**   | ✅ applied (manually before run-3) | rev-2 review (run-2) |

The forge task is in the **forge** repo because it edits a forge task
file (no guardkit code change).

### Run-3 update (2026-05-07)

The first four tasks (CV-001, PA-002, COACH-001, FM-002) were applied
manually before run-3 and **all four behaved as designed**:

- TASK-FRR-PEB-003 approved in **1 turn** (was max_turns_exceeded
  after 5 turns in run-2).
- TASK-FRR-PEB-004 approved in 2 turns (new wave).
- Waves 1, 2, 3-010 correctly skipped via resume semantics.

Run-3 nevertheless failed because the **smoke gate after Wave 4 hit
a fourth, environmental bug** (`No module named pytest` in the
worktree venv). This is unrelated to bugs A/B/C — it is a
bootstrap-extras gap surfaced for the first time because run-3 was
the first run to actually reach a smoke gate. **TASK-GK-BS-001 is
the structural fix.**

Manual workaround in use today (preserves across `--resume`, lost on
`--fresh`):

```bash
cd <forge>/.guardkit/worktrees/FEAT-PEBR
uv pip install -e ".[dev]"
```

## Validation Plan

Once all four tasks land, validate cross-repo by:

1. In **forge**: confirm `git status` is clean and TASK-FRR-PEB-003
   has frontmatter `status: backlog`, no `autobuild_state` block,
   and no `src/forge/dispatch/` references.
2. In **guardkit**: confirm all three task PRs land green; new
   regression tests pass.
3. From **forge**:
   `guardkit autobuild feature FEAT-PEBR --resume`
4. Expected:
   - Wave 1, 2 skipped (already `status: completed` in
     `.guardkit/features/FEAT-PEBR.yaml`).
   - Wave 3 / TASK-FRR-PEB-010 skipped (already completed).
   - Wave 3 / TASK-FRR-PEB-003 runs and approves in 1 turn:
     `criteria_met=7/7`, `plan_audit_passed=True`,
     `decision=approve`. ✅ **Validated in run-3.**
   - Wave 4 / TASK-FRR-PEB-004 approves. ✅ **Validated in run-3.**
   - Smoke gate after Wave 4 runs cleanly (requires
     TASK-GK-BS-001 OR the manual `uv pip install -e ".[dev]"`
     workaround in the worktree).
   - Waves 5-8 proceed without re-tripping any of A/B/C/D.

If any task in waves 5-8 hits a *different* phantom-path or stall
shape, that is a new bug — open a fresh review task in forge.

## Worktree Preservation

The worktree at
`forge/.guardkit/worktrees/FEAT-PEBR/` MUST be preserved until
validation completes. It contains the partial implementation
(translation.py, bridge.py, version_check.py, fixtures, tests) that
is the verification artefact for both the FEAT-PEBR work and the
guardkit fixes.

Do NOT run `git worktree remove` until step 4 above passes.
