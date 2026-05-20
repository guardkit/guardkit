---
id: TASK-HMIG-009
title: Canary validation — TASK-GLI-004 + 2 additional canary tasks under LangGraph
status: backlog
task_type: validation
created: 2026-05-19T20:30:00Z
updated: 2026-05-19T20:30:00Z
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
