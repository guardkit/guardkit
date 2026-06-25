# TASK-ABFIX-012 — Implementation Plan

**Goal:** Kill the FEAT-FMDR-004 false-approval — a TESTING-type task false-APPROVED
on turn 1 while its own run was 5/9 red (real code bugs reasoned away as "substrate")
— WITHOUT re-opening the false-red ABFIX-010 prevents (a substrate-blocked TESTING
task must not `unrecoverable_stall`).

## Key architectural fact (verified against `main`, 2026-06-24)

The **live** Coach decision path is `CoachValidator.gather_evidence()`
(`autobuild.py:6051`) → `CoachEvidenceBundle` → deterministic guards in
`AgentInvoker._invoke_with_role` (`agent_invoker.py:2293-2325`) + LLM Coach.
`validate()` (where `_classify_test_failure` is *called* and the
`parallel_contention` amnesty lives) is the **legacy** path (`GUARDKIT_COACH_LEGACY=1`
only). Therefore a genuine independent CODE failure (`tests_passed=False,
signal_absent=False`) has **no deterministic blocking guard** in the live path today —
it relied on the LLM Coach, which is what false-approved FMDR-004. Flipping
`tests_required=True` alone is necessary but **not sufficient**; a deterministic guard
is required.

## Design (mandatory ordering: classifier first, required-flip last)

1. **Widen `_classify_test_failure`** with stack-agnostic host-substrate signals
   (`command not found`, `executable file not found`, Windows "not recognized…") →
   `("infrastructure","high")`, checked **before** the `is_parallel` reclassification
   so a substrate miss is never amnestied as `parallel_contention` and never reaches a
   code block. (Dropped the over-broad `": not found"` — it false-matches `"key: not
   found"` and would mis-route a real code bug to infrastructure → false-green.)
2. **Route substrate gaps to `signal_absent=True`** in `run_independent_tests` (all
   three paths: SDK, subprocess-python, isolated) via a shared `_is_host_substrate_gap`
   helper (returncode 126/127 OR the explicit shell strings). This reuses the EXISTING
   `_reconcile_absent_independent_test_signal` guard → feedback bounded by `max_turns`,
   and flows through the ABFIX-010 `None`/UNKNOWN channel. Substrate → absent (never a
   pass, never a code block).
3. **Neutralise the `wave_size` swing for TESTING:** add a `_CODE_FAILURE_HIGH_CONFIDENCE`
   token list (`AssertionError`/`AttributeError`/`has no attribute`/`NameError`/`is not
   defined`/`TypeError`). In `_classify_test_failure`, for `task_type == "testing"` a
   token match returns `("code","high")` **regardless of `is_parallel`** — so a real
   assertion failure is rejected in BOTH single and parallel waves. Non-token failures
   still fall through to `parallel_contention`, preserving the genuine cross-task
   contention amnesty (import/collection races are not tokens).
4. **Carry the verdict to the live path:** new `IndependentTestClassification`
   dataclass on `CoachEvidenceBundle` (mirrors `RuntimeParityResult`; serialized
   automatically by `to_dict`/`asdict` per ABFIX-010). `gather_evidence` populates it
   **only** when `tests_passed is False AND signal_absent is False` — an absent signal
   never manufactures a code verdict.
4a. **Parallel-wave non-token closure (adversarial-review finding).** The token
   list (step 3) cannot enumerate every exception, so a parallel-wave TESTING
   failure with a non-token exception (`ValueError`/`KeyError`/custom) classified
   `parallel_contention` and the guard skipped it → residual false-green. Fix: in
   `gather_evidence`, reclassify a TESTING `parallel_contention` to `("code","high")`
   **unless** `_detect_source_file_contention` finds genuine peer source-file
   overlap (the one case the AC's "amnesty stays for genuine cross-task contention
   on shared files" preserves). The original ABFIX-005 contention (import/collection
   races) classifies earlier (`infrastructure`/`collection_error`/`signal_absent`)
   and never reaches this branch, so only real own-code failures are reclassified.

5. **New deterministic guard** `AgentInvoker._apply_independent_test_code_failure_guard`
   (mirrors `_apply_runtime_parity_guard`): overrides `approve`→`feedback` when
   `task_type=="testing"` AND independent tests ran-and-failed (`tests_passed False`,
   `signal_absent False`) AND `classification.failure_class == "code"` (any confidence —
   a single-wave non-token failure is still `("code","n/a")` and must block; firing only
   on `"high"` would leave a false-green hole). Substrate gaps (`signal_absent True` →
   owned by the absent guard) and genuine contention (`parallel_contention`) never reach
   it. No `peer_overlap` precondition — bias to feedback (a false-red self-corrects on
   the next, serialised turn; a false-green ships the FMDR-004 harm).
6. **Flip `TaskType.TESTING` `tests_required=True` + `zero_test_blocking=True`** LAST.
   `zero_test_blocking` is safe: `_check_zero_test_anomaly:6984` exempts a genuinely
   passing independent run; it fires only on "no tests ran/found" (not "zero new tests
   added"), which for a TESTING task is the suspect case the task wants surfaced.

Scope: only TESTING gate semantics change. FEATURE/REFACTOR/INTEGRATION/etc. unchanged
(the classifier override and the guard are both `task_type=="testing"`-gated).

## Edits (files)
- `guardkit/orchestrator/quality_gates/coach_validator.py` — 2 class constants,
  `_is_host_substrate_gap` helper, 3 substrate-routing sites in `run_independent_tests`,
  `_classify_test_failure` (signature + substrate check + TESTING code override),
  `validate()` caller threading, `gather_evidence` classification population.
- `guardkit/orchestrator/quality_gates/coach_evidence.py` — `IndependentTestClassification`
  dataclass + bundle field.
- `guardkit/orchestrator/agent_invoker.py` — new guard method + call-site.
- `guardkit/models/task_types.py` — TESTING profile flip + docstring.

## Tests
- `tests/unit/test_task_types.py` — TESTING `tests_required`/`zero_test_blocking` True.
- `tests/unit/test_coach_failure_classification.py` — substrate→infra/high (single+parallel);
  TESTING token→code/high (single+parallel); FEATURE token→parallel_contention (scope);
  non-token parallel failure→parallel_contention (amnesty preserved); `"key: not found"`
  with rc1 NOT substrate.
- `tests/unit/test_abfix012_substrate_signal_absent.py` — substrate (rc127/"command not
  found") → `run_independent_tests` `signal_absent=True` on all three paths.
- `tests/orchestrator/test_abfix012_testing_code_failure_guard.py` — approve→feedback for
  TESTING code failure; NO override for: signal_absent True, failure_class infrastructure/
  parallel_contention, task_type feature, classification None; re-persists coach_turn_N.json.

## Rule compliance
absence-of-failure / absence-must-survive-every-reconciliation-layer / path-string-mismatch
/ evidence-boundary / smoke-gate-is-feedback / per-task-green / stack-plugin-architecture —
all "complies" (substrate→absent→feedback; code→block; absent never coerced to False; new
field serialized via asdict; stack-agnostic DATA pattern lists; TESTING-scoped).
