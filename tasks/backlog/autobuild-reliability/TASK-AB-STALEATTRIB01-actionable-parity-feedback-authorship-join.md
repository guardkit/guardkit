---
id: TASK-AB-STALEATTRIB01
title: Actionable parity/smoke-gate feedback + authorship join for stale-test attribution
status: backlog
created: 2026-07-04T09:30:00Z
priority: high
tags: [autobuild, runtime-parity, smoke-gate, coach-feedback, stale-tests, attribution]
complexity: 5
source: docs/retro/autobuild-retro-xref-2026-07-04.md
---

# Task: Actionable parity/smoke-gate feedback + authorship join for stale-test attribution

> **Implementation in progress 2026-07-04 (same session that filed this task); this
> file is the tracking record.**

## Description

Sourced from the 2026-07-04 retro cross-reference, §5 items 4+5 (R3 —
study-tutor FEAT-SMP-001 "self-defeating boundary tests + wrong-task
attribution").

The per-task runtime-parity guard worked exactly as designed on SMP-04 — it
correctly red-flagged a failing test — but it **blamed the wrong task, with
unactionable feedback**:

1. The override rationale hardcodes the runs-standalone framing ("the
   deliverable … fix the deliverable so it runs standalone") even when the
   reused `smoke_gates.command` is a **test runner** (`pytest tests/unit`,
   FEAT-SMP-001.yaml:95-101) and the real defect is *a test in the smoke
   suite failed*. The failing-test stderr is buried in
   `issue['details']['stderr_tail']`, which `_extract_feedback`
   (`autobuild.py:6829-6874`) **never surfaces** — the Player was told the
   wrong thing and never shown the failing test's name.
2. **Authorship data exists but is unused:** per-task `files_authored`
   records are already on disk (read by `_wave_authored_files`,
   `feature_orchestrator.py:2401-2443`), but no join is done between the
   failing test's file and the task that authored it. In R3 the failing
   assertion was a stale point-in-time boundary test authored by an
   *earlier* task; the guard fed the failure to the *current* task with no
   way to act on it.

Note the retro's own C6 correction: the "Runtime-parity check FAILED …"
string is emitted only by the **per-task runtime-parity guard**
(`coach_validator.py:3245`; `_gather_runtime_parity` def `:3156`), which
reuses the feature YAML's `smoke_gates.command` via `_per_task_smoke_command`
(`feature_orchestrator.py:3108-3134`). The fix surface is
`agent_invoker._apply_runtime_parity_guard` (`:5574`), not (only)
`_build_smoke_feedback`.

## Acceptance Criteria

- [ ] AC-001: The runtime-parity override issue carries the parity stderr
      tail / parsed failing-test node-IDs in the issue's `test_output` field
      (populated at `agent_invoker.py:5651-5663`), and `_extract_feedback`
      (`autobuild.py:6829-6874`) delivers that content verbatim to the
      Player's next-turn feedback. A regression test asserts the failing
      test's node-ID appears in the extracted feedback text.
- [ ] AC-002: The override rationale is conditional on the smoke command
      shape: when the reused `smoke_gates.command` is a test runner, the
      rationale says "a test in the smoke suite failed" (naming the test),
      not the hardcoded runs-standalone framing. Applied in BOTH surfaces:
      `agent_invoker.py:5641` (per-task parity guard) and
      `_build_smoke_feedback` (`feature_orchestrator.py:2233`, post-wave
      smoke gate).
- [ ] AC-003: Orchestrator-side authorship join: failing-test file paths are
      matched against the per-task `files_authored` records (the data
      `_wave_authored_files`, `feature_orchestrator.py:2401-2443`, already
      reads). When the failing test's file was authored by an EARLIER task
      in the same feature, the feedback says so explicitly.
- [ ] AC-004: When the authorship join attributes the failing test to an
      earlier task, the feedback grants a **narrowly-scoped** permission:
      "you may amend/delete that specific stale assertion — nothing else in
      that file". The permission names the specific test, never the whole
      file or suite.
- [ ] AC-005: Unmatched failing-test paths (no `files_authored` record
      resolves) **fail open** to the current-task framing — no new
      false-red, no suppression, no rerouting of the failure to another
      task's verdict.
- [ ] AC-006: The red signal stays red: the parity/smoke failure still
      overrides approve→feedback exactly as today. This task changes only
      the *content* and *attribution* of the feedback, never the verdict
      direction or the disposition.
- [ ] AC-007: Regression coverage for: test-runner rationale vs
      runs-standalone rationale; authorship-join hit (earlier task);
      authorship-join miss (fail-open); `test_output` surfaced through
      `_extract_feedback`.

## Implementation Notes

File:line anchors from the xref (§3 R3, §5 items 4+5):

- `guardkit/orchestrator/agent_invoker.py:5574` —
  `_apply_runtime_parity_guard` (the guard that fires the override; primary
  fix surface).
- `guardkit/orchestrator/agent_invoker.py:5641` — the hardcoded
  runs-standalone rationale (make conditional).
- `guardkit/orchestrator/agent_invoker.py:5651-5663` — where the override
  issue is built; put the stderr tail / failing node-IDs into `test_output`
  (~2-line core change per the xref).
- `guardkit/orchestrator/autobuild.py:6829-6874` — `_extract_feedback`,
  which carries `test_output` verbatim but never surfaces
  `details['stderr_tail']` (that is why the evidence was invisible).
- `guardkit/orchestrator/feature_orchestrator.py:2233` —
  `_build_smoke_feedback` (post-wave smoke-gate sibling; same conditional
  rationale).
- `guardkit/orchestrator/feature_orchestrator.py:3108-3134` —
  `_per_task_smoke_command` (why the parity guard runs a test suite at all).
- `guardkit/orchestrator/feature_orchestrator.py:2401-2443` —
  `_wave_authored_files` (the existing reader of the per-task
  `files_authored` records the authorship join should reuse).
- `guardkit/orchestrator/quality_gates/coach_validator.py:3156` / `:3245` —
  `_gather_runtime_parity` def / the "Runtime-parity check FAILED" emission.

## Regression constraints

From xref §5/§6 — load-bearing, verify each before merging:

- **L3 parity timeout stays ran-and-failed.** A runtime-parity *timeout* is
  deliberately `ran=True, passed=False` (TASK-AB-COACHRUNPARITY01,
  operator-reaffirmed 2026-06-24; pinned by `test_timeout_is_ran_and_failed`).
  Do NOT flip it to absent while touching this code — see
  `.claude/rules/absence-must-survive-every-reconciliation-layer.md` ("What
  the rule does NOT cover", L3).
- **Fail open on unmatched paths** — the authorship join must never turn a
  path-resolution miss into blame or suppression; this is the
  `.claude/rules/path-string-mismatch-is-not-dishonesty.md` discipline
  (identity-based resolution before path-equality conclusions; unknown paths
  fail open).
- **Feed back, never terminate** — the smoke/parity failure disposition
  (bounded `seed_feedback`, replace-not-append `wave_results[-1]`, C1
  mark-gating) is untouched; see
  `.claude/rules/smoke-gate-is-feedback-not-terminator.md`.
- **Do NOT reroute or suppress the failure** (xref §5 item 5). The stale
  assertion permission is a *content* affordance in the feedback, not a
  verdict change — `.claude/rules/absence-of-failure-is-not-success.md`
  forbids converting this red into a green.
- **Deterministic overrides re-persist to disk** — the parity guard's
  approve→feedback override must keep re-writing `coach_turn_N.json`
  (`.claude/rules/deterministic-verdict-override-must-persist-to-disk.md`);
  changing the issue payload must not drop the persist.
- **A7B2 overlap-forces-feedback veto and the contention amnesty are
  load-bearing** (§6) — do not widen the amnesty to auto-approve while
  improving attribution.
- The companion transient-assertion guidance is TASK-AB-INVARIANTTEST01;
  this task's authorship join doubles as the monitor for when that prompt
  guidance is ignored (xref §5 item 13).
