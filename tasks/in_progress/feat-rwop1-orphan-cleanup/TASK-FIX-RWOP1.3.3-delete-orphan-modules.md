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

## Completion Notes (2026-04-23)

Landed in four batches; each batch committed separately with pytest sanity
between them.

### Modules deleted outright (31 files + 1 subpackage)

**Batch 1 — pure orphans (6):**
- `flag_validator.py`, `feature_detection.py` (commands/lib copy only;
  `installer/core/lib/feature_detection.py` retained),
  `graphiti_context_loader.py`, `library_detector.py`, `library_context.py`,
  `phase_gate_validator.py`

**Batch 2 — complexity + review_modes cluster (21):**
- Complexity: `complexity_calculator.py`, `complexity_factors.py`,
  `complexity_models.py`, `review_router.py`, `agent_utils.py`
- Review modes: `review_modes.py` (file) + `review_modes/` subpackage
  (5 files), `review_mode_executor.py`
- Task tooling: `task_review_orchestrator.py`, `task_breakdown.py`,
  `breakdown_strategies.py`, `task_split_advisor.py`, `split_models.py`,
  `visualization.py`
- Plan-modification cluster: `version_manager.py`, `change_tracker.py`,
  `modification_session.py`, `modification_applier.py`,
  `modification_persistence.py`, `pager_display.py`
- Caught-in-chain: `qa_manager.py` (imported only by `review_modes.py`)

**Batch 3 — plan-persistence cluster (5):**
- `plan_persistence.py`, `plan_modifier.py`, `refinement_handler.py`,
  `checkpoint_display.py`, `plan_markdown_renderer.py`

### Modules retained with narrowed surface

- **`AgentInvocationTracker`** (`agent_invocation_tracker.py`): class
  retained for the RWOP1.3.1 `validate_agent_invocations` input shape;
  the sibling `add_pending_phases()` function was removed (its only
  consumer was the unwired PhaseGateValidator).
- **`plan_audit.py`** (RWOP1.3.2 wire): `_load_plan` now inlines the
  workspace-root lookup instead of deferring to the deleted
  `plan_persistence.load_plan`.
- **`phase_execution.py`**: rewritten from ~1385 → ~260 lines. Retains
  `execute_phase_5_5_plan_audit` + interactive helpers plus a local
  inlined `_plan_exists` helper. Deleted: `execute_phases`,
  `execute_design_phases`, `execute_implementation_phases`,
  `execute_standard_phases`, `execute_phase_1_6_clarification` + helpers,
  `get_clarification_for_prompt`, `execute_phase_3`,
  `analyze_task_context`, and the lib-local `StateValidationError` (the
  live `StateValidationError` in `guardkit.orchestrator.exceptions` is
  unrelated).
- **`plan_markdown_parser.py`**: kept for `plan_audit._load_plan`. The
  write-side counterpart `plan_markdown_renderer.py` was deleted with
  the plan-persistence cluster.
- **`task_utils.py`**: `move_task_to_blocked()` function removed per
  task spec row #7; the rest of the module stays (other lib modules use
  `update_task_frontmatter`, `read_task_file`).
- **`lib/__init__.py`**: reduced from 204 → 75 lines. Public surface is
  now `error_messages`, `greenfield_qa_session`, `agent_discovery`,
  `agent_invocation_tracker`, `agent_invocation_validator` only. The
  long-standing `# TEMPORARY FIX: Commented out` block for review_modes
  imports was promoted to deletion (AC).

### Test files removed (35) + surgical edits (2)

Orphan-only unit/integration/e2e tests for the deleted modules, plus
caught-in-chain fixture modules (`tests/e2e/` top-level files,
`tests/stacks/` whole directory, `tests/fixtures/data_fixtures.py` /
`factory_fixtures.py` / `mock_fixtures.py`,
`tests/unit/commands/review_modes/` whole directory, ~20 individual test
files across `tests/unit/` and `tests/integration/`).

Surgical test edits:
- `tests/unit/test_graphiti_structured_logging.py`: removed
  `TestGraphitiContextLoaderLogging` class only; four other classes
  (feature_plan_context, autobuild_context_loader, interactive_capture,
  consistent_log_format) still cover live Graphiti code.
- `tests/integration/conftest.py`: removed imports of the deleted
  fixture modules.

### Spec prose updates

- **`installer/core/commands/task-work.md`**: all pseudo-Python
  references to deleted modules either removed or converted to
  Claude-runtime intent prose. Phase 2.1 (library-context gathering,
  ~110 lines) collapsed to a pointer at the existing Context7 MCP
  section. Phase 2.9 (design-first workflow routing, ~185 lines of
  pseudo-code) replaced with one paragraph explaining the modules were
  deleted and what to do instead. Six per-phase
  `PhaseGateValidator` / `move_task_to_blocked` blocks replaced with a
  one-line "deferred to Step 6.5" note (validation now happens
  post-write via `validate_agent_invocations`, RWOP1.3.1).
- **`installer/core/agents/task-manager-ext.md`**: the
  `plan_persistence` / `flag_validator` / `execute_phases` import block
  in "Integration Points" replaced with a note pointing at
  `execute_phase_5_5_plan_audit` as the one live lib entry.

### Out-of-scope orphan chains (flagged for future cleanup)

Found during inventory but left alone to keep this task focused — none
touched by Batch 1-4:

- `template_merger.py` + `template_versioning.py`: zero non-lib callers.
  Independent of the deleted cluster (different `TemplateVersionManager`
  class).
- `micro_task_workflow.py` + `micro_task_detector.py`: only
  doc-referenced (`task-manager-ext.md`). The `--micro` flag is
  Claude-prose-driven.
- `api_call_preview.py`: no non-test callers.
- `spec_drift_detector.py`: only referenced in `code-reviewer-ext.md`
  doc. Still has `from feature_detection import supports_requirements`
  — the import is latent (module is itself orphan, nothing triggers it
  at runtime).
- Older agent docs (e.g. `complexity-evaluator.md`, other sections of
  `task-manager-ext.md`) still describe workflows involving deleted
  modules. The agents themselves are effectively dead (no runtime
  invocation path). TASK-FIX-RWOP1.3.4 covers broader pseudo-code
  prose softening.

### LOC / test impact

- Commits: 4 (Batches 1 / 2 / 3 / 4 prose) all on main
- LOC removed: ~44,000 net deletions across four commits (~25,800 in
  Batch 2 alone, dominated by the complexity + review_modes cluster)
- Test files removed: 35; test files surgically edited: 2
- Full pytest suite: 322 pre-existing failures, 0 new regressions
  across all four batches. Target-region tests (agent invocations
  gate, plan audit, phase 5.5, agent invocation validator) all pass.

### Verification

- AC grep: `grep -rn "from installer.core.commands.lib\." installer/
  guardkit/ | grep -v tests/` filtered for deleted-subsystem names
  returns empty ✓
- Package import sanity:
  `from installer.core.commands.lib import AgentInvocationTracker,
  validate_agent_invocations, ValidationError` ✓
  `from installer.core.commands.lib.phase_execution import
  execute_phase_5_5_plan_audit` ✓
