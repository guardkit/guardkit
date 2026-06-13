---
id: TASK-FIX-COACHREASON01
title: Add GUARDKIT_COACH_SYNTHESIS_DISABLE_THINKING — suppress gemma4-31b reasoning tax that reasoning_budget can't (server ignores it)
status: completed
task_type: fix
created: 2026-06-13T12:40:00Z
updated: 2026-06-13T12:55:00Z
completed: 2026-06-13T12:55:00Z
state_transition_reason: "Implemented + unit-verified in guardkitfactory (commit 7526b55): default-off env var injects chat_template_kwargs={enable_thinking:false} into the toolless synthesis extra_body; 7 new tests, 21/21 synthesis tests green. Live probe confirmed the server honours it (reasoning_content 147->0) while reasoning_budget=0 is ignored (still 3041 chars)."
priority: high
complexity: 3
related: [TASK-PERF-COACHTURNBUDGET, TASK-ARCH-COACHSPLIT, FEAT-9DDE]
implementation_mode: task-work
tags: [autobuild, coach, reasoning, gemma, langgraph-harness, latency, llama-swap]
---

# Task: Disable the gemma4-31b Coach reasoning tax via the chat-template toggle

## Why this task exists

FEAT-9DDE run 3 (2026-06-13) hit a **~31-minute Coach turn** (turn 1, TSJ-001).
gemma4-31b on the GB10 llama-swap endpoint serves in reasoning mode
(`reasoning_budget=unset` in the COACHSPLIT log), so it spent its `max_tokens`
budget generating `reasoning_content` before the grammar-constrained verdict.
The pre-existing Lever-2 knob (`GUARDKIT_COACH_SYNTHESIS_REASONING_BUDGET`,
TASK-PERF-COACHTURNBUDGET) carried a *deferred* AC-4 falsifier: was the llama.cpp
`reasoning_budget` wire-field actually honoured on the GB10? This run answered it.

**Empirical finding (the deferred falsifier, now resolved):**

| toggle | reasoning_content | completion tokens |
|---|---|---|
| baseline | 147 chars | 47 |
| `reasoning_budget: 0` | **3041 chars** (IGNORED) | 776 |
| `chat_template_kwargs.enable_thinking=false` | **0 chars** ✅ | 2 |

The server ignores `reasoning_budget`; it honours the transformers/vLLM/jinja
chat-template kwarg `enable_thinking=false`.

## What was done

- guardkitfactory `langgraph_harness.py`: added default-off env var
  `GUARDKIT_COACH_SYNTHESIS_DISABLE_THINKING`; when truthy
  (`1`/`true`/`yes`/`on`) the toolless-synthesis `extra_body` carries
  `chat_template_kwargs={"enable_thinking": false}` alongside `grammar` /
  `reasoning_budget` (orthogonal — both can be set; each server honours
  whichever it supports). Default-off = unchanged behaviour.
- Helper `_synthesis_disable_thinking()`; COACHSPLIT log line now reports
  `disable_thinking=…`.
- 7 new tests in `tests/harness/test_langgraph_harness_synthesis.py`; 21/21 green.
- Committed: guardkitfactory `7526b55`.

## How to use

Add to the autobuild recipe when the Coach model serves in reasoning mode:

```bash
GUARDKIT_COACH_SYNTHESIS_DISABLE_THINKING=1 \
GUARDKIT_HARNESS=langgraph OPENAI_BASE_URL=… OPENAI_API_KEY=… \
  guardkit autobuild feature FEAT-XXX --model … --coach-model gemma4-31b …
```

## Follow-on (optional, not blocking)

The handoff's separate "pin gemma models out of reasoning mode on llama-swap"
server-side fix is still valid (it would help every consumer, not just the
Coach), but it requires GB10 server access and a model reload; the client-side
toggle here is the substrate-portable fix and needs no server change.

## Evidence
- Result writeup: `docs/retro/coder-player-experiment-RESULT-2026-06-13.md` §"Finding 4".
- Commit: guardkitfactory `7526b55`.
</content>
