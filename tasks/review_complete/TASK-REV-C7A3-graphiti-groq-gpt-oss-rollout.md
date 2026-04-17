---
id: TASK-REV-C7A3
title: Roll out Graphiti Groq + GPT-OSS 120B cloud LLM config across all GuardKit repos
status: review_complete
task_type: review
review_mode: decision
review_depth: standard
created: 2026-04-17T00:00:00Z
updated: 2026-04-17T00:00:00Z
priority: high
tags: [graphiti, groq, gpt-oss, cloud-llm, mcp, infrastructure, multi-repo, gpu-contention]
complexity: 6
review_results:
  mode: decision
  depth: standard
  score: 78
  findings_count: 7
  recommendations_count: 5
  decision: adopt-option-a-groq
  report_path: .claude/reviews/TASK-REV-C7A3-review-report.md
  completed_at: 2026-04-17T00:00:00Z
---

# Task: Roll out Graphiti Groq + GPT-OSS 120B cloud LLM config across all GuardKit repos

## Description

Analyse and implement the changes described in
[docs/research/graphiti-cloud/graphiti-cloud-llm-config.md](docs/research/graphiti-cloud/graphiti-cloud-llm-config.md)
so Graphiti's entity-extraction LLM runs on **Groq (openai/gpt-oss-120b)** instead of
the local GB10 vLLM instance (Qwen2.5-14B-Instruct-FP8 on port 8000). Embeddings
(`nomic-embed-text-v1.5` on port 8001) stay local.

The end goal is to free the GB10 GPU for fine-tuning, model hosting, and dataset
factory runs without breaking Graphiti ingestion in any GuardKit-related project that
shares the FalkorDB instance.

## Background

### Why

- GB10 currently runs Qwen2.5-14B on port 8000 for Graphiti entity extraction. This
  blocks fine-tuning, agentic-dataset-factory runs, and other model-hosting work.
- Graphiti only calls the LLM during **ingestion/seeding** (not queries), so a cloud
  API is a good fit — low, bursty traffic, minimal cost.
