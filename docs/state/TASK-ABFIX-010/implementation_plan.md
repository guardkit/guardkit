# Implementation Plan — TASK-ABFIX-010 (v2, post architectural review)

**Scope (confirmed at Phase 1.6):** W1 + W2 + W2b. W3 (`--timeout` injection) and
W4 (required test gate) are explicitly deferred to separate follow-on tasks.

**Mode:** standard · **Intensity:** standard · **Complexity:** 7/10 · **Workflow:** design-only

**One-sentence design:** keep an absent test signal representable as `None`
(UNKNOWN) through every reconciliation/synthesis/serialization layer **and**
through the gate-evaluation chain, so the **approval** consumer treats absent as
"don't approve, give feedback" while the **checkpoint pollution** consumer treats
it as "not a failure" — without ever resolving it to a pass.

> **v2 note:** revised after Phase 2.5B architectural review (score 64/100,
> approved-with-mandatory-corrections). v1 fixed only the reconciliation dict and
> would NOT have fixed the bug — `verify_quality_gates` reads `all_passed` first
> and never reads the `None` written to `tests_passed`. v2 carries the tri-state
> through the gate chain. See "Architectural review" section below.

---

## Design principle (the invariant being restored)

`.claude/rules/absence-must-survive-every-reconciliation-layer.md`. Two consumers
of the test signal must be **decoupled**, because absent means different things to
each:

| Consumer | Absent signal must mean | Today it wrongly gets |
|---|---|---|
| **Coach approval** (`verify_quality_gates` → `all_gates_passed`) | NOT approve → feed back (absence ≠ pass; smoke-gate "feed back, not terminate") | `False` (looks like a real failure — fine for approval, but…) |
| **Checkpoint pollution** (`_extract_tests_passed` → `should_rollback`) | NOT counted as a failure (`None`; CKPTTESTRED01) | …that same `False` is counted → 3 turns → false `unrecoverable_stall` |

