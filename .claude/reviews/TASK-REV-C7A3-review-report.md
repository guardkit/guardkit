# Review Report: TASK-REV-C7A3 — Graphiti Groq + GPT-OSS 120B rollout

- **Mode**: decision
- **Depth**: standard
- **Date**: 2026-04-17
- **Reviewer**: task-review (3 parallel Explore agents)

---

## Executive Summary

The research doc's recommended approach — Groq + `openai/gpt-oss-120b` for entity
extraction, local embeddings preserved — is **viable** and can be rolled out in a
contained change.

**Score: 78/100** — high-confidence path, low blast radius, minor code work required.

Key finding that simplifies the rollout:

- **The Graphiti MCP server (at `graphiti/mcp_server`) already has native Groq support.**
  `factories.py` dispatches on `config.llm.provider` and supports `groq` via
  `GroqClient` out of the box. No MCP-server code changes needed — config-only.
- **The GuardKit Python client (`guardkit.knowledge`) does not.** It hardcodes
  `VALID_PROVIDERS = ("openai", "vllm", "ollama")` and raises `ValueError` on
  `llm_provider: groq`. Three small code touches are needed.

The rollout is therefore two parallel tracks:

1. **Config track** (no code): update `.mcp.json` + `config-guardkit.yaml` + every
   repo's `.guardkit/graphiti.yaml` so the MCP server runs on Groq.
2. **Code track** (one PR): add `groq` to the GuardKit Python client so
   `guardkit graphiti seed` and AutoBuild's Graphiti calls work via Groq too.

---

## Findings

### F1 — MCP server is Groq-ready today

Source: `graphiti/mcp_server/src/services/factories.py` lines 98–260

- `LLMClientFactory.create()` dispatches on `config.llm.provider` across five
  providers: `openai`, `azure_openai`, `anthropic`, `gemini`, **`groq`**.
- Native `GroqClient` is imported at line 67; Groq branch is at 241–257.
- Schema (`schema.py` line 121–126) defines `GroqProviderConfig` with a default
  `api_url` of `https://api.groq.com/openai/v1`.
- Env vars override YAML — so the same `.mcp.json` env-var mechanism keeps working,
  we just swap which env vars are set.

**Implication**: MCP-based queries from Claude Code (`mcp__graphiti__*`) will work
on Groq as soon as we change the config. No upstream PR needed.

### F2 — GuardKit Python client needs three code changes

Source: `guardkit/knowledge/graphiti_client.py` + `config.py`

| # | Change | Location |
|---|--------|----------|
| 1 | Add `"groq"` to `VALID_PROVIDERS` | `config.py` ~line 103 |
| 2 | Add `groq` branch in `_build_llm_client()` that instantiates `graphiti_core.llm_client.groq_client.GroqClient` with `LLMConfig(api_key, model, small_model)` | `graphiti_client.py` ~lines 586–607 |
| 3 | Add `graphiti-core[groq]` to `pyproject.toml` (currently `graphiti-core>=0.5.0` with no extras; lockfile pins `0.26.3`, which does ship `groq_client.py`) | `pyproject.toml` line 34 |

Scope is small: one config allowlist, one factory branch, one dependency extra.

### F3 — Latent bug: `embedding_dimensions` not passed through

Source: `guardkit/knowledge/graphiti_client.py` `_build_embedder()` lines 568–584

- `.guardkit/graphiti.yaml` sets `embedding_dimensions: 1024`.
- Config loader stores it.
- `_build_embedder()` constructs `OpenAIEmbedderConfig(base_url, embedding_model,
  api_key)` — **never passes the `embedding_dim` field**.
- Works by accident today because the embedding model (nomic-v1.5 via vLLM) returns
  1024-dim vectors natively.

**Risk**: independent of Groq, but worth fixing in the same PR — any future change
to the embedding model would silently produce dimension-mismatched vectors.

### F4 — Config drift across 14 active repos (mostly benign)

Source: multi-repo survey of `/Users/richardwoollcott/Projects/appmilla_github/`

| Drift | Repos affected | Severity |
|-------|----------------|----------|
| Missing explicit `embedding_dimensions: 1024` | 9 repos | Low (currently correct by default) |
| Missing `embedding_dimensions` field entirely | `youtube-transcript-mcp` | Medium (silently defaults to model native) |
| No Graphiti integration at all | `agentecflow_platform`, `deepagents` | N/A — skip |
| Retired | `architect-agent_delete_me`, `deepagents-player-coach-exemplar-original` | Skip |
| No MacBook-endpoint drift | None | Clean |

All 11 Graphiti-configured repos point at the GB10 vLLM endpoint
(`promaxgb10-41b1:8000/v1`). No repos accidentally on MacBook.

### F5 — Secret management needs a decision

- `GROQ_API_KEY` should NOT be written directly into `.mcp.json` or
  `graphiti.yaml` (both are in git).
- Options:
  - **(A)** Reference env var: `"GROQ_API_KEY": "${GROQ_API_KEY}"` in `.mcp.json`.
    Requires the user's shell to export it before launching Claude Code.
  - **(B)** Per-repo `.env.local` (gitignored) sourced by a wrapper script.
  - **(C)** Keychain + shell integration.

Recommended: **(A)** — simplest, matches existing `OPENAI_API_KEY=not-needed-vllm-local`
pattern (env-var driven), and rotation is a single-location change.

### F6 — Reranker cost concern from the research doc — can be deferred

The research doc worries reranker calls (per-query) could dwarf entity-extraction
costs (per-seed). Checking the code:

- MCP server's embedder path is independent of the LLM — reranker isn't explicitly
  wired in the current setup.
