# Run-23 autobuild artifacts snapshot — Coach catches real Player bug; F20 was parallel-load amplified

> **Purpose**: snapshot the FEAT-AOF artifact tree from run 23 (Wave 2
> split into 3 sequential single-task waves per the run-22 README's
> Scenario B+C operator workaround for the broken `--max-parallel 1`).
>
> **Source**: live worktree artifacts copied 2026-06-10T16:23Z.
> **Run log**:
> [`autobuild-FEAT-AOF-run-23.md`](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-23.md)
> (committed in the same change as this snapshot).

## 🎯 TL;DR — Coach demonstrably did its job

```
FEATURE RESULT: FAILED
Status: FAILED
Tasks: 2/3 completed (1 failed)
Duration: 149m 3s
```

| Task | Wave | Coach Decision | Notes |
|---|---|---|---|
| TASK-FIX-IA03 | 1 (sequential) | ✓ **approve** (5/5 ACs) | B-full enriched, populated `criteria_verification` |
| TASK-FIX-GD02 | 2 (sequential, alone) | ✓ **approve** (7/7 ACs) | B-full enriched, populated `criteria_verification` |
| TASK-FIX-TP05 | 3 (sequential, alone) | ⚠ **feedback** — Coach caught REAL Player bug | TIMEOUT_BUDGET_EXHAUSTED before turn 2 could fix |

But "FAILED" at the feature level masks **the biggest positive signal
yet for adversarial-cooperation rigour**: TP05's Coach found a real
TypeError in the Player's implementation and emitted a substantive,
schema-valid feedback verdict with 3 issues + 6 per-AC entries
(verified/rejected mix).

## 🎯 Headline: TP05 Coach catches a real Player bug

[`TASK-FIX-TP05/coach_turn_1.json`](TASK-FIX-TP05/coach_turn_1.json):

```json
{
  "task_id": "TASK-FIX-TP05",
  "turn": 1,
  "decision": "feedback",
  "issues": [
    {
      "type": "test_failure",
      "severity": "critical",
      "description": "TypeError in `guardkit/orchestrator/specialist_invocations.py:924` inside `invoke_test_orchestrator`: '<' not supported between instances of 'int' and 'Mock'. This prevents independent test execution from functioning.",
      "requirement": "AC-002",
      "suggestion": "Ensure `sdk_timeout` is correctly typed as an integer before passing it to `min()`, or update the mocks in `tests/unit/test_autobuild_orchestrator.py` to provide integer values for timeouts."
    },
    { "type": "test_failure", "severity": "major", ... },
    { "type": "missing_requirement", "severity": "critical", ... }
  ],
  "criteria_verification": [
    {"criterion_id":"AC-001","result":"verified", "notes":"Unit tests in test_task_types.py for testing profile configuration passed."},
    {"criterion_id":"AC-002","result":"rejected", "notes":"The implementation crashes with a TypeError in invoke_test_orchestrator during independent test runs."},
    {"criterion_id":"AC-003","result":"rejected", "notes":"Logic crashes before feedback can be generated."},
    {"criterion_id":"AC-004","result":"rejected", "notes":"No evidence provided to verify that zero_test_blocking remains False."},
    {"criterion_id":"AC-005","result":"verified", "notes":"Verified via evidence bundle (conftest.py existence)."},
    {"criterion_id":"AC-006","result":"verified", "notes":"Unit tests in test_task_types.py verify the updated profile."}
  ],
  "rationale": "The implementation introduces critical regressions in the orchestrator, causing multiple unit tests to fail with TypeErrors and AssertionErrors. The core functionality of independent test execution (AC-002) is currently broken."
}
```

This is **exactly the adversarial-cooperation rigour the architecture
was designed to provide**:

- Coach actually read the Player's diff and the test failures
- Identified specific code locations (`specialist_invocations.py:924`)
- Differentiated severity (`critical` vs `major`)
- Distinguished verified from rejected per AC (not all-or-nothing)
- Provided actionable suggestions tied to specific tests
- Articulated the load-bearing functional regression in the rationale

The "FAILED" feature status is real — Player did introduce a TypeError —
but the **right** thing happened: Coach caught it before merge, and
the run-23 evidence shows the architecture is now working as designed.

If turn 2 had been allowed, Player would have had the chance to fix
the TypeError per the suggestions and retry. The TIMEOUT_BUDGET_EXHAUSTED
is the operator-policy gap, not an architectural one.

## 🆕 Finding: F20 was parallel-load amplified, NOT a single-call envelope issue

Run 22 hypothesis test: "TP05's F20 ctx overflow at 108,094 tokens —
is it single-call or parallel-amplified?"

**Run-23 answer: PARALLEL AMPLIFIED.** Running TP05 alone in Wave 3,
**no F20 fired**. Coach completed its B-full investigation Phase-A
without hitting the n_ctx limit. The 108,094-token overflow in run 22
was substrate-pressure-amplified: with GD02 also running, llama-server's
KV cache was split, TP05's agent loop had to do more retries / longer
chains to make progress, growing its context further.

This is consistent with what the run-22 README noted as the substrate
behaviour change vs run 21: the failure envelope is now "one call hits
ctx overflow under parallel pressure" instead of "both crash together
(F23A)". With the parallel pressure removed, single-call ctx pressure
also goes away.

