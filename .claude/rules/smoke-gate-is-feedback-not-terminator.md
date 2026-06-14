# Smoke gate is a feedback source, not a hard terminator

> **Source**: Seeded by TASK-AB-COACHRUNPARITY01 (2026-06-14, commit `a11708d0`).
> Pair with the Graphiti design-rule node *"smoke gate is a feedback source, not a
> hard terminator; per-task runtime-parity is an absent-signal oracle"* under
> `guardkit__project_decisions`. Sibling of
> [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md)
> (false-green inverse), [`path-string-mismatch-is-not-dishonesty.md`](path-string-mismatch-is-not-dishonesty.md)
> (false-red inverse), [`harness-cancellation-contract.md`](harness-cancellation-contract.md)
> (dispatch), [`evidence-boundary-narrower-than-write-surface.md`](evidence-boundary-narrower-than-write-surface.md)
> (collection), and [`namespace-hygiene.md`](namespace-hygiene.md)
> (tests-pass / production-fails) — the others are all instances of *a binary
> verdict from a low-fidelity oracle that cannot distinguish "no signal" from
> "positive/negative signal"*. This rule adds the family's first **disposition**
> shape: a *correct* high-fidelity verdict thrown away to terminate the loop
> instead of being fed back into it.

## The rule

A high-fidelity oracle whose failure is used to **terminate** the Player-Coach
adversarial loop — instead of being **fed back** to the Player as the next
turn's feedback and re-entering the loop — is a wasted-signal generator. The
post-wave smoke gate is the highest-fidelity oracle the autobuild loop has: a
*ran-and-failed* smoke result is the most actionable input the loop can
receive. Discarding it with a bare `break` (terminating the feature with no
feedback) squanders exactly the signal the adversarial loop exists to consume.
The verdict was *right*; the defect is what the orchestrator *did* with a
believed failure.

The rule has two arms, in two different families:

- **Arm a (the new shape — disposition).** A *believed, present, correct*
  high-fidelity failure MUST be routed back into the loop as turn-1
  `seed_feedback` and re-entered, **bounded** by a retry budget
  (`GUARDKIT_SMOKE_GATE_MAX_RETRIES`, default 1). It must NOT terminate the
  loop with a bare `break`. The re-run wave result REPLACES the last wave
  result (never appends) so the outcome classifier counts the wave once, and
  the wave is persisted as completed only after the smoke gate is satisfied (the
  C1 mark-gating below).
- **Arm b (an existing-family instance — absence-of-failure / namespace-hygiene).**
  A per-task Coach that approves on a *low*-fidelity oracle (pytest, which puts
  the worktree root on `sys.path` so `from installer.core...` resolves) while
  the deliverable `ModuleNotFoundError`s when run standalone is a textbook
  tests-pass / production-fails false-green. The per-task runtime-parity check
  runs the deliverable's real runtime entry point before approving, and is
  built **absence-of-failure-safe**: an absent signal NEVER blocks and NEVER
  counts as a pass; only a ran-and-failed result overrides approve→feedback.

The rule applies to **any** orchestrator decision that consumes a believed
high-fidelity verdict inside the autobuild loop. One known instance is
documented below; future incidents that match the same shape — a correct
high-fidelity signal routed to *terminate* rather than *feed back* — should be
folded under this rule rather than retried as ad-hoc fixes.

## Why this rule exists

The class-of-defect emerged when the autobuild evidence loop met a deliverable
that passes pytest but does not run standalone:

1. **2026-06-14** — FEAT-9DDE run 8. The per-task Coach approved a deliverable
   on pytest (pytest puts the worktree root on `sys.path`, so the deliverable's
   `from installer.core...` import resolves), but the same import raised
   `ModuleNotFoundError` when the deliverable ran STANDALONE (`python <module>`).
   The post-wave smoke gate — a *high*-fidelity oracle that runs the declared
   runtime entry point — DID catch the failure. But the wave-enumerate loop's
   smoke-gate branch ran a bare `break` (former
   `feature_orchestrator.py:2212`, under the `if not smoke_result.passed:` head
   at former `:2179`), terminating the feature with NO feedback to the Player.
   The Player never saw the failure; from the Player's vantage the loop simply
   ended. Pytest-green ≠ runs-standalone, and the one oracle that knew the
   difference had its verdict thrown away.

