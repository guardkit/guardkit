"""Factory guard utilities for tool allowlisting and input contract enforcement.

Prevents the tool leakage bugs (TRF-003, TRF-012, TRF-016, TRF-017) and
dual system message crashes (TASK-OR-006, TASK-REV-R2A1) that dominated
early factory runs. See docs/reference/model-compatibility.md for model-
specific quirks that interact with these guards.

ainvoke() message contract (TASK-REV-R2A1):
    create_agent() unconditionally prepends system_prompt on every ainvoke()
    call. Input messages must contain only ``user`` and ``assistant`` roles.
    Never pass ``system`` messages — use ``user`` role for additional
    instructions (e.g. retry reinforcement). Violation causes dual system
    messages which vLLM rejects with HTTP 400. Use assert_no_system_messages()
    to enforce this at the call site.

Dependencies: stdlib only (deepagents imports are lazy).
"""

from __future__ import annotations

from typing import Any, Sequence


class ToolLeakageError(Exception):
    """Raised when an agent's tool inventory does not match the expected set."""


def assert_tool_inventory(agent: Any, expected_tools: set[str]) -> None:
    """Post-factory assertion: verify agent has exactly the expected tools.

    Call this at factory exit (not just in tests) to catch tool leakage
    before the agent is used.

    Args:
        agent: The agent instance whose tools to check.
        expected_tools: Exact set of tool names the agent should have.

    Raises:
        ToolLeakageError: If unexpected or missing tools are detected,
            with a diff showing which tools were added/removed.
    """
    actual_tools = {getattr(t, "name", str(t)) for t in agent.tools}

    if actual_tools != expected_tools:
        unexpected = actual_tools - expected_tools
        missing = expected_tools - actual_tools
        parts = []
        if unexpected:
            parts.append(f"unexpected tools: {sorted(unexpected)}")
        if missing:
            parts.append(f"missing tools: {sorted(missing)}")
        raise ToolLeakageError(
            f"Tool inventory mismatch: {'; '.join(parts)}. "
            f"Expected: {sorted(expected_tools)}, "
            f"Actual: {sorted(actual_tools)}"
        )


def create_restricted_agent(
    model: Any,
    tools: Sequence[Any],
    system_prompt: str,
    *,
    memory: list[str] | None = None,
    allowed_tools: set[str] | None = None,
) -> Any:
    """Create an agent WITHOUT FilesystemMiddleware injection.

    WARNING: create_deep_agent() unconditionally injects FilesystemMiddleware
    (8 tools: ls, read_file, write_file, edit_file, glob, grep, execute, write_todos)
    Use create_restricted_agent() for agents that must have curated tool access.

    WARNING: create_agent() unconditionally prepends system_prompt to messages
    on every ainvoke() call (langchain/agents/factory.py:1270-1271).
    NEVER pass system role messages in ainvoke() input — the framework owns
    system message injection. Additional instructions must use user role.
    Violation causes dual system messages -> vLLM 400 Bad Request.
    See: TASK-REV-R2A1 root cause analysis.

    Args:
        model: The LLM model instance or provider:model string.
        tools: List of tools for the agent (curated, no filesystem tools).
        system_prompt: System prompt for the agent.
        memory: Optional list of memory file paths.
        allowed_tools: If provided, assert tool inventory after creation.

    Returns:
        A configured agent with only the specified tools.

    Raises:
        ToolLeakageError: If allowed_tools is set and the resulting
            agent has unexpected tools.
    """
    from langchain.agents import create_agent

    middleware: list[Any] = []
    if memory is not None:
        from deepagents.backends import FilesystemBackend
        from deepagents.middleware import MemoryMiddleware

        backend = FilesystemBackend(root_dir=".")
        middleware.append(MemoryMiddleware(backend=backend, sources=memory))

    kwargs: dict[str, Any] = {
        "model": model,
        "tools": list(tools),
        "system_prompt": system_prompt,
    }
    if middleware:
        kwargs["middleware"] = middleware

    agent = create_agent(**kwargs)

    if allowed_tools is not None:
        assert_tool_inventory(agent, allowed_tools)

    return agent


def assert_no_system_messages(input_data: dict) -> None:
    """Validate ainvoke() input has no system messages.

    create_agent() unconditionally prepends its system_prompt.
    Passing system messages in input causes duplication.
    See TASK-REV-R2A1 for root cause analysis.

    Args:
        input_data: The dict passed to agent.ainvoke().

    Raises:
        ValueError: If any message in input_data has role "system".
    """
    for msg in input_data.get("messages", []):
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
        if role == "system":
            raise ValueError(
                "ainvoke() input must not contain system messages. "
                "create_agent() prepends system_prompt automatically. "
                "Use 'user' role for additional instructions."
            )
