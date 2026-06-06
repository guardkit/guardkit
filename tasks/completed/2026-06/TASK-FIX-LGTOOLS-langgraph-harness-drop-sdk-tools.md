---
id: TASK-FIX-LGTOOLS
title: LangGraphHarness Wave-2 — drop caller-supplied SDK tool-name strings (use DeepAgents built-ins only)
task_type: implementation
status: completed
created: 2026-06-03T06:30:00Z
updated: 2026-06-03T06:35:00Z
completed: 2026-06-03T06:35:00Z
priority: high
complexity: 2
effort_hours: 0.5
parent_review: TASK-REV-HM09
parent_task: TASK-HMIG-009A
related_tasks:
  - TASK-FIX-MODELPLUMB   # Sibling pre-canary fix; landed 2026-06-02
  - TASK-HMIG-002R        # Where the FAITHFUL tool translation belongs
tags:
  - bug-fix
  - autobuild
  - harness
  - langgraph-migration
  - guardkitfactory
  - pre-canary-blocker
falsifier: "After fix: TASK-HMIG-009A AC-001D no longer fails with 'function object has no attribute name' inside DeepAgents → SubAgentMiddleware → langgraph.prebuilt.ToolNode. The harness's create_deep_agent call succeeds; any downstream failure is in a different layer (e.g. Coach LLM tool-surface mismatch, real network call to qwen36-workhorse)."
---

# Task: LangGraphHarness Wave-2 — drop caller-supplied SDK tool-name strings

> **NOTE**: This fix lives in the separate `../guardkitfactory/` repo, NOT in `guardkit-py`. The file is at `../guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py`. As of 2026-06-03 the change is applied locally; needs an upstream commit in guardkitfactory.

## Problem

`guardkit autobuild task` with `GUARDKIT_HARNESS=langgraph` fails inside Coach + specialist invocations with:

```
AttributeError: 'function' object has no attribute 'name'
```

Wrapped by LangGraphHarness as:

```
LangGraphHarnessError: failed to construct DeepAgent for role='coach'
model='openai:qwen36-workhorse': 'function' object has no attribute 'name'
```

Surfaced by TASK-HMIG-009A AC-001D on 2026-06-03 — see [`docs/reviews/autobuild-migration/TASK-FIX-A7D3-langraph-run-2.md`](../../../docs/reviews/autobuild-migration/TASK-FIX-A7D3-langraph-run-2.md).

The post-TASK-FIX-MODELPLUMB landing made the model parameter correct (`openai:qwen36-workhorse`, was `None`), but the same error pattern still fired — proving the model was not the root cause.

## Root cause (verified via direct DeepAgents probe)

