# Memory Injection Pattern

`MemoryMiddleware` + `FilesystemBackend` loads boundary files (like `AGENTS.md`) into agent system prompts at runtime. This injects operational rules and role constraints without giving agents filesystem tool access.

## Core Pattern

```python
from deepagents.backends import FilesystemBackend
from deepagents.middleware import MemoryMiddleware

# Backend for memory file reading only — NOT for filesystem tool injection
backend = FilesystemBackend(root_dir=".")
middleware = [
    MemoryMiddleware(backend=backend, sources=["./AGENTS.md"]),
]
```

`FilesystemBackend` here is for **reading memory files only**. It does NOT inject filesystem tools (ls, read_file, write_file, etc.) — that is what `FilesystemMiddleware` does, and we deliberately avoid it.

Source: `agents/player.py.template`, `agents/coach.py.template`

## How Boundaries Are Injected

The `AGENTS.md` file defines ALWAYS/NEVER/ASK rules for each agent role. `MemoryMiddleware` reads this file via `FilesystemBackend` and prepends its content to the agent's system prompt at runtime.

```python
# In the Player factory
system_prompt = PLAYER_SYSTEM_PROMPT + "\n\n" + domain_prompt

backend = FilesystemBackend(root_dir=".")
middleware = [
    MemoryMiddleware(backend=backend, sources=["./AGENTS.md"]),
    PatchToolCallsMiddleware(),
]

return create_agent(
    model=model,
    tools=tools,
    system_prompt=system_prompt,
    middleware=middleware,
)
```

The agent sees (in order):
1. The system prompt (`PLAYER_SYSTEM_PROMPT` + domain criteria)
2. The AGENTS.md boundaries (injected by MemoryMiddleware)

## AGENTS.md Structure

The boundary file defines per-role operational rules:

```markdown
## Framework Contract: ainvoke() Message Rules (TASK-REV-R2A1)
[Message role constraints — applies to all agents]

## Player Agent
### ALWAYS:
- Call `search_data` before generating any content
- Produce valid JSON output conforming to DOMAIN.md schema
### NEVER:
- Write output without Coach approval
- Skip the search step

## Coach Agent
### ALWAYS:
- Return structured JSON evaluation matching the schema
- Evaluate against every criterion in DOMAIN.md
### NEVER:
- Write to output files
- Return prose instead of JSON
```

Source: `AGENTS.md.template`

## Why FilesystemBackend, Not FilesystemMiddleware

| Component | Purpose | Adds Tools? |
|-----------|---------|-------------|
| `FilesystemBackend` | Read-only file access for `MemoryMiddleware` | No |
| `FilesystemMiddleware` | Full filesystem tool injection | Yes (8 tools: ls, read_file, write_file, edit_file, glob, grep, execute, write_todos) |

Using `FilesystemMiddleware` would violate tool separation — the Player would get `write_file` (bypassing orchestrator-gated writes) and the Coach would get tools (violating the D5 invariant).

This distinction was a root cause of tool leakage in runs 1-6 (TRF-003, TRF-012, TRF-016, TRF-017). The fix was to use `create_agent()` with explicit `MemoryMiddleware` + `FilesystemBackend` instead of `create_deep_agent()` which unconditionally adds `FilesystemMiddleware`.

## When to Use

- Injecting operational boundaries (ALWAYS/NEVER/ASK rules) into agents
- Loading shared context files that all agents in a system should follow
- Making agents aware of their role constraints at runtime
- Any case where agents need to read files but must NOT have filesystem tools

## When NOT to Use

- When the agent needs actual filesystem tools (use `create_deep_agent()` instead)
- For domain-specific content injection (use the domain-driven-configuration pattern)
- For prompt content that is static and known at factory time (just concatenate strings)
