---
id: TASK-ARCH-COACHBFULL
title: Restore the investigating Coach (B-full) — tool-using gather phase before toolless grammar synthesis
status: completed
task_type: feature
created: 2026-06-09T00:00:00Z
updated: 2026-06-09T14:00:00Z
completed: 2026-06-09T14:00:00Z
previous_state: in_review
state_transition_reason: "Quality gates passed (compile + 22 new tests + 39 existing Coach tests green). AC-1/2/4/5/6 done; AC-3 deterministic leg done, live GB10 leg pending as documented operator follow-up."
priority: high
complexity: 7
parent_task: TASK-ARCH-COACHSPLIT
related: [TASK-ARCH-COACHSPLIT, TASK-FIX-COACHTESTTO, TASK-HMIG-008R, TASK-OPS-COACH31B]
implementation_mode: task-work
intensity: strict
---

# Task: Restore the investigating Coach (B-full)

## Why this task exists

TASK-ARCH-COACHSPLIT shipped **B-min**: the Coach synthesises its verdict
**toolless**, over the deterministic `CoachEvidenceBundle` only. That made
the verdict reliable on the weak local substrate (gemma4:31b on llama.cpp
hard-rejects grammar+tools), but it **removed the Coach's ability to
investigate** — and that is a real departure from the adversarial-
cooperation pattern GuardKit is modelled on.

