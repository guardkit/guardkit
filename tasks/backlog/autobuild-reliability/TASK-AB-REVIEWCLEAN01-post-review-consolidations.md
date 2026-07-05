---
id: TASK-AB-REVIEWCLEAN01
title: Post-review consolidations deferred from the 2026-07-04 code review
status: backlog
created: 2026-07-04T18:30:00Z
priority: low
tags: [autobuild, cleanup, consolidation, coach-guards, pytest-parsing, tech-debt]
complexity: 4
source: 2026-07-04 post-implementation code review (TASK-AB-* batch)
---

# Task: Post-review consolidations deferred from the 2026-07-04 code review

> **Implemented 2026-07-05 (session following the 2026-07-04 handoff), items
> 1–4 + 6; item 5 closed wontfix (see below). This file is the tracking
> record.**
>
> - **Item 1** — one pytest-summary parser: `guardkit/lib/pytest_summary.py`
>   (`parse_pytest_summary` → `PytestSummary`). `specialist_invocations
>   ._parse_pytest_counts` and `coach_validator._parse_tests_skipped` both
>   delegate to it; the streaming `agent_invoker` parser is DELIBERATELY left
>   separate (documented in-code) — it is a decoration-anchored max-wins
>   accumulator whose behaviour folding-in would change (AC-007). Tests:
>   `tests/unit/lib/test_pytest_summary.py`.
> - **Item 2** — one shared `AgentInvoker._persist_coach_decision(decision,
>   coach_output_path, *, tag, kind)`; all 10 hand-rolled write blocks route
>   through it (one `write_text` in the file). The
>   `deterministic-verdict-override-must-persist-to-disk` rule's grep
>   fingerprints updated to match.
> - **Item 3** — `IndependentTestResult.from_run` / `.absent` / `.skipped`
>   classmethod factories own `tests_skipped` (derived from output in
>   `from_run`, so it cannot be silently omitted) and `resolved_interpreter`;
>   all 16 construction sites migrated.
> - **Item 4** — `_extract_agent_invocations_violation` and
>   `_extract_environment_stall_signal` now consume the shared
>   `_coach_report_issues` walker.
> - **Item 6** — `stale_test_attribution.smoke_gate_header` +
>   `runtime_parity_rationale`; the smoke-gate and per-task-parity surfaces
>   consume one composer (a wording change is a one-file edit).
> - **Item 5 (single-persist-per-turn) — CLOSED wontfix.** Rationale below in
>   the item-5 section: it would WIDEN the crash window where disk says
>   `approve` while memory says `feedback` (the exact Layer-4 resurrection
>   `deterministic-verdict-override-must-persist-to-disk` guards). Item 2's
>   shared helper already delivers the "impossible to forget on the next
>   guard" safety without moving the write; the every-guard-persists
>   convention is intentionally kept.

## Description

The 2026-07-04 post-implementation code review of the TASK-AB-* batch
(STALEATTRIB01 / RESUMEVENV01 / SKIPVIS01 / STALLTAX01 / ZEROTESTLOUD01 /
NULLEVID01 and siblings) fixed its correctness findings in-session and
deliberately deferred six *consolidation* cleanups: none is a defect today,
but each is duplication that drifts — and at the Coach-guard seam, drift
re-opens closed defects. This task is the single tracking record for those
six deferred consolidations.

1. **Unify the THREE pytest-summary parsers.**
   `specialist_invocations._parse_pytest_counts`
   (`guardkit/orchestrator/specialist_invocations.py:941`),
   `coach_validator._parse_tests_skipped`
   (`guardkit/orchestrator/quality_gates/coach_validator.py:1098`), and the
   `PYTEST_SUMMARY_PATTERN` handling in `agent_invoker`
   (`guardkit/orchestrator/agent_invoker.py:892`, consumed at `:1123`) each
   re-implement "parse the pytest short summary line". Extract ONE helper
   under `guardkit/lib/` (sibling of `guardkit/lib/pytest_argv.py`) that
   returns the full passed/failed/errors/skipped tuple; the three call
   sites become consumers.

2. **A shared `_override_and_persist` helper (or ordered guard registry)
   for the Coach-guard seam.** `agent_invoker` now carries ~7 hand-rolled
   flip/annotate-then-`coach_output_path.write_text` blocks
   (`agent_invoker.py:5753, 5863, 6041, 6071, 6188, 6352, 6470, 6549` —
   `_reconcile_absent_independent_test_signal`,
   `_apply_spec_gap_absent_guard`, `_apply_runtime_parity_guard`,
   `_apply_independent_test_code_failure_guard`,
   `_reconcile_coach_narrative_with_records`, and peers). Each duplicates
   the same contract: mutate the loaded `decision` dict, then re-persist
   `coach_turn_N.json` fail-open (`try/except OSError` + WARNING). One
   helper (or an ordered registry the invoke path iterates) makes the
   contract impossible to forget on the next guard.

3. **An `IndependentTestResult` factory owning `tests_skipped` /
   `resolved_interpreter` population.** The ~10+ construction sites
   (concentrated in `coach_validator.py` — 16 `IndependentTestResult(`
   occurrences) each hand-populate the SKIPVIS01 `tests_skipped` and
   RESUMEVENV01 `resolved_interpreter` fields; a site that forgets one
   silently drops advisory/forensic evidence. A small factory (or
   classmethod constructors per outcome shape: passed / failed / absent /
   timeout) owns the population once.

