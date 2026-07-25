---
complexity: 5
dependencies: []
feature_id: FEAT-CV4M
id: TASK-CMIR-002
implementation_mode: task-work
status: in_review
task_type: feature
title: v4 Decision Format prompt + vocabulary mirror
wave: 1
autobuild_state:
  current_turn: 2
  max_turns: 30
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-CV4M
  base_branch: main
  started_at: '2026-07-25T22:32:46.833585'
  last_updated: '2026-07-25T23:39:31.858551'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Coach verdict-emission failed: Coach decision not found: no assistant
      text in harness events for TASK-CMIR-002 turn 1 (0 AssistantMessageEvent). Likely
      substrate limitation (qwen36-workhorse F2 at Coach level). Player should retry
      on turn 2 with this feedback.'
    timestamp: '2026-07-25T22:32:46.833585'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-07-25T23:24:54.156684'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# v4 Decision Format prompt + vocabulary mirror (switch-gated)

Under contract=v4 the coach synthesis prompt must instruct EXACTLY the v4 contract the
tune was trained on; under contract=coachsplit it must stay byte-identical to today.
Seams: `guardkit/orchestrator/agent_invoker.py::_build_coach_prompt` (:3003-3339 — the
Decision Format f-string :3269-3332, verification_example :3148-3161, responsibilities
:3217-3252) and `_render_absence_of_failure_guards` (:3899). Binding spec with the
NORMATIVE v4 block text and the six vocabulary substitutions:
docs/coach-contract-mirror-scope-and-buildplan.md §4 Fix B. Use the same contract
resolution seam as TASK-CMIR-001 (env `GUARDKIT_COACH_CONTRACT`, default coachsplit).

## Acceptance Criteria
- [ ] With contract=v4 the rendered synthesis prompt contains the normative v4 Decision Format block VERBATIM (byte-compare against the spec text in a hermetic test) and does NOT contain: "fenced JSON block", "criteria_verification", `"decision": "approve" | "feedback"`, "takes only the **last** fenced block"
- [ ] With contract=v4 the rendered prompt (incl. the absence-of-failure guards section) contains NONE of: "Surface as feedback", 'Surface a "feedback" decision', "verbatim in the rationale", "that is FEEDBACK, not approval", "Either APPROVE or provide specific FEEDBACK", "create a criteria_verification entry" — each replaced per the spec's substitution table
- [ ] With contract=coachsplit the rendered prompt is byte-identical to main (a golden test renders both and asserts equality; existing tests/orchestrator/test_coach_synthesis_split.py passes UNMODIFIED)
- [ ] The synthesis budget (_trim_synthesis_prompt) still applies on the v4 path and its _VERDICT_BEARING_MARKERS still protect the evidence sections in a v4-rendered prompt
