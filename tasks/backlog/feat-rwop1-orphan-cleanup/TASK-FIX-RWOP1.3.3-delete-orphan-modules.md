---
id: TASK-FIX-RWOP1.3.3
title: Delete 12 orphan modules from installer/core/commands/lib/ and clean lib/__init__.py
status: backlog
task_type: refactor
created: 2026-04-22T12:00:00Z
updated: 2026-04-22T12:00:00Z
priority: medium
complexity: 4
tags: [runner-without-producer, task-work, delete, cleanup, rwop1]
parent_task: TASK-FIX-RWOP1.3
parent_review: TASK-REV-RWOP1
feature_id: FEAT-RWOP1
related_tasks:
  - TASK-FIX-RWOP1.3
  - TASK-FIX-RWOP1.3.1
  - TASK-FIX-RWOP1.3.2
depends_on:
  - TASK-FIX-RWOP1.3.1
  - TASK-FIX-RWOP1.3.2
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Delete 12 orphan module subsystems from `installer/core/commands/lib/`

## Problem Statement

Per the [TASK-FIX-RWOP1.3 triage](../../../docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md) (18 DELETE-MODULE verdicts across 12 distinct subsystems), the following modules under `installer/core/commands/lib/` are well-implemented and well-unit-tested but have **zero non-test callers** in `guardkit/` and no sensible runtime caller given how `/task-work` actually runs today (autobuild uses inline protocols; interactive `/task-work` is Claude-driven).

The modules contribute three kinds of confusion:
1. They appear in `lib/__init__.py` re-exports, making them look load-bearing.
2. Their unit-test suites pass, producing false confidence that "the gate runs."
3. Newcomers reasonably conclude from the spec prose that these modules execute during `/task-work`. They do not.

The explicit, long-standing design-drift marker is `lib/__init__.py:41-48`: the `QuickReviewHandler` import is commented out with *"TEMPORARY FIX: Commented out due to missing classes in review_modes package"*. That's been there long enough to be a decision.

## Scope

### In-scope — delete these 12 subsystems

