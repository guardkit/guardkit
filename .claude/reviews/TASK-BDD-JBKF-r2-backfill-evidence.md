# TASK-BDD-JBKF — R2 Backfill Evidence

**Date:** 2026-04-22
**Task:** TASK-BDD-JBKF — Backfill R2 activation on jarvis by tagging scenarios and running pytest-bdd
**Status at write-time:** in_progress → will transition to in_review
**Parent:** TASK-REV-4D190 (jarvis-first autobuild review)
**Target of verification:** TASK-BDD-E8954 (R2 BDD oracle)

---

## TL;DR — Outcome D (P0 defect in R2)

Tagging two jarvis scenarios and invoking `bdd_runner.run_bdd_for_task(...)` produced neither the desired three-state result (Outcome A) nor either of the two previously contemplated defects (Outcomes B, C). Instead, a **fourth** failure mode was surfaced:

> **Outcome D — silent approval on pytest usage error.**
> `BDDResult` is returned (not `None`), with `scenarios_passed=0, scenarios_failed=0, scenarios_pending=0` and empty `failures`/`pending` lists. pytest's returncode was **4** (USAGE_ERROR) — not 5 (NO_TESTS_COLLECTED) — so the third silent-skip path at `bdd_runner.py:430-441` did **not** fire. Coach's approval rule (`bdd_results.scenarios_failed == 0`) would **approve this task while nothing actually ran**.

This is a strictly worse failure mode than either B (pending collapsed into failed, would be caught as a false-positive block) or C (silent-skip via path 3, would be caught by any cohort-task post-run null check). Outcome D produces **silent false approval**, which is the single most dangerous oracle outcome — a green light on an unverified implementation. It affects every cohort task tagged with `@task:` whose environment lacks pytest-bdd glue OR whose pytest invocation produces any non-zero exit code other than 5.

**Recommendation:** File P0 defect against TASK-BDD-E8954; block TASK-COH-RUN1 R2 pre-flight on the fix.

---

## Probes performed

### Setup

- Throwaway venv in jarvis working copy: `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.venv-r2-probe/`
- Installed: `pytest 9.0.3`, `pytest-bdd 8.1.0` (installed into the throwaway venv only — **not** added to `jarvis/pyproject.toml`).
- Feature file (working copy only, **not committed to jarvis main**):
  `/Users/richardwoollcott/Projects/appmilla_github/jarvis/features/project-scaffolding-supervisor-sessions/project-scaffolding-supervisor-sessions.feature`

Working-copy diff added these two tags:

```diff
   # Why: "version" is the smallest self-test for the installed package
+  @task:TASK-J001-001
   @key-example @smoke
   Scenario: Rich checks the installed jarvis version
```

```diff
   # Why: Running "jarvis" with no arguments should be discoverable (prints command list)
+  @task:TASK-J001-006
   @key-example
   Scenario: Running jarvis with no command prints the available commands
```

Runner invocation (from `guardkit` repo via `.claude/reviews/jbkf_probe.py`):

```python
run_bdd_for_task(
    task_id="TASK-J001-001",  # and TASK-J001-006
    worktree_path=Path("/Users/richardwoollcott/Projects/appmilla_github/jarvis"),
    python_executable="/Users/richardwoollcott/Projects/appmilla_github/jarvis/.venv-r2-probe/bin/python",
    features_subdir="features/project-scaffolding-supervisor-sessions",
    timeout=120,
)
```

Note: `features_subdir` was overridden from the default `"features"` because the jarvis feature file is nested one level deeper. With the default, `find_feature_files_with_tag` (non-recursive glob) would miss the file and the runner would return `None` via silent-skip path (1). **That nested-feature non-discovery is a separate pre-existing weakness of R2 worth noting** but is orthogonal to the primary finding below.

### Probe 1 — glue-less (no conftest.py, no step defs)

Raw captured output from the runner's subprocess:

```
ERROR: not found: /Users/richardwoollcott/Projects/appmilla_github/jarvis/features/project-scaffolding-supervisor-sessions/project-scaffolding-supervisor-sessions.feature
(no match in any of [<Dir project-scaffolding-supervisor-sessions>])
```

Manual pytest re-run to capture exit code:

```
$ cd /Users/richardwoollcott/Projects/appmilla_github/jarvis
$ .venv-r2-probe/bin/python -m pytest --gherkin-terminal-reporter \
      -m task_TASK_J001_001 \
      features/project-scaffolding-supervisor-sessions/project-scaffolding-supervisor-sessions.feature
PYTEST_EXIT_CODE=4
```

`BDDResult` returned by the runner:

```json
{
  "scenarios_passed": 0,
  "scenarios_failed": 0,
  "scenarios_pending": 0,
  "failures": [],
  "pending": [],
  "feature_files": ["features/project-scaffolding-supervisor-sessions/project-scaffolding-supervisor-sessions.feature"],
  "tag": "@task:TASK-J001-001"
}
```

**Both tagged task IDs (`TASK-J001-001`, `TASK-J001-006`) produced identical structure.** Full capture: `.claude/reviews/TASK-BDD-JBKF-probe-output.json`.

