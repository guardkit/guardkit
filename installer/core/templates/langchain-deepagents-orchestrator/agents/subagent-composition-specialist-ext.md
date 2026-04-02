# Subagent Composition Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **subagent-composition-specialist** agent.

**Core documentation**: See [subagent-composition-specialist.md](./subagent-composition-specialist.md)

---

## Related Templates

### Primary

- `templates/other/agents/agents.py.template` — Core template defining all four factory functions (`implementer_subagent`, `evaluator_subagent`, `builder_async_subagent`, `create_orchestrator`). Contains the canonical patterns for constructing `SubAgent` and `AsyncSubAgent` TypedDicts, validating model strings, injecting runtime date via `.format(date=today)`, and passing tool lists to `create_deep_agent(subagents=[...])`.

- `templates/other/other/agent.py.template` — Entrypoint template showing how the assembled graph is wired: reads `orchestrator-config.yaml` for model selection, loads `domains/{domain}/DOMAIN.md` for domain context, then calls `create_orchestrator()`. Demonstrates the module-level `agent` variable pattern required by `langgraph.json` and graceful fallback defaults when config or domain files are missing.

- `templates/other/prompts/implementer_prompts.py.template` — Shows the `{date}` placeholder convention used in system prompts. Every subagent factory must call `PROMPT.format(date=today)` before placing the result in the `system_prompt` field of the TypedDict, ensuring temporal grounding without hardcoded dates.

### Supporting

- `templates/other/tools/orchestrator_tools.py.template` — Defines the four tools (`analyse_context`, `plan_pipeline`, `execute_command`, `verify_output`) that are assigned to the implementer subagent. Shows the `@tool(parse_docstring=True)` decorator convention and the requirement that all tools return strings and never raise exceptions.

- `templates/other/agents/__init__.py.template` — Package exports for the agents module. Confirms the public API surface: `create_orchestrator`, `implementer_subagent`, `evaluator_subagent`, `builder_async_subagent` must all be re-exported from `__init__.py`.

- `templates/other/prompts/orchestrator_prompts.py.template` — Demonstrates the two-placeholder pattern (`{date}` and `{domain_prompt}`) used when a subagent system prompt requires both temporal and domain-specific injection at `create_orchestrator()` call time.

## Code Examples

### Sync SubAgent with Tools (`implementer_subagent`)

Derived from `templates/other/agents/agents.py.template` lines 32-64.

```python
# DO: validate model, inject date, copy tool list
def implementer_subagent(model: str) -> SubAgent:
    if not model or not isinstance(model, str):
        raise ValueError(f"model must be a non-empty string, got: {model!r}")

    today = datetime.date.today().isoformat()
    prompt = IMPLEMENTER_SYSTEM_PROMPT.format(date=today)

    return SubAgent(
        name="implementer",
        description=(
            "Focused execution agent that implements plans by writing code, "
            "creating files, and running commands."
        ),
        system_prompt=prompt,
        model=model,
        tools=list(_ORCHESTRATOR_TOOLS),  # copy, not shared reference
    )
```

```python
# DON'T: skip validation, hardcode date, share mutable tool list
def implementer_subagent_bad(model: str) -> SubAgent:
    return SubAgent(
        name="implementer",
        description="Execution agent.",
        system_prompt=IMPLEMENTER_SYSTEM_PROMPT,  # missing .format(date=today)
        model=model,                              # unvalidated
        tools=_ORCHESTRATOR_TOOLS,               # shared reference
    )
```

**Key rules from the template**:
- Guard clause first: `if not model or not isinstance(model, str): raise ValueError(...)`
- Always call `.format(date=today)` on the prompt before storing it
- Use `list(_ORCHESTRATOR_TOOLS)` to copy the list, preventing cross-agent mutation

---

### Sync SubAgent WITHOUT Tools (`evaluator_subagent`)

Derived from `templates/other/agents/agents.py.template` lines 67-98.

```python
# DO: pass tools=[] explicitly for a tool-free subagent
def evaluator_subagent(model: str) -> SubAgent:
    if not model or not isinstance(model, str):
        raise ValueError(f"model must be a non-empty string, got: {model!r}")

    today = datetime.date.today().isoformat()
    prompt = EVALUATOR_SYSTEM_PROMPT.format(date=today)

    return SubAgent(
        name="evaluator",
        description=(
            "Objective quality-assurance agent that reviews completed work "
            "against acceptance criteria and returns a structured JSON verdict. "
            "Has no tools — evaluation is purely reasoning-based."
        ),
        system_prompt=prompt,
        model=model,
        tools=[],  # explicit empty list signals intentional no-tools design
    )
```

---

### Async SubAgent for Remote LangGraph (`builder_async_subagent`)

Derived from `templates/other/agents/agents.py.template` lines 101-131.