Both arms of the fix share a root cause with two different remediations. Arm b
is the *interpretation* defect (a low-fidelity oracle misread as high-fidelity)
— the same shape as the false-green family; its fix is a positive-evidence
precondition (`RuntimeParityResult.ran`). Arm a is the *disposition* defect (a
correctly-read high-fidelity failure mis-routed to terminate) — a genuinely new
shape; its fix is to route the signal back into the loop, bounded by a retry
budget.

The fix (TASK-AB-COACHRUNPARITY01) replaced the bare `break` with a
`_run_post_wave_smoke_gate` helper that feeds the smoke stderr back to the
Player as turn-1 `seed_feedback` and re-enters the wave; added a per-task
`RuntimeParityResult` evidence slice; and (C1, from Phase 2.5 review) moved
`_mark_wave_completed` out of `_execute_wave` to a smoke-gated call-site so a
tasks-pass-but-smoke-fails wave is never persisted as completed.

## Symptom

**Arm a — high-fidelity signal discarded (the new shape):**

- A feature terminates after a wave whose per-task Coach `approve`d every task,
  with NO feedback turn emitted to the Player about the failure.
- The post-wave smoke gate ran and failed (a present, correct, negative
  verdict), but the Player report for that wave shows no `seed_feedback` and no
  subsequent re-entry attempt.
- The feature outcome is a terminal failure with the smoke stderr visible in the
  orchestrator log but absent from any Player turn.
- A resume would skip the wave as "completed" even though its deliverable never
  passed the smoke gate.

**Arm b — pytest-green misread as runs-standalone (existing family):**

- The per-task Coach `approve`s a deliverable whose tests pass under pytest but
  that raises `ModuleNotFoundError` (or another import/runtime error) when run
  standalone via its declared entry point.
- `git`/disk inspection shows the deliverable imports `from installer.core...`
  (or another worktree-root-relative path) that only resolves because pytest
  placed the worktree root on `sys.path`.

## Detection recipe

```bash
# 1. Oracle-failure-then-bare-terminate. Oracle-agnostic (\w+_result.passed),
#    so it also catches a FUTURE non-smoke high-fidelity gate getting the same
#    bad treatment. MUST be NO MATCH on current main; any hit is a regression.
rg --pcre2 -U -n "if not \w+_result\.passed:\s*\n(?:[^\n]*\n){0,40}?\s+break\b" \
   guardkit/orchestrator/feature_orchestrator.py

# 2. The feedback re-entry that replaces the bare break. MUST MATCH; absence is
#    a regression (the smoke failure is no longer fed back to the Player).
rg -n "seed_feedback=smoke_feedback" guardkit/orchestrator/feature_orchestrator.py

# 3. The bounded retry budget — confirm the re-entry is bounded, default 1.
rg -n "GUARDKIT_SMOKE_GATE_MAX_RETRIES" guardkit/orchestrator/feature_orchestrator.py

# 4. C1 mark-gating — _mark_wave_completed must be called ONLY from the
#    smoke-gated wave-loop site (not from inside _execute_wave), so a
#    tasks-pass-but-smoke-fails wave is never persisted as completed.
rg -n "_mark_wave_completed|smoke_blocked|all_succeeded and not" \
   guardkit/orchestrator/feature_orchestrator.py

# 5. Arm-b absence-of-failure safety — the per-task runtime parity check must
#    return an absent signal (never a pass) on a parallel wave / missing
#    command / runner error, and only a ran-and-failed result must override.
rg -n "_gather_runtime_parity|parallel_wave|wave_size > 1" \
   guardkit/orchestrator/quality_gates/coach_validator.py
rg -n "_apply_runtime_parity_guard" guardkit/orchestrator/agent_invoker.py

# 6. Cross-check against existing instances of the family.
rg "smoke-gate-is-feedback|absence-of-failure|path-string-mismatch|harness-cancellation|evidence-boundary-narrower|namespace-hygiene" .claude/rules/
```

## Remediation recipe

1. **Route a believed high-fidelity failure back into the loop, never to a bare
   terminator.** A ran-and-failed smoke gate composes Player-facing feedback
   (`_build_smoke_feedback`, `feature_orchestrator.py:2243`) and re-enters the
   wave with that feedback as turn-1 `seed_feedback`
   (`feature_orchestrator.py:2401`). The bare `break` is reserved for the
   exhausted-budget case only.
