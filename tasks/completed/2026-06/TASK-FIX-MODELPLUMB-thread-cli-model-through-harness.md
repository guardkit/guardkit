---
id: TASK-FIX-MODELPLUMB
title: Thread CLI --model through AutoBuild orchestrator to harness construction (LangGraph blocker)
task_type: implementation
status: completed
created: 2026-06-02T20:50:00Z
updated: 2026-06-02T20:55:00Z
completed: 2026-06-02T20:55:00Z
priority: high
complexity: 2
effort_hours: 0.5
parent_review: TASK-REV-HM09
parent_task: TASK-HMIG-009A
feature_id: FEAT-HMIG
parent_feature: hmig-pre-canary-fixes
tags:
  - bug-fix
  - autobuild
  - harness
  - langgraph-migration
  - pre-canary-blocker
falsifier: "After fix: TASK-HMIG-009A AC-001D (LangGraph one-rep smoke against TASK-FIX-A7D3) reaches at least Coach turn 1 with non-empty files_modified, replacing the prior 'LangGraphHarnessError: failed to construct DeepAgent for role=coach model=None: function object has no attribute name' failure."
---

# Task: Thread CLI `--model` through to harness construction

## Problem

The `--model` flag on `guardkit autobuild task` was captured at the CLI layer (Click param at [`cli/autobuild.py:268-286`](../../../guardkit/cli/autobuild.py#L268-L286)) and **never plumbed anywhere**. It was displayed in the AutoBuild panel and otherwise dropped on the floor.

**Verified by grep**:
- No `model_name` / `player_model` / `coach_model` field on `AutoBuildOrchestrator` or `AgentInvoker`.
- `AgentInvoker.invoke_coach` (around line 1933) called `_invoke_with_role` without a `model=` kwarg, with a comment that read *"Model selection delegated to CLI default"* — but no mechanism actually carried the CLI default through.
- Same pattern in the legacy direct-SDK Player path (around line 1774) and in `run_specialist` ([specialist_invocations.py:199](../../../guardkit/orchestrator/specialist_invocations.py#L199)).
- Result: `_invoke_with_role`'s `model: Optional[str] = None` default propagated all the way to `select_harness(model=None)`, which passed `None` to `LangGraphHarness(model=None)`.

**Why SDK paths survived the bug**: claude-agent-sdk routes via `ANTHROPIC_BASE_URL` (env var); the model name in the request body is decorative for llama-swap's Anthropic-compat endpoint. So `model=None` was harmless on the SDK path.

**Why LangGraph paths failed**: `LangGraphHarness.invoke()` at [`langgraph_harness.py:147`](../../../../guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py) calls `create_deep_agent(model=self.model, ...)`. With `self.model=None`, DeepAgents tries to introspect a default model factory and crashes with `'function' object has no attribute 'name'`. Surfaced in AC-001D of TASK-HMIG-009A on 2026-06-02 — see [`docs/reviews/autobuild-migration/TASK-FIX-A7D3-langrapgh-run-1.md`](../../../docs/reviews/autobuild-migration/TASK-FIX-A7D3-langrapgh-run-1.md) for the full log.

## Root cause

Wiring oversight from TASK-HMIG-006. When the harness adapter was introduced, `select_harness(model=...)` was wired correctly at the only call site that already had a `model` parameter (`_invoke_with_role`), but the upstream chain (CLI → orchestrator → invoker → invocation method) was never extended to carry a CLI-supplied model name. The SDK path didn't expose the gap because it doesn't use the parameter.

## Fix (this task)

Thread `model` through four layers + add a defensive translator-layer fix:

1. **`guardkit/cli/autobuild.py`** — pass `model=model` to `AutoBuildOrchestrator(...)`.
2. **`guardkit/orchestrator/autobuild.py`** — add `model: Optional[str] = None` to `AutoBuildOrchestrator.__init__`; store as `self._model_name`; pass `model_name=self._model_name` to all three `AgentInvoker(...)` construction sites.
3. **`guardkit/orchestrator/agent_invoker.py`** — add `model_name: Optional[str] = None` to `AgentInvoker.__init__`; store as `self._model_name`; in `_invoke_with_role`, fall back to `self._model_name` when the caller's `model` kwarg is `None`. (This catches all downstream callers — `invoke_coach`, legacy direct-SDK Player, `run_specialist` — without needing to modify each one.)
4. **`guardkit/orchestrator/harness/selector.py`** — in `_translate_kwargs_for_langgraph`, auto-prefix `openai:` when the caller passes a bare alias (e.g. `qwen36-workhorse`) with no provider prefix. DeepAgents' `init_chat_model` requires a provider-prefixed string; the SDK path historically accepted bare aliases (decorative), so the translator owns the prefix transformation.

All five edits tagged with `# TASK-FIX-MODELPLUMB` comments for traceability.

## Acceptance Criteria

- [x] **AC-001** — `--model qwen36-workhorse` from `guardkit autobuild task` propagates to `AgentInvoker._model_name`. Verified via `inspect`.
- [x] **AC-002** — `_invoke_with_role` falls back to `self._model_name` when the caller's `model` kwarg is `None`. Verified via source inspection.
- [x] **AC-003** — `_translate_kwargs_for_langgraph` auto-prefixes bare aliases. Verified: `{'model': 'qwen36-workhorse'} → {'model': 'openai:qwen36-workhorse'}`; prefixed values and `None` pass through unchanged.
- [x] **AC-004** — All three `AgentInvoker(...)` construction sites in `autobuild.py` pass `model_name=self._model_name`. Verified via grep.
- [ ] **AC-005** — TASK-HMIG-009A AC-001D (LangGraph one-rep smoke) passes after fix. **Pending operator re-run**.

## Why this didn't surface earlier

- TASK-HMIG-009A's preflight AC-001B [OpenAI-compat] bypassed the orchestrator → harness → DeepAgents stack entirely (probed `:9000/v1/chat/completions` directly with httpx). That probe confirms wire-format compatibility but is structurally blind to construction-time wiring bugs in `LangGraphHarness` or `DeepAgents`. AC-001D was the integration gate designed to catch exactly this class of bug, and it did.

## Out of scope

- **TASK-HMIG-006.1/.2/.3** — three other SDK call sites still hardcode `claude_agent_sdk` and bypass the harness adapter entirely. AC-001D showed the Player still ran via SDK on a `GUARDKIT_HARNESS=langgraph` invocation because of the unmigrated `agent_invoker.py:5269+` task-work delegation path (TASK-HMIG-006.1's scope). That's a separate, larger refactor; this fix only addresses the model-plumbing gap.
- **Forwarding richer harness construction kwargs** to LangGraph (`allowed_tools`, `permission_mode`, etc.) — selector's translator deliberately drops these as out-of-scope for the Wave-2 skeleton; TASK-HMIG-002R is the right place.

## References

- Failure log: [`docs/reviews/autobuild-migration/TASK-FIX-A7D3-langrapgh-run-1.md`](../../../docs/reviews/autobuild-migration/TASK-FIX-A7D3-langrapgh-run-1.md)
- Working SDK run for comparison: [`docs/reviews/autobuild-migration/TASK-FIX-A7D3.md`](../../../docs/reviews/autobuild-migration/TASK-FIX-A7D3.md)
- Parent task: [TASK-HMIG-009A](../../backlog/hmig-pre-canary-fixes/TASK-HMIG-009A-partial-canary-no-preloop-backlog-tasks.md)
- LangGraphHarness source: [`../guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py`](../../../../guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py)
- Selector source: [`guardkit/orchestrator/harness/selector.py`](../../../guardkit/orchestrator/harness/selector.py)
