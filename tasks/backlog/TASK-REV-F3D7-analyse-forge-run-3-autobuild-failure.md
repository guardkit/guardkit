---
id: TASK-REV-F3D7
title: Analyse forge-run-3 autobuild failure after stall-resilience fixes
status: review_complete
created: 2026-04-24T18:00:00Z
updated: 2026-04-24T18:45:00Z
priority: high
task_type: review
decision_required: true
tags: [autobuild, review, stall-analysis, forge, post-fix-regression, code-review, decision-point]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: architectural
  depth: deep
  decision: implement
  findings_count: 4
  recommendations_count: 6
  root_cause_class: code
  report_path: docs/reviews/bdd-acceptance-wired-up/forge-run-3-analysis.md
  completed_at: 2026-04-24T18:45:00Z
  implementation_bundle: recommended
  implementation_feature_id: FEAT-F3D7
  implementation_tasks:
    - TASK-FIX-7A08
    - TASK-FIX-7A09
    - TASK-FIX-7A0A
---

# Task: Analyse forge-run-3 autobuild failure after stall-resilience fixes

## Description

AutoBuild run **FEAT-FORGE-002 (NATS Fleet Integration)** was re-executed after
landing all seven subtasks of `autobuild-sdk-stall-resilience/IMPLEMENTATION-GUIDE.md`
(TASK-FIX-7A01 → TASK-FIX-7A07). Those fixes were intended to resolve the
Player-invocation stall and Coach-agent-invocations stall that previous runs
exhibited.

**Despite the fixes, the feature still fails.** The captured transcript is at
[docs/reviews/bdd-acceptance-wired-up/forge-run-3.md](docs/reviews/bdd-acceptance-wired-up/forge-run-3.md).

### Outcome summary (from the transcript)

| Task | Result | Turns | Decision |
|------|--------|-------|----------|
| TASK-NFI-001 | ✓ SUCCESS | 1 | approved (conditional — collection_error) |
| TASK-NFI-002 | ✓ SUCCESS | 1 | approved (conditional — collection_error) |
| TASK-NFI-003 | ✗ FAILED | 3 | `unrecoverable_stall` (coach_agent_invocations_stall; missing phases 4, 5) |
| TASK-NFI-006 | ✓ SUCCESS | 1 | approved |
| TASK-NFI-007 | ✗ FAILED | 3 | `unrecoverable_stall` (coach_agent_invocations_stall; missing phases 3, 5) |
| Wave 2 | ✗ FAILED | — | stopped execution; 3/11 tasks completed |

### What the fixes *did* deliver (evidence from the transcript)

1. The new `coach_agent_invocations_stall` classifier (TASK-FIX-7A07) fires
   correctly, with enriched remediation text pointing at required specialists
   (`test-orchestrator`, `code-reviewer`, stack-specific Phase-3) and offering
   `implementation_mode: direct` as escape hatch (forge-run-3.md:1098-1109,
   1192-1205).
2. `implementation_mode: direct` works for declarative tasks (TASK-NFI-001/002).
3. Conditional-approval path fires when Coach independent tests hit
   `collection_error` with Docker available + all gates passing (lines 227-229,
   297-299).
4. Coach pytest interpreter is wired to bootstrap venv (TASK-FIX-7A05,
   line 90, 352).

### What the fixes did *not* deliver (the failure signal)

1. **Player still does not invoke the required specialists via the Task tool**
   for `task-work` mode tasks (TASK-NFI-003 and TASK-NFI-007). Three turns of
   `task_work_results.json → agent_invocations_validation` report "1 of 3
   required agent invocations" — Player completes inline. This is the
   *behavioural* failure mode that TASK-FIX-7A07 only *classifies*; the
   remediation text explicitly cites TASK-FIX-7A08 which is **not present in
   the IMPLEMENTATION-GUIDE.md** (forge-run-3.md:1104).
2. **`claude_agent_sdk` subprocess still fails with exit code 1** during
   Coach independent-test SDK path (lines 218-223, 288-293, 727-729), triggering
   fallback to subprocess pytest which then hits `collection_error`. The
   TASK-FIX-7A03 defensive stream handling evidently did not address this class
   of stream failure, or the failure is downstream of message parsing.
3. **Environment bootstrap gate (TASK-FIX-7A04) did not block** the initial
   Wave 1 execution despite pyproject requiring `python >= 3.13` and
   `nats-core>=0.2.0` being unavailable from the configured index
   (lines 59-62, 87). The run proceeded on the system interpreter
   (`/usr/bin/python3`) with partial venv bootstrap — the very scenario
   TASK-FIX-7A04's hard-fail gate was intended to prevent. Either the default
   `bootstrap_failure_mode: warn` absorbed the failure, or the JMBP-E
   `requires-python` pre-check didn't fire.
4. **Context pollution stall co-fires** (`context_pollution_stall_no_checkpoint`)
   because the Player writes progressively more modified files across turns
   (6→49→55 for NFI-007; 37→44→52 for NFI-003) without the agent-invocations
   gate ever letting a turn pass — so no checkpoint is ever created, and the
   rollback-on-pollution safety net cannot engage.

## Why this is a review task, not a /task-work

The transcript exposes **at least four distinct hypothesis classes** for why
the fixes did not rescue this run — each implies a different follow-up task
(or bundle of tasks), and prematurely committing to one would mis-scope the
remediation:

1. **Missing subtask** — TASK-FIX-7A08 (Player system-prompt mandates
   Task-tool invocation) was promised by the classifier's remediation text but
   is not in the IMPLEMENTATION-GUIDE.md. Was it dropped from the plan, or is
   it live elsewhere?
