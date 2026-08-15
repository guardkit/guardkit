# Test-debt triage — 2026-08-14

**Subject.** 141 pre-existing failing tests across `tests/unit` + `tests/integration`
on `main`. Not caused by any lane landed that day — the same failures reproduce on
an untouched checkout. Every future lane was paying for them in
differential-verification overhead: you cannot tell "my change broke something" from
"this was already red" without re-measuring the whole baseline first.

**What this lane did.** Fixed 71 of them and honestly skipped 2, touching **tests,
fixtures and test-only plumbing only**. The other 68 are ledgered below with a
diagnosis each. Four of those are the valuable output: they are tests that are
probably *right*, pointing at production code that is probably wrong.

**Scope fence.** No production file was changed. Any failure whose honest cure needs
a production change was ledgered, never fixed — a production change deserves its own
coach-gated lane. No test was deleted.

---

## Counts

Measured in this lane's own venv (fresh worktree, `uv venv --python 3.12 && uv sync
--all-extras`, Python 3.12.3), running `pytest tests/unit tests/integration`.
Absolute counts drift between venvs, so these are differential against this venv's
own baseline, taken before any edit:

| | Failed | Passed | Skipped | xfail |
|---|---|---|---|---|
| **Before** | 141 | 10,183 | 318 | 1 |
| **After** | **68** | **10,254** | **320** | 1 |
| Change | **−73** | +71 | +2 | 0 |

**Zero new failures.** The 68 that remain are a strict subset of the original 141
— nothing that passed before this lane fails after it.

The −73 is 71 tests made to pass plus 2 turned into honest, reasoned skips.

**Amended 2026-08-15.** The F12 correction below moved one of those two skips
back to passing and added a new in-process test, so the current shape is 72 cured
+ 1 skipped. Re-measured in a fresh worktree on Python 3.14.4, where absolute
counts sit two higher for interpreter reasons (see caution 8): 70 failed /
10,254 passed / 319 skipped, against 70 / 10,252 / 320 for the lane before the
correction. No failure set changed.

**Amended again 2026-08-15 — L1 cured.** `lane/archival-fix-0815` fixed the
production defect this lane refused to paper over. Same matched-venv method:
**70 → 63 failed**, 10,254 → 10,261 passed, the seven `test_feature_archival.py`
tests green **unchanged**, zero added failures. The ledger below is 68 → **61**.
Details in "Two findings that outrank the arithmetic" §2.

---

## Two findings that outrank the arithmetic

### 1. The suite was reading the repo's own config and the machine's own PATH

Six failures came from guardkit's own `.guardkit/config.yaml` — which pins
`autobuild.coach.contract: v4` — leaking into tests that assert the *code* default
(`coachsplit`). The resolver falls through the environment variable to the **current
directory's** config, so those tests silently measured the repo's configuration
instead of the behaviour they described. Their result depended on where the suite
was run. That is worse than being red: run from anywhere else they would have gone
green while testing nothing.

One more failure came from a fixture shelling out to a bare `python`, which does not
exist on this machine (only `python3`).

Worse, `tests/unit/orchestrator/test_coach_output_parser.py::test_default_contract_is_coachsplit`
did `os.environ.pop("GUARDKIT_COACH_CONTRACT", None)` with **no restore**. It was
silently unpinning the coach contract for every test that ran after it in the same
session — an active order-polluter, not merely a failing test. Now fixed via
`monkeypatch`.

### 2. Seven red tests are pointing at a live production bug — ✅ FIXED 2026-08-15

`feature_orchestrator.py:5082` sets `feature.status = "awaiting_merge"`.
`feature_loader.py:484` declares:

```python
status: Literal["planned", "in_progress", "completed", "failed", "paused"] = "planned"
```

`awaiting_merge` is not in that list, and it appears nowhere else in the codebase.
Every feature archival therefore raises a validation error on save. Confirmed
directly in this venv, outside the test suite:

```
ValidationError: 1 validation error for Feature
status
  Input should be 'planned', 'in_progress', 'completed', 'failed' or 'paused'
  [type=literal_error, input_value='awaiting_merge', input_type=str]
