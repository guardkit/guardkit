# Run-21 autobuild artifacts snapshot — B-full delivers enrichment; parallel Wave-2 breaks substrate

> **Purpose**: snapshot the FEAT-AOF artifact tree from run 21 (first
> run with `GUARDKIT_COACH_GATHER=1` exercising the B-full
> investigation phase per commit `4e0b05be`) for the GB10 Claude
> session to diagnose. Same pattern as runs 13-20.
>
> **Source**: live worktree artifacts copied 2026-06-09T19:00Z.
> **Run log**:
> [`autobuild-FEAT-AOF-run-21.md`](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-21.md)
> (committed in the same change as this snapshot).

## TL;DR — Mixed result: B-full enrichment works (IA03 ✓), parallel Wave-2 breaks substrate (TP05+GD02 ✗)

```
FEATURE RESULT: FAILED
Status: FAILED
Tasks: 1/3 completed (2 failed)
Duration: 59m 46s
```

| Task | Wave | Mode | Coach | Outcome |
|---|---|---|---|---|
| TASK-FIX-IA03 | 1 (sequential) | B-full Phase-A → toolless synthesis | ✓ approve | **Real verdict + populated `criteria_verification`** |
| TASK-FIX-TP05 | 2 (parallel with GD02) | B-full Phase-A failed mid-flight → degraded to B-min synthesis → synthesis also failed | ✗ error | Connection error |
| TASK-FIX-GD02 | 2 (parallel with TP05) | Same shape as TP05 | ✗ error | Connection error |

Two separately load-bearing observations in one run:

1. **B-full enrichment is real and substantive** ([IA03 coach_turn_1.json](TASK-FIX-IA03/coach_turn_1.json)) — closes run-19 caveat #2 (the `criteria_verification` array was empty in B-min). The tool-using investigation phase produced per-AC structured notes with concrete code-citation evidence.
2. **Parallel Wave-2 Coach calls exceed gemma4:31b's substrate envelope** — two concurrent B-full investigation phases broke llama-swap/llama.cpp with HTTP 502, and COACHBFULL's graceful-degradation fallback to B-min synthesis couldn't recover because the substrate was already crashed.

## 🎯 IA03 — B-full enrichment delivered

[`coach_turn_1.json`](TASK-FIX-IA03/coach_turn_1.json) contains the
populated `criteria_verification` array that was empty in runs 19/20:

```json
{
  "task_id": "TASK-FIX-IA03",
  "turn": 1,
  "decision": "approve",
  "validation_results": {
    "requirements_met": ["AC-001","AC-002","AC-003","AC-004","AC-005"],
    "tests_run": true,
    "tests_passed": true,
    "test_command": "pytest tests/unit/test_doc_level_constraint.py -v --tb=short",
    "test_output_summary": "22 passed, 2 warnings in 3.13s",
    ...
  },
  "criteria_verification": [
    {
      "criterion_id": "AC-001",
      "result": "verified",
      "notes": "Verified that .guardkit/autobuild/ is in _DOC_LEVEL_EXCLUDED_PATTERNS, effectively excluding player_turn_N.json."
    },
    {
      "criterion_id": "AC-002",
      "result": "verified",
      "notes": "Verified that _validate_file_count_constraint uses _is_doc_level_excluded to filter all paths before counting."
    },
    {
      "criterion_id": "AC-003",
      "result": "verified",
      "notes": "Verified the warning message in agent_invoker.py now specifies 'user files'."
    },
    {
      "criterion_id": "AC-004",
      "result": "verified",
      "notes": "Verified 22 passing tests in tests/unit/test_doc_level_constraint.py."
    },
    {
      "criterion_id": "AC-005",
      "result": "verified",
      "notes": "Verified that 2 user files + artifacts do not trigger a warning at the 'minimal' level (limit 2)."
    }
  ],
  "rationale": "The Player implemented all acceptance criteria correctly..."
}
```

**Why this matters**: in runs 19/20, the same field was an empty array
because B-min's deterministic gather doesn't produce per-AC narrative
evidence. B-full's tool-using investigation actually inspected the
code (`_DOC_LEVEL_EXCLUDED_PATTERNS` constant, `_validate_file_count_constraint`,
the warning string) and recorded its findings inline. This is genuine
adversarial-cooperation rigour, not just a schema being filled in for
its own sake.

## ❌ Wave 2 — parallel Coach calls broke the substrate

