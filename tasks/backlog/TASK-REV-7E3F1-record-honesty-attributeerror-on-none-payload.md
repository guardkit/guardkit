---
id: TASK-REV-7E3F1
title: "Review: _record_honesty() crashes with AttributeError when Coach emits non-blocking advisory turn"
status: review_complete
created: 2026-05-06T00:00:00Z
updated: 2026-05-06T00:00:00Z
priority: high
task_type: review
review_mode: architectural
review_depth: quick
tags: [autobuild, coach, honesty-verification, orchestrator-crash, none-handling, absence-of-failure]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: architectural
  depth: quick (revised — deeper trace)
  revision: 2
  decision: layer_b_plus_layer_c_same_pr
  severity: release_blocking
  regression_introduced_by: b9a45694
  regression_introduced_at: 2026-05-06T16:45:00Z
  findings_count: 12
  recommendations_count: 4
  diagrams: [c4_component, sequence_failing_path, sequence_llm_coach_safe, sequence_pre_regression]
  report_path: .claude/reviews/TASK-REV-7E3F1-review-report.md
  completed_at: 2026-05-06T00:00:00Z
---

# Task: Review: `_record_honesty()` crashes with AttributeError when Coach emits non-blocking advisory turn

## Description

During the FEAT-FFC3 Wave 4 autobuild on 2026-05-06 (TASK-FFC3-006, turn 2),
the orchestrator crashed mid-loop with `AttributeError: 'NoneType' object
has no attribute 'get'` after a Player turn that completed cleanly and
received a non-blocking advisory verdict from Coach. The crash dragged the
task to `error` and the wave to `FAILED`, even though the production code
and 183 tests in the worktree were green.

**Root mechanism (as documented in the incident report):**

1. Turn 2 Player ran 8 SDK turns / 117s — completed correctly.
2. Coach evaluated the turn and emitted a **non-blocking advisory only**
   (no `must_fix` issues, no honesty data emitted because there was nothing
   to verify-against).
3. `_record_honesty(turn_record)` is called unconditionally after Coach
   finishes. The honesty payload it expected on `turn_record` was `None`
   rather than an empty dict.
4. Line 4376 of `guardkit/orchestrator/autobuild.py` does
   `honesty_score = honesty_data.get("honesty_score", 1.0)`, which raises
   `AttributeError` on the `None`.
5. The exception propagates out of `_loop_phase` and the orchestrator
   declares `error`. **The exit is non-retryable in this orchestrator
   path**, so a recoverable advisory becomes a fatal wave failure.

**Why this matters together with the related Bug 1**: TASK-REV-1B452 covers
the false-fail honesty short-circuit (Bug 1). The two bugs compose to
hard-fail an otherwise-recoverable feature: a turn-1 Bug-1 hit forces a
turn-2 retry; the turn-2 advisory then trips Bug 2. **Either bug alone
would have been recoverable; together they hard-failed Wave 4 of FEAT-FFC3
whose code + 183 tests are all green.** Bug 2 must be analyzed and fixed
on its own merit even after Bug 1 is resolved, because non-blocking
advisory verdicts are a legitimate Coach output that any turn can produce.

This task analyzes the failure, scopes the fix, and produces an
implementation breakdown. Implementation is out of scope (a follow-on
`/task-work` task is expected if the review concludes a fix is warranted).

## Context

**Incident report (load-bearing reference):**
[autobuild-FFC3-honesty-path-mismatch-incident.md](/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/docs/history/autobuild-FFC3-honesty-path-mismatch-incident.md)
— specifically the §"Companion Bug — `_record_honesty()` AttributeError on
`None` honesty_data" section starting at line 170.

**Companion evidence (in the specialist-agent repo, not this one):**
- Raw resume log: `/tmp/ffc3-resume5.log` on the originating workstation.
- Traceback (reproduced verbatim in the incident report) names:
  - `guardkit/orchestrator/autobuild.py:1333` (`orchestrate` → `_loop_phase`)
  - `guardkit/orchestrator/autobuild.py:2242` (`_loop_phase` →
    `_record_honesty`)
  - `guardkit/orchestrator/autobuild.py:4376` (`_record_honesty` →
    `honesty_data.get(...)`)

