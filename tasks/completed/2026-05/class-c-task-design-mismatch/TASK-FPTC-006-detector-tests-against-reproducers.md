---
id: TASK-FPTC-006
title: "End-to-end detector tests against FEAT-FD32 reproducers + false-positive guard"
status: completed
created: 2026-05-03T12:00:00Z
updated: 2026-05-03T13:45:00Z
completed: 2026-05-03T13:45:00Z
previous_state: in_review
state_transition_reason: "All 5 ACs satisfied; 9/9 contract tests pass"
priority: high
task_type: testing
implementation_mode: task-work
tags:
  - testing
  - detector
  - reproducer
  - false-positive
  - class-c
  - feature-plan-defects
complexity: 4
estimated_minutes: 120
parent_review: TASK-REV-AUTM
feature_id: FEAT-AUTM
parent_feature: feature-plan-defects
wave: 3
conductor_workspace: feature-plan-defects-wave3-2
dependencies:
  - TASK-FPTC-001
---

# Task: Detector test fixtures against reproducers

## Description

Hard-gate the detector against the two real-world incidents that
motivated this workstream. Both reproducer ACs MUST be flagged. Three
benign-looking ACs must NOT be flagged (false-positive guard). One
borderline case (an operator-mention in a docs context) is asserted
to be flagged, since false positives cost only operator attention and
we bias toward catching everything.

Because the detector lives in the agent prompt rather than a Python
function, these are *prompt-contract* tests: they assert the prompt
text in `feature-plan.md` contains the strong-signal markers that
would match each reproducer, plus they exercise a small Python
matcher that mirrors the prompt's strong/weak/pairing rules so the
contract is mechanically checkable in CI.

## Acceptance Criteria

- [x] **AC-FPTC-006-01** —
      `tests/integration/commands/test_feature_plan_class_c_detection.py`
      exists.
- [x] **AC-FPTC-006-02** — The test file contains a fixture
      `AC_SEED_01` whose text is the verbatim AC-SEED-01 from
      TASK-GR-SEED:
      *"`python scripts/seed_student_model.py` runs successfully
      against live FalkorDB at whitestocks:6379 ... All 25 entity
      writes succeed without 401s, timeouts, or
      GroupIdValidationError failures."*
      Test asserts the fixture matches the strong-signal rules
      ("FalkorDB", "live", hostname pattern).
- [x] **AC-FPTC-006-03** — The test file contains a fixture
      `AC_DEMO_01` whose text is the verbatim AC-DEMO-01 from
      TASK-GR-DEMO:
      *"A live MCP tutor session is conducted from Claude Desktop
      with the user as the human-in-the-loop. Sequence: 5–7 ×
      tutor_turn(...) exchanges with at least one Coach revision ..."*
      Test asserts the fixture matches the strong-signal rules
      ("live", "human-in-the-loop", "Claude Desktop").
- [x] **AC-FPTC-006-04** — Three benign-looking fixtures are asserted
      NOT to trigger:
      1. *"All unit tests pass with `pytest tests/ -v`."*
      2. *"`SettingsClass.from_env()` reads `FALKORDB_HOST` from
         environment and constructs a valid client config."*
      3. *"Calling `parse_yaml(s)` returns the expected dict with
         key `version=1`."*
- [x] **AC-FPTC-006-05** — A small Python helper
      `tests/integration/commands/_detector_matcher.py` (or
      embedded in the test file) implements the same strong/weak/
      pairing rules described in `feature-plan.md` and is exercised
      by tests AC-FPTC-006-02 through AC-FPTC-006-04. The helper is
      explicitly a *contract mirror* of the prompt rules, not a
      production detector — its purpose is to mechanically verify
      that the prompt-side rules cover all four reproducer cases.

## Implementation Notes

- Keep the matcher tiny. Strong signals → list of regexes; weak
  signals → list of regexes; matching = at least one strong, OR
  one strong paired with one or more weak.
- The matcher does NOT need to be invoked by `/feature-plan` at
  runtime — the agent does that work in its prompt-time reasoning.
  This is purely a CI-side check that the prompt covers the cases.

## Cross-component contract

**Consumes** TASK-FPTC-001:
- The strong/weak signal taxonomy as published in
  `feature-plan.md`. The contract-mirror matcher must implement the
  same rules.

