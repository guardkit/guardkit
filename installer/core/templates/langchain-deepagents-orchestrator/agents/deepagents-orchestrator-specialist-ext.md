# Deepagents Orchestrator Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **deepagents-orchestrator-specialist** agent.

**Core documentation**: See [deepagents-orchestrator-specialist.md](./deepagents-orchestrator-specialist.md)

---

## Related Templates

### Primary Templates

- `templates/other/other/agent.py.template` — Module-level entrypoint that loads `orchestrator-config.yaml`, reads `domains/{domain}/DOMAIN.md`, calls `create_orchestrator()`, and assigns the result to the `agent` variable required by `langgraph.json`. Demonstrates `_load_config`, `_load_domain_prompt`, `_build_agent` helper separation and `parse_known_args()` for LangGraph-safe CLI argument parsing.

- `templates/other/agents/agents.py.template` — Defines all four agent factory functions: `implementer_subagent()`, `evaluator_subagent()`, `builder_async_subagent()`, and `create_orchestrator()`. Demonstrates how to call `create_deep_agent(model=, tools=, system_prompt=, subagents=, memory=, skills=, context_schema=)` and how to build `SubAgent` and `AsyncSubAgent` TypedDicts with validated model strings.

- `templates/other/tools/orchestrator_tools.py.template` — Four `@tool(parse_docstring=True)` decorated functions (`analyse_context`, `plan_pipeline`, `execute_command`, `verify_output`) that return strings and never raise exceptions. Shows the correct import path (`from {{ProjectName}}.tools import tool`) and the pattern of wrapping all I/O in try/except with `logger.exception` fallback.

### Supporting Templates

- `templates/other/prompts/orchestrator_prompts.py.template` — `ORCHESTRATOR_SYSTEM_PROMPT` with `{date}` and `{domain_prompt}` placeholders. Shows the domain-agnostic prompt pattern where domain instructions are injected at runtime via `str.format`.

- `templates/other/prompts/evaluator_prompts.py.template` — `EVALUATOR_SYSTEM_PROMPT` built via a two-phase construction function: %-formatting to inject the verdict schema, then curly-brace escaping so `str.format(date=...)` works without colliding with JSON braces in the schema.

- `templates/other/prompts/implementer_prompts.py.template` — `IMPLEMENTER_SYSTEM_PROMPT` with `{date}` placeholder. Demonstrates the separation of implementation concerns: the Implementer executes plans but never self-evaluates.

## Code Examples

### Example 1: Wiring create_deep_agent in create_orchestrator

The central pattern in this template is assembling the orchestrator by passing all components into `create_deep_agent`. The result is a `CompiledStateGraph` exported as the module-level `agent`.

```python
# DO: Build each subagent via its factory function, then pass the list to create_deep_agent
from deepagents import AsyncSubAgent, SubAgent, create_deep_agent
from prompts import ORCHESTRATOR_SYSTEM_PROMPT
from tools import analyse_context, execute_command, plan_pipeline, verify_output
import datetime

_ORCHESTRATOR_TOOLS = [analyse_context, plan_pipeline, execute_command, verify_output]

def create_orchestrator(
    reasoning_model: str,
    implementation_model: str,
    domain_prompt: str,
) -> CompiledStateGraph:
    if not reasoning_model or not isinstance(reasoning_model, str):
        raise ValueError(f"reasoning_model must be a non-empty string, got: {reasoning_model!r}")

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

    graph = create_deep_agent(
        model=reasoning_model,
        tools=list(_ORCHESTRATOR_TOOLS),
        system_prompt=system_prompt,
        subagents=subagents,
        memory=["./AGENTS.md"],
        skills=None,
        context_schema=None,
    )
    return graph
```

```python
# DON'T: Pass raw model strings without validation, or omit skills/context_schema kwargs
graph = create_deep_agent(
    model="",              # Empty string will cause runtime errors
    tools=_ORCHESTRATOR_TOOLS,  # DON'T pass the original list — use list() to copy
    system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,  # DON'T forget to .format() the placeholders
    subagents=subagents,
    # Omitting memory, skills, context_schema is fine only if intentional
)
```