**Affected GuardKit components (in this repo):**
- `guardkit/orchestrator/autobuild.py` — the `_record_honesty` method and
  the call site in `_loop_phase`.
- `guardkit/orchestrator/quality_gates/coach_validator.py` — the producer
  side of the honesty payload; review must confirm under which Coach
  outcome shapes the payload is `None` vs `{}` vs populated.
- Player turn-record shape — wherever `turn_record.honesty_data` (or the
  equivalent attribute) is populated. Review must identify the exact
  attribute name and its declared type.

**Related prior art (must be reviewed for consistency, not duplicated):**
- TASK-REV-1B452 — the sibling review task covering Bug 1 (honesty
  false-fail on path mismatch). The two reviews must produce a coherent
  picture of the Coach → orchestrator honesty data contract; if either
  review changes the shape of the honesty payload, the other must be
  notified.
- TASK-AB-FIX-INVAB1 (commit `b9a45694`) — wired `CoachVerifier` into the
  deterministic Coach path. The honesty payload that fired here originates
  in that verifier. Review must confirm whether non-blocking advisory
  outcomes go through `CoachVerifier` at all, or whether they bypass it
  (which would explain the missing payload).
- `.claude/rules/absence-of-failure-is-not-success.md` — the meta-rule
  for Coach gates that misread zero-cardinality oracle results. **Bug 2
  is not the same shape, but it is adjacent**: the producer side
  legitimately emits no honesty data (zero-cardinality input), and the
  consumer side mishandles it (assumes a dict where there is `None`).
  Review must articulate whether this is a third instance of the
  meta-rule, a different defect class, or both.

## Review Scope

**Focus**: The producer→consumer honesty data contract between
`coach_validator` and `_record_honesty`, with three candidate fixes
ordered from most-targeted to most-defensive:

1. **Layer A (consumer-side defensive default)**: Change line 4376 to
   `honesty_score = (honesty_data or {}).get("honesty_score", 1.0)`.
   Smallest possible diff; restores the documented default (1.0) when
   there is no payload. Risk: masks future producer-side regressions
   that emit `None` when they should emit a real payload.

2. **Layer B (consumer-side guard with early return)**: Restructure
   `_record_honesty` to early-return when `honesty_data` is `None`,
   logging "non-blocking advisory turn; no honesty payload to record"
   at debug level. Equivalent runtime behaviour to Layer A but
   self-documenting and traceable in logs.

3. **Layer C (producer-side contract fix)**: Make `coach_validator`
   always emit an honesty payload — at minimum an empty dict `{}` —
   even on non-blocking advisory turns. This makes the consumer-side
   change unnecessary, but is a wider blast radius (affects every
   call site that reads the payload). Required only if review
   determines the contract should be "always a dict" rather than
   "dict-or-None".

**Trade-off priority**: Robustness (no more orchestrator crashes on
legitimate Coach outputs) over signal (we lose the implicit "no payload
means nothing happened" distinction, but the Coach decision shape
already conveys this — `decision: feedback` with no `must_fix` issues
is the explicit signal).

**Out of scope:**
- Changes to the Coach decision taxonomy itself (when to emit `feedback`
  vs `approve` vs `reject`). The bug is the orchestrator's reaction to a
  legitimate `feedback` shape, not the shape itself.
- Bug 1 (honesty false-fail on path mismatch) — covered by
  TASK-REV-1B452. The two bugs compose to make FEAT-FFC3 unrecoverable,
  but Bug 2 is independently analyzable and fixable.
- Bug 3 (`--resume` cannot finalize a feature whose tasks are all
  completed) — separate review, not yet filed.
- Implementation. This is a `/task-review` task; implementation is a
  follow-on `/task-work` task if the review approves a fix.

## Acceptance Criteria

