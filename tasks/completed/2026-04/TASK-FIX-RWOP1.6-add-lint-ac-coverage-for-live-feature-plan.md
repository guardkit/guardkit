---
id: TASK-FIX-RWOP1.6
title: Add lint-ac coverage for the live (non-from-spec) feature-plan path
status: completed
task_type: feature
created: 2026-04-23T00:00:00Z
updated: 2026-04-23T00:00:00Z
completed: 2026-04-23T00:00:00Z
previous_state: in_review
state_transition_reason: "All ACs satisfied, 4/4 new tests passing, full feature_plan suite green (60/60)"
test_results:
  status: pass
  coverage: null
  last_run: 2026-04-23T00:00:00Z
  passed: 4
  failed: 0
  suite: "tests/integration/feature_plan/"
  suite_passed: 60
  suite_failed: 0
priority: medium
complexity: 4
tags: [coverage-gap, feature-plan, lint-compliance, post-rwop1.5, rwop1]
parent_review: TASK-REV-RWOP1
parent_task: TASK-FIX-RWOP1.5
feature_id: FEAT-RWOP1
related_to: TASK-FIX-RWOP1.5
related_tasks:
  - TASK-FIX-RWOP1.5
  - TASK-FIX-RWOP1.2  # Live nudge-injection producer that this task asserts against
---

# Task: Add lint-ac coverage for the live (non-from-spec) feature-plan path

## Decision Origin

Follow-up to [TASK-FIX-RWOP1.5](../../completed/2026-04/TASK-FIX-RWOP1.5-feature-plan-from-spec-orphan-disposition.md), recorded in
[.claude/reviews/TASK-FIX-RWOP1.5-from-spec-decision.md](../../../.claude/reviews/TASK-FIX-RWOP1.5-from-spec-decision.md)
§"Known, accepted outcomes" → "Coverage gap for live lint-ac policy".

## Problem Statement

`tests/planning/test_lint_ac_compliance.py` was the only test asserting that
**generated feature plans include lint-compliance acceptance criteria in
implementation tasks** (and that no standalone quality-gate-verification tasks
appear). RWOP1.5 quarantined that test alongside the rest of the
`--from-spec` cluster (it was using `parse_research_template` and
`generate_quality_gates` as setup scaffolding — both now in
`_scratch/planning/`).

Two of the three things that test asserted are still live policy and apply to
**every** `/feature-plan` invocation, regardless of mode:

1. Implementation tasks must include lint-compliance ACs (e.g. AC entries
   referencing the project's lint command).
2. No standalone `verify-quality-gates`/equivalent tasks should appear in the
   generated feature YAML.

The third assertion (`generate_quality_gates` works with lint-bearing
`coach_validation_commands`) tracked the now-quarantined helper and is
correctly retired.

The live producer for `--from-spec`-free feature plans is
`installer/core/commands/lib/generate_feature_yaml.py` (post-RWOP1.2). That
producer currently has *zero* automated coverage of the lint-AC and
no-standalone-QG-task properties. Until this task lands, both properties are
asserted only by code review.

## Scope

### In-Scope

- One new integration test file at
  `tests/integration/feature_plan/test_generate_feature_yaml_lint_ac_compliance.py`
  (matches the sibling-naming convention established by
  `test_generate_feature_yaml_nudges.py` and `test_generate_feature_yaml_linter.py`).
- The test materialises a minimum-viable feature description, invokes
  `generate_feature_yaml.py` against it, parses the resulting feature YAML,
  and asserts:
  - **Lint AC presence**: every task whose `task_type` is implementation-class
    (i.e. not docs / not test-only) has at least one acceptance criterion
    mentioning the project's lint compliance (string match: `lint`, scoped to
    the AC list, case-insensitive).
  - **No standalone QG tasks**: no task in the generated YAML has a
    `task_type` or `name` indicating it exists solely to verify quality gates
    (e.g. titled `Verify quality gates`, type `quality_gate_verification`).
