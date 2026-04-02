# Langchain Tool Decorator Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **langchain-tool-decorator-specialist** agent.

**Core documentation**: See [langchain-tool-decorator-specialist.md](./langchain-tool-decorator-specialist.md)

---

## Related Templates

### Primary Reference

- `templates/other/tools/orchestrator_tools.py.template` — The canonical source for all four @tool decorator implementations (`analyse_context`, `plan_pipeline`, `execute_command`, `verify_output`). Demonstrates docstring-driven parameter schemas, string return types, and try/except wrapping. This is the template to study before writing any new tool.

- `templates/other/tools/__init__.py.template` — Shows the required package export pattern. Every tools package must expose all tool functions via `__all__` so agents can import them with a single `from tools import ...` statement.

- `templates/other/agents/agents.py.template` — Demonstrates how tool lists are assembled into `_ORCHESTRATOR_TOOLS` and passed to both `SubAgent` constructors and `create_deep_agent`. Follow this pattern when wiring tools into agent graphs.

### Supporting Context

- `templates/other/tools/execute_command.py.template` — Illustrates the re-export shim pattern: when a tool needs to be importable from an alternative module path, create a thin shim that re-exports from the canonical location rather than duplicating the implementation.

- `templates/other/other/agent.py.template` — Shows how the overall entrypoint loads configuration and domain context before constructing the orchestrator, demonstrating the runtime environment tools must operate within (Path-based resolution, yaml config, dotenv loading).

## Code Examples

### DO: Correct @tool decorator pattern with full docstring schema

Every tool must use `@tool(parse_docstring=True)`, define all parameters in the `Args:` section of the docstring, return a `str`, and wrap the entire body in try/except.

```python
from langchain_core.tools import tool
import logging

logger = logging.getLogger(__name__)

@tool(parse_docstring=True)
def analyse_context(query: str, domain: str) -> str:
    """Read and summarise project context for a given query and domain.

    If the query is a path to an existing file, reads and returns its content
    along with the domain context. Otherwise returns a context summary based
    on the query and domain provided.

    Args:
        query: A context query string, or a file path to read for context.
        domain: The domain to focus the analysis on.
    """
    try:
        query_path = Path(query)
        if query_path.is_file():
            content = query_path.read_text(encoding="utf-8")
            truncated = content[:4000] if len(content) > 4000 else content
            return (
                f"Context analysis for domain '{domain}':\n"
                f"Source: {query}\n"
                f"Content ({len(content)} chars):\n{truncated}"
            )
        return (
            f"Context analysis for domain '{domain}':\n"
            f"Query: {query}\n"
            f"Summary: Analysed context for '{query}' within the '{domain}' domain."
        )
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return f"Error analysing context: {exc}"
    except Exception as exc:
        logger.exception("Unexpected error in analyse_context")
        return f"Error analysing context: {exc}"
```

Key points from the template:
- `parse_docstring=True` is not optional — omitting it means parameter schemas are not extracted from the `Args:` section
- The `Args:` section is the single source of truth for parameter descriptions; keep them concise but specific
- Two except clauses: specific exceptions first, bare `Exception` last with `logger.exception()` for unexpected failures
- All return paths produce a plain string — no dicts, no exceptions propagate to the caller

---

### DO: Structured JSON return from tools that produce data

When a tool produces structured output (e.g. a pipeline plan), use `json.dumps` to serialise it as a string. The LLM receives the string and can parse it as needed.

```python
@tool(parse_docstring=True)
def plan_pipeline(task: str, context: str) -> str:
    """Generate a JSON pipeline plan for the given task and context.

    Args:
        task: Description of the task to plan a pipeline for.
        context: Contextual information to inform the plan.
    """
    try:
        task_clean = task.strip() if task else "unspecified task"
        context_clean = context.strip() if context else "no additional context"
        plan = {
            "task": task_clean,
            "context": context_clean,
            "steps": [
                {"step": 1, "action": "analyse", "description": f"Analyse requirements for: {task_clean}"},
                {"step": 2, "action": "implement", "description": f"Implement solution using context: {context_clean}"},
                {"step": 3, "action": "verify", "description": f"Verify output meets criteria for: {task_clean}"},
            ],
        }
        return json.dumps(plan, indent=2)
    except (TypeError, ValueError) as exc:
        return json.dumps({"error": str(exc), "steps": []})
    except Exception as exc:
        logger.exception("Unexpected error in plan_pipeline")
        return json.dumps({"error": str(exc), "steps": []})
```

