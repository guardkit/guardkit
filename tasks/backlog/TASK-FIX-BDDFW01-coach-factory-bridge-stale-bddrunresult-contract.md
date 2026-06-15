---
id: TASK-FIX-BDDFW01
title: Fix Coach BDD-factory bridge — mapper/discover/stack-profile target a stale BDDRunResult contract (silently dead on the live path)
status: backlog
task_type: fix
created: 2026-06-15T00:00:00Z
updated: 2026-06-15T00:00:00Z
priority: high
complexity: 5
related: [TASK-BDDW-001, TASK-BDDW-002, TASK-HMIG-BDDWIRE, TASK-REV-STKB, TASK-INFRA-XREPOCONTRACT]
implementation_mode: task-work
tags: [autobuild, coach, bdd, guardkitfactory, cross-repo-contract, silent-degradation, stale-contract, absence-of-failure]
---

# Task: Fix Coach BDD-factory wiring — production mapper/discover/stack-profile target a stale BDDRunResult contract; reconcile the failing wiring test

> **Provenance.** Surfaced while completing TASK-FIX-EVBINST02 (a pre-existing
> collection error was flagged), then root-caused by a multi-agent
> investigation (4 parallel angles + 3 adversarial verifiers, all of which
> **refuted** the initial "stale test, rename the import" hypothesis). The
> three production mismatches and the live-path reachability below were
> independently re-verified by hand against the real files before filing.

## Why this task exists

`tests/integration/orchestrator/test_coach_validator_bdd_factory_wiring.py`
fails at **collection** with `ImportError: cannot import name
'map_bdd_run_result'`. The obvious read — "stale test, rename the import" —
is **wrong and dangerous**. A pure rename only converts the collection-time
`ImportError` into a runtime `AttributeError`/`TypeError` against real
production, because the **production BDD-factory bridge in `coach_validator.py`
was written against an abandoned `guardkitfactory` contract and has never been
exercised against the real one.**

The bridge is the deliverable of **TASK-BDDW-001** (completed,
`tasks/completed/bddwire/`). On the live deterministic Coach path it is
currently **silently dead**: whenever its branch is taken it raises, the raise
is swallowed by a broad `except Exception`, and the Coach falls back to the
legacy Player-reported `bdd_results`. The failing wiring test is the *only*
test that constructs the **real** `BDDRunResult` and would catch this; the
sibling `test_bdd_factory_bridge.py` is green only because it uses a local
fake (`_FakeBDDRunResult`) that mirrors the stale shape.

## Root cause

**Primary (production defect, live path).** `CoachValidator.gather_evidence`
(`coach_validator.py:2704-2705`) calls `_detect_stack_profile` then
`_run_factory_bdd`, which calls `discover` (`:319`), `plugin.run()` (`:331`),
and `_map_bdd_run_result_to_bundle` (`:342`). Three contract mismatches against
the real `guardkitfactory`:

1. **`discover` arity/type** — production calls `discover(stack_profile)` with
   ONE positional `str` (`coach_validator.py:319`); the real signature is
   `discover(stack: StackProfile, worktree: Path)`
   (`guardkitfactory/src/guardkitfactory/bdd/loader.py:52`). Verified:
   `discover('python')` raises `TypeError: missing 1 required positional
   argument: 'worktree'`.
2. **`_detect_stack_profile` return type** — annotated `-> Optional[str]`,
   returns `_STACK_PROFILE_MAP.get(template)` i.e. a plain `str`
   (`coach_validator.py:144,161`); `discover` needs a `StackProfile` dataclass
   (`language/test_framework/package_manager/project_root/extras`).
3. **`_map_bdd_run_result_to_bundle` field names** — reads `run_result.failures`
   (`:190`), `.pending` (`:191`), `.scenarios_pending` (`:223`),
   `.feature_files` (`:226`); NONE exist on the real `BDDRunResult` (real
   fields: `scenarios_attempted/passed/failed/skipped/errored`,
   `duration_seconds`, `raw_report_path`, `discoveries`, `errors` —
   `guardkitfactory/src/guardkitfactory/bdd/plugin.py:43-62`). Verified:
   `_map_bdd_run_result_to_bundle(<real BDDRunResult>)` raises
   `AttributeError: 'BDDRunResult' object has no attribute 'failures'`.

The crash is swallowed by `except Exception` at `coach_validator.py:344`
(`# noqa: BLE001 — BDD failures must not break evidence gathering`), logged as a
warning, and degraded to the legacy fallback — so the defect is **silent**. The
stale mapping doc-comment at `coach_validator.py:113-125` still documents the
abandoned field names, confirming the code targets the obsolete shape.

