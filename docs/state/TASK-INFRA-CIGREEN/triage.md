# TASK-INFRA-CIGREEN — full-suite triage & burn-down plan

> 2026-06-11. Environment: **Python 3.12.3**, `pip install -e ".[dev]"` +
> `claude-agent-sdk>=0.1.49,<0.2` + `pytest-timeout`. Command:
> `pytest tests/ -o addopts="" --timeout=60 --timeout-method=thread
> --continue-on-collection-errors`.

## Headline

The task assumed ~26 version-related failures that vanish under 3.12. **Reality:
the suite was deeply red and had never run to completion.** It hung on a `flock`
deadlock; once that was fixed the full run reported:

| Result | Count |
|---|---|
| passed | **14,041** |
| skipped | 1,213 |
| **failed** | **468** |
| **errors** | **50** |
| **failed + errored (unique nodes)** | **518** |

All 518 are **pre-existing** — none are caused by this task's changes (version
floor, lint stubs, the deadlock fix, the collection-error `importorskip`
guards). The suite rotted unnoticed precisely because there was no CI gating it,
which is the motivation in the task brief.

## Blocker fixed first: `flock` deadlock (was hanging the whole suite)

`installer/core/lib/external_id_persistence.py` — `load_mappings()` /
`load_counters()` called their recursive backup-retry **inside** the
`with self._file_lock(path):` block. The retry re-acquired the same
`fcntl.flock(LOCK_EX)` on a second fd of the same file in the same process →
permanent deadlock. Triggered by
`tests/lib/test_external_id_persistence.py::test_load_prevents_infinite_recursion`
(corrupt main + corrupt backup). Fix: defer the restore + recursive retry to
**after** the lock releases. `--timeout-method=thread` could not kill the
C-level `flock`, so this had to be fixed before any complete run was possible.

## First catch by the new gate: a real 3.11 incompatibility

The local triage ran on 3.12 only (no 3.11 interpreter available locally), so the
quarantine was 3.12-derived. The very first CI run surfaced a **3.11-specific**
cluster the quarantine couldn't have known about: `template_packager.py:176` used
`Path.walk()`, which **only exists on Python 3.12+**, so all 14
`tests/test_template_packager.py::TestTemplatePackager` tests raised
`AttributeError: 'PosixPath' object has no attribute 'walk'` on the 3.11 leg
(green on 3.12). Fixed by switching to `os.walk()` (3.11+) — *not* quarantined,
because it was a genuine bug in shipped code on the supported floor. This is
exactly the class of regression the gate exists to catch.

## The 518 by bucket

| Bucket | ~Count | Root cause | Representative modules |
|---|---|---|---|
| **A. Foreign-machine paths** | ~74 | Tests hardcode `/Users/.../ai-engineer/...` (the old repo name, a Mac) — can't pass on any other host | `test_task_011e_documentation`, `test_task_011f_validation`, `test_task_007_documentation_validation` |
| **B. SSIM / scikit-image** | ~107 lines (~21 tests) | Need `scikit-image` + `pillow` (not a guardkit dep) | `tests/orchestrator/test_visual_comparator.py` |
| **C. FalkorDB** | ~12 | Need `graphiti-core[falkordb]` | `tests/knowledge/test_falkordb_workaround.py`, `test_graph_store_config.py` |
| **D. SDK-in-subprocess** | ~32 | Coach spawns a *separate* interpreter that lacks `claude_agent_sdk` | `tests/seam/test_autobuild_coach.py`, `test_sdk_environment_parity.py` |
| **E. Stale mocks** | ~182 | Orchestrator code evolved; mocks not updated (`int < Mock`, `a coroutine was expected, got <Mock>`, `Mock has no attribute …`) | `tests/unit/test_autobuild_orchestrator.py`, `test_autobuild_task_type.py` |
| **F. Doc/template drift** | ~110 | Assert specific docs/templates exist that are missing/moved (maui-appshell, fastmcp-python scaffolds) | `tests/unit/test_fastmcp_templates.py`, `tests/templates/test_maui_appshell_structure.py`, `tests/docs/test_gr005_completion.py` |

(Buckets overlap at the edges — e.g. A's foreign paths surface inside F's
doc-validation modules. Counts are by symptom, not partition.)

## What this task changed

1. **Version floor → `>=3.11`** (`pyproject.toml`): drops the 3.10 classifier;
   the orchestrator's `asyncio.timeout()` is 3.11+. (AC-2)
2. **Dead-task-ID lint green** (AC-3): filed 9 provenance records under
   `docs/state/` for real historical/cross-repo task references, and
   placeholdered one docstring *example* (`preflight.py`).
3. **`flock` deadlock fixed** so the suite can complete.
4. **`importorskip` guards** on the 6 collection-error modules
   (`claude_agent_sdk` ×4, `langchain_core` ×1, `fastapi` ×1) so they skip
   cleanly instead of erroring at collection. (AC-4)
5. **Quarantine** (`tests/quarantine.txt` + `tests/conftest.py`): the 518
   pre-existing reds are skipped with a documented reason so the gate is green
   and catches new regressions. (AC-5)
6. **`tests.yml`** runs the suite on 3.11 + 3.12 on push/PR. (AC-6)

## Burn-down plan (follow-up: TASK-INFRA-CIGREEN-BURN)

Each bucket is independently fixable; remove lines from `tests/quarantine.txt`
as they go green (run `GUARDKIT_NO_QUARANTINE=1 pytest tests/<module>` to work
on the red set):

- **A (foreign paths)**: rewrite the absolute `/Users/.../ai-engineer/` paths
  to repo-relative paths, or delete the obsolete duplicate-file assertions.
- **B (SSIM)**: `importorskip("skimage")` at the top of `test_visual_comparator`
  (and add `scikit-image`+`pillow` to a `viz` extra) — they then run where the
  dep is present.
- **C (FalkorDB)**: `importorskip("falkordb")` / mark `requires_falkordb`.
- **D (SDK-subprocess)**: make the coach subprocess inherit the SDK-bearing
  interpreter, or skip when the child interpreter can't import the SDK.
- **E (stale mocks)**: update the mocks to the current orchestrator signatures
  (return ints/awaitables where the code now compares/awaits). Highest-value —
  these are genuine orchestrator tests.
- **F (doc/template drift)**: decide per module whether the missing scaffold
  should exist (regenerate it) or the assertion is obsolete (delete it).
