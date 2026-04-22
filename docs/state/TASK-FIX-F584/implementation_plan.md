# TASK-FIX-F584 — Implementation Plan

**Complexity**: 4/10
**Intensity**: standard (user-confirmed, lifted from auto-detected `light` given P0/quality-gate nature)
**Scope decisions** (user-confirmed 2026-04-22):
- Primary runner-error surfacing fix: in-scope
- Secondary `rglob` fix with dotdir/vendored filter: **bundled** in-scope
- AC #5 (post-fix jarvis probe re-run): **in-task** follow-up, budget 15–30 min for venv setup/teardown

## Files to modify

| File | Change | LOC est. |
|------|--------|----------|
| `guardkit/orchestrator/quality_gates/bdd_runner.py` | Primary fix (runner-error surfacing) + recursive discovery with filter | +40 |
| `tests/unit/orchestrator/quality_gates/test_bdd_runner.py` | +6 new tests (returncodes 2/3/4, coach-rejection, nested rglob, filter-out) | +140 |
| `.claude/reviews/TASK-BDD-JBKF-r2-backfill-evidence.md` | Append "Post-fix re-run" section | +25 |

No new files, no new dependencies.

## Fix 1 — Primary: runner-error surfacing

**Location**: `bdd_runner.py:425-467` inside `run_bdd_for_task`.

**Change shape**: after `parse_junit_xml` returns `(0, [], [])` and before the existing `returncode == _PYTEST_EXIT_NO_TESTS` silent-skip, insert a new branch:

```python
# New: runner-error surfacing. If pytest errored (returncode != 0) with
# no collected tests and no parsed failures, we cannot distinguish "nothing
# to test" from "runner exploded" without the exit code. For any non-zero
# exit code other than 5 (NO_TESTS, legitimate skip), surface a synthetic
# failure so Coach's approval rule (`scenarios_failed == 0`) catches it.
if (
    passed == 0
    and not failures
    and not pending
    and invocation.returncode not in (0, _PYTEST_EXIT_NO_TESTS)
):
    failures = [_synthesise_runner_error_failure(invocation, matching)]
    logger.warning(
        "BDD runner for %s: pytest exited with %d and produced no testcases; "
        "surfacing as synthetic failure (runner error). First 200 chars of stderr: %r",
        task_id,
        invocation.returncode,
        (invocation.stderr or invocation.stdout or "")[:200],
    )
```

**Helper**:

```python
_PYTEST_EXIT_USAGE_ERROR = 4        # "usage error"/"not found"
_PYTEST_EXIT_INTERNAL_ERROR = 3     # internal error
_PYTEST_EXIT_INTERRUPTED = 2        # interrupted (SIGINT etc.)
_RUNNER_ERROR_REASON_MAX = 200


def _synthesise_runner_error_failure(
    invocation: _PytestInvocation,
    feature_files: Sequence[Path],
) -> FailureDetail:
    """Produce a synthetic FailureDetail when pytest errored with no testcases.

    Drives Coach's `scenarios_failed > 0` rule so runner errors block approval
    rather than silently passing as `(0, 0, 0, [], [])`.
    """
    snippet = (invocation.stderr or invocation.stdout or "").strip()
    if len(snippet) > _RUNNER_ERROR_REASON_MAX:
        snippet = snippet[: _RUNNER_ERROR_REASON_MAX - 3] + "..."
    reason = f"pytest_runner_error: exit={invocation.returncode}"
    if snippet:
        reason = f"{reason}; {snippet}"
    first_file = str(feature_files[0]) if feature_files else "<unknown>"
    return FailureDetail(
        feature_file=first_file,
        scenario_name="pytest_runner_error",
        failing_step="",
        reason=reason,
    )
```

**Preserved behaviour**:
- `returncode == 0 and (0,0,0)` → **not** a runner error (no tests ran, fine); falls through to normal `BDDResult(0,0,0)` — but note this path is rare and still produces a non-blocking result. No change here; no existing test exercises it.
- `returncode == 5` → silent-skip via existing guard (unchanged).
- Normal populated results → unchanged.

## Fix 2 — Secondary: recursive feature discovery with dotdir/vendored filter

**Location**: `bdd_runner.py:117-135` (`find_feature_files_with_tag`).

**Change shape**:

```python
_EXCLUDED_DIR_NAMES: frozenset[str] = frozenset({
    "node_modules",
    "__pycache__",
    "site-packages",
})


def find_feature_files_with_tag(features_dir: Path, tag: str) -> List[Path]:
    matches: List[Path] = []
    if not features_dir.is_dir():
        return matches
    for fp in sorted(features_dir.rglob("*.feature")):
        rel_parts = fp.relative_to(features_dir).parts
        # Skip dotdirs (.venv, .git, .tox, etc.) and known vendored dirs.
        if any(part.startswith(".") or part in _EXCLUDED_DIR_NAMES for part in rel_parts):
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.debug("Could not read %s: %s", fp, exc)
            continue
        if tag in text:
            matches.append(fp)
    return matches
```

Jarvis's nested scaffold (`features/<slug>/<slug>.feature`) now discovered under default `features_subdir="features"`. Vendored `.feature` files under `.venv/`, `.git/`, `node_modules/` excluded.

## Test plan (additions to existing `test_bdd_runner.py`)

1. `test_runner_error_exit_4_surfaces_as_failure` — **primary AC** reproduction. Monkeypatch `_invoke_pytest_bdd` to return `_PytestInvocation(returncode=4, stdout="ERROR: not found: ...", stderr="", junit_xml="")`, assert `result.scenarios_failed == 1`, `result.failures[0].reason` contains `"pytest_runner_error: exit=4"`.
2. `test_runner_error_exit_3_surfaces_as_failure` — internal error variant.
3. `test_runner_error_exit_2_surfaces_as_failure` — interrupted variant.
4. `test_coach_rejects_runner_error_bdd_result` — e2e Coach-rejection AC. Construct the runner-error `BDDResult`, `to_dict()`, wrap as `{"bdd_results": ...}`, pass to `CoachValidator._check_bdd_results`, assert returned `blocking` list is non-empty with `category == "bdd_failure"`. Comment cites Graphiti-captured approval rule.
5. `test_find_feature_files_with_tag_discovers_nested_layout` — jarvis-style nested path found.
6. `test_find_feature_files_with_tag_filters_out_vendored_and_dotdirs` — filter-out AC. Create `.feature` files under `.venv/`, `node_modules/`, `.git/`, `.tox/` subtrees, assert NONE discovered.

## Coverage target

≥85% on the modified module; existing suite already near this — additions should keep us above.

## Out of scope (noted for follow-up)

- `parse_junit_xml("")` returning `(0,0,0)` silently rather than signalling empty-parse — upstream contributor to this bug class. Worth a defensive follow-up task but not addressed here.
- Returncode 0 with all-zero counters (rare; not covered by existing tests, not flagged in evidence).

## Risks

- **Low**: The synthetic-failure approach adds a failure to the existing `failures` list; downstream Coach consumer already handles `failures[:5]` summarisation, so no consumer change needed.
- **Low**: `rglob` traversal over very large repos could be slower; offset by filter excluding the dotdirs/vendored that dominate large trees.

## Post-fix verification

After tests pass locally:
1. Re-run `.claude/reviews/jbkf_probe.py` against jarvis throwaway venv.
2. Confirm Outcome D no longer occurs: `BDDResult.scenarios_failed >= 1`.
3. Append "Post-fix re-run" section to `.claude/reviews/TASK-BDD-JBKF-r2-backfill-evidence.md`.
4. Tear down jarvis `.venv-r2-probe/`.
