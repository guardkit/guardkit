# TASK-FIX-RWOP1.3 — `task-work.md` orphan triage (Phase 1 of 4)

**Task:** [TASK-FIX-RWOP1.3](../../tasks/in_progress/TASK-FIX-RWOP1.3-task-work-orphan-rollup.md)
**Parent review:** [TASK-REV-RWOP1](TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md) §Per-file findings (task-work.md) + [Appendix A](TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md#appendix-a--task-workmd-raw-findings)
**Canonical fix shape:** [TASK-FIX-3C9D](../../tasks/completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md) — fold producer into the script the spec already shells out to
**Date:** 2026-04-22
**Scope:** Phase 1 (triage + sub-task filing) per the user's "A" slice. Phases 2/3/4 (execution) roll out as sub-tasks [TASK-FIX-RWOP1.3.1](../../tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.3.1-wire-agent-invocation-validator.md), [TASK-FIX-RWOP1.3.2](../../tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.3.2-wire-phase-5-5-plan-audit.md), [TASK-FIX-RWOP1.3.3](../../tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.3.3-delete-orphan-modules.md), [TASK-FIX-RWOP1.3.4](../../tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.3.4-soften-pseudo-code-prose.md).

---

## Triage decision rule

For each orphan imperative in `installer/core/commands/task-work.md` (25 rows in [Appendix A](TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md#appendix-a--task-workmd-raw-findings); 22 orphans + 6 producer-ambiguous per the parent tally), one of three verdicts:

- **WIRE** — the module provides enough value to pay the wiring cost. Execute in priority order via sub-task RWOP1.3.1 / RWOP1.3.2.
- **DELETE-MODULE** — the module is well-tested but has no runtime caller and no sensible runtime caller given how `/task-work` actually runs today. Delete the module, clean `lib/__init__.py`, soften the spec prose. Executed via RWOP1.3.3.
- **DELETE-PROSE** — the spec prose is pseudo-code that was never implemented as a module at all. Rewrite the prose as LLM-intent language (the *actual* contract). Executed via RWOP1.3.4.

**Framing constraint.** The parent review's core observation is decisive here: the autobuild cohort path **does not invoke `/task-work` as a skill**. `TaskWorkInterface._build_autobuild_design_prompt` and `AgentInvoker._invoke_task_work_implement` run the Player through inline protocols at `guardkit/orchestrator/prompts/autobuild_*_protocol.md`, which import **zero** modules from `installer/core/commands/lib/`. Consequently, orphans in `task-work.md` are **not cohort-contaminating** — they are sources of false-green completion reports when a human runs `/task-work` interactively, and maintenance debt that makes `lib/__init__.py`'s exports look load-bearing when they are not.

This shifts the wiring-value calculus. A wire only pays off if it produces a deterministic signal that a downstream **deterministic consumer** (Coach) actually reads. Gates that exist only to guard an interactive-Claude runtime that is already under a human's supervision are much lower-leverage than gates that backstop the Player LLM's self-report in autobuild.

**Applied to the two highest-leverage candidates:**

| Orphan | Deterministic consumer? | Fix shape | Verdict |
|---|---|---|---|
| `validate_agent_invocations` (Step 6.5) | **Yes** — Coach reads `task_work_results.json` (`guardkit/orchestrator/quality_gates/coach_validator.py`). Adding an `agent_invocations_violations` field that Coach gates on is a direct TASK-FIX-3C9D-shaped wire. | Call `validate_agent_invocations(tracker_from_report, workflow_mode)` inside `AgentInvoker._write_task_work_results` (`guardkit/orchestrator/agent_invoker.py:3885-3912` + the autobuild update surface at `:2753-2789`). Write violations into the results file; Coach already has the consumer surface. | **WIRE P1** |
| `execute_phase_5_5_plan_audit` (Phase 5.5) | **Yes** — Coach already reads `task_work_results["plan_audit"]["violations"]` at `coach_validator.py:1118-1130`. Today the producer is the Player LLM's self-report; the Player can trivially claim "violations=0". | Same hook as above. After Player writes `task_work_results.json`, run `execute_phase_5_5_plan_audit` deterministically against the saved plan + actual artefacts. Override the Player's `plan_audit` block with the deterministic result. | **WIRE P2** |
| `PhaseGateValidator.validate_phase_completion` (6 call-sites: Phases 2, 2.5B, 3-BDD, 3, 4, 5) | **No** — the design intent is between-phase validation *during* a `/task-work` run. In the autobuild path there is no between-phase runtime because the Player executes as a single LLM turn. In the interactive path Claude is both the phase executor and the purported validator, which is self-refereeing and useless. | N/A — no sensible wiring target exists. | **DELETE-MODULE** |

The "wire everything" position is tempting — the modules are already written and unit-tested — but every wire lands a module in the cohort-adjacent runtime that must then be carried forward. For PGV specifically, a wired implementation would be worse than deletion because it would legitimise a gate the code cannot actually enforce.

---

## Open decisions called out in review (2026-04-23)

A follow-up Claude review surfaced three refinements that needed explicit resolution before the sub-tasks could be picked up. Resolutions recorded here for auditability; corresponding scope text is updated in the relevant sub-tasks.

### D-1. `AgentInvocationTracker` — resolved by shipped RWOP1.3.1

**Question:** `validate_agent_invocations(tracker, workflow_mode)` reads `tracker.invocations`. If RWOP1.3.1 wires the validator but RWOP1.3.3 deletes the tracker, what does the validator check against?

**Status:** RWOP1.3.1 shipped (7 integration tests passing, in_review). This section updated to be descriptive of the shipped code rather than prescriptive.

**Shipped approach** (`guardkit/orchestrator/agent_invoker.py:5341-5372` — `_extract_invocations_from_result_data`):

1. **Preferred source:** the Player's explicit `agent_invocations` list from `task_work_results.json` (if present and well-formed).
2. **Fallback source:** the SDK stream parser's `phases` dict (`_phases`, populated during turn streaming from `phase_{N}` markers in the tool-use/text output). `_PARSER_PHASE_TO_VALIDATOR_PHASE` reverse-maps `phase_{N}` → validator phase IDs.
3. **No-data sentinel:** if both sources are empty, the validation block is recorded with `status: "no_data"` rather than passed/violation — avoids false positives on synthetic test fixtures or pipeline-failure-before-phase-ran cases.

**Authoritative vs self-report trade-off:** the shipped order is self-report-first. A sophisticated Player that fabricates an `agent_invocations` list matching the expected phases would still pass the check. The stream-parsed `phases` dict is the *more* authoritative source (it's derived from actual tool-use events during the SDK turn) but is used only as fallback.

**Forward-note (optional hardening, not required for this sweep):** a future tightening could invert the order — use stream-parsed `phases` as primary and treat Player's explicit list as an annotated cross-check only. This would elevate the spec's *"ONLY checkpoint that prevents false reporting"* claim from "catches most misreports" to "catches fabrications." Not in scope for RWOP1.3; file separately if desired.

**Flow-on to RWOP1.3.3:** `AgentInvocationTracker` is retained (used by the shipped wire to pass data into `validate_agent_invocations`). RWOP1.3.3 should narrow the tracker's public surface to the minimum the wire needs: `__init__`, the `invocations` list attribute, and whatever `record_invocation` / `mark_complete` helpers the wire actually uses. Delete `add_pending_phases` and the `examples/demo_phase_gate_integration.py` demo (both only serviced the unwired PGV).

### D-2. `PhaseGateValidator` DELETE — contra-R1 defense

**Question:** R1 (TASK-FIX-3C9D) wired a Python producer with no caller rather than deleting it. The original triage defended PGV DELETE with "gate cannot enforce anything in autobuild (single LLM turn) or interactive (Claude self-referees)" — but that's structurally the same argument that would have led to DELETE for the AC linter. Is DELETE here consistent with R1?

**Resolution:** DELETE is consistent — but the defense needs to be sharpened. The right framing is **API redundancy**, not "the gate cannot enforce anything."

Concretely:
- PGV's public API is `validate_phase_completion(phase_id: str, description: str)` — a per-phase check that the phase's agent was invoked.
- `validate_agent_invocations(tracker, workflow_mode)` is a collective check that **all** expected phases for the workflow mode were invoked. Its `identify_missing_phases` helper returns the exact same per-phase information PGV's call-sites are trying to produce.
- The 6 PGV call-sites in task-work.md prose all attempt to assert "phase N's agent was invoked" — which is the **union** of what `validate_agent_invocations` checks in a single post-write call. There is no per-phase check PGV does that `validate_agent_invocations` doesn't.
- Wiring both would ship the same check twice. Choice is which API survives; the collective check is strictly more useful because it's workflow-mode-aware and runs at the single natural hook point (post-Player-write) instead of 6 mid-phase hook points that don't exist in either autobuild or interactive runtime.

**Contra-R1 consistency check:** The R1 AC-linter is not analogous to PGV. The R1 analog in task-work.md is `validate_agent_invocations` (which IS being wired, via RWOP1.3.1). PGV is analogous to a hypothetical *second* AC-linter that re-checks what the first one already checks. R1's "wire the orphan producer" rule applies to `validate_agent_invocations`; it does not apply to PGV.

**Coach-consumable phase-specific gates the reviewer hinted at** (Phase 4.5 fix-loop-attempts-exceeded, Phase 5.5 plan-audit-violations):
- Phase 5.5 plan-audit-violations → already being wired by [TASK-FIX-RWOP1.3.2](../../tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.3.2-wire-phase-5-5-plan-audit.md).
- Phase 4.5 fix-loop-attempts-exceeded → **not a PGV retention candidate** — PGV doesn't currently track attempt counts. This would be a *new* feature, not a wire of existing PGV code. If desired, file as a separate follow-up task: "wire a max-attempts counter into `task_work_results.json` so Coach can reject runs that spun out of 3 attempts without resolution." Recommended as low-priority because Coach's independent pytest run already catches the end-state failure; the attempt-count gate would only add finer-grained signal.

**Conclusion:** PGV DELETE stands. The defense in the per-orphan table has been sharpened (see rows 8, 10, 17-19, 21 below).

### D-3. Autobuild protocol drift — RWOP1.3.4 scope extension

**Grep result** (`guardkit/orchestrator/prompts/autobuild_design_protocol.md` + `autobuild_execution_protocol.md` against all pseudo-code keywords):

```
autobuild_execution_protocol.md:230: WHILE (compilation_errors > 0 OR test_failures > 0) AND attempt <= 3:
```

One hit. The Phase 4.5 retry-loop pseudo-code is duplicated in the autobuild execution protocol. If RWOP1.3.4 softens task-work.md's copy but not the autobuild prompt's copy, the two prose artefacts drift in opposite directions: task-work.md reads as "LLM-best-effort guidance" while the autobuild prompt continues to instruct the Player in pseudo-code.

**Resolution:** Extend [TASK-FIX-RWOP1.3.4](../../tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.3.4-soften-pseudo-code-prose.md) scope to include `autobuild_execution_protocol.md:230` (and surrounding prose up to ~line 253 per the audit). Match the rewrite voice to task-work.md's softened Phase 4.5 prose; cross-link the two files in the sub-task completion notes so future readers see they are synced.

No other pseudo-code keywords (`extract_compilation_errors`, `determine_next_state`, `detect_bdd_framework`, `extract_test_failures`, `extract_coverage`) matched the autobuild prompts, so the drift surface is contained to Phase 4.5.

---

## Per-orphan triage (25 rows from Appendix A, 16 subsystems)

Appendix A line numbers reference `installer/core/commands/task-work.md`. Row count matches Appendix A; "Subsystem" column groups rows that share a single remediation decision.

| # | Line | Imperative / Subsystem | Verdict | Sub-task | Rationale |
|---|---|---|---|---|---|
| 1 | 1272 | `flag_validator.validate_flags` | **DELETE-MODULE** | RWOP1.3.3 | Flag parsing is a Claude-runtime concern (read user input, branch on flags). Claude is already doing this in prose. A Python module for flag validation is redundant: it can only run if Claude invokes it, and Claude has no reason to invoke it when it can parse the flags itself. Tests-only callers. |
| 2 | 1252 | `feature_detection.supports_bdd` | **DELETE-MODULE** | RWOP1.3.3 | The "is RequireKit installed" check is one-line: `(Path.home() / ".agentecflow/require-kit.marker.json").exists()`. Soften the spec prose to say exactly that; drop the module. Same argument applies to `supports_requirements` + `supports_epics`. |
| 3 | 1505 | `feature_detection.supports_requirements/supports_epics/supports_bdd` | **DELETE-MODULE** | RWOP1.3.3 | Duplicate of #2 — same module, second invocation site. Remove both imports from prose. |
| 4 | 1905-1915 | `graphiti_context_loader.is_graphiti_enabled, load_task_context_sync` | **DELETE-MODULE** | RWOP1.3.3 | The wired CLI path uses the `graphiti-check` bin wrapper ([Appendix A line 1809](TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md#step-1--phase-15-17--context-load), verdict: wired). `graphiti_context_loader` is a parallel Python entry point that nobody uses. The MCP path is Claude-native and requires no Python at all. Delete the duplicate Python path. |
| 5 | 2074-2086 | `AgentInvocationTracker` + `add_pending_phases` | **DELETE-MODULE** | RWOP1.3.3 | Tracker exists to feed `PhaseGateValidator`. PGV is being deleted (see row 8-21 below). Tracker goes with it. |
| 6 | 2429 | `library_detector.detect_library_mentions` | **DELETE-MODULE** | RWOP1.3.3 | Phase 2.1 library-context gathering is already performed end-to-end by Claude invoking the Context7 MCP directly. The Python detector is a pre-filter for a Python driver that does not exist. |
| 7 | 2448 | `library_context.gather_library_context` | **DELETE-MODULE** | RWOP1.3.3 | Same as #6. Context7 MCP calls are Claude-native; the Python wrapper has no caller. |
| 8 | 2669 | `PhaseGateValidator.validate_phase_completion("2", ...)` | **DELETE-MODULE** | RWOP1.3.3 | API redundancy with `validate_agent_invocations` (row 23, WIRE P1): PGV's per-phase check `validate_phase_completion("N")` is the **union** of what `validate_agent_invocations` checks collectively in one post-write call, via its `identify_missing_phases` helper. Wiring both ships the same check twice. See [D-2 in Open decisions](#d-2-phasegatevalidator-delete--contra-r1-defense) for the full contra-R1 reasoning. Delete the module and remove this + 5 sibling prose blocks (rows 10, 17, 18, 19, 21). |
| 9 | 2675 | `task_utils.move_task_to_blocked` | **DELETE-MODULE** | RWOP1.3.3 | Helper for PGV (and for `validate_agent_invocations` pre-wire). Moving the task file to `tasks/blocked/` mid-autobuild is confusing because the file lives in the player worktree, not the main tree; blocking behaviour is better expressed as a violation entry in `task_work_results.json` (which Coach already gates on). Not needed after PGV is gone. |
| 10 | 2880 | `PhaseGateValidator.validate_phase_completion("2.5B", ...)` | **DELETE-MODULE** | RWOP1.3.3 | Recurrence of row 8. |
| 11 | 2883 | `task_utils.move_task_to_blocked` | **DELETE-MODULE** | RWOP1.3.3 | Recurrence of row 9. |
| 12 | 3118 | `QuickReviewHandler` | **DELETE-MODULE** | RWOP1.3.3 | Already commented out in `installer/core/commands/lib/__init__.py:41-48` with *"TEMPORARY FIX: Commented out due to missing classes in review_modes package"*. The comment has been there long enough to be promoted to a permanent deletion. Clear the `# TEMPORARY FIX:` block; soften the Phase 2.8 prose reference. Phase 2.8's actual runtime is Claude displaying a checkpoint card and reading user input — no Python driver needed. |
| 13 | 3401 | `plan_persistence.save_plan` (import) | **DELETE-MODULE** | RWOP1.3.3 | `--design-only` workflow is aspirational: save an implementation plan in Phase 2, hand it to a separate `--implement-only` run later. No non-test caller exists. If the workflow is a product feature, file it as a separate wiring task, not a task-work.md cleanup. For now, delete. |
| 14 | 3426 | `plan_path = save_plan(...)` (call) | **DELETE-MODULE** | RWOP1.3.3 | Same decision as #13 (same subsystem). |
| 15 | 3487 | `phase_execution.execute_implementation_phases, StateValidationError` | **DELETE-MODULE** | RWOP1.3.3 | Counterpart to `save_plan`: the `--implement-only` entry point. Same rationale. `task_work_interface.py:709` imports `load_plan, plan_exists` inside `_execute_via_import`, which is a dead branch (`_execute_via_sdk` is always preferred). |
| 16 | 1616 | `detect_bdd_framework(project_path)` | **DELETE-PROSE** | RWOP1.3.4 | Pseudo-code function defined inside the spec itself (lines 1616-1661). No module backs it. Rewrite Phase 1.5 BDD-framework-detection prose as LLM-intent: "Detect the BDD framework by reading the project's package/requirements file (`pyproject.toml` + `pytest-bdd` → pytest-bdd; `.csproj` + `SpecFlow` → specflow; `package.json` + `@cucumber/cucumber` → cucumber-js)." |
| 17 | 3645 | `PhaseGateValidator.validate_phase_completion("3-BDD", ...)` | **DELETE-MODULE** | RWOP1.3.3 | Recurrence of row 8. |
| 18 | 3715 | `PhaseGateValidator.validate_phase_completion("3", ...)` | **DELETE-MODULE** | RWOP1.3.3 | Recurrence of row 8. |
| 19 | 3815 | `PhaseGateValidator.validate_phase_completion("4", ...)` | **DELETE-MODULE** | RWOP1.3.3 | Recurrence of row 8. |
| 20 | 3842-3848 | `extract_compilation_errors`, `extract_test_failures`, `extract_coverage` | **DELETE-PROSE** | RWOP1.3.4 | Pseudo-code functions spec-internal; no module. Rewrite the Phase 4.5 retry-loop prose from `compilation_errors = extract_compilation_errors(phase_4_output)` to "scan the testing agent's output for build errors (patterns: 'error:', 'error TS', 'FAILED', exit code non-zero) and test failures (patterns: 'FAILED', 'assertion failed', test framework summary lines). The Player LLM does this qualitatively; there is no deterministic driver." |
| 21 | 4021 | `PhaseGateValidator.validate_phase_completion("5", ...)` | **DELETE-MODULE** | RWOP1.3.3 | Recurrence of row 8. |
| 22 | 4195-4229 | `determine_next_state(phase_45_results, coverage_results)` | **DELETE-PROSE** | RWOP1.3.4 | Pseudo-code Python in the spec body. No module defines it. The routing logic ("BLOCKED if compilation errors, IN_REVIEW if all gates pass") is what Coach actually does by reading `task_work_results.json`. Rewrite the Step 6 prose as "consult `task_work_results.json` and the coach_validator decision; route to BLOCKED / IN_REVIEW / IN_PROGRESS accordingly." |
| 23 | 4266-4274 | `validate_agent_invocations` | **WIRE P1** | **RWOP1.3.1** | The spec itself (line 4346) declares this *"the ONLY checkpoint that prevents false reporting."* The consumer surface already exists in `coach_validator`. The producer needs to move from Player-LLM-prose to `AgentInvoker._write_task_work_results`. Highest-leverage wire in this sweep; start here even before the deletions. |
| 24 | 4270 | `task_utils.move_task_to_blocked` | **DELETE-MODULE** | RWOP1.3.3 | Recurrence of row 9. Task-blocking is expressed in the results file once P1 wire lands. |
| 25 | 4466 | `commit_state_files` (Step 8 Conductor.build worktree commit) | **DELETE-MODULE** | RWOP1.3.3 | The Conductor.build worktree-commit rationale at task-work.md:4489 is aspirational. If real, belongs in a separate Conductor integration task. Zero callers today. |

### Producer-ambiguous (6)

| # | Line | Imperative | Verdict | Rationale |
|---|---|---|---|---|
| PA-1 | 3022 | `ComplexityCalculator` via task-manager subagent | **DELETE-MODULE** (folded into RWOP1.3.3) | Coach doesn't consume complexity score. The agent-side usage (task-manager reasoning about effort) is LLM-qualitative; a Python calculator adds ceremony without a deterministic consumer. Delete the module; leave the prose as "the task-manager subagent assigns a complexity level." |
| PA-2 | 3488 | `plan_persistence.load_plan, plan_exists` | **DELETE-MODULE** (paired with #13/#15) | `task_work_interface.py:709` imports these inside the dead `_execute_via_import` branch. Delete with the rest of plan-persistence. |
| PA-3 | 3850 | Phase 4.5 retry loop (`WHILE ... attempt <= max_attempts`) | **DELETE-PROSE** (folded into RWOP1.3.4) | The loop is prose instruction to the LLM; `autobuild_execution_protocol.md:215-253` restates the same instructions. No deterministic driver. Backstopped by Coach's independent `pytest` run. Rewrite the loop prose as "the Player is expected to fix, re-run, and re-report; Coach enforces the pass bar independently." |
| PA-4 | 4142-4145 | `execute_phase_5_5_plan_audit` | **WIRE P2** | **RWOP1.3.2** — see [Triage decision rule](#triage-decision-rule) above. |
| PA-5 | — | `extract_files_to_create`, `extract_dependencies`, `extract_duration` (from Phase 2.9 plan-data builder) | **DELETE-PROSE** (folded into RWOP1.3.4) | Pseudo-code helpers referenced in the `--design-only` prose. Once `save_plan` is deleted, their references go with it. |
| PA-6 | — | Step 10 `ImplementOrchestrator` "use for orchestration logic" dead-docstring (feature-plan.md, not task-work.md) | out-of-scope | This is a feature-plan.md producer-ambiguous, not task-work.md. Separate review surface. |

### Verdict tally

| Verdict | Count (of 25 rows) | Distinct subsystems | Sub-task |
|---|---:|---:|---|
| WIRE | 2 (rows 23, PA-4) | 2 (`validate_agent_invocations`, `execute_phase_5_5_plan_audit`) | RWOP1.3.1 + RWOP1.3.2 |
| DELETE-MODULE | 18 (rows 1-15, 17-19, 21, 24, 25, PA-1, PA-2) | 12 subsystems¹ | RWOP1.3.3 |
| DELETE-PROSE | 5 (rows 16, 20, 22, PA-3, PA-5) | 5 prose blocks | RWOP1.3.4 |
| out-of-scope | 0 rows (1 PA noted for traceability) | — | — |

¹ `flag_validator`, `feature_detection`, `graphiti_context_loader`, `AgentInvocationTracker`, `library_detector`, `library_context`, `PhaseGateValidator`, `task_utils.move_task_to_blocked`, `QuickReviewHandler`, `plan_persistence` (save/load/exists), `phase_execution` (`execute_implementation_phases`), `commit_state_files`, `ComplexityCalculator`. That's 13 distinct module files; counted as 12 because `plan_persistence` functions count as one subsystem.

---

## Projected wiring rate after remediation

Appendix A's current count: 43 walked · 15 wired · 22 orphan · 6 producer-ambiguous · **34.9 %** wiring rate.

Applying the triage:

- **WIRE** (+2): `validate_agent_invocations` + `execute_phase_5_5_plan_audit` become wired. Wired count: 15 → 17.
- **DELETE-MODULE** (−18 rows, −13 subsystems): orphan rows disappear from the spec because the spec references are softened/removed. Walked count drops by 18 rows. Orphan count drops by 18.
- **DELETE-PROSE** (−5 rows): orphan rows become Claude-runtime intent language, which per the audit methodology is **excluded** from the imperative count (as `/feature-spec`'s ~70% Claude-runtime prose was excluded). Walked count drops by 5 rows. Orphan count drops by 5.

Projected post-remediation: **20 walked · 17 wired · 0 orphan · 3 producer-ambiguous · 85.0 %** wiring rate.

Producer-ambiguous residuals:
- PA-3 (Phase 4.5 retry loop): still LLM-driven, still backstopped by Coach-independent pytest. Acceptable PA — Coach is the deterministic producer.
- Remaining 2 PA slots reserved for the new deterministic producers (wired P1 + P2) — they themselves will be Coach-consumed, not Coach-producing, so they could be re-classified as wired. If re-classified: **20 walked · 19 wired · 0 orphan · 1 producer-ambiguous · 95.0 %**.

**Target from RWOP1.3 acceptance criteria: ≥ 75 %. Projected: 85-95 %.** Well above target.

---

## Acceptance-criterion coverage

| AC | Status | Evidence |
|----|--------|----------|
| Phase 1 triage doc at `docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md` with per-orphan verdict, rationale, and priority rank for WIRE entries | ✅ | This document. 25 Appendix A rows triaged into 2 WIRE / 18 DELETE-MODULE / 5 DELETE-PROSE. WIRE priority: P1 `validate_agent_invocations`, P2 `execute_phase_5_5_plan_audit`. |
| Phase 2 execution: `validate_agent_invocations` and `execute_phase_5_5_plan_audit` WIRED with end-to-end tests | rolled over | [TASK-FIX-RWOP1.3.1](../../tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.3.1-wire-agent-invocation-validator.md), [TASK-FIX-RWOP1.3.2](../../tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.3.2-wire-phase-5-5-plan-audit.md) |
| Phase 3 execution: `QuickReviewHandler` reference resolved, `lib/__init__.py` TEMPORARY FIX comment cleared | rolled over | [TASK-FIX-RWOP1.3.3](../../tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.3.3-delete-orphan-modules.md) (explicitly includes the TEMPORARY FIX cleanup) |
| Phase 4 execution: pseudo-code function references either backed or rewritten | rolled over | [TASK-FIX-RWOP1.3.4](../../tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.3.4-soften-pseudo-code-prose.md) |
| Post-execution wiring rate recalculated, target ≥ 75 % | projected 85-95 % (above); final recalc lands in RWOP1.3.4's completion report | §[Projected wiring rate after remediation](#projected-wiring-rate-after-remediation) |
| Graphiti update with the remediation shape | pending | To be added as a `guardkit__project_decisions` episode referencing this triage doc + the sub-tasks. Recommended content: "task-work.md scale applies the runner-without-producer remediation as a MIX of WIRE (2 items, narrow + high-leverage) and DELETE (13 subsystems, broad + low-leverage) — in contrast to R1's pure-WIRE fix. Design rule update: a module that is well-tested AND has no sensible runtime consumer is evidence of design drift, not evidence of being load-bearing." |

---

## Cross-links

- Parent review: [TASK-REV-RWOP1](TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md) §Per-file findings (task-work.md) + Appendix A
- Sibling RWOP1 cohort-blockers: [TASK-FIX-RWOP1.1](../../tasks/completed/2026-04/TASK-FIX-RWOP1.1-wire-feature-plan-step-11-bdd-linking.md), [TASK-FIX-RWOP1.2](../../tasks/completed/2026-04/TASK-FIX-RWOP1.2-fold-bdd-oracle-and-smoke-gates-nudges.md)
- Sibling non-blockers: [TASK-FIX-RWOP1.4](../../tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.4-feature-spec-coach-gating-and-dead-surface.md), [TASK-FIX-RWOP1.5](../../tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.5-feature-plan-from-spec-orphan-disposition.md)
- Canonical fix shape: [TASK-FIX-3C9D](../../tasks/completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md)
- Sub-tasks filed by this triage:
  - [TASK-FIX-RWOP1.3.1](../../tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.3.1-wire-agent-invocation-validator.md) — Phase 2 WIRE P1
  - [TASK-FIX-RWOP1.3.2](../../tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.3.2-wire-phase-5-5-plan-audit.md) — Phase 2 WIRE P2
  - [TASK-FIX-RWOP1.3.3](../../tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.3.3-delete-orphan-modules.md) — Phase 3 DELETE-MODULE
  - [TASK-FIX-RWOP1.3.4](../../tasks/backlog/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.3.4-soften-pseudo-code-prose.md) — Phase 4 DELETE-PROSE
- Design-rule candidate (Graphiti): *"runner without producer anti-pattern"* — `guardkit__project_decisions`, uuid `184731b0-3cb6-4eb2-a310-883421767dbf`
