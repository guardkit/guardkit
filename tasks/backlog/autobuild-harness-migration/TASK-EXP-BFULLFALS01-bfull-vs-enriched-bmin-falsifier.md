---
id: TASK-EXP-BFULLFALS01
title: B-full vs enriched-B-min bug-catching falsifier + decision note
status: backlog
task_type: ops
created: 2026-06-11T00:00:00Z
updated: 2026-06-11T00:00:00Z
priority: high
complexity: 3
effort_hours: 4
parent_feature: autobuild-harness-migration
related: [TASK-OPS-COACHMOE01, TASK-ARCH-COACHSMOKE01, TASK-ARCH-COACHBFULL, TASK-PERF-COACHSYNTH]
depends_on:
  - TASK-OPS-COACHMOE01     # run the falsifier on whichever Coach substrate wins
implementation_mode: manual
intensity: standard
falsifier: "Inject a known mechanical bug (the run-23 TypeError class or the FEAT-9DDE import-path class) into a fixture task. Run (a) B-min with the enriched evidence bundle and (b) B-full with recursion_limit raised to ~25 + resident Coach. The experiment PASSES if it produces a recorded decision either way; the B-full PATH passes only if it catches a bug that enriched-B-min misses."
---

# Task: Decide B-full's fate with evidence, not by default (retro #2)

## Why this task exists

B-full (the Phase-A tool-using investigation) currently degrades **100% of the
time** at `recursion_limit=12` and is default-OFF
(`GUARDKIT_COACH_GATHER`, `agent_invoker.py:571-584`) — so `recursion_limit=12`
is deciding the architecture by default. The retro
(`docs/retro/coach-arc-journey-and-state-2026-06-11.md` §5 #1-2, §9 #2) demands
a deliberate decision with a falsifier. The evidence so far leans hard toward
dropping it:

- Every bug actually caught has been **mechanical** (run-23 `TypeError`;
  FEAT-9DDE `ModuleNotFoundError`) and deterministic checks caught them cheaper
  (smoke gate ~1s vs the 13–42 min gathers of runs 21–23).
- B-full's only unique win (run-23) cost a 41m43s turn that exhausted the
  budget before the fix turn.
- DeepAgents' fixed 170k-token summarization trigger exceeds gemma4:31b's 98k
  window (Graphiti `666820cb`), so long B-full investigations on g31 can't even
  rely on mid-flight summarization.
- Run-25's "equivalent verdict quality" claim rests on criteria_verification
  *structure*, not adjudicated content — this experiment is also the first
  content-level comparison.

## Spec

1. Build (or reuse) a **known-buggy fixture task**: unit tests green, deliverable
   broken (the FEAT-9DDE divergence class), plus one run-23-style runtime
   `TypeError` variant.
2. **Arm A — enriched B-min**: `GUARDKIT_COACH_GATHER=0`, evidence bundle
   including the smoke leg (TASK-ARCH-COACHSMOKE01; if not yet landed, inject
   smoke results into the bundle by hand for the experiment).
3. **Arm B — B-full, actually allowed to run**: `GUARDKIT_COACH_GATHER=1`,
   `GUARDKIT_COACH_GATHER_RECURSION_LIMIT=25` (run-25 README suggestion),
   Coach resident, generous task timeout so the gather can converge.
4. Score each arm: did the Coach verdict surface the injected bug as
   `must_fix` feedback? At what wall-time? With what `criteria_verification`
   content quality?
5. Write the **decision note** (`docs/decisions/` or `.claude/reviews/`):
   - Enriched-B-min catches ⇒ **drop B-full**: keep `GUARDKIT_COACH_GATHER`
     default 0, delete or quarantine the dead gather path, close the retro §5
     question.
   - Only B-full catches ⇒ invest: raise the default recursion limit, budget a
     resident Coach, and re-scope COACHTURNBUDGET so a gather turn fits ≤50%
     of budget.
6. Capture the outcome in Graphiti (`guardkit__project_decisions`) with edges
   to the absence-of-failure rule cluster.

## Acceptance Criteria

- [ ] **AC-001** — Both arms executed against the same injected-bug fixtures on
      the substrate chosen by TASK-OPS-COACHMOE01.
- [ ] **AC-002** — Catch/miss + wall-time + verdict-content table recorded.
- [ ] **AC-003** — Decision note written and linked from the retro's successor
      doc; Graphiti decision captured.
- [ ] **AC-004** — The losing path's default state made explicit in code/docs
      (no half-on state left behind).

## References

- Retro: `docs/retro/coach-arc-journey-and-state-2026-06-11.md` §5, §7 #2, §9 #2
- B-full wiring + degrade: `guardkit/orchestrator/agent_invoker.py:2296-2418`
- Run-23 (the one B-full catch): `docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-23.md`
- Run-25 recursion-raise suggestion: `docs/state/TASK-REV-HMIG/run-25-artifacts/README.md:197-206`