- [ ] **AC-1**: Failure mechanism confirmed against the running code.
  Read `guardkit/orchestrator/autobuild.py` and confirm:
  (a) line 4376 still does `honesty_data.get(...)` with no `None`
  guard;
  (b) the call site in `_loop_phase` (line ~2242) invokes
  `_record_honesty(turn_record)` unconditionally after Coach.
  Cite both file + line and the actual current code.

- [ ] **AC-2**: Identify the exact attribute on `turn_record` from which
  `honesty_data` is read. Confirm its declared type (e.g. is it typed
  `Optional[dict]`, `dict`, untyped?). If typed, the type system has
  been lying — flag this.

- [ ] **AC-3**: Identify the exact `coach_validator` code path that
  produces a turn record with `honesty_data is None`. Confirm or refute
  the incident report's hypothesis: "when Coach issues only a
  non-blocking advisory (no `must_fix` issues, no honesty data emitted
  because there was nothing to verify-against), the honesty payload is
  `None` rather than an empty dict." Cite file + line.

- [ ] **AC-4**: Decide between Layer A, Layer B, and Layer C. Justify the
  choice. The default should be Layer B (consumer-side guard with early
  return) unless review identifies a reason to prefer producer-side
  normalization (Layer C).

- [ ] **AC-5**: Specify the regression test shape. Construct a Coach
  turn record with `honesty_data=None`, invoke `_record_honesty`,
  assert no exception is thrown and the turn is recorded with the
  documented default honesty score (1.0) — or, if Layer B is chosen,
  assert the recording is skipped and a debug-level log line is
  emitted. Indicate where this test should live (which test module
  under `tests/`).

- [ ] **AC-6**: Articulate the relationship to
  `.claude/rules/absence-of-failure-is-not-success.md`. Decide: is Bug 2
  a third instance of the meta-rule (zero-cardinality input mishandled
  by a downstream consumer), a sibling defect class, or both? If
  meta-rule applies, propose the rule update; do not write the rule
  in this task.

- [ ] **AC-7**: Risk assessment. The Layer A/B fix's biggest risk is
  masking a future producer-side regression that emits `None` when it
  should emit a real payload (e.g. a Coach refactor accidentally
  drops the honesty step). Recommend a complementary safeguard
  (e.g. an assertion in `coach_validator` that the payload is a dict
  before returning, with `None` only allowed on the explicit
  "non-blocking advisory" branch).

- [ ] **AC-8**: Cross-link with TASK-REV-1B452. If Bug 1's review
  recommends changes to the honesty payload shape, confirm those
  changes do not invalidate Bug 2's fix (and vice versa). The two
  fixes must compose.

- [ ] **AC-9**: Produce an implementation task breakdown for the
  approved layer. The fix is small (single-line or single-method),
  but the regression test must exercise the producer→consumer
  contract end-to-end. Each subtask should be independently
  implementable and testable.

## Review Mode

Recommended: `/task-review TASK-REV-7E3F1 --mode=architectural --depth=quick`

The defect is narrow (one line, one type-discipline gap), but it sits
on a contract between two components and needs a producer-side
verification step. Architectural mode is appropriate; quick depth is
sufficient given the clear reproduction and small fix surface.

## Notes

- This is a **review task only**. Do not start implementing. After
  review, the [I]mplement decision will create the follow-on task.
- Manual workaround already applied to FEAT-FFC3: TASK-FFC3-006 status
  flipped to `completed` in `.guardkit/features/FEAT-FFC3.yaml` to
  unblock feature finalisation. The production code is correct and
  committed to the worktree on branch `autobuild/FEAT-FFC3`. The
  reviewer should not need to re-run the autobuild to reproduce — the
  traceback is preserved in the incident report.
- This task is the sibling of TASK-REV-1B452. The two reviews can run
  in parallel; their implementations should also be independent. The
  cross-link AC (AC-8) is the only coupling.
- Bug 3 from the same incident report (`--resume` cannot finalize a
  feature whose tasks are all `completed`) is **not** in scope here.
  If the user wants it reviewed, file a third review task.