### Probe 2 — with minimal pytest-bdd glue (conftest.py calling `scenarios()`)

Added a minimal conftest.py beside the feature file:

```python
# features/project-scaffolding-supervisor-sessions/conftest.py (working copy only)
from pytest_bdd import scenarios
scenarios("project-scaffolding-supervisor-sessions.feature")
```

Raw captured output:

```
ImportError while loading conftest '.../features/.../conftest.py'.
features/project-scaffolding-supervisor-sessions/conftest.py:13: in <module>
    scenarios("project-scaffolding-supervisor-sessions.feature")
.venv-r2-probe/lib/python3.14/site-packages/pytest_bdd/scenario.py:448: in scenarios
    features_base_dir = get_features_base_dir(caller_path)
.venv-r2-probe/lib/python3.14/site-packages/pytest_bdd/scenario.py:388: in get_features_base_dir
    d = get_from_ini("bdd_features_base_dir")
.venv-r2-probe/lib/python3.14/site-packages/pytest_bdd/scenario.py:400: in get_from_ini
    config = CONFIG_STACK[-1]
E   IndexError: list index out of range
```

`PYTEST_EXIT_CODE=4` (verified manually).

`BDDResult` returned by the runner: **identical to Probe 1** — `(0, 0, 0)` with empty lists. Full capture: `.claude/reviews/TASK-BDD-JBKF-probe-output-with-glue.json`.

Probe 2 is evidence that the defect is **not** specific to a missing-conftest setup — any pytest invocation path that errors with returncode ≠ 5 produces the same silent-approval outcome. (It also incidentally surfaces that pytest-bdd 8.x's `scenarios()` at module-import time errors with `IndexError: CONFIG_STACK[-1]` when called from a conftest.py without a prior pytest-bdd config section. That's a pytest-bdd 8.x usage issue, not an R2 defect — but it strengthens the primary finding because it shows a second distinct code path into Outcome D.)

---

## Outcome classification against the re-scoped AC

| AC outcome | Condition | Occurred? |
|---|---|---|
| **A (desired)** | `BDDResult` ≠ None, `scenarios_pending > 0`, `scenarios_failed == 0` | ❌ |
| **B (P0: pending→failed collapse)** | `scenarios_failed > 0` | ❌ |
| **C (P0: silent-skip via path 3)** | `BDDResult` is `None` via `returncode == 5` | ❌ |
| **D (NEW — P0 silent false approval)** | `BDDResult = (0,0,0)` returned despite pytest error, returncode ≠ 5 | ✅ |

Outcome D was not enumerated in either the original or re-scoped AC. The re-scoped AC anticipated that pytest-bdd-without-glue would either (i) report pending (Outcome A) or (ii) hit `returncode == 5` and silent-skip (Outcome C). Neither happened. pytest-bdd without glue errors with `returncode == 4` (usage error: "not found"), and the runner's guard only catches `returncode == 5`.

---

## Defect analysis — what to file against TASK-BDD-E8954

**Defect class:** silent false approval. `BDDResult(0, 0, 0)` is returned for pytest invocations that errored for reasons other than "no tests collected". Coach's approval rule (`bdd_results.scenarios_failed == 0`) approves this result, which means **any `@task:`-tagged feature whose environment has any of the following** produces a false green oracle signal:

- pytest-bdd installed but no step-def glue (conftest with `scenarios()` or step-def modules)
- pytest-bdd glue present but errors at conftest import time (e.g., pytest-bdd 8.x `CONFIG_STACK[-1]` issue)
- Any future pytest usage error that produces returncode 4 instead of 5

**Proposed fix (for R2 bug ticket):** in `bdd_runner.run_bdd_for_task`, treat the result as untrustworthy when **all three** of the following hold:

1. `passed == 0 and not failures and not pending`
2. `returncode != 0`  (not just `!= 5`)
3. No JUnit XML testcases were emitted

In that case, either return `None` (escalate to silent-skip, caught by a Coach post-run null check) **or** surface as a distinct `FailureDetail` with `reason="runner_error"` (caught by the existing `scenarios_failed > 0` rule). The latter is preferred because it keeps Coach's rule simple and makes the signal loud.

**Secondary defect (lower priority):** `find_feature_files_with_tag` is non-recursive, so nested feature files under `features/<subdir>/` are invisible under the default `features_subdir="features"`. Jarvis's scaffold already produces this nested layout (`features/project-scaffolding-supervisor-sessions/...feature`). Any cohort task that follows the same scaffold convention will silent-skip via path (1) without this fix.

---

## Cleanup (pre-close)

Before closing TASK-BDD-JBKF, the following jarvis working-copy changes must be reverted:

- `features/project-scaffolding-supervisor-sessions/project-scaffolding-supervisor-sessions.feature` — remove `@task:TASK-J001-001` and `@task:TASK-J001-006` tag lines.
- `.venv-r2-probe/` — delete directory.
- `.guardkit/bdd/` — delete if created by runner (may contain stale JUnit XML).
- `features/project-scaffolding-supervisor-sessions/conftest.py` — already removed as part of Probe 2 cleanup; confirm absent.

jarvis `main` branch must not contain any of the above.

