# Agent Factory Pattern

`create_agent()` vs `create_deep_agent()` decision and the `create_restricted_agent()` wrapper for tool-safe agent creation.

Fixes prevented: TRF-003, TRF-012, TRF-016, TRF-017 (tool leakage). TASK-REV-R2A1 (dual system messages).

## The Core Decision: create_agent() vs create_deep_agent()

| Factory Function | Middleware Injection | Tool Count | Use Case |
|-----------------|---------------------|------------|----------|
| `create_agent()` | Only what you explicitly pass | Your tools only | Adversarial agents (Player, Coach) |
| `create_deep_agent()` | Unconditionally adds FilesystemMiddleware, TodoListMiddleware, SubAgentMiddleware | Your tools + 8-10 framework tools | General-purpose agents needing filesystem access |

**SDK source validation** (DeepAgents 0.4.12, `deepagents/graph.py` lines 249-267):

`create_deep_agent()` unconditionally builds this middleware stack:

```python
deepagent_middleware = [
    TodoListMiddleware(),              # adds: write_todos
    FilesystemMiddleware(backend=...),  # adds: ls, read_file, write_file, edit_file, glob, grep, execute
    SubAgentMiddleware(backend=...),    # adds: task
    create_summarization_middleware(model, backend),
    AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
    PatchToolCallsMiddleware(),
]
```

There is NO way to disable these within `create_deep_agent()`. Passing `tools=[]` only controls user-provided tools; middleware tools are always added.

Source: TASK-REV-32D2 Section 1.1, SDK source validation.

## create_restricted_agent() Wrapper

For agents that need memory injection but NOT filesystem tools:

```python
def create_restricted_agent(
    model, tools, system_prompt, *, memory=None, allowed_tools=None,
):
    """Create an agent WITHOUT FilesystemMiddleware injection.

    Uses create_agent() directly. Adds MemoryMiddleware for file reading
    if memory paths are provided. Asserts tool inventory at factory exit.
    """
    middleware = []
    if memory is not None:
        backend = FilesystemBackend(root_dir=".")
        middleware.append(MemoryMiddleware(backend=backend, sources=memory))

    agent = create_agent(
        model=model,
        tools=list(tools),
        system_prompt=system_prompt,
        middleware=middleware if middleware else None,
    )

    if allowed_tools is not None:
        assert_tool_inventory(agent, allowed_tools)

    return agent
```

Source: `lib/factory_guards.py`

## Tool Allowlisting at Factory Exit

Every factory function declares its expected tools and asserts them at creation:

```python
PLAYER_ALLOWED_TOOLS: set[str] = {"search_data"}
COACH_ALLOWED_TOOLS: set[str] = set()  # Coach: evaluation only, no tools

def create_player_agent(model, tools, system_prompt, *, memory=None):
    agent = create_restricted_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        memory=memory,
        allowed_tools=PLAYER_ALLOWED_TOOLS,
    )
    return agent
```

The `assert_tool_inventory()` call at factory exit catches tool leakage before the agent is ever used:

```python
def assert_tool_inventory(agent, expected_tools):
    actual_tools = {getattr(t, "name", str(t)) for t in agent.tools}
    if actual_tools != expected_tools:
        unexpected = actual_tools - expected_tools
        missing = expected_tools - actual_tools
        raise ToolLeakageError(f"Tool inventory mismatch: unexpected={sorted(unexpected)}, missing={sorted(missing)}")
```

Source: `scaffold/agent_factory.py.template`, `lib/factory_guards.py`

## ainvoke() Contract (TASK-REV-R2A1)

`create_agent()` unconditionally prepends `system_prompt` on every `ainvoke()` call (langchain/agents/factory.py:1270-1271). Input messages must use only `user` or `assistant` roles. Never pass `system` messages.

```python
# At every ainvoke() call site:
assert_no_system_messages(input_data)
result = await agent.ainvoke(input_data)
```

Violation causes dual system messages, triggering vLLM HTTP 400 Bad Request.

## When to Use create_agent()

- Player agents (need domain tools only, no filesystem)
- Coach agents (need zero tools)
- Any agent in an adversarial cooperation system
- Agents where tool inventory must be exactly controlled

## When to Use create_deep_agent()

- General-purpose agents that need filesystem access (ls, read, write, edit)
- Agents that need TodoListMiddleware for task tracking
- Agents that spawn sub-agents (SubAgentMiddleware)
- Single-agent systems where tool separation is not a concern

## When NOT to Use

- Do NOT use `create_deep_agent()` for adversarial agents — it injects 8-10 unwanted tools that bypass the orchestrator-gated writes invariant
- Do NOT rely on `tools=[]` to prevent middleware tool injection — it only controls user-provided tools
