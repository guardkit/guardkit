---
id: TASK-FIX-SPECVIOL01
title: Orchestrator-injected specialist-violation records must not be attributed to Player honesty
task_type: feature
status: backlog
created: 2026-06-12T19:50:00Z
priority: high
tags: [autobuild, coach, honesty, specialist, false-red]
complexity: 5
---

# Task: Specialist violation ≠ Player dishonesty

## Problem (observed FEAT-C332 run 2, TASK-QAWE-002, 2026-06-12)

The `test-orchestrator` specialist **hung** (no model activity for 150s; the
TASK-FIX-SPECHANG2 watchdog terminated it before the 600s cap), so no tests
actually ran. The orchestrator then **injected** specialist records into the
Player's `task_work_results.json`:

```
WARNING ... run_specialist(test-orchestrator): hang detected (no model activity for 150s)
INFO    ... Extracted partial data from 0 events: 0 text blocks, 0 tool calls, 0 file mods
INFO    ... Injected orchestrator specialist records into .../task_work_results.json (merged=2, validation=violation)
```

Downstream, the deterministic honesty verification read the resulting
test-claim mismatch as a **Player** dishonesty discrepancy
(`Turn 1 honesty: 0.93 (1 discrepancies)` → `partial_honesty_abort`),
aborted all 9 criteria verifications, and the turn was rejected. Turn 2
repeated the shape (12 discrepancies, honesty 0.38 — mostly stale re-listed
turn-1 claims) and the 4800s task budget exhausted →
`timeout_budget_exhausted`. The Player's production code was real and later
verified green (78 tests) — the task failed on substrate noise attributed
to the Player.

This is a new instance of the
`.claude/rules/path-string-mismatch-is-not-dishonesty.md` meta-class: **a
verifier treating orchestrator-injected content as a Player honesty claim.**
There, the orchestrator injected ghost *paths*; here it injects
`validation=violation` *specialist records* into the same
`task_work_results.json` the honesty gate reads as Player-authored.

## Two halves

1. **Attribution (the rule violation, primary).** When the orchestrator
   injects specialist records (hang, partial extraction, violation), the
   honesty verifier must distinguish "Player claimed X, disk says ¬X"
   (dishonesty) from "Player claimed X, the orchestrator's own specialist
   substrate failed to produce the evidence" (absent signal). The latter
   should surface as a `should_fix`/advisory issue naming the SPECIALIST
   failure, never a `must_fix` honesty discrepancy with `partial_honesty_abort`.
   Mirror the Layer-3' mechanism: record injected/overwritten fields at
   injection time and provide a reader the honesty gate consults.
2. **Hang root cause (secondary, may split out).** Why does
   `test-orchestrator` produce zero model activity for 150s under the
   LangGraph + llama-swap substrate? Suspect co-resident model swap latency
   or a lost stream. The watchdog (SPECHANG2) bounds the damage; it does
   not explain it.

## Acceptance criteria

- [ ] AC-001: a turn where a specialist hangs and the orchestrator injects
      `validation=violation` records does NOT produce a `must_fix` honesty
      discrepancy attributed to the Player; criteria verification proceeds.
- [ ] AC-002: the substrate failure is still surfaced (advisory/should_fix
      issue naming the specialist and the hang), never silently dropped —
      absence of evidence stays absent-signal.
- [ ] AC-003: regression test reproducing the FEAT-C332 run-2 shape:
      synthetic task_work_results with orchestrator-injected violation
      records + honest Player file claims → no `partial_honesty_abort`.
- [ ] AC-004: genuine Player test-claim fabrication (no specialist
      injection in scope) still short-circuits as today.

## Evidence

- Run log: `.guardkit/autobuild/FEAT-C332-run2-stdout.log` (lines ~250-262, ~582)
- Verdicts: `.guardkit/autobuild/FEAT-C332-run2-artifacts-TASK-QAWE-002/coach_turn_{1,2}.json`
- Meta-class rule: `.claude/rules/path-string-mismatch-is-not-dishonesty.md`
- Watchdog prior art: TASK-FIX-SPECHANG2 (`guardkit/orchestrator/specialist_invocations.py:90`)
- Sibling follow-up: TASK-FIX-COACHNARR01 (the narrative misattribution that
  compounded this failure)