2. **Bound the re-entry.** The retry budget is
   `GUARDKIT_SMOKE_GATE_MAX_RETRIES` (`feature_orchestrator.py:698`, default 1).
   An unbounded re-entry would let a permanently-broken deliverable burn the
   whole task budget — feed back, but bounded.
3. **Replace, do not append, the re-run wave result.** The re-run wave result
   REPLACES `wave_results[-1]` (`feature_orchestrator.py:2223`) so the outcome
   classifier counts the wave once. The terminator fires only after the budget
   is spent (`if outcome.terminate: break`, `feature_orchestrator.py:2224`).
4. **Gate wave-completion persistence on the smoke gate (C1).**
   `_mark_wave_completed` is called ONLY from the smoke-gated wave-loop site
   (`feature_orchestrator.py:2238-2239`, guarded by
   `wave_result.all_succeeded and not smoke_blocked`), NOT from inside
   `_execute_wave`. A tasks-pass-but-smoke-fails wave is never persisted as
   completed, so a resume cannot skip an unverified wave.
5. **For the per-task low-fidelity oracle (arm b), pair the approval with a
   positive-evidence precondition.** Run the deliverable's real runtime entry
   point before approving (`_gather_runtime_parity`,
   `coach_validator.py:2896`), producing a `RuntimeParityResult` evidence slice
   (`coach_evidence.py:76`). Thread `expected_exit` (`smoke_expected_exit`) so
   the per-task check agrees with the configured gate.
6. **Keep absent runtime-parity signals absent (absence-of-failure safety).**
   A `RuntimeParityResult` with `ran=False` — no smoke command, a parallel wave
   (`wave_size > 1` guard, `coach_validator.py:2916`), or a runner error — NEVER
   blocks and NEVER counts as a pass. `_apply_runtime_parity_guard`
   (`agent_invoker.py:5533`) deterministically overrides approve→feedback ONLY
   on a ran-and-failed result.

## Grep-able signature (for next agent)

```bash
# Active-hazard fingerprint (arm a): oracle-failure-then-bare-terminate.
# MUST be NO MATCH on current main; a hit means a high-fidelity gate is being
# used to terminate the loop instead of feeding back. (Pre-fix a11708d0^: 1
# match; current: 0.)
rg --pcre2 -U -n "if not \w+_result\.passed:\s*\n(?:[^\n]*\n){0,40}?\s+break\b" \
   guardkit/orchestrator/feature_orchestrator.py

# Feedback-re-entry fingerprint (arm a): MUST MATCH (absence = regression).
rg -n "seed_feedback=smoke_feedback" guardkit/orchestrator/feature_orchestrator.py   # -> 2401

# Bounded-retry fingerprint (arm a).
rg -n "GUARDKIT_SMOKE_GATE_MAX_RETRIES" guardkit/orchestrator/feature_orchestrator.py # -> 698

# Landed-helper fingerprints (arm a).
rg -n "_run_post_wave_smoke_gate" guardkit/orchestrator/feature_orchestrator.py       # -> 196, 2219, 2280
rg -n "SmokeGatePhaseOutcome"     guardkit/orchestrator/feature_orchestrator.py       # -> 193 (dataclass)
rg -n "_build_smoke_feedback"     guardkit/orchestrator/feature_orchestrator.py       # -> 2243 (def), 2389 (call)

# C1 mark-gating fingerprint (arm a): mark-completed only at the smoke-gated site.
rg -n "all_succeeded and not smoke_blocked" guardkit/orchestrator/feature_orchestrator.py  # -> 2238

# Runtime-parity fingerprints (arm b): absent-signal-safe per-task oracle.
rg -n "_gather_runtime_parity"     guardkit/orchestrator/quality_gates/coach_validator.py  # -> 2873 (call), 2896 (def)
rg -n "_apply_runtime_parity_guard" guardkit/orchestrator/agent_invoker.py                 # -> 2303 (call), 5533 (def)
rg -n "class RuntimeParityResult"  guardkit/orchestrator/quality_gates/coach_evidence.py   # -> 76 (def; also referenced in quality_gates/coach_validator.py)

# Sibling-rule lookup (this rule + the whole family)
rg "smoke-gate-is-feedback|absence-of-failure|path-string-mismatch|harness-cancellation|evidence-boundary-narrower|namespace-hygiene" .claude/rules/
```

