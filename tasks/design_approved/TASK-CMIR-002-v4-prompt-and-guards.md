---
complexity: 5
dependencies: []
feature_id: FEAT-CV4M
id: TASK-CMIR-002
implementation_mode: task-work
status: design_approved
task_type: feature
title: v4 Decision Format prompt + vocabulary mirror
wave: 1
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