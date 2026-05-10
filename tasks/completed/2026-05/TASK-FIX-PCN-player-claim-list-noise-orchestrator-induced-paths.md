---
id: TASK-FIX-PCN
title: Player report writer dumps tracked-but-unmodified orchestrator paths into files_modified, breaking checkpoint-claim audit
status: completed
task_type: implementation
implementation_mode: task-work
parent_review: TASK-REV-F30A
external_origin: study-tutor/.claude/reviews/TASK-REV-F30A-review-report.md
external_run_log: study-tutor/docs/history/autobuild-FEAT-39E1-run-5.md
priority: high
created: 2026-05-10T20:30:00Z
updated: 2026-05-10T21:45:00Z
completed: 2026-05-10T21:45:00Z
completed_location: tasks/completed/2026-05/
previous_state: in_review
state_transition_reason: "All 7 ACs implemented + tested; scoped tests passing (862 in coach/honesty/claim filter)"
complexity: 5
tags: [autobuild, agent-invoker, player-report, claim-audit, false-fail, divergence]
related_tasks:
  - TASK-AB-FIX-CHECKPOINT-CLAIM-AUDIT
  - TASK-FIX-IGNR
  - TASK-FIX-RBSS
  - TASK-FIX-HEAB
inputs:
  source_files:
    - guardkit/orchestrator/agent_invoker.py
  reference: |
    Run-5 PH1-005 timeline (study-tutor/docs/history/autobuild-FEAT-39E1-run-5.md):
      Turn 1 honesty 0.95 (4 discrepancies)  — manageable, recoverable
      Turn 2 honesty 0.49 (25 discrepancies) — divergence begins
      Turn 3 feedback (rollback fired)
      Turn 4 honesty 0.13 (179 discrepancies) — terminal divergence
      decision=timeout_budget_exhausted (4 turns)
test_results:
  status: passing
  coverage: not_measured_full_run
  last_run: 2026-05-10T21:30:00Z
  scoped_runs:
    - "tests/unit/test_orchestrator_induced_path_filter.py: 43 passed"
    - "tests/unit/test_coach_verification_claim_audit.py: 14 passed"
    - "tests/integration/orchestrator/test_coach_claim_audit.py: 6 passed"
    - "tests/unit/ + tests/integration/orchestrator/ -k 'coach or honesty or claim': 862 passed"
  pre_existing_failures_unrelated:
    - "tests/unit/test_agent_invoker.py::test_invoke_task_work_implement_mode_passed (confirmed pre-existing on main via stash/test/restore)"
    - "tests/rules/test_no_dead_task_id_references.py: 4 hardcoded TASK-IDs (TASK-FRR-PEB-FM-001, TASK-REV-PEBR-002, TASK-REV-DEA8, TASK-FRR-PEB-006) in untouched files"
acceptance_criteria_status:
  AC-1: passed  # Filter at agent_invoker.py:2826-2862; scope = state_bridge moves only
  AC-2: passed  # _strip_orchestrator_managed_paths covers .guardkit/autobuild/*, .guardkit/bootstrap_state.json, tasks/<state>/*
  AC-3: passed  # test_orchestrator_induced_path_filter: 1 comprehensive + 18 parametric matcher tests
  AC-4: passed  # test_player_authored_paths_pass_through + 12 parametric pass-through tests
  AC-5: passed  # Logging emits 'Filtered N orchestrator-induced ghost path(s) for {task_id}: [...]' with full sorted set
  AC-6: passed  # _classify_dropped_path returns 'tracked_unmodified' when ls-files --error-unmatch succeeds; demoted to should_fix in _verify_claims_were_staged + coach_validator._honesty_issues_from
  AC-7: passed  # test_claim_audit_tracked_unmodified_is_should_fix + test_claim_audit_unmodified_does_not_short_circuit_gate
files_changed:
  - guardkit/orchestrator/agent_invoker.py
  - guardkit/orchestrator/coach_verification.py
  - guardkit/orchestrator/quality_gates/coach_validator.py
  - tests/unit/test_orchestrator_induced_path_filter.py
  - tests/unit/test_coach_verification_claim_audit.py
---

# Task: Player report writer dumps tracked-but-unmodified orchestrator paths into files_modified

## Description