- `guardkit.knowledge`'s client construction (F2) also doesn't wire a cross-encoder
  separately — graphiti-core's default behavior is used.

**Action**: ship Groq for LLM, keep embeddings local, **do not add a cloud
reranker** unless/until we observe it's needed. This side-steps the cost concern.

### F7 — No existing provider toggle — but we don't need a new one

The research doc proposes a `GRAPHITI_LLM_PROVIDER` env var toggle. The code already
reads `LLM_PROVIDER` into the config, and `llm_provider:` is a yaml field. Flipping
between `vllm` and `groq` is already just a yaml/env edit. **Don't add a third
toggle — overkill.**

---

## Decision Matrix

| Option | Effort | Risk | Reversibility | Cost (moderate use) | Recommendation |
|--------|--------|------|---------------|---------------------|----------------|
| **A. Groq + gpt-oss-120b (research doc Option A)** | Low — 1 code PR + config fanout | Low — known pattern, MCP already supports | Trivial — flip yaml back | £3-6/mo | ✅ **Adopt** |
| B. Bedrock via LiteLLM | Medium — LiteLLM proxy + generic client | Medium — more moving parts | Trivial | £10-30/mo | ❌ Skip — no cost/quality win |
| C. Anthropic direct (Haiku) | Low — native client exists | Low | Trivial | £10-30/mo | ❌ Skip — 3-5× Groq cost |
| D. Stay local (do nothing) | Zero | Zero | N/A | £0 | ❌ GPU contention unresolved |

**Recommended: Option A**, per research doc.

---

## Recommendations

Prioritized for implementation. Waves and parallelization marked for the
auto-detection pipeline.

1. **[Code, Wave 1] Add `groq` provider support to guardkit Python client**
   - Add `"groq"` to `VALID_PROVIDERS` in `guardkit/knowledge/config.py`
   - Add Groq branch in `_build_llm_client()` instantiating `GroqClient` from
     `graphiti_core.llm_client.groq_client`
   - Add `graphiti-core[groq]` extra to `pyproject.toml`
   - Add unit tests for config parsing and client construction
   - **Also in this PR**: fix F3 — pass `embedding_dimensions` through to
     `OpenAIEmbedderConfig(embedding_dim=...)`

2. **[Config, Wave 1] Update guardkit's own `.mcp.json` and `.guardkit/graphiti.yaml` as reference**
   - `.mcp.json`: replace `OPENAI_API_KEY`/`LLM_API_URL`/`LLM_MODEL` env vars with
     `GROQ_API_KEY=${GROQ_API_KEY}`. Keep `EMBEDDING_API_URL`, `EMBEDDING_DIM`,
     `CONFIG_PATH`.
   - `config-guardkit.yaml` (shared, in the graphiti repo): set `llm.provider:
     groq`, `llm.model: openai/gpt-oss-120b`, `llm.providers.groq.api_key:
     ${GROQ_API_KEY}`. Embedder section unchanged.
   - `.guardkit/graphiti.yaml`: set `llm_provider: groq`, `llm_model:
     openai/gpt-oss-120b`, remove/comment the vLLM/Ollama blocks.
   - Smoke-test: run `guardkit graphiti seed` on one small document and
     `mcp__graphiti__search_nodes` from Claude Code.

3. **[Config, Wave 2] Roll out to GPU-bound repos**
   - `agentic-dataset-factory`, `forge`, `specialist-agent` — copy the updated
     `.mcp.json` + `graphiti.yaml` shape (with each repo's own `project_id`
     preserved).

4. **[Config, Wave 3] Roll out to remaining active repos**
   - `nats-infrastructure`, `nats-core`, `lpa-platform`,
     `dotnet-functional-fastendpoints-exemplar`, `require-kit`,
     `deepagents-player-coach-exemplar`, `youtube-transcript-mcp`.
   - For `youtube-transcript-mcp` specifically: **add** `embedding_dimensions: 1024`
     (currently missing).
   - For all 9 repos currently missing explicit `embedding_dimensions: 1024`: add
     it while we're in there (F4 tidy-up).

5. **[Documentation] Update `docs/reference/graphiti-macbook-offload.md`**
   - The GB10/MacBook toggle pattern is being superseded by local/cloud. Either
     retire the doc or add a "superseded by Groq" note linking to the research doc.
   - Also capture the rollout outcome as an ADR in `architecture_decisions` group
     so future sessions can find it via Graphiti.

**Non-recommendations / out of scope:**

- Do **not** add a `GRAPHITI_LLM_PROVIDER` toggle (F7 — redundant with yaml).
- Do **not** switch the reranker to cloud (F6 — defer until observed need).
- Do **not** touch `vllm-profiling` (uses GB10 vLLM intentionally), or
  `agentecflow_platform` / `deepagents` (independent MCP configs).
- Do **not** decommission the Qwen2.5-14B vLLM instance on port 8000 in this review
  — do it as a separate follow-up after all waves ship and soak for a week.

---

## Context Used

No Graphiti knowledge-graph queries were run (intentional — this review is about
reconfiguring Graphiti itself, so the research doc at
`docs/research/graphiti-cloud/graphiti-cloud-llm-config.md` is the authoritative
context).

Investigation sources:
- `guardkit/knowledge/graphiti_client.py`, `config.py`, `pyproject.toml`, `uv.lock`
- `graphiti/mcp_server/src/services/factories.py`, `schema.py`, `graphiti_mcp_server.py`
- 14 `.mcp.json` + `.guardkit/graphiti.yaml` files across `appmilla_github/`
