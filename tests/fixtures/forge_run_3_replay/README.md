# forge-run-3 replay fixtures (TASK-FIX-7A08)

Minimised replay fixtures derived from the forge-run-3 transcript
(`docs/reviews/bdd-acceptance-wired-up/forge-run-3.md`) lines 1084-1111
(TASK-NFI-003) and 1178-1205 (TASK-NFI-007).

The original run produced `agent_invocations_validation.status == "violation"`
for three consecutive turns because the Player did all work inline instead
of invoking the specialists via `Task`.

These fixtures simulate what `task_work_results.json` looks like **after**
the Player prompt has been corrected (TASK-FIX-7A08) — the Player followed
the new mandate and invoked `test-orchestrator` (Phase 4) and
`code-reviewer` (Phase 5) via `Task`, so the validator sees 3 of 3 required
invocations and the Coach's agent-invocations gate passes.

## Files

- `nfi_003_turn_1_post_fix.json` — post-fix replay for TASK-NFI-003 turn 1
  (minimum fields the validator + Coach consume).
- `nfi_007_turn_1_post_fix.json` — post-fix replay for TASK-NFI-007 turn 1.

## Consumers

- `tests/unit/test_coach_agent_invocations_stall_classification.py`
  (`test_post_fix_replay_coach_no_reject`, `test_post_fix_replay_stall_classifier_quiet`)