## Meta-frame

This rule's **arm b** is a plain instance of the family below. Its **arm a** is
the family's first **disposition** member. The four prior siblings are all
instances of *a binary verdict from a low-fidelity oracle that cannot
distinguish "no signal" from "positive/negative signal"*. Where they differ is
**which part of the oracle pipeline produces the spurious "no signal"**:

| Rule | Failure locus | Direction | Spurious "no signal" comes from… |
|---|---|---|---|
| `absence-of-failure-is-not-success` | interpretation | false-green | a zero counter read as a pass when zero attempts ran |
| `path-string-mismatch-is-not-dishonesty` | interpretation | false-red | a path miss read as a lie when the orchestrator moved the file |
| `harness-cancellation-contract` | dispatch | divergence | a cancel that no-ops on a substrate it wasn't written for |
| `evidence-boundary-narrower-than-write-surface` | collection | both | work done outside the oracle's spatial aperture |
| **`smoke-gate-is-feedback-not-terminator`** | **disposition** | **wasted-signal** | **a *correct* high-fidelity failure used to terminate the loop instead of being fed back into it** |

**Unlike the four siblings, this row's signal is NOT spurious — the oracle was
right.** The "no signal" the loop ends up acting on is the **absence of a
feedback turn**: the Player never sees the failure, so from the Player's vantage
the loop simply ended. The fix restores the missing signal by routing the
failure back as `seed_feedback`. The four prior rules pair the binary verdict
with a *precondition* before trusting it (count of attempts > 0; identity-based
resolution; substrate-agnostic dispatch; a spatial aperture covering the write
surface). This rule pairs a *believed* verdict with a *disposition contract*:
route a high-fidelity failure back into the adversarial loop (bounded), rather
than out of it. Arm b alone is the precondition pattern again
(`RuntimeParityResult.ran` > the count-of-attempts analogue); arm a is the new
disposition contract.

## Prior art

- **Sibling rule (false-green inverse direction) + arm-b home**:
  [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md)
  — arm b (the per-task runtime-parity check) is a direct instance of THIS
  rule: a low-fidelity oracle (pytest) misread as high-fidelity, made
  absence-of-failure-safe (`ran=False` never blocks, never a pass).
- **Sibling rule (false-red inverse direction)**:
  [`path-string-mismatch-is-not-dishonesty.md`](path-string-mismatch-is-not-dishonesty.md)
  — the other interpretation-locus member; where it keeps a correct path miss
  from becoming a false-red, arm a keeps a correct runtime failure from becoming
  a *wasted* signal.
- **Sibling rule (dispatch locus)**:
  [`harness-cancellation-contract.md`](harness-cancellation-contract.md)
  — guards the *dispatch* of a cancellation across substrates; arm a guards the
  *disposition* of a believed high-fidelity failure (feed it back via
  `seed_feedback`, bounded by `GUARDKIT_SMOKE_GATE_MAX_RETRIES`, rather than
  terminating the loop with a bare `break`).
- **Sibling rule (collection locus, canonical meta-frame table)**:
  [`evidence-boundary-narrower-than-write-surface.md`](evidence-boundary-narrower-than-write-surface.md)
  — this file appends the fifth (disposition) row to that table.
- **Sibling rule (tests-pass / production-fails)**:
  [`namespace-hygiene.md`](namespace-hygiene.md) — arm b's `sys.path`-shadowing
  mechanism (pytest puts the worktree root on `sys.path` so
  `from installer.core...` resolves, but the standalone run does not) is exactly
  this rule's "production tests pass, production runs fail" lineage.
- **Pair fact in Graphiti** (`guardkit__project_decisions`): node *"smoke gate
  is a feedback source, not a hard terminator; per-task runtime-parity is an
  absent-signal oracle"*.
- **Originating defect**: FEAT-9DDE run 8 — per-task Coach approved a
  pytest-green deliverable that `ModuleNotFoundError`d standalone; the smoke
  gate caught it and the bare `break` discarded the signal.