---

## Next actions

1. **File P0 defect** as `TASK-FIX-R2S-???` (silent false approval on pytest usage errors) against TASK-BDD-E8954. Include this evidence file as proof.
2. **Mark TASK-COH-RUN1 R2 pre-flight as a hard block** on the P0 fix landing.
3. **Optionally file a secondary defect** for the nested-feature non-discovery issue in `find_feature_files_with_tag`.
4. **Revert jarvis working copy** (see Cleanup).
5. **Move TASK-BDD-JBKF to in_review** with this evidence file referenced.

---

## Artefacts

- `.claude/reviews/jbkf_probe.py` — probe script (keep; small, reproducible).
- `.claude/reviews/TASK-BDD-JBKF-probe-output.json` — Probe 1 capture (glue-less).
- `.claude/reviews/TASK-BDD-JBKF-probe-output-with-glue.json` — Probe 2 capture (with conftest glue).
- `.claude/reviews/TASK-BDD-JBKF-probe-output-post-fix.json` — Post-fix re-run capture (TASK-FIX-F584 applied).
- `/tmp/jbkf_pytest_stdout.log`, `/tmp/jbkf_pytest_stderr.log`, `/tmp/jbkf_pytest_noglue_stdout.log`, `/tmp/jbkf_pytest_noglue_stderr.log` — raw manual pytest captures (exit code 4 confirmed). Ephemeral.

---

## Post-fix re-run (TASK-FIX-F584 applied)

**Date:** 2026-04-22
**Fix:** TASK-FIX-F584 — runner-error surfacing + recursive feature discovery
**Verification:** Outcome D (silent false approval) no longer occurs.

### Re-run setup

- Throwaway venv recreated at `jarvis/.venv-r2-probe/` (pytest 9.0.3, pytest-bdd 8.x).
- `@task:TASK-J001-001` tag re-added to `Rich checks the installed jarvis version` scenario (working copy only).
- Ran `python3 .claude/reviews/jbkf_probe.py` from guardkit with bdd_runner.py at HEAD of TASK-FIX-F584 (post-fix).
- Cleanup after re-run: tag reverted, `.venv-r2-probe/` deleted, `__pycache__` cleared, `.guardkit/bdd/` removed. Jarvis working copy clean (no diff in `features/`).

### Probe 1 (TASK-J001-001, glue-less) — post-fix result

Raw `BDDResult` returned by the runner (full capture: `TASK-BDD-JBKF-probe-output-post-fix.json`):

```json
{
  "scenarios_passed": 0,
  "scenarios_failed": 1,
  "scenarios_pending": 0,
  "failures": [
    {
      "feature_file": "/.../project-scaffolding-supervisor-sessions.feature",
      "scenario_name": "pytest_runner_error",
      "failing_step": "",
      "reason": "pytest_runner_error: exit=4; ERROR: not found: /.../project-scaffolding-supervisor-sessions.feature\n(no match in any of [<Dir pro..."
    }
  ],
  "pending": [],
  "tag": "@task:TASK-J001-001"
}
```

And the runner emitted a `logger.warning` (INFO-level visibility for Coach's human-readable feedback):

```
BDD runner for TASK-J001-001: pytest exited with 4 and produced no testcases;
surfacing as synthetic failure. First 200 chars of stderr/stdout:
'ERROR: not found: /.../project-scaffolding-supervisor-sessions.feature
(no match in any of [<Dir pro'
```

### Outcome classification — post-fix

| Outcome | Condition | Occurred? |
|---|---|---|
| **A (desired three-state)** | `BDDResult` ≠ None, `scenarios_pending > 0`, `scenarios_failed == 0` | ❌ (still blocked by conftest-free environment — unrelated to this fix) |
| **B (pending→failed collapse)** | N/A — no scenarios collected | ❌ |
| **C (silent-skip via path 3)** | `BDDResult` is `None` via `returncode == 5` | ❌ |
| **D (silent false approval, pre-fix)** | `BDDResult = (0,0,0)` returned despite pytest error, returncode ≠ 5 | ❌ ← **fix confirmed** |
| **E (runner-error surfaced, post-fix)** | `BDDResult` ≠ None, `scenarios_failed == 1`, reason names `pytest_runner_error: exit=4` | ✅ |

Coach's approval rule (`bdd_results.scenarios_failed == 0`) now **rejects** this result. The silent-false-approval failure mode is eliminated for returncodes 2/3/4 (verified by unit tests) and confirmed end-to-end for returncode=4 against the real jarvis environment.

### Remaining out-of-scope notes

- Reaching Outcome A still requires pytest-bdd step-def glue in the target worktree — this is a cohort-task prerequisite, not a runner bug.
- Probe 2 (conftest with `scenarios()` call) was not re-run; the pytest-bdd 8.x `CONFIG_STACK[-1]` issue is a separate pytest-bdd usage problem and is already covered by the exit-code-4 generalisation.
- `parse_junit_xml("")` returning `(0,0,0)` rather than signalling empty-parse remains as an upstream contributor to this bug class — tracked as an out-of-scope follow-up in TASK-FIX-F584's Implementation Notes.
