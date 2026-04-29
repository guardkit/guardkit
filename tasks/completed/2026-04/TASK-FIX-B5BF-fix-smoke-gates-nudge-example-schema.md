---
id: TASK-FIX-B5BF
title: Fix smoke_gates_nudge example schema that fails AutoBuild validation
status: completed
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:00:00Z
completed: 2026-04-29T00:00:00Z
previous_state: in_review
state_transition_reason: "Completed via /task-complete; all ACs met; 27/27 tests pass"
completed_location: tasks/completed/2026-04/
priority: high
tags: [bug, feature-plan, smoke-gates, documentation]
task_type: feature
complexity: 2
parent_task: TASK-FP-NDG2
test_results:
  status: passed
  coverage: null
  last_run: "2026-04-29"
  passed: 15
  failed: 0
  command: "pytest tests/unit/commands/test_smoke_gates_nudge.py"
---

# Task: Fix smoke_gates_nudge example schema that fails AutoBuild validation

## Discovery Context

Discovered 2026-04-29 during AutoBuild of FEAT-1773 in the study-tutor project.
A planner followed the nudge example verbatim; AutoBuild died at the Setup
phase with a `SchemaValidationError` from `FeatureLoader._parse_feature()`
before any task ran. Validator surfaced **6 errors**: 2× `Field required` (for
`after_wave` and `command`) + 4× `Extra inputs not permitted` (one per
`after_wave_N` key, since the model has `extra="forbid"`). The user-facing
impact is high — every `/feature-plan` run with ≥2 waves prints this nudge,
so every author who follows it hits the same wall.

## Problem Statement

`installer/core/commands/lib/smoke_gates_nudge.py:42-46` prints a "minimal example"
of how to activate feature-level smoke gates. The example shipped to users is:

```yaml
smoke_gates:
  after_wave_1:
    - python -c "import your_package"
  after_wave_2:
    - pytest tests/smoke -x
```

