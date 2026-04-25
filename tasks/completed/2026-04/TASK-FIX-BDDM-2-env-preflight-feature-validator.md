---
id: TASK-FIX-BDDM-2
title: 'Env-level preflight in feature_validator (R3) — catch pytest-bdd gap before SDK turns burn'
status: completed
created: '2026-04-25T00:00:00Z'
updated: '2026-04-25T00:00:00Z'
completed: '2026-04-25T00:00:00Z'
completed_location: tasks/completed/2026-04/
previous_state: in_review
state_transition_reason: "task-complete: all quality gates passed"
priority: high
complexity: 5
task_type: bugfix
tags: [bdd, autobuild, preflight, cost-protection, regression-fix]
parent_review: TASK-REV-BDDM
feature_id: FEAT-BDDM
implementation_mode: task-work
wave: 1
conductor_workspace: bdd-fix-wave1-2
depends_on: []
test_results:
  status: passed
  coverage: '100% (validate_feature_environment); 99% (entire feature_validator.py)'
  last_run: '2026-04-25T00:00:00Z'
  tests_run: 8
  tests_passed: 8
  tests_failed: 0
---

# Task: Env-level preflight in feature_validator (R3)

## Description

[feature_validator.validate_feature_preflight()](../../../guardkit/orchestrator/feature_validator.py#L127-L208) currently inspects only frontmatter (task_type, required fields). It does NOT inspect runtime environment. As a result, a project where tagged feature files exist but `pytest-bdd` is missing only surfaces the gap **inside** the Player-Coach loop — where TASK-FIX-BDDM-1's synthetic blocker burns ~3 SDK turns before TASK-AB-SD01 stall-detection exits.

This task adds an env-level preflight that catches the gap **before** any Player turn runs, keeping cost-efficiency neutral. **R3 is paired with R1 (TASK-FIX-BDDM-1) — both are MUST_FIX in revision 2 of the review.**

## Acceptance Criteria

- [ ] New function `validate_feature_environment(feature, repo_root, worktree_path) -> PreFlightValidationResult` added to [feature_validator.py](../../../guardkit/orchestrator/feature_validator.py).
- [ ] For each task in `feature.tasks`, the function calls `find_feature_files_with_tag(repo_root / "features", task_tag(task.id))`.
- [ ] If any task has tagged feature files AND `bdd_runner.has_pytest_bdd(python_executable=worktree_python)` returns False → emit `ValidationIssue` with severity=`error`, suggestion `"Add 'pytest-bdd>=8.1,<9' to {pyproject_path} dependencies and reinstall the worktree env"`.
- [ ] Wired into [feature_orchestrator.py:733](../../../guardkit/orchestrator/feature_orchestrator.py#L733) next to existing `validate_feature_preflight(...)` call.
- [ ] New unit tests in `tests/unit/orchestrator/test_feature_validator_bdd_preflight.py`:
  - `test_no_tagged_scenarios_skips_preflight` — feature with no `@task:` tags → no issue raised.
  - `test_tagged_scenarios_with_pytest_bdd_present_skips_preflight` — pytest-bdd present → no issue raised.
  - `test_tagged_scenarios_without_pytest_bdd_raises_error` — the failing case from TASK-REV-BDDM → error emitted.
  - `test_preflight_reports_specific_pyproject_path_in_suggestion` — error suggestion mentions the actual pyproject path.
- [ ] Coverage on `validate_feature_environment` ≥ 90% (line + branch).

## Implementation Notes

**Approach** — minimal extension, mirrors `validate_feature_preflight` shape:

```python
def validate_feature_environment(
    feature: Feature,
    repo_root: Path,
    worktree_python: Optional[str] = None,
) -> PreFlightValidationResult:
    """Env-level preflight: catch pytest-bdd ↔ tagged feature files gaps."""
    from guardkit.orchestrator.quality_gates.bdd_runner import (
        find_feature_files_with_tag, has_pytest_bdd, task_tag,
    )

    result = PreFlightValidationResult()
    features_dir = repo_root / "features"
    if not features_dir.is_dir():
        return result

    pytest_bdd_ok: Optional[bool] = None  # lazy probe; only check if needed
    affected_tasks: List[str] = []

    for task in feature.tasks:
        tagged = find_feature_files_with_tag(features_dir, task_tag(task.id))
        if not tagged:
            continue
        if pytest_bdd_ok is None:
            pytest_bdd_ok = has_pytest_bdd(python_executable=worktree_python)
        if not pytest_bdd_ok:
            affected_tasks.append(task.id)

    if affected_tasks:
        result.errors.append(ValidationIssue(
            task_id=", ".join(affected_tasks[:5]) + ("..." if len(affected_tasks) > 5 else ""),
            field="environment",
            severity="error",
            message=(
                f"{len(affected_tasks)} task(s) have tagged feature files but "
                "pytest-bdd is not importable in the worktree env. AutoBuild "
                "would surface this as a Coach-blocking failure (R1)."
            ),
            suggestion=(
                f"Add 'pytest-bdd>=8.1,<9' to {repo_root}/pyproject.toml "
                "dependencies and reinstall."
            ),
        ))
    return result
```

**Wiring** in `feature_orchestrator.py:733` — after existing preflight, before the loop:

```python
preflight_result = validate_feature_preflight(feature, self.repo_root)
env_result = validate_feature_environment(feature, self.repo_root)
preflight_result.errors.extend(env_result.errors)
preflight_result.warnings.extend(env_result.warnings)
# ... existing report-and-bail logic
```

**Regression-safety:** function is purely additive — no existing call site behaviour changes unless tagged features + missing pytest-bdd coexist. Healthy projects skip the new check at the `if not tagged: continue` line.

## Notes

- **Pair with TASK-FIX-BDDM-1** — both are MUST_FIX, both ship in Wave 1.
- **Why error not warning:** if R1 is in place, the in-loop blocker would block anyway; preflight error simply moves the same outcome earlier with zero SDK cost.
- Architecture decision: see [.claude/reviews/TASK-REV-BDDM-review-report.md](../../../.claude/reviews/TASK-REV-BDDM-review-report.md) §E (R3 upgrade rationale).

## Implementation Summary

Added `validate_feature_environment(feature, repo_root, worktree_python=None)` to `guardkit/orchestrator/feature_validator.py`. The function lazily probes the worktree env for `pytest_bdd` only when at least one task in the feature has `.feature` files containing `@task:<TASK-ID>` — keeping cost neutral for healthy projects and projects that don't use BDD. When the gap exists, it emits a single `ValidationIssue` (severity=`error`, field=`environment`) covering all affected tasks (truncated at 5 + "..." for display), with a suggestion naming the worktree's actual `pyproject.toml` path.

Wired into `guardkit/orchestrator/feature_orchestrator.py:733` immediately after the existing `validate_feature_preflight` call: env errors/warnings are folded into the same `PreFlightValidationResult` so they flow through the existing report-and-bail path with no new branches.

**Regression-safety**: purely additive at both the function and call-site level — when no tagged features exist, or pytest-bdd is importable, no observable change. Stash-and-rerun confirmed the 14 unrelated failures in the broader orchestrator suite pre-existed on `main`.

## Lessons

- **Lazy probes scale with absence of triggers.** The `pytest_bdd_ok = None` sentinel + check-on-first-tagged-task pattern means the new validation costs literally one `find_feature_files_with_tag` scan per task and zero subprocess probes when no BDD content exists. The cost-neutrality claim isn't aspirational — it's structural.
- **Local imports keep cross-package coupling honest.** `feature_validator.py` lives in `guardkit/orchestrator/`; `bdd_runner` in `guardkit/orchestrator/quality_gates/`. The import at function scope (not module scope) makes it explicit that the validator only depends on bdd_runner when the env-preflight check actually runs, and dodges any future circular-import risk if quality_gates ever needs to import from feature_validator.
- **AC R1↔R3 cross-reference belongs in the user-facing message.** The "(R1)" suffix in the error message ties the preflight outcome to the in-loop blocker that would otherwise surface the same gap mid-Player-turn. Future readers grep'ing for "R1" in logs will land on the same review §E rationale rather than having to reconstruct the relationship.
