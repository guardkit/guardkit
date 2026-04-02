# Langgraph Deployment Config Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **langgraph-deployment-config-specialist** agent.

**Core documentation**: See [langgraph-deployment-config-specialist.md](./langgraph-deployment-config-specialist.md)

---

## Related Templates

### Primary Reference

- `templates/other/other/agent.py.template` — The canonical entrypoint demonstrating all three deployment concerns: the `agent` module-level variable exported for `langgraph.json`, `_load_config()` reading `orchestrator-config.yaml` with YAML `safe_load` and graceful fallback, and `_arg_parser.parse_known_args()` absorbing unknown `sys.argv` values injected by the LangGraph server at import time.

- `templates/other/agents/agents.py.template` — Shows how factory functions accept a `model: str` parameter in `provider:model` format (e.g. `"anthropic:claude-sonnet-4-6"`), how those strings flow from YAML config through `create_orchestrator()` into each `SubAgent` and `AsyncSubAgent` constructor, and how `create_deep_agent()` assembles the final `CompiledStateGraph` that becomes the exported `agent`.

### Supporting Reference

- `templates/other/tools/orchestrator_tools.py.template` — Illustrates the tool layer wired into the graph. Understanding the tool surface helps when configuring `langgraph.json` graph names, because each `SubAgent` that receives tools must be reachable through the graph exported by the entrypoint.

## Code Examples

### Example 1 — Correct langgraph.json graph mapping

`langgraph.json` references a graph using `"./agent.py:agent"` — the path to the Python module and the name of the module-level variable. The variable must exist at import time.



In `agent.py.template` the last executed statement at module scope produces that variable:



**DO**: Assign the compiled graph to a bare module-level name (`agent`) so `langgraph.json` can import it directly.

**DON'T**: Wrap the graph construction inside a `if __name__ == "__main__"` block or a function that is never called at import time — LangGraph will import the module and look for the variable immediately.

---

### Example 2 — YAML model selection with provider:model format

The YAML config file stores model identifiers in `provider:model` format, which is the string format accepted by LangChain's `init_chat_model`. The entrypoint reads these strings and passes them directly to agent factory functions.



The `_load_config()` helper in `agent.py.template` reads this file safely:



Those strings pass through `create_orchestrator()` in `agents.py.template` into each `SubAgent`:



**DO**: Use `yaml.safe_load` (not `yaml.load`) and always validate that required keys are present before using them, merging with hardcoded defaults when keys are missing.

**DON'T**: Use `yaml.load(fh)` without a `Loader` argument — it is a security risk and will raise a warning in modern PyYAML versions.

---

### Example 3 — argparse.parse_known_args surviving LangGraph server injection

When LangGraph serves a module it imports it, which executes module-level code. The server may inject additional values into `sys.argv`. Using `parse_args()` raises `SystemExit` on unknown arguments; `parse_known_args()` silently collects them in `_unknown_args` and continues.



The parsed `--domain` value is then used immediately to load domain-specific context:



**DO**: Call `parse_known_args()` at module scope (not inside `main()`) so the argument is available when `agent` is constructed during import.

**DON'T**: Call `parse_args()` at module scope in any file that LangGraph will import — unknown `sys.argv` entries injected by the server will cause a `SystemExit(2)` that terminates the server process.

---

## Troubleshooting Guide

### "Graph not found" when starting LangGraph server

| Cause | Fix |
|-------|-----|
| Graph name in langgraph.json doesn't match module path | Verify `"./src/ProjectName/agent.py:agent"` is correct |
| `agent` variable inside function or `if __name__` guard | Move to bare module scope |
| Exception during import crashes before `agent =` assigned | Check server logs for traceback |
| Wrong Python path | Confirm package is on `PYTHONPATH` or `pyproject.toml` correct |

### "Unknown argument" warnings in logs

This is expected and safe. `parse_known_args()` captures LangGraph's injected argv values in `_unknown_args`. The server continues normally.

### "Model not supported" or ValueError from init_chat_model

The model string is missing the `provider:` prefix:

```yaml
# WRONG
reasoning_model: "claude-sonnet-4-6"

# CORRECT
reasoning_model: "anthropic:claude-sonnet-4-6"
```

## Environment Variable Precedence

`load_dotenv(override=False)` means:

```
Precedence (highest → lowest):
1. Shell environment variables (set by CI/CD, Docker, export)
2. .env file values (only used if key NOT already in shell env)
```

Never use `override=True` in production — it allows a local `.env` to shadow deployment secrets.

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
