# Absence must survive every reconciliation/synthesis layer, not just the terminal guard

> **Source**: Seeded by TASK-ABFIX-010 (2026-06-24) from the FEAT-FMDR autobuild
> post-mortem (`forge/docs/reviews/FEAT-FMDR-autobuild-false-green-analysis.md`)
> and its pre-implementation regression review. **Status: FIXED for L1 + L2
> (commit `069086a0`, 2026-06-24, TASK-ABFIX-010 W1+W2+L2). L3 (runtime-parity
> timeout) is NOT in scope — see below.** The L1 fingerprints below now describe
> the *fixed* state (the reconciliation branches on `signal_absent`/error and
> emits `None`); the pre-fix coercion is gone from `main`.
>
> **L3 is a deliberate exception, not an instance of this rule.** A runtime-parity
> *timeout* is intentionally treated as ran-and-failed (blocks), distinct from a
> runner-error (absent) — TASK-AB-COACHRUNPARITY01, operator-reaffirmed 2026-06-24.
> Rationale: a smoke entry point that *starts and hangs* is a genuine deliverable
> defect (it would hang in production), unlike a test-oracle timeout which is a
> verification artifact. Do NOT "fix" `_gather_runtime_parity`'s timeout branch to
> `ran=False` under this rule — that test (`test_timeout_is_ran_and_failed`) pins
> the intended behaviour.
>
> Pair with the Graphiti design-rule node *"absence must survive every
> reconciliation layer (CKPTTESTRED01 generalized upstream)"* under
> `guardkit__project_decisions`. Direct parent / instance-superset of
> [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md)
> (item 4, CKPTTESTRED01 — the *terminal guard* tri-state fix). Sibling of
> [`path-string-mismatch-is-not-dishonesty.md`](path-string-mismatch-is-not-dishonesty.md),
> [`harness-cancellation-contract.md`](harness-cancellation-contract.md),
> [`evidence-boundary-narrower-than-write-surface.md`](evidence-boundary-narrower-than-write-surface.md),
> [`smoke-gate-is-feedback-not-terminator.md`](smoke-gate-is-feedback-not-terminator.md),
> and [`per-task-green-is-not-feature-green.md`](per-task-green-is-not-feature-green.md).
> The shared meta-frame: *a binary verdict from a low-fidelity oracle that cannot
> distinguish "no signal" from "positive/negative signal"*.

## The rule

An absent oracle signal MUST be preserved as `None` / UNKNOWN through **every**
reconciliation, synthesis, or serialization layer between the oracle and the
consuming gate. Any intermediate layer that coerces absent → explicit pass/fail
is a CKPTTESTRED01-class regression — **even when the terminal guard is itself
tri-state-correct.**