```python
# DO: start from AsyncSubAgent TypedDict, conditionally add url
def builder_async_subagent(
    url: str | None = None,
    graph_id: str = "builder",
) -> AsyncSubAgent:
    spec: dict[str, Any] = AsyncSubAgent(
        name="builder",
        description=(
            "Non-blocking async subagent for long-running build and deployment "
            "tasks. Connects to a remote LangGraph deployment."
        ),
        graph_id=graph_id,
    )
    if url is not None:
        spec["url"] = url  # only set url when explicitly provided
    return spec  # type: ignore[return-value]
```

---

### Assembling the Graph with `create_deep_agent()`

Derived from `templates/other/agents/agents.py.template` lines 134-187.

```python
# DO: build each subagent via its factory, pass as list to create_deep_agent
def create_orchestrator(
    reasoning_model: str,
    implementation_model: str,
    domain_prompt: str,
) -> CompiledStateGraph:
    if not reasoning_model or not isinstance(reasoning_model, str):
        raise ValueError(f"reasoning_model must be a non-empty string, got: {reasoning_model!r}")
    if not implementation_model or not isinstance(implementation_model, str):
        raise ValueError(f"implementation_model must be a non-empty string, got: {implementation_model!r}")

    today = datetime.date.today().isoformat()
    system_prompt = ORCHESTRATOR_SYSTEM_PROMPT.format(
        date=today,
        domain_prompt=domain_prompt,
    )

    subagents = [
        implementer_subagent(model=implementation_model),
        evaluator_subagent(model=reasoning_model),
        builder_async_subagent(),
    ]

    return create_deep_agent(
        model=reasoning_model,
        tools=list(_ORCHESTRATOR_TOOLS),
        system_prompt=system_prompt,
        subagents=subagents,
        memory=["./AGENTS.md"],
        skills=None,
        context_schema=None,
    )
```

**Observation**: the orchestrator uses `reasoning_model` for its own model AND for the evaluator. The implementer uses `implementation_model` (typically a cheaper/faster model). Assign cost-optimised models to execution roles and reasoning-grade models to evaluation and coordination roles.

---

## Complete create_orchestrator() Assembly

Shows all three subagents wired together with create_deep_agent:

```python
import datetime
from deepagents import AsyncSubAgent, SubAgent, create_deep_agent
from prompts import ORCHESTRATOR_SYSTEM_PROMPT
from tools import analyse_context, execute_command, plan_pipeline, verify_output

_ORCHESTRATOR_TOOLS = [analyse_context, plan_pipeline, execute_command, verify_output]

def create_orchestrator(
    reasoning_model: str,
    implementation_model: str,
    domain_prompt: str,
    builder_url: str | None = None,
):
    # Validate both models before constructing anything
    if not reasoning_model or not isinstance(reasoning_model, str):
        raise ValueError(f"reasoning_model invalid: {reasoning_model!r}")
    if not implementation_model or not isinstance(implementation_model, str):
        raise ValueError(f"implementation_model invalid: {implementation_model!r}")

    today = datetime.date.today().isoformat()
    system_prompt = ORCHESTRATOR_SYSTEM_PROMPT.format(
        date=today, domain_prompt=domain_prompt,
    )

    subagents = [
        implementer_subagent(model=implementation_model),  # sync, with tools
        evaluator_subagent(model=reasoning_model),          # sync, no tools
        builder_async_subagent(url=builder_url),            # async, optional url
    ]

    return create_deep_agent(
        model=reasoning_model,
        tools=list(_ORCHESTRATOR_TOOLS),  # copy to prevent mutation
        system_prompt=system_prompt,
        subagents=subagents,
        memory=["./AGENTS.md"],
        skills=None,
        context_schema=None,
    )
```

## AsyncSubAgent Transport Patterns

Local development (no remote server needed):
```python
# url omitted → ASGI local transport (default, safe for dev)
builder = builder_async_subagent()
# Result: AsyncSubAgent(name="builder", description=..., graph_id="builder")
```

Remote deployment (LangGraph server running):
```python
# url provided → HTTP transport to remote LangGraph
builder = builder_async_subagent(
    url="https://my-langgraph-server.example.com",
    graph_id="builder",
)
# Result: AsyncSubAgent(name="builder", ..., graph_id="builder", url="https://...")
```

## Cost Optimization Guide

The two-model architecture separates reasoning from execution:

| Role | Model | Rationale |
|------|-------|-----------|
| Orchestrator | `reasoning_model` (e.g., claude-sonnet) | Coordination requires strong reasoning |
| Evaluator | `reasoning_model` (same as orchestrator) | Quality assessment needs equivalent reasoning |
| Implementer | `implementation_model` (e.g., claude-haiku) | Code execution is cheaper, high-volume |

This typically reduces token cost by 40-60% compared to using the reasoning model for all roles.

*This extended documentation is part of GuardKit's progressive disclosure system.*