**Secondary (test-side stale symbols).** The failing test imports two names that
never shipped on main:
- `map_bdd_run_result` (`test...wiring.py:28`) — production exports private
  `_map_bdd_run_result_to_bundle` only; the public name existed solely in an
  abandoned `bdd_plugin_wiring.py` in orphan checkpoint `66ad36ef` (marked
  *tests: fail*), never merged.
- `_GUARDKITFACTORY_AVAILABLE` (`test...wiring.py:327`) — production has
  `_FACTORY_AVAILABLE`.

The test entered main via commit `740e1585` ('tidy up', 2026-06-13) without
reconciling to the shipped private API, so it has been **dead on arrival**
(never collectable on any main-ancestry commit).

## Fix

Production first, then reconcile the test to the corrected production — do not
paper over with a rename.

1. **`_detect_stack_profile`** — return a real `guardkitfactory` `StackProfile`
   (construct it from the detected template string + worktree root), or keep
   returning the str and have `_run_factory_bdd` build the `StackProfile`.
   Update the return annotation accordingly.
2. **`_run_factory_bdd`** — call `discover(stack_profile, worktree_path)` with
   the correct 2-arg signature.
3. **`_map_bdd_run_result_to_bundle`** — rewrite against real `BDDRunResult`
   fields: emit `scenarios_errored`, `duration_seconds`, `raw_report_path`;
   derive `feature_files` from `discoveries`; derive `failures[*]['error']`
   from `errors`; derive `scenarios_pending` from `scenarios_skipped`.
   **Preserve `scenarios_attempted` verbatim** (never coerce 0) so the
   absence-of-failure gate still reads 0 as ABSENT SIGNAL.
4. **Doc-comment** — update `coach_validator.py:113-125` to the real field
   names.
5. **Legacy consumers** — realign `_check_bdd_results` (reads
   `scenarios_pending`/`failures`/`pending`) and the sibling test's
   `_FakeBDDRunResult` so ONE coherent `bundle.bdd` shape satisfies both tests.
6. **Test reconciliation** — fix the two stale imports (`map_bdd_run_result` ->
   the now-correct mapper symbol; `_GUARDKITFACTORY_AVAILABLE` ->
   `_FACTORY_AVAILABLE`). Either alias the mapper publicly or update the test to
   the private name — pick whichever keeps both tests coherent.
7. **No new silent masking** — an unsupported stack must remain ABSENT SIGNAL
   (`None` + logged warning), never a silent pass.

## Acceptance Criteria

- [ ] `python -m pytest tests/integration/orchestrator/test_coach_validator_bdd_factory_wiring.py -o addopts= -q` collects and exits 0 (all tests pass).
- [ ] The test's two stale imports are reconciled; no symbol it imports is absent from `coach_validator.py`.
- [ ] `_run_factory_bdd` calls `discover(stack: StackProfile, worktree: Path)` correctly — no `TypeError` on the live path.
- [ ] `_detect_stack_profile` returns a `discover`-compatible value; `test_detect_stack_profile_returns_python` (`.language`/`.test_framework`) passes against real production.
- [ ] `_map_bdd_run_result_to_bundle` reads only real `BDDRunResult` fields; calling it on a real instance does NOT raise `AttributeError`.
- [ ] Mapper emits `scenarios_errored`, `duration_seconds`, `raw_report_path`, `feature_files` (from `discoveries`), `failures[*]['error']` (from `errors`), `scenarios_pending` (from `scenarios_skipped`); `scenarios_attempted` preserved verbatim.
- [ ] The stale mapping comment (`coach_validator.py:113-125`) documents the real field names.
- [ ] GUARD: `python -m pytest tests/integration/orchestrator/test_bdd_factory_bridge.py -o addopts= -q` -> 8 passed (realign its `_FakeBDDRunResult`/`_check_bdd_results` if needed so both tests share one contract).
- [ ] `python -m pytest tests/ --co -q -o addopts=` reports 0 collection errors (currently 1).
- [ ] No new broad-except masking; unsupported stack surfaces as ABSENT SIGNAL, never a silent pass (`.claude/rules/absence-of-failure-is-not-success.md`).

## Evidence

