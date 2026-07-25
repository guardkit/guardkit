---
complexity: 5
dependencies: []
feature_id: FEAT-CV4M
id: TASK-CMIR-001
implementation_mode: task-work
status: in_review
task_type: feature
title: v4-first parser + wire-to-internal adapter
wave: 1
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-CV4M
  base_branch: main
  started_at: '2026-07-25T22:32:46.837383'
  last_updated: '2026-07-25T23:03:20.575768'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-07-25T22:32:46.837383'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# v4-first coach output parsing + wire-to-internal adapter

coach-ft-v4 replies with a SINGLE RAW JSON object `{"verdict": "approve"|"reject",
"findings": [{"locus": "..."}]}` — no fence, no prose, no task_id/turn. The current
parser (`guardkit/orchestrator/coach_output_parser.py::extract_and_write`, :191-337)
only extracts the last fenced ```json block and requires task_id/turn/decision keys.
Add a v4-first path gated on the active contract, adapting the v4 wire shape into the
UNCHANGED internal verdict object. Binding spec:
docs/coach-contract-mirror-scope-and-buildplan.md §2 + §4 Fix A. The contract-resolution
helper may be stubbed here (env `GUARDKIT_COACH_CONTRACT`, default `coachsplit`) if
TASK-CMIR-003 has not landed; keep the seam small.

## Acceptance Criteria
- [ ] With contract=v4: a canned raw v4 reply parses via whole-text json.loads; a v4 object embedded after stray text parses via last-balanced-object-containing-"verdict"; each is adapted to the internal object exactly per spec §2 (decision mapping, issues[] from findings with severity "major" landing in the fix-loop's must-fix bucket — bucketing boundary verified against `_parse_coach_feedback` and pinned in a test; criteria_verification []; task_id/turn injected from the call site; contract+findings provenance keys) and written to coach_turn_{turn}.json
- [ ] With contract=v4: approve⇒findings must be empty and reject⇒every finding needs a non-empty locus — violations raise CoachDecisionInvalidError with its existing message substring; a fenced LEGACY reply still parses via the unchanged fallback path and a log line records `contract=v4 path=legacy-fallback`
- [ ] With contract=coachsplit (the default): behaviour is byte-identical to today — the existing parser test suite passes UNMODIFIED, and exception classes/message substrings ("Coach decision not found"/"Coach decision invalid") are unchanged
- [ ] Every successful parse logs which path fired (contract + raw|balanced|legacy-fallback); a hermetic test asserts the log marker