- GPT-OSS 120B is preferred because it has **no thinking mode** (Qwen3 thinking blocks
  caused 900+ second timeouts locally — see research doc §"CRITICAL: Thinking Mode
  Incompatibility").

### Recommended Config (from research doc Option A)

- **LLM provider**: Groq native client (`graphiti-core[groq]`)
- **Model**: `openai/gpt-oss-120b` ($0.15/M in, $0.60/M out)
- **Small model**: `openai/gpt-oss-20b` ($0.075/M in, $0.30/M out)
- **Embeddings**: unchanged — local vLLM on GB10 port 8001, 1024-dim
- **Reranker**: Groq `openai/gpt-oss-20b` (keeps stack fully OpenAI-free)
- **Semaphore**: start at 3, tune based on Groq tier

## Review Scope

### Primary Questions

1. **Config schema compatibility**
   - Does the current `.guardkit/graphiti.yaml` schema support a `groq` provider? If
     not, what needs to extend in `guardkit/knowledge/` config loading?
   - Does `GraphitiClient` / `GraphitiClientFactory` wire the Groq client path, or is
     only `openai`/`vllm`/`ollama` currently handled?
   - Is `graphiti-core[groq]` included in GuardKit's Python dependencies?

2. **MCP server compatibility**
   - `graphiti/mcp_server` (at `/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server`)
     is launched via `.mcp.json` with `LLM_API_URL` / `LLM_MODEL` env vars. Does the
     MCP server support a `GROQ_API_KEY` + Groq endpoint, or does it need an
     OpenAI-generic base URL? Confirm whether `https://api.groq.com/openai/v1` works
     as a drop-in for `LLM_API_URL`.
   - What's the correct shape of `config-guardkit.yaml` to target Groq?

3. **Multi-repo rollout plan**
   - Sixteen local repos have `.guardkit/graphiti.yaml` and/or `.mcp.json`. Which are
     actively used vs stale? (`architect-agent_delete_me`,
     `deepagents-player-coach-exemplar-original` look retired.)
   - Do any repos need to keep the local vLLM config (e.g. `vllm-profiling`,
     offline/airgapped scenarios)?
   - Can we roll this out in waves — guardkit first, then exemplars, then the rest?

4. **Secret management**
   - Where does `GROQ_API_KEY` live? Each repo's `.env`? A shared `.envrc`? Keychain?
   - Should `.mcp.json` reference an env var (`${GROQ_API_KEY}`) instead of being
     rewritten per-repo, so rotation is painless?

5. **Rollback story**
   - The research doc proposes a `GRAPHITI_LLM_PROVIDER` toggle (local | groq |
     bedrock). Should we build this toggle into `graphiti.yaml` so each repo can flip
     back to GB10 vLLM without editing YAML?
   - What's the fallback if Groq has an outage during a `guardkit graphiti seed` run?

6. **Embedding + reranker dimensions**
   - The research doc example shows `embedding_dim=768` in Python code, but our
     FalkorDB is seeded at **1024-dim** (Matryoshka, per `graphiti.yaml`). Must
     confirm the Groq path preserves 1024-dim embeddings — any mismatch will break
     vector search across all shared knowledge.

## Repos to Update

### Actively in use (guardkit org repos — per `gh repo list guardkit`)

| Repo | `.mcp.json` | `.guardkit/graphiti.yaml` | Notes |
|------|-------------|---------------------------|-------|
| `guardkit` | ✅ | ✅ | Source of truth — update first |
| `forge` | ✅ | ✅ | Software factory, heavy Graphiti user |
| `specialist-agent` | ✅ | ✅ | Architecture agent |
| `agentic-dataset-factory` | ✅ | ✅ | Biggest GPU beneficiary of this change |
| `nats-infrastructure` | ✅ | ✅ | |
| `nats-core` | ✅ | ✅ | |
| `deepagents-orchestrator-exemplar` | ? | ? | Needs check (uses graphiti?) |
| `deepagents-player-coach-exemplar` | ❌ | ✅ | No MCP |
| `dotnet-functional-fastendpoints-exemplar` | ✅ | ✅ | |
| `youtube-transcript-mcp` | ❌ | ✅ | |
| `vllm-profiling` | ❌ | ✅ | **Keep local** — profiles vLLM |

### Local-only / satellite repos (in `/Users/richardwoollcott/Projects/appmilla_github/`)

| Repo | `.mcp.json` | `.guardkit/graphiti.yaml` | Notes |
|------|-------------|---------------------------|-------|
| `agentecflow_platform` | ✅ | ❌ | MCP only |
| `deepagents` | ✅ | ❌ | MCP only |
| `lpa-platform` | ✅ | ✅ | |
| `require-kit` | ❌ | ✅ | |
| `architect-agent_delete_me` | ✅ | ✅ | **Skip — retired** |
| `deepagents-player-coach-exemplar-original` | ❌ | ✅ | **Skip — retired** |

## Files Referenced

### Source of truth

- [docs/research/graphiti-cloud/graphiti-cloud-llm-config.md](docs/research/graphiti-cloud/graphiti-cloud-llm-config.md) — the research doc
- [.guardkit/graphiti.yaml](.guardkit/graphiti.yaml) — current GuardKit config
- [.mcp.json](.mcp.json) — current MCP server config
- `/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/config/config-guardkit.yaml` — MCP server's YAML config

### Code that reads the config

- `guardkit/knowledge/` — Python client, `GraphitiClient`, `GraphitiClientFactory`
- Graphiti MCP server source: `/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/main.py`

## Acceptance Criteria

### Review deliverables

- [ ] Confirm `graphiti-core[groq]` is compatible with the installed `graphiti-core`
      version pinned in GuardKit (check `pyproject.toml` / installed version)
- [ ] Confirm MCP server supports Groq endpoint (document the right env var shape)
- [ ] Confirm Groq + local 1024-dim embeddings works end-to-end — no dimension
      mismatch, no reranker breakage
- [ ] Document the canonical `.mcp.json` diff and `.guardkit/graphiti.yaml` diff
- [ ] Document secret-management approach (env var referenced in `.mcp.json`, or
      per-repo `.env`, etc.)

### Implementation deliverables

- [ ] Update `guardkit/knowledge/` config loader to support `llm_provider: groq` (if
      not already supported)
- [ ] Add `graphiti-core[groq]` to GuardKit dependencies
- [ ] Add `GRAPHITI_LLM_PROVIDER` toggle (`local` | `groq`) with `local` preserved as
      fallback
- [ ] Update `guardkit/.mcp.json` and `guardkit/.guardkit/graphiti.yaml` as reference
- [ ] Roll out to actively-used repos in waves (guardkit → forge/specialist-agent →
      rest)
- [ ] Smoke-test one `guardkit graphiti seed` run per repo after the switch
- [ ] Verify MCP-based queries (`mcp__graphiti__search_nodes`) still work from Claude
      Code after the MCP server switch

### Non-deliverables (explicitly out of scope)

- Option B (AWS Bedrock via LiteLLM) — not implementing; just evaluated in the
  research doc
- Changing the FalkorDB host / port / embedding dimensions
- Changing the local embedding model
- Retired repos (`architect-agent_delete_me`,
  `deepagents-player-coach-exemplar-original`)

## Implementation Notes

### Suggested rollout order

1. **Wave 1 — guardkit itself**: update `.mcp.json` + `.guardkit/graphiti.yaml`, code
   changes to support `groq` provider, tests, smoke-test seed run.
2. **Wave 2 — GPU-bound users**: `agentic-dataset-factory`, `forge`,
   `specialist-agent` — these directly benefit from the GB10 GPU being freed.
3. **Wave 3 — remaining active repos**: `nats-infrastructure`, `nats-core`,
   `lpa-platform`, `dotnet-functional-fastendpoints-exemplar`,
   `youtube-transcript-mcp`, `require-kit`, deepagents exemplars.
4. **Wave 4 — MCP-only repos**: `agentecflow_platform`, `deepagents` — only need
   `.mcp.json` updated.

### GB10 decommissioning

Once all waves are complete, the Qwen2.5-14B vLLM instance on port 8000 can be
stopped. Keep port 8001 (embeddings) running. Update
`docs/reference/graphiti-macbook-offload.md` — the GB10/MacBook toggle pattern there
is being replaced by the local/cloud toggle.

### Open question — reranker cost

The research doc uses `openai/gpt-oss-20b` as the reranker. Reranking happens per
**query**, not per seed, so reranker costs could dwarf entity-extraction costs.
Quantify this before committing to Groq-for-reranker, or fall back to a cheaper
strategy (disable reranker? use embedding-only?).

## Notes

- Today's date: 2026-04-17
- Research doc author left a cost table showing light usage at £0.50-2/mo — should be
  negligible even with some reranker traffic.
- The research doc's "Thinking Mode Incompatibility" warning (March 2026) is the key
  constraint driving GPT-OSS over Qwen3 — do not silently swap the model later.