Note that even the error path returns `json.dumps(...)` — not a plain string — so callers always receive parseable JSON from this tool.

---

### DO: Package export pattern from `__init__.py`

All tools must be exported from the package `__init__.py` and listed in `__all__`.

```python
# tools/__init__.py
"""Orchestrator tools package.
Exports the four orchestrator tools: analyse_context, plan_pipeline,
execute_command, and verify_output.
"""
from {{ProjectName}}.orchestrator_tools import (
    analyse_context,
    execute_command,
    plan_pipeline,
    verify_output,
)

__all__ = [
    "analyse_context",
    "plan_pipeline",
    "execute_command",
    "verify_output",
]
```

This allows agents to import with `from tools import analyse_context, plan_pipeline, execute_command, verify_output` rather than referencing internal module paths.

---

### DON'T: Raise exceptions, return non-strings, or skip docstring Args

```python
# WRONG — raises exception, no try/except, returns dict, missing Args section
@tool(parse_docstring=True)
def bad_tool(query: str) -> dict:  # dict return type is wrong
    """Fetch something.
    # No Args section — parse_docstring=True will not extract parameter schemas
    """
    result = do_something_risky(query)  # may raise — not wrapped
    return {"result": result}           # dict, not str

# RIGHT — matches template pattern
@tool(parse_docstring=True)
def good_tool(query: str) -> str:
    """Fetch something.

    Args:
        query: The query string to process.
    """
    try:
        result = do_something_risky(query)
        return f"Result: {result}"
    except (ValueError, OSError) as exc:
        return f"Error: {exc}"
    except Exception as exc:
        logger.exception("Unexpected error in good_tool")
        return f"Error: {exc}"
```

---

## Common Anti-Patterns

### Anti-Pattern 1: Raising Instead of Returning

```python
# WRONG — exception escapes to the orchestrator graph
@tool(parse_docstring=True)
def read_file(path: str) -> str:
    """Read a file.

    Args:
        path: File path to read.
    """
    return Path(path).read_text()  # FileNotFoundError will crash the graph

# CORRECT — catch and return error string
@tool(parse_docstring=True)
def read_file(path: str) -> str:
    """Read a file.

    Args:
        path: File path to read.
    """
    try:
        return Path(path).read_text(encoding="utf-8")
    except (FileNotFoundError, OSError) as exc:
        return f"Error reading {path}: {exc}"
    except Exception as exc:
        logger.exception("Unexpected error in read_file")
        return f"Error: {exc}"
```

### Anti-Pattern 2: Missing Args Section

```python
# WRONG — parse_docstring=True but no Args section means no parameter schema
@tool(parse_docstring=True)
def analyse(query: str, domain: str) -> str:
    """Analyse context for a query."""  # Missing Args: section!
    ...

# CORRECT — Args section defines parameter schema for the SDK
@tool(parse_docstring=True)
def analyse(query: str, domain: str) -> str:
    """Analyse context for a query.

    Args:
        query: The search query or file path to analyse.
        domain: The domain to focus analysis on.
    """
    ...
```

### Anti-Pattern 3: Returning Non-String Types

```python
# WRONG — returning dict breaks the tool contract
@tool(parse_docstring=True)
def get_status() -> dict:
    """Get system status."""
    return {"status": "ok", "count": 42}  # dict, not str

# CORRECT — return JSON-serialized string
@tool(parse_docstring=True)
def get_status() -> str:
    """Get system status.

    Args: (no arguments)
    """
    import json
    return json.dumps({"status": "ok", "count": 42}, indent=2)
```

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
