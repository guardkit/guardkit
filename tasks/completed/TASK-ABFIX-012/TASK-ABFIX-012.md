---
id: TASK-ABFIX-012
title: "Widen substrate-vs-code failure classifier, then make the test gate required for TESTING-type tasks (kills the FMDR-004 false-approval without re-opening a false-red)"
status: completed
task_type: fix
created: 2026-06-24T00:00:00Z
updated: 2026-06-25T00:00:00Z
completed: 2026-06-25T00:00:00Z
completed_location: tasks/completed/TASK-ABFIX-012/
previous_state: in_review
state_transition_reason: "Completed: all quality gates passed (578 passed / 0 failed; adversarial diff review CLOSED)"
priority: medium
complexity: 7
related:
  - TASK-ABFIX-010              # parent; this is its deferred "see also" / W4
  - TASK-ABFIX-005              # parallel-contention conditional approval (the wave_size swing)
  - TASK-AB-PERTASKFG01         # per-task-green / mocked-seam evidence
implementation_mode: task-work
tags: [autobuild, coach, test-gate, substrate-vs-code, false-approval, task-types, deferred-from-abfix-010]
source_docs:
  - ../forge/docs/reviews/FEAT-FMDR-autobuild-false-green-analysis.md   # "Second finding — TASK-FMDR-004 false approval"
---

# Task: required test gate for TESTING-type tasks, gated on a widened substrate-vs-code classifier

> **Provenance.** Deferred "see also" / W4 of TASK-ABFIX-010, from the FEAT-FMDR
> post-mortem's **second finding** (the mirror image of the main bug): TASK-FMDR-004
> — a *testing*-type task whose entire purpose was a passing test — was
> **false-APPROVED on turn 1 while its own deterministic run was 5/9 red**, because
> the test gate was `required=False` and the LLM Coach reasoned the failures were
> "a substrate failure … evidence is ABSENT, not failed." The approval masked two
> real test-code bugs (`get_runbook_by_id` doesn't exist; asserting
> `runbook.status.value == "complete"` when completion is pointer-based).

## Why this task exists (and why it's NOT a one-line flip)

For a TESTING task whose deliverable IS the passing test, `tests_required=False` +
"substrate failure" LLM reasoning lets a red suite self-approve with real code bugs
inside. The obvious fix — flip the TESTING profile to `tests_required=True` — is a
**NO-GO on its own** (ABFIX-010 regression review, R3/HIGH): it re-creates the
false-*red* kill from the opposite gate. A host-substrate gap
(`psql: command not found`, missing docker) currently classifies as `('code','n/a')`
in `_classify_test_failure` — indistinguishable from a real bug — so a blanket flip
would stall legitimately substrate-blocked tasks. Worse, the verdict **flips on
`wave_size`**: single-task → explicit False every turn → stall; parallel wave →
reclassified `parallel_contention` and *conditionally approved* (false-green). The
gate's verdict must not depend on whether it ran alone or in a wave.

So this task **widens the deterministic substrate-vs-code distinguisher first**,
then makes the gate required — substrate failures route to the *same* absence
channel ABFIX-010 built (`None`/feedback), and only high-confidence **code** failures
produce an explicit blocking False.

## Code surface (verified against `main`, 2026-06-24)