This shape **does not validate** against the real `SmokeGates` Pydantic model in
[guardkit/orchestrator/feature_loader.py:320-386](guardkit/orchestrator/feature_loader.py#L320-L386).
The actual schema is a **single mapping** with these fields:

- `after_wave: int | List[int] | Literal["all"]`  (note: `after_wave`, not `after_wave_1`)
- `command: str` (single string, not a list)
- `expected_exit: int = 0`  (optional)
- `timeout: int = 120`  (optional, bounded `[1, 600]`)

The model is configured with `model_config = ConfigDict(extra="forbid")`, so the
nudge example fails validation on three counts:

1. `after_wave_1` / `after_wave_2` are unknown keys → `extra="forbid"` rejects them
2. There is no top-level `command` field → required-field error
3. The current example implies multiple gates per feature, but the schema only
   accepts one `SmokeGates` object per feature (`smoke_gates: Optional[SmokeGates]`
   in `Feature`, see [feature_loader.py:431](guardkit/orchestrator/feature_loader.py#L431))

Users who copy the example verbatim trigger `SchemaValidationError` in
`FeatureLoader._parse_feature` ([feature_loader.py:644-649](guardkit/orchestrator/feature_loader.py#L644-L649))
before `/feature-build` starts. The nudge — whose entire purpose is to make
smoke-gate activation "one edit away" — actively misleads authors away from a
working configuration.

The canonical valid shape, per
[tests/unit/models/test_feature_yaml_schema.py](tests/unit/models/test_feature_yaml_schema.py)
fixtures, is a flat object — `smoke_gates` is a *single* `SmokeGates` per
feature, **not a dict-of-waves**. That is the trap the current example sets:

```yaml
# smoke_gates is ONE object per feature (not a dict-of-waves).
# after_wave selects which wave(s) the single command fires after.
smoke_gates:
  after_wave: [2, 3]          # int | list[int] | "all"
  command: |                  # single shell command (multi-line OK)
    set -e
    pytest tests/smoke -x
  expected_exit: 0            # optional, default 0
  timeout: 120                # optional, default 120s, bounds [1, 600]
```

## Description

Replace the broken multi-gate dict-style example in
`installer/core/commands/lib/smoke_gates_nudge.py:42-46` with a minimal example
that round-trips through `SmokeGates.model_validate(...)` cleanly. Add a
regression test that pins the example to the schema so this class of drift
cannot recur.

## Acceptance Criteria

- [ ] **AC-1**: The example string emitted by `_NOTICE_TEMPLATE` in
      `installer/core/commands/lib/smoke_gates_nudge.py` parses as valid YAML
      and validates against `SmokeGates.model_validate(...)` without raising.
- [ ] **AC-2**: The example uses the documented field names from the Pydantic
      model: `after_wave` (singular), `command` (single string). No
      `after_wave_1`, no list-of-commands.
- [ ] **AC-3**: The example demonstrates a realistic gate using a list-form
      `after_wave` (e.g. `after_wave: [2, 3]`) with a multi-line `command: |`
      block scalar — this shape illustrates the schema's range better than a
      single-wave scalar and is the most common production case (one smoke
      command, fired after the last few content waves). Include a brief inline
      comment naming the trap explicitly: **`smoke_gates` is one object per
      feature, not a dict-of-waves**. The example need not show
      `after_wave: "all"` or `after_wave: 1`, but must not contradict them.
- [ ] **AC-4**: A regression test under `tests/unit/commands/test_smoke_gates_nudge.py`
      extracts the example block from the notice text and validates it against
      `SmokeGates.model_validate(...)`. The test fails on the current `main`
      and passes after the fix.
- [ ] **AC-5**: The notice's link reference to
      `installer/core/commands/feature-plan.md § "Smoke gates"` continues to
      resolve. If `feature-plan.md` does not currently document the canonical
      schema with field-by-field semantics, **add a brief schema reference
      block** there (one YAML example + one-liner per field) so the nudge has
      somewhere accurate to point to.
- [ ] **AC-6**: No behavioral change to `check_smoke_gates_activation()` — its
      detection logic (≥ 2 waves, no `smoke_gates:` key, error suppression,
      `quiet` flag) is unaffected. Existing tests in
      `tests/unit/commands/test_smoke_gates_nudge.py` continue to pass.
- [ ] **AC-7**: All modified files pass project-configured lint/format checks
      with zero new errors.

## Test Requirements

- [ ] New test `test_notice_example_validates_against_smoke_gates_schema` that:
      - Calls `check_smoke_gates_activation()` against a fixture multi-wave
        feature YAML (or constructs the notice via `_NOTICE_TEMPLATE.format(...)`)
      - Extracts the YAML block between the "Minimal example:" line and the
        "See ..." line
      - Calls `yaml.safe_load(...)` on the extracted block
      - Calls `SmokeGates.model_validate(parsed["smoke_gates"])` and asserts no
        exception
- [ ] All existing tests in `tests/unit/commands/test_smoke_gates_nudge.py`
      continue to pass after the example string is rewritten

## Implementation Notes

### Files in scope

- `installer/core/commands/lib/smoke_gates_nudge.py` — fix `_NOTICE_TEMPLATE`
  example block (lines 42-46)
- `tests/unit/commands/test_smoke_gates_nudge.py` — add AC-4 regression test
- `installer/core/commands/feature-plan.md` § "Smoke gates" — add canonical
  schema reference if missing (AC-5)

### Files OUT of scope (do not change)

- `guardkit/orchestrator/feature_loader.py` — schema is correct as-is; the
  example, not the schema, is wrong
- `guardkit/orchestrator/smoke_gates.py` — fire/dispatch logic unrelated
- `guardkit/orchestrator/feature_orchestrator.py` — runtime wiring unrelated
- `check_smoke_gates_activation()` detection logic — only the example string
  inside `_NOTICE_TEMPLATE` changes

### Anti-stub note

This is a documentation/string-content fix with a paired regression test. The
"primary deliverable" is the corrected example string and the test that pins
it. Per `.claude/rules/anti-stub.md`, the test must actually parse and validate
the example — a test that asserts `True` or only checks string presence is a
stub for this task.

### Drift-prevention rationale

The current bug is precisely the "local design decisions that touch
externally-defined contracts" pattern called out in
`.claude/rules/namespace-hygiene.md` § "Prior art" (broader meta-rule). The
nudge string is a local copy of an externally-defined schema; nothing currently
holds them in sync. The AC-4 test closes that gap by making the example a
schema-validated artefact rather than a free-form documentation string.

## Out of Scope

- Auto-generating smoke-gate commands per stack (explicitly rejected by the
  parent design — see `feature-plan.md` § "Non-goals")
- Rewriting the feature YAML on the user's behalf
- Blocking `/feature-build` from running without smoke gates
- Changing the suppression rules in `check_smoke_gates_activation()`
- Adding multi-gate support to `SmokeGates` (model is single-object by design;
  if multi-gate is needed, that is a separate design task, not this fix)

## Related Artefacts

- **Parent (added the nudge)**: [TASK-FP-NDG2](tasks/completed/TASK-FP-NDG2/TASK-FP-NDG2.md)
  — original task that introduced the smoke-gates nudge but did not validate
  the example string against the `SmokeGates` schema. This task closes that
  gap.
- **Schema source-of-truth**: [TASK-SMK-F703A](tasks/completed/TASK-SMK-F703A/TASK-SMK-F703A.md)
  — defined the `SmokeGates` Pydantic model that the example must round-trip
  through.
- **Sibling (folded NDG2 + bdd_oracle nudges)**: [TASK-FIX-RWOP1.2](tasks/completed/2026-04/TASK-FIX-RWOP1.2-fold-bdd-oracle-and-smoke-gates-nudges.md)
  — touched the same nudge surface but did not catch the example/schema
  drift.
- **Discovery failure log** (external): `study-tutor/docs/history/autobuild-FEAT-1773-run-1.md`
  — captures the `SchemaValidationError` traceback that surfaced this bug.
- **Working post-fix YAML** (external reference for example shape):
  `study-tutor/.guardkit/features/FEAT-1773.yaml` once that project's nudge-
  generated YAML is corrected.
- **Graphiti episode** (group `guardkit__failure_patterns`): "guardkit
  smoke_gates schema gotcha (TASK-FP-NDG2 nudge example is wrong)" —
  documents the correct shape as a fast cushion for users until this task
  ships.

## Estimated Complexity

**2/10**. Single-file content edit in `_NOTICE_TEMPLATE` plus one regression
test that pins the example to the schema. The regression test is the
load-bearing change — it prevents this class of drift from recurring.

## Test Execution Log

### 2026-04-29 — `/task-work TASK-FIX-B5BF` (intensity: minimal)

**Files changed**:
- `installer/core/commands/lib/smoke_gates_nudge.py` — replaced the broken
  `after_wave_N` dict-of-waves example in `_NOTICE_TEMPLATE` with the
  canonical flat-object shape (`after_wave: [2, 3]` + multi-line
  `command: |` block). Added inline `# smoke_gates is ONE object per
  feature (not a dict-of-waves)` trap comment per AC-3.
- `tests/unit/commands/test_smoke_gates_nudge.py` —
  - Updated `test_returns_notice_when_two_waves_without_smoke_gates`
    assertions: dropped `after_wave_1`/`after_wave_2` checks (those
    strings are intentionally absent from the new example), added
    `after_wave:` and `command:` assertions for the canonical schema.
  - Added `test_notice_example_validates_against_smoke_gates_schema`
    (AC-4): extracts the YAML block between the "Minimal example:" and
    "See ..." anchors, parses it with `yaml.safe_load`, and validates
    `parsed["smoke_gates"]` against `SmokeGates.model_validate` to pin
    the example to the schema and prevent recurrence.
- `installer/core/commands/feature-plan.md` — added a "Smoke gates —
  canonical schema reference" block inside § 10.7 (AC-5) so the
  nudge's pointer resolves to a concrete schema reference (one YAML
  example + one-liner per field + the `extra="forbid"` semantics).

**AC verification**:
- AC-1 ✅ — example string round-trips through `SmokeGates.model_validate`
  cleanly (verified by new regression test).
- AC-2 ✅ — example uses `after_wave` (singular), `command` (single
  string). No `after_wave_1`, no list-of-commands.
- AC-3 ✅ — example uses list-form `after_wave: [2, 3]` with multi-line
  `command: |` block; trap comment names `smoke_gates is ONE object per
  feature, not a dict-of-waves` explicitly.
- AC-4 ✅ — `test_notice_example_validates_against_smoke_gates_schema`
  fails on pre-fix `main` (confirmed manually: 4 validation errors —
  missing `after_wave`, missing `command`, plus 2× `extra_forbidden`)
  and passes post-fix.
- AC-5 ✅ — feature-plan.md § "Smoke gates" now contains a canonical
  schema reference (YAML example + field-by-field semantics + drift
  prevention reference to the regression test).
- AC-6 ✅ — `check_smoke_gates_activation()` detection logic untouched;
  all 14 pre-existing tests still pass.
- AC-7 ✅ — Python files compile cleanly; no new lint errors.

**Test run** (intensity-minimal — compilation + tests, coverage skipped):

```
$ pytest tests/unit/commands/test_smoke_gates_nudge.py \
        tests/unit/models/test_feature_yaml_schema.py
============================== 27 passed in 0.22s ==============================
```

15 nudge tests (14 pre-existing + 1 new AC-4 regression) + 12 upstream
`SmokeGates` schema tests, all green.

**Out of scope (per task spec, not touched)**:
- `guardkit/orchestrator/feature_loader.py` — schema correct as-is.
- `guardkit/orchestrator/smoke_gates.py` — fire/dispatch logic.
- `check_smoke_gates_activation()` detection logic.
