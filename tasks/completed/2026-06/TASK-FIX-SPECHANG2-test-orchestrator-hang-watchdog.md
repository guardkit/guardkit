---
id: TASK-FIX-SPECHANG2
title: Detect test-orchestrator hangs by no-model-activity watchdog (not just the 600s duration cap)
status: completed
task_type: bug
created: 2026-06-07T13:00:00Z
updated: 2026-06-07T15:00:00Z
completed: 2026-06-07T15:00:00Z
completed_location: tasks/completed/2026-06/
previous_state: in_review
state_transition_reason: "All ACs met; quality gates passed (compile, tests 22/22, coverage 85%)"
priority: medium
complexity: 4
effort_hours: 3
deadline: 2026-06-30
parent_review: TASK-REV-AOF-RUN9
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 4
implementation_mode: task-work
intensity: standard
related_tasks:
  - TASK-FIX-SPECHANG   # completed — added the 600s cap; bounded the hang but did not eliminate it
surfaced_in: ../guardkitfactory/docs/reviews/autobuild-migration/TASK-REV-AOF-RUN9-pre-next-run-readiness-review.md
tags:
  - autobuild
  - specialists
  - test-orchestrator
  - substrate-robustness
falsifier: "After landing, a test-orchestrator specialist that stops making model calls (no /v1/responses POST) for > watchdog_seconds is terminated by the watchdog with a distinct 'hang detected (no model activity)' reason BEFORE the blunt 600s duration cap, and the turn proceeds (or fails fast) rather than idling to the cap. Re-running a turn that reproduces the run-9 turn-2 churn no longer wastes ~480s of idle wall-clock."
---

# Task: No-model-activity hang watchdog for the test-orchestrator (anomaly E / R2)

## Why this task exists

`TASK-FIX-SPECHANG` (completed) capped the test-orchestrator at 600s. Run-9 showed
that cap **bounding but not eliminating** the hang:

- **Turn 1:** test-orchestrator made continuous `/v1/responses` model calls and
  **completed in ~240s**.
- **Turn 2** (after the synthetic-feedback 45-file churn): test-orchestrator made
  its **last model call at ~90s, then ZERO model calls for ~480s** until it hit
  the 600s cap and `SDKTimeoutError`d (run-9 L435-456; verified: 0 `httpx` POSTs
  in the 90s→570s window). That is a **genuine agent hang** (stuck polling /
  no-op), not a large-test-surface slowdown.

The blunt duration cap fired correctly but wasted ~480s of idle wall-clock and
returned 0 results. A watchdog keyed on **no model activity** would terminate the
hang far sooner with a clearer signal.

**Scope note (why this is latent, not a pre-run blocker):** the hang was downstream
of the COACHBUDG01 retry storm (synthetic feedback → 45-file churn). With the
reasoning fix landed, turn-1 produces a real verdict and the churn does not recur,
so E is **moot on the turn-1-accept branch** and only bites if a churn/hang turn is
reached. Build it as resilience, not as a gate.

## What to do

1. Add a per-specialist **no-model-activity watchdog**: track the timestamp of the
   last model call (the harness already logs `/v1/responses` POSTs); if the gap
   exceeds `watchdog_seconds` (e.g. 120-180s), terminate with reason
   `hang detected (no model activity for Ns)`, distinct from the duration cap.
2. Keep the 600s duration cap as the outer backstop.
3. Emit both signals to the run log / review summary so future hangs are
   diagnosable at a glance.

## Acceptance criteria

- [x] **AC-1:** Watchdog terminates a no-model-activity specialist before the 600s
  cap, with a distinct reason string.
  - `_run_specialist_with_watchdog` (`guardkit/orchestrator/specialist_invocations.py`)
    races the invocation against a poll loop reading
    `AgentInvoker._last_activity_monotonic` (refreshed per harness event in
    `_invoke_with_role`). On a stale gap it cooperatively cancels
    (`cancellation_event` → in-flight `_cancel_monitor` dispatches
    `harness.cancel()` + SIGTERM) then hard-cancels the task, returning the
    distinct reason `hang detected (no model activity for Ns)`. Default window
    150s (`_TEST_ORCHESTRATOR_NO_ACTIVITY_WATCHDOG_SECONDS`, env-tunable via
    `GUARDKIT_SPECIALIST_WATCHDOG_SECONDS`), well below the 600s cap.
  - Tests: `test_run_specialist_watchdog_terminates_hung_specialist`,
    `test_invoke_test_orchestrator_wires_watchdog` (asserts terminated < 5s
    vs a 10s synthetic hang; distinct reason on the result and the on-disk
    `phase_4` block).