| Site | File:line | Role |
|---|---|---|
| TESTING profile | [`task_types.py:236`](../../guardkit/models/task_types.py#L236) `tests_required=False` (TESTING enum `:58`); `zero_test_blocking` default False (`:131`) | the flag the naive fix would flip |
| classifier | [`coach_validator.py:6374`](../../guardkit/orchestrator/quality_gates/coach_validator.py#L6374) `_classify_test_failure`; high-confidence infra patterns [`:1270`](../../guardkit/orchestrator/quality_gates/coach_validator.py#L1270), ambiguous [`:1297`](../../guardkit/orchestrator/quality_gates/coach_validator.py#L1297) | substrate-vs-code decision |
| classifier call | [`coach_validator.py:2098`](../../guardkit/orchestrator/quality_gates/coach_validator.py#L2098) (`requires_infrastructure` hint) | where the failure class is consumed |
| parallel amnesty | [`coach_validator.py:2140-2288`](../../guardkit/orchestrator/quality_gates/coach_validator.py#L2140) (TASK-ABFIX-005 conditional approval; `wave_size > 1`, `_peer_changed_files`) | the wave_size swing to neutralise for TESTING |
| absent channel | ABFIX-010: `signal_absent=True` → `None` through the gate chain | where widened-substrate failures must route |

## Design constraints (mandatory ordering: classifier first, then required-ness)

1. **Widen `_classify_test_failure` with stack-agnostic shell signals.**
   `command not found`, `No such file or directory` (on an exec'd tool),
   `executable not found`, `: not found` → `('infrastructure', high)` →
   `signal_absent=True` (UNKNOWN, routes through ABFIX-010's `None` channel, breaks
   the run / feeds back — never blocks, never passes). Stack-agnostic strings, not
   Python-specific.
2. **Reserve explicit `False` for high-confidence CODE failures only.** A genuine
   assertion failure / wrong-symbol / AttributeError is code → blocking False. An
   ambiguous failure with no diagnostic stays absent (bias to feedback).
3. **Neutralise the `wave_size` swing for TESTING.** For TESTING tasks, disable the
   `parallel_contention` amnesty on the task's *own* assertion failures
   (:2140-2288), so a real code bug is rejected in BOTH single-task and parallel
   waves. (The amnesty stays for genuine cross-task contention on shared files.)
4. **Then** set the TESTING profile's `tests_required=True`. Consider
   `zero_test_blocking` deliberately so a legitimately test-less TESTING subtask
   isn't a silent UNKNOWN-pass (a TESTING task with zero tests is itself suspect).
5. **Do not** weaken the absence-of-failure guarantees: substrate gap → `None`
   (feedback, bounded by max_turns), code bug → False (blocks). Never the reverse.

## Acceptance Criteria

- [x] `_classify_test_failure` maps host-substrate gaps (`command not found`,
      `executable not found`, missing-file-on-exec) to `('infrastructure', high)` →
      `signal_absent=True`, stack-agnostically. *(`_HOST_SUBSTRATE_MISSING_PATTERNS`
      + `_is_host_substrate_gap` rc-126/127; routed to `signal_absent` in all 3
      `run_independent_tests` paths.)*
- [x] A real code-class failure (wrong method name, assertion) for a TESTING task is
      rejected (`must_fix`) in a **single-task** wave. *(`('code','n/a')` →
      `_apply_independent_test_code_failure_guard` blocks on any `code` confidence.)*
- [x] The same code-class failure is rejected in a **parallel** wave (the
      `parallel_contention` amnesty does not cover the task's own assertion failures
      for TESTING). *(Token override → `('code','high')`; plus peer-overlap-aware
      reclassification in `gather_evidence` closes the non-token residual the
      adversarial review found, while keeping the amnesty for genuine shared-file
      contention.)*
- [x] A substrate-blocked TESTING task (e.g. `psql` missing) does NOT
      `unrecoverable_stall` — it surfaces as absent/feedback (and would pass once the
      substrate is present), exactly the false-red ABFIX-010 prevents.
- [x] TESTING profile `tests_required=True` only AFTER the classifier widening lands;
      `zero_test_blocking` set with explicit rationale.
- [x] Reproducer mirrors FMDR-004: a 5/9-red testing task with real test-code bugs is
      NOT approved; a 9/9 (or substrate-only-red) testing task is handled correctly.
- [x] CI: harness-touching tests pin `GUARDKIT_HARNESS=sdk` or `skipif`.

## Implementation summary (2026-06-25)

Key finding that reshaped the naive plan: the **live** Coach path is
`gather_evidence()` → `CoachEvidenceBundle` → deterministic guards in
`agent_invoker` (NOT the legacy `validate()` where the cited line numbers live).
So `tests_required=True` alone was necessary-but-insufficient — a new deterministic
`_apply_independent_test_code_failure_guard` (mirroring `_apply_runtime_parity_guard`)
was required to make the rejection deterministic in the live path.

Files: `coach_validator.py` (classifier widening + substrate→signal_absent + the
`IndependentTestClassification` computation in `gather_evidence`, incl. the
peer-overlap parallel-wave closure), `coach_evidence.py`
(`IndependentTestClassification` dataclass + bundle field), `agent_invoker.py`
(the new guard + call-site), `task_types.py` (TESTING `tests_required`/
`zero_test_blocking` → True). Tests:
`tests/unit/test_abfix012_testing_test_gate.py` (36) +
`tests/orchestrator/test_abfix012_gather_evidence_classification.py`.

Verification: 578 passed / 49 harness-skipped / 0 failed across the related Coach,
guard, ABFIX-010, checkpoint-absence, and parallel-isolation suites; zero
regressions (the only red tests fail identically on clean `main` — they need the
real SDK/langchain harness). Adversarial 3-lens diff review: false-red + scope
SOUND; the one false-green residual it found (parallel non-token failure) was
closed and re-verified CLOSED. Plan: `docs/state/TASK-ABFIX-012/implementation_plan.md`.

## Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| blanket `tests_required=True` flip → false-red stall on substrate gaps | HIGH | classifier widening FIRST (constraint 1); substrate → `None` |
| verdict flips on `wave_size` (parallel amnesty approves a real bug) | HIGH | constraint 3 (disable own-assertion amnesty for TESTING) |
| widened infra patterns over-match a real code failure → false-green | MEDIUM | high-confidence patterns only; ambiguous stays absent/feedback, not pass |
| tension with ABFIX-011 (W3) | LOW | independent; both route their "couldn't run" cases to the same `None` channel |

## Out of scope

- The pytest `--timeout` injection (TASK-ABFIX-011 / W3).
- Non-TESTING task-type gate semantics (FEATURE/REFACTOR/etc. unchanged).
- LLM-prose substrate reasoning — this task makes the distinction *deterministic*;
  it does not try to improve the Coach's natural-language rationale.
