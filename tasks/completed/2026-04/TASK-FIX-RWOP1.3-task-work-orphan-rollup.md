---
id: TASK-FIX-RWOP1.3
title: /task-work orphan rollup — decide wire-vs-delete for 22 runner-without-producer orphans in task-work.md
status: completed
task_type: review
review_mode: architectural
review_depth: standard
decision_required: true
created: 2026-04-22T00:00:00Z
updated: 2026-04-23T00:00:00Z
completed: 2026-04-23T00:00:00Z
completed_location: tasks/completed/2026-04/
previous_state: in_review
state_transition_reason: "Phase 1 triage complete; Phases 2/3/4 filed as sub-tasks per user scope (A — triage only); follow-up review refinements resolved (D-1/D-2/D-3); parent task discharged"
triage_doc: docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md
subtasks_filed:
  - TASK-FIX-RWOP1.3.1  # shipped 2026-04-23 (WIRE P1)
  - TASK-FIX-RWOP1.3.2  # backlog (WIRE P2, depends on 3.1 ✓)
  - TASK-FIX-RWOP1.3.3  # backlog (DELETE-MODULE, depends on 3.2)
  - TASK-FIX-RWOP1.3.4  # backlog (DELETE-PROSE, parallel with 3.3)
priority: medium
complexity: 6
tags: [runner-without-producer, task-work, cleanup, architecture-decision, rwop1]
parent_review: TASK-REV-RWOP1
feature_id: FEAT-RWOP1
related_to: TASK-REV-RWOP1
related_tasks:
  - TASK-REV-RWOP1
  - TASK-REV-4D190
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: /task-work orphan rollup — decide wire-vs-delete for 22 orphans

## Triage outcome (2026-04-22)

Phase 1 (triage) complete. Per user scope decision (A — triage only), Phases 2/3/4 rolled over as four sub-tasks.

**Triage doc:** [docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md](../../docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md)

**Verdict tally** (25 Appendix A rows → 16 distinct subsystems):

| Verdict | Rows | Subsystems | Sub-task |
|---|---:|---:|---|
| WIRE | 2 | 2 | [TASK-FIX-RWOP1.3.1](../backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.3.1-wire-agent-invocation-validator.md) (P1) + [TASK-FIX-RWOP1.3.2](../backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.3.2-wire-phase-5-5-plan-audit.md) (P2) |
| DELETE-MODULE | 18 | 12 | [TASK-FIX-RWOP1.3.3](../backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.3.3-delete-orphan-modules.md) |
| DELETE-PROSE | 5 | 5 | [TASK-FIX-RWOP1.3.4](../backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.3.4-soften-pseudo-code-prose.md) |

**WIRE P1:** `validate_agent_invocations` — the spec-declared "ONLY checkpoint that prevents false reporting." Fold into `AgentInvoker._write_task_work_results` so the validator runs deterministically post-Player-write and Coach reads the authoritative result.

**WIRE P2:** `execute_phase_5_5_plan_audit` — same hook, same shape. Today Coach consumes `task_work_results["plan_audit"]["violations"]` produced by Player LLM prose; wiring makes the deterministic auditor the producer.

**Delete headline:** `PhaseGateValidator` (6 prose call-sites, 0 runtime) — between-phase validation doesn't map to either the autobuild single-LLM-turn path or the interactive Claude-self-referees path. A wired implementation would be worse than deletion. Paired deletion targets cover 12 module subsystems including the already-commented-out `QuickReviewHandler` `# TEMPORARY FIX:` block in `lib/__init__.py:41-48`.

**Projected post-remediation wiring rate:** 85–95% (target was ≥75%, up from current 34.9%).

**Deferred ACs** (rollover to sub-tasks):
- AC-2 (Phase 2 execution) → RWOP1.3.1 + RWOP1.3.2
- AC-3 (Phase 3 execution) → RWOP1.3.3 (explicitly includes the `# TEMPORARY FIX:` cleanup)
- AC-4 (Phase 4 execution) → RWOP1.3.4
- AC-5 (post-execution wiring recalc) → recorded by RWOP1.3.4 completion notes
- AC-6 (Graphiti update) → pending; triage doc §Cross-links includes the episode content to add

