---
id: TASK-FIX-CHO01
title: DeepAgents writes conversation history to read-only `/conversation_history/` host root
status: completed
previous_state: backlog
state_transition_reason: "Superseded by two guardkitfactory-side tasks that together deliver F11's fix with a better factoring than this GuardKit-side framing anticipated. TASK-HMIG-002R-SUMM-ROOT addressed the offload-path symptom (CompositeBackend wrapping LocalShellBackend, exposes artifacts_root=<worktree> so the summarization middleware computes <worktree>/conversation_history/ instead of literal /conversation_history/). TASK-HMIG-002R-MODEL-PROFILE addressed the root sizing question (model_config.py with MODEL_CONTEXT_WINDOWS registry + _resolve_model_for_invoke attaching model.profile.max_input_tokens — switches deepagents' summarization from no-profile fallback ('tokens', 170000) to ('fraction', 0.85), firing at ~111k tokens inside qwen36-workhorse's 131k window). Both landed in guardkitfactory 2026-06-05 with 92 passing tests, 0 failures. The selector.py-keeps-the-bridge invariant preserved (no GuardKit-side changes needed). The deferred message-count belt-and-braces trigger is documented in model_config.py's module docstring for future addition."
completed_at: 2026-06-05T08:00:00Z
completed_by: operator
superseded_by:
  - TASK-HMIG-002R-SUMM-ROOT   # guardkitfactory: offload-path fix
  - TASK-HMIG-002R-MODEL-PROFILE # guardkitfactory: model.profile sizing
task_type: bug
created: 2026-06-04T21:00:00Z
updated: 2026-06-05T08:00:00Z
priority: critical
complexity: 4
deadline: 2026-06-15
parent_review: TASK-REV-HMIG
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
implementation_mode: task-work
intensity: standard
effort_hours: 2
# blocks: cleared on supersession — TASK-HMIG-010 is unblocked w.r.t. F11.
# Original block reference (historical): TASK-HMIG-010
falsifier: "After landing, the test-orchestrator specialist invocation under qwen36-workhorse does NOT log `Failed to offload conversation history to /conversation_history/...` and does NOT hit `request (NNNNNN tokens) exceeds the available context size (131072 tokens)` for a normal-sized task. The summarization middleware either (a) successfully writes to a writable per-worktree directory, or (b) operates in a no-offload mode that caps message history without filesystem I/O."
tags:
  - autobuild
  - langgraph-migration
  - bugfix
  - deepagents
  - guardkitfactory
  - sibling-of-novmode
---

# Task: DeepAgents conversation-history offload writes to read-only host root

## Description

