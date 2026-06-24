---
id: TASK-HMIG-009
title: Canary validation — TASK-GLI-004 + 2 additional canary tasks under LangGraph
status: completed
resolution: superseded
superseded_by: TASK-HMIG-009A
completed: 2026-06-18
completed_location: tasks/completed/autobuild-harness-migration/
task_type: validation
created: 2026-05-19T20:30:00Z
updated: 2026-06-18T16:00:00Z
previous_state: blocked
state_transition_reason: "Halted after pilot smokes v1–v7 (2026-05-27) surfaced F1 (pre-loop bypasses harness adapter) + F4 (worktree manager ignores cwd branch). 18-rep canary execution paused pending TASK-REV-HM09 review; the review substituted the substitute partial canary TASK-HMIG-009A (12-run batch, 83.3% any-turn / passed the ≥75% central falsifier, completed 2026-06-04) and CANCELLED the full-spec redo TASK-HMIG-009B. The canary question this task exists to answer was answered (YES, LangGraph ≥75%); superseded 2026-06-18."
# blocked_by: TASK-REV-HM09 — RESOLVED: the review produced 009A (substitute, passed) + 009B (cancelled).
priority: critical
complexity: 4
deadline: 2026-06-15
parent_review: TASK-REV-HMIG
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
parallel_group: 3A
implementation_mode: task-work
intensity: standard
effort_hours: 4
depends_on:
  - TASK-HMIG-006
  - TASK-HMIG-007   # in guardkitfactory; BDD plugin must be in place
  - TASK-HMIG-008
falsifier: "Each canary task is run 3× under GUARDKIT_HARNESS=langgraph and 3× under GUARDKIT_HARNESS=sdk in the same window with identical fixtures. The LangGraph run completes within 2× the SDK run's turn count, produces equivalent acceptance criteria pass/fail, and writes a byte-compatible coach_turn_N.json (modulo model_used field). Aggregate first-pass-success rate for LangGraph across the 9 runs ≥ 75% (the central-recommendation falsifier from TASK-REV-HMIG §11). If <75%, escalate to operator for revert decision."
tags:
  - autobuild
  - validation
  - canary
  - langgraph-migration
---

# Task: Canary validation under LangGraph