- `coach_validator.py:319` `discover(stack_profile)` (1 arg) vs `guardkitfactory/src/guardkitfactory/bdd/loader.py:52` `def discover(stack: StackProfile, worktree: Path)` — verified `TypeError` on 1-arg call.
- `coach_validator.py:144,161` `_detect_stack_profile -> Optional[str]` returning a plain str — verified via `inspect`.
- `coach_validator.py:190-191,223,226` read `.failures/.pending/.scenarios_pending/.feature_files` — verified `hasattr` False for all four on a real `BDDRunResult`.
- Real fields: `guardkitfactory/src/guardkitfactory/bdd/plugin.py:43-62`.
- Verified: `_map_bdd_run_result_to_bundle(<real BDDRunResult>)` -> `AttributeError: 'BDDRunResult' object has no attribute 'failures'`.
- Live path: `gather_evidence` `coach_validator.py:2704-2705` -> `_run_factory_bdd` `:319/331/342`; broad `except Exception` `:344` swallows + logs the fallback (factory path silently dead). Branch condition: factory available AND Player produced no `bdd_results` (`coach_validator.py:2690-2705`).
- Test stale imports: `test...wiring.py:28` `map_bdd_run_result` (absent), `:327` `_GUARDKITFACTORY_AVAILABLE` (absent; prod has `_FACTORY_AVAILABLE`) — verified.
- Collection error: `pytest tests/ --co` -> `1 error`; single-module -> `ImportError: cannot import name 'map_bdd_run_result'`.
- Sibling green via stub: `pytest tests/integration/orchestrator/test_bdd_factory_bridge.py` -> 8 passed; its local `_FakeBDDRunResult` mirrors the stale shape.
- Git: failing test added by `740e1585` ('tidy up', 2026-06-13); public `map_bdd_run_result` existed only in `bdd_plugin_wiring.py` in orphan checkpoint `66ad36ef` (*tests: fail*), never on main; production fn private from birth.
- Stale doc-comment: `coach_validator.py:113-125` documents the abandoned `.failures/.pending/.scenarios_pending/.feature_files` mapping.

## Notes

**Broader class.** This is a fresh instance of the project's own
*tests-pass-via-stub-fake / absence-of-failure-is-not-success* family
(`.claude/rules/absence-of-failure-is-not-success.md`, `namespace-hygiene.md`,
`smoke-gate-is-feedback-not-terminator.md` arm b). The sibling test is green
because its local `_FakeBDDRunResult` mirrors the obsolete production
assumption — a low-fidelity stub oracle masking a real cross-repo contract
drift across the **guardkit ↔ guardkitfactory** seam
(`BDDRunResult`/`StackProfile`/`discover`). The broad `except Exception` at
`coach_validator.py:344` is the silent-degradation mechanism that hid the
defect end-to-end: the TASK-BDDW-001 deliverable is effectively unwired but the
autobuild loop never visibly fails.

**Recurrence prevention (recommended follow-up, not in scope).** Add an
executable cross-repo seam test — the analogue of
`tests/orchestrator/harness/test_xrepo_contract_seam.py`
(TASK-INFRA-XREPOCONTRACT) — that asserts the orchestrator's actual calls
(`discover` arity, the `BDDRunResult` field reads) against the **real
installed** `guardkitfactory` via `inspect`/`dataclasses`, run in the
merge-gating `seam-tests.yml`. Then a future `BDDRunResult` field rename is a
red CI build, not a silently-dead branch.

**CI gap to investigate (separate task worth filing).** This collection
`ImportError` should already be a red merge gate via
`.github/workflows/tests.yml` (full `pytest tests/`, exit 2 on collection
error). The quarantine in `tests/conftest.py` cannot mask it
(`pytest_collection_modifyitems` runs post-collection and the module isn't
quarantined). Investigate why `740e1585` was not blocked.

**Relationship to adjacent BDD tasks (checked, NOT duplicates).**
- **FEAT-BDDM** (`tasks/backlog/bdd-runner-silent-bypass-fix/`) is a *different*
  code path — the legacy `bdd_runner.py` silently skipping when `pytest-bdd` is
  missing. This task is about the *factory bridge* in `coach_validator.py`
  targeting a stale `BDDRunResult` contract. Same meta-class
  (silent BDD degradation), different mechanism and different code.
- **TASK-HMIG-BDDWIRE** (`tasks/backlog/`, status backlog) is titled "wire the
  factory BDD subsystem into the Coach" and asserts "nothing in the orchestrator
  consumes" it. That premise is **stale**: TASK-BDDW-001 already wired it (the
  code this task fixes). Whoever picks up either task should reconcile the two —
  TASK-HMIG-BDDWIRE may be fully or partially superseded by BDDW-001, and its
  remaining value (if any) is making the *correct* wiring that this task lands
  robust. Flag for triage.

**Isolation.** Tree-wide there is exactly ONE collection error; the other
BDD-bridge tests (`test_bdd_factory_bridge.py`,
`tests/orchestrator/test_qawe_004_spec_gap.py`) use correct names and
collect/pass. No sibling stale references exist beyond the two symbol-name
imports inside the one failing file.
