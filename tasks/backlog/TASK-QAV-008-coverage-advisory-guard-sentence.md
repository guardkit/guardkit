---
id: TASK-QAV-008
title: Add a coverage advisory guard sentence to the Coach prompt (asymmetric with stub-scan guard #9)
task_type: fix
priority: low
status: backlog
created: 2026-07-05T12:40:00+01:00
tags: [qa-verifier, coverage-gate, coach-prompt, advisory]
---

# Task: Coverage findings need an advisory guard sentence like stub-scan's

## Finding (post-merge ASSUM-006 review, 2026-07-05)

The merged L3 coverage gate emits findings with `severity="warning"`
(`coverage_gate.py:68`) and — correctly — has no deterministic rejection
path. But unlike stub-scan, which has an explicit advisory guard sentence
(guard #9 in `AgentInvoker._render_absence_of_failure_guards`,
`agent_invoker.py:3674-3682`: "never reject the turn on stub_scan findings
alone"), **coverage findings reach the Coach only as raw bundle JSON**
(truncated at `agent_invoker.py:3457`) with no structured instruction on
how to treat them.

Risk (both directions): an LLM Coach may treat coverage warnings as
blocking (false-red-ish leniency inversion) or silently ignore them
(losing the advisory feedback value). The FEAT-C332 §5.4 advisory-first
posture and ASSUM-006 intended symmetric treatment.

## Fix shape

Add a coverage advisory guard (guard #10) to
`_render_absence_of_failure_guards`, mirroring guard #9 verbatim in
structure: when `evidence_bundle.coverage` is non-null and its findings
list is non-empty, instruct the Coach to surface the zero-execution
symbols as advisory `should_fix` feedback and NEVER reject the turn on
coverage findings alone.

Per `.claude/rules/player-prompt-reinforce-coach-constraint-in-three-locations.md`:
this is a Coach-side guard only (no input-referencing structural constraint
on a Player output field), so the three-location Player-prompt rule does
not apply — but check whether the autobuild-player prompt mentions
coverage findings and keep wording consistent if it does.

## Acceptance criteria

- [ ] AC-1: guard renders when coverage findings are non-empty; absent/empty
  coverage renders nothing (absent-signal-safe, mirrors guard #9 gating).
- [ ] AC-2: wording pins the advisory contract ("never reject the turn on
  coverage findings alone"); unit test mirrors
  `test_qav002_stub_scan_fields.py`'s AC-7 no-blocking shape.
- [ ] AC-3: no change to coverage_gate.py severity or any deterministic
  path — prompt-layer only.

## Origin

ASSUM-006 post-merge verification (Fable-window guardkit session
2026-07-05); deviation recorded in
`features/qav-behavioural-gates/qav-behavioural-gates_assumptions.yaml`.
