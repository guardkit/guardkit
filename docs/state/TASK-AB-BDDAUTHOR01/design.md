# TASK-AB-BDDAUTHOR01 — BDD authoring sweep: design (AC-001 gate)

> Written 2026-07-05 against verified current source (line numbers re-checked;
> the task file's `coach_validator.py:6740-6822` anchor is stale — the
> TASK-FIX-CC-BDD glue-exclusion code now lives at `coach_validator.py:7196-7271`
> (call sites) and `:7461-7543` (`_filter_bdd_glue_files`); `is_bdd_glue_file`
> is defined in `bdd_runner.py:178`, not in coach_validator).
>
> **Review round 1 (2026-07-05): REJECT 54/100** — finding 1 (CRITICAL): the
> `validate()` wiring alone runs only under `GUARDKIT_COACH_LEGACY=1`; the
> default primary Coach path never calls it. **Amendments applied (v2, as
> implemented):**
>
> 1. **Both-paths deterministic enforcement** — new
>    `AutoBuildOrchestrator._bdd_authoring_sweep_gate`, mirroring
>    `_direct_mode_evidence_gate` exactly: wired at BOTH Coach call sites
>    (legacy + primary), after the evidence-repo/direct-mode gates and before
>    the LLM Coach, blocking via `_emit_synthetic_coach_feedback` (which
>    persists the verdict file itself — no post-synthesis override, so no
>    Layer-4 re-persist hazard). The `validate()` wiring stays as legacy-path
>    defence-in-depth. The sweep result also rides the evidence bundle
>    (`CoachEvidenceBundle.bdd_authoring_sweep`, populated in
>    `gather_evidence`, auto-rendered via `asdict`) so the LLM Coach sees it.
> 2. **Activation input (finding 2)** — `files_authored` when NON-EMPTY, else
>    `files_created ∪ files_modified` (seam-local parser-extracted claims;
>    the `[]`-is-authoritative reading is degenerate at this seam and would
>    silently skip Bash-written glue). Divergence documented in code.
> 3. **Ownership rule (finding 3)** — the sweep runs ONLY over glue OWNED by
>    this task (per-task-named `…__<sanitised_task_id>.py`, or created this
>    turn — `glue_owned_by_task`). Edited pre-existing shared/legacy glue is
>    NOT swept (logged), fully closing the shared-legacy-edit false-red
>    vector rather than demoting it. Blocking feedback names BOTH
>    remediations (implement the step OR narrow the binding per
>    `bdd-per-task-glue.md`).
> 4. **exit-4 row (finding 4)** — "not found" signature → absent
>    (`_is_absent_feature_collection` reused); conftest-loading veto /
>    ambiguous exit-4 → blocking runner-error (F584 preserved). The
>    "structurally unreachable" claim is withdrawn.
> 5. **exit-5 vacuous-pass (finding 5)** — binding glue that collects zero →
>    all-zero sweep result → non-blocking `bdd_sweep_zero_collected`
>    advisory; helpers-only glue stays silently absent.
> 6. **AC-003 wording (finding 6)** — amended in the task file: targets are
>    the authored glue modules (executing the scenarios they bind); undefined
>    details carry module classnames, not `.feature` paths (accepted).
> 7. **Notes 7-8** — `BDDResult` docstring states `scenarios_undefined` is
>    structurally 0 in tag-scoped results; the sweep reuses
>    `isolated_basetemp` and unlinks the stale authoring junit before runs.

## 1. Problem recap (R4)

The step-def **authoring** task (FEAT-SMP-002 / TASK-SMP2-07) owned zero
`@task:` tags by its own design → `run_bdd_for_task` legitimately returned
`None` (activation-by-artefact) → no pytest run, no junit, gate inert. BDD
glue is ALSO deliberately excluded from the Coach's independent pytest
command (TASK-FIX-CC-BDD). So the authoring task's glue was exercised by
**neither** verification leg, and an undefined step
(`StepDefinitionNotFoundError`) sailed through to the operator's pre-merge run.