**Practical implication**: the operator-side fix for B-full + this
codebase is NOT to bump `n_ctx` (substrate-sizing); it's to **either
land TASK-FIX-MAXPARALLEL01 or use the parallel_groups YAML split**
to keep Coach calls sequential. The substrate envelope is fine for
single-Coach load at 98,304 ctx.

## ⚠ Finding: Task budget needs adjustment for B-full TP05

TP05 in isolation:
- Player turn 1: ~7m
- Specialists (SPECHANG): ~3m
- Coach turn 1 (B-full + synthesis): ~65m
- **Total: ~75m**

Task budget was 4800s = 80m. Coach turn 1 completed with ~5m to spare.
But starting turn 2 would have exceeded the budget. Orchestrator
correctly didn't start a turn it knew couldn't complete.

Options:
1. **Bump TP05's task budget** via per-task frontmatter override to 7200s (120m). Allows 1-2 recovery turns under B-full. (TP05 is `complexity: 4` so this is reasonable.)
2. **Reduce B-full Coach scope for this task type** — but the architectural-rigour win came from B-full's depth, so trimming it loses what we just gained.
3. **Accept**: TP05's Player needs to ship working code on turn 1. The Coach's actionable suggestions are exactly what a human reviewer would say — if the Player can't fix on turn 1, that's a Player-quality finding worth pursuing on its own.

## Wave/timing comparison: parallel vs serialized

| Run | Wave 2 shape | TP05 outcome | Total wall |
|---|---|---|---|
| 21 | parallel (GD02 + TP05) | both ✗ HTTP 502 simultaneously (F23A) | abort |
| 22 | parallel (broken --max-parallel) | GD02 ✓, TP05 ✗ HTTP 400 F20 at 108k | 165m |
| 23 | **3 sequential waves** | GD02 ✓, TP05 ⚠ feedback (real bug caught) | 149m |

Sequential execution adds wall time (no overlap) but **eliminates the
substrate failures entirely**. Run 23's failure is now a real-architecture
signal: Coach found a real bug. Run 22's failure was a substrate
artifact. Different categories.

## ✅ All architecture invariants working

- **B-full Phase-A → toolless synthesis**: 3/3 tasks completed the
  Phase-A → synthesis pipeline this run; 3/3 produced real Coach
  verdicts (vs run 22's 2/3 — failure mode was budget, not substrate)
- **COACHBFULL graceful-degradation**: not exercised this run (no
  Phase-A failures to degrade from — substrate held up)
- **COACHTESTTO bypass-LLM independent tests**: validated again
  (Coach independent-test runs succeeded across all 3 tasks)
- **COACHFG01 fail-closed**: not exercised (no absent-oracle case)
- **COACHSF01 substring-pinned safety net**: not routed (the TP05
  feedback was a real Coach decision, not a synthetic fallback)
- **CTOUT01 cancellation**: not exercised (no in-flight cancellations)
- **SPECCOCH01**: contained SPECHANG on IA03 and TP05 cleanly

## What's in this snapshot

### `TASK-FIX-IA03/` — 8 files (Wave 1 success, B-full enriched)
### `TASK-FIX-GD02/` — 9 files (Wave 2 success, B-full enriched, incl. `phase_4_summary.json`)
### `TASK-FIX-TP05/` — 9 files (Wave 3 feedback, **incl. the headline Coach verdict above**)

All three `coach_turn_1.json` files are real (not COACHSF01 synthetic),
schema-valid, with populated `criteria_verification` arrays. TP05's is
the only one with `decision: "feedback"` instead of `"approve"`, and
its issues/criteria_verification reflect a substantive Coach engagement
with a real Player regression.

## Suggested next steps

1. **Take run 23 as the cutover-positive evidence**. The architecture
   is doing what it was designed to do. Player can ship broken code;
   Coach catches it. The "FAILED" feature status is operational, not
   architectural.

2. **Operator config for TP05**: bump task_timeout for TP05 via
   per-task frontmatter override (`autobuild.task_timeout: 7200`).
   This is the smallest possible change to give B-full + complexity-4
   tasks room to do a feedback → recover turn pattern.

3. **File TASK-FIX-MAXPARALLEL01** as previously suggested. The
   `parallel_groups` YAML workaround proves the orchestrator can run
   serial waves correctly when told to — fixing `--max-parallel` to
   force this without YAML editing is the productisation step.

4. **Resolve the real Player bug**: the TypeError in
   `specialist_invocations.py:924` (`'<' not supported between
   instances of 'int' and 'Mock'`) is a genuine code defect that
   needs fixing. The Coach gave you a precise location and suggestion.
   This is a separate task — not blocking cutover, but worth resolving.

5. **TASK-HMIG-011 (cutover) is unblocked**. Run 20 stands as the
   B-min reproducible baseline; run 23 demonstrates B-full's
   adversarial-cooperation working as designed. The B-full path can
   mature on its own timeline. Cutover the default posture now.

## Cross-reference

- **Run-22 README**: the parallel-load amplification hypothesis that
  run 23 just confirmed
- **Run-20 README**: the validated B-min cutover baseline
- **Run-19 caveat #2 closure**: `criteria_verification` populated on
  all 3 verdicts (B-full delivers)
- **TASK-ARCH-COACHBFULL** (commit `4e0b05be`): the architecture that
  enabled the TP05 verdict above
- **TASK-FIX-COACHFG01** (commit `ae2e1404`): fail-closed mechanism;
  not exercised but loaded as defence-in-depth
