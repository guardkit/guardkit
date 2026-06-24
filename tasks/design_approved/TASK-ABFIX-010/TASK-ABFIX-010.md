---
id: TASK-ABFIX-010
title: "Harness false-red/false-green on Coach test-timeouts: keep an absent test signal as UNKNOWN (None) through every reconciliation/synthesis layer, not coerced to False"
status: design_approved
task_type: fix
created: 2026-06-24T00:00:00Z
updated: 2026-06-24T00:00:00Z
previous_state: in_progress
state_transition_reason: "design-only run complete — Phase 2.8 checkpoint approved by human"
priority: high
complexity: 7
design:
  status: approved
  approved_by: human
  scope: "W1+W2+W2b (W3/W4 deferred)"
  implementation_plan: docs/state/TASK-ABFIX-010/implementation_plan.md
  implementation_plan_version: v2
  architectural_review_score: 64
  architectural_review_status: approved_with_mandatory_corrections
  complexity_score: 7
  design_notes: "v2 folds in the Phase 2.5B blocking fix (carry None through the gate chain) and the tests_failed=0 false-green guard. Ready for --implement-only / autobuild."
related:
  - TASK-FIX-CKPTTESTRED01      # checkpoint-layer tri-state (this task extends its invariant upstream)
  - TASK-AB-FIX-INVAB1          # absence-of-failure-is-not-success origin
  - TASK-AB-PERTASKFG01         # per-task-green false-green backstop (must NOT be disarmed)
  - TASK-ABFIX-005              # parallel-wave Coach isolation (4th injection site / parallel amnesty)
  - TASK-AB-COACHRUNPARITY01    # runtime-parity (RuntimeParityResult) — timeout branch in scope
  - FEAT-9DDE
implementation_mode: task-work
tags: [autobuild, coach, false-red, false-green, absence-of-failure, test-timeout, reconciliation, bdd-runner, runtime-parity]
source_docs:
  - ../forge/docs/reviews/FEAT-FMDR-autobuild-false-green-analysis.md
  - ../forge/docs/handoffs/FMDR-NATS-SESSION-DISCOVERIES-2026-06-24.md
---

# Task: keep an absent test signal as UNKNOWN through every reconciliation layer

> **Provenance.** Filed from the FEAT-FMDR autobuild post-mortem
> (`forge/docs/reviews/FEAT-FMDR-autobuild-false-green-analysis.md`, lines 48-93)
> and a pre-implementation regression review (2026-06-24) that found the
> originating analysis aimed three of its four proposed changes at the **wrong
> layer** and that, as worded, each re-opened a hole an existing fix already
> closed. This spec is the corrected, regression-checked version. All file:line
> citations below were verified against `main` on 2026-06-24.

## Why this task exists

In the FEAT-FMDR autobuild run (SDK harness), **TASK-FMDR-001 was killed as
`unrecoverable_stall`** after 3 "consecutive test failures" even though its code
was, by then, green (34/34 pass in 0.18s when run directly). The Coach's
*isolated* pytest run timed out at 60s with `tests_run=0` (an early-turn test
version blocked on a real connection before mocks were added). That timeout — an
**absent** test signal — was then **coerced into an explicit test failure**, and
three such turns tripped the context-pollution guard.

This is the **`absence-of-failure-is-not-success` family, false-red direction**
(`.claude/rules/absence-of-failure-is-not-success.md`, item 4). CKPTTESTRED01
already fixed it **at the checkpoint layer** (an absent `None` breaks the run, is
not counted). This task fixes the same defect **at the layers upstream of the
checkpoint that destroy the tri-state distinction before CKPTTESTRED01 can
protect it.**

## The key insight — the kill is a coercion ONE LAYER ABOVE the pollution guard