The Block AI Research paper *"Adversarial Cooperation in Code Synthesis"*
(Dec 2025; ref impl `g3`, coach model `g31` = `gemma4:31b`) describes the
Coach as an **LLM agent that itself "tests compilation and functionality"**
and emits a rich **per-requirement compliance checklist** (✅/❌ per
requirement + "IMMEDIATE ACTIONS NEEDED"). GuardKit's B-min Coach does the
opposite: it cannot test or probe; it reads a Python-gathered dossier and,
in run-19, **rubber-stamped green gates** — every verdict had
`criteria_verification: []` and a ~200-char rationale (see
`docs/state/TASK-REV-HMIG/run-19-artifacts/README.md` caveat #2).

The fix is the **B-full** realization that TASK-ARCH-COACHSPLIT's own title
names ("tool-using **gather** + toolless grammar verdict") and that B-min
explicitly deferred. It restores the paper's investigating Coach **without
sacrificing** the reliable grammar-constrained verdict.

## The design (Phase A + Phase B)

The harness already exposes both primitives (TASK-ARCH-COACHSPLIT):

- `HarnessAdapter.invoke` — tool-bound agentic turn (the Coach can Read /
  Bash / Grep / Glob to investigate).
- `HarnessAdapter.invoke_synthesis` — toolless, GBNF-grammar-enforced
  verdict.

B-full chains them per Coach turn:

1. **Phase A — evidence gather (tool-using LLM).** Invoke the Coach
   tool-bound over the requirements + ACs + Player report + the
   deterministic bundle, asking it to **investigate and produce findings**
   (compile, run the focused test, read the changed files, check the ACs it
   is unsure about) — output is *findings text*, NOT a fenced verdict.
2. **Phase B — verdict synthesis (toolless + grammar).** Hand Phase A's
   findings (as text, not a tool-call transcript) plus the deterministic
   bundle to the existing `invoke_synthesis` call. Unchanged from B-min
   except the prompt now also carries the gather findings.

**Strict dominance over B-min (the load-bearing property).** Phase A is
tool-bound, so the run-18 tool-parse-500 class can recur *there* — but
Phase A's output is not the verdict and needs no grammar. A failed/garbled
gather is **non-fatal**: degrade to B-min (synthesise over the deterministic
bundle alone). So B-full ADDS investigation when the substrate cooperates
and FALLS BACK to today's behaviour when it doesn't. It can only improve
verdict quality, never regress reliability.

## Where (code surface)

- `guardkit/orchestrator/agent_invoker.py` — add the Phase-A gather
  invocation (tool-bound `_invoke_with_role`, `synthesis=False`, role
  `coach`), thread its findings into `_build_coach_prompt`'s synthesis
  variant. Gate behind an env flag `GUARDKIT_COACH_GATHER`, **default OFF
  (opt-in)** — B-min stays the shipped default until B-full earns promotion
  (see "Flag default + promotion criteria" below).
- `guardkit/orchestrator/autobuild.py` — `_invoke_coach_primary` wiring.
- Honour `.claude/rules/harness-cancellation-contract.md` (Phase A is a
  second in-flight invocation per Coach turn — the cancel monitor must
  cover it) and the per-turn budget (two LLM calls now).

## Acceptance criteria

- [x] **AC-1**: A tool-using Phase-A gather invocation runs before the
  toolless Phase-B synthesis, producing investigation *findings* (text),
  not a verdict. Verified by inspecting the two distinct harness calls per
  Coach turn (one tool-bound, one toolless+grammar).
  → `invoke_coach` Phase-A wiring + `_invoke_coach_gather` /
  `_build_coach_gather_prompt`; test
  `test_coach_gather_bfull.py::test_gather_on_runs_toolbound_then_toolless`.
- [x] **AC-2 (strict dominance)**: a Phase-A failure (tool-parse error,
  timeout, empty findings) **degrades to B-min** (synthesis over the
  deterministic bundle) and never fails the turn. Regression test drives a
  broken gather and asserts a valid verdict still emerges.
  → `_invoke_coach_gather` `except Exception → None`; tests
  `test_gather_failure_degrades_to_bmin`, `test_empty_findings_degrade_to_bmin`.
- [~] **AC-3 (the falsifier)**: construct a case the deterministic bundle
  marks green but where an AC is actually unmet. B-full Coach (investigating)
  **catches it and returns feedback**; B-min Coach (current) approves.
  → **Deterministic leg DONE**:
  `tests/integration/orchestrator/test_coach_bfull_falsifier.py` (same green
  bundle + same honest Coach; only the gather differs; approve↔feedback
  divergence proven). **Live leg PENDING** (operator GB10 run) —
  `docs/state/TASK-ARCH-COACHBFULL/ac3-live-confirmation.md`.
- [x] **AC-4**: the synthesis verdict now carries a populated, structured
  `criteria_verification` (per-AC result + notes), not an empty array.
  → root cause fixed: `invoke_coach` now threads `acceptance_criteria` into
  `_build_coach_prompt` (the run-19 empty-array cause); `autobuild.py`
  `_invoke_coach_primary` normalizes `List[str]→[{id,text}]` with the same
  ID extractor CoachValidator uses. Prompt-driven only (grammar left
  unconstrained per coach-verdict.gbnf notes). Tests
  `TestCriteriaThreading::*`.
- [x] **AC-5**: cancellation + per-turn budget hold with two LLM calls per
  turn (the cancel monitor covers Phase A; the combined budget is bounded).
  → per-call cancel monitor in `_invoke_with_role` covers the gather (free);
  `CancelledError` (BaseException) propagates; budget split (Phase A ≤
  `_COACH_GATHER_BUDGET_FRACTION`·effective, floored; Phase B full). Tests
  `test_cancellation_during_gather_propagates`,
  `test_gather_budget_is_bounded_synthesis_keeps_full`.
- [x] **AC-6**: unit/integration tests for the two-phase flow incl. the
  gather-degrades-to-B-min and zero-evidence paths (absence-of-failure:
  an empty gather + empty bundle must NOT auto-approve).
  → empty/whitespace gather → no findings section (B-min, existing guards
  intact); `test_empty_findings_degrade_to_bmin` + the falsifier.

## Flag default + promotion criteria

`GUARDKIT_COACH_GATHER` ships **default OFF (opt-in)**. Rationale: B-min
(toolless synthesis) is the *validated* default — it passed runs 19 and 20 —
and B-full re-introduces the tool-bound g31 path that D-3 removed for substrate
reliability (run-18 tool-parse-500 class). The "degrade-to-B-min on gather
failure" safety net (AC-2) is a *design* claim until proven on the real
substrate, so the unproven path must not be the default. This is the inverse of
`GUARDKIT_COACH_SYNTHESIS` (which defaulted ON because B-min was the *fix for a
broken* substrate; B-full is an *enhancement over a working* baseline — those
warrant opposite defaults). Error-cost is asymmetric: a wrong opt-in default
costs a few days of opt-in; a wrong opt-out default ships a regression + ~2× g31
latency to every autobuild run by default.

**Lifecycle:**

- **Now (this task):** flag defaults OFF. The COACHBFULL validation run sets
  `GUARDKIT_COACH_GATHER=1` to exercise B-full in isolation; everyone else stays
  on proven B-min.
- **Promotion to default ON** is a **separate, dated one-line commit** (flip the
  default in the gate helper + update the run recipe + this task), made ONLY
  after ALL of the following hold:

  - [ ] **P-1**: ≥2 consecutive green end-to-end autobuild runs with
    `GUARDKIT_COACH_GATHER=1` (e.g. FEAT-AOF), 3/3 first-pass approve, no
    non-recoverable failures.
  - [ ] **P-2**: the gather phase is observed actually running in those runs
    (two distinct g31 calls per Coach turn in the llama-swap log — a tool-bound
    gather *then* a toolless synthesis), i.e. B-full is genuinely exercised, not
    silently always-degrading to B-min.
  - [ ] **P-3**: the degrade-to-B-min fallback (AC-2) is observed firing
    cleanly at least once on a real gather hiccup (or forced via fault
    injection) with no turn failure — the safety net is *empirically* confirmed,
    not just unit-tested.
  - [ ] **P-4**: no verdict-quality or false-reject regression vs the B-min
    baseline (verdicts schema-valid; ideally `criteria_verification` now
    populates per AC-4).
  - [ ] **P-5**: per-turn latency is acceptable as the default — i.e.
    TASK-PERF-COACHSYNTH has landed (resident g31) OR the measured two-call
    latency is confirmed to stay well under `sdk_timeout` on a representative
    feature. (B-full doubles g31 calls/turn; don't make that the default while
    each call still cold-loads.)

  The promotion commit references the runs that satisfy P-1…P-5.

## Notes / sequencing

- Best done **after** TASK-FIX-COACHTESTTO (restores the deterministic
  independent-test leg) so B-full builds on a sound evidence floor.
- The substrate is now settled (TASK-OPS-COACH31B): gemma4:31b is a capable
  Coach; the only reason it ran toolless was verdict-emission reliability,
  which Phase B preserves.
- Surfaced while reviewing run-19 against the Block paper (2026-06-09).