The autobuild Player report writer (in `agent_invoker.py`'s `_construct_player_report` / equivalent enrichment path — find the exact site) is including paths in `files_modified` that the Player did not actually modify in this turn. Specifically, paths it observed on disk because:

- The orchestrator wrote them itself before the Player ran (`.guardkit/autobuild/<TASK-ID>/coach_turn_N.json`, `player_turn_N.json`, `turn_state_turn_N.json`)
- The orchestrator's setup phase copied them in (`tasks/backlog/<TASK-ID>-*.md`)
- The bootstrap/environment phase wrote them (`.guardkit/bootstrap_state.json`)

These paths are NOT gitignored (so TASK-FIX-IGNR's gitignored→should_fix demotion does not apply) and they exist on disk (so the file-existence check passes). They simply weren't *modified* in this turn — `git status --porcelain` correctly returns nothing for them. The Coach's `_verify_claims_were_staged` audit then flags every one as `severity="critical"` (or `must_fix`) because the path is claimed but absent from porcelain.

In study-tutor FEAT-39E1 run-5 PH1-005 (NATSAdapter), this turned a fully-correct Player implementation (332-line `nats_adapter.py` + 27-test `test_nats_adapter.py` — verified, 27/27 pass post-salvage) into a four-turn `timeout_budget_exhausted` failure. The Player's actual Authoring was sound; the report's claim list grew from 4 → 25 → 30+ → 179 paths across turns as the Player became "more thorough" in response to the audit feedback, sweeping more orchestrator-induced files into `files_modified` each turn. Honesty score collapsed monotonically. RBSS session-reset (now correct) cleared the SDK conversation memory between turns but the Player's report-generation logic produced the same noise on each fresh session.

The auditor is correct — these paths weren't modified. The defect is that the **Player report should not list them in the first place**. They are orchestrator-managed state, not Player work product.

A precedent exists for this filtering: in run-3, an `agent_invoker.py` log line read *"Filtered N orchestrator-induced ghost path(s) for TASK-NATS-PH1-004: ['tasks/backlog/TASK-NATS-PH1-004-command-router.md']"*. So a filter exists but in run-5 it caught zero paths across four turns of PH1-005 even though dozens of orchestrator-induced paths reached the Coach's claim audit. The filter is either pattern-matching too narrowly, gated off, or running at the wrong point in the report-construction pipeline.

## Acceptance Criteria

- [x] **AC-1**: Identify and document the call site of the existing "Filtered N orchestrator-induced ghost path(s)" filter in `agent_invoker.py`. Report the exact patterns it matches today.
- [x] **AC-2**: Extend the filter (or add a sibling) so it removes the following from Player-report `files_created` / `files_modified` / `tests_written` / `completion_promises[*].implementation_files` BEFORE the report reaches the Coach claim audit:
  - `.guardkit/autobuild/<TASK-ID>/*.json` — orchestrator's per-task metadata sidecars
  - `.guardkit/bootstrap_state.json` — environment bootstrap state
  - `.guardkit/autobuild/<FEAT-ID>/*.{jsonl,md,json}` — feature-level metadata
  - `tasks/backlog/<any-TASK-ID>-*.md`, `tasks/design_approved/<any-TASK-ID>-*.md`, `tasks/in_review/...`, `tasks/in_progress/...`, `tasks/completed/...` — task scaffolding the orchestrator copies during setup
  - `tasks/backlog/<feature-slug>/<TASK-ID>-*.md` — sub-folder variants
- [x] **AC-3**: New unit test `test_orchestrator_induced_path_filter` exercises a synthetic Player report with each AC-2 path class included; asserts they are stripped before the report leaves the agent_invoker enrichment.
- [x] **AC-4**: New regression test `test_player_authored_paths_pass_through` exercises a report containing genuine Player work (`src/.../*.py`, `tests/.../*.py`) and asserts NONE of those paths are stripped.
- [x] **AC-5**: `Filtered N orchestrator-induced ghost path(s)` log line surfaces all stripped paths (not just one), in the same `agent_invoker` logger so the run-3-style logging continues to work.
- [x] **AC-6**: Add a "tracked-but-unmodified" demotion at the Coach claim-audit layer (sibling to TASK-FIX-IGNR's gitignored demotion): when a claimed path satisfies `(self.worktree_path / path).exists() AND git ls-files --error-unmatch <path> succeeds AND porcelain shows nothing` → emit `Discrepancy(claim_type="claim_audit_unmodified", severity="should_fix")` rather than `severity="critical"`. Defence-in-depth: if PCN's Player-side filter misses a path, the audit still surfaces a warning rather than collapsing the gate.
- [x] **AC-7**: New unit test `test_claim_audit_tracked_unmodified_is_should_fix` covers AC-6.

## Implementation Notes

- The Player-side filter (AC-1/AC-2/AC-3) is the **load-bearing** fix. AC-6 is belt-and-braces.
- Be conservative with the path patterns: scope them tightly to known orchestrator-managed namespaces (`\.guardkit/autobuild/.*`, `\.guardkit/bootstrap_state\.json`, `tasks/(?:backlog|design_approved|in_progress|in_review|completed)/.*`) so genuine Player work in unrelated `tasks/` subdirectories or `.guardkit/` user-scripted artefacts is not stripped.
- Run-3 analysed in TASK-REV-F30A (see external_review). The audit-trail preservation now in TASK-FIX-RBSS gives this task a place to validate against — replay an archived run-5 turn through the new filter and assert the discrepancy count drops from 179 to ~0.
- This task does **not** depend on TASK-FIX-HEAB-FOLLOWUP. They address different surfaces: HEAB-FOLLOWUP makes the loop *exit faster* on divergence; PCN prevents the divergence in the first place. Both wanted.

## Why this matters

Without PCN, every autobuild turn for a non-trivial task produces a noisy claim list that the Coach correctly fails. The result is reproducible: divergent honesty curve, max_turns or timeout_budget exhaustion, no implementation lands. The user's FEAT-39E1 demo recovery has now hand-implemented or salvaged five PH1-* tasks because of this defect; without PCN the same hand-implementation will be required for every subsequent feature.

The bug presents as Player dishonesty (`severity="critical"` claim_audit) but the Player's *actual code* in run-5 PH1-005 was correct — 27/27 unit tests passed when salvaged from the worktree to main. The defect is in report construction, not in the Player's work product. A user reading the autobuild log without forensic context will reasonably conclude the Player is broken; the truth is the report writer is.