CKPTTESTRED01's guard is **intact and correct**:
[`worktree_checkpoints.py:737`](../../guardkit/orchestrator/worktree_checkpoints.py#L737)
counts a failure only on `cp.tests_passed is False`; a `None` (UNKNOWN) breaks
the consecutive-failure run. **Do not weaken it.**

The FMDR timeout never *reaches* the guard as `None`. The sequence:

1. Coach isolated run times out → `IndependentTestResult(signal_absent=True)`.
2. `_run_deterministic_phase_4` maps it to
   `{"status": "failed", "error": "absent test signal …", "tests_run": 0}`
   ([`specialist_invocations.py` ~1092](../../guardkit/orchestrator/specialist_invocations.py#L1092)).
   The **ran-and-failed** branch (~1120) emits the *same* `status="failed"` with
   `error="tests failed …"` — **the only deterministic discriminator between the
   two is the `error` prefix.**
3. The "narrative false-green" reconciliation
   ([`agent_invoker.py:8358-8384`](../../guardkit/orchestrator/agent_invoker.py#L8358))
   fires on `status=="failed"` **alone** — it does not branch on `error` — and
   flattens the distinction:
   `qg["tests_passed"] = phase_4_block.get("tests_run", 0) or 0` → `0` →
   `bool(0)=False`; it also hard-sets `qg["coverage_met"]=False`.
4. That explicit `False` is written to `task_work_results.json`, read back, and
   surfaces as `quality_gates.tests_passed=False`; `_extract_tests_passed` returns
   explicit `False`; the guard *correctly* counts it. 3 turns → kill.

**Why CKPTTESTRED01 didn't cover it:** CKPTTESTRED01 guards the *signal layer*
(an LLM-Coach report that simply *omits* a verdict → `None`). The reconciliation
runs *before* the Coach reads the file and **manufactures an explicit `False`
from an absent signal**, upstream of where the tri-state is protected. Same
defect class, different layer.

**The reconciliation already has the discriminator it needs:** `phase_4_block`
carries `error` in that exact block (it is logged at
[`agent_invoker.py:8366`](../../guardkit/orchestrator/agent_invoker.py#L8366)).
Branching on the `error` prefix needs **no new heuristic.**

## The defect is systemic — THREE layers coerce a timeout into a counted failure

The originating analysis found one (the reconciliation). The regression review
found two more, **both unprotected by a reconciliation-only fix**:

| # | Layer | File:line | What it does on a timeout | Direction |
|---|---|---|---|---|
| L1 | Phase-4 reconciliation (pytest oracle) | [`agent_invoker.py:8379`](../../guardkit/orchestrator/agent_invoker.py#L8379) | `tests_passed = 0` (False) + `coverage_met=False` | false-red kill |
| L2 | BDD runner | [`bdd_runner.py:604-611`](../../guardkit/orchestrator/quality_gates/bdd_runner.py#L604) → [`_synthesise_runner_error_failure:482-506`](../../guardkit/orchestrator/quality_gates/bdd_runner.py#L482) | `returncode=-1` → `scenario_name="pytest_runner_error"` → `scenarios_failed≥1` | false-red kill (`--mode=bdd`) |
| L3 | Runtime parity | [`coach_validator.py:3092-3101`](../../guardkit/orchestrator/quality_gates/coach_validator.py#L3092) → [`_apply_runtime_parity_guard:5549`](../../guardkit/orchestrator/agent_invoker.py#L5549) | `RuntimeParityResult(ran=True, passed=False, timed_out=True)` → overrides approve→feedback | wasted-signal / non-convergence |

L2 deliberately classifies a BDD timeout as **ran-and-failed** (opposite of the
pytest oracle). L3's `except Exception` branch correctly uses `ran=False`
("runner errors are ABSENT") — but the **timeout branch** sets `ran=True`,
contradicting that posture. A complete fix must treat all three consistently, or
explicitly scope L2/L3 out with a stated rationale.

## Symptom

- `unrecoverable_stall` ("context pollution detected … no passing checkpoint")
  on a task whose code is green when tests are run directly.
- Coach log shows `Isolated test execution timed out after 60s` / `tests_run=0`
  followed by `… overriding to NOT passed (narrative false-green)`.
- For `--mode=bdd` tasks: 3 turns of `scenarios_failed=1` with
  `scenario_name="pytest_runner_error"` and `exit=-1`.
- For runtime-parity: a Coach `approve` flipped to feedback after a parity
  *timeout* (not a genuine standalone-run failure).

## Detection recipe

```bash
# L1 — reconciliation coerces an absent-signal timeout to explicit False?
rg -n "narrative false-green|reconciled_from_specialist|tests_passed.*tests_run.*or 0" \
   guardkit/orchestrator/agent_invoker.py
# L1 — the two phase-4 branches share status="failed", differ only by error prefix:
rg -n "absent test signal|tests failed" guardkit/orchestrator/specialist_invocations.py
# L2 — BDD timeout surfaced as a failed scenario:
rg -n "pytest_runner_error|_synthesise_runner_error_failure|returncode=-1" \
   guardkit/orchestrator/quality_gates/bdd_runner.py
# L3 — runtime-parity timeout sets ran=True:
rg -n "timed_out=True|ran=True" guardkit/orchestrator/quality_gates/coach_validator.py
# Serialization gap — signal_absent NOT in to_dict():
rg -n "def to_dict" guardkit/orchestrator/quality_gates/coach_validator.py   # ~1160; confirm no signal_absent key
rg -n "signal_absent" guardkit/orchestrator/autobuild.py                     # 6740 (report path), 7797 (extract)
# Guard must stay intact (DO NOT WEAKEN):
rg -n "cp.tests_passed is False" guardkit/orchestrator/worktree_checkpoints.py  # ~737
```

## Workstreams, verdicts, and sequencing

Implement in order. **W1 + W2 are the load-bearing fix for the originating
incident and are low risk.** W3 and W4 are gated/deferred enhancements that, as
worded in the source analysis, would each cause a regression.

### W1 — Reconciliation: keep an absent-signal timeout as UNKNOWN (PRIMARY, low risk)

In the reconciliation override
([`agent_invoker.py:8358-8384`](../../guardkit/orchestrator/agent_invoker.py#L8358)),
branch on the phase-4 `error` prefix:

- `error.startswith("absent test signal")` →
  set `qg["tests_passed"] = None` (UNKNOWN); **do not** set `coverage_met=False`
  as a hard fail for the absent case; set a `reconciled_absent=True` marker.
- `error.startswith("tests failed")` (or any non-absent failure) → **unchanged**
  current behaviour (`tests_passed=0`/False, `coverage_met=False`).

CKPTTESTRED01's existing tri-state guard then absorbs the absent case with **zero
new failure definitions** and blast radius confined to this one site.

### W2 — Thread + serialize `signal_absent` (MANDATORY companion to W1)

Without this, W1's `None` is unreachable for the Coach's own isolated run:

1. Add `phase_4_block["signal_absent"]` in
   [`specialist_invocations.py` ~1092](../../guardkit/orchestrator/specialist_invocations.py#L1092)
   so downstream code branches on a boolean, not a string prefix (the string
   branch in W1 is the minimal fix; this makes it robust).
2. Serialize `independent_tests.signal_absent` in
   [`IndependentTestResult.to_dict()` ~1160-1164](../../guardkit/orchestrator/quality_gates/coach_validator.py#L1160)
   — it is currently omitted, so
   [`_extract_tests_passed`'s `independent.get("signal_absent") is True` guard at autobuild.py:7797](../../guardkit/orchestrator/autobuild.py#L7797)
   is dead for the Coach-run path. (The report path at
   [`autobuild.py:6740`](../../guardkit/orchestrator/autobuild.py#L6740) re-injects
   it, but the reconciliation writes the Coach *input* `task_work_results.json`,
   bypassing that enrichment.)

### W2b — Extend the UNKNOWN-not-False invariant to L2 (BDD) and L3 (runtime parity)

Either fix or **explicitly scope out with written rationale**:

- **L2 (BDD):** a `subprocess.TimeoutExpired` (`returncode=-1`) must NOT be
  synthesised as a failed scenario. Surface it as an absent/UNKNOWN BDD signal
  (distinct from a genuine `scenarios_failed`), so a BDD-mode task hitting the
  same hang is not killed. If scoped out: state that `--mode=bdd` tasks remain
  exposed and why.
- **L3 (runtime parity):** the timeout branch
  ([`coach_validator.py:3092-3101`](../../guardkit/orchestrator/quality_gates/coach_validator.py#L3092))
  should set `ran=False` (absent), matching the `except Exception` branch's
  "runner errors are ABSENT" posture, so a parity *timeout* does not convert a
  Coach approve into feedback. If scoped out: state the rationale.

### W3 — Per-test `--timeout` injection (ENHANCEMENT — only fully gated; do NOT ship unconditional)

The source analysis's item 1. **An unconditional `--timeout` is a CRITICAL
harness-wide regression** — `pytest-timeout` is not in guardkit deps and is not
installed into worktree venvs, so injection yields
`unrecognized arguments: --timeout` (returncode 4) on every project lacking it.
This is the already-reverted FEAT-FMDR-003 repo-side regression, replayed
harness-wide. Ship **only** with all of:

1. **Dependency handling** — prefer installing `pytest-timeout` into the worktree
   venv for Python stacks via
   [`environment_bootstrap.py`](../../guardkit/orchestrator/environment_bootstrap.py)
   (mirror the existing pytest-extras install); **or** probe
   (`importlib.util.find_spec('pytest_timeout')` in the pinned interpreter) and
   inject only on success, else fall back to the existing process-level
   `self.test_timeout` (no regression).
2. **Stack-agnostic gate** (`.claude/rules/stack-plugin-architecture.md`) — inject
   only on the Python branch (`test_cmd.startswith("pytest")` AND no active
   non-Python stack profile), by argv-splitting (not string-append). .NET/JS/Go
   suites get **no** timeout arg and keep existing absent-signal behaviour.
   Per-test timeout for non-Python stacks is an explicit non-goal.
3. **Defence-in-depth classifier** — extend the absence classifier (the
   `signal_absent` detection in `coach_validator.py`) to map
   `'unrecognized arguments: --timeout'` / returncode 4 → `signal_absent=True`,
   so a mis-probe degrades to an absent signal, never a counted failure.
4. **All FOUR injection sites**, not three — the standard run paths *and* the
   ABFIX-005 parallel-isolated temp-dir path. Audit
   `coach_validator.py` for every `pytest`-cmd construction site before claiming
   coverage.
5. **`--timeout-method`** chosen for asyncio-heavy suites (guardkit's own tests
   are pytest-asyncio): validate `thread` vs `signal` does not spuriously
   interrupt GIL-holding/async tests.

W3 does **not** fix the kill on its own — W1 does. W3 is a quality improvement
(per-test attribution) layered on top.

### W4 — Required test gate for TESTING-type tasks (DEFERRED behind classifier widening)

The source analysis's "see also" (the mirror-image false-*approval*, FMDR-004).
**A blanket `tests_required=False→True` flip is a NO-GO** — it re-creates the
false-red kill from the opposite gate: a host-substrate gap
(`psql: command not found`) classifies as `('code','n/a')` in
[`_classify_test_failure`](../../guardkit/orchestrator/quality_gates/coach_validator.py#L2080)
and counts as a real failure, and the verdict even flips green↔red on `wave_size`
via the parallel-contention amnesty
([`coach_validator.py:2140-2176`](../../guardkit/orchestrator/quality_gates/coach_validator.py#L2140)).
Pursue only **after**:

1. Widen `_classify_test_failure` with stack-agnostic shell signals
   (`'command not found'`, `'No such file or directory'`, `'executable not
   found'`) → `('infrastructure', high)` → `signal_absent=True` (UNKNOWN, routes
   through the same absence channel as W1).
2. Reserve explicit `False` for high-confidence **code-class** failures only.
3. For TESTING tasks, disable the parallel-contention amnesty on the task's own
   assertion failures (resolves the `wave_size` swing).
4. Set `zero_test_blocking` deliberately so a legitimately test-less TESTING
   subtask is not a silent UNKNOWN-pass.

This makes W4 a separate sub-task gated on classifier widening, not a one-line
flip in [`task_types.py`](../../guardkit/models/task_types.py#L129).

## Regression risks this task MUST avoid (DO-NOT list)

- **R1 (CRITICAL):** do NOT touch the `signal_absent` classifier to reclassify a
  timeout as "ran-and-failed" — `signal_absent=True` is the sole precondition for
  the false-green backstop `_reconcile_absent_independent_test_signal`
  ([`agent_invoker.py:5323/5378`](../../guardkit/orchestrator/agent_invoker.py#L5323)).
  Disarming it re-opens the TASK-AB-PERTASKFG01 false-green. (This is why the
  source analysis's item 2 is folded into W1, not implemented as worded.)
- **R2 (CRITICAL):** do NOT inject `--timeout` unconditionally (see W3 gating).
- **R3 (HIGH):** do NOT weaken `should_rollback`'s genuine-`False` tally
  ([`worktree_checkpoints.py:737`](../../guardkit/orchestrator/worktree_checkpoints.py#L737))
  — three genuine ran-and-failed turns must still stall.
- **R4 (HIGH):** fix at the coercion site (W1), not only the guard — the
  `tests_passed=0` coercion also feeds rollback-target selection
  (`find_last_passing_checkpoint`) and Player feedback; a guard-only patch leaves
  absent→False corruption live elsewhere.
- **R5 (MEDIUM):** ensure `max_turns` still terminates a task that yields `None`
  every turn with `success=False` (never approve) — guard against
  false-green-by-non-termination.

## Acceptance Criteria

- [ ] **W1:** the reconciliation override branches on the phase-4 `error` prefix;
      an `"absent test signal"` timeout yields `quality_gates.tests_passed=None`
      (not `0`/False) and does not hard-set `coverage_met=False`; a `"tests
      failed"` result is unchanged.
- [ ] **W2:** `phase_4_block["signal_absent"]` is set in `specialist_invocations`
      and `IndependentTestResult.to_dict()` serializes `signal_absent`;
      `_extract_tests_passed` returns `None` for a Coach-run absent signal.
- [ ] **W2b:** L2 (BDD timeout) and L3 (runtime-parity timeout) are EITHER routed
      to an absent/UNKNOWN signal OR explicitly scoped out with a written
      rationale in this task's Implementation Summary.
- [ ] **No regression:** CKPTTESTRED01's tri-state guard is unchanged; three
      genuine consecutive ran-and-failed turns still produce `unrecoverable_stall`.
- [ ] **No regression:** the false-green backstop
      (`_reconcile_absent_independent_test_signal`) still overrides approve→feedback
      on a Coach-isolated timeout (`signal_absent` stays `True`).
- [ ] **W3 (if included):** `--timeout` is injected only when `pytest-timeout` is
      resolvable in the worktree interpreter AND the stack is Python; absence
      falls back to process-level timeout with no `unrecognized arguments`
      failure; a usage error degrades to `signal_absent=True`; all injection sites
      covered.
- [ ] **W4 (if included):** `_classify_test_failure` maps host-substrate gaps to
      an absent signal; TESTING-type real code bugs are rejected in BOTH
      single-task and parallel waves; substrate-blocked TESTING tasks do NOT
      `unrecoverable_stall`.
- [ ] **CI:** any new test that touches harness dispatch
      (`select_harness`/SDK-harness paths) pins `GUARDKIT_HARNESS=sdk` or
      `skipif` — the main `tests.yml` runs without guardkitfactory/langchain
      (see `.claude/rules` memory `ci-tests-yml-no-guardkitfactory`).
- [ ] **New rule seeded** (see below).

## Tests / regression-proofs (reproducers)

Mirror `tests/unit/test_checkpoint_pollution_absent_test_signal.py`.

- **T1 (W1, both poles):** (a) phase-4 `error="absent test signal …", tests_run=0`
  → reconciliation emits `tests_passed=None` → tri-state `None` → `should_rollback`
  False across 3 turns (no kill). (b) 3× phase-4 `error="tests failed …",
  tests_run≥1` → explicit `False` → `should_rollback` True (still stalls). Both
  must hold.
- **T2 (W3 dependency hazard):** plugin-present → injected; plugin-absent → no
  injection + process-level fallback (no usage error); non-Python stack → no
  injection; `--timeout` usage error (rc=4) → `signal_absent=True`.
- **T3 (W1/PERTASKFG01 backstop):** a Coach-isolated timeout keeps
  `signal_absent=True` and `_reconcile_absent_independent_test_signal` still
  overrides approve→feedback (backstop NOT disarmed).
- **T4 (W2 serialization):** `to_dict()` includes `signal_absent`;
  `_extract_tests_passed` reads it from a Coach-run report and returns `None`.
- **T5 (W2b):** a BDD-mode timeout does not produce an `unrecoverable_stall`
  (or test asserts the documented scope-out); a runtime-parity timeout does not
  flip a Coach approve to feedback (or asserts the scope-out).
- **T6 (non-termination bound):** a task whose Coach run times out every turn for
  `max_turns` terminates `success=False`, never `approve`.
- **T7 (W4, if pursued — mirrors FMDR-004):** TESTING task with a host-binary gap
  → no stall; TESTING task with a real code bug → rejected in single-task AND
  parallel waves.

## New `.claude/rules/` entry to seed

The defect recurs at **three independent layers** (reconciliation, BDD runner,
runtime parity), all coercing an absent timeout into a counted failure — the
signature for a rule, not a one-site patch. Seed
`.claude/rules/absence-must-survive-every-reconciliation-layer.md` (sibling of
`absence-of-failure-is-not-success.md`):

> *An absent oracle signal must be preserved as `None`/UNKNOWN through every
> reconciliation, synthesis, or serialization layer between the oracle and the
> consuming gate. Any intermediate layer that coerces absent → explicit
> pass/fail (e.g. `tests_run or 0` → `False`, a timeout → a synthesised failed
> scenario, a timeout → `ran=True/passed=False`) is a CKPTTESTRED01-class
> regression, even when the terminal guard is itself tri-state-correct.*

Pair with a Graphiti node under `guardkit__project_decisions` linked to the
CKPTTESTRED01 instance.

## Evidence / references

- Source post-mortem: `forge/docs/reviews/FEAT-FMDR-autobuild-false-green-analysis.md` (lines 48-93, 62-93).
- Session handoff: `forge/docs/handoffs/FMDR-NATS-SESSION-DISCOVERIES-2026-06-24.md` (line 111).
- Prior fix (checkpoint layer): `tasks/completed/TASK-FIX-CKPTTESTRED01/TASK-FIX-CKPTTESTRED01.md`.
- Invariant family: `.claude/rules/absence-of-failure-is-not-success.md`,
  `.claude/rules/smoke-gate-is-feedback-not-terminator.md`,
  `.claude/rules/per-task-green-is-not-feature-green.md`,
  `.claude/rules/stack-plugin-architecture.md`.
- Pre-implementation regression review: workflow `abfix-010-regression-review`
  (2026-06-24) — 10 agents, all four load-bearing facts confirmed against `main`.
