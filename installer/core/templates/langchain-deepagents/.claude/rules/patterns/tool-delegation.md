# Tool Delegation Pattern

Tool separation contract enforcing that Player gets domain tools only, Coach gets NO tools, and the Orchestrator owns all write operations. Enforced at factory level by `validate_player_tools()` and `assert_tool_inventory()`.

Fixes prevented: TRF-003, TRF-012, TRF-016, TRF-017 (tool leakage).

## Tool Separation Contract

| Role | Allowed Tools | Enforcement |
|------|--------------|-------------|
| Player | Domain tools only (e.g. `search_data`) | `validate_player_tools()` + `assert_tool_inventory()` |
| Coach | NONE (empty `tools=[]`) | D5 invariant: no `tools` parameter in factory signature |
| Orchestrator | `write_output` (programmatic call, not an agent tool) | `OrchestratorWriteGate.attempt_write()` |

## validate_player_tools()

Basic guard: asserts `write_output` is not in the Player's tool list.

```python
def validate_player_tools(player_tools: list[Any]) -> None:
    """Assert that Player does not have write_output in its tool list."""
    tool_names = [getattr(t, "name", str(t)) for t in player_tools]
    assert "write_output" not in tool_names, (
        "TOOL SEPARATION VIOLATION: Player must NOT have write_output. "
        "Only the Orchestrator may call write_output after Coach acceptance."
    )
```

Called in the Player factory after constructing the tool list, before creating the agent.

Source: `scaffold/orchestrator_pattern.py.template`

## assert_tool_inventory() (Stronger Guard)

Exact-set comparison: asserts the agent has **exactly** the expected tools, catching both unexpected additions and missing tools.

```python
def assert_tool_inventory(agent: Any, expected_tools: set[str]) -> None:
    """Post-factory assertion: verify agent has exactly the expected tools."""
    actual_tools = {getattr(t, "name", str(t)) for t in agent.tools}
    if actual_tools != expected_tools:
        unexpected = actual_tools - expected_tools
        missing = expected_tools - actual_tools
        raise ToolLeakageError(
            f"Tool inventory mismatch: unexpected={sorted(unexpected)}, "
            f"missing={sorted(missing)}"
        )
```

This catches `FilesystemMiddleware`-injected tools that `validate_player_tools()` misses (e.g. `write_file`, `edit_file`, `execute`).

Source: `lib/factory_guards.py`

## D5 Invariant: Coach Has NO Tools

The Coach factory enforces zero tools by design:

```python
def create_coach(model, domain_prompt: str):
    """D5 invariant: No tools parameter in signature — Coach NEVER has tools."""
    system_prompt = COACH_SYSTEM_PROMPT + "\n\n" + domain_prompt
    return create_agent(
        model=model,
        tools=[],          # Explicit empty list
        system_prompt=system_prompt,
        middleware=middleware,
    )
```

The factory signature deliberately omits a `tools` parameter. The Coach evaluates only; it has no side effects.

Source: `agents/coach.py.template`

## assert_no_system_messages()

Validates that `ainvoke()` input contains no `system` role messages, enforcing the framework contract where `create_agent()` owns system message injection.

```python
def assert_no_system_messages(input_data: dict) -> None:
    """Validate ainvoke() input has no system messages."""
    for msg in input_data.get("messages", []):
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
        if role == "system":
            raise ValueError(
                "ainvoke() input must not contain system messages. "
                "create_agent() prepends system_prompt automatically."
            )
```

Call at every `ainvoke()` call site to prevent dual system messages (TASK-REV-R2A1).

Source: `lib/factory_guards.py`

## Enforcement Layers

Tool separation is enforced at three layers:

1. **Factory level**: `validate_player_tools()` + `assert_tool_inventory()` at agent creation
2. **SDK level**: Using `create_agent()` instead of `create_deep_agent()` to prevent middleware tool injection
3. **Runtime level**: `assert_no_system_messages()` at every `ainvoke()` call site

## When to Use

- Any multi-agent system where agents have different privilege levels
- Adversarial cooperation where one agent must not be able to write output
- Systems where tool leakage is a security or correctness concern
- Any factory that creates agents with curated tool access

## When NOT to Use

- Single-agent systems where tool separation is not relevant
- General-purpose agents that intentionally need all filesystem tools
- Prototyping where tool leakage is acceptable (but add guards before production)
