---
id: TASK-FIX-ACWS
title: Reject whitespace-containing tokens in AC path scanning (backtick regex swallows whole inline-code commands)
status: backlog
created: 2026-06-12T19:30:00Z
updated: 2026-06-12T19:30:00Z
priority: high
tags: [autobuild, plan-audit, ac-scanner, false-positive, unrecoverable-stall]
complexity: 3
implementation_mode: task-work
estimated_effort_hours: 2
related:
  - TASK-AB-FIX-INVAB1  # introduced the AC-005 escalation rule
  - TASK-GK-PA-002      # narrowed scan to AC section
  - TASK-GK-AC-001      # prior false-positive fix (bare basenames)
---

# Task: AC path scanner treats backtick-quoted shell commands as missing file paths

## Why this exists

During FEAT-5A64 in `lpa-platform-poc` (2026-06-12), TASK-MH03-005 hit
`UNRECOVERABLE_STALL` because its acceptance criteria contained:

```markdown
- [ ] `grep -n "_fire_rules_check" src/moneyhub/service.py` shows the stub ...
```

The backtick extraction regex `` `([^`]+\.[a-zA-Z]+)` `` in
`_scan_ac_for_missing_paths` (`guardkit/orchestrator/agent_invoker.py:8011`)
captured the **entire inline-code span** — `grep -n "_fire_rules_check"
src/moneyhub/service.py` — as a single "path". It ends in `.py` and contains
`/`, so it passed both filters, and
`(self.worktree_path / p).exists()` was naturally False. Result chain:

1. Plan audit returns `status: violation, severity: high` with
   `missing_files: ['grep -n "_fire_rules_check" src/moneyhub/service.py']`
   — even when `src/moneyhub/service.py` exists and tests pass.
2. Coach evidence gathering aborts (`partial_gate_abort`); tests/coverage
   fields are nulled (absence-of-failure guards then forbid approval).
3. Three consecutive feedback turns trip the context-pollution stall with
   no passing checkpoint → `unrecoverable_stall`, wasting the whole task
   budget (~30 min) on every retry until the AC text itself was reworded.

The Coach itself flagged the contradiction in its turn-2 feedback ("the plan
audit may have a path resolution issue") but has no way to override the gate.

Same-shaped bug exists in the parity twin:
`guardkit/orchestrator/synthetic_report.py:269`
(`generate_file_existence_promises`, secondary backtick pass) — the
swallowed command becomes a `file_existence` completion promise that can
never verify. The double-/single-quote passes in both files
(`"([^"]+\.[a-zA-Z]+)"` / `'([^']+\.[a-zA-Z]+)'`) have the identical flaw
for quoted commands like `'pytest tests/foo.py'`.

## Description

A file path never contains whitespace in our AC conventions, while inline
code spans frequently do (`grep ...`, `pytest ... -v`, `alembic upgrade
head`). Reject any captured token containing whitespace before treating it
as a path, in both extraction sites:

- `agent_invoker.py` `_scan_ac_for_missing_paths` (and its docstring's
  parity claim) — applies to all four regex passes, simplest as a single
  filter alongside the existing `"*" in p` / extension / basename checks.
- `synthetic_report.py` `generate_file_existence_promises` — same filter
  before a token becomes a `file_existence` promise. Keep the two sites'
  behaviour aligned (the agent_invoker docstring explicitly promises regex
  parity with the synthetic-report path).

Option considered and rejected: extracting the path-like substring out of
the command (e.g. pull `src/moneyhub/service.py` out of the grep). The
primary regex `[\w./\-]+\.\w{1,5}` already captures bare path tokens from
the same AC line, so the substring is found anyway when it matters —
dropping whitespace tokens loses nothing.

## Acceptance criteria

- [ ] A token captured from AC text that contains any whitespace is never
  reported in `missing_files` by `_scan_ac_for_missing_paths`, for all four
  regex passes (primary, backtick, double-quoted, single-quoted).
- [ ] Regression test reproducing FEAT-5A64: an AC body containing
  `` `grep -n "_fire_rules_check" src/moneyhub/service.py` `` against a
  worktree where `src/moneyhub/service.py` exists returns no missing paths;
  against a worktree where it does NOT exist, the bare-path primary capture
  `src/moneyhub/service.py` IS still reported (escalation behaviour for
  genuinely missing files is preserved).
- [ ] `generate_file_existence_promises` no longer emits a `file_existence`
  promise whose path contains whitespace; a test covers the same grep-style
  AC line.
- [ ] Existing plan-audit and synthetic-report test suites pass unchanged
  (no regression to TASK-GK-AC-001 basename skipping or TASK-GK-PA-002
  AC-section narrowing).
- [ ] Docstring of `_scan_ac_for_missing_paths` updated to document the
  whitespace rejection and keep the synthetic-report parity claim accurate.

## Evidence / reproduction

- Consumer repo: `lpa-platform-poc`, feature FEAT-5A64, task TASK-MH03-005
  turn states (`.guardkit/worktrees/FEAT-5A64/.guardkit/autobuild/TASK-MH03-005/turn_state_turn_{1,2,3}.json`)
  show `plan_audit` message: `no plan on disk; AC names file path(s) that do
  not exist on disk: grep -n "_fire_rules_check" src/moneyhub/service.py`.
- Workaround applied consumer-side: AC line reworded to "Grepping for
  `_fire_rules_check` in src/moneyhub/service.py ..." after which the task
  approved in 1 turn.
