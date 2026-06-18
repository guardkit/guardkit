---
id: TASK-FIX-COACHSCHEMA
title: Tighten the Coach prompt template with explicit schema example + self-check at end-of-prompt
status: blocked
deferred: 2026-06-18   # Path 1B falsified (run 14) AND the 31B-dense escalation rejected (06-18: "slower, no better"); accept gemma4:26b + COACHSF01
blocked_reason: "Path 1B FALSIFIED by run 14 — the decisive prompt + --sdk-timeout 3600 did NOT make gemma4-coach converge. Turn 1: 49,720 chars reasoning_content (9x run-12), no verdict, ~45 min; turn 2: 1347 chars, still no verdict. More time made it worse, not better → not a time/prompt problem, it's the substrate (3.8B-active model can't converge). Escalate to a substrate change: Gemma 4 31B dense QAT (30.7B active, ~same memory) + distillation; see TASK-DATA-COACHHARVEST."
task_type: fix
created: 2026-06-08T00:00:00Z
updated: 2026-06-18T16:15:00Z
priority: low   # deferred 2026-06-18 (was: high) — see banner
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
falsifier: "Run 14 of `guardkit autobuild feature FEAT-AOF ... --coach-model gemma4:26b --task-timeout 4800 --sdk-timeout 3600` produces ≥1 Coach turn that CONVERGES — emits a valid fenced-JSON verdict (task_id/turn/decision present) and finishes WITHIN the per-invocation SDK timeout — across ≥4 Coach turns, with ≥80% emitting valid required fields. PRIMARY metric is convergence (Coach completes), not emission-rate alone; run 13 timed out at the 2340s SDK timeout before emitting anything. NOTE: the wall is the per-invocation --sdk-timeout (run 13: base 1200 × 1.5 task-work × 1.3 complexity = 2340s), NOT --task-timeout (already 4800 in run 13). --sdk-timeout 3600 is the MAX (MAX_SDK_TIMEOUT) and gives 60 min/turn. If it still times out at 3600s, the substrate is the wall → toolless verdict-synthesis call or Path 2."
---

# Task: Tighten Coach prompt template for schema-correct fenced-JSON emission

> **DEFERRED 2026-06-18 (priority → low).** Path 1B (prompt-tightening) was
> **falsified by run 14** (more time + a decisive prompt made gemma4:26b *worse*,
> not better — 49,720 chars of reasoning, no verdict). The run-14 analysis
> recommended escalating to a **Gemma 4 31B dense** substrate, but the operator's
> **2026-06-18 investigation evaluated 31B and rejected it** ("slower, no better
> than the gemma4:26b MoE"). Both fix-approaches in this thread (GBNF / prompt /
> 31B) are therefore exhausted. The settled resolution is **gemma4:26b + the
> COACHSF01 safety net**, which runs green in practice (FEAT-9DDE, FEAT-FAUD). If
> coach reliability later becomes a felt pain, the live forward option is a
> **toolless grammar-constrained verdict-synthesis call** (see TASK-OPS-COACHGRAMMAR
> banner), or the deprioritized fine-tuned/distilled coach (TASK-DATA-COACHHARVEST).
> Recorded in the autobuild retro xref.

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

- [~] **AC-1 (implemented then REVERTED)**: The `## Verification Budget — Be Decisive` block (decisiveness + 3-field self-check) was added to `_build_coach_prompt` (commit `78fde34e`, designed via a judge-panel workflow), shipped in run 14 — and **reverted 2026-06-08 after run 14 falsified it** (see AC-4). Reverted to restore the clean baseline prompt (the one runs 12–13 used) so the **Gemma 4 31B QAT substrate A/B isolates the model variable** without a prompt confound; and because the self-check clause is the suspected cause of turn-1's 49,720-char loop. The design is preserved in git history (`78fde34e`) — re-add **decisiveness-only (drop the self-check)** later if the 31B benefits.

- [~] **AC-2 (REVERTED)**: `test_coach_decisiveness_prompt.py` (5 tests) was added then removed with the AC-1 revert.

- [ ] **AC-3 (smoke — caveated)**: A no-tools single-shot replay against gemma4-coach can sanity-check the new prompt renders + still produces a verdict, BUT **a single-shot smoke does NOT represent the tool-bound agentic Coach** (this is exactly the trap that made Path 1A's AC-4 look like it worked). Do not treat a green single-shot as proof. The real test is AC-4.

- [✗] **AC-4 (falsifier — run 14: FAILED)**: Run 14 ([log](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-14.md), [artifacts](../../../docs/state/TASK-REV-HMIG/run-14-artifacts/README.md)) ran with Path 1B + `--sdk-timeout 3600`. **Both Coach turns failed to converge** — no fenced JSON in either channel, COACHSF01 synthetic feedback both turns, `TIMEOUT_BUDGET_EXHAUSTED`, 0/3 tasks, 74m. Turn 1: 328 chars content + **49,720 chars reasoning_content** (9× run-12), ~45 min; turn 2: 1155 + 1347 chars, ~18 min, still no verdict. **Decisive finding: more time made it WORSE** — the 3600s budget let the Coach ramble 9× longer without converging, so the wall is NOT time, NOT prompt, NOT grammar — it's the **substrate** (3.8B-active gemma4-26B-A4B can't organise agentic reasoning to a verdict). **Possible backfire**: the self-check instruction ("before emitting, re-read and verify the 3 fields") may have *induced* the turn-1 self-review explosion (run-14-artifacts H-A) — "the cure may be worse than the disease". Net: prompt-tightening is exhausted. → Escalate to a substrate change (Gemma 4 31B dense QAT + distillation, [TASK-DATA-COACHHARVEST](../../TASK-DATA-COACHHARVEST-harvest-claude-era-coach-training-data.md)), not the toolless-synthesis tweak.

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
