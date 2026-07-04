# Retro: AutoBuild Coach approved a task with an undefined BDD step

**Date:** 2026-07-04
**Feature / task:** study-tutor `FEAT-SMP-002` (Postgres StudentStore reads, W2) — `TASK-SMP2-07` (BDD step defs + fake/ephemeral-PG read tests)
**Tool:** `guardkit autobuild feature` (SDK harness, `GUARDKIT_HARNESS=sdk`)
**Severity:** Low–Medium (one defect slipped Coach approval; caught in the operator's independent pre-merge verification; the product code was correct — test wiring only)
**Status:** Resolved (one-line step def added by hand before merge)
**Tags:** autobuild, guardkit, coach, bdd, pytest-bdd, verification, honesty-abort
**Related:** the two sibling study-tutor retros (same family, `study-tutor/docs/retros/`): [self-defeating boundary tests](../../../study-tutor/docs/retros/2026-07-03-autobuild-self-defeating-boundary-tests.md) and [parallel-wave worktree pollution](../../../study-tutor/docs/retros/2026-07-03-autobuild-parallel-wave-worktree-pollution.md).

## Summary

`TASK-SMP2-07` authored the pytest-bdd step definitions that make the feature's 19 scenarios executable. The Coach **approved** it (turn 2), and the whole feature reported 7/7 tasks passed. But a plain `pytest features/student-model-postgres-store-reads/` in the operator's independent pre-merge pass **failed**:

```
StepDefinitionNotFoundError: Step definition is not found:
When "her recent misconceptions are read"
  Line 195 ... scenario "A recent misconception is returned with a confidence band at observation"
```

The feature file has four "read misconceptions" `When` phrasings — `… over the default recency window`, `… over a {N}-day window`, and the **bare** `her recent misconceptions are read` (used by the band-at-observation scenario). The Player wired the two qualified variants but not the bare form, so that one scenario had no matching step and pytest-bdd raised a hard collection error. The Coach's per-task green missed it; only the operator's independent run caught it.

**Crucially, this was a test-wiring gap, not a product defect.** The `get_recent_misconceptions` band-at-observation logic (LEFT JOIN on the current `topic_confidence.band`, default `"struggling"`) was correct and independently covered by `tests/integration/knowledge/store/test_postgres_get_recent_misconceptions.py` (green among 109 passing integration tests). Only the BDD scenario's step handler was absent.

## Root cause

Two contributing factors, both worth fixing:

1. **The task's BDD oracle was not (re-)executed as an independent, blocking gate on the turn that authored the step defs.** `TASK-SMP2-07` turn 1 hit `partial_honesty_abort` — the Player's report over-claimed files that did not exist on disk, so evidence gathering aborted before any independent verification: *"leaving all quality gates null (tests, bdd, coverage_details, plan_audit, arch_review). No independent test execution occurred."* The task then converged and approved on turn 2 after the file list was corrected — but **no `TASK-SMP2-07_junit.xml` was ever produced** (tasks SMP2-01…06 each emitted one; the *authoring* task did not). So the approving turn's BDD signal leaned on the Player's self-reported "scenarios passing" rather than a fresh `pytest features/` that would have surfaced the collection error.

2. **Undefined-step vs. not-yet-implemented ambiguity.** Even when the R2 task-level BDD oracle *does* run, pytest-bdd's "undefined step" concept overlaps semantically with "step stubbed as pending," and the runner's three-state mapping (`scenarios_passed` / `scenarios_failed` / `scenarios_pending`) treats `pending` as **non-blocking** by design. A step handler that is *genuinely never wired* (`StepDefinitionNotFoundError`) for a scenario the current task is responsible for making executable should be `failed`, not silently folded into non-blocking `pending`.

## Evidence

```
# operator independent run (pre-merge), plain pytest:
2 failed, 50 passed
  FAILED ...::test_a_recent_misconception_is_returned_with_a_confidence_band_at_observation
  -> StepDefinitionNotFoundError: When "her recent misconceptions are read"

# after the one-line fix:
52 passed
```

- `TASK-SMP2-07` turn-1 record: `decision: feedback` … *"Evidence gathering aborted at partial_honesty_abort stage … No independent test execution occurred."* Turn 2: `decision: approve`.
- `.guardkit/bdd/` held `TASK-SMP2-01_junit.xml` … `TASK-SMP2-06_junit.xml` but **not** `…07`.
- Band-at-observation behaviour was independently correct (integration test green), confirming the defect was scenario wiring only.

## Impact

Low — caught pre-merge by the operator's independent full verification (the exact practice the sibling self-defeating-boundary-tests retro already mandates). Cost: one hand-fix plus a re-verify. **Had the merge trusted Coach-green alone, `pytest features/` would have been red on `main` (CI failure), despite correct product code.** This is a "Coach per-task green ≠ mergeable" case with a different mechanism than the sibling retro (there: a stale test invalidated by a later task; here: an undefined step mis-scored as non-blocking / never independently run).

## Resolution

One line — stack the bare form onto the existing default-window handler (pytest-bdd allows multiple `@when` decorators per function):

```python
@when("her recent misconceptions are read")
@when("her recent misconceptions are read over the default recency window")
async def read_recent_misconceptions_default_window(bdd_context): ...
```

Re-ran `pytest features/…` → `52 passed`. No product code changed. Merged as study-tutor `1c27347`.

## Prevention / action items

- [ ] **Make the R2 task-level BDD oracle a real, independent, blocking gate on the BDD-authoring task** — it must actually execute `pytest features/` (emit junit) on the approving turn, not fall back to the Player's self-report. When a turn's evidence is `partial_honesty_abort` with all gates null, a subsequent approving turn should **require a fresh independent test execution** before `approve` (never approve a null-evidence gate on self-report).
- [ ] **Classify `StepDefinitionNotFoundError` as `scenarios_failed`, not `scenarios_pending`, for `@task:`-tagged scenarios owned by the current task.** "Pending" should mean an explicitly stubbed, not-yet-implemented step — not a handler that is missing entirely. Distinguish the two in `bdd_runner.py`'s outcome mapping.
- [ ] **Emit a BDD junit for the authoring task, not only for earlier tasks whose scenarios were still pending.** The absence of `TASK-SMP2-07_junit.xml` was the tell.
- [ ] **Operator practice reaffirmed:** always run an independent `pytest features/ && pytest tests/` before merging AutoBuild output. Coach per-task green is necessary but not sufficient (same conclusion as the self-defeating-boundary-tests retro; the two failure modes compound).

## Links

- Merged feature: study-tutor `main` @ `1c27347` (squash of `autobuild/FEAT-SMP-002`).
- Sibling retros (study-tutor repo): self-defeating boundary tests; parallel-wave worktree pollution — the three together map the "Coach-green but not mergeable" surface for store-style autobuild features.