### Example 2: SubAgent and AsyncSubAgent factory functions

Each subagent role has its own factory function. Sync `SubAgent` specs include a model and optional tools; async `AsyncSubAgent` specs reference a remote graph by ID.

```python
# DO: Validate model argument, inject date into prompt, build SubAgent TypedDict
def implementer_subagent(model: str) -> SubAgent:
    if not model or not isinstance(model, str):
        raise ValueError(f"model must be a non-empty string, got: {model!r}")
    today = datetime.date.today().isoformat()
    prompt = IMPLEMENTER_SYSTEM_PROMPT.format(date=today)
    return SubAgent(
        name="implementer",
        description="Focused execution agent that implements plans...",
        system_prompt=prompt,
        model=model,
        tools=list(_ORCHESTRATOR_TOOLS),
    )

# DO: Evaluator has NO tools — pure reasoning only
def evaluator_subagent(model: str) -> SubAgent:
    if not model or not isinstance(model, str):
        raise ValueError(f"model must be a non-empty string, got: {model!r}")
    today = datetime.date.today().isoformat()
    prompt = EVALUATOR_SYSTEM_PROMPT.format(date=today)
    return SubAgent(
        name="evaluator",
        description="Objective QA agent...",
        system_prompt=prompt,
        model=model,
        tools=[],   # Intentionally empty — no tools for pure evaluation
    )

# DO: AsyncSubAgent for non-blocking long-running tasks; conditionally set url
def builder_async_subagent(url: str | None = None, graph_id: str = "builder") -> AsyncSubAgent:
    spec: dict = AsyncSubAgent(
        name="builder",
        description="Non-blocking async subagent for long-running build tasks.",
        graph_id=graph_id,
    )
    if url is not None:
        spec["url"] = url
    return spec
```

### Example 3: @tool decorator pattern and error handling

All orchestrator tools use `@tool(parse_docstring=True)`, return strings, and never raise exceptions to the caller.

```python
# DO: Use @tool(parse_docstring=True), return str, wrap all I/O in try/except
from {{ProjectName}}.tools import tool
import logging

logger = logging.getLogger(__name__)

@tool(parse_docstring=True)
def analyse_context(query: str, domain: str) -> str:
    """Read and summarise project context for a given query and domain.

    Args:
        query: A context query string, or a file path to read for context.
        domain: The domain to focus the analysis on.
    """
    try:
        query_path = Path(query)
        if query_path.is_file():
            content = query_path.read_text(encoding="utf-8")
            truncated = content[:4000] if len(content) > 4000 else content
            return f"Context analysis for domain '{domain}':\n{truncated}"
        return f"Context analysis for domain '{domain}':\nQuery: {query}"
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return f"Error analysing context: {exc}"
    except Exception as exc:
        logger.exception("Unexpected error in analyse_context")
        return f"Error analysing context: {exc}"

# DON'T: Raise exceptions from tools or use a bare @tool without parse_docstring=True
@tool
def bad_tool(query: str) -> str:
    # No parse_docstring — args not parsed from docstring
    result = Path(query).read_text()  # DON'T: will raise if file missing
    return result
```

### Example 4: Module-level agent entrypoint for langgraph.json

The `agent.py` entrypoint must export a module-level `agent` variable and use `parse_known_args()` to tolerate extra argv values injected by LangGraph.

```python
# DO: Use parse_known_args() so LangGraph server argv doesn't cause SystemExit
_arg_parser = argparse.ArgumentParser(description="DeepAgents orchestrator exemplar")
_arg_parser.add_argument("--domain", default="example-domain")
_parsed_args, _unknown_args = _arg_parser.parse_known_args()  # NOT parse_args()

# DO: Load config with safe fallback, load domain prompt with safe fallback
_config = _load_config(_PROJECT_ROOT / "orchestrator-config.yaml")
_domain_prompt = _load_domain_prompt(_PROJECT_ROOT, _parsed_args.domain)

# DO: Assign result to module-level 'agent' — this is what langgraph.json references
agent = _build_agent(_config, _domain_prompt)

# DON'T: Call parse_args() — it will raise SystemExit when LangGraph passes extra argv
# DON'T: Name the variable anything other than 'agent' unless langgraph.json is updated
# DON'T: Build the graph directly at module level without helper functions (untestable)
```