```

The tests are right; the code is wrong. Ledgered and left red — the fix is a
production enum change and belongs in its own gated lane. **Do not make these green.**

#### ✅ Fixed 2026-08-15 — `lane/archival-fix-0815`

That gated lane ran. **The loader was the wrong side**, and here is why, not just
that:

- `awaiting_merge` is a *specified* state, not a typo. TASK-FC-003
  ("Implement feature folder archival") states the requirement verbatim —
  "Update feature YAML: set `status: awaiting_merge`" — and lists it as a signed
  acceptance criterion. `tasks/backlog/feature-complete/README.md` names it as
  step 3 of the Wave-1 flow, and the TASK-REV-FC01 review report carries the same
  line. The writer at `feature_orchestrator.py:5082` is doing exactly what it was
  commissioned to do.
- The `Literal` is simply **older than the state it rejects**. `git log -L 484,484`
  shows the list has read `planned/in_progress/completed/failed/paused` unchanged
  since the original AutoBuild commit `b7f0472ac`, which predates
  `/feature-complete` entirely. TASK-FC-003 extended `FeatureExecution` with the
  archival fields and never widened the sibling status list.
- **Widening breaks nothing, and this was checked rather than assumed.** No
  exhaustive construct exists over the feature-status set anywhere in `guardkit/`
  or `installer/` — no `match`, no status→X dict, no `assert_never`, no
  `get_args()`. The complete reader list is two membership tests:
  `FeatureLoader.is_resumable` (`in_progress`/`paused`/`failed`) and
  `FeatureCompleteOrchestrator`'s `== "completed"` guard. Both give an
  awaiting-merge feature the right answer — not resumable, not done — which is
  the correct semantics for "built, archived, waiting on a human's merge word".

**The change.** One production file, one field, plus the comment explaining it:

```python
status: Literal[
    "planned", "in_progress", "completed", "failed", "paused", "awaiting_merge"
] = "planned"
```

**Receipts.**

| Check | Result |
|---|---|
| The seven L1 tests | 11/11 in `test_feature_archival.py` pass, **file unchanged** (`git diff -- tests/` empty) |
| Mutation proof | re-narrowing the `Literal` to its old five values re-reddens exactly those seven |
| Differential, `pytest tests/unit tests/integration`, matched venvs (Python 3.14.4, `uv sync --all-extras`) | **70 → 63 failed**, 10,254 → 10,261 passed |
| Strict subset | the 63 are a strict subset of the 70; the diff is exactly the seven archival tests; **ZERO added** |

**Two adjacent findings, ledgered not fixed** (they are a different defect from
L1 and deserve their own decision):

1. Four of the 41 feature YAMLs in this repo's own `.guardkit/features/` **cannot
   be loaded at all today** — `FEAT-9DDE` and `FEAT-FP-002` carry feature statuses
   `merged` and `superseded_by_rwop1.5`; `FEAT-MEM-09` and `FEAT-C90E` fail on
   `FeatureTask.status` and `FeatureTask.result`. This lane deliberately did not
   bless those values: `merged` is a real vocabulary word (`/feature-complete`
   Phase 3 writes it) and probably belongs in the Literal, but
   `superseded_by_rwop1.5` is hand-written drift that should be corrected in the
   file rather than legalised in the schema. That is a ruling, not a fix.
2. `FeatureTask.status` (`feature_loader.py:239`) has the **same shape of staleness**:
   it omits `merged`, `backlog` and `in_review`, all three of which appear in live
   feature YAMLs on disk. Same class, separate lane.

---

## The shape of the debt

The single largest driver is not "stale mocks" in the abstract. It is that
`AutoBuildOrchestrator` grew real machinery — worktree git commits, a Phase 4/5
specialist path, an M0 seat fence, a stall detector, an oracle-declaration law —
while a generation of integration fixtures kept modelling the 2025 orchestrator.
The clearest evidence: **one conftest, three attributes and a `git init` recovered
38 tests.**

The second driver is a governance fence landing on tests that never declared a seat.
The M0 fence and the langgraph harness cutover account for roughly 28 failures across
L2/L3/L4/L5/L15. Those want **one ruling, not fifteen fixes** — and the ruling should
not be `GUARDKIT_ALLOW_FRONTIER=1`, which would switch the fence off inside the suite
and hide the next regression. The repo's own `tests/conftest.py` says exactly this,
and already ships `m0_routine_fleet_route` as the sanctioned answer.

---

## What was fixed

Every row was measured in this venv, before and after, at file scope.

| # | Tests | File(s) | Class | What changed | Before → After |
|---|---|---|---|---|---|
| F1 | 38 | `tests/integration/quality_gates/conftest.py` | stale fixture | `mock_agent_invoker` gains an int-returning `_calculate_sdk_timeout`, a base `sdk_timeout_seconds`, and an AsyncMock `_invoke_with_role`; `task_scenario` makes the worktree a real git repo (`init -b main` + seed commit, local-only identity) | 49 → 11 failed in that directory |
| F2 | 5 | `tests/unit/test_autobuild_timeout_budget.py` | stale fixture | `_make_orchestrator` (a `__new__` helper) gains `_run_id` plus the invoker's timeout defaults | 5 → 0 (46 passed) |
| F3 | 4 | `tests/integration/test_timeout_budget.py`, `test_cancellation_timing.py` | stale fixture | shared `_stub_sdk_timeout` helper mirroring the real method's contract (an int, capped at the remaining budget), plus an awaitable `_invoke_with_role` | 4 → 0 (11 passed) |
| F4 | 3 | `tests/unit/test_inter_wave_bootstrap.py` | stale fixture | fake tasks get `estimated_minutes = None` — the real "no estimate" value — since `_resolve_wave_task_timeouts` now compares it to a number | 3 → 0 |
| F5 | 6 | `test_coach_grammar.py` (3), `test_agent_invoker.py` (2), `test_coach_output_parser.py` (1) | **env-dependent** | five tests pin `GUARDKIT_COACH_CONTRACT=coachsplit` via monkeypatch, naming the contract their assertions are about; the sixth chdirs to an empty `tmp_path` so "nothing configures otherwise" is actually true, and its unrestored `environ.pop` is replaced with `monkeypatch.delenv` | 6 → 0 (569 passed across the three files) |
| F6 | 4 | `tests/unit/commands/test_{arch_refine,system_arch,design_refine,system_design}*.py` | stale test | `spec_content` strips a leading YAML frontmatter block. All 32 command specs now carry `format_version`; the tests assert on the spec's prose. **No command markdown changed** — that surface belongs to another lane tonight | 4 → 0 (440 passed) |
| F7 | 1 | `tests/integration/orchestrator/test_red_baseline_replay.py` | **env-dependent** | the smoke command shells out for real; `sys.executable` replaces a bare `python`, which is absent on this machine | 1 → 0 |
| F8 | 2 | `tests/integration/autobuild/test_bdd_end_to_end.py` | stale fixture | the fixture worktree writes a minimal `pytest.ini`. Under TS-lane D.1b an undeclared toolchain is an ABSENT oracle rather than a guessed `pytest tests/`, so a bare `tmp_path` failed independent verification and drowned the `bdd_results` signal under test | 2 → 0 |
| F9 | 1 | `tests/integration/test_autobuild_context_opt.py` | superseded pin | `TASK_WORK_SDK_MAX_TURNS` 50 → 100. The receipt is in the production comment: TASK-FIX-ASPF-005 raised it because with `--fresh`, Player needs ~35–50 turns and 50 left no headroom | 1 → 0 (38 passed) |
| F10 | 3 | `tests/integration/test_config_error_fast_exit.py` | stale fixture + **dead premise** | invoker defaults, and the "invalid" task type swapped: `enhancement` is now a **registered alias** for `feature` in `TASK_TYPE_ALIASES`, so the tests were feeding a valid type and asserting rejection | 5 → 2 (the 2 are ledgered as L8) |
| F11 | 3 | `tests/integration/test_ablation_mode.py` | stale fixture | `git init -b main` (a bare `init` gave `master` here, and `WorktreeManager` branches off `main`), plus real values on the `MagicMock(spec=AgentInvoker)` | 3 → 0 (5 passed) |
| F12 | 2 | `tests/integration/test_quality_gate_validation.py`, `tests/integration/test_features/FEAT-CODE-TEST/*` | stale fixture | **corrected 2026-08-15 — see "F12 was diagnosed wrong" below.** The checked-in FEAT-CODE-TEST fixture had drifted from the schema the feature loader reads, so both tests died at parse time and never reached a model seat. The fixture is repaired; one test now genuinely passes and the other is guarded on the one dependency that really blocks it | 2 failed → 1 passed + 1 skipped |
| F13 | 1 | `tests/integration/test_autobuild_preloop.py` | superseded pin | the pre-loop gates now normalise `skip_arch_review: False` into the `execute_design_phase` options dict; the pinned call args are updated | 2 → 1 (the 1 is ledgered as L15) |

**Total: 72 cured + 1 honestly skipped.**

---

## F12 was diagnosed wrong — corrected 2026-08-15

The first pass of this lane recorded F12 as env-dependent and wrote a skip-guard
saying the two tests "need a real `guardkit-py autobuild feature` run against a
live model seat". That was wrong, and the guard hid a plain fixture bug of
exactly the kind this lane exists to fix. The row above has been rewritten. What
is true:

**The tests never reached a seat.** They failed in about two seconds with
`FeatureParseError: Missing required field 'id' in feature definition`. The
checked-in fixture `tests/integration/test_features/FEAT-CODE-TEST/FEAT-CODE-TEST.yaml`
had drifted from the schema `guardkit/orchestrator/feature_loader.py` actually
reads. Five separate pieces of drift, each found by fixing the one in front of it
and re-running:

| Drift | Fixture had | Loader requires |
|---|---|---|
| feature key | `feature_id:` | `id:` (`_parse_feature`, required with `name`) |
| task key | `file:` | `file_path:` (`_parse_task`, required with `id`) |
| feature status | `status: testing` | one of `planned`/`in_progress`/`completed`/`failed`/`paused` |
| orchestration | absent | `validate_feature` reports "Tasks not in orchestration" without it |
| task frontmatter | no `task_type` | pre-flight validation rejects the task file without it |

The task `file_path` was also flattened to `tasks/backlog/TASK-….md`. AutoBuild
derives the feature slug from that path and copies task files out of
`tasks/backlog/<slug>/`, so the flat form made the setup phase log "Task file not
found … Failed to copy 1 task file(s)". The fixture now uses
`tasks/backlog/feat-code-test/…` and the temp-repo fixture builds that layout,
after which the run finds the task and advances it to `design_approved`.

**A green test was holding the drift in place.** `test_feat_code_test_yaml_valid`
asserted `data["feature_id"] == "FEAT-CODE-TEST"`. It read the YAML with pyyaml
only, which proves the file is well-formed text and nothing about whether the
field names are the ones GuardKit reads. It has been updated to pin the corrected
schema, and a new companion test —
`test_feat_code_test_yaml_loads_through_feature_loader` — runs the fixture
through the real `FeatureLoader` in-process (no CLI, no seat, no network). That
is the test that would have caught this.

**What each test actually needs, measured with the seat made unreachable**
(`ANTHROPIC_BASE_URL` pointed at a closed port, so no live traffic was possible):

- `test_autobuild_creates_worktree` — **needs no seat.** The shared worktree is
  created in AutoBuild's setup phase, before any model is invoked. It now passes
  in about two seconds. Its guard and its `live` marker are removed, and it runs
  *seatless* by design: the subprocess is given an unreachable model endpoint, so
  the default suite never drives whatever seat the operator has running. That is
  a tightening, not a loosening — if worktree creation ever moved to after the
  first model call, this test would go red, which is the signal wanted.
- `test_quality_gates_evaluated` — **genuinely needs a working seat.** It asserts
  a Player report exists, and the Player only writes `player_turn_N.json` if it
  really runs; with no reachable seat the M0 fence stops it. It keeps the `live`
  marker and the `GUARDKIT_LIVE_AUTOBUILD_TESTS=1` opt-in, with a skip reason
  that now names that one dependency and nothing else.

**Two more test-only defects surfaced on the way and were fixed:**

1. `get_latest_turn_reports` looked only in `.guardkit/autobuild/<task_id>/`.
   Coach reports are now written to `.guardkit/autobuild-private/<task_id>/`, and
   the Player writes inside the shared worktree, so the helper silently found
   nothing. It now searches all known locations. Verified: with the seat
   unreachable the Coach report is found and the Player report is correctly
   absent, which is what makes the remaining guard honest.

2. The tests shelled out to a bare `guardkit-py` on PATH. On this machine that
   resolves to `~/.local/bin/guardkit-py`, a system-python shim that imports
   guardkit from the **main checkout** — so a test running inside a worktree was
   validating a different tree's code. The call is now
   `sys.executable -m guardkit.cli.main`, which pins the run to the code under
   test. Mutation-checked: breaking `required_fields` in the worktree's
   `feature_loader.py` turns both worktree-touching tests red, which it could not
   have done before this change.

**Mutation checks on this fix** (each mutation applied alone, then reverted):

| Mutation | Result |
|---|---|
| `id:` → `feature_id:` in the fixture | 3 red |
| `status: planned` → `status: testing` | 3 red |
| drop the `orchestration` block | 3 red |
| drop `task_type` from the task frontmatter | 1 red |
| add a bogus required field to `feature_loader.required_fields` | 2 red |

One candidate change was **dropped** rather than kept: pinning the temp repo to
`git init -b main`. It reads plausible (`WorktreeManager` branches off `main`,
and F11 needed exactly that), but with the fixture repaired the tests pass on a
`master` default too, so the change carried a claim the measurement did not
support.

**Differential after this fix**, same worktree and venv (Python 3.14.4):
70 failed / 10254 passed / 319 skipped, against the lane's 70 / 10252 / 320
before it. Two tests moved from skipped-or-absent to passing, no failure set
changed, and no failure in the touched file.

**Ledgered, not fixed:** `docs/testing/quality-gate-testing.md:532` still shows
the old `feature_id:` key in its example YAML. It is documentation, outside this
lane's tests-only fence, and it will teach the same drift to the next person who
copies it.

### Commits in this lane

One per group, each carrying its own story and its own measured before/after:

```
751af469  test(quality-gates): teach the shared conftest what the orchestrator now needs
7d59eb15  test(timeout-budget): give the mock invoker the numbers and awaitables the loop needs
e724612c  test(coach-contract): stop the suite reading guardkit's own config, and kill an order-polluter
0b3fde93  test(command-specs): read the spec body, not the frontmatter header
07a31e86  test(red-baseline): shell out to the interpreter running the suite, not a bare `python`
6ef17e94  test(bdd-e2e): declare a toolchain in the fixture worktree
9d6daf57  test(pins): update two tests pinning values production deliberately changed
a33ecbd9  test(config-error): stop testing config rejection with a type that is now valid
128ceebc  test(ablation): pin the fixture repo's branch to main and finish the invoker mock
9d23787c  test(quality-gate-validation): guard the two tests that need a live autobuild run
```

---

## The ledger — 68 failures not fixed here

### The production-defect suspects — read these first

These four are the valuable output of the exercise. In each case the test is
probably **right** and the production code is probably **wrong**. The value they are
currently delivering is the bug report. Resist the pull to make them green.

**Update 2026-08-15:** L1 has been taken through its own gated lane and cured —
the test was right, the loader was wrong. Three suspects remain open (L8, L10,
L11), carrying 5 failures between them.

| # | Tests | Diagnosis |
|---|---|---|
| ~~**L1**~~ **✅ FIXED 2026-08-15** | ~~7~~ 0 — `tests/integration/test_feature_archival.py` | `feature_orchestrator.py:5082` writes `status = "awaiting_merge"`; the `Literal` at `feature_loader.py:484` omitted it, so **every feature archival raised a validation error on save**. **Verdict: the loader was the wrong side** — `awaiting_merge` is specified verbatim by TASK-FC-003 and the `Literal` predates `/feature-complete` (unchanged since `b7f0472ac`). Cured on `lane/archival-fix-0815` by widening the `Literal`; the seven tests are green **unchanged**, re-narrowing re-reddens exactly them, and the differential is 70 → 63 with zero added. Full receipts in "Two findings that outrank the arithmetic" §2 above. |
| **L8** | 2 — `tests/integration/test_config_error_fast_exit.py` (residue after F10) | With a genuinely-invalid task type, `CoachValidator.validate` **does** produce the configuration error — verified directly. But `_loop_phase` never fast-exits: it goes on to invoke the LLM Coach, which the tests had stubbed as "should not be reached". The fast-exit wiring may have regressed. Making these green would mean giving that fallback Coach a return value, which would **hide** the fact the fast-exit did not fire. |
| **L10** | 2 — `tests/integration/test_drift_detection_workflow.py` | `SpecDriftDetector.analyze_drift` reports 100% implemented for a fixture that **deliberately omits a method**, and the formatted report no longer names the implementation file. A drift detector that cannot see a missing method is not detecting drift. |
| **L11** | 1 — `tests/integration/lib/test_agent_generator_integration.py` | `_identify_capability_needs` returns zero needs where the test states the hard-coded `testing_framework` pattern always fires. |

### Awaiting one ruling, not fifteen fixes

Roughly 28 failures share a single cause: the M0 seat fence and the langgraph
harness cutover landing on tests that never declared a seat.

| # | Tests | Class | Diagnosis |
|---|---|---|---|
| L2 | 11 — `test_sdk_delegation.py` | stale (harness cutover) | Patches `sys.modules["claude_agent_sdk"]`. The default harness has been langgraph since TASK-HMIG-011 (2026-06-16). Under `GUARDKIT_HARNESS=sdk` the M0 fence refuses, because the bundled CLI default is an Anthropic seat. **Needs a ruling: port to langgraph, or fence-and-skip.** |
| L3 | 2 — `test_autobuild_phase_4_5_orchestration.py` | stale (same family) | `StubSDKRecorder` never fires — "expected two SDK calls, got 0". |
| L4 | 10 — `test_autobuild_delegation.py` | **dead claim (~5)** + L2 family (3) + multi-wall (2) | `asyncio.create_subprocess_exec` and `--mode=` appear **nowhere** in `agent_invoker.py`: the subprocess-CLI delegation mechanism is gone. Flag for whoever takes this: the file's currently-*passing* subprocess tests pass **vacuously**, which is worse than the red ones. |
| L5 | 4 — `test_autobuild_e2e.py` | stale (multi-wall) | git-init branch, then invoker attributes, then the M0 fence in the **design** phase — which `model=` does not satisfy, because `task_work_interface.py:503` resolves its own seat. Possible secondary `TASK-FIX-MODELPLUMB` gap into the pre-loop harness. |
| L15 | 1 — `test_autobuild_preloop.py` (residue after F13) | L2 family | `test_player_fails_without_plan` gets the M0-fence message instead of the plan-missing error. |

The ruling should **not** be `GUARDKIT_ALLOW_FRONTIER=1` for the suite. That switches
the fence off exactly where the next regression would be caught. `tests/conftest.py`
already ships `m0_routine_fleet_route` as the sanctioned way to declare a routine
local-fleet seat for the duration of one test.

### Dead claims — deletion candidates, with receipts

| # | Tests | Diagnosis |
|---|---|---|
| L6 | 7 — `test_template_create_orchestrator_integration.py` | `TestPhase75BatchEnhancement` (6 tests) plus one assertion in `test_orchestrator_has_all_phases` target `_phase7_5_enhance_agents`, **removed by TASK-SIMP-9ABE** for a 0% success rate — the source comment recording this is at `installer/core/commands/lib/template_create_orchestrator.py:1528`. The claim is dead: the feature is retired. Deletion is defensible **with that receipt written into the commit**, which is why it is ledgered rather than done here. Two side notes: an orphan `_display_enhancement_errors` (line 2515) now has zero callers, and these tests assert on code *strings*, a weak test form worth replacing rather than restoring. |

### Behavioural disagreements and residue

| # | Tests | Class | Diagnosis |
|---|---|---|---|
| L7 | 11 — `tests/integration/quality_gates/` residue after F1 | mixed | 7 assert `max_turns_exceeded` but get `unrecoverable_stall`: the stall detector (TASK-FIX-7A07, threshold 3) fires first because the fixtures feed identical Coach feedback every turn. Which outcome is correct is a design question, not a mock fix. 3 construct `QualityGateBlocked(score=…)` where the signature is `(reason, gate_name, details)`. 1 leaks a coroutine from a bare `AsyncMock()` `invoke_coach` into `_extract_feedback`. |
| L9 | 7 — `test_smoke_gate_blocks_wave.py` (6), `test_smoke_gate_noop.py` (1) | stale mock **over** a real disagreement | `_common_patches` stubs `find_task` as `lambda f, tid: f` — "any non-None task is fine" — which broke when `_resolve_wave_task_timeouts` began reading `task.estimated_minutes`. Past that wall the tests still disagree with production: `_execute_wave` fires twice where 3 are expected, `run_smoke_gate` twice where 1 is expected. **Needs a ruling on the intended retry sequence** before the mock is worth repairing. |
| L12 | 1 — `test_requires_infra_propagation.py` | stale test | The key **is** set in production (`autobuild.py:7327`, `:7506`), but `validate` is never reached: `_direct_mode_evidence_gate` / `_bdd_authoring_sweep_gate` short-circuit first. Needs a decision on whether to drive the test past the new gates. |
| L13 | 1 — `test_skip_arch_review_implement_only.py` | stale test | The orchestrator is built with no `agent_invoker`, and the Coach path now requires one (`'NoneType' object has no attribute 'invoke_coach'` → synthetic feedback). Fixing it means **authoring new test intent** — a Coach mock that approves — which is writing a new test, not repairing an old one. |
| L14 | 1 — `test_worktree_checkpoints_evidence.py` | **flaky / ordering** | Passes alone, fails inside a full `tests/unit` run — reproduced. `assert 'plain' not in {'plain': 'HEAD'}`: a non-git sibling receives an evidence commit whose hash is the literal fallback ref `"HEAD"`. The polluter is inside `tests/unit` and has not been isolated; the `os.chdir`/`GIT_DIR` and unrestored-`.start()` candidates were ruled out. |

### Ledger totals

| Group | Count (as triaged 08-14) | Open after 08-15 |
|---|---|---|
| Production-defect suspects (L1, L8, L10, L11) | 12 | **5** (L1's 7 fixed) |
| M0 fence / langgraph cutover (L2, L3, L5, L15) + L4's share | 28 | 28 |
| Dead claims (L6, part of L4) | ~12 | ~12 |
| Behavioural disagreements and residue (L7, L9, L12, L13) | 20 | 20 |
| Flaky / ordering (L14) | 1 | 1 |
| **Total** | **68** | **61** |

The 68 → 61 is measured, not arithmetic: `pytest tests/unit tests/integration` in
matched venvs reports 70 failed on `main` (`bfb2b826`) and 63 on
`lane/archival-fix-0815`, the difference being exactly the seven archival tests.
(70 rather than 68 because these venvs run Python 3.14 — see caution 8.)

(The L4 file splits across three causes, so the middle rows overlap by design; the
per-file counts in the tables above are exact.)

---

## Cautions for whoever picks this up

1. **Re-measure in your own venv.** Absolute counts drift between venvs and Python
   versions. This lane's numbers are differential against a baseline taken in the same
   tree with the same interpreter (3.12.3). Take your own before touching anything.

2. **L1, L8, L10 and L11 are probably right.** They are bug reports wearing test
   clothing. The temptation to turn a red suite green is exactly what would delete
   them. Each needs a production lane, not a fixture edit. **L1 has now had that
   lane (2026-08-15) and the diagnosis held: the test was right, the loader's
   `Literal` was stale. L8, L10 and L11 remain open.**

3. **`test_autobuild_delegation.py` has vacuously-passing tests.** Its subprocess
   tests currently pass because the mechanism they patch no longer exists. Green there
   means nothing. Anyone deleting the red tests in that file should look at the green
   ones in the same pass.

4. **The M0 fence group wants a decision first.** Fifteen separate fixture repairs
   would be wasted work if the ruling is "port these to langgraph" or "fence and skip".

5. **Do not reach for `GUARDKIT_ALLOW_FRONTIER=1`.** It would turn the fence off
   inside the suite, which is where you most want it on.

6. **`test_strict_flag_loads_strict` does not guard what its name suggests.** Its
   assertion is `"root" in g and "prelude" in g`, but `prelude` appears in both
   coachsplit grammars (`coach-verdict.gbnf` and `coach-verdict-strict.gbnf`) and
   in neither v4 grammar. So it discriminates coachsplit-vs-v4, not
   strict-vs-primary: forcing the name to `_PRIMARY` leaves it green. This is a
   pre-existing weakness the lane inherited unchanged — the F5 contract pin it
   gained is correct and does bite — but nobody should read it as proof the
   strict grammar was loaded.

7. **`test_task_work_sdk_max_turns_is_100` is exposed to your environment.** The
   constant it asserts is derived from `GUARDKIT_SDK_MAX_TURNS`
   (`agent_invoker.py:667-668`), and the test does not isolate that variable, so
   it fails spuriously for any operator who has it set. Pre-existing, not
   introduced here; a `monkeypatch.delenv` plus a module reload would close it.

8. **The 68 ledgered count is exact only on Python 3.12.** On 3.14 two extra
   tests fail (`tests/integration/feature_plan/test_validate_smoke_gates_step_8_6.py`),
   asserting stderr is empty when a pydantic-v1-on-3.14 `UserWarning` lands
   there. They are red on main too, so the strict-subset claim is unaffected —
   but this is why caution 1 is real advice rather than boilerplate.

---

## Production observation for a future lane (not fixed here)

`guardkit/orchestrator/coach_grammar.py:60` defines its own
`resolve_coach_contract()`, duplicating the resolver in `coach_contract.py` —
whose module docstring claims "both prior resolvers delegate here; no duplicated
env reads (TASK-CMIR-003 AC-1)". That claim is stale. Two independent resolvers
now read the same environment variable, which means F5's fix silently depends on
them agreeing. Consolidating them is a production change and belongs in its own
coach-gated lane.
