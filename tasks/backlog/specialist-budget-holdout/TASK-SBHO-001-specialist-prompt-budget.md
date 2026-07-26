---
complexity: 4
dependencies: []
feature_id: FEAT-SBHO
id: TASK-SBHO-001
implementation_mode: task-work
status: blocked
task_type: feature
title: Budget the specialist/advisory prompt seams
wave: 1
autobuild_state:
  current_turn: 4
  max_turns: 30
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO
  base_branch: main
  started_at: '2026-07-26T02:04:42.034673'
  last_updated: '2026-07-26T03:26:32.752047'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Deterministic honesty record (claim_audit_unmodified, severity=should_fix):\
      \ Player claim: Player claimed file guardkit/orchestrator/specialist_invocations.py.\
      \ Actual: Path is tracked in git but 'git status --porcelain' shows no change\
      \ for it \u2014 the Player claimed work on a file it did not actually modify\
      \ this turn. Most likely cause: the report writer swept an orchestrator-managed\
      \ path (e.g. a file under .guardkit/autobuild/ or tasks/<state>/) into files_modified.\
      \ Defence-in-depth for the agent_invoker-side filter; this is a warning, not\
      \ a turn-rejecting fabrication..\n- Deterministic honesty record (claim_audit_unmodified,\
      \ severity=should_fix): Player claim: Player claimed file guardkit/qa/review_seat.py.\
      \ Actual: Path is tracked in git but 'git status --porcelain' shows no change\
      \ for it \u2014 the Player claimed work on a file it did not actually modify\
      \ this turn. Most likely cause: the report writer swept an orchestrator-managed\
      \ path (e.g. a file under .guardkit/autobuild/ or tasks/<state>/) into files_modified.\
      \ Defence-in-depth for the agent_invoker-side filter; this is a warning, not\
      \ a turn-rejecting fabrication..\n- Deterministic honesty record (claim_audit,\
      \ severity=critical): Player claim: Player claimed file tests/qa/test_review_seat.py::TestAdvisoryNeverRaises.\
      \ Actual: Path absent from 'git status --porcelain' so 'git add -A' would not\
      \ stage it. Probes: path_exists=False; gitignore_match=no rule matched; tracked=no.\
      \ Most likely cause: the Player claimed work on a file that does not exist on\
      \ disk..\n... and 3 more issues"
    timestamp: '2026-07-26T02:04:42.034673'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: "- Deterministic honesty record (claim_audit_unmodified, severity=should_fix):\
      \ Player claim: Player claimed file guardkit/orchestrator/quality_gates/coach_validator.py.\
      \ Actual: Path is tracked in git but 'git status --porcelain' shows no change\
      \ for it \u2014 the Player claimed work on a file it did not actually modify\
      \ this turn. Most likely cause: the report writer swept an orchestrator-managed\
      \ path (e.g. a file under .guardkit/autobuild/ or tasks/<state>/) into files_modified.\
      \ Defence-in-depth for the agent_invoker-side filter; this is a warning, not\
      \ a turn-rejecting fabrication..\n- Deterministic honesty record (claim_audit_unmodified,\
      \ severity=should_fix): Player claim: Player claimed file guardkit/orchestrator/specialist_invocations.py.\
      \ Actual: Path is tracked in git but 'git status --porcelain' shows no change\
      \ for it \u2014 the Player claimed work on a file it did not actually modify\
      \ this turn. Most likely cause: the report writer swept an orchestrator-managed\
      \ path (e.g. a file under .guardkit/autobuild/ or tasks/<state>/) into files_modified.\
      \ Defence-in-depth for the agent_invoker-side filter; this is a warning, not\
      \ a turn-rejecting fabrication..\n- Deterministic honesty record (claim_audit_unmodified,\
      \ severity=should_fix): Player claim: Player claimed file guardkit/qa/review_seat.py.\
      \ Actual: Path is tracked in git but 'git status --porcelain' shows no change\
      \ for it \u2014 the Player claimed work on a file it did not actually modify\
      \ this turn. Most likely cause: the report writer swept an orchestrator-managed\
      \ path (e.g. a file under .guardkit/autobuild/ or tasks/<state>/) into files_modified.\
      \ Defence-in-depth for the agent_invoker-side filter; this is a warning, not\
      \ a turn-rejecting fabrication..\n... and 1 more issues"
    timestamp: '2026-07-26T02:20:14.023005'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 3
    decision: feedback
    feedback: "- Deterministic honesty record (claim_audit_unmodified, severity=should_fix):\
      \ Player claim: Player claimed file guardkit/orchestrator/quality_gates/coach_validator.py.\
      \ Actual: Path is tracked in git but 'git status --porcelain' shows no change\
      \ for it \u2014 the Player claimed work on a file it did not actually modify\
      \ this turn. Most likely cause: the report writer swept an orchestrator-managed\
      \ path (e.g. a file under .guardkit/autobuild/ or tasks/<state>/) into files_modified.\
      \ Defence-in-depth for the agent_invoker-side filter; this is a warning, not\
      \ a turn-rejecting fabrication..\n- Deterministic honesty record (claim_audit_unmodified,\
      \ severity=should_fix): Player claim: Player claimed file guardkit/orchestrator/specialist_invocations.py.\
      \ Actual: Path is tracked in git but 'git status --porcelain' shows no change\
      \ for it \u2014 the Player claimed work on a file it did not actually modify\
      \ this turn. Most likely cause: the report writer swept an orchestrator-managed\
      \ path (e.g. a file under .guardkit/autobuild/ or tasks/<state>/) into files_modified.\
      \ Defence-in-depth for the agent_invoker-side filter; this is a warning, not\
      \ a turn-rejecting fabrication..\n- Deterministic honesty record (claim_audit_unmodified,\
      \ severity=should_fix): Player claim: Player claimed file guardkit/qa/review_seat.py.\
      \ Actual: Path is tracked in git but 'git status --porcelain' shows no change\
      \ for it \u2014 the Player claimed work on a file it did not actually modify\
      \ this turn. Most likely cause: the report writer swept an orchestrator-managed\
      \ path (e.g. a file under .guardkit/autobuild/ or tasks/<state>/) into files_modified.\
      \ Defence-in-depth for the agent_invoker-side filter; this is a warning, not\
      \ a turn-rejecting fabrication..\n... and 1 more issues"
    timestamp: '2026-07-26T02:43:05.934215'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 4
    decision: feedback
    feedback: '- Direct-mode evidence gate blocked the turn (direct_mode_ac_unverified).
      Direct mode relaxes coverage/arch gates but still requires verifiable AC delivery,
      resolved wiring, and runnable registered producers:

      - [direct_mode_ac_unverified] Direct mode: 4/4 acceptance criteria have no disk
      evidence (unmet: [''AC-001'', ''AC-002'', ''AC-003'', ''AC-004'']). Direct mode
      relaxes coverage/arch but NOT AC delivery.'
    timestamp: '2026-07-26T03:09:31.762424'
    player_summary: '[RECOVERED via git_test_detection] Original error: SDK timeout
      after 610s: task-work execution exceeded 610s timeout'
    player_success: true
    coach_success: true
