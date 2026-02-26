---
id: TASK-INV-0A11
title: Investigate vLLM Turn 1 cold start pattern — all direct-mode tasks waste first turn
status: completed
previous_state: in_review
task_type: review
created: 2026-02-26T00:00:00Z
updated: 2026-02-26T00:00:00Z
completed: 2026-02-26T00:00:00Z
completed_location: tasks/completed/TASK-INV-0A11/
priority: low
tags: [autobuild, vllm, investigation, prompt-engineering]
complexity: 5
parent_review: TASK-REV-BA6F
decision_required: true
---

# Task: Investigate vLLM Turn 1 cold start pattern

## Problem

Across all four GB10 vLLM autobuild runs, direct-mode tasks consistently produce **0/N criteria matches on Turn 1**. The Player generates generic summaries like "Add logging settings to core config module" instead of specific entries that match acceptance criteria text.

This wastes a full Player-Coach turn (5-10 minutes) on every direct-mode task.

## Evidence from Run 4 (TASK-REV-BA6F)

| Task | Mode | Turn 1 Criteria | Turn 2 Criteria |
|------|------|-----------------|-----------------|
| LOG-001 | direct | 0/7 | 5/7 |
| LOG-003 | task-work | 0/9 (empty) | 9/9 |
| LOG-004 | direct (synthetic) | 5/5 (ASPF-006 fallback) | — |
| LOG-005 | task-work | 0/6 (empty) | 6/6 |

The pattern is consistent: Turn 1 fails, Turn 2 succeeds after Coach feedback.

## Contrast with Anthropic API

The Anthropic API model (Claude) typically succeeds on Turn 1 for direct-mode tasks because it produces structured `completion_promises` that match by criterion ID, making text formatting irrelevant.

## Questions to Investigate

1. Is the Turn 1 failure due to the Player prompt not being clear enough about the expected report format?
2. Can few-shot examples in the Player prompt improve Turn 1 report quality?
3. Is this specific to Qwen3, or a general pattern with vLLM-served models?
4. Would adding the acceptance criteria text to the Player prompt (as reference) improve matching?
5. Is the cost of wasting Turn 1 acceptable, or should we invest in fixing it?

## Review Scope

1. Analyze Player prompt for direct mode — does it clearly specify the expected `requirements_met` format?
2. Compare Player output format between Anthropic and vLLM models
3. Propose 2-3 prompt engineering approaches to improve Turn 1 quality
4. Assess effort vs impact of each approach

## Acceptance Criteria

1. Root cause identified (prompt clarity, model capability, or both)
2. 2-3 proposed solutions with effort/impact assessment
3. Recommendation on whether to fix or accept the Turn 1 cost

---

## Investigation Findings

### AC-1: Root Cause — Prompt clarity (primary) + Model capability (secondary)

**Primary cause (~80%): `acceptance_criteria` parameter not passed in direct mode**

In `agent_invoker.py:2808-2810`, `_invoke_player_direct()` calls `_build_player_prompt()` WITHOUT passing the `acceptance_criteria` parameter:

```python
prompt = self._build_player_prompt(
    task_id, turn, requirements, feedback, context=context
)
# acceptance_criteria defaults to None → two critical prompt sections are empty
```

This omission causes the Player prompt to be missing:
- **Structured criteria list with IDs** (AC-001, AC-002, etc.) — `_build_player_prompt()` lines 1207-1213
- **Completion promises JSON example** — `_build_player_prompt()` lines 1217-1231

The parameter and prompt sections already exist and work correctly — they're just never invoked for direct mode.

**Secondary cause (~20%): Model capability gap**

Claude (Anthropic API) infers structured `completion_promises` from the generic instruction (line 1271) alone. Qwen3 (vLLM) cannot reliably do this without explicit examples and structured criteria IDs.

**Why Turn 2 succeeds**: Coach feedback explicitly lists missing criteria text, acting as the structured criteria list that was missing from the Turn 1 prompt.

### AC-2: Proposed Solutions

| # | Solution | Effort | Impact | Risk |
|---|----------|--------|--------|------|
| 1 | **Pass `acceptance_criteria` to `_build_player_prompt()` in direct mode** | Low (1-2h, ~20 LOC) | High — eliminates root cause | None — uses existing code path |
| 2 | Add few-shot completion_promises example to report format template | Low (1h) | Medium — improves format compliance | Slight prompt length increase |
| 3 | vLLM-specific structured output reinforcement preamble | Medium (4-6h) | Medium — general vLLM improvement | Prompt branching complexity |

**Solution 1 detail** — parse acceptance criteria from the task file in `_invoke_player_direct()` and pass as the existing `acceptance_criteria` kwarg:

```python
# In _invoke_player_direct(), before building prompt:
acceptance_criteria = None
task_file = self._find_task_file(task_id)
if task_file:
    task_data = TaskLoader._parse_task_file(task_file, task_id)
    raw_criteria = task_data.get("acceptance_criteria", [])
    if raw_criteria:
        acceptance_criteria = [
            {"id": f"AC-{i+1:03d}", "text": c}
            for i, c in enumerate(raw_criteria)
        ]

prompt = self._build_player_prompt(
    task_id, turn, requirements, feedback,
    acceptance_criteria=acceptance_criteria,  # ADD THIS
    context=context,
)
```

### AC-3: Recommendation — Fix it (Solution 1)

**Recommend: Implement Solution 1**, optionally complemented by Solution 2.

This is a clear bug, not a trade-off. The `acceptance_criteria` parameter exists, the prompt sections that use it work correctly, and `_invoke_player_direct()` simply never passes it. The fix is ~20 lines.

**Cost of not fixing**: Every direct-mode task wastes 5-10 minutes on a guaranteed-to-fail Turn 1. With 4-8 direct tasks per feature build, that's 20-80 wasted minutes per run.

**Key files**:
- `guardkit/orchestrator/agent_invoker.py:2808` — the call site to fix
- `guardkit/orchestrator/agent_invoker.py:1137-1281` — `_build_player_prompt()` (already correct)
- `guardkit/orchestrator/quality_gates/coach_validator.py:1472-1710` — Coach validation (no changes needed)
