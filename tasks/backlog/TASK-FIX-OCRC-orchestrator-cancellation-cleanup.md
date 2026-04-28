---
id: TASK-FIX-OCRC
title: Fix orchestrator cancellation residual cleanup — atomic _clean_state + replay-vs-execute disambiguation
status: backlog
task_type: feature
created: 2026-04-28T13:10:00Z
updated: 2026-04-28T13:10:00Z
priority: low
post_demo: true
tags: [autobuild, orchestrator-hygiene, cancellation, observability, post-demo, FEAT-ABSR-9C6E-related]
complexity: 4
estimated_effort_days: 1.5
parent_review: TASK-REV-OCRC
related_reviews:
  - TASK-REV-OCRC  # Triage report; verdict: real-bug-confirmed
  - TASK-REV-WORS  # Originally surfaced this as a sidequest (events.jsonl §3.3)
related_features:
  - FEAT-ABSR-9C6E  # Sibling post-demo work item alongside CMPL/WTKS
implementation_mode: task-work
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Fix orchestrator cancellation residual cleanup

## Description

Two coupled defects in the autobuild feature orchestrator, plus an
unconfirmed orphan-START hygiene issue. Filed by [TASK-REV-OCRC quick
triage](../in_review/TASK-REV-OCRC-orchestrator-cancellation-residual-cleanup.md);
full evidence and fix sketches in
[`.claude/reviews/TASK-REV-OCRC-report.md`](../../.claude/reviews/TASK-REV-OCRC-report.md).

**Symptom**: Cancelling a `--fresh` autobuild mid-clear with Ctrl-C
produces:

1. `Player failed: Unexpected error: Task TASK-J004-013 not found in any state`
   on the next invocation, AND
2. A misleading 80 ms cluster of `WaveCompletedEvent` records in
   `events.jsonl` (e.g. `jarvis/.guardkit/autobuild/FEAT-J004-702C/events.jsonl`
   lines 45-48), each claiming a wave completed N tasks in zero time —
   indistinguishable in shape from a genuinely-executed wave, distinguishable
   only by the impossible timestamp delta.

**Root causes**:

- **Defect 1 — Non-atomic `_clean_state`**:
  `feature_orchestrator.py:1628-1631`. `FeatureLoader.reset_state()` mutates
  the in-memory `Feature` object, then `FeatureLoader.save_feature()` persists.
  These are separate calls. Ctrl-C between them leaves the on-disk YAML
  recording the prior run's `completed_waves=[1, 2, 3, 4]` while the in-memory
  copy is reset. Next invocation reads the stale YAML.

- **Defect 2 — `WaveCompletedEvent` always emits, even for fully replayed
  waves**: `feature_orchestrator.py:2293-2321`. When every task in a wave has
  `status=="completed"` (typical resume case), `_execute_wave_parallel`
  returns synthetic `success=True` results with `final_decision="already_completed"`.
  `_execute_wave` then emits a `WaveCompletedEvent` with `tasks_completed=N`,
  `task_failures=0`, no rate-limit signal — identical in shape to a real
  execution event. Observability tools that read `events.jsonl` cannot
  distinguish replay from execution without inspecting timestamp deltas.

- **Defect 3 (lower confidence) — Orphan player START emission**: Line 49 of
  the same `events.jsonl` shows a `TASK-J004-013` START with no matching END
  and `feature_id=null`. Two plausible sources (leaked subprocess vs
  stale-state-driven re-emit); needs a reproducer to pin down. Likely shares
  a fix with Defect 1 once the stale-state vector is closed.

## Acceptance Criteria

### Defect 1 — Atomic `_clean_state`

- [ ] AC-001: `_clean_state` is atomic with respect to `KeyboardInterrupt`. A
      Ctrl-C anywhere between the start and end of `_clean_state` either
      leaves the persisted YAML in a fully-pre-clean state OR a fully-clean
      state — never an intermediate state.
- [ ] AC-002: Implementation prefers a structural fix (persist-first ordering
      with a fresh `Feature` instance, OR commit-on-write semantics) over
      signal-masking. Rationale: structural is more testable and less
      platform-fragile (see report §4 Fix 1, option (a) preferred over (b)).
