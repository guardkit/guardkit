---
id: TASK-AB-COACHSUBPROC01
title: Make coach test_execution subprocess the default (SDK becomes opt-in)
status: backlog
created: 2026-07-04T09:35:00Z
priority: medium
tags: [autobuild, coach, test-execution, sdk, subprocess, default-flip, masked-infra]
complexity: 3
source: docs/retro/autobuild-retro-xref-2026-07-04.md
---

# Task: Make coach test_execution subprocess the default (SDK becomes opt-in)

> **Implementation in progress 2026-07-04 (same session that filed this task); this
> file is the tracking record.**

## Description

Sourced from the 2026-07-04 retro cross-reference, §5 item 15 (revival of
the borderline call from the 2026-06-17 xref).

The Coach's independent test-execution path defaults to the SDK
(`coach_test_execution: str = "sdk"`, `coach_validator.py:1373`), with a
subprocess fallback. The 2026-06-17 xref judged flipping the default
borderline and did not file it. **This corpus is the recurrence evidence
that settles it**: across the full 153-incident history mined for the
2026-07-04 xref, the SDK parity path failed with the opaque exit-1
**"Fatal error in message reader" on essentially 100% of invocations across
every repo, machine and vintage** (jarvis, forge, study-tutor,
specialist-agent) — never root-caused, always masked by the subprocess
fallback.

That is the "chronic masked infra" pattern named in xref §7: *fallbacks that
keep runs alive hide permanently broken paths. Budget one diagnosis or
change the default; don't let a fallback become the primary path silently.*
The diagnosis has been budgeted repeatedly (TASK-REV-COSE,
TASK-FIX-A7B7 remain open); this task changes the default.

Flip: `coach.test_execution: subprocess` becomes the default; the SDK path
stays in-repo as an explicit opt-in (config/env), mirroring the
`DEFAULT_HARNESS` cutover pattern (one constant, one-line permanent
rollback).

## Acceptance Criteria

- [ ] AC-001: The default for `coach_test_execution` is `"subprocess"`; the
      default lives in ONE place (the `coach_validator.py` constructor
      default and/or a single module constant, mirroring the
      `selector.py::DEFAULT_HARNESS` precedent) so permanent rollback is a
      one-line change.
- [ ] AC-002: The SDK path remains selectable via the existing
      `.guardkit/config.yaml` key (`autobuild.coach.test_execution: sdk`)
      and is NOT removed — opt-in fallback for diagnosis work
      (TASK-REV-COSE / TASK-FIX-A7B7).
- [ ] AC-003: Config docs updated: subprocess documented as default, SDK as
      opt-in with a pointer to the diagnosis tasks and the corpus evidence
      (this xref).
- [ ] AC-004: The `requires_infra`-forces-SDK branch
      (`coach_validator.py:4663`, `:4725-4727`) is reviewed and its
      behaviour under the new default is explicit and tested (it must not
      silently re-select a known-broken path).
- [ ] AC-005: Regression tests: (a) default resolution is subprocess with no
      config; (b) explicit `sdk` config still routes to the SDK path;
      (c) existing subprocess-path timeout/absent-signal semantics
      unchanged.

## Implementation Notes

File:line anchors:

- `guardkit/orchestrator/quality_gates/coach_validator.py:1373` —
  `coach_test_execution: str = "sdk"` (the default to flip); stored at
  `:1454`; consumed at `:4601-4605`, `:4663`, `:4725-4727`.
- Precedent for the flip mechanics:
  `guardkit/orchestrator/harness/selector.py::DEFAULT_HARNESS`
  (TASK-HMIG-011 cutover — default in one place, opt-in revert via
  env/config, old path stays in-repo).
- Evidence: xref §5 item 15 + §7 "Chronic masked infra" (SDK exit-1 "Fatal
  error in message reader", ~100% failure across jarvis, forge, study-tutor,
  specialist-agent; masked by the subprocess fallback every time).
- Related open diagnosis tasks:
  `tasks/backlog/TASK-REV-COSE-diagnose-coach-sdk-test-execution-opaque-stderr.md`,
  `tasks/backlog/TASK-FIX-A7B7-pin-sdk-message-reader-root-cause.md` — this
  task does not close them; it stops the broken path being the default while
  they are open.

## Regression constraints

From xref §5/§6 — load-bearing, verify each before merging:

- **Don't let a fallback become the primary path silently** (§7): the flip
  makes the de-facto primary path the de-jure default — but it must be
  *loud* (documented, one constant), not another silent drift. This is the
  same posture as `.claude/rules/structural-defence-beats-prompt-instruction.md`:
  a deterministic default beats hoping the fallback keeps firing.
- **Tri-state stays tri-state** (§6): the subprocess path's timeout/absent
  handling is governed by
  `.claude/rules/absence-must-survive-every-reconciliation-layer.md`
  (ABFIX-010: a test-oracle timeout arrives at the gate as `None`, never
  `False`). Flipping the default must not touch that chain — the
  `reconciled_absent` / `signal_absent` fingerprints must still match.
- **Glue exclusion from independent tests stays** (§6; TASK-FIX-CC-BDD,
  `coach_validator.py:6740-6822`): the subprocess command construction keeps
  excluding BDD glue — the default flip must not re-route around that
  exclusion.
- **Both Coach paths, deterministically** (§6): whatever executes the tests,
  the deterministic guards downstream (`_reconcile_absent_independent_test_signal`,
  the parity guard, this session's null-evidence guard) apply identically.
- **Keep the SDK path revivable**: mirror the harness-cutover contract — no
  SDK code removal in this task; removal (if ever) is a separate
  post-cutover cleanup with its own review.
