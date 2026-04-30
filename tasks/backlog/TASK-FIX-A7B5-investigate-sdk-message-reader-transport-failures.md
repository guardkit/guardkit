---
id: TASK-FIX-A7B5
title: Investigate Claude Agent SDK `Fatal error in message reader` transport failures during Coach pytest gates
status: backlog
task_type: investigation
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
priority: low
complexity: 4
dependencies: []
external_reference:
  source_repo: appmilla_github/study-tutor
  reports:
    - /home/richardwoollcott/Projects/appmilla_github/study-tutor/.claude/reviews/TASK-REV-AB7A-report.md
related_tasks:
  - TASK-REV-COSE  # Coach SDK opaque-stderr review (related observability concern)
related_features: [sdk-adapter, coach-validator]
tags: [sdk, transport, coach, observability, noise-reduction]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Investigate `Fatal error in message reader` SDK transport failures during Coach pytest gates

## Description

During every Coach SDK pytest gate observed in the FEAT-70A4 run (sibling
study-tutor repo), the message reader subprocess crashes with:

```
Fatal error in message reader: Command failed with exit code 1
```

The orchestrator then falls back to direct subprocess execution (see the
fallback path in `guardkit/orchestrator/quality_gates/coach_validator.py`).
The fallback **always succeeds**, so this is non-blocking — but the noise
is high (5 occurrences in a 27-minute run, one per Coach gate) and
indicates an unaddressed transport defect in the Claude Agent SDK
harness.

Plausible classifications to triage during the investigation:

- Pipe / IPC issue between parent and SDK message-reader subprocess
- File-descriptor limit interaction (FD exhaustion under parallel waves)
- Environment-variable leak / mismatch between parent and child
- Protocol-version skew between guardkit's SDK adapter and a recent
  Claude Agent SDK release
- A specific stdout/stderr framing edge case the reader doesn't tolerate

## Cross-reference

§4 of `<sibling>/.claude/reviews/TASK-REV-AB7A-report.md`.

## Acceptance Criteria

- [ ] AC-001: Root cause identified with evidence (logs, strace, or
      reproduction script — whichever pins it down). Document the
      classification (IPC / FD / env / protocol / framing / other).
- [ ] AC-002: A minimal reproducer is captured. Either a unit-style
      harness in `tests/` or a standalone script under
      `docs/reviews/sdk-message-reader/` (or wherever similar SDK
      investigations land — audit for precedent).
- [ ] AC-003: Disposition decided and acted on:
      (a) Fix in guardkit's SDK adapter if the bug is on guardkit's
          side of the contract, OR
      (b) File upstream against the Claude Agent SDK with the minimal
          repro and a clear classification, AND add a tracking comment
          / ticket reference in the guardkit code so future readers
          know the fallback noise is by-design pending upstream fix.
- [ ] AC-004: If filed upstream, also reduce the log-level of the
      fallback-path "Fatal error in message reader" line from whatever
      it currently emits at to `WARNING` or `INFO` with deduplication
      (e.g. log first occurrence per run at WARNING, subsequent at
      DEBUG) — so the noise stops dominating Coach run output until the
      upstream fix lands.

## Files Likely To Change

- `guardkit/orchestrator/quality_gates/coach_validator.py` — the
  fallback path that catches the transport failure. Search for
  `message reader` or the literal error string.
- Possibly `guardkit/orchestrator/agent_invoker.py` if the SDK harness
  lives there.
- A new investigation note under `docs/reviews/` capturing the
  classification and minimal repro.

## Out Of Scope

- Replacing the Claude Agent SDK harness wholesale.
- Refactoring the fallback path itself — only its observability is in
  scope until root cause is known.
- Coach SDK opaque-stderr work (covered by TASK-REV-COSE).
