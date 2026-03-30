# Getting Started

A step-by-step guide to your first working adversarial cooperation pipeline.

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| Python | >= 3.11 | Type hint syntax requires 3.11+ |
| DeepAgents SDK | >= 0.4.11 | `pip install deepagents` |
| LangChain | >= 1.2.11 | Plus langchain-core >= 1.2.18, langchain-community >= 0.3 |
| LangGraph | >= 0.2 | Graph orchestration |
| LLM provider | vLLM recommended | OpenAI-compatible endpoint; see [model-compatibility.md](reference/model-compatibility.md) |

Install dependencies:

```bash
pip install -r requirements.txt
```

## Quick Start (5 minutes)

### 1. Verify installation

```bash
pytest tests/ -v
```

All tests should pass before proceeding.

### 2. Configure your LLM endpoint

Set environment variables for your OpenAI-compatible provider:

```bash
export OPENAI_API_BASE="http://localhost:8000/v1"
export OPENAI_API_KEY="not-needed"  # vLLM doesn't require a key
```

### 3. Create a domain

Create `domains/my-domain/DOMAIN.md` with four required sections:

```markdown
## Domain Description
What the Player should generate.

## Generation Guidelines
Step-by-step instructions for the Player.

## Evaluation Criteria
| Criterion | Description |
|-----------|-------------|
| Accuracy  | All claims supported by cited sources |

## Output Format
JSON schema the Player must produce.
```

See the `example-domain/` directory for a complete reference.

### 4. Run the pipeline

```bash
python agent.py --domain my-domain
```

The Orchestrator will loop Player and Coach until the Coach accepts or retries are exhausted.

## Key SDK Constraints

These constraints come from the DeepAgents SDK and cause hard-to-debug failures if violated.

### `create_agent()` vs `create_deep_agent()`

| Function | Use for | Why |
|----------|---------|-----|
| `create_agent()` | Player and Coach agents | You control exactly which tools and middleware are added |
| `create_deep_agent()` | General-purpose agents needing filesystem access | Unconditionally injects 8-10 middleware tools (write_file, execute, etc.) |

**Rule**: Always use `create_agent()` for adversarial agents. `create_deep_agent()` injects `FilesystemMiddleware` which gives agents `write_file` and `execute` tools, bypassing orchestrator-gated writes.

See: `.claude/rules/patterns/factory.md`

### `ainvoke()` message contract

`create_agent()` prepends the `system_prompt` on every `ainvoke()` call. If you pass a `system` role message in the input, the LLM receives **two** system messages, which vLLM rejects with HTTP 400.

```python
# CORRECT
await agent.ainvoke({"messages": [{"role": "user", "content": feedback}]})

# WRONG - causes dual system messages
await agent.ainvoke({"messages": [{"role": "system", "content": feedback}]})
```

Use `assert_no_system_messages()` from `lib/factory_guards.py` at every `ainvoke()` call site.

## Tool Separation Rules

The three-role architecture enforces strict tool boundaries:

| Role | Tools | Responsibility |
|------|-------|---------------|
| **Orchestrator** | `write_output` (programmatic, not an agent tool) | Coordinates loop, owns all file writes |
| **Player** | Domain tools only (e.g. `search_data`) | Generates content, revises on rejection |
| **Coach** | **NONE** (`tools=[]`) | Evaluates Player output, returns structured verdict |

Enforcement layers:

1. **Factory level**: `assert_tool_inventory()` verifies exact tool set at agent creation
2. **SDK level**: Using `create_agent()` prevents middleware tool injection
3. **Runtime level**: `assert_no_system_messages()` at every `ainvoke()` call

The `OrchestratorWriteGate` ensures writes only happen after Coach acceptance.

See: `.claude/rules/patterns/tool-delegation.md`, `.claude/rules/patterns/adversarial-cooperation.md`

## Common Pitfalls

### 1. Using `create_deep_agent()` for Player or Coach

**Symptom**: Player writes files directly, bypassing Coach evaluation.
**Cause**: `create_deep_agent()` injects `FilesystemMiddleware` with `write_file`, `edit_file`, `execute`.
**Fix**: Use `create_agent()` with explicit tools and `MemoryMiddleware` for boundary injection.

### 2. Passing system messages in `ainvoke()` input

**Symptom**: vLLM returns HTTP 400 Bad Request.
**Cause**: `create_agent()` already prepends the system prompt; a second system message is invalid.
**Fix**: Use `"role": "user"` for all input messages including retry feedback.

### 3. Using `--reasoning-parser qwen3` with vLLM

**Symptom**: `write_output` validation fails; `<think>` blocks silently disappear.
**Cause**: The parser strips think blocks from `.content` into `reasoning_content`, which LangChain discards.
**Fix**: Omit `--reasoning-parser`. The `JsonExtractor` handles think blocks in raw content.

### 4. Double-serialised tool arguments (Qwen models)

**Symptom**: Tool dispatch fails with JSON parse errors.
**Cause**: Qwen models sometimes emit tool `arguments` as a JSON string inside a JSON string.
**Fix**: Check if `arguments` is a string and call `json.loads()` twice if needed.

### 5. Using `FilesystemMiddleware` for memory injection

**Symptom**: Agents gain unexpected filesystem tools (ls, read_file, write_file, etc.).
**Cause**: `FilesystemMiddleware` injects tools; `FilesystemBackend` + `MemoryMiddleware` does not.
**Fix**: Use `MemoryMiddleware(backend=FilesystemBackend(...))` to inject boundary files read-only.

See: [model-compatibility.md](reference/model-compatibility.md) for model-specific issues.

## What to Do Next

Once your pipeline runs successfully:

1. **Customise your domain**: Edit `DOMAIN.md` to match your use case — generation guidelines, evaluation criteria, and output schema
2. **Add domain tools**: Create LangChain `@tool` functions for your Player (see `.claude/rules/guidance/langchain-tool-specialist.md`)
3. **Review pattern rules**: Deep-dive into the architecture via `.claude/rules/patterns/`:
   - `adversarial-cooperation.md` — Three-role architecture and rejection-revision loop
   - `factory.md` — Agent factory decision tree
   - `tool-delegation.md` — Tool separation contract and enforcement
   - `memory-injection.md` — Boundary file injection without tool leakage
   - `domain-driven-configuration.md` — Making the system domain-agnostic
4. **Consider weighted evaluation**: If your domain requires subjective quality scoring (not binary pass/fail), see the [`langchain-deepagents-weighted-evaluation`](../../langchain-deepagents-weighted-evaluation/) extension template
5. **Check model compatibility**: Review [model-compatibility.md](reference/model-compatibility.md) before switching models
