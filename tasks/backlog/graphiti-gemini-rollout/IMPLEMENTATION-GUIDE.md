# Implementation Guide: Graphiti Gemini 2.5 Flash Rollout (FEAT-G7B2)

## Prerequisites

- [ ] Obtain a Google API key from https://aistudio.google.com/apikey
- [ ] Export `GOOGLE_API_KEY` in your shell (add to `~/.zshrc` or equivalent)
- [ ] Keep the GB10 embedding vLLM on port 8001 running throughout rollout
- [ ] Do **not** stop the GB10 LLM vLLM on port 8000 until Wave 4 + soak completes

## Wave 1 — Code + MCP config (parallelizable)

### TASK-G7B2-001 — Python client: add `gemini` provider + fix `embedding_dim`

Touches: `guardkit/knowledge/config.py`, `guardkit/knowledge/graphiti_client.py`,
`pyproject.toml`, tests.

Changes:

1. `guardkit/knowledge/config.py` — extend `valid_providers` tuple (line ~186) to
   `("openai", "vllm", "ollama", "gemini")`. Propagate `embedding_dimensions`
   and new `gemini` fields through `load_graphiti_config()`.

2. `guardkit/knowledge/graphiti_client.py`:
   - Extend `VALID_PROVIDERS` at line 108 to include `"gemini"`
   - In `_build_llm_client()` (line ~586), add a `gemini` branch:
     ```python
     if self.config.llm_provider == "gemini":
         from graphiti_core.llm_client.gemini_client import GeminiClient
         from graphiti_core.llm_client import LLMConfig
         return GeminiClient(config=LLMConfig(
             api_key=os.environ["GOOGLE_API_KEY"],
             model=self.config.llm_model or "gemini-2.5-flash",
         ))
     ```
   - In `_build_embedder()` (line ~568), pass `embedding_dim` through when set
     (fixes the latent bug — currently `embedding_dimensions` from yaml is
     never reached the embedder config)

3. In the settings → GraphitiConfig bridge (`_do_init_thread_client` ~line 2406),
   pass `embedding_dimensions=settings.embedding_dimensions` through.

4. `pyproject.toml` — add `graphiti-core[google-genai]` as an optional
   dependency group, and include it in the `all` extra:
   ```toml
   gemini = ["graphiti-core[google-genai]"]
   ```

5. Tests (under `tests/knowledge/`):
   - `gemini` accepted as valid provider (both in `config.py` and `graphiti_client.py`)
   - `_build_llm_client()` builds a `GeminiClient` when configured
   - `_build_embedder()` passes `embedding_dim=1024` through to `OpenAIEmbedderConfig`
   - Settings bridge passes `embedding_dimensions` through to `GraphitiConfig`

### TASK-G7B2-002 — MCP server config update (no code)

Touches: `guardkit/.mcp.json`,
`/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/config/config-guardkit.yaml`.

`.mcp.json` env block:

```jsonc
"env": {
  "CONFIG_PATH": "/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/config/config-guardkit.yaml",
  "GOOGLE_API_KEY": "${GOOGLE_API_KEY}",
  "EMBEDDING_API_URL": "http://promaxgb10-41b1:8001/v1",
  "EMBEDDING_DIM": "1024"
}
```

Remove: `OPENAI_API_KEY`, `LLM_API_URL`, `LLM_MODEL`.

`config-guardkit.yaml` — set LLM block:

```yaml
llm:
  provider: "gemini"
  model: "gemini-2.5-flash"
  providers:
    gemini:
      api_key: ${GOOGLE_API_KEY}
```

Leave the embedder block pointing at GB10:8001. Do **not** modify database or
graphiti sections.

## Wave 2 — Guardkit flip + smoke-test (gating)

### TASK-G7B2-003 — Flip guardkit's own `.guardkit/graphiti.yaml` to Gemini

Touches: `guardkit/.guardkit/graphiti.yaml`.

Changes:
- `llm_provider: gemini`
- `llm_model: gemini-2.5-flash`
- Comment out / remove the vLLM/Ollama `llm_base_url` lines (Gemini URL is
  implicit in the native client)
- Keep `embedding_provider: vllm`, `embedding_base_url`, `embedding_dimensions: 1024`
- Keep `max_concurrent_episodes: 3` (Gemini's generous free tier tolerates this
  easily; can raise to 5 later)

Smoke-test checklist (must all pass before Wave 3):
- [ ] Restart Claude Code so MCP server picks up new config
- [ ] `mcp__graphiti__search_nodes` returns results against existing
      `guardkit__*` groups (query fast path — no LLM call)
- [ ] `guardkit graphiti seed-system --force` on one small group completes
      within the normal time window (watch for stalls that could indicate
      thinking-mode contamination)
- [ ] `mcp__graphiti__add_memory` with a test episode succeeds (verifies Gemini
      entity-extraction end-to-end)
- [ ] FalkorDB vector-dim check: new embeddings still 1024-dim
- [ ] `guardkit graphiti status` reports healthy

**Gate**: if any smoke-test fails, revert `.guardkit/graphiti.yaml` and
`.mcp.json` on this repo only. Do not proceed to Wave 3.

## Wave 3 — Multi-repo rollout (parallelizable after Wave 2)

### TASK-G7B2-004 — GPU-bound repos

Repos: `agentic-dataset-factory`, `forge`, `specialist-agent`.

For each:
1. Apply the same `.mcp.json` diff as TASK-G7B2-002 (preserving
   `CONFIG_PATH` absolute paths)
2. Apply the same `.guardkit/graphiti.yaml` diff as TASK-G7B2-003 (preserving
   the per-repo `project_id`)
3. Smoke-test: one MCP query from Claude Code in that repo

### TASK-G7B2-005 — Remaining active repos

Repos: `nats-infrastructure`, `nats-core`, `lpa-platform`,
`dotnet-functional-fastendpoints-exemplar`, `require-kit`,
`deepagents-player-coach-exemplar`, `youtube-transcript-mcp`.

Same diffs as Wave 3a. Additionally:
- 9 repos currently missing explicit `embedding_dimensions: 1024`: add it.
- `youtube-transcript-mcp` missing entirely: must add.
- Repos with no `.mcp.json` (graphiti.yaml only): skip the MCP step.

Skip entirely: `vllm-profiling`, `agentecflow_platform`, `deepagents`,
`architect-agent_delete_me`, `deepagents-player-coach-exemplar-original`.

## Wave 4 — Docs + ADR

### TASK-G7B2-006 — Retire macbook-offload doc + capture ADR

- Update `docs/reference/graphiti-macbook-offload.md` with a "superseded by
  Gemini rollout (TASK-REV-C7A3)" banner linking to the research doc and this
  feature folder. Or delete if no historical value.
- Capture the decision via `mcp__graphiti__add_memory` into
  `architecture_decisions`:
  - Name: `ADR: Graphiti LLM on Gemini 2.5 Flash`
  - Content: rationale, alternatives considered (Groq, Bedrock, Anthropic,
    stay-local), cost profile, fallback (flip `llm_provider: vllm` in yaml),
    pivot note (originally scoped Groq, pivoted April 2026 due to Developer tier).

## Rollback Plan

Rollback for any repo is a single commit reverting `.guardkit/graphiti.yaml`
(and `.mcp.json` if applicable) to the vLLM config. The GB10 vLLM on port 8000
remains running throughout the rollout — fallback is instant, no data loss, no
re-seeding.

Only after Wave 4 completes and the setup has soaked for 1+ weeks should the
port 8000 vLLM be considered for decommissioning (separate task).