**Cohort impact:** none — parent review already marked this non-blocking because the autobuild cohort path does not invoke `/task-work` as a skill.

### Follow-up review refinements (2026-04-23)

A follow-up review surfaced three points that needed explicit resolution. Recorded in triage doc [§Open decisions](../../docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md#open-decisions-called-out-in-review-2026-04-23) and propagated into the sub-tasks:

- **D-1 `AgentInvocationTracker` retention** — the reviewer flagged this as a hard blocker for 3.1. Resolved by the actual shipped 3.1 implementation (`_extract_invocations_from_result_data`): tracker retained, dual-source reconstruction (explicit self-report → stream-parsed `phases` fallback → `no_data` sentinel). RWOP1.3.3 row 4 updated to retain the tracker class with narrow surface.
- **D-2 PGV DELETE contra-R1 defense** — reviewer asked for explicit "why not WIRE, contra R1" reasoning. Sharpened: PGV's `validate_phase_completion("N")` is API-redundant with shipped `validate_agent_invocations`; wiring both would ship the same check twice. The R1 analog in task-work.md IS `validate_agent_invocations` (now wired), not PGV. RWOP1.3.3 row 6 rationale updated.
- **D-3 Autobuild prompt drift** — reviewer flagged potential drift between task-work.md and `autobuild_execution_protocol.md`. Grep confirmed: one hit (`autobuild_execution_protocol.md:230`, the Phase 4.5 `WHILE ... attempt <= 3` block). RWOP1.3.4 scope extended to soften the autobuild prompt in parallel with task-work.md; added AC for it.

### Sub-task status (2026-04-23)

| Sub-task | Status | Notes |
|---|---|---|
| RWOP1.3.1 (WIRE P1) | ✅ shipped (in_review, 7 integration tests passing) | `guardkit/orchestrator/agent_invoker.py:5341-5437` |
| RWOP1.3.2 (WIRE P2) | backlog | Depends on RWOP1.3.1 (✓ landed); ready to pick up |
| RWOP1.3.3 (DELETE-MODULE) | backlog | Depends on RWOP1.3.2; tracker/PGV retention calls resolved |
| RWOP1.3.4 (DELETE-PROSE) | backlog | Can land in parallel with 3.3; scope now includes autobuild prompt softening |

## Problem Statement

[TASK-REV-RWOP1](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md)
found that
[installer/core/commands/task-work.md](../../../installer/core/commands/task-work.md)
carries **22 orphan imperatives + 6 producer-ambiguous callables**.
Wiring rate is 34.9 % (15/43 wired). The spec reads less like a
command specification than like a specification *of* a command that
was never deterministically implemented — entire Python subsystems
are built, exhaustively unit-tested, and then never called from any
runtime caller.

Critical framing from the parent audit: in the autobuild cohort path
`/task-work` is **not** invoked as a skill. The cohort uses inline
protocols at `guardkit/orchestrator/prompts/autobuild_*_protocol.md`
which re-state the phases as prose for the Player LLM and do NOT
import any `installer/core/commands/lib/` module. So most of these
orphans are **not** cohort-blocking. They are:

- **Sources of false-green completion reports** when a human runs
  `/task-work` interactively (the spec claims phase-gate enforcement
  and agent-invocation validation that do not happen).
- **Maintenance debt** — ~12 modules under `installer/core/commands/lib/`
  that exist only to support tests. Newcomers reading `lib/__init__.py`
  (which re-exports `PhaseGateValidator`, `AgentInvocationTracker`,
  `validate_agent_invocations`, etc.) reasonably conclude these are
  load-bearing runtime components. They are not.
- **Design-drift warning signals** — the `QuickReviewHandler` import
  in `lib/__init__.py:41-48` is literally commented out with the note
  *"TEMPORARY FIX: Commented out due to missing classes in
  review_modes package"*, and the spec still references it at Phase
  2.8. That comment has been there long enough to deserve a decision.

This task is a **review + decision**, not a straight implementation.
Each of the 22 orphans needs a wire-or-delete determination. Some
(e.g. `validate_agent_invocations` — Finding #4 of the parent review,
the spec-declared sole safeguard against false reporting) are
high-value to wire; others (e.g. pseudo-code functions like
`extract_compilation_errors`, `determine_next_state`) are probably
better deleted as "LLM-best-effort is the actual contract — stop
pretending otherwise."

## Scope

### In-Scope

Execute in four ordered sub-phases:

**Phase 1 — Triage (half-day effort):**

Walk each of the 22 orphans listed in the parent review's §Per-file
findings for `task-work.md` (specifically [Appendix A](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md#appendix-a--task-workmd-raw-findings)).
For each orphan, record one of three verdicts in a new file
`docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md`:

- **WIRE** — the module provides value worth enforcing; either the
  Player LLM should be backstopped by a deterministic check, or Coach
  should consume a new field. Priority-rank each WIRE verdict.
- **DELETE-MODULE** — the Python module is well-tested but never
  called; the contract is that Claude interprets the prose. Delete the
  module, remove it from `lib/__init__.py` re-exports, update the
  spec prose to stop referencing it.
- **DELETE-PROSE** — the spec prose references a module/function that
  does not merit a Python implementation at all (e.g. pseudo-code
  `extract_compilation_errors`). Soften the prose from "execute
  `extract_compilation_errors(...)`" to "inspect test output for
  compilation errors" — clarifying this is LLM-best-effort, not a
  deterministic gate.

**Phase 2 — Execute the WIRE verdicts (priority order):**

Starting with the highest-priority WIRE verdicts from Phase 1. The
parent review flags these as the strongest candidates for wiring
(re-audit in Phase 1 to confirm):

1. **`validate_agent_invocations`** (Step 6.5) — the spec itself
   declares this is *"the ONLY checkpoint that prevents false
   reporting."* Wire into `agent_invoker._write_task_work_results`
   before file emission, so any Player that skips `architectural-reviewer`,
   `code-reviewer`, or `test-agent` invocations is caught.
2. **`execute_phase_5_5_plan_audit`** (Phase 5.5) — Coach consumes
   `task_work_results["plan_audit"]["violations"]` but the producer
   is LLM-prose today. Wire the deterministic call into
   `agent_invoker` post-Player-write; Coach's LLM-reported
   `plan_audit` block becomes a sanity cross-check, not the source of
   truth. This is the exact TASK-FIX-3C9D shape applied to plan-audit.
3. **`PhaseGateValidator.validate_phase_completion`** — 6 callsites
   in prose, 0 in runtime. Wire as a post-phase check after each
   Task-tool invocation's stream completes, with violations
   propagated into `task_work_results.json` for Coach to read.

**Phase 3 — Execute the DELETE-MODULE verdicts:**

For each DELETE-MODULE verdict from Phase 1:
- Remove the module file from `installer/core/commands/lib/`.
- Remove its re-export from `installer/core/commands/lib/__init__.py`.
- Remove or soften references to it in `task-work.md`.
- Remove the associated unit tests (or keep them but mark the
  module as deprecated — phase-by-phase call).

**Phase 4 — Execute the DELETE-PROSE verdicts:**

For each DELETE-PROSE verdict:
- Rewrite the spec prose in `task-work.md` to replace pseudo-code
  function calls with LLM-intent language. E.g. replace `Call
  extract_compilation_errors(output)` with `Scan test output for
  compilation errors; consider cases like "syntax error", ".ts:N:M
  error", "cannot find module"`.
- Similarly for `determine_next_state`, `detect_bdd_framework` (inline
  pseudo-code), `extract_coverage`, etc.

### Out-of-Scope

- `/feature-plan` orphans — handled by TASK-FIX-RWOP1.1 and RWOP1.2.
- `/feature-spec` orphans — handled by TASK-FIX-RWOP1.4.
- `--from-spec` block — handled by TASK-FIX-RWOP1.5.
- Rewriting the autobuild inline protocols
  (`autobuild_design_protocol.md`, `autobuild_execution_protocol.md`).
  Those are separate artifacts with their own triage.
- Wiring the 6 producer-ambiguous callables (plan_audit, Phase 4.5
  retry loop, `_execute_via_import` branch, `load_plan`,
  `ComplexityCalculator`). Decide Phase 1 whether each should be
  upgraded to WIRE or downgraded to DELETE-PROSE; the actual wiring
  work rolls into Phases 2-4.

## Acceptance Criteria

- [ ] Phase 1 triage doc at `docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md`
      with per-orphan verdict (WIRE / DELETE-MODULE / DELETE-PROSE),
      rationale (1-2 sentences), and priority rank for WIRE entries.
- [ ] Phase 2 execution: at minimum `validate_agent_invocations` and
      `execute_phase_5_5_plan_audit` WIRED with end-to-end tests
      demonstrating Coach catches a Player that skips them.
- [ ] Phase 3 execution: at minimum the `QuickReviewHandler` reference
      at Phase 2.8 resolved (either wired or removed with the
      `lib/__init__.py` TEMPORARY FIX comment cleared).
- [ ] Phase 4 execution: pseudo-code function references in
      `task-work.md` (`extract_compilation_errors`, `extract_test_failures`,
      `extract_coverage`, `determine_next_state`, `detect_bdd_framework`,
      `extract_files_to_create`, `extract_dependencies`, `extract_duration`)
      either have real module backing OR are rewritten as LLM-intent
      prose.
- [ ] Post-execution wiring rate for `task-work.md` recalculated and
      recorded in the triage doc. Target: ≥ 75 % (up from 34.9 %).
      If below target, record why.
- [ ] Graphiti update: add a second episode confirming the pattern's
      remediation shape at task-work scale (expect a mix of WIRE and
      DELETE decisions, unlike the pure-WIRE R1 remediation).

## Implementation Notes

- This is an explicit **decision-heavy** task. Use `/task-review
  --mode=architectural --depth=standard --with-questions` to run the
  triage if that feels more structured; Phase 1 is primarily analysis.
- Phase 2's wiring work can — and probably should — be split into its
  own sub-tasks once triage is done. Recommend treating this task as
  the triage + priority ranking, and filing Phase 2/3/4 sub-tasks
  from it.
- **Do NOT block TASK-COH-RUN1 on this task.** The cohort bypasses
  task-work.md entirely (via `autobuild_*_protocol.md`). Cohort
  readiness hinges on TASK-FIX-RWOP1.1 + RWOP1.2 only.
- The `validate_agent_invocations` wiring is the highest-leverage
  individual item: the spec already declares it load-bearing. Start
  with that even before Phase 1 triage if you want an immediate win.

## Related

- Parent review:
  [docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md)
  §Per-file findings (task-work.md) + Appendix A
- Canonical fix shape:
  [tasks/completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md](../../completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md)
- Feature orchestrator guide:
  [FEAT-RWOP1-IMPLEMENTATION-GUIDE.md](../FEAT-RWOP1-IMPLEMENTATION-GUIDE.md)
- Cohort-blocking sibling tasks:
  [TASK-FIX-RWOP1.1-wire-feature-plan-step-11-bdd-linking.md](../r2-pipeline-closure-and-forge-cohort/TASK-FIX-RWOP1.1-wire-feature-plan-step-11-bdd-linking.md)
  + [TASK-FIX-RWOP1.2-fold-bdd-oracle-and-smoke-gates-nudges.md](../r2-pipeline-closure-and-forge-cohort/TASK-FIX-RWOP1.2-fold-bdd-oracle-and-smoke-gates-nudges.md)
  — those are cohort-blocking; this is not.
- Design-rule candidate (Graphiti): *"runner without producer
  anti-pattern"* — uuid
  `184731b0-3cb6-4eb2-a310-883421767dbf`