2. **Bootstrap gate configuration drift** — Did TASK-FIX-7A04 land with the
   intended default, or was the default flipped to `warn` + the JMBP-E
   requires-python pre-check silently disabled?
3. **SDK stream handling completeness** — TASK-FIX-7A03's stream-level
   try/except evidently doesn't protect the Coach independent-test path. Is
   the SDK `_internal.query` exit-code-1 a different failure shape (e.g.,
   transport-level, pre-message) that 7A03 was never designed to catch?
4. **Anti-fraud posture / strictness vs. direct-mode guidance** — The
   classifier now tells the operator to flip to `implementation_mode: direct`
   as remediation, but offers no affordance for the orchestrator to auto-
   downgrade (with logging) when a wave is on its Nth retry with the same
   missing-phases signature. Is that a policy gap worth filing, or intentional?

A review pass is the right shape here: one agent reads the full transcript
against the IMPLEMENTATION-GUIDE acceptance criteria, categorises each
observed failure against the four hypothesis classes above, names the
smallest-footprint remediation set, and produces a ranked task list for
`/task-review [I]mplement` to spin up.

## Acceptance Criteria

- [ ] Full traversal of `forge-run-3.md` producing a timeline of every error,
      warning, rejection, and stall event (line numbers cited).
- [ ] Each of the seven IMPLEMENTATION-GUIDE subtasks (7A01–7A07) evaluated
      for whether its gate observably fired in this run: **fired**, **did not
      fire but should have**, **fired correctly**, or **not exercised by this
      scenario**.
- [ ] The four hypothesis classes above (missing 7A08 / bootstrap gate drift /
      SDK stream completeness / anti-fraud-vs-direct-mode policy) each marked
      as confirmed / refuted / partial with citations from the transcript and
      the current `guardkit/orchestrator/autobuild.py`,
      `agent_invoker.py`, `coach_validator.py`, `environment_bootstrap.py`,
      `feature_orchestrator.py`.
- [ ] Explicit verdict on whether the IMPLEMENTATION-GUIDE.md's Feature-Level
      Verification (§ "Feature-Level Verification", points 1–3) ever ran, and
      if so what evidence exists.
- [ ] Ranked recommendation: minimal set of follow-up tasks (0–N) to close the
      gap, each sized (complexity 1–10) and tagged with the hypothesis class
      it resolves.
- [ ] A decision checkpoint clearly stated: [A]ccept findings as-is, [I]mplement
      the recommended remediation set, [R]evise (deeper analysis of a specific
      hypothesis class), [C]ancel (run was non-representative — e.g., GB10 env
      drift — rerun first).
- [ ] Review captures whether the root cause is *code* (a fix was not
      actually implemented or landed broken) vs. *configuration* (the fix is
      live but the defaults/flags in this environment neutralised it) vs.
      *scope* (the fix class was not intended to cover this failure mode).
- [ ] Review report saved under
      `docs/reviews/bdd-acceptance-wired-up/forge-run-3-analysis.md` (or
      equivalent canonical location).

## Key References

- **Transcript under review**:
  [docs/reviews/bdd-acceptance-wired-up/forge-run-3.md](docs/reviews/bdd-acceptance-wired-up/forge-run-3.md)
- **Implementation guide that was supposed to fix this**:
  [tasks/backlog/autobuild-sdk-stall-resilience/IMPLEMENTATION-GUIDE.md](tasks/backlog/autobuild-sdk-stall-resilience/IMPLEMENTATION-GUIDE.md)
- **Prior forge runs (for comparison — the fixes were derived from these)**:
  - `docs/reviews/bdd-acceptance-wired-up/forge-run-1.md`
  - `docs/reviews/bdd-acceptance-wired-up/forge-run-2.md`
- **Orchestrator code likely in scope**:
  - `guardkit/orchestrator/autobuild.py` (classifier, stall-detector, summary)
  - `guardkit/orchestrator/agent_invoker.py` (SDK invocation, timeouts)
  - `guardkit/orchestrator/quality_gates/coach_validator.py`
    (agent-invocations gate, SDK test path, subprocess fallback)
  - `guardkit/orchestrator/environment_bootstrap.py` (bootstrap gate)
  - `guardkit/orchestrator/feature_orchestrator.py` (wave orchestration,
    bootstrap-failure-mode)
- **Related runbook**:
  [docs/guides/autobuild-instrumentation-guide.md](docs/guides/autobuild-instrumentation-guide.md#if-autobuild-stalls-immediately)

## Notes

- User reported this result with a "sad face" — the fixes landed but the run
  still fails. Framing for the review: *not* "did 7A01–7A07 ship?" (they did),
  but "what did we fail to fix that we should have, and what minimum
  additional work closes the gap?"
- The transcript explicitly names `TASK-FIX-7A08` as the remediation path
  (lines 1104, 1198) — **confirm whether that task ID exists in the repo**
  before recommending new work; it may be the single missing piece.
- Conditional-approval behavior on Wave 1 (approving despite
  `collection_error` on independent verification) is *designed* per
  Graphiti's `conditional_approval` rule, but worth flagging: approving a
  task whose independent tests could not be collected is load-bearing on the
  Player's own test results being truthful.

---

## Next Steps

1. Execute review: `/task-review TASK-REV-F3D7 --mode=architectural --depth=deep`
2. At the checkpoint, choose [A]/[I]/[R]/[C] based on findings.
3. If [I]mplement, the review will spawn sized follow-up tasks that can be
   bundled (or not) with any outstanding items from the original
   `autobuild-sdk-stall-resilience` feature.
4. Complete: `/task-complete TASK-REV-F3D7`