Surfaced by TASK-HMIG-010 run 2 (2026-06-04T19:33, see [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-2.md`](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-2.md) line 342). The DeepAgents summarization middleware attempts to offload conversation history to an absolute host-root path `/conversation_history/session_*.md`, which fails with `[Errno 30] Read-only file system: '/conversation_history'`. Because the offload fails, the middleware can't trim the running message history; the next LLM call accumulates the full conversation (569,665 tokens against qwen36-workhorse's 131,072 context window) and llama-swap returns HTTP 400 `exceed_context_size_error`.

This is a **guardkitfactory / DeepAgents-side configuration issue**. The DeepAgents summarization middleware (`deepagents/middleware/summarization.py`) constructs offload paths from a config that defaults to (or has been left at) host root `/conversation_history/`. The LangGraph harness in guardkitfactory needs to either:
- (a) Point the offload directory at a writable per-worktree path (e.g. `<worktree>/.guardkit/conversation_history/`), OR
- (b) Disable offloading and configure a message-count or token-count cap on the summarization middleware directly.

This is a **sibling-of-NOVMODE** finding. Recall TASK-HMIG-002R-NOVMODE (referenced in TASK-HMIG-009A) flipped `virtual_mode=False` to fix path-doubling — another instance of DeepAgents writing paths the host filesystem couldn't service correctly. F11 is the same shape: a default DeepAgents configuration that assumes a virtualised filesystem but lands on a real one.

Recorded as **F11** in [`docs/state/TASK-REV-HMIG/feature-run-incidents.md`](../../../docs/state/TASK-REV-HMIG/feature-run-incidents.md).

## Symptom

Run-2 stdout log lines 342–350:

```
WARNING:deepagents.middleware.summarization:Failed to offload conversation history
  to /conversation_history/session_7b9e811b.md (60 messages):
  Error writing file '/conversation_history/session_7b9e811b.md':
  [Errno 30] Read-only file system: '/conversation_history'
ERROR:deepagents.middleware.summarization:Offloading conversation history to backend
  failed during summarization. Older messages will not be recoverable.
[... 8 LLM calls succeeding with growing context ...]
WARNING:guardkit.orchestrator.specialist_invocations:run_specialist(test-orchestrator)
  failed for TASK-FIX-IA03: ...
  LangGraphHarnessError: ... model='openai:qwen36-workhorse':
  Error code: 400 - {'error': {'code': 400,
    'message': 'request (569665 tokens) exceeds the available context size (131072 tokens)...',
    'type': 'exceed_context_size_error',
    'n_prompt_tokens': 569665, 'n_ctx': 131072}}
```

## Why it matters

Once TASK-FIX-LGFM2 lands (F10 fix), the main Player path will route correctly. But every non-trivial task will then trip F11 the moment the test-orchestrator (or any specialist with non-tiny conversation history) accumulates enough messages. **F10 and F11 are sequential blockers**: F10 unblocks the main Player; F11 unblocks the specialists.

For qwen36-workhorse specifically, the 131k context window is much smaller than the Claude Sonnet baseline (~200k). Even with successful offloading, the summarization cadence may need tuning for the smaller window. But the immediate fix is to make offloading work at all.

## Acceptance Criteria

- [ ] AC-001: Identify the DeepAgents summarization middleware configuration in guardkitfactory's LangGraph harness setup. Likely sites: `guardkitfactory.harness.langgraph_harness.LangGraphHarness` or its `build_autobuild_backend(cwd)` factory.
- [ ] AC-002: Choose remediation strategy:
  - **(a)** Point offload directory at `<worktree>/.guardkit/conversation_history/` (writable, ephemeral, cleaned up with worktree). RECOMMENDED.
  - **(b)** Disable offload + set hard message-count cap (~20 messages) on the summarization middleware. Simpler but loses long-conversation context.
  - **(c)** Both: writable path AS WELL AS a smaller cap to reduce per-LLM-call prompt size for small-context models like qwen36-workhorse.
- [ ] AC-003: Implement chosen strategy. Likely a guardkitfactory change; track parallel guardkitfactory task if needed.
- [ ] AC-004: Live smoke (HMIG-010 run 3, post-F10+F11): test-orchestrator specialist runs to completion (or fails with a substrate-quality finding, NOT a filesystem/context-overflow finding).
- [ ] AC-005: Regression test: assert that the LangGraph harness configures the summarization middleware with a writable offload directory (or with offload disabled and a configured cap).

## Implementation Notes

- This sibling-of-NOVMODE fix likely lives in `guardkitfactory.harness.langgraph_harness.LangGraphHarness.__init__` or wherever DeepAgents middleware is composed. The work mirrors the NOVMODE diff shape.
- If the fix needs to land in DeepAgents itself (not just guardkitfactory's wrapper), file the upstream contribution but keep the guardkitfactory workaround (conftest-style override) shipping first.
- For qwen36-workhorse's 131k context, a 20-message cap is a reasonable starting heuristic. The test-orchestrator's prompt at the failure was 569k tokens / ~60 messages → roughly 10k tokens per message average. 20 messages × 10k = 200k tokens (overshoots 131k); 12 messages × 10k = 120k (fits). Operator may want to A/B this against Sonnet's larger window once cross-model parity matters.
- The `Older messages will not be recoverable` warning is acceptable; resumability lives in the orchestrator's session_id path, not in the DeepAgents conversation log.

## References

- Run-2 failure log: [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-2.md`](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-2.md) (lines 342, 346–350)
- NOVMODE sibling: TASK-HMIG-002R-NOVMODE (referenced in [TASK-HMIG-009A](../../completed/TASK-HMIG-009A-partial-canary-no-preloop-backlog-tasks.md))
- DeepAgents middleware: `deepagents/middleware/summarization.py` (line 1045 in the run-2 traceback)
- guardkitfactory harness: `guardkitfactory.harness.langgraph_harness.LangGraphHarness` and its `build_autobuild_backend(cwd)` factory
- Blocked task: [TASK-HMIG-010](../../in_progress/TASK-HMIG-010-full-feature-autobuild-validation.md)
- Sibling blocker: [TASK-FIX-LGFM2](TASK-FIX-LGFM2-inline-implement-model-threading.md)

## Notes

If TASK-FIX-LGFM2 lands first and a re-run is attempted before F11 is fixed, expect the run to fail at the test-orchestrator specialist (now with a real model name routing to llama-swap, but immediately tripping the context overflow). That outcome would empirically confirm F11's reproducibility and is acceptable as a debugging step — but for clean falsifier evaluation, both fixes should land before the AC-008 verdict run.
