# Implementation Plan — TASK-AB-BDDNEUTRAL01

**Neutral BDD verdict on absent feature file + auto-install conftest bridge**

Complexity 4 · bug · intensity: light. Source: `docs/retro/autobuild-retro-xref-2026-06-17.md` §3.5.
Provenance: fleet-memory FEAT-MEM-07 Error 1 ("BDD exit-4 affects every task").

## Root cause (empirically verified, pytest 9.0.2)

| Scenario | exit | output signature | correct verdict |
|---|---|---|---|
| `.feature` passed, **no conftest bridge** (the bug) | 4 | `ERROR: not found: <path>` + `(no match...)` | **neutral (absent)** |
| non-existent `.feature` path | 4 | `ERROR: file or directory not found: <path>` | **neutral (absent)** |
| broken conftest (ImportError) — genuine runner error | 4 | `ImportError while loading conftest` (no "not found:") | **failure (F584)** |
| exit 2/3, timeout(-1), empty-stream exit-4 | 2/3/-1/4 | no not-found signature | **failure (F584)** |
| directory arg, no bridge | 5 | `collected 0 items` | already → `None` |

The bridge (`conftest.py.template`) returns `None` without a sibling glue module, so
pytest exit-4 "not found" also fires for `.feature`-present-but-no-glue (scaffolding) —
correctly neutral too.

## Half 1 — Neutral verdict (`guardkit/orchestrator/quality_gates/bdd_runner.py`)

- New constants `_PYTEST_UNCOLLECTABLE_MARKERS` (`ERROR: not found:`,
  `ERROR: file or directory not found:`) and `_PYTEST_RUNNER_ERROR_MARKERS`
  (`while loading conftest`).
- New `_is_absent_feature_collection(invocation)`: exit==4 AND has uncollectable
  marker AND NOT a conftest-load marker. Positive-evidence precondition (per
  `.claude/rules/absence-of-failure-is-not-success.md`); biases to *failure* on
  ambiguity (empty stream → not neutral).
- In `run_bdd_for_task`, between the exit-5→None block and the F584 runner-error
  block: if `passed==0 and not failures and not pending and
  _is_absent_feature_collection(invocation)` → log + `return None`.
- F584's net unchanged for everything else (conftest ImportError, exit 2/3,
  empty-stream exit-4, timeout) → still synthetic failure.

## Half 2 — Auto-install bridge

- **New** `guardkit/templates/conftest_bridge.py` ::
  `install_features_conftest_bridge(target_dir) -> bool`. Single source of truth.
  Guards: `features/` dir with ≥1 `.feature` file present; no existing
  `features/conftest.py`; template resolvable. Never clobbers; never raises.
- Wire 1 (autobuild bootstrap): `WorktreeManager.create()` before returning the
  `Worktree` — single chokepoint for both task and feature worktrees. Safe no-op
  for non-BDD worktrees.
- Wire 2 (`guardkit init`): `_cmd_init` after `apply_template`.

## Tests

- `tests/unit/orchestrator/quality_gates/test_bdd_runner.py`: repurpose the 2
  conflicting F584 tests (exit-4 "not found" → failure) to genuine exit-4 conftest
  ImportError; add `TestAbsentFeatureCollectionIsNeutral` (not-found→None,
  file-not-found→None, conftest-import→failure, empty-stream→failure,
  collected-testcases-not-neutral, end-to-end Coach neutral). Keep AC-2: a real
  failing scenario still → `failed`.
- **New** `tests/unit/templates/test_conftest_bridge.py`: install, no-clobber,
  no-features no-op, no-.feature-files no-op, missing-template no-op, idempotent.
- **New** `tests/integration/test_worktree_conftest_bridge.py`: real-git
  `WorktreeManager.create()` with a committed `.feature` installs the bridge.

## Acceptance criteria mapping

- AC-1 (no matching `.feature` / exit-4 absent → not_applicable/absent, never a
  failure in tally or checkpoint) → Half 1; `None` ⇒ `bdd_results` key absent ⇒
  no gate, no checkpoint contribution.
- AC-2 (real scenario failure still `failed`) → unchanged JUnit-failure path +
  explicit test.
- AC-3 (init / bootstrap auto-installs bridge, guarded) → Half 2.
- AC-4 (regression tests both directions) → test additions above.