| # | Subsystem | Files | Appendix A rows | Rationale |
|---|---|---|---|---|
| 1 | `flag_validator` | `lib/flag_validator.py` + tests | 1272 | Claude parses flags in prose; module is redundant |
| 2 | `feature_detection` | `lib/feature_detection.py` + tests | 1252, 1505 | Marker-file existence checks; trivially inlineable in prose |
| 3 | `graphiti_context_loader` | `lib/graphiti_context_loader.py` + tests | 1905-1915 | Parallel Python entry to the wired `graphiti-check` bin wrapper |
| 4 | `add_pending_phases` + `examples/demo_phase_gate_integration.py` (tracker sibling surface) | `lib/agent_invocation_tracker.py` (partial — `add_pending_phases` only) + demo + tests for deleted bits | 2074-2086 | **RETAIN `AgentInvocationTracker` class itself** — shipped RWOP1.3.1 uses it as the input shape to `validate_agent_invocations` (see `guardkit/orchestrator/agent_invoker.py:5418` and triage doc [§D-1](../../../docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md#d-1-agentinvocationtracker--resolved-by-shipped-rwop131)). Narrow the public surface to: `__init__`, `invocations` attribute, and whatever `record_invocation` / `mark_complete` calls the wire actually exercises. Delete `add_pending_phases` (only served the unwired PGV) and the demo file. |
| 5 | `library_detector` + `library_context` | `lib/library_detector.py`, `lib/library_context.py` + tests | 2429, 2448 | Context7 MCP does this directly from Claude; Python pre-filter has no driver |
| 6 | `PhaseGateValidator` | `lib/phase_gate_validator.py` + tests | 2669, 2880, 3645, 3715, 3815, 4021 | **API redundancy with `validate_agent_invocations` (shipped in RWOP1.3.1).** PGV's per-phase check `validate_phase_completion("N")` is the union of what `validate_agent_invocations` checks collectively in one post-write call. Wiring both ships the same check twice. See triage doc [§D-2](../../../docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md#d-2-phasegatevalidator-delete--contra-r1-defense) for the contra-R1 reasoning (R1's fix-shape applies to `validate_agent_invocations`, not to PGV — PGV would be a *second* redundant linter). |
| 7 | `task_utils.move_task_to_blocked` | `lib/task_utils.py` (this helper; keep the rest of `task_utils.py` if it has other live helpers) | 2675, 2883, 4270 | Blocking behaviour is expressed in `task_work_results.json` post-RWOP1.3.1 |
| 8 | `QuickReviewHandler` + surrounding `review_modes` | `lib/review_modes.py` (audit which classes inside are actually referenced) | 3118 | Already commented out in `lib/__init__.py:41-48`. Promote the comment to deletion |
| 9 | `plan_persistence` | `lib/plan_persistence.py` + tests | 3401, 3426, 3488 | Aspirational `--design-only` / `--implement-only` workflow. **BUT** see RWOP1.3.2 dependency below. |
| 10 | `phase_execution.execute_implementation_phases` | `lib/phase_execution.py` (delete `execute_implementation_phases` + `StateValidationError`; **retain `execute_phase_5_5_plan_audit`** — that's the wire target for RWOP1.3.2) | 3487 | Aspirational `--implement-only` driver |
| 11 | `ComplexityCalculator` + related | `lib/complexity_calculator.py`, `lib/complexity_factors.py`, `lib/complexity_models.py`, `lib/review_router.py` + tests | 3022 (PA-1) | Coach doesn't consume complexity score; task-manager reasons qualitatively |
| 12 | `git_state_helper.commit_state_files` | `lib/git_state_helper.py` + tests | 4466 | Aspirational Conductor.build worktree commit; no caller |

### Critical dependency sequencing

**Must land AFTER [TASK-FIX-RWOP1.3.2](TASK-FIX-RWOP1.3.2-wire-phase-5-5-plan-audit.md).** (RWOP1.3.1 already shipped as of 2026-04-23 — `AgentInvocationTracker` retention call is now a known quantity; see row 4 above and triage doc [§D-1](../../../docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md#d-1-agentinvocationtracker--resolved-by-shipped-rwop131).)

- **Tracker retention (RESOLVED by shipped RWOP1.3.1):** retain `AgentInvocationTracker` class with narrow public surface. The wire constructs a tracker from parsed SDK stream + Player self-report (see `_extract_invocations_from_result_data` at `guardkit/orchestrator/agent_invoker.py:5341`). Delete `add_pending_phases` and the PGV demo only.
- `plan_persistence.save_plan` (row 9) is the writer for `docs/state/{task_id}/implementation_plan.md`. `plan_audit` (wired in RWOP1.3.2) reads that file. Before deleting `plan_persistence`:
  - EITHER decide the canonical plan-write path lives somewhere else (e.g. `task-manager` agent writes it directly as markdown),
  - OR keep `plan_persistence.save_plan` as the single-purpose "Phase 2.9 writes the approved plan to disk" helper and soften its `lib/__init__.py` re-export to minimal.
  - `load_plan` / `plan_exists` (PA-2) go away regardless.
- `phase_execution.py` is split: `execute_implementation_phases` is deleted; `execute_phase_5_5_plan_audit` is retained and wired by RWOP1.3.2. Split the file if it makes the module boundary cleaner.

### Out-of-scope

- The 2 WIRE items (tasks RWOP1.3.1 + RWOP1.3.2).
- Pseudo-code prose softening (`extract_compilation_errors`, `determine_next_state`, etc.) — that's [TASK-FIX-RWOP1.3.4](TASK-FIX-RWOP1.3.4-soften-pseudo-code-prose.md).
- Re-authoring the `/task-work` spec prose end-to-end. This task only removes prose that names deleted modules; broader restructuring is a separate task.
- Deleting test files is fine if the module is deleted — but if retaining a test for a *live* subsystem that touches a deleted helper, update the test rather than delete it.

## Acceptance Criteria

- [ ] All 12 subsystems listed above are either (a) deleted outright, or (b) reduced to the minimum surface needed by RWOP1.3.1 / RWOP1.3.2 wires, with explicit rationale recorded in the sub-task completion notes for any retained module.
- [ ] `installer/core/commands/lib/__init__.py` re-exports only live surfaces. The `# TEMPORARY FIX: Commented out due to missing classes in review_modes package` block (lines 41-48 + `__all__` lines 167-173) is removed, not just decommented.
- [ ] `grep -rn "from installer.core.commands.lib\." installer/ guardkit/ | grep -v tests/` inventory has zero imports of deleted subsystems.
- [ ] `task-work.md` prose updated to remove references to deleted modules. Replace with either (a) Claude-runtime intent prose, or (b) removed entirely if the phase no longer exists.
- [ ] `pytest tests/` passes after deletions (expected: tests for deleted modules are also deleted; no other tests regress).
- [ ] A completion note in the task file summarises: which subsystems deleted, which partially retained, LOC removed, test files removed.

## Implementation Notes

- Work in dependency order: RWOP1.3.1 → RWOP1.3.2 → RWOP1.3.3. Do NOT start until both wires are green; otherwise the retention calls for `AgentInvocationTracker` and `plan_persistence` can't be made confidently.
- For each deletion, run `grep -rn "<module_name>\|<ClassName>" installer/ guardkit/ .claude/ --include=\"*.py\" --include=\"*.md\" | grep -v tests/` and inspect every hit. Tests-only or spec-only hits are expected; any runtime hit is a signal to audit before deleting.
- The `lib/__init__.py` currently re-exports 12 complexity/modification/pager types (`ReviewMode`, `ForceReviewTrigger`, `ComplexityScore`, `ImplementationPlan`, `ReviewDecision`, `EvaluationContext`, `FactorScore`, `ComplexityFactor`, `FileComplexityFactor`, `PatternFamiliarityFactor`, `RiskLevelFactor`, `DEFAULT_FACTORS`, etc.). Most will go with row #11 (`ComplexityCalculator` subsystem). Audit each re-export individually.
- Retain `ValidationError` (from `phase_gate_validator`) only if RWOP1.3.1 decides to reuse the name; otherwise delete with PGV.

## Related

- Parent triage: [docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md](../../../docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md)
- Parent review: [TASK-REV-RWOP1](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md)
- Dependencies: [TASK-FIX-RWOP1.3.1](TASK-FIX-RWOP1.3.1-wire-agent-invocation-validator.md), [TASK-FIX-RWOP1.3.2](TASK-FIX-RWOP1.3.2-wire-phase-5-5-plan-audit.md) — both must land first
- Sibling: [TASK-FIX-RWOP1.3.4](TASK-FIX-RWOP1.3.4-soften-pseudo-code-prose.md) (can land in parallel — they don't touch the same files)