## 2. Operator-input answers adopted (handoff §2.2)

1. **Blocking from day one** for `scenarios_undefined` within the sweep (the
   task file's AC-004 mandates it; the scoping argument makes it safe — the
   authoring task's entire job is making scenarios executable). Ordinary
   assertion FAILURES inside the sweep are **advisory** (see §5 — this is the
   FEAT-39E1 guard).
2. **Parallel-wave guard:** authored-files scoping (AC-006's own formulation)
   rather than a `wave_size == 1` gate — the sweep's collection targets are
   only files THIS task authored THIS turn, so a sibling's glue can never be
   collected, in any wave shape (see §6).
3. **Sweep + planner rule: both.** This task ships the sweep (the structural
   defence). The planner-side rule ("the authoring task must own at least the
   scenarios it makes executable") is follow-up ergonomics — filed as a note
   in the task file, not implemented here.
4. **junit name:** `<worktree>/.guardkit/bdd/<task_id>_authoring_junit.xml` —
   same directory as the standard `<task_id>_junit.xml`, distinct suffix so
   existing tooling reading the standard name is unaffected.

## 3. Activation (artefact, no flag)

After the Player turn, while writing `task_work_results.json`
(`agent_invoker.py` — the same seam that calls `_run_bdd_oracle`, ~`:10302`):

1. Compute the authored set from the results dict being written, mirroring
   `CoachValidator._compute_authored_set` semantics (presence-based:
   `files_authored` when the key is present — an explicit `[]` is
   authoritative — else `files_created ∪ files_modified`).
2. Filter to paths that (a) exist under the worktree and (b) satisfy
   `is_bdd_glue_file` (`bdd_runner.py:178` — pytest-bdd import/scenarios-call
   text scan).
3. Zero glue → **no sweep, no key** (silent, behaviour-identical skip —
   `activate-by-artefact-not-opt-in-flag`). Scaffolding tasks author
   `.feature` files, not glue, so they never enter the sweep —
   `bdd-pending-is-not-failed` is preserved **by construction**.

## 4. Execution (one deliberate deviation from AC-003's letter)

`run_bdd_authoring_sweep(task_id, worktree_path, glue_files, *, timeout=120,
python_executable=None)` — new function in `bdd_runner.py`, reusing the
module's existing helpers (`parse_junit_xml`, timeout sentinel, venv-pinned
interpreter passed by the caller exactly as `_run_bdd_oracle` does).

pytest argv: `pytest --gherkin-terminal-reporter
--junitxml=<worktree>/.guardkit/bdd/<task_id>_authoring_junit.xml
<authored glue files...>` — **no `-m task_<ID>` filter, no
`GUARDKIT_BDD_TASK_ID`**.

**Deviation, with rationale:** AC-003 says "run pytest over the glue-bound
feature files". We instead pass the **authored glue modules themselves** as
the collection targets. Collecting a pytest-bdd glue module executes exactly
the scenarios that glue binds (each `@scenario` def is a test function), so
the intent — exercise everything the authored glue makes executable,
unfiltered — is satisfied, while avoiding two failure modes of
feature-file targets:

- feature-file targets route through the `features/conftest.py` bridge, whose
  glue lookup keys off `GUARDKIT_BDD_TASK_ID` / the legacy shared name — with
  the env var unset it would pick the *legacy* module (possibly another
  task's, or absent → the exit-4 "not found" path), defeating AC-006;
- glue-module targets make parallel-wave isolation structural: the target
  list contains only THIS task's authored files.

This also delivers the missing-junit artefact (retro action (c)) for free.

## 5. Classification within the sweep (the FEAT-39E1 reconciliation)

The verified tension: TASK-FIX-CC-BDD exists precisely because unscoped
pytest over glue surfaces *peer-task* scenarios as FAILED (cross-task
false-reds). The sweep deliberately runs unscoped — so its **blocking set is
narrower than its collection set**:

| Sweep observation | Mapping | Disposition |
|---|---|---|
| `StepDefinitionNotFoundError` testcase (via the existing `_PENDING_MARKERS` classification in `parse_junit_xml` — untouched) | `scenarios_undefined` + `undefined` details | **BLOCKING** (`must_fix`, category `bdd_undefined_steps`) — feeds back naming each undefined step |
| Ordinary assertion failure | `scenarios_failed` + `failures` details | **ADVISORY** (`should_fix`, category `bdd_sweep_failure`) — surfaced with scenario names; pass/fail ownership stays with each scenario's tag-scoped oracle (avoids re-opening FEAT-39E1) |
| Synthesised `pytest_bdd_not_importable` / `pytest_runner_error` failure (existing BDDM-1/F584 shapes, recognised by our own sentinel `scenario_name`) | blocking | **BLOCKING** — glue was authored but cannot run at all; a vacuous pass here is exactly the `absence-of-failure` hazard |
| pytest exit 5 (zero items collected from the glue) | absent | **ABSENT** (`None`, no key). Legitimate: a step-def *helpers* module (`_steps_<slug>.py` pattern from `bdd-per-task-glue.md`) imports pytest_bdd but binds no scenarios. Residual gap documented in §8. |
| Timeout | absent | **ABSENT** (`None`) — ABFIX-010: a verification timeout is never a synthesised failure |
| Passed scenarios | `scenarios_passed` | informational |

The tag-scoped oracle is **byte-for-byte unchanged**: `_PENDING_MARKERS`,
`parse_junit_xml`'s pending-vs-failed split, and `run_bdd_for_task` are not
modified (the sweep *reinterprets* the parse result's `pending` list as
`undefined` at result-construction time, in the new function only).

## 6. Data model + serialization journey (absence-must-survive)

- `BDDResult` gains `scenarios_undefined: int = 0` and
  `undefined: List[PendingDetail] = field(default_factory=list)`; both are
  ALWAYS serialized by `to_dict()` (defaults `0`/`[]` in the tag-scoped path,
  so existing consumers see additive keys only).
- The sweep writes a **distinct top-level key** `bdd_authoring_sweep` in
  `task_work_results.json` (never touches `bdd_results`). Journey:
  `run_bdd_authoring_sweep` → `AgentInvoker._run_bdd_authoring_sweep`
  (exception-swallowing wrapper, identical posture to `_run_bdd_oracle`) →
  `results["bdd_authoring_sweep"] = result.to_dict()` **only when a result
  exists** → `CoachValidator._check_bdd_authoring_sweep` reads the key.
  Absent sweep = absent key at every layer; no layer coerces absent to 0/pass
  or to a failure.
- The guardkitfactory bridge (`map_bdd_run_result`) is NOT extended: the
  sweep has a single producer (this new leg); the factory bridge feeds the
  tag-scoped `bundle.bdd` only. No drift surface is created because no second
  producer of `bdd_authoring_sweep` exists.

## 7. Coach gate

`CoachValidator._check_bdd_authoring_sweep(task_work_results) ->
(blocking, non_blocking)`, shaped exactly like `_check_bdd_results`
(`coach_validator.py:8050`):

- key absent → `([], [])` (gate inert);
- `scenarios_undefined > 0` → blocking `must_fix` / `bdd_undefined_steps`,
  listing each undefined step + the junit path;
- synthesised runner-error/not-importable failure → blocking `must_fix` /
  `bdd_sweep_error`;
- ordinary `scenarios_failed > 0` → non-blocking `should_fix` /
  `bdd_sweep_failure`.

Wired in `validate()` immediately after the existing "5.7 BDD oracle gate"
block (`coach_validator.py:2837-2861`), with the same disposition: blocking →
`_feedback_result` (feedback **within** the adversarial loop, bounded by
`max_turns` — feed back, never bare-terminate); non-blocking rides the
approval path via `all_issues`. This is the same (deterministic, both-paths)
placement precedent as the tag-scoped gate.

## 8. Known residual gaps (documented, not silent)

- A helpers-only authoring task (`_steps_*.py`, no `@scenario` bindings)
  yields exit-5 → absent; its steps are exercised only when a binding glue
  module runs. Closing this needs the planner-side rule (§2 item 3).
- Sibling tasks mutating shared worktree state mid-run can still perturb the
  sweep in a parallel wave — the same ambient exposure the tag-scoped oracle
  and independent-test leg already carry; the overlap auto-serialise
  mitigation (WAVECTL01 batch) bounds it upstream.
- ~~Turn-scoped activation hole~~ **CLOSED (batch review round 2, MAJOR
  finding 2):** per-task-named glue already on disk now re-arms the sweep on
  EVERY turn (`find_per_task_glue` + the union in
  `AgentInvoker._run_bdd_authoring_sweep`) — a Player blocked on undefined
  steps can no longer clear the deterministic gate by simply not touching
  its glue next turn. Residual within the residual: LEGACY-named glue
  created in turn N is not name-attributable and is not re-armed on later
  turns (per-task naming is what the Player prompt mandates; accepted).

## 9. Regression-constraint checklist (from the task file, verified)

| Constraint | How the design honours it |
|---|---|
| `bdd-pending-is-not-failed` pinned tests (`test_pending_step_recorded_distinctly`, `test_bdd_pending_approves_with_feedback`) | tag-scoped path untouched; sweep is a separate function + separate key; pinned tests run unmodified |
| `_PENDING_MARKERS` untouched | reused as-is; reinterpretation happens only at sweep-result construction |
| activate-by-artefact | authored glue IS the artefact; no flag; zero-glue turns byte-identical |
| `bdd-per-task-glue` race rules | collection targets = this task's authored files only; no conftest-bridge glue lookup at all |
| TASK-FIX-CC-BDD glue exclusion stays | `_filter_bdd_glue_files` and the independent-test command are untouched; the sweep is a new BDD-aware leg with its own junit |
| feed back, never terminate | blocking issues are `must_fix` feedback inside the Player-Coach loop (same as `bdd_failure`); nothing terminates the feature |
| vacuous-true guard / BDDNEUTRAL01 / ABFIX-010 | not-importable + runner-error → synthesised BLOCKING; timeout → absent; exit-5 → absent; exit-4 "not found" is structurally unreachable (targets are files we just wrote; existence-checked before running) |
| absence-must-survive-every-reconciliation-layer | new fields always serialized; absent sweep = absent key end-to-end; no coercion at any layer |

## 10. Test plan (AC-008)

Unit (`tests/unit/orchestrator/quality_gates/test_bdd_authoring_sweep.py`):
- undefined step in authored glue → `scenarios_undefined == 1`, blocking
  `bdd_undefined_steps` naming the step; junit written to `*_authoring_junit.xml`;
- passing glue → sweep result with 0 undefined, no blocking issue;
- ordinary failure → advisory `bdd_sweep_failure`, decision NOT rejected by
  the sweep alone;
- scaffolding shape (authored `.feature`, no glue) → no sweep, no key,
  `bdd_results` semantics unchanged;
- helpers-only glue (exit 5) → absent; timeout → absent; not-importable →
  blocking synthesised;
- parallel isolation: authored set containing only this task's glue while a
  sibling glue module exists on disk → sibling never in the pytest argv;
- serialization: `BDDResult.to_dict()` carries `scenarios_undefined`/`undefined`;
  tag-scoped `run_bdd_for_task` result has them at 0/[].
- Coach gate: key absent → `([], [])`; undefined > 0 → feedback decision;
  existing `test_bdd_pending_approves_with_feedback` unchanged.