4. **Rewrite the two pre-existing coach-turn walkers over
   `_coach_report_issues`.** `_extract_environment_stall_signal`
   (`guardkit/orchestrator/autobuild.py:452`) and
   `_extract_agent_invocations_violation` (`autobuild.py:406`) predate the
   shared defensive walk `_coach_report_issues` (`autobuild.py:506`,
   TASK-AB-ZEROTESTLOUD01) and still inline their own report/issues shape
   checks. Rewrite both as consumers, like
   `_test_verification_issues` / `_extract_verifier_infrastructure_signal`
   already are.

5. **Single-persist-per-turn for `coach_turn_N.json`. — CLOSED wontfix
   (2026-07-05).** The proposal was to have guards mutate memory and persist
   ONCE after the last guard. Rejected for long-term correctness: moving the
   write to chain-end WIDENS the window in which the on-disk file says
   `approve` while the in-memory verdict is already `feedback` — precisely
   the divergence Layer-4 (`feature_orchestrator._check_late_approval`)
   resurrects into an `approved_late` false-green
   (`deterministic-verdict-override-must-persist-to-disk`). The current
   "every guard re-persists immediately" convention keeps disk == memory at
   every step, which is the invariant that matters. Item 2's shared
   `_persist_coach_decision` helper already delivers the stated goal of item
   5 ("impossible to forget the persist on the next guard") WITHOUT moving
   the write — one seam, N calls, the contract centralised. N writes per turn
   is cheap (small JSON, already on the guard path) and is the safe posture.
   Original proposal preserved above for the record; not implemented.

6. **A shared framing composer for the parity/smoke feedback wording.**
   `agent_invoker._apply_runtime_parity_guard` (`agent_invoker.py:6197`,
   the `test_output` / conditional-rationale framing around `:6276-6316`)
   and `feature_orchestrator._build_smoke_feedback`
   (`guardkit/orchestrator/feature_orchestrator.py:2276-2315`) compose
   near-identical failing-test framing around the same
   `stale_test_attribution` helpers, and their wording is pinned by two
   parallel test suites (`test_runtime_parity.py`,
   `test_smoke_feedback_retry.py`) that must be updated in lockstep today.
   Move the composition into `stale_test_attribution` (it already owns the
   note wording) so the two surfaces consume one composer.

## Acceptance Criteria

- [ ] AC-001: One pytest-summary parser under `guardkit/lib/`; the three
      call sites consume it; behaviour pinned by the existing suites
      (skip-count visibility, specialist counts, agent_invoker summary
      matching) unchanged.
- [ ] AC-002: Every deterministic Coach-guard override routes through one
      shared override-and-persist mechanism; no guard carries its own
      `write_text` block; the COACHFG01 on-disk-flip reproducer
      (`test_override_rewrites_coach_turn_file_on_disk`) still passes.
- [ ] AC-003: `IndependentTestResult` construction routes through the
      factory; `tests_skipped` and `resolved_interpreter` cannot be
      silently omitted (absent stays `None`, never a default that reads as
      evidence).
- [ ] AC-004: Both pre-existing walkers are `_coach_report_issues`
      consumers; their stall/violation extraction behaviour is unchanged.
- [ ] AC-005: `coach_turn_N.json` is persisted at most once per turn after
      the guard chain, fail-open; Layer-4 late-approval reads the
      post-guard verdict exactly as it does today.
- [ ] AC-006: Parity and smoke feedback framing come from one composer in
      `stale_test_attribution`; a wording change is a one-file edit.
- [ ] AC-007: No behaviour change anywhere — this is consolidation only;
      the full suites named in each touched task's test list stay green.

## Implementation Notes

- Sequence 2 → 5 together (the guard registry naturally yields
  single-persist); 1, 3, 4, 6 are independent and can land separately.
- Item 5 changes WHEN the disk write happens (after the last guard rather
  than inside each). Verify no consumer reads `coach_turn_N.json` between
  guards before landing it.
- Keep `find_authoring_task`'s public single-file shape when touching item
  6 — it is implemented over the shared one-scan map builder
  (`_build_authorship_map`) from the 2026-07-04 review FIX 2.

## Regression constraints

From `.claude/rules/` — load-bearing, verify each before merging:

- **`deterministic-verdict-override-must-persist-to-disk.md`** (items 2, 5):
  the whole point of the shared helper is that duplication drift re-opens
  the COACHFG01 defect — an in-memory flip whose disk half is forgotten
  lets Layer-4 (`_check_late_approval`) resurrect the stale `approve`.
  Single-persist must land AFTER the last guard and BEFORE any consumer
  reads the file; the write stays fail-open (WARNING, never un-reject).
- **`absence-must-survive-every-reconciliation-layer.md`** and
  **`absence-of-failure-is-not-success.md`** (items 1, 3): the unified
  parser and the factory are new reconciliation/serialization layers —
  absent counts (`tests_skipped`, `tests_run`, `resolved_interpreter`)
  must stay `None`/absent through them, never coerced to 0/False/pass.
- **`bdd-pending-is-not-failed.md`** (item 1): if the unified parser grows
  BDD-adjacent counters, pending stays a third state — never folded into
  failed.
- **`smoke-gate-is-feedback-not-terminator.md`** and
  **`path-string-mismatch-is-not-dishonesty.md`** (item 6): the shared
  composer changes wording plumbing only — the feed-back-not-terminate
  disposition and the fail-open attribution join (no note on unmatched /
  ambiguous / current-task files) are untouched.
- **`player-prompt-reinforce-coach-constraint-in-three-locations.md`**
  (item 6): if the composed wording is ever reinforced in Player prompts,
  keep the reinforcement locations in sync with the single composer.
- **`structural-defence-beats-prompt-instruction.md`** (item 2): the guard
  registry is orchestrator-side structure; do not weaken any guard into a
  prompt-level instruction while consolidating.
