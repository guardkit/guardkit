---
id: TASK-FIX-SPECVIOL01
title: Orchestrator-injected specialist-violation records must not be attributed to Player honesty
task_type: feature
status: completed
created: 2026-06-12T19:50:00Z
updated: 2026-06-13T00:00:00Z
completed: 2026-06-13T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/TASK-FIX-SPECVIOL01/
state_transition_reason: "All quality gates passed; reviewed and completed via /task-complete"
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

- [x] AC-001: a turn where a specialist hangs and the orchestrator injects
      `validation=violation` records does NOT produce a `must_fix` honesty
      discrepancy attributed to the Player; criteria verification proceeds.
- [x] AC-002: the substrate failure is still surfaced (advisory/should_fix
      issue naming the specialist and the hang), never silently dropped —
      absence of evidence stays absent-signal.
- [x] AC-003: regression test reproducing the FEAT-C332 run-2 shape:
      synthetic task_work_results with orchestrator-injected violation
      records + honest Player file claims → no `partial_honesty_abort`.
- [x] AC-004: genuine Player test-claim fabrication (no specialist
      injection in scope) still short-circuits as today.

## Resolution (2026-06-12)

**Corrected root cause.** Forensics on the run-2 artifacts showed the
turn-1 `must_fix` discrepancy did NOT come from the injected
`agent_invocations` records (the honesty checks never read that field).
It fired from the **claim-audit gate**: the Player's honest promise
AC-018 carried `test_file: "tests/orchestrator/test_coach_evidence_bundle.py,
tests/unit/orchestrator/quality_gates/test_coach_validator.py"` — a
comma-joined string of two test files the Player *ran* (both exist,
tracked). `_verify_claims_were_staged` audited the whole string as ONE
path → `Path.exists()` False → "fabricated" → `claim_audit` critical
(exempt from the FFC3 demotion) → `partial_honesty_abort`. The specialist
hang was correlated substrate noise, not the discrepancy's source.

**Fixes** (see `docs/state/TASK-FIX-SPECVIOL01/implementation_plan.md`):

1. `coach_verification.py::_verify_claims_were_staged` — claims are now
   partitioned by provenance: `test_file` entries are **run-claims**
   (comma-split per path), not authored-file claims. A run-claim on an
   existing tracked-unmodified test file emits nothing (zero signal); a
   run-claim on a nonexistent path stays `claim_audit` critical (AC-004).
2. `coach_validator.py::_compute_specialist_failure_advisories` — new
   helper wired into both `gather_evidence` and legacy `validate()`:
   orchestrator-injected `source: "orchestrator"`, `status: "failed"`
   specialist records surface as `should_fix` advisories
   (`category: "specialist_substrate"`) naming the specialist and the
   hang error (AC-002). Benign `skipped` records do not advise.

**Tests:** 4 new unit tests in
`tests/unit/test_coach_verification_claim_audit.py`; 3 regression tests in
`tests/orchestrator/test_specialist_violation_attribution.py` (run-2
reproducer, advisory attribution, AC-004 fabrication preserved). Affected
suites: 335 passed; full `tests/unit`: 7947 passed (7 pre-existing
environment-dependent failures unchanged with/without this fix).

**Hang root cause (half 2)** remains open — substrate question (llama-swap
model-swap latency / lost stream under LangGraph), bounded by the
SPECHANG2 watchdog. Split out if it recurs.

## Evidence

- Run log: `.guardkit/autobuild/FEAT-C332-run2-stdout.log` (lines ~250-262, ~582)
- Verdicts: `.guardkit/autobuild/FEAT-C332-run2-artifacts-TASK-QAWE-002/coach_turn_{1,2}.json`
- Meta-class rule: `.claude/rules/path-string-mismatch-is-not-dishonesty.md`
- Watchdog prior art: TASK-FIX-SPECHANG2 (`guardkit/orchestrator/specialist_invocations.py:90`)
- Sibling follow-up: TASK-FIX-COACHNARR01 (the narrative misattribution that
  compounded this failure)