> **COMPLETED (superseded) 2026-06-18.** This task's original 18-run spec was
> halted 2026-05-27 at F1/F4 and never resumed in that form. The TASK-REV-HM09
> review resolved the block by **substituting TASK-HMIG-009A** — a partial
> 12-run canary (no pre-loop, backlog tasks) that ran 2026-06-04 and **passed
> the central ≥75% falsifier at 5/6 = 83.3% any-turn-approve** (LangGraph 67%
> first-pass / SDK 50%) — and **cancelling TASK-HMIG-009B** (the optional
> full-original-spec redo, in `tasks/cancelled/`). The canary question ("is
> LangGraph ≥75%?") was answered YES by 009A, which gated TASK-HMIG-010 and the
> cutover (TASK-HMIG-011, shipped 2026-06-16). No further canary work is needed;
> closing this as superseded-by-009A. Evidence:
> `docs/state/TASK-REV-HMIG/canary-analysis.md`.

## Description

Wave 3's first task. Validate the LangGraph harness against a small canary
task set before any feature-level commitment. This is the gate that decides
whether the central recommendation in the parent review (§1.1) is confirmed,
weakly-confirmed, or falsified.

The canary task set is **TASK-GLI-004** (the existing canary task from
[`autobuild_local_vllm.md`](../../../docs/autobuild_local_vllm.md))
plus 2 additional tasks spanning the {trivial-port, adaptation, redesign}
surfaces from review §4. Selection should cover at least one task that hit
Pattern 3 (honesty false-fail) and one that hit Pattern 2 (BDD missing glue)
in the SDK historical record so the migration guards are exercised under
load.

## Acceptance Criteria

- [ ] AC-001: Canary task set defined and recorded in
      `.guardkit/autobuild/TASK-REV-HMIG-canary-set.json` with the rationale for each pick.
- [ ] AC-002: Each canary task run 3× per harness (6 runs per task; 18 runs total).
- [ ] AC-003: Identical fixtures across SDK and LangGraph runs (same task spec,
      same input files, same backing model where possible — Anthropic
      Sonnet 4.5 for SDK, Qwen36-workhorse for LangGraph since the model is
      the unavoidable variable).
- [ ] AC-004: Per-task per-run record in
      `.guardkit/autobuild/TASK-REV-HMIG-canary-results.json`:
      `task_id`, `harness`, `run_index`, `turns_used`, `coach_decision`,
      `acceptance_criteria_passed`, `acceptance_criteria_failed`,
      `wall_clock_seconds`, `model_used`, `notes`.
- [ ] AC-005: Aggregate first-pass-success rate for LangGraph across all 9
      LangGraph runs computed and recorded. Computation: `count(coach_decision == "approve" AND turns_used == 1) / 9`.
- [ ] AC-006: Comparison written to `.guardkit/autobuild/TASK-REV-HMIG-canary-comparison.md`:
      LangGraph vs SDK on first-pass-success rate, mean turns-to-approve,
      mean wall-clock, and per-task AC equivalence (which ACs the two harnesses agree on, which they disagree on).
- [ ] AC-007: Falsifier evaluation:
  - If LangGraph rate ≥ 85%: recommendation strongly confirmed. Proceed at full pace to TASK-HMIG-010.
  - If LangGraph rate in [75%, 85%): recommendation weakly confirmed. Proceed with elevated risk weighting on R-02 and R-06; flag at the Wave 4 cutover decision.
  - If LangGraph rate < 75%: recommendation **falsified per review §11**. Halt Wave 4 cutover. Escalate to operator. Open a new task (TASK-HMIG-011 or similar) to decide between (a) extending validation window, (b) reverting to SDK + extending API-key-redirect lifetime negotiation with Anthropic if possible, (c) pivoting to a third option (OpenCode in headless mode, more gate engineering, etc.).
- [ ] AC-008: Result analysis written to `docs/state/TASK-REV-HMIG/canary-analysis.md` for audit.

## Implementation Notes

- The 3× repetition per task per harness controls for run-to-run variance from
  non-deterministic LLMs. Don't reduce below 3 without acceptance criteria revision.
- "Identical fixtures" means: same `.feature` file, same acceptance criteria, same task description, same starting commit on the worktree branch. The only deliberate difference is the active substrate.
- If guardkitfactory's `LangGraphHarness` exposes diagnostic tracing (LangSmith), capture trace IDs in the per-run record for forensic recovery if a falsifier fires.
- Schedule this work for D-13 → D-9 so there's slack to investigate failures before TASK-HMIG-010 starts.

## References

- Review §11 — Falsifier for the central recommendation (75% threshold)
- Review §7.3 — Wave 3 sequencing
- `docs/autobuild_local_vllm.md` — TASK-GLI-004 canary definition (may need a copy-or-update before the run)

## Notes

This is the most important task in the migration. The two prior task sets
(Wave 1 foundation, Wave 2 quality-gate integration) build the harness; this
task answers the question "is the harness actually better?" If the answer is
no, the rest of Wave 3 + Wave 4 does not happen.

## Operator handoff (2026-05-21, scaffolded by `/task-work TASK-HMIG-009`)

`/task-work` produced the **scaffolding** for this validation but did not
execute the 18 autobuild runs — those are operator-driven because each
costs real LLM tokens and ~10-30 min wall-clock.

### Scaffolded artefacts

| Path | Purpose |
|---|---|
| `.guardkit/autobuild/TASK-REV-HMIG-canary-set.json` | Canary picks + per-harness env/model config. Operator may edit task picks (slots 2 and 3 are operator-pickable; TASK-GLI-004 is mandated). |
| `scripts/canary_validation_runner.py` | Drives the 18 runs sequentially. Resumable. Has `--dry-run`, `--aggregate`, `--task`, `--harness`, `--reps` flags. |
| `.guardkit/autobuild/TASK-REV-HMIG-canary-comparison.md` | Auto-regenerated by `--aggregate`. Sections 1-3 auto, section 4 hand-fill. |
| `docs/state/TASK-REV-HMIG/canary-analysis.md` | Human-authored audit narrative. To complete after section 1 of comparison doc lands. |

### Canary picks and rationale

1. **TASK-GLI-004** (mandated, complexity 2, harness-agnostic baseline) — already completed in main, so the operator must either (a) author a pre-implementation fixture branch, or (b) `git revert` the implementation commit on a fixture branch. Without this step, autobuild sees the work already done and exits trivially.
2. **TASK-FIX-A7D3** (complexity 3, Pattern-3 surface) — currently in backlog. Critical-priority Python scoping bugfix in `installer/core/lib/agent_enhancement/enhancer.py`. Exercises state-bridge moves where Pattern 3 manifested. No prep needed.
3. **TASK-DOC-267D** (complexity 2, Pattern-2 *weak* surface) — currently in backlog. Multi-file template-edit task. CAVEAT: `bdd_scenarios: []`, so does NOT directly exercise the BDD-plugin contract C1. If faithful Pattern-2 coverage is required, supplement with a synthetic small task that has `bdd_scenarios: [BDD-CANARY-001]` and intentionally mismatched step definitions. See `canary-set.json:selection_notes.operator_override_protocol`.

### Pre-flight before running

```bash
# 1. Verify guardkitfactory is installed in this venv for langgraph runs.
python -c "from guardkitfactory.harness import LangGraphHarness; print('ok')"

# 2. Verify the LangGraph model string format. The Wave-2 skeleton only
#    forwards `model`. Update the canary-set.json model field for the
#    langgraph harness if the format differs from
#    "openai:Qwen/Qwen3-Coder-30B-A3B".

# 3. Verify the SDK path. Either real ANTHROPIC_API_KEY, or the
#    gb10:9000 redirect is active (until 2026-06-15).
guardkit autobuild task --help >/dev/null

# 4. Decide TASK-GLI-004's fixture-branch strategy (see picks above)
#    and execute it BEFORE invoking the runner. Otherwise the SDK
#    baseline runs for TASK-GLI-004 will all trivially "succeed" with
#    0 work and skew the first-pass rate upward.
```

### Execution (D-13 → D-9 per spec; ~4-12 hours total)

```bash
# Dry-run first to confirm the 18-run plan.
python scripts/canary_validation_runner.py --dry-run

# Smoke one slice before committing to all 18.
python scripts/canary_validation_runner.py --task TASK-GLI-004 --reps 1

# Run all 18. Resumable — re-invoke after interruption.
python scripts/canary_validation_runner.py

# Generate the comparison doc with falsifier verdict.
python scripts/canary_validation_runner.py --aggregate
```

### After the runs complete

1. Read `.guardkit/autobuild/TASK-REV-HMIG-canary-comparison.md` section 1 for the verdict.
2. Hand-fill section 4 (per-task AC equivalence) from the per-run `coach_turn_N.json` artefacts under `.guardkit/autobuild/TASK-REV-HMIG-canary/`.
3. Write `docs/state/TASK-REV-HMIG/canary-analysis.md` (skeleton already exists). Sections 3, 4, 5, 6 require manual narrative.
4. Tick AC-001 through AC-008 above based on what landed.
5. Per AC-007: if LangGraph rate ≥ 85%, proceed to TASK-HMIG-010. If 75-85%, proceed with elevated R-02/R-06 risk weighting. If <75%, **HALT Wave 4 cutover** and file TASK-HMIG-011 (revert decision).
