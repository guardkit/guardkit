---
id: TASK-FIX-3F04D
title: Fix pre-existing test_config_propagation + autobuild_timeout test failures
status: completed
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
completed: 2026-04-30T00:00:00Z
previous_state: in_review
state_transition_reason: "All 11 failing tests now pass; 208-test regression suite green"
completed_location: tasks/completed/TASK-FIX-3F04D/
priority: medium
task_type: feature
complexity: 4
tags: [test-fix, regression, feature_orchestrator, autobuild]
---

# TASK-FIX-3F04D — Fix pre-existing test failures

## Description

Eleven pre-existing test failures surfaced during the FEAT-ATR work
(commits `bf761d4b` ATR-001 / `51960fe7` ATR-002 / `fc1f09c4` ATR-003 /
`adacc159` test floor bypass). All eleven were verified to **pre-date**
those commits — they reproduce on `bf761d4b` (the tip before our
session began) — and have causes unrelated to the `task_timeout` floor
that `adacc159` already addressed. They were left out of scope for the
ATR feature so the test fix could land as a focused, reviewable change.

## Failures

### Group A — `tests/integration/test_config_propagation.py` (10 failures)

```
TestSdkTimeoutPropagation::test_task_work_interface_default_timeout
TestEnablePreLoopCascade::test_cli_flag_highest_priority
TestEnablePreLoopCascade::test_task_frontmatter_overrides_feature
TestEnablePreLoopCascade::test_feature_yaml_used_when_no_task_override
TestEnablePreLoopCascade::test_default_true_when_no_config
TestEnablePreLoopCascade::test_empty_autobuild_config_uses_default
TestConfigCombinations::test_sdk_timeout_from_cli_enable_pre_loop_from_feature
TestConfigCombinations::test_feature_level_defaults_for_all_tasks
TestEdgeCases::test_missing_autobuild_section_in_task
TestEdgeCases::test_empty_frontmatter_uses_default
```

**Two distinct failure modes**:

1. **`Feature.autobuild_config` field removed** — 9 of 10 fail with:
   ```
   ValueError: "Feature" object has no field "autobuild_config"
   ```
   The Pydantic `Feature` model no longer has an `autobuild_config`
   attribute, but the tests still try to set it
   (e.g. `sample_feature.autobuild_config = None` at
   `test_config_propagation.py:424`). Either the field was
   intentionally dropped (in which case the tests are obsolete and
   should be rewritten against the new config surface — likely
   per-task frontmatter `autobuild:` blocks) or the rename wasn't
   applied to the test fixture.

2. **SDK timeout default changed** — `test_task_work_interface_default_timeout`
   fails with:
   ```
   assert interface.sdk_timeout_seconds == 900
   E   assert 1200 == 900
   ```
   The default SDK timeout is now 1200s (matches the `sdk_timeout=1200`
   fallback in `feature_orchestrator.py:2177` and similar sites). Test
   needs to assert the new default, or the test is asserting against
   a constant that should be exposed.

### Group B — `tests/unit/test_autobuild_timeout_budget.py` (1 failure)

```
TestFeatureOrchestratorBudgetPropagation::test_execute_task_accepts_time_budget_parameter
```

Fails with:
```
TaskExecutionResult(
  task_id='TASK-T-001', success=False, total_turns=0,
  final_decision='error',
  error="'FeatureOrchestrator' object has no attribute '_bootstrap_venv_python'",
  ...
)
```

The attribute *does* exist on the real class (`feature_orchestrator.py:644`
initialises `self._bootstrap_venv_python = None`), so the failure is
almost certainly a fixture / Mock issue: the test constructs a
`FeatureOrchestrator` (or stubs its `__init__`) in a way that bypasses
the `__init__` body and never sets `_bootstrap_venv_python`. The fix
is likely either (a) call the real `__init__` from the fixture, or
(b) explicitly set `_bootstrap_venv_python = None` on the test
instance.

## Acceptance Criteria

- [ ] All 10 `test_config_propagation.py` tests pass without modifying
      the underlying Pydantic `Feature` schema or production
      `feature_orchestrator.py` config-resolution code (the tests
      should be updated to match current production behaviour, not the
      other way around).
- [ ] `test_execute_task_accepts_time_budget_parameter` passes after a
      fixture-level fix (no production code changes — the attribute
      exists in `__init__`).
- [ ] No regression in the 148 currently-passing tests in
      `tests/unit/test_feature_orchestrator.py`,
      `tests/integration/test_parallel_wave_execution.py`, and
      `tests/unit/test_timeout_logging_reconciliation.py`.
- [ ] If the `autobuild_config` Pydantic field truly was renamed/moved
      (e.g. into per-task frontmatter), the tests should be rewritten
      against the new config surface, *not* the old field re-added.
- [ ] Each test's assertion either matches current production
      behaviour or has a comment explaining the historical context if
      a deliberate behaviour change happened (e.g. SDK timeout
      900 → 1200 — link to the commit that changed it).

## Test Requirements

- pytest unit + integration tests as listed above
- Re-run the full test_feature_orchestrator + test_parallel_wave +
  test_timeout_logging suites for regression check (148 tests)

## Implementation Notes

**Investigation order**:

1. `git log -p tests/integration/test_config_propagation.py` to see when
   `autobuild_config` was last set on `Feature` — gives the rename
   commit and what the new config surface looks like.
2. `git log -p guardkit/orchestrator/feature_loader.py` (where
   `Feature` lives) to see when the field was removed.
3. For Group B, inspect the test's fixture setup —
   `tests/unit/test_autobuild_timeout_budget.py` line 771 area — to
   see how the orchestrator instance is constructed.

