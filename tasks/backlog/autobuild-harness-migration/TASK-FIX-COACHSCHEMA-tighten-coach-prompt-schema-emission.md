---
id: TASK-FIX-COACHSCHEMA
title: Tighten the Coach prompt template with explicit schema example + self-check at end-of-prompt
status: in_progress
task_type: fix
created: 2026-06-08T00:00:00Z
updated: 2026-06-08T15:00:00Z
priority: high
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
blocker: true
surfaced_in: docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-13.md
falsifier: "Run 14 of `guardkit autobuild feature FEAT-AOF ... --coach-model gemma4:26b --task-timeout 4800` produces ≥1 Coach turn that CONVERGES — emits a valid fenced-JSON verdict (task_id/turn/decision present) and finishes WITHIN the per-invocation SDK timeout (no 2340s reason-forever timeout like run 13) — across ≥4 Coach turns, with ≥80% emitting valid required fields. PRIMARY metric is convergence (Coach completes), not emission-rate alone; run 13 timed out before emitting anything."
---

# Task: Tighten Coach prompt template for schema-correct fenced-JSON emission

## Why this task exists

> **PROMOTED TO PRIMARY 2026-06-08 — Path 1A is invalidated + re-scoped beyond schema.**
> Path 1A ([TASK-OPS-COACHGRAMMAR](TASK-OPS-COACHGRAMMAR-enforce-coach-verdict-schema-via-llama-cpp-gbnf.md))
> was a **no-op**: llama.cpp bypasses a route-level `--grammar-file` whenever a
> request carries `tools`, and the `deepagents` Coach sends built-in tools on every
> `/v1/responses` call, so the grammar never reached the Coach (see
> [`grammars/README.md`](../../../docs/research/dgx-spark/grammars/README.md)). This
> task is therefore the **primary** prompt-side path, and it has been **re-scoped**:
> run 13 showed the dominant failure is not bad-schema emission (run 12) but
> **non-convergence** — the Coach ran ~39 min as an agent and timed out (2340s) before
> emitting *anything*. So the prompt change targets **decisiveness/efficiency first**
> (converge + emit), schema self-check second.

F24 / run 12: gemma4-coach emitted verdicts but with missing/incomplete schema.
**Run 13: gemma4-coach as a tool-using agentic Coach never converged — it
over-explored and hit the SDK timeout with no verdict at all.** The substrate
(gemma4-26B-A4B-IT as an agentic verifier under a per-invocation timeout) is the
constraint; this prompt change is a nudge toward convergence, not a guarantee.

This task touches only the Coach prompt template — it works regardless of `tools`
(unlike the bypassed grammar). If the run-14 falsifier still times out, the
substrate is the wall → escalate to the **toolless verdict-synthesis call**
(grammar-constrained, code change) or **Path 2** (nemotron-3-super, 2nd GB10).

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

- [x] **AC-1 (re-scoped)**: Coach prompt updated with a **decisiveness/efficiency** block AND a 3-field self-check, inserted before `## Your Responsibilities` in `_build_coach_prompt` ([`agent_invoker.py`](../../../guardkit/orchestrator/agent_invoker.py)). ✓ **Done 2026-06-08** — the `## Verification Budget — Be Decisive` section (verify each AC once → STOP → emit; "decisive means efficient, never lazy / a false approve is the worst outcome"; then self-check `task_id`/`turn`/`decision`). Designed + adversarially reviewed via a judge-panel workflow (verdict: ship). It reaches the LangGraph Coach (`_build_coach_prompt` feeds both harnesses via `_invoke_with_role`) — unlike the bypassed grammar.

- [x] **AC-2**: Unit test asserts the block is rendered. ✓ **Done** — [`tests/orchestrator/test_coach_decisiveness_prompt.py`](../../../tests/orchestrator/test_coach_decisiveness_prompt.py) (5 tests: section present; the decisiveness/STOP levers; the no-false-approve guardrails; the `task_id (string), turn (integer), decision (...)` self-check; and that the block precedes `## Decision Format`). All pass; adds 0 new failures to the suite.

- [ ] **AC-3 (smoke — caveated)**: A no-tools single-shot replay against gemma4-coach can sanity-check the new prompt renders + still produces a verdict, BUT **a single-shot smoke does NOT represent the tool-bound agentic Coach** (this is exactly the trap that made Path 1A's AC-4 look like it worked). Do not treat a green single-shot as proof. The real test is AC-4.

- [ ] **AC-4 (falsifier — run 14, PRIMARY metric = convergence)**: Run 14 (`--task-timeout 4800`, langgraph harness, from the Mac) produces ≥1 Coach turn that **converges** — emits a valid fenced-JSON verdict (`task_id`/`turn`/`decision`) AND finishes within the per-invocation SDK timeout (no 2340s reason-forever timeout) — across ≥4 Coach turns, ≥80% with valid required fields. If the Coach still times out, the substrate is the wall → escalate to the toolless verdict-synthesis call or Path 2 (nemotron-3-super:120b-a12b, 2nd GB10).

## Implementation notes

- **Prompt-engineering, not architecture**: this task touches only the
  Coach prompt template string. No changes to the parser, COACHSF01
  safety net, harness, or schema. Defensive nudge only.
- **Path 1A is moot** (no-op for the tool-bound Coach — see "Why this task
  exists"). This prompt change stands alone and applies regardless of `tools`.
- **Primary risk is now the timeout, not schema**: the block is aimed at
  convergence (the run-13 failure). A *secondary* risk is that too-aggressive
  decisiveness phrasing induces a fast-but-wrong approve — mitigated by the
  verbatim "decisive means efficient, never lazy / still verify EACH criterion /
  a false approve is the worst outcome" guardrails (pinned by AC-2).
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