- Test fixtures (research-style markdown blob or in-memory feature
  description) live alongside the test file. Do NOT introduce new fixtures
  under `tests/fixtures/` shared with other suites.

### Out-of-Scope

- **Do NOT** restore `tests/planning/test_lint_ac_compliance.py` from
  `_scratch/`. The from-spec parser path it used is dead; we want the new
  test to assert against the live producer instead.
- **Do NOT** introduce new lint-compliance behaviour into
  `generate_feature_yaml.py`. If the live producer fails the new assertions
  on day one, that is a finding to surface (open a separate fix task) — not
  a reason to quietly add behaviour from this task.
- **Do NOT** assert on the *exact text* of the lint AC. Testing that a lint
  AC is present is the load-bearing claim; the wording is the producer's
  business and changes harmlessly over time.
- Schema-level changes to the feature YAML format. Consume current schema
  as-is.

## Acceptance Criteria

- [x] New test file at
      `tests/integration/feature_plan/test_generate_feature_yaml_lint_ac_compliance.py`
      with at least two test functions: one for lint-AC presence, one for
      no-standalone-QG-task.
- [x] Each test function has both a positive case (compliant fixture passes)
      and a negative-control case (a deliberately-broken fixture is rejected
      by the assertion logic — proves the test isn't vacuous).
- [x] Tests pass locally with the current `generate_feature_yaml.py`. If they
      *fail*, do not modify the producer to make them pass — file a follow-up
      task documenting the actual lint-AC gap and complete this task without
      that file (the test is still a net-positive guardrail).
- [x] Decision doc for RWOP1.5 updated: strike the "Coverage gap until
      RWOP1.6 lands" entry.
- [x] No existing tests regress.

## Implementation Notes

- **Fixture pattern**: minimum viable input is whatever the live
  `generate_feature_yaml.py` accepts as a feature-description input. Mirror
  the input shape used by `test_generate_feature_yaml_nudges.py` —
  consistency over novelty.
- **Negative-control technique**: feed a feature description whose tasks
  deliberately omit lint references and assert the test catches it. Or
  inject a `Verify quality gates` task and assert it's flagged. Without
  negative controls, presence-checks tend to silently pass on empty inputs.
- **Locating implementation-class tasks**: read the current
  `generate_feature_yaml.py` to see how `task_type` is set on output. If
  the field doesn't exist, fall back to filename/title-substring heuristics
  documented in the test file.
- **Coverage scope**: this task adds *coverage*, not behaviour. Total time
  expectation is on the order of a few hours, not a full day — if scope is
  blowing past that, the test is overreaching.

## Preconditions

- TASK-FIX-RWOP1.5 must be merged (the test it replaces is in `_scratch/`,
  the producer it asserts against is `generate_feature_yaml.py` from
  RWOP1.2 — both already landed).
- Confirm `tests/integration/feature_plan/` is the right home (it is per
  current layout — sibling files live there).

## Related

- Decision doc: [.claude/reviews/TASK-FIX-RWOP1.5-from-spec-decision.md](../../../.claude/reviews/TASK-FIX-RWOP1.5-from-spec-decision.md)
- Quarantined test (do not restore):
  [_scratch/planning/tests/test_lint_ac_compliance.py](../../../_scratch/planning/tests/test_lint_ac_compliance.py)
- Live producer:
  [installer/core/commands/lib/generate_feature_yaml.py](../../../installer/core/commands/lib/generate_feature_yaml.py)
- Sibling test (style reference):
  [tests/integration/feature_plan/test_generate_feature_yaml_nudges.py](../../../tests/integration/feature_plan/test_generate_feature_yaml_nudges.py)
- Parent review:
  [docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md)
- Feature guide: [IMPLEMENTATION-GUIDE.md](../../backlog/feat-rwop1-orphan-cleanup/IMPLEMENTATION-GUIDE.md)
