# Implementation Guide: FEAT-BDDM (BDD Runner Silent-Bypass Fix)

## Execution Order

**Strict dependency:** Wave 3 cross-repo remediation tasks must NOT start until Wave 1 GuardKit core fix is merged to `main`. This is because:

1. Wave 1 ships the new R1 contract (synthetic blocker on missing pytest-bdd).
2. Wave 3's per-repo fixes ASSUME that contract is in place (so the Coach blocks loudly when tagged scenarios + missing dep coexist).
3. Without Wave 1 merged first, Wave 3 might appear to "work" while still relying on the silent-bypass underneath.

Wave 2 (Graphiti episode) only needs Wave 1 *content* to reference; it can run in parallel with Wave 3 once Wave 1 is merged.

## Wave 1: GuardKit Core Fix

### TASK-FIX-BDDM-1 — BDD runner synthetic blocker (R1 + R2)

**Files modified:**
- [guardkit/orchestrator/quality_gates/bdd_runner.py](../../../guardkit/orchestrator/quality_gates/bdd_runner.py) (+25/-3 LOC)
- [tests/unit/orchestrator/quality_gates/test_bdd_runner.py](../../../tests/unit/orchestrator/quality_gates/test_bdd_runner.py) (rename + rewrite 1 test, add 2 new tests)

**Patch sketch:** see `.claude/reviews/TASK-REV-BDDM-review-report.md` §B.4 for the exact before/after of `bdd_runner.py:466-473`.

**TDD workflow recommended:**
1. RED: rename `test_pytest_bdd_unavailable_returns_none` → `test_pytest_bdd_unavailable_with_tags_returns_synthetic_blocker`; assert `result.scenarios_failed == 1`, `result.failures[0].scenario_name == "pytest_bdd_not_importable"`. Test fails.
2. GREEN: replace `return None` at line 466-473 with the synthetic `BDDResult` construction.
3. Add `test_pytest_bdd_unavailable_no_tags_still_skips` — confirms the legitimate-skip path at line 458 is unchanged.
4. Add `test_synthetic_blocker_routes_through_coach_validator` — e2e: synthetic blocker reaches Coach as `category=bdd_failure`.

**Key non-regression assertions to verify:**
- `test_no_feature_file_returns_none` (line 365) still passes.
- `test_no_matching_tag_returns_none` (line 377) still passes.
- All ~12 tests that mock `has_pytest_bdd: True` still pass.
- `test_feature_file_with_failing_scenario_causes_coach_feedback` (test_bdd_end_to_end.py:97) still passes.
- `test_no_feature_file_behaves_as_today` (test_bdd_end_to_end.py:155) still passes.

### TASK-FIX-BDDM-2 — Env-level preflight in feature_validator (R3)

**Files modified:**
- [guardkit/orchestrator/feature_validator.py](../../../guardkit/orchestrator/feature_validator.py) (+50 LOC)
- [guardkit/orchestrator/feature_orchestrator.py](../../../guardkit/orchestrator/feature_orchestrator.py) (+1 wire at line 733)
- New test: `tests/unit/orchestrator/test_feature_validator_bdd_preflight.py`

**Approach:** Add a function `validate_feature_environment(feature, repo_root, worktree_path) -> PreFlightValidationResult`:
1. For each task in `feature.tasks`, call `find_feature_files_with_tag(repo_root / "features", task_tag(task.id))`.
2. If non-empty AND `bdd_runner.has_pytest_bdd(python_executable=worktree_python)` returns False → emit a `ValidationIssue` with severity=`error`.
3. Wire into `feature_orchestrator.py:733` next to `validate_feature_preflight(...)`.

### TASK-DOC-BDDM-4 — BDD workflow docs (R5)

**Files modified:**
- [docs/guides/bdd-workflow-for-agentic-systems.md](../../../docs/guides/bdd-workflow-for-agentic-systems.md) (+15 LOC: new "Runtime Prerequisites" subsection after line 54)
- [installer/core/commands/feature-spec.md](../../../installer/core/commands/feature-spec.md) (line 491-493 wording amendment)

