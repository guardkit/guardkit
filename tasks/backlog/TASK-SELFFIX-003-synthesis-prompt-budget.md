---
id: TASK-SELFFIX-003
title: Loud synthesis-prompt budget
task_type: feature
parent_review: TASK-REV-SELFFIX
feature_id: FEAT-8AD1
wave: 2
implementation_mode: task-work
complexity: 5
dependencies: [TASK-SELFFIX-001, TASK-SELFFIX-002]
---
# Loud synthesis-prompt budget

Task-work coach bundles reached 109,634 tokens and overflowed the normal checker's
crash-tested 98,304 window (FEAT-8737 TASK-SMOKE-002 turn 1, HTTP 400 receipt in the run
log). The per-tool-result gather cap (GUARDKIT_COACH_GATHER_MAX_TOOL_RESULT_CHARS, 12000)
exists but nothing bounds the RENDERED synthesis prompt. Investigate first: which bundle
fields carried the bulk in that receipt's shape. Then enforce an overall budget at the
synthesis-prompt build seam in `guardkit/orchestrator/agent_invoker.py`. Binding spec:
docs/factory-self-fix-scope-and-buildplan.md §2 Fix C + §3.

## Acceptance Criteria
- [ ] A short investigation note (in the task's implementation summary) names which fields dominated the oversized bundle shape
- [ ] The rendered coach synthesis prompt is bounded by GUARDKIT_COACH_SYNTHESIS_MAX_CHARS (default 300000) — a hermetic test renders an oversized synthetic bundle and asserts the rendered prompt fits the budget
- [ ] Trimming drops bulkiest low-signal content first (raw output tails) and NEVER the verdict-bearing fields (requirements, acceptance criteria, honesty, stub_scan, behavioural_oracle)
- [ ] Trimming is loud: a visible notice inside the prompt names what was cut and by how much, and a WARNING is logged — a hermetic test asserts both
- [ ] A normal-sized bundle renders byte-identically to today (no-trim path proven by test)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Implementation Notes
- Chars, not tokens: budget in characters (the seam has no tokenizer); 300000 chars ≈ 85k tokens leaves real margin under 98304.
- This is the permanent fix behind the operator dial used for this very build's run env.
