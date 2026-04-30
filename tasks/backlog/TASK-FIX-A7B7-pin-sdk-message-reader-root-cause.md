---
id: TASK-FIX-A7B7
title: Pin Claude Agent SDK message-reader root cause once TASK-REV-COSE lands real CLI stderr
status: backlog
task_type: investigation
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
priority: low
complexity: 4
dependencies:
  - TASK-REV-COSE
related_tasks:
  - TASK-FIX-A7B5  # parent — investigation kicked off, AC-004 (log dedup) shipped
  - TASK-REV-COSE  # blocker — real CLI stderr capture
related_features: [sdk-adapter, coach-validator]
tags: [sdk, transport, coach, observability, deferred]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Pin Claude Agent SDK message-reader root cause (deferred from TASK-FIX-A7B5)

## Description

TASK-FIX-A7B5 investigated the upstream `claude_agent_sdk` "Fatal error
in message reader: Command failed with exit code 1" log line that fires
on every Coach pytest gate. AC-004 (log-noise dedup) was shipped at the
`claude_agent_sdk._internal.query` logger boundary — see
`docs/reviews/TASK-FIX-A7B5-sdk-message-reader-investigation.md`.

The remaining ACs (root cause + minimal repro + disposition) require
real CLI stderr to be falsifiable. Until TASK-REV-COSE lands stderr
capture in `coach_validator`'s SDK dispatch, hypothesis ranking can't
be promoted to evidence-backed classification.

This task picks up where A7B5 left off, **once TASK-REV-COSE is in**.

## Top hypothesis (carried forward from A7B5 investigation)

CLI exit-code semantics: `claude` CLI exits non-zero after delivering
its result, possibly because Coach's `max_turns=1` + single-`Bash`-tool
option pattern terminates the agent loop in a way the CLI interprets as
a non-clean exit. Pattern matches: deterministic firing once per Coach
gate, JSON delivered cleanly before the error.

Secondary hypothesis: stdin-close race — SDK closes stdin to CLI
before CLI writes its final result/control message.

## Acceptance Criteria

- [ ] AC-001: Root cause identified with evidence from real CLI stderr
      (now available post-COSE). Document classification (IPC / FD /
      env / protocol / framing / CLI-exit-semantics / other).
- [ ] AC-002: Minimal reproducer captured. Either a unit-style harness
      under `tests/` (preferred — no real LLM call) or a standalone
      script under `docs/reviews/sdk-message-reader/` if a real-CLI
      repro is required to demonstrate the cause.
- [ ] AC-003: Disposition decided and acted on:
      (a) Fix in guardkit's SDK adapter if the bug is on guardkit's
          side of the contract (e.g., `max_turns=1` misused, stdin
          closed too early), OR
      (b) File upstream against the Claude Agent SDK with the minimal
          repro and clear classification, AND add a tracking comment /
          ticket reference in `guardkit/orchestrator/sdk_utils.py`
          near the dedup filter so future readers know whether the
          dedup is still load-bearing.
- [ ] AC-004: If root cause is fixed in guardkit (path (a)) or
      upstream (path (b) and a release lands with the fix), reassess
      the dedup filter in `sdk_utils.py`:
      - If noise is gone: remove the filter and its install hook.
      - If noise persists: leave filter in place, update the docstring
        with the new context.

## Files Likely To Change

- `guardkit/orchestrator/sdk_utils.py` — possibly remove the dedup
  filter if root cause is fixed.
- `guardkit/orchestrator/quality_gates/coach_validator.py` — fix path
  if the bug is on guardkit's side of the contract.
- `docs/reviews/TASK-FIX-A7B5-sdk-message-reader-investigation.md` —
  update with root-cause findings and disposition decision.
- A new investigation note (or extension of the A7B5 note) capturing
  the minimal repro and classification.

## Out Of Scope

- Replacing the Claude Agent SDK harness wholesale.
- Refactoring `coach_validator`'s SDK fallback path beyond what the
  root-cause fix requires.
- Re-doing the log dedup work (already shipped by A7B5).

## Cross-reference

- `docs/reviews/TASK-FIX-A7B5-sdk-message-reader-investigation.md` —
  full investigation deferral note from A7B5.
- TASK-REV-COSE — blocker; must land first.
- TASK-FIX-7A09 — sibling SDK error-cascade refactor whose intent
  must not be undone.