---

# Budget the specialist/advisory prompt seams

The FEAT-8AD1 merge (58bc42b6) filed this follow-up: the code-reviewer specialist prompt
is a SEPARATE seam from the coach synthesis budget (3 live overflow receipts,
advisory/non-fatal) — same budget owed. Two seams are unbudgeted today:
guardkit/qa/review_seat.py::build_seat_messages (:319-338 — only the diff is capped at
60k; repo_context and the assembled payload are unbounded) and
guardkit/orchestrator/specialist_invocations.py::_build_code_reviewer_prompt (:886-936 —
a ~2000-char seed cap only). Mirror the _trim_synthesis_prompt pattern
(agent_invoker.py:3402-3665): env-tunable ceiling, protected sections, loud in-prompt
truncation marker + WARNING log, degrade never raise. Binding spec:
docs/specialist-budget-and-holdout-scope-and-buildplan.md §2.

## Acceptance Criteria
- [ ] GUARDKIT_REVIEW_SEAT_MAX_CHARS (default 300000) bounds the ASSEMBLED review-seat user message: a hermetic test builds an oversized payload (huge repo_context + big diff) and asserts the assembled message fits the budget, contains the loud truncation marker, trims repo_context before the diff, and never trims the instruction header or the finding-schema section
- [ ] GUARDKIT_SPECIALIST_PROMPT_MAX_CHARS (default 300000) backstops the final prompt for the specialist builders in specialist_invocations.py; the existing ~2000-char seed-cap behaviour is unchanged when under budget
- [ ] Advisory/non-fatal contracts unchanged: run_advisory_review still never raises and never returns blocking=True (existing tests pass unmodified); a WARNING log fires on any trim
- [ ] Zero net-new failures on the existing suite; both new tests are hermetic (no model calls)