Wave 2 ran TP05 and GD02 in parallel
([log:516, 583](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-21.md#L516)).
Both Player phases succeeded. Both then entered Coach validation
**simultaneously** (TP05 Coach started ~18:36, GD02 Coach started ~18:38).
Both Coach LLM invocations ran for ~15 minutes producing successful
HTTP 200s in parallel, then **both hit HTTP 502 Bad Gateway within
milliseconds of each other**
([log:700-701](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-21.md#L700-L701)):

```
HTTP/1.1 502 Bad Gateway   (TP05 — ~1050s elapsed)
HTTP/1.1 502 Bad Gateway   (GD02 — ~900s elapsed)
```

COACHBFULL's graceful-degradation fired correctly for both
([log:706, 709](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-21.md#L706-L709)):

```
TASK-ARCH-COACHBFULL: Phase-A gather failed for TASK-FIX-GD02 turn 1 ... degrading to B-min synthesis.
TASK-ARCH-COACHBFULL: Phase-A gather failed for TASK-FIX-TP05 turn 1 ... degrading to B-min synthesis.
```

But the B-min synthesis calls **also failed**
([log:714-715, 743-744](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-21.md#L714)):

```
LangGraphHarness: synthesis ainvoke failed for role='coach'
  model='openai:gemma4:31b': Connection error.
```

Both Wave-2 tasks failed at the exact same timestamp (`18:53:31.458Z`
and `18:53:31.603Z` — within 150ms) — synchronised by the shared
substrate failure.

## Why parallel Wave-2 broke it

Hypothesis (for the GB10 to confirm):

**F23A-style OOM, amplified by concurrent agentic loops.** Each B-full
Phase-A is a deepagents tool-using Coach with growing context (file
reads, test outputs, AC-by-AC inspection). Two such agents running on
the same single GB10 gemma4:31b instance compete for the same KV
cache. Once context for both grows past the envelope, llama-server
crashes. Both clients see the 502.

The COACHBFULL graceful-degradation is correct *in principle* — fall
back to B-min toolless synthesis if Phase-A fails — but assumed the
substrate would still be available. When Phase-A failed due to a
crash, the substrate was down for the synthesis call too. The
fallback is currently substrate-dependent in a way that defeats it
for parallel-wave failure modes.

The wave-1 sequential case worked because only one Coach call hit the
substrate at a time, staying inside the envelope.

## Run progression at a glance

| Phase | Time | Result |
|---|---|---|
| Feature start | 17:53:45 | task budget 4800s × 3 |
| Wave 1 / IA03 Player | → 17:59:01 (~316s) | ✓ 41 created, 1 modified |
| Wave 1 / IA03 SPECHANG | contained | ✓ |
| **Wave 1 / IA03 Coach (B-full → synthesis)** | → 18:19:54 (~21m) | **✓ APPROVE — populated criteria_verification** |
| Wave 2 / TP05 Player | → 18:32:56 (~5m) | ✓ |
| Wave 2 / GD02 Player | → 18:35:47 (~5m) | ✓ |
| Wave 2 / TP05 + GD02 Coach (PARALLEL, B-full Phase-A) | running ~15m each | both growing context |
| **Substrate crash** | ~18:53:00 | HTTP 502 on both, synchronised |
| COACHBFULL degrade-to-B-min for both | ✓ correct path fired | but substrate down |
| Both B-min synthesis calls fail | 18:53:31 | Connection error |
| FEATURE | FAILED | 59m 46s |

## What's in this snapshot

### `TASK-FIX-IA03/` (Wave 1 success — 8 files)

Full artifact set including the populated `coach_turn_1.json`. This is
the headline file for the run.

### `TASK-FIX-TP05/` and `TASK-FIX-GD02/` (Wave 2 substrate failures — 6 files each)

Same artifacts as IA03 minus `coach_turn_1.json` and `checkpoints.json`
(Coach failed before emitting either). The `turn_state_turn_1.json`
captures the orchestrator's post-failure record. `task_work_results.json`
has the substantive Player turn-1 output that Coach was trying to
validate.

## What's NOT in this snapshot

- `coach_turn_1.json` for TP05 / GD02 — substrate crash before emission
- The full Coach LLM streams for the three Coach attempts. Especially
  interesting for the GB10:
  - **IA03 (B-full success)**: 17:59:01 → 18:19:54 UTC — how big did
    the Phase-A investigation context grow, and how small was the
    final synthesis prompt?
  - **TP05 + GD02 (parallel crash)**: 18:36 → 18:53 UTC — how was the
    KV cache split across the two concurrent agents? Did peak RAM hit
    F23A territory in `free -h`?

## Diagnostic hypotheses for the GB10 session

1. **F23A-recurrence under parallel-wave load.** Sequential B-full
   (Wave 1) stayed inside envelope; parallel B-full × 2 (Wave 2)
   broke it. The fix space:
   - **Operator policy**: cap concurrency to 1 for FEAT-AOF on the
     single GB10. (`--max-parallel 1` if such a flag exists, or
     restructure the feature so all tasks are in Wave 1 / single-task
     waves.)
   - **Substrate**: wait for 2nd GB10 + nemotron-3-super:120b-a12b
     (AC-007) and run the B-full investigation phase on the bigger
     machine
   - **Code**: serialize Coach calls within a wave (Player can run
     parallel, but Coach LLM invocations wait their turn at a
     semaphore). Cheap fix; may bottleneck wider features post-cutover.

2. **COACHBFULL graceful-degradation needs a substrate-health check
   before assuming B-min synthesis can run.** Currently the fallback
   path assumes the substrate is the issue with B-full's specific
   tool-using context size, not that the substrate is down. The
   degrade-to-B-min path should probably back off briefly (poll the
   substrate's `/v1/models` endpoint) before attempting synthesis. If
   substrate is still down, the right behaviour is COACHSF01 synthetic
   feedback for retry, not another doomed synthesis call.

3. **The IA03 B-full enrichment delivers exactly what was hoped for.**
   `criteria_verification` is now populated with per-AC notes that
   actually engage with code (`_DOC_LEVEL_EXCLUDED_PATTERNS`,
   `_validate_file_count_constraint`, the warning message text). That
   is meaningful adversarial-cooperation evidence — Coach demonstrably
   read and understood the implementation, not just the test count.

## Cross-reference

- **TASK-ARCH-COACHBFULL** (the architecture this run exercises):
  commit `4e0b05be feat(TASK-ARCH-COACHBFULL): restore investigating
  Coach (B-full) — tool-using gather before toolless grammar synthesis`
- **Run-19 caveat #2** that this run closes (for the Wave-1 task only):
  empty `criteria_verification` array in the B-min D-3 output
- **Run-15 F23A original diagnosis** (commit `1ee4baab`): same shape
  failure on bigger Player payloads under single-Coach load. Run-21
  Wave-2 is the parallel-Coach amplification of the same envelope.
- **Run-11 F23 forensics handoff** (still reusable):
  [`../run-11-f23-forensics-handoff.md`](../run-11-f23-forensics-handoff.md)
  §3 forensic commands with time window **2026-06-09T18:36 → 18:53 UTC**

## Architecture invariants

All silent across all three tasks:
- COACHBFULL Phase-A gather: exercised on IA03 (success), fired-and-degraded on TP05/GD02 (correct path even though substrate ate both)
- COACHBFULL graceful-degradation: correctly took the B-min fallback when Phase-A failed; substrate just couldn't satisfy either
- D-3 toolless synthesis: succeeded for IA03 (the verdict file proves it)
- COACHTESTTO bypass-LLM independent tests: presumably worked (would need to check `task_work_results.json` to confirm — the Coach failures pre-empt that signal)
- SPECCOCH01: contained SPECHANG on all 3 tasks
- COACHSF01: NOT routed for the substrate Connection errors (correct per the substrate-vs-decision invariant)

## Suggested next steps

1. **Run TASK-HMIG-011 (cutover) now, NOT later** — run-20 already
   validated end-to-end success on the B-min posture (which is the
   default, `GUARDKIT_COACH_GATHER` off). B-full is opt-in
   enrichment that can mature independently. Don't block cutover on
   substrate concurrency limits that only show up under parallel-wave
   B-full.
2. **File `TASK-FIX-COACHBSEMAPHORE`** (or similar): serialize Coach
   LLM calls within a wave via a substrate-level semaphore. Cheap
   fix; preserves Player parallelism while bounding Coach load.
3. **Document the operational guidance**: `GUARDKIT_COACH_GATHER=1` is
   currently safe only with sequential waves OR `--max-parallel 1`.
   Add this to the §9.13-style operator runbook or to the
   COACHBFULL task file's "known constraints" section.