CKPTTESTRED01 made the *terminal* guard
([`worktree_checkpoints.py:737`](../../guardkit/orchestrator/worktree_checkpoints.py#L737)
— `cp.tests_passed is False` counts; `None` breaks the run) tri-state-correct.
That is necessary but **not sufficient**: a correct terminal guard is defeated if
any layer *upstream* of it converts the absent signal into an explicit `False`
before the guard ever sees it. Fixing the guard alone leaves the defect live one
layer up. The invariant must hold at every hop, not just the last one.

This rule's locus is **preservation** (a.k.a. transport): unlike its siblings, the
oracle correctly emits "absent" — the defect is a layer in transit *destroying*
that distinction. The single sentence the whole rule reduces to: **a timeout (or
any "the oracle could not run" outcome) must arrive at the consuming gate as
`None`, never as `False`.**

## Why this rule exists

In the FEAT-FMDR autobuild run (SDK harness), **TASK-FMDR-001 was killed as
`unrecoverable_stall`** after 3 "consecutive test failures" on a codebase that was
green (34/34 pass in 0.18s run directly). The Coach's isolated pytest run timed
out at 60s with `tests_run=0` — an *absent* signal — which was then coerced into
an explicit failure three turns running.

The regression review found the absent→False coercion at two genuine layers (L1,
L2 — both fixed by TASK-ABFIX-010) and one layer (L3) that on inspection was a
**deliberate prior decision, NOT a coercion bug**:

| # | Layer | File:line | Pre-fix behaviour | Status |
|---|---|---|---|---|
| L1 | Phase-4 reconciliation (pytest oracle) | [`agent_invoker.py:8358+`](../../guardkit/orchestrator/agent_invoker.py#L8358) (was `tests_passed = tests_run or 0` → `False`; `coverage_met=False`) | absent → explicit `False` (false-red kill) | **FIXED** — branches on `signal_absent`/error → `None`; carried through `verify_quality_gates` → `QualityGateStatus(Optional[bool])` → `to_dict` → checkpoint |
| L2 | BDD runner | [`bdd_runner.py`](../../guardkit/orchestrator/quality_gates/bdd_runner.py) (was `TimeoutExpired` → synthesised `scenarios_failed≥1`) | absent → ran-and-failed (false-red, `--mode=bdd`) | **FIXED** — `_PYTEST_EXIT_TIMEOUT` sentinel → `run_bdd_for_task` returns `None` (absent), never a synthesised failure |
| L3 | Runtime parity | [`coach_validator.py` `_gather_runtime_parity`](../../guardkit/orchestrator/quality_gates/coach_validator.py) timeout branch sets `ran=True, passed=False` | (NOT a bug) | **OUT OF SCOPE — deliberate.** A runtime-parity *timeout* (smoke entry point ran but hung) is intentionally ran-and-failed per TASK-AB-COACHRUNPARITY01, distinct from a runner-error (absent). A hung entry point is a real deliverable defect. Pinned by `test_timeout_is_ran_and_failed`. Do NOT flip it under this rule. |

L1 was the kill mechanism for the standard pytest oracle; CKPTTESTRED01 sits
*downstream* of L1 and could not see the absent signal because L1 already replaced
it with `False` (now fixed → `None`). L2 (pre-fix) classified a BDD timeout as
ran-and-failed — also fixed to absent (`None`). L3 looked like a third instance
(its timeout branch sets `ran=True` while its `except Exception` branch uses
`ran=False`), but that asymmetry is **deliberate**: TASK-AB-COACHRUNPARITY01 draws
a real line between a smoke entry point that *ran and hung* (a deliverable defect
worth blocking) and one that *could not start* (absent). So this rule covers L1
and L2 (genuine absent→False coercions); L3 is explicitly excluded.

A contributing structural fact: at the oracle layer, the absent branch
([`specialist_invocations.py` ~1092](../../guardkit/orchestrator/specialist_invocations.py#L1092),
`error="absent test signal …"`) and the genuine-failure branch (~1120,
`error="tests failed …"`) both return `status="failed"` — distinguishable only by
the `error` prefix. L1's reconciliation fires on `status=="failed"` alone and does
not branch on `error`, so it flattens the two into one `False`.

## Symptom

- `unrecoverable_stall` ("context pollution detected … no passing checkpoint") on
  a task whose code is green when its tests are run directly.
- Coach log: `Isolated test execution timed out … tests_run=0` →
  `… overriding to NOT passed (narrative false-green)`.
- `--mode=bdd`: repeated `scenarios_failed=1`, `scenario_name="pytest_runner_error"`,
  `exit=-1`.
- Runtime parity: a Coach `approve` flipped to feedback after a parity *timeout*
  (not a genuine standalone-run failure).
- The terminal guard (`worktree_checkpoints.should_rollback`) is tri-state-correct
  and *still* fires — proving the coercion happened upstream.

## Detection recipe

```bash
# L1 — reconciliation coerces an absent-signal timeout to explicit False:
rg -n "narrative false-green|tests_passed.*tests_run.*or 0|reconciled_from_specialist" \
   guardkit/orchestrator/agent_invoker.py
# Oracle's two branches share status="failed", differ only by error prefix:
rg -n "absent test signal|tests failed" guardkit/orchestrator/specialist_invocations.py
# L2 — BDD timeout synthesised as a failed scenario:
rg -n "pytest_runner_error|_synthesise_runner_error_failure|returncode=-1" \
   guardkit/orchestrator/quality_gates/bdd_runner.py
# L3 — runtime-parity timeout sets ran=True (should be ran=False / absent):
rg -n "timed_out=True|ran=True" guardkit/orchestrator/quality_gates/coach_validator.py
# Serialization gap — signal_absent NOT carried by to_dict(), so the absent path
# is unreachable for the Coach's own run:
rg -n "def to_dict" guardkit/orchestrator/quality_gates/coach_validator.py   # ~1160; confirm no signal_absent
rg -n "signal_absent" guardkit/orchestrator/autobuild.py                     # 6740 (report path), 7797 (extract)
# Terminal guard MUST stay intact (do NOT weaken):
rg -n "cp.tests_passed is False" guardkit/orchestrator/worktree_checkpoints.py  # ~737
# Sibling-rule lookup:
rg "absence-must-survive|absence-of-failure|per-task-green-is-not-feature-green" .claude/rules/
```

## Remediation recipe

1. **Fix at the coercion site, not the terminal guard.** Patching only the guard
   (CKPTTESTRED01) leaves the absent→False corruption live everywhere downstream
   of L1 (rollback-target selection via `find_last_passing_checkpoint`, Player
   feedback, completion gates). The invariant must be restored where absence is
   *destroyed*.
2. **Branch on the existing discriminator.** L1 already has `phase_4_block["error"]`
   in scope (it is logged). On `error.startswith("absent test signal")` set
   `tests_passed = None` (UNKNOWN) and do **not** hard-set `coverage_met=False`;
   on a genuine `"tests failed"` keep explicit `False`. No new heuristic.
3. **Make the boolean explicit and serialize it.** Thread
   `phase_4_block["signal_absent"]` and serialize
   `IndependentTestResult.signal_absent` in `to_dict()`
   ([`coach_validator.py` ~1160](../../guardkit/orchestrator/quality_gates/coach_validator.py#L1160))
   so downstream branches on a boolean, and so
   [`_extract_tests_passed`'s `signal_absent is True` guard (autobuild.py:7797)](../../guardkit/orchestrator/autobuild.py#L7797)
   is reachable for the Coach-run path (today it is dead — `to_dict()` omits it,
   and the reconciliation writes the Coach *input* `task_work_results.json`, which
   bypasses the report-path re-injection at
   [`autobuild.py:6740`](../../guardkit/orchestrator/autobuild.py#L6740)).
4. **Apply the invariant at every layer, or scope out in writing.** L2 (BDD
   timeout) and L3 (runtime-parity timeout) must each route a timeout to an
   absent/UNKNOWN signal, OR the task that touches them must state explicitly that
   the layer remains exposed and why. Silent partial coverage is the trap: fixing
   L1 alone makes `--mode=bdd` and parity tasks *look* covered when they are not.
5. **Do NOT disarm the false-green backstop.** `signal_absent=True` is the sole
   precondition for `_reconcile_absent_independent_test_signal`
   ([`agent_invoker.py:5323/5378`](../../guardkit/orchestrator/agent_invoker.py#L5323)),
   which overrides a Coach approve→feedback when the Coach saw no test signal.
   Preserving absence as `None` for the *checkpoint* must not flip `signal_absent`
   to `False` for the *backstop* — keep absence absent in both directions
   (false-red AND false-green).
6. **Do NOT weaken the terminal guard.** Three genuine ran-and-failed turns
   (`tests_passed is False` from a real failure) must still stall.
7. **Bound non-termination.** A task that yields `None` every turn must terminate
   via `max_turns` with `success=False`, never `approve` — else preserving absence
   becomes a false-green-by-non-termination.

## Grep-able signature (for next agent)

```bash
# Regression fingerprint (POST-FIX, commit 069086a0): the L1 fix must persist —
# the reconciliation MUST branch on signal_absent and emit None. These MUST MATCH;
# absence is a regression (the absent→False coercion has returned):
rg -n "reconciled_absent" guardkit/orchestrator/agent_invoker.py
rg -n "reconciled_absent" guardkit/orchestrator/quality_gates/coach_validator.py  # verify_quality_gates short-circuit
rg -n "tests_passed: Optional\[bool\]" guardkit/orchestrator/quality_gates/coach_validator.py
# The OLD coercion (unconditional ``tests_run or 0`` for the absent case) MUST NOT
# return on the absent path — it now lives only under the genuine-fail else-branch:
rg -n "qg\[.tests_passed.\] = phase_4_block.get\(.tests_run., 0\) or 0" \
   guardkit/orchestrator/agent_invoker.py
# Terminal guard intact (must remain TRUE both before and after):
rg -n "cp.tests_passed is False" guardkit/orchestrator/worktree_checkpoints.py
# Sibling-rule lookup (this rule + the family):
rg "absence-must-survive|absence-of-failure|path-string-mismatch|harness-cancellation|evidence-boundary-narrower|smoke-gate-is-feedback|per-task-green-is-not-feature-green" .claude/rules/
```

## Meta-frame

This rule adds the **preservation** (transport) locus to the family. The prior
siblings differ by *which part of the oracle pipeline produces the spurious "no
signal"*; this one is unique in that the oracle gets it RIGHT (it emits "absent")
and a downstream **transit layer destroys the distinction** before the consuming
gate sees it.

| Rule | Failure locus | Direction | Spurious "no signal" comes from… |
|---|---|---|---|
| `absence-of-failure-is-not-success` | interpretation | false-green / false-red | a zero/absent counter read as a verdict at the consuming gate |
| `path-string-mismatch-is-not-dishonesty` | interpretation | false-red | a path miss read as a lie when the orchestrator moved the file |
| `harness-cancellation-contract` | dispatch | divergence | a cancel that no-ops on a substrate it wasn't written for |
| `evidence-boundary-narrower-than-write-surface` | collection | both | work done outside the oracle's *spatial* aperture |
| `per-task-green-is-not-feature-green` | collection | false-green | integration outside the oracle's *assembly/temporal* aperture |
| `smoke-gate-is-feedback-not-terminator` | disposition | wasted-signal | a *correct* high-fidelity failure terminating instead of feeding back |
| **`absence-must-survive-every-reconciliation-layer`** | **preservation** | **false-red (+ false-green-by-non-termination)** | **a correctly-absent signal coerced to explicit pass/fail by a transit layer, before a tri-state-correct guard can see it** |

The shared remediation is to pair the binary verdict with a positive-evidence
precondition. CKPTTESTRED01 placed that precondition at the *terminal guard*; this
rule generalizes it: the precondition must hold — absence must remain
representable as `None` — at *every* layer the signal passes through.

## Prior art

- **Direct parent (terminal-guard instance)**:
  [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md)
  item 4 (CKPTTESTRED01, commit `c6b5e7d9`) — fixed the consuming guard;
  this rule covers the layers upstream of it.
- **Tests-pass / production-fails lineage**:
  [`namespace-hygiene.md`](namespace-hygiene.md),
  [`smoke-gate-is-feedback-not-terminator.md`](smoke-gate-is-feedback-not-terminator.md)
  (arm b RuntimeParityResult — the L3 component; its timeout branch's
  `ran=True` is a *deliberate* COACHRUNPARITY01 distinction, NOT an instance of
  this rule — see "What the rule does NOT cover").
- **Originating defect**: FEAT-FMDR autobuild run — TASK-FMDR-001 false `unrecoverable_stall`
  on a green codebase via the L1 timeout coercion.
- **Fix (LANDED, commit `069086a0`, 2026-06-24)**: TASK-ABFIX-010
  (`tasks/in_review/TASK-ABFIX-010/`). W1 = L1 reconciliation branch-on-
  `signal_absent`/error → `None`, carried through `verify_quality_gates` (a
  `reconciled_absent` short-circuit) → `QualityGateStatus.tests_passed:
  Optional[bool]` (None appended, not skipped) → `to_dict` → checkpoint; W2 =
  thread + serialize `signal_absent`; W2b/L2 = BDD timeout → `None`. **L3 closed
  as wontfix** (deliberate COACHRUNPARITY01 semantics, operator-reaffirmed).
  Reproducers: `tests/unit/test_abfix010_absent_reconciliation.py` (8) +
  `test_bdd_runner.py::test_timeout_is_absent_not_a_synthesised_failure` (1).

## When this rule triggers

- Before introducing or modifying ANY layer that sits between a test/runtime
  oracle and a consuming gate and that can observe a timeout / "could not run"
  outcome: the Phase-4 reconciliation (`agent_invoker.py`), the BDD runner
  (`bdd_runner.py`), runtime parity (`coach_validator.py`), evidence-bundle
  synthesis, or any new oracle reconciler.
- Before adding a new `to_dict()` / serialization for an evidence object that
  carries an absent/UNKNOWN flag — confirm the flag survives serialization.
- During Phase 2.5 architectural review for anything touching
  `agent_invoker.py` reconciliation, `coach_validator.py` evidence, `bdd_runner.py`,
  `worktree_checkpoints.py`, or `autobuild.py` `_extract_tests_passed`.
- During any diagnostic session investigating an `unrecoverable_stall` on a
  codebase that is green when its tests are run directly, or a Coach verdict that
  flips on a *timeout* rather than a genuine failure.

## What the rule does NOT cover

- **Genuine ran-and-failed signals.** A real failing test (`tests_passed=False`,
  `signal_absent=False`) must stay `False` and must still count toward the stall
  tally and the backstop. This rule is permissive only for *absent* signals.
- **The terminal guard itself.** That is CKPTTESTRED01's territory
  (`absence-of-failure-is-not-success.md` item 4); this rule presumes the guard is
  already tri-state-correct and addresses the layers upstream of it.
- **Coach-side hallucination** of a passing/failing verdict it never ran — a
  different meta-defect (hallucinated evidence), not a mis-preserved absent one.
- **Non-test oracles** outside the autobuild test/runtime signal path (e.g.
  honesty path-existence checks) — those have their own absence rules
  (`path-string-mismatch-is-not-dishonesty.md`).
- **Runtime-parity timeouts (L3).** `_gather_runtime_parity`'s timeout branch
  deliberately sets `ran=True` (ran-and-failed/blocks), per TASK-AB-COACHRUNPARITY01
  (operator-reaffirmed 2026-06-24). A smoke entry point that *starts and hangs* is
  a genuine deliverable defect (it would hang in production), unlike a verification
  timeout. This is NOT an absent→False coercion and must not be "fixed" under this
  rule; `test_timeout_is_ran_and_failed` pins it. A runner-error (couldn't start)
  remains absent (`ran=False`) — that asymmetry is the intended design.