- [ ] AC-003: A test simulates `KeyboardInterrupt` raised inside `reset_state`
      and verifies the on-disk YAML is unchanged from before `_clean_state`
      was called. (Not a flaky timing test — use a mock that raises
      synchronously.)
- [ ] AC-004: A second test simulates `KeyboardInterrupt` raised inside
      `save_feature` (or whatever the post-fix critical-section call is) and
      verifies the on-disk YAML is fully reset. Together with AC-003, these
      pin down the atomicity invariant from both sides.

### Defect 2 — Replay vs execute disambiguation

- [ ] AC-005: When a wave consists entirely of tasks with
      `final_decision == "already_completed"`, the emitted event makes the
      replay status machine-readable. Two acceptable shapes:
      (a) `WaveCompletedEvent` gains a `replay: bool` field, OR
      (b) A dedicated `WaveSkippedEvent` (or `WaveReplayedEvent`) is emitted
      instead. Either is fine; pick whichever fits the existing
      `instrumentation/schemas.py` style.
- [ ] AC-006: Mixed waves (some real execution, some replay) emit a single
      event whose semantics are unambiguous: either the replay flag is per-task
      not per-wave (preferred), OR the wave-level event reports counts
      separately for `tasks_executed` vs `tasks_replayed`. Pick one explicitly
      and document the choice in the schema docstring.
- [ ] AC-007: Downstream consumers in `instrumentation/concurrency.py`
      (specifically `ConcurrencyController.on_wave_completed`) ignore replayed
      waves rather than feeding their zero-latency artificial datapoints into
      worker-count adaptation logic. Verify with a unit test that a fully-replayed
      wave does not trigger `action="reduce"` or `action="increase"`.
- [ ] AC-008: An events.jsonl reader (or the equivalent dashboard if any)
      can distinguish replay from execution by reading a single field, without
      timestamp-delta heuristics.

### Defect 3 — Orphan player START investigation (lower priority within this task)

- [ ] AC-009: Reproducer runbook documented (5-10 min): steps to reliably
      produce orphan player START events via cancelled `--fresh`. Likely
      sequence:
      1. `guardkit autobuild feature FEAT-X --fresh` (against a fixture
         with completed_waves > 0)
      2. Ctrl-C immediately after the "[yellow]⚠[/yellow] Clearing previous
         incomplete state" line appears
      3. `guardkit autobuild feature FEAT-X --fresh` (or `--resume`) again
      4. Inspect `events.jsonl` for orphan player START records
      Document outcome: reproducible Y/N, and which hypothesis (leaked
      subprocess vs stale-state-driven re-emit) is supported by stderr/stdout.
- [ ] AC-010: If the orphan-START source is closed by Defect 1's fix
      (hypothesis (b) in the triage report), regression test pinning the
      reproducer is added. If not closed by Defect 1, file a separate task
      with the runbook output and downscope this AC to "investigation
      complete, follow-up filed".

### Cross-cutting

- [ ] AC-011: Existing autobuild tests continue to pass.
- [ ] AC-012: A standalone integration smoke check (≤5 min runtime) verifies
      that a clean `--fresh → cancel → --fresh` cycle now leaves a coherent
      `events.jsonl` (no orphan STARTs, no zero-latency `WaveCompletedEvent`s
      that look like real executions).

## Source artefacts