The terminal pollution guard ([worktree_checkpoints.py:737](../../../guardkit/orchestrator/worktree_checkpoints.py#L737))
is tri-state-correct and **must not be touched**. The fix carries `None` to it.

---

## Files to modify (6 files)

| # | File / function | Change | WS |
|---|------|--------|----|
| 1 | `agent_invoker.py` reconciliation (~8358-8384) | Branch on `phase_4_block["signal_absent"]`/`error` prefix. Absent → `all_passed=None`, `tests_passing=None`, `tests_passed=None`, `reconciled_absent=True`; **do NOT** copy the absent block's `tests_failed=0` into `qg`; leave `coverage_met` unchanged. Genuine fail → unchanged. | W1 |
| 2 | `coach_validator.py` `verify_quality_gates` (~3394-3425) | Add a `reconciled_absent` short-circuit at the TOP of the test-resolution block (after the `tests_required` skip, BEFORE the `all_passed`/`tests_failed` logic): `tests_passed = None`. Prevents the `tests_failed==0 → True` false-green. | W1 |
| 3 | `coach_validator.py` `QualityGateStatus` (~952-976) | `tests_passed: Optional[bool]`. In `__post_init__`, **append** `tests_passed` to `required_gates` even when `None` (so `all([None,…])` is falsy → does NOT auto-approve); coerce `all_gates_passed = bool(all(required_gates))`. **Do NOT skip `None`** — skipping would let other gates approve despite absent tests (gate-level false-green). | W1 |
| 4 | `coach_validator.py` `_feedback_from_gates` (~7710-7739) | Guard `gates.tests_passed is False` (not `not gates.tests_passed`); add a distinct branch for `tests_passed is None` → emit an **absent-signal** feedback issue ("test oracle did not run — timeout/absent; ensure tests run within budget"), driving a feedback turn but messaged as absent, not "tests failed". | W1 |
| 5 | `specialist_invocations.py` absent branch (~1092-1098) | Add `"signal_absent": True` to the absent-branch dict (boolean discriminator for #1, so it doesn't rely on the error-string prefix). | W2 |
| 6 | `coach_validator.py` `to_dict()` (~1160-1165) | Serialize `independent_tests.signal_absent` so [autobuild.py:7797](../../../guardkit/orchestrator/autobuild.py#L7797)'s `signal_absent is True → None` guard is reachable for the Coach's own independent run (the second decoupling path). | W2 |
| 7 | `bdd_runner.py` (~482-506, 604-611) | `subprocess.TimeoutExpired` (test the exception type at the catch site, not `returncode==-1`) → emit an absent/UNKNOWN BDD signal, NOT a synthesised `pytest_runner_error` scenario. Genuine non-timeout runner errors keep `scenarios_failed≥1`. | W2b (L2) |
| 8 | `coach_validator.py` runtime parity (~3092-3101) | Timeout branch → `RuntimeParityResult(ran=False, …)` (match the `except Exception` "runner errors are ABSENT" posture), so a parity *timeout* does not flip a Coach approve→feedback. Genuine non-zero standalone exit keeps `ran=True, passed=False`. | W2b (L3) |

(6 files; `coach_validator.py` carries four of the changes.) No new modules, no
new dependencies.

---

## The two decoupling paths (why both W1-gate and W2-serialize are needed)

1. **Reconciliation/specialist path** (the FMDR-001 kill): raw `qg` dict (W1 #1)
   → `verify_quality_gates` `reconciled_absent` short-circuit (#2) →
   `QualityGateStatus.tests_passed=None` (#3) → `to_dict()` serializes it →
   `_extract_tests_passed` reads `quality_gates.tests_passed=None` → checkpoint
   sees `None`.
2. **Coach independent-run path**: `IndependentTestResult.signal_absent=True` →
   `to_dict()` serializes it (#6) → `_extract_tests_passed` reads
   `independent_tests.signal_absent → None` (the autobuild.py:7797 guard, dead
   today) → checkpoint sees `None`.

Both terminate at the same tri-state guard. Approval is gated to "not approve"
in both via `all_gates_passed=False` (#3) — the loop feeds back, bounded by
`max_turns` (T6).

---

## Architectural review (Phase 2.5B) — score 64/100, mandatory corrections folded in

| Finding | Disposition |
|---|---|
| **BLOCKING:** `verify_quality_gates` reads `all_passed` first; v1's `None` on `tests_passed` was stranded → bug unfixed | Fixed by #2/#3 (carry tri-state through the gate chain) |
| `QualityGateStatus.tests_passed: bool` not `Optional` | Fixed by #3 |
| `_feedback_from_gates` `not gates.tests_passed` truthy for `None` | Fixed by #4 |
| `to_dict()` reads dataclass not raw dict (Issue 3) | Resolved: #3 puts `None` on the dataclass, so it serializes |
| **Reviewer R2 said "skip `None` in `required_gates`"** | **Overridden** — skipping causes a gate-level false-green (other gates approve despite absent tests). Verified: absent branch carries `tests_failed=0`, so we APPEND `None` and short-circuit in `verify_quality_gates`. This is the one place the design departs from the review, with rationale. |
| L3 (runtime parity → `ran=False`) | Confirmed sound (R4) |
| L2 (discriminate on exception type, not returncode) | Adopted (R5) |

---

## Consumer audit (resolved into concrete changes)

Every reader of `quality_gates.tests_passed` / `QualityGateStatus.tests_passed`,
None-safety status after this task:

- `verify_quality_gates` (3394-3425) — **changed** (#2): absent short-circuit.
- `QualityGateStatus.__post_init__` (966-976) — **changed** (#3): append `None`, coerce bool.
- `_feedback_from_gates` (7710-7739) — **changed** (#4): `is False` guard + absent branch.
- `_extract_tests_passed` (autobuild.py 7802-7804) — **already None-safe**. ✓
- `worktree_checkpoints.should_rollback`/`find_last_passing_checkpoint` — tri-state via CKPTTESTRED01; receives `None` unchanged. ✓
- Any display/log — render `None` as `unknown`.

`grep -n "not .*\.tests_passed\|tests_passed ==" guardkit/` is a pre-implementation AC to catch any remaining non-None-safe reader.

---

## Test strategy (reproducers — mirror `tests/unit/test_checkpoint_pollution_absent_test_signal.py`)

| Test | Asserts | WS |
|------|---------|----|
| T1a | phase-4 absent timeout → reconciliation `all_passed=None`+`reconciled_absent`; `verify_quality_gates`→`tests_passed=None`; 3 turns → `should_rollback` False (no kill) | W1 |
| **T1c** | phase-4 absent timeout with `tests_failed=0` present → `verify_quality_gates` does NOT resolve `tests_passed=True` (the false-GREEN guard) | W1 |
| T1b | 3× genuine `error="tests failed…", tests_run≥1` → `tests_passed`=False; `should_rollback` True (still stalls) | W1 regression |
| T1d | absent turn → `all_gates_passed=False` (Coach does NOT approve; gives feedback) | W1 |
| T3 | Coach-isolated timeout keeps `signal_absent=True`; `_reconcile_absent_independent_test_signal` ([agent_invoker.py:5323](../../../guardkit/orchestrator/agent_invoker.py#L5323)) still overrides approve→feedback (false-green backstop NOT disarmed) | W1/W2 |
| T4 | `to_dict()` includes `signal_absent`; `_extract_tests_passed` reads it from a Coach-run report → `None` | W2 |
| T5a | BDD `TimeoutExpired` → absent signal, no `scenarios_failed≥1`, no `unrecoverable_stall`; a genuine non-timeout runner error still sets `scenarios_failed≥1` | W2b L2 |
| T5b | runtime-parity timeout → `ran=False`; does not flip a Coach approve→feedback; a genuine non-zero exit still `ran=True,passed=False` | W2b L3 |
| T6 | a task whose Coach run times out every turn terminates via `max_turns` `success=False`, never `approve` | W1 |

CI: harness-touching tests pin `GUARDKIT_HARNESS=sdk` or `skipif`.

---

## Risks & mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **false-GREEN** from `tests_failed=0` on the absent branch resolving `tests_passed=True` | CRITICAL | #2 short-circuit on `reconciled_absent` BEFORE the `tests_failed` logic; T1c guards it |
| `__post_init__` skipping `None` lets other gates auto-approve (gate-level false-green) | CRITICAL | Append `None` (don't skip); T1d guards "absent → not approve" |
| W1 weakens the genuine-fail path | HIGH | exact `signal_absent`/error-prefix branch; T1b regression-guards |
| non-None-safe reader of `tests_passed` elsewhere | HIGH | grep AC + consumer audit |
| disarming the false-green backstop | CRITICAL | never flip `signal_absent`→False; T3 |
| W2b L2/L3 masking a genuine failure | MEDIUM | only timeout (exception-type / `TimeoutExpired`) reclassifies; genuine fails unchanged; T5a/T5b |
| non-termination (absent every turn) | MEDIUM | bounded by `max_turns`→`success=False`; T6 |

---

## Out of scope (deferred follow-on tasks)

- **W3** — per-test `--timeout` injection: pytest-timeout dependency handling,
  stack-agnostic gate, 4 injection sites, usage-error classifier.
- **W4** — required test gate for TESTING-type tasks: requires
  `_classify_test_failure` substrate-vs-code widening + parallel-amnesty handling.

---

## Context Used (Phase 1.7)

- `.claude/rules/absence-must-survive-every-reconciliation-layer.md` (design principle).
- `.claude/rules/absence-of-failure-is-not-success.md` item 4 / CKPTTESTRED01 (terminal guard).
- `.claude/rules/smoke-gate-is-feedback-not-terminator.md` (feed-back-not-terminate; L3 `ran=False` posture).
- Pre-implementation regression review + Phase 2.5B architectural review (64/100, corrections folded into v2).