**Out of scope**:
- Changing production `Feature` schema or
  `feature_orchestrator.py` config resolution. The tests should match
  the current production surface.
- Re-adding the old `autobuild_config` field if it was removed
  intentionally.
- Floor-related issues (already fixed in commit `adacc159`).

## Related

- Parent context: FEAT-ATR (TASK-ATR-001/002/003 + the
  `adacc159` test fix) — the ATR work surfaced these but didn't fix
  them.
- The 4 `test_parallel_wave_execution.py` failures that *did* get
  fixed in `adacc159` (validator regression + mock signature drift)
  are a peer of these failures but were small enough to bundle with
  the floor fix.

## Implementation Summary

All 11 originally-failing tests now pass; 208-test regression suite
remains green. Fix is test-only — zero production code changes.

### Root cause (Group A: 10 tests in `test_config_propagation.py`)

Two distinct historical drifts, both on the test side:

1. **`Feature` migrated from `@dataclass` to Pydantic v2 `BaseModel`**
   with `extra="ignore"`. Tests authored at PR #26 (`b7f0472ac`)
   assumed dataclass semantics and did
   `sample_feature.autobuild_config = {...}`, which Pydantic v2
   rejects with `ValueError: "Feature" object has no field
   "autobuild_config"`. Production reads via
   `getattr(feature, "autobuild_config", None) or {}` — i.e. the
   field is read but never declared and is never set in the
   non-test code path. Fix: switch the eight call sites to
   `object.__setattr__(sample_feature, "autobuild_config", value)`,
   which writes to `__dict__` and is found by `getattr`.

2. **Production default for feature-build `enable_pre_loop` is
   `False`**, not `True` (see
   `feature_orchestrator.py::_resolve_enable_pre_loop` step 4 —
   "feature tasks have detailed specs from feature-plan"). Four
   tests asserted the obsolete `True` default; updated to `False`
   with a docstring explaining why feature-build differs from
   stand-alone `autobuild task`. Renamed
   `test_default_true_when_no_config` →
   `test_default_false_when_no_config`.

3. **`DEFAULT_SDK_TIMEOUT` raised 900s → 1200s** in commit
   `e0449c547` ("increase default timeout for autobuild") to give
   complexity-6+ tasks adequate headroom for the full Phase 3-5
   pipeline. Updated `test_task_work_interface_default_timeout` to
   assert against the imported `DEFAULT_SDK_TIMEOUT` constant
   (with a parallel `== 1200` assertion as a smoke check) and a
   docstring linking the commit.

### Root cause (Group B: 1 test in `test_autobuild_timeout_budget.py`)

`test_execute_task_accepts_time_budget_parameter` constructs the
orchestrator via `FeatureOrchestrator.__new__(...)` to bypass the
real `__init__`, then sets a curated subset of attributes by hand.
The bypass missed `_bootstrap_venv_python` (initialised to `None`
in `__init__` at `feature_orchestrator.py:644`, forwarded to
`AutoBuildOrchestrator(venv_python=...)` at line 2738). Adding
`fo._bootstrap_venv_python = None` to the fixture surfaced a
second pre-existing fixture issue: `mock_orchestrate_result` was
a generic `Mock()`, so `result.stall_classification` returned a
truthy Mock and tripped the `list(stall_classification.co_fires)`
path. Setting `mock_orchestrate_result.stall_classification = None`
makes the no-stall branch deterministic.

### Approach

Tests-only fix per task scope. No changes to `Feature`,
`feature_orchestrator.py`, or `task_work_interface.py`. Where
production behaviour intentionally diverges from the original
test expectation (default `True` → `False`, timeout `900` → `1200`),
the new docstring/assertion explains the historical context and
links the commit, per the acceptance criteria.

### Lessons

- **Pydantic-v2 migration of a previously-`@dataclass` model is a
  silent test-fixture trap**: `extra="ignore"` only tells you
  unknown fields will be dropped on validation; it does not warn
  that ad-hoc attribute assignment will fail at runtime. Anywhere
  a fixture writes `obj.unknown_attr = ...` to a Pydantic model,
  switch to `object.__setattr__` (test-only) or declare the
  field. Grep `obj\.[a-z_]+ =` against models with `extra="ignore"`
  to catch peers. (See `tests/integration/test_requires_infra_propagation.py`
  for the same field on a `Mock()` — that path doesn't trip.)

- **`__new__`-bypass fixtures rot every time `__init__` adds an
  attribute that downstream methods read**. Periodically diffing
  the `__init__` body against the curated attribute list in any
  `__new__`-using fixture is cheaper than waiting for the next
  `'X' object has no attribute 'Y'` error. Better: use a real
  constructor with mocked dependencies wherever possible — the
  attribute list maintains itself.

- **Generic `Mock()` for orchestrator return values is fragile
  against `is not None` guards**: a bare Mock is truthy, so any
  `if result.stall_classification is not None: list(...co_fires)`
  branch trips. Either use `Mock(spec=ClassName)` with explicit
  `None` for unset fields, or set every field the production
  codepath inspects (the second form keeps the test brittle in
  the helpful direction — adding a new field to production
  immediately fails fixtures that haven't been updated).

### Verification

`pytest tests/integration/test_config_propagation.py
tests/unit/test_autobuild_timeout_budget.py
tests/unit/test_feature_orchestrator.py
tests/integration/test_parallel_wave_execution.py
tests/unit/test_timeout_logging_reconciliation.py` →
**208 passed in 55s**.

The two `coroutine never awaited` `RuntimeWarning`s emitted by
`test_parallel_wave_execution.py` are pre-existing (mocking
artefact, unrelated to this fix).
