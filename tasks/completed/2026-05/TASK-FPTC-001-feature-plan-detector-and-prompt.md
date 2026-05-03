---
id: TASK-FPTC-001
title: "/feature-plan: detect operator-shaped ACs and prompt for operator_handoff (L3a)"
status: completed
created: 2026-05-03T12:00:00Z
updated: 2026-05-03T13:45:00Z
completed: 2026-05-03T13:45:00Z
previous_state: in_review
state_transition_reason: "All 5 acceptance criteria satisfied; 10/10 contract tests pass"
priority: high
task_type: feature
implementation_mode: task-work
tags:
  - feature-plan
  - operator-handoff
  - detector
  - class-c
  - feature-plan-defects
complexity: 5
estimated_minutes: 120
parent_review: TASK-REV-AUTM
feature_id: FEAT-AUTM
parent_feature: feature-plan-defects
wave: 1
conductor_workspace: feature-plan-defects-wave1-1
dependencies: []
---

# Task: /feature-plan detector + interactive operator_handoff prompt (L3a)

## Description

Class C of `/feature-plan` defects: the agent emits acceptance criteria
whose verification predicate is `observed_at_runtime(real_world)`,
which Player and Coach cannot satisfy by construction. This task adds
plan-time detection rules + an interactive prompt that lets the user
mark such tasks `task_type: operator_handoff` so autobuild skips them.

Reproducer ACs (from study-tutor FEAT-FD32, both manually completed
2026-05-03):
- TASK-GR-SEED AC-SEED-01: *"`python scripts/seed_student_model.py`
  runs successfully against live FalkorDB at whitestocks:6379 ..."*
- TASK-GR-DEMO AC-DEMO-01: *"A live MCP tutor session is conducted
  from Claude Desktop with the user as the human-in-the-loop ..."*

Both must be flagged by the rules below. See
`.claude/reviews/TASK-REV-AUTM-review-report.md` §AC-AUTM-02 for the
full detection-rule rationale and false-positive guard.

## Acceptance Criteria

- [ ] **AC-FPTC-001-01** — `installer/core/commands/feature-plan.md`
      contains a new section titled "Detection Rules — when to mark a
      task `operator_handoff`" enumerating:
      - **Strong signals** (any one triggers): live infrastructure
        markers, human verbs, wall-clock language, author
        self-disclosure (verbatim phrases listed in the review).
      - **Weak signals** (require pairing with a strong signal):
        "verify"/"ensure"/"check", "running" (ambiguous), specific
        user/dataset names.
      - **False-positive guard**: weak signal alone does NOT trigger;
        strong signal always triggers.
- [ ] **AC-FPTC-001-02** — Same file's "Task Type Assignment Rules"
      table (currently around line 1311) gains a row:
      `Live infrastructure / human-in-the-loop / wall-clock observation
      patterns → operator_handoff`.
- [ ] **AC-FPTC-001-03** — Same file describes the interactive prompt
      step the agent runs at plan time when a strong signal fires:
      shows the offending AC text, asks
      *"Mark this task as `operator_handoff` and skip autobuild? [Y/n]"*,
      and on Y emits `task_type: operator_handoff` plus appends a
      "Required operator follow-up" block listing the runtime ACs
      verbatim.
- [ ] **AC-FPTC-001-04** — Pytest contract test
      `tests/integration/commands/test_feature_plan_detector_rules.py`
      asserts `feature-plan.md` contains the strong-signal markers
      ("FalkorDB", "live", "human-in-the-loop", "Claude Desktop",
      "p50", "p95", "wall-clock") and the false-positive guard string
      ("weak signal alone does NOT trigger" or equivalent).
- [ ] **AC-FPTC-001-05** — Same test asserts the operator_handoff row
      is present in the Task Type Assignment Rules table.

## Implementation Notes

- This is a prompt-engineering change to a single `.md` file plus a
  contract test. No Python implementation required — the detector
  runs *inside* the `/feature-plan` agent, not as a separate Python
  function.
- Keep the "Required operator follow-up" template tight (3–5 lines)
  so it doesn't bloat task files.
- Pair this with TASK-FPTC-002 (taxonomy) — the prompt is harmless
  without the enum but the enum is harmless without the prompt.

## Cross-component contract

This task only modifies `feature-plan.md` and one test file. The
`task_type: operator_handoff` value it emits is consumed by:
- TASK-FPTC-002 (`TaskType` enum + profile)
- TASK-FPTC-003 (orchestrator skip)
- TASK-FPTC-004 (validator/loader awareness)

Format produced: standard task frontmatter with the new value:
```yaml
task_type: operator_handoff
```

## Files

- `installer/core/commands/feature-plan.md` (edit)
- `tests/integration/commands/test_feature_plan_detector_rules.py` (new)

## Out of Scope

- Python detector logic. The detector runs in the agent's prompt-time
  reasoning, not as code. (This is the deliberate design decision in
  the parent review — keep intelligence at plan-time, not validation-time.)
- Backwards compatibility for existing tasks. See parent-review
  AC-AUTM-04.

## Implementation Summary

Shipped Wave 1 / L3a of the Class C `feature-plan-defects` workstream:
plan-time detection rules and an interactive operator_handoff prompt
inside `installer/core/commands/feature-plan.md`. No Python — the
detector lives entirely in the Plan agent's prompt surface.

Concrete changes:
- Added a row to the Task Type Assignment Rules table mapping the
  pattern *"Live infrastructure / human-in-the-loop / wall-clock
  observation patterns"* → `operator_handoff` (AC-02).
- Added a new "Detection Rules — when to mark a task `operator_handoff`"
  subsection enumerating the four strong-signal categories from
  TASK-REV-AUTM §AC-AUTM-02 (live infrastructure, human verbs,
  wall-clock language, author self-disclosure), the four weak signals,
  and the false-positive guard *"weak signal alone does NOT trigger"*
  (AC-01).
- Added an "Interactive prompt step" describing the verbatim Y/n prompt
  the agent runs at plan time when a strong signal fires, plus the
  `## Required operator follow-up` block template the agent appends to
  flagged tasks (AC-03).
- Added contract test `tests/integration/commands/test_feature_plan_detector_rules.py`
  pinning all 7 strong-signal markers, the false-positive guard string,
  the Detection Rules section heading, and the operator_handoff row in
  the assignment table — 10/10 tests pass, existing
  `test_feature_plan_prompts.py` still 9/9 (AC-04 + AC-05).

Approach:

The review (`.claude/reviews/TASK-REV-AUTM-review-report.md`) already
specified verbatim phrase lists. The implementation strategy was to
pin those phrases in prompt text and a contract test rather than build
a Python detector — this is consistent with the design rule that
intelligence should live at plan-time inside the agent's reasoning,
not at validation-time as a Python function. The contract test is the
only structural enforcement.

Lessons:

- Pinning prompt content via verbatim-substring assertions in pytest is
  a cheap, low-noise regression guard for `.md` files the agent reads
  at runtime — same shape as the existing TASK-FPSG-001 prompt tests.
- Folding strong-signal categories into a single markdown table keeps
  the rules grep-able for both the agent and human readers; a
  parametrised pytest test over the marker list catches any one
  category dropping out.
- The new `tests/integration/commands/` directory needed an empty
  `__init__.py` for pytest collection — this was the only file outside
  the original plan and is required scaffolding rather than scope creep.

Pairs with: TASK-FPTC-002 (taxonomy enum), TASK-FPTC-003 (orchestrator
skip), TASK-FPTC-004 (validator/loader awareness). The detector is
inert without those Wave 2 / 3 tasks shipping the runtime side.