---

## Complete agent.py Initialization Sequence

The module-level execution in `agent.py.template` follows this exact order:

```
1. load_dotenv(dotenv_path=_PROJECT_ROOT / ".env", override=False)
   └── Loads environment variables; silent if .env absent.

2. _arg_parser.parse_known_args()
   └── Parses --domain flag; unknown argv silently discarded.

3. _load_config(_PROJECT_ROOT / "orchestrator-config.yaml")
   └── yaml.safe_load() with _DEFAULT_CONFIG fallback on any error.

4. _load_domain_prompt(_PROJECT_ROOT, _parsed_args.domain)
   └── Reads domains/{domain}/DOMAIN.md with _DEFAULT_DOMAIN_PROMPT fallback.

5. _build_agent(_config, _domain_prompt)
   └── Calls create_orchestrator() → create_deep_agent() → CompiledStateGraph.

6. agent = <compiled graph>   ← module-level export for langgraph.json
```

**Testing implication**: Steps 1-6 run at import time. Any test that does `import agent` without patching `create_orchestrator` will attempt a real LLM connection. Always patch before importing.

---

## Configuration Schema Reference

Complete schema for `orchestrator-config.yaml`:

```yaml
orchestrator:
  reasoning_model: "anthropic:claude-sonnet-4-6"   # str, required
  implementation_model: "anthropic:claude-haiku-4-5" # str, required
  domain: "example-domain"                          # str, optional
  max_retries: 3                                    # int, optional
```

- If file is missing entirely, `_DEFAULT_CONFIG` provides `reasoning_model` and `implementation_model`.
- If file exists but keys are missing, `_load_config()` merges partial dict with `_DEFAULT_CONFIG["orchestrator"]`.
- `domain` and `max_retries` are not read by `_load_config()` — `domain` comes from `--domain` CLI arg.

---

## Testing the Orchestrator

Patch `create_deep_agent` at the call site before importing `agent` to prevent real LLM connections.

```python
from unittest.mock import MagicMock, patch
import pytest

class TestCreateOrchestrator:
    @pytest.fixture(autouse=True)
    def mock_create_deep_agent(self) -> MagicMock:
        with patch("agents.create_deep_agent") as mock:
            mock.return_value = MagicMock(name="compiled_graph")
            yield mock

    def test_returns_compiled_graph(self, mock_create_deep_agent):
        from agents import create_orchestrator
        result = create_orchestrator(
            reasoning_model="anthropic:claude-sonnet-4-6",
            implementation_model="anthropic:claude-haiku-4-5",
            domain_prompt="Test domain.",
        )
        mock_create_deep_agent.assert_called_once()
        assert result is mock_create_deep_agent.return_value

    @pytest.mark.parametrize("reasoning,implementation", [
        ("", "anthropic:claude-haiku-4-5"),
        (None, "anthropic:claude-haiku-4-5"),
        ("anthropic:claude-sonnet-4-6", ""),
    ])
    def test_raises_for_invalid_model(self, reasoning, implementation, mock_create_deep_agent):
        from agents import create_orchestrator
        with pytest.raises(ValueError):
            create_orchestrator(reasoning, implementation, "irrelevant")
```

---

## Subagent Failure Handling

The Evaluator returns a JSON verdict that drives the retry loop:

| Verdict | Score | Orchestrator Action |
|---------|-------|---------------------|
| `accept` | 4-5 | Task complete — return final output |
| `revise` | 2-3 | Re-plan with Evaluator issues, re-delegate |
| `reject` | 1 | Escalate — do not retry without human input |

The `max_retries: 3` key in config sets the ceiling for `revise` cycles. Retry exhaustion behaviour is an implementation choice (see ASK boundary).

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