- [TASK-REV-OCRC review report](../../.claude/reviews/TASK-REV-OCRC-report.md) — full diagnostic
- [TASK-REV-WORS report v2 §3.3](../../.claude/reviews/TASK-REV-WORS-report.md#33-the-orphan-j004-013-start-at-075008-bug-to-file-as-sidequest) — origin
- `jarvis/.guardkit/autobuild/FEAT-J004-702C/events.jsonl` (lines 44-53) — primary evidence
- User-reported terminal log: `Player failed: Unexpected error: Task TASK-J004-013 not found in any state`

## Implementation Notes

### Files likely to change

- `guardkit/orchestrator/feature_orchestrator.py` — `_clean_state`
  (lines 1597-1631), `_execute_wave` event emission (lines 2293-2321),
  `_emit_wave_completed` (lines 2334-2394).
- `guardkit/orchestrator/feature_loader.py` — `reset_state` (lines 1275-1295);
  may need a new `clean_and_save_atomic()` helper if going with the
  persist-first restructure.
- `guardkit/orchestrator/instrumentation/schemas.py` — `WaveCompletedEvent`
  schema (line 284) gains `replay` field, OR new `WaveSkippedEvent` class
  added; plus updates to `__all__` (line 368).
- `guardkit/orchestrator/instrumentation/concurrency.py` — adaptation logic
  (lines 104-185) gains a "skip if replayed" guard.
- `guardkit/tasks/state_bridge.py` — likely no change; the
  `TaskNotFoundError` at line 312 is a *symptom* of Defect 1, not a separate
  defect. Confirm during implementation.

### Design-phase notes from the user (carry into Phase 2 design)

These four caveats anchored the [I]mplement decision and should be reflected
in the design plan:

1. **Diagnosis is solid; sketches are concrete enough for `/task-work --design-only`
   to produce a workable plan immediately.** No additional spike needed before
   design phase.
2. **The two coupled defects belong in one task.** They share call sites
   (`_clean_state` → `_execute_wave_parallel` → wave event emission) and a
   shared call-site audit. Splitting would duplicate the audit and risk
   lock-step regressions.
3. **Filing is cheap, retrieval is the win.** This task lives in the post-demo
   backlog alongside CMPL/WTKS so future-you doesn't lose the diagnostic
   context that's freshest now.
4. **POST-DEMO-RESUMPTION-NOTES.md anchors this task** for the
   demo-aftermath sprint. Keep that anchor in sync if the task ID changes.

### Sequencing relative to FEAT-ABSR-9C6E post-demo work

Per [POST-DEMO-RESUMPTION-NOTES.md](autobuild-stall-resilience/POST-DEMO-RESUMPTION-NOTES.md),
the recommended order on the post-demo sprint is:

1. TASK-ABSR-CMPL (high — Phase-2.5 effective-complexity heuristic)
2. TASK-ABSR-WTKS Phase 1 (medium — pre-Phase-4 consistency check)
3. TASK-ABSR-WTKS Phase 2 (medium — per-task subworktrees)
4. **TASK-FIX-OCRC (low — this task)** — independent track; can run alongside
   any of the above without code conflict (touches `_clean_state` and event
   schemas; WTKS touches worktree-creation semantics).

WTKS Phase 2 may slightly interact with Defect 1 (per-task subworktree
cleanup is a sibling concern to feature-level state cleanup); confirm the
interaction during this task's design phase if WTKS Phase 2 has shipped first.

### Why low priority

- **Not demo-blocking.** Validated by jarvis FEAT-J004-702C run-4 (20/20
  tasks, 100% success). The `_clean_state` race is only triggered by manual
  Ctrl-C during a rare window; not on the demo path.
- **Defect 2 affects only observability** (event journal readability), not
  correctness. The orchestrator's adaptation logic in `concurrency.py` does
  feed off `WaveCompletedEvent`, so there *is* a small correctness exposure
  via AC-007, but no production incident has been traced to it.
- **Defect 3** is a hygiene concern with no known production impact.

## Out of scope

- Full rewrite of `_clean_state` semantics (e.g. transactional state machine,
  WAL-style journal). Atomicity for the Ctrl-C window is sufficient.
- Anything in the orchestrator outside the cancellation/replay path (per
  TASK-REV-OCRC scope).
- Wave-4 failure mode investigation (covered by TASK-REV-WORS).
- Coach SDK opaque-stderr (covered by TASK-REV-COSE).
- Demo-blocking work — explicitly post-demo only.

## Estimate

**1-2 days** for an experienced engineer with autobuild orchestrator
familiarity, broken down approximately:

- Design phase (Phase 2 + 2.5): 2-3 hours
- Defect 1 fix + tests: 3-4 hours
- Defect 2 schema change + downstream concurrency.py guard + tests: 3-4 hours
- Defect 3 reproducer runbook + (if applicable) regression test: 1-2 hours
- Integration smoke (AC-012): 1 hour
- Code review + iteration: 2-3 hours

Buffer absorbed in the 1-2 day range; no need for finer-grained estimation
given the post-demo priority.
