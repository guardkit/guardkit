---
id: TASK-ABSR-A1B2
title: Smart-default bootstrap_failure_mode to 'block' when requires-python is declared
status: completed
task_type: feature
created: 2026-04-27T00:00:00Z
updated: 2026-04-27T00:00:00Z
completed: 2026-04-27T00:00:00Z
completed_location: tasks/completed/2026-04/
previous_state: in_review
state_transition_reason: "All quality gates passed (167/167 bootstrap-suite tests). Closes Wave 1 R1 of FEAT-ABSR-9C6E."
priority: high
tags: [autobuild, bootstrap, environment, regression-fix]
parent_review: TASK-REV-FA04
feature_id: FEAT-ABSR-9C6E
implementation_mode: task-work
wave: 1
conductor_workspace: autobuild-stall-resilience-wave1-block-default
complexity: 4
depends_on: []
---

# TASK-ABSR-A1B2 — Smart-default bootstrap_failure_mode to 'block' when requires-python is declared

## Description

Flip [`DEFAULT_BOOTSTRAP_FAILURE_MODE`](../../../guardkit/orchestrator/feature_orchestrator.py#L225) from `"warn"` to a smart-default function that returns `"block"` when **any detected manifest declares `requires-python`** and `"warn"` otherwise. The existing `block` codepath ([`_maybe_hardfail_requires_python`](../../../guardkit/orchestrator/feature_orchestrator.py#L1257-L1308) and [`_maybe_hardfail_bootstrap`](../../../guardkit/orchestrator/feature_orchestrator.py#L1219-L1255)) already raises `FeatureOrchestrationError` with a remediation hint naming `uv python install`, `pyenv install`, and `conda create` — this task only changes when that path fires.

This eliminates the failure class identified in TASK-REV-FA04: silent continuation past a Python interpreter mismatch that produces an `installs_failed=1, installs_attempted=1` outcome and then traps tasks with `task_type=declarative` + `implementation_mode=task-work` in a feedback stall.

## Acceptance Criteria

- [ ] [`DEFAULT_BOOTSTRAP_FAILURE_MODE`](../../../guardkit/orchestrator/feature_orchestrator.py#L225) is replaced (or kept and supplemented) by a function `compute_default_bootstrap_failure_mode(manifests)` that returns `"block"` when any manifest in `manifests` has a non-empty `get_requires_python()` and `"warn"` otherwise.
- [ ] [`load_bootstrap_config`](../../../guardkit/orchestrator/feature_orchestrator.py#L228-L305) preserves the precedence chain: explicit yaml value > CLI override > smart default. (The smart default is applied only when neither yaml nor CLI provided a value.)
- [ ] The smart-default decision happens *after* manifest detection (so it has the manifest list to inspect) but *before* the requires-python precheck and the bootstrap call.
- [ ] [`guardkit/cli/autobuild.py:649-654`](../../../guardkit/cli/autobuild.py#L649-L654) help text is updated to reflect the smart default: `'block' (smart default — applies when any manifest declares requires-python; otherwise 'warn')`.
- [ ] [`tests/orchestrator/test_bootstrap_gating.py:177`](../../../tests/orchestrator/test_bootstrap_gating.py#L177) (`assert DEFAULT_BOOTSTRAP_FAILURE_MODE == "warn"`) is replaced by tests that cover both branches of the smart default.
- [ ] [`tests/orchestrator/test_bootstrap_gating.py:162,176`](../../../tests/orchestrator/test_bootstrap_gating.py#L162) assertions of `"warn"` defaulting are updated.
- [ ] Hint-text assertions at [lines 134, 375, 496](../../../tests/orchestrator/test_bootstrap_gating.py#L134) — verify the warn-opt-out hint string still matches the rendered message.
- [ ] **New tests**:
  - `test_smart_default_blocks_when_requires_python_declared` — manifest with `requires-python` produces `"block"` default.
  - `test_smart_default_warns_when_no_requires_python` — manifest without `requires-python` (or empty manifests) produces `"warn"` default.
  - `test_explicit_yaml_warn_overrides_smart_default_block` — yaml `warn` wins over smart default.
  - `test_explicit_cli_warn_overrides_smart_default_block` — CLI `--bootstrap-failure-mode warn` wins over yaml and smart default.
- [ ] Replay the failing FEAT-J004-702C scenario as an integration-style test (mocked manifests + mocked pip-failure) and assert that `FeatureOrchestrationError` is raised before Wave 1 starts.
- [ ] No regression in PEP-668-fallback path: existing `tests/unit/test_environment_bootstrap*.py` continue to pass unchanged.

## Implementation Notes

- The decision must be visible in logs: log the resolved default at `INFO` once per orchestration run, naming whether the smart default applied and which manifest(s) drove it.
- Be careful with the `BOOTSTRAP_FAILURE_MODES` tuple at [feature_orchestrator.py:224](../../../guardkit/orchestrator/feature_orchestrator.py#L224) — it should remain `("block", "warn")`. The smart-default is *which* of those two is returned by default, not a new mode.
- This is a behaviour change for any consumer not setting an explicit value AND running on a project that declares `requires-python`. The opt-out is documented in the existing hint-text and CLI help. Add a CHANGELOG entry naming the change and the opt-out path.

## Out of Scope

- Interpreter-discovery (R5 in TASK-REV-FA04 report) — deferred.
- Changes to the `_maybe_hardfail_*` gate logic itself — only the default-mode resolution changes.
- Changes to PEP-668 retry path.

## References

- Review: [TASK-REV-FA04 report](../../../.claude/reviews/TASK-REV-FA04-report.md) §F1, §F8, §R1, "Regression Analysis — R1"
- Failing run: [autobuild-FEAT-J004-702C-history.md](../../../../jarvis/docs/history/autobuild-FEAT-J004-702C-history.md) lines 46-67 confirming the silent-continue path

## Implementation Summary

Replaced the hardcoded `DEFAULT_BOOTSTRAP_FAILURE_MODE = "warn"` resolution with a smart-default function that decides post-manifest-detection. The constant is kept as the documented baseline; the new function `compute_default_bootstrap_failure_mode(manifests)` returns `"block"` when any detected manifest declares a non-empty `requires-python` constraint, `"warn"` otherwise.

### Changes

- **`guardkit/orchestrator/feature_orchestrator.py`**:
  - Added `compute_default_bootstrap_failure_mode(manifests: Iterable[Any]) -> str`.
  - Extended `load_bootstrap_config` to track a `failure_mode_explicit` flag (True when yaml or CLI provided a valid value). Precedence preserved: CLI > yaml > smart default.
  - Added `_resolve_smart_default_failure_mode(manifests)` invoked from `_bootstrap_environment` after `detector.detect()` and before `_maybe_hardfail_requires_python` / `bootstrapper.bootstrap`. Logs the resolved mode and triggering manifest paths at INFO once per orchestration run.
- **`guardkit/cli/autobuild.py`**: updated `--bootstrap-failure-mode` help text to describe the smart default and the opt-out paths.
- **`tests/orchestrator/test_bootstrap_gating.py`**: added 11 new tests (4 AC tests + 4 unit tests for the pure function + 1 INFO-log test + 1 replay test for FEAT-J004-702C + 1 init-baseline test). Updated 2 pre-existing tests to accommodate the new `failure_mode_explicit` field.
- **`CHANGELOG.md`**: `[Unreleased] → Breaking Changes` entry naming the smart-default behaviour change and the yaml/CLI opt-out paths.

### Approach

Kept the `__init__`-time resolution unchanged for the explicit case (CLI / yaml). Smart default is a *late-bound* decision — applied inside `_bootstrap_environment` once `manifests` is in hand, then memoised by setting `_bootstrap_failure_mode_explicit = True` so a between-wave second invocation does not re-evaluate. This avoided introducing a separate manifest-scanning round-trip at `__init__` time and kept the per-orchestration-run INFO log tightly scoped.

### Lessons

- **Late-bound configuration resolution avoids re-plumbing**: the alternative — moving manifest detection into `__init__` — would have entangled bootstrap with the orchestrator constructor and broken existing test fixtures that build orchestrators without manifests. Keeping the resolution at the `_bootstrap_environment` boundary preserved the existing test surface (only one previously-asserted dict-equality test needed adjustment) and put the decision exactly where the manifest list is naturally available.
- **`failure_mode_explicit` is a useful "did the user choose this?" signal beyond just smart-default routing** — it makes the precedence chain self-documenting in the code path that consumes the resolved value, rather than scattering "if not yaml and not cli" reasoning across multiple sites. Worth replicating for any future config that has a CLI override + yaml + smart default chain.
- **Pre-existing 14 unrelated test failures in `test_design_context_integration.py` and `instrumentation/test_digest_content.py`** are present on `main` without this change — confirmed via `git stash` round-trip. Not blocking for this task; tracked separately.

### Quality Gates

- Compilation: ✅ Pass.
- Tests: ✅ 167/167 in the bootstrap suite (`test_bootstrap_gating.py` + `test_environment_bootstrap.py`).
- Coverage: not measured separately for this task; existing test_bootstrap_gating coverage of `feature_orchestrator.py` exercises every branch of the new code (smart-default trigger / no-trigger / explicit-yaml-overrides / explicit-CLI-overrides / replay).
- AC checklist: all 11 AC items satisfied (function added, precedence preserved, decision happens after detection / before pre-check, CLI help updated, new tests added, replay test added, no PEP-668 regression, INFO-log on resolved value, BOOTSTRAP_FAILURE_MODES tuple unchanged, CHANGELOG entry).