## Wave 2: Knowledge Graph

### TASK-DOC-BDDM-3 — Graphiti episode (R4)

Write a Graphiti episode in `guardkit__project_decisions` linking this incident to the existing "runner without producer anti-pattern" rule (uuid `184731b0-3cb6-4eb2-a310-883421767dbf`). Cite TASK-FIX-F584 as the invocation-error sibling. Reference `.claude/reviews/TASK-REV-BDDM-review-report.md`.

## Wave 3: Cross-Repo Remediation

All per-repo tasks share the same shape: edit `pyproject.toml` to add `"pytest-bdd>=8.1,<9"` to test/dev dependencies, run the project's install (`pip install -e .[dev]` or equivalent), and verify `python -c "import pytest_bdd"` succeeds.

**Critical task:** TASK-OPS-BDDM-9 (jarvis) is the only one with currently-silent-bypassed scenarios (86 `@task:` tags). After adding pytest-bdd:
1. Verify `pytest_bdd` is importable in jarvis's worktree env.
2. Re-run AutoBuild on a representative FEAT-J002 task with the GuardKit fix from Wave 1 in place.
3. Confirm the BDD oracle now produces a non-vacuous `bdd_results` block.
4. If scenarios fail/pend → file follow-up tasks for the actual implementation gaps.
5. FEAT-J003 is cancelled (history filename suffix `-cancelled.md`); accept the BDD-verification gap retrospectively.

**Lower-priority tasks (TASK-OPS-BDDM-5, 6, 7, 8, 10, 11):** these projects either have feature scaffolding without tags yet, or no BDD scope at all. Adding pytest-bdd is preventative — it ensures any future `/feature-spec` or `/feature-plan` invocation that introduces tagged scenarios will be verifiable from the start.

## Conductor Workspaces (Optional)

For Wave 1 parallel execution:

```
authentication-bdd-fix-wave1-1  →  TASK-FIX-BDDM-1
authentication-bdd-fix-wave1-2  →  TASK-FIX-BDDM-2
authentication-bdd-fix-wave1-3  →  TASK-DOC-BDDM-4
```

Wave 3 cross-repo tasks naturally parallelise — each runs in its own target repo's worktree, so no GuardKit-side coordination is needed beyond ordering after Wave 1 merge.

## Validation Plan

After Wave 1 merge, before starting Wave 3:

```bash
# In GuardKit repo:
# 1. Confirm bdd_runner now produces synthetic blocker on missing pytest-bdd
python3 -c "
from guardkit.orchestrator.quality_gates import bdd_runner
from pathlib import Path
import tempfile, os
with tempfile.TemporaryDirectory() as tmp:
    p = Path(tmp); (p/'features').mkdir()
    (p/'features'/'x.feature').write_text('Feature: X\n  @task:TASK-001\n  Scenario: Y\n    Given a\n    When b\n    Then c\n')
    # Force pytest_bdd absent
    bdd_runner.has_pytest_bdd = lambda **_: False
    result = bdd_runner.run_bdd_for_task('TASK-001', p)
    print('result:', result)
    assert result is not None and result.scenarios_failed == 1
    assert 'pytest_bdd_not_importable' in result.failures[0].reason
    print('R1 verified.')
"

# 2. Confirm env preflight surfaces the same gap (R3)
# (run full feature_validator integration test after TASK-FIX-BDDM-2 merges)
```

After Wave 3 (jarvis):

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/jarvis
grep "pytest-bdd" pyproject.toml  # should show pytest-bdd>=8.1,<9
python -c "import pytest_bdd; print('OK', pytest_bdd.__version__)"

# Then run AutoBuild on a J002 task and check the bdd_results block
# in .guardkit/worktrees/.../task_work_results.json
```
