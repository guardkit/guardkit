---
id: TASK-FIX-COACHSCHEMA
title: Tighten the Coach prompt template with explicit schema example + self-check at end-of-prompt
status: backlog
task_type: fix
created: 2026-06-08T00:00:00Z
updated: 2026-06-08T00:00:00Z
priority: medium
complexity: 3
effort_hours: 2
deadline: 2026-06-15
parent_review: TASK-REV-HMIG
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
implementation_mode: direct
intensity: standard
blocker: false
surfaced_in: docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-12.md
falsifier: "After landing (only IF Path 1A / TASK-OPS-COACHGRAMMAR is unavailable OR insufficient): run 13/14 of `guardkit autobuild feature FEAT-AOF --fresh --model qwen36-workhorse --coach-model gemma4:26b` produces Coach verdict-emission rate ≥80% across ≥6 Coach turns. (Lower bar than Path 1A's 95% because prompt-shaping is a nudge, not enforcement.)"
---

# Task: Tighten Coach prompt template for schema-correct fenced-JSON emission

## Why this task exists

**This task is the Path 1B fallback to [TASK-OPS-COACHGRAMMAR](TASK-OPS-COACHGRAMMAR-enforce-coach-verdict-schema-via-llama-cpp-gbnf.md).**
Only land this if Path 1A (substrate-layer GBNF grammar enforcement) is
unavailable on the operator's llama.cpp build OR if Path 1A lands but
gemma4-coach still struggles with the semantic side of verdict emission
under the grammar constraint.

F24 (recorded as
[I-013](../../../docs/state/TASK-REV-HMIG/feature-run-incidents.md))
surfaced in run 12: gemma4-coach under `--reasoning auto` is unreliable
at the structured fenced-JSON contract. Three Coach turns, three
different failure shapes, 0/3 natural verdict-emissions. Architecture
has delivered; substrate is the constraint.

Path 1A enforces the schema at the inference layer (architecturally
correct, zero code change). Path 1B (this task) is the code-side
defensive fallback: a tighter Coach prompt that nudges the model
toward the schema with an explicit example and a self-check
instruction.

The two paths are complementary, not exclusive:
- Path 1A on its own: enforced schema, may produce syntactically valid
  but semantically incorrect verdicts (Coach approves work it shouldn't)
- Path 1B on its own: relies on the model honoring the instruction;
  partial coverage; some emissions still incomplete
- Path 1A + 1B together: enforced shape + steered semantics

## What to do

Edit the Coach prompt template in
[`guardkit/orchestrator/agent_invoker.py`](../../../guardkit/orchestrator/agent_invoker.py).
The prompt is at approximately line 2393 per the [I-007 notes in
feature-run-incidents.md](../../../docs/state/TASK-REV-HMIG/feature-run-incidents.md);
verify the current line number before editing.

**Add a schema-example block at the end of the Coach prompt.** Example
addition (operator should tune to match codebase style):

```python
COACH_PROMPT_TEMPLATE = """
... existing prompt ...

# CRITICAL: Verdict emission format

Your response MUST end with a fenced JSON block in EXACTLY this shape:

```json
{
  "task_id": "<the task id you were validating>",
  "turn": <the integer turn number>,
  "decision": "approve" | "feedback",
  "rationale": "<one-paragraph justification>",
  "criteria_results": [
    {"id": "<AC-NNN>", "status": "verified" | "rejected" | "pending"}
  ]
}
```

Before finalising your response, re-read your fenced JSON block and
verify:

1. All three REQUIRED fields are present: `task_id`, `turn`, `decision`
2. `task_id` matches the task you were given
3. `turn` is the integer turn number from the input
4. `decision` is exactly the string "approve" or "feedback" (not bool,
   not null)
5. The fence opens with EXACTLY ```json and closes with EXACTLY ```

If your block is missing any of these, revise it before sending your
final response. The orchestrator's parser will REJECT and retry if any
required field is missing.
"""
```

## Acceptance criteria

- [ ] **AC-1**: Coach prompt template in `agent_invoker.py` updated with explicit schema example and self-check instruction at end-of-prompt. Existing prompt structure preserved (just appended).

- [ ] **AC-2**: Unit test asserts the rendered Coach prompt contains the literal substrings `"task_id"`, `"turn"`, `"decision"`, and `"approve"` / `"feedback"` after a fresh render. Pins the template against silent regression.

- [ ] **AC-3 (smoke)**: 5× replay of a representative Coach prompt against gemma4-coach (with the new template) produces ≥4/5 responses with all three required fields present. (Lower bar than Path 1A's 5/5 because we're nudging, not enforcing.)

- [ ] **AC-4 (falsifier — downstream verification, ONLY if Path 1A is unavailable)**: Run 13/14 produces **Coach verdict-emission rate ≥80%** across ≥6 Coach turns. If ≥95% is achieved, AC-006 / AC-009 satisfied. If <80%, escalate to Path 2 (nemotron-3-super:120b-a12b, gated on 2nd GB10).

## Implementation notes

- **Prompt-engineering, not architecture**: this task touches only the
  Coach prompt template string. No changes to the parser, COACHSF01
  safety net, harness, or schema. Defensive nudge only.
- **Idempotent with Path 1A**: if the operator lands both 1A (substrate
  grammar) AND 1B (prompt tightening), the two are complementary. The
  grammar enforces shape; the prompt steers semantics. No conflict.
- **Risk**: too-aggressive prompt-shaping can confuse the model and
  degrade response quality on the actual *content* of the verdict.
  Pilot with the 5× smoke (AC-3) before committing to a full run.
- **Verify the COACHOUT01 schema source-of-truth**: cross-check the
  required-field list against
  [`guardkit/orchestrator/coach_output_parser.py`](../../../guardkit/orchestrator/coach_output_parser.py)
  before editing. If the parser requires additional fields beyond
  `task_id` / `turn` / `decision`, include them in the example.

## Related

- **Surfaces**: F24 in [feature-run-analysis.md §6](../../../docs/state/TASK-REV-HMIG/feature-run-analysis.md)
- **Incident**: I-013 in [feature-run-incidents.md](../../../docs/state/TASK-REV-HMIG/feature-run-incidents.md)
- **Substrate-layer companion (preferred)**: [TASK-OPS-COACHGRAMMAR](TASK-OPS-COACHGRAMMAR-enforce-coach-verdict-schema-via-llama-cpp-gbnf.md) (Path 1A)
- **Parser schema source-of-truth**: [`guardkit/orchestrator/coach_output_parser.py`](../../../guardkit/orchestrator/coach_output_parser.py)
- **COACHOUT01 schema invariant**: [`.claude/rules/feature-build-invariants.md`](../../../.claude/rules/feature-build-invariants.md) FB-004
- **Escalation path if 1A + 1B both insufficient**: TASK-HMIG-013 AC-007 (nemotron-3-super:120b-a12b, gated on 2nd GB10 + ConnectX-7)
- **Blocks**: TASK-HMIG-010 AC-006 / AC-009 (only IF Path 1A unavailable or insufficient)