The agent_invoker calls [`harness.invoke(tools=allowed_tools, ...)`](../../../guardkit/orchestrator/agent_invoker.py#L2878) where `allowed_tools` is a `list[str]` of SDK tool names (e.g. `["Read", "Bash", "Grep", "Glob"]`). LangGraphHarness forwards this `tools` parameter directly to `create_deep_agent(tools=tools)`. Downstream:

```
deepagents.create_deep_agent(tools=['Read', 'Bash', ...])
  → deepagents.middleware.subagents.SubAgentMiddleware._get_subagents
    → langchain.agents.create_agent(model, available_tools, ...)
      → langgraph.prebuilt.ToolNode(tools=available_tools)
        → for tool_ in tools: self._tools_by_name[tool_.name] = tool_
        → AttributeError on raw functions from DeepAgents' internal tool merge
```

Direct probe (with `OPENAI_BASE_URL`/`OPENAI_API_KEY` set):

| Call shape | Result |
|---|---|
| `create_deep_agent(model='openai:qwen36-workhorse', tools=['Read', 'Bash', 'Grep', 'Glob'], ...)` | **FAIL** with the exact AttributeError |
| `create_deep_agent(model='openai:qwen36-workhorse', tools=[], ...)` | **SUCCESS** — returns `CompiledStateGraph` |

The Wave-2 LangGraphHarness skeleton's tests at [`test_langgraph_harness.py:51, 274`](../../../../guardkitfactory/tests/harness/test_langgraph_harness.py) only ever pass `tools=[]` — the skeleton was never exercised end-to-end with a non-empty tools list, so the format mismatch went undetected until AC-001D.

## Wave-2 contract: tools=[] is the documented intent

Per the selector's own docstring at [`guardkit/orchestrator/harness/selector.py:56-58`](../../../guardkit/orchestrator/harness/selector.py#L56-L58):

> "allowed_tools — SDK ClaudeAgentOptions.allowed_tools field; **the LangGraph path receives its tool surface through ... DeepAgents' built-in tool set** (filesystem + execute + planning + sub-agents)."

The selector already drops `allowed_tools` from the harness construction kwargs. But `harness.invoke(tools=...)` still receives them. The fix codifies "Wave-2 drops the tools parameter" inside `LangGraphHarness.invoke()` itself, matching the documented intent.

## Fix

[`../guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py`](../../../../guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py):

- Add `import logging` + `logger = logging.getLogger(__name__)`.
- In `LangGraphHarness.invoke()`: emit a DEBUG-level trace when the caller supplies a non-empty `tools` list (so any consumer can see what got dropped), then pass `tools=[]` to `create_deep_agent` regardless. Comment cross-references TASK-HMIG-002R as the proper home for faithful SDK→LangGraph tool translation.

Tagged in the source with `# TASK-FIX-LGTOOLS`.

## Verification

```python
# With OPENAI_BASE_URL + OPENAI_API_KEY set:
harness = LangGraphHarness(model='openai:qwen36-workhorse')
stream = harness.invoke(
    prompt='Test', role='coach',
    tools=['Read', 'Bash', 'Grep', 'Glob'],  # SDK shape that crashed before
    cwd=Path.cwd(), timeout_seconds=60,
)
# → PASS — async_generator returned, construction path completes
#   without the AttributeError. (Awaiting first event would burn LLM
#   tokens for a real call; not part of this verification.)
```

## Acceptance Criteria

- [x] **AC-001** — `LangGraphHarness.invoke(tools=[...non-empty list of strings...])` no longer raises `AttributeError: 'function' object has no attribute 'name'` during `create_deep_agent` construction. Verified.
- [x] **AC-002** — DEBUG-level log line "LangGraphHarness Wave-2: dropping N caller-supplied tool(s)" fires when the caller passes non-empty tools, so the behaviour change is observable from the orchestrator logs.
- [x] **AC-003** — The Wave-2 skeleton tests at `test_langgraph_harness.py` continue to pass (they already use `tools=[]`, so behaviour is identical for them).
- [ ] **AC-004** — TASK-HMIG-009A AC-001D reaches at least one layer further (likely the Coach LLM execution itself, or a new failure at a different boundary). **Pending operator re-run**.
- [ ] **AC-005** — Upstream commit to guardkitfactory. Currently the fix is in the local working tree only.

## Expected next-layer failure (heads-up, not in scope)

Even with construction unblocked, the Coach (and specialists) will be invoked with DeepAgents' built-in tool surface (`read_file`, `write_file`, `execute`, etc.) instead of the SDK's surface (`Read`, `Write`, `Edit`, `Bash`, `Grep`, `Glob`). The Coach's system prompt was authored for the SDK surface. Three plausible next-layer outcomes:

1. Coach LLM adapts via DeepAgents' tool advertisement, calls the right built-ins, succeeds.
2. Coach LLM gets confused, calls non-existent tools (e.g. `Bash`), DeepAgents errors or the call no-ops.
3. Faithful tool-surface mapping is needed → TASK-HMIG-002R becomes the gate.

Document whatever happens; don't try to fix in this task.

## Out of scope

- **Faithful tool translation** (mapping `Read`/`Write`/`Bash` to LangChain `BaseTool` wrappers around the operator's preferred implementations) — TASK-HMIG-002R.
- **Fixing the Coach system prompt** to match DeepAgents' surface — separate concern, post-002R.
- **Modifying agent_invoker.py to pass tools=[] for LangGraph** — that would couple the orchestrator to harness type. The harness owns its translation contract; fix lives on the harness side.

## References

- Failure log (run 2): [`docs/reviews/autobuild-migration/TASK-FIX-A7D3-langraph-run-2.md`](../../../docs/reviews/autobuild-migration/TASK-FIX-A7D3-langraph-run-2.md)
- Sibling fix (model plumbing, prerequisite): [TASK-FIX-MODELPLUMB](./TASK-FIX-MODELPLUMB-thread-cli-model-through-harness.md)
- Parent task: [TASK-HMIG-009A](../../backlog/hmig-pre-canary-fixes/TASK-HMIG-009A-partial-canary-no-preloop-backlog-tasks.md)
- Future faithful fix: TASK-HMIG-002R (LangGraph backend + permissions + tool surface wiring)
- LangGraphHarness source: [`../../../../guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py`](../../../../guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py)