- [x] **AC-2:** A normally-progressing specialist (continuous model calls) is never
  killed by the watchdog (turn-1's ~240s run must still complete).
  - Activity clock is refreshed on every harness event, so a specialist making
    continuous model calls never accrues a 150s silent gap. Test:
    `test_run_specialist_watchdog_allows_progressing_specialist` (refreshes
    activity faster than the window → completes `passed`, no reap).
- [x] **AC-3:** Hang vs cap distinguishable in logs/review summary.
  - Hang: WARNING `... hang detected (no model activity for Ns) — terminating
    before the 600s duration cap` + the same reason string on the failed
    `phase_4` block's `error`. Cap: the existing `SDKTimeoutError: Agent
    invocation exceeded Ns timeout`. Distinct strings, both grep-able.
- [x] **AC-4:** Re-examined whether 600s is the right outer cap for real test
  execution on this substrate (turn-1 evidence: ~240s is adequate).
  - **Decision: keep 600s as the outer backstop.** Turn-1's healthy run was
    ~240s with continuous model calls; 600s gives ~2.5× headroom for a
    legitimately larger suite. The new 150s no-activity watchdog now handles
    the *hang* case far sooner, so the cap no longer needs to be tight to
    bound idle wall-clock — its only remaining job is catching a
    *busy-but-too-slow* run (continuous calls past 600s), for which 240s would
    be too aggressive and risk false-killing a real large suite. Lowering the
    cap is therefore unnecessary and slightly risky; left unchanged. (Per the
    SPECHANG completion note, suites that legitimately need >600s should be
    decomposed at the task level.)

## References

- Review (anomaly E / R2): `../guardkitfactory/docs/reviews/autobuild-migration/TASK-REV-AOF-RUN9-pre-next-run-readiness-review.md`
- SPECHANG (completed): `tasks/completed/2026-06/TASK-FIX-SPECHANG-test-orchestrator-polls-background-bash-until-sdk-timeout.md`
- Run-9 log L431, L435-456 (the hang window)

## Implementation summary

**Approach.** The watchdog reuses the existing cancellation substrate
(`_cancel_monitor` → `harness.cancel()` + SIGTERM) rather than inventing a new
termination path — consistent with `.claude/rules/harness-cancellation-contract.md`
(cancel dispatched through the substrate-agnostic interface; SIGTERM stays as the
SDK escalation, no-op under LangGraph). The hang signal is the *absence* of
harness events: in run-9 turn-2 the specialist produced zero `/v1/responses`
traffic for ~480s, which surfaces as a stale activity clock.

**Code changes:**
- `guardkit/orchestrator/agent_invoker.py`
  - `__init__`: new `self._last_activity_monotonic: float = 0.0`.
  - `_invoke_with_role`: reset the clock at invocation start; refresh it on every
    harness event in the stream loop (one assignment — harmless for Player/Coach,
    read only by the specialist watchdog).
- `guardkit/orchestrator/specialist_invocations.py`
  - `_TEST_ORCHESTRATOR_NO_ACTIVITY_WATCHDOG_SECONDS` (default 150,
    `GUARDKIT_SPECIALIST_WATCHDOG_SECONDS` override) and
    `_WATCHDOG_HANG_REASON_TEMPLATE`.
  - `_no_activity_watchdog_exceeded` (pure predicate, unit-tested),
    `_reap_specialist_processes` (shared reap helper), and
    `_run_specialist_with_watchdog` (the race + cooperative-then-hard cancel).
  - `run_specialist` gains `no_activity_watchdog_seconds`; synthesises a
    cancellation event when none is supplied (so `_cancel_monitor` starts) and
    restores invoker state afterwards. Legacy direct-await path is byte-for-byte
    preserved when the watchdog is disabled.
  - `invoke_test_orchestrator` wires the watchdog (test-orchestrator scope only;
    the 600s cap from SPECHANG stays as the outer backstop).
- `tests/unit/orchestrator/test_specialist_invocations.py`: 5 new tests
  (predicate, hang-fires-distinct-reason, progressing-not-killed,
  synthesised-event-restore, invoke_test_orchestrator wiring).

**Verification.** `tests/unit/orchestrator/test_specialist_invocations.py`:
22 passed (17 pre-existing + 5 new); module line coverage 85% (>80% gate). The 5
failures in `tests/orchestrator/test_specialist_observability.py` are
**pre-existing on baseline** (`module 'asyncio' has no attribute 'timeout'` —
`asyncio.timeout` needs Python 3.11+, the dev venv is 3.10.20; confirmed via
`git stash` baseline, identical failures). Same environmental caveat documented
in the SPECHANG completion note.

**Falsifier status.** Structurally satisfied by unit tests (synthetic 10s hang
terminated in <5s with the distinct reason; progressing run untouched). Empirical
confirmation on a real run-9-style turn-2 reproducer is deferred to the next
canary/AOF batch (same deferral pattern as SPECHANG AC-004/005).
