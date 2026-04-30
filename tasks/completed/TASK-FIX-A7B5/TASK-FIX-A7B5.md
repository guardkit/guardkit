---
id: TASK-FIX-A7B5
title: SDK message-reader transport-noise dedup (rescoped from full investigation)
status: completed
task_type: investigation
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
completed: 2026-04-30T00:00:00Z
completed_location: tasks/completed/TASK-FIX-A7B5/
previous_state: in_review
state_transition_reason: "AC-004 shipped (logger-side dedup filter); AC-001/002/003 deferred to TASK-FIX-A7B7 blocked on TASK-REV-COSE"
priority: low
complexity: 4
dependencies: []
external_reference:
  source_repo: appmilla_github/study-tutor
  reports:
    - /home/richardwoollcott/Projects/appmilla_github/study-tutor/.claude/reviews/TASK-REV-AB7A-report.md
related_tasks:
  - TASK-REV-COSE  # Coach SDK opaque-stderr review — blocker for full root cause
  - TASK-FIX-A7B7  # Follow-up: pin root cause once TASK-REV-COSE lands
  - TASK-FIX-7A09  # Sibling: SDK error-cascade refactor that AC-004 must not undo
related_features: [sdk-adapter, coach-validator]
tags: [sdk, transport, coach, observability, noise-reduction]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: SDK message-reader transport-noise dedup (rescoped from full investigation)

## Rescope summary

The original task asked for full root-cause + disposition + log-level
fix for the upstream `claude_agent_sdk` "Fatal error in message reader:
Command failed with exit code 1" line that fires on every Coach pytest
gate. Investigation found that:

1. **The error originates upstream**, not in guardkit — the literal log
   line is at `claude_agent_sdk/_internal/query.py:308` and the
   underlying `ProcessError` comes from the wrapped `claude` CLI
   subprocess exiting non-zero **after** delivering its result via
   stdout JSON. There is no actual transport breakage.
2. **Root cause is not falsifiable from current logs** — the SDK sets
   `ProcessError.stderr` to a placeholder string; real CLI stderr is
   never captured. Sibling task **TASK-REV-COSE** covers exactly that
   observability gap and must land first.
3. **TASK-FIX-7A09** (sibling SDK error-cascade refactor) deliberately
   chose to surface transport-level failures with structured
   diagnostics rather than swallowing them. Reducing log level **inside
   the fallback path** would partly undo that intent.

**Decision** (with user, 2026-04-30): ship AC-004 as a logger-side
dedup filter at the upstream `claude_agent_sdk._internal.query` boundary
(does not touch TASK-FIX-7A09's structured-error path), and defer
AC-001/002/003 to follow-up **TASK-FIX-A7B7** which depends on
**TASK-REV-COSE**.

Full investigation deferral note:
`docs/reviews/TASK-FIX-A7B5-sdk-message-reader-investigation.md`

## Cross-reference

§4 of `<sibling>/.claude/reviews/TASK-REV-AB7A-report.md`.

## Acceptance Criteria

- [ ] AC-001: Root cause identified with evidence — **deferred to
      TASK-FIX-A7B7**, blocked on TASK-REV-COSE.
- [ ] AC-002: Minimal reproducer captured — **deferred to TASK-FIX-A7B7**,
      blocked on TASK-REV-COSE (synthetic-shim repro is feasible now
      but only reproduces the symptom, not the cause).
- [ ] AC-003: Disposition decided and acted on — **deferred to
      TASK-FIX-A7B7**, blocked on TASK-REV-COSE.
- [x] AC-004: Reduce log-level of "Fatal error in message reader" with
      deduplication. Implemented as a logger-side filter at the upstream
      `claude_agent_sdk._internal.query` logger boundary. First
      occurrence per process is demoted ERROR → WARNING (still visible);
      subsequent occurrences ERROR → DEBUG (silenced under default INFO
      logging). Filter is idempotently installed when `guardkit.orchestrator`
      is imported, so all three SDK call sites (`coach_validator`,
      `task_work_interface`, `agent_invoker`) are covered.

## Files Changed

- `guardkit/orchestrator/sdk_utils.py` — `MessageReaderDedupFilter`
  class + `install_sdk_message_reader_dedup_filter()` idempotent
  installer.
- `guardkit/orchestrator/__init__.py` — calls the installer at package
  import time.
- `tests/unit/test_sdk_message_reader_dedup.py` — 8 unit tests
  (first-match WARNING, subsequent-match DEBUG, unrelated ERROR
  pass-through, install idempotency, end-to-end behaviour through
  caplog).
- `docs/reviews/TASK-FIX-A7B5-sdk-message-reader-investigation.md` —
  investigation deferral note.
- `tasks/backlog/TASK-FIX-A7B7-pin-sdk-message-reader-root-cause.md` —
  follow-up task holding deferred ACs with `depends_on: [TASK-REV-COSE]`.

## Out Of Scope

- Replacing the Claude Agent SDK harness wholesale.
- Refactoring the fallback path itself — only its observability was
  considered, and AC-004 is satisfied at the upstream logger boundary.
- Coach SDK opaque-stderr work (covered by TASK-REV-COSE).
- Full root-cause investigation (deferred to TASK-FIX-A7B7).