## Files

- `tests/integration/commands/test_feature_plan_class_c_detection.py`
  (new)
- `tests/integration/commands/_detector_matcher.py` (new)

## Out of Scope

- The detector itself (TASK-FPTC-001).
- Tests of the orchestrator skip behaviour (those live in
  TASK-FPTC-003 and TASK-FPTC-004).

## Implementation Summary

Shipped Wave 3 / FPTC-006 of the Class C `feature-plan-defects`
workstream: end-to-end contract tests that hard-gate the
operator_handoff detector against the two real-world FEAT-FD32
reproducer ACs and three benign false-positive fixtures.

Concrete changes:

- Added `tests/integration/commands/_detector_matcher.py` — a small
  contract-mirror matcher (~30 regexes) implementing the same
  strong/weak/pairing rules as `installer/core/commands/feature-plan.md`
  lines 1359-1381. Strong signals are bucketed into the four categories
  the prompt enumerates (`live_infrastructure`, `human_verbs`,
  `wall_clock`, `author_self_disclosure`). Module docstring is explicit
  that this is a contract mirror, not a production detector — the
  Plan agent does the actual detection in its prompt-time reasoning
  per AC-AUTM-02 of the parent review.
- Added `tests/integration/commands/test_feature_plan_class_c_detection.py`
  with 9 tests:
  - `AC_SEED_01` and `AC_DEMO_01` fixtures pinned verbatim from the
    parent review (AC-FPTC-006-02, AC-FPTC-006-03). Each fixture has
    one test asserting the surface markers the AC calls out
    (`FalkorDB`, `live`, hostname pattern for SEED;
    `live`, `human-in-the-loop`, `Claude Desktop` for DEMO) and one
    test asserting the matcher triggers via the relevant strong-signal
    category.
  - Three benign fixtures parametrized over a single negative test
    (AC-FPTC-006-04): pytest-passes, FALKORDB_HOST as env-var config
    string, and parse_yaml returning a dict. The case-sensitive
    `FalkorDB at` pattern is the load-bearing decision that keeps the
    `FALKORDB_HOST` benign case inert.
  - Two pairing-rule tests (AC-FPTC-006-05): weak alone does NOT
    trigger; 1 strong + N weak still triggers.

Approach:

The matcher is intentionally tight — case-sensitive `FalkorDB at`
(not just `FalkorDB`) so the `FALKORDB_HOST` config-string
false-positive case stays inert without needing extra negative-lookup
logic. The four strong-signal categories from feature-plan.md are
encoded as a `Mapping[str, Sequence[Pattern]]` so the matcher returns
which category fired — the contract test asserts a specific category
match for each reproducer (`live_infrastructure` for SEED,
`human_verbs` for DEMO) rather than just "any strong signal" so a
prompt drift that swapped categories would still be caught.

Test results: 9/9 new tests pass; 19/19 pass across the whole
`tests/integration/commands/` directory (the 10 sibling FPTC-001
prompt-pinning tests are unaffected). 1.68 s wall-clock for the
directory.

Lessons:

- Mirroring prompt-text rules in a tiny Python matcher is a low-noise
  way to catch prompt-vs-rules drift in CI. The pattern is the same
  shape as TASK-FPTC-001's verbatim-substring assertions, just one
  level deeper — TASK-FPTC-001 pins the words exist; TASK-FPTC-006
  pins they fire correctly on the real reproducer text.
- Case-sensitivity is doing real work in the false-positive guard.
  `FALKORDB_HOST` appearing as a Python-style env-var name vs
  `FalkorDB at <host>` as prose is a meaningful distinction the
  matcher needs to encode.
- Returning the *category* (not just a bool) from the matcher gives
  the test suite enough resolution to assert each reproducer fires
  via the expected signal class. A purely boolean matcher would
  silently survive a prompt rewrite that swapped categories.

Pairs with: TASK-FPTC-001 (the prompt-side rules under test), and
the Wave 2 runtime-side tasks (FPTC-003 orchestrator skip, FPTC-004
validator/loader awareness). FPTC-006 is the contract gate that keeps
all three surfaces — prompt, mirror, and runtime skip — in agreement.