- **Originating fix**: TASK-AB-COACHRUNPARITY01 (commit `a11708d0`,
  2026-06-14). Arm a: `SmokeGatePhaseOutcome`
  (`feature_orchestrator.py:193`), `_build_smoke_feedback` (`:2243`),
  `_run_post_wave_smoke_gate` (`:2280`), `GUARDKIT_SMOKE_GATE_MAX_RETRIES`
  (`:698`), `seed_feedback=smoke_feedback` (`:2401`), C1 mark-gating
  (`:2238-2239`). Arm b: `RuntimeParityResult` (`coach_evidence.py:76`),
  `_gather_runtime_parity` (`coach_validator.py:2896`),
  `_apply_runtime_parity_guard` (`agent_invoker.py:5533`).
- **Reproducer tests**:
  `tests/unit/orchestrator/test_smoke_feedback_retry.py` (arm a:
  `seed_feedback` reaches turn-1 `previous_feedback`; feedback composition),
  `tests/unit/orchestrator/test_runtime_parity.py` (arm b: ran-and-failed
  override; parallel-wave / runner-error / no-command absent-signal no-ops),
  `tests/integration/autobuild/test_smoke_gate_blocks_wave.py` (failure →
  feed back → pass; retries-exhausted terminates; smoke-pass marks wave
  completed / smoke-fail does not),
  `tests/integration/autobuild/test_smoke_gate_noop.py` (no-smoke-gates path
  unchanged), `tests/unit/orchestrator/test_autobuild_smoke_placement.py`
  (smoke hook lives in wave phase only, not per-task).
- **Plan / trail**:
  `docs/state/TASK-AB-COACHRUNPARITY01/implementation_plan.md`.

## When this rule triggers

- Before introducing or modifying any orchestrator branch that consumes a
  believed high-fidelity verdict (a smoke gate, a post-wave runtime check, any
  future "run the deliverable for real" oracle) inside the autobuild loop — the
  failure path MUST feed back, not terminate.
- Before adding a new per-task Coach evidence oracle whose substrate is
  lower-fidelity than the eventual runtime (pytest vs standalone run) — it must
  be absence-of-failure-safe (`ran=False` never blocks, never passes).
- Before changing the smoke-gate retry budget, the
  `wave_results[-1] = wave_result` replace-not-append contract, or the C1
  `_mark_wave_completed` smoke-gating call-site.
- During Phase 2.5 architectural review for any task touching
  `feature_orchestrator.py` wave-loop / smoke-gate handling,
  `coach_validator.py` runtime parity, `agent_invoker.py` parity guard, or
  `coach_evidence.py` `RuntimeParityResult`.
- During any diagnostic session investigating a "the smoke gate caught it but
  the feature terminated with no Player feedback" report, or a "per-task Coach
  approved but the deliverable doesn't run standalone" report.

## What the rule does NOT cover

- **Genuinely terminal conditions.** Some failures legitimately terminate the
  loop (budget exhaustion, an unrecoverable infrastructure error). The rule
  requires feeding back a *believed high-fidelity deliverable failure* that the
  Player can plausibly fix; it does not require infinite re-entry. The retry
  budget bounds the feed-back; an exhausted budget terminates correctly.
- **The retry budget value itself.** `GUARDKIT_SMOKE_GATE_MAX_RETRIES` (default
  1) is operator policy. The rule governs the *shape* (feed back, bounded,
  replace-not-append), not the numeric budget.
- **Multi-task-wave per-task runtime parity.** The arm-b runtime-parity check
  is guarded to `wave_size == 1` to avoid multi-task-wave false-fails; a
  parallel wave yields an absent signal, not a pass. Finer-grained per-task
  attribution inside a parallel wave is out of scope.
- **Low-fidelity-oracle *interpretation* defects.** When the oracle itself
  cannot distinguish "no signal" from a verdict (a zero count, a path miss, a
  no-op cancel), that is the four prior siblings' territory, not this rule's
  disposition shape. Arm b is folded here only because it is the companion fix
  that shipped with arm a; its mechanism belongs to
  `absence-of-failure-is-not-success.md` / `namespace-hygiene.md`.
- **Coach-side hallucination of a passing smoke verdict.** A Coach inventing a
  green smoke result it never ran is a different meta-defect (hallucinated
  evidence), not a mis-disposed correct one.
