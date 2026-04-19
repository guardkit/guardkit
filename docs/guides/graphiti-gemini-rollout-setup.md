# Graphiti Gemini Rollout — Setup Guide

How GuardKit's Graphiti integration was switched from the local GB10 vLLM
(Qwen2.5-14B-FP8) to Google Gemini 2.5 Pro on the paid tier, and what needs to
be done to roll the same change out to any additional repo that shares the
FalkorDB knowledge graph.

- **Feature**: FEAT-G7B2
- **Smoke-test gate**: 2026-04-17 (Wave 2, passed)
- **Models in play**: `gemini-2.5-pro` (paid tier) for LLM, `nomic-embed-text-v1.5`
  at 1024 dims on GB10:8001 for embeddings (unchanged)

## Why the switch

The GB10 GPU was hosting two vLLM endpoints: Qwen2.5-14B on `:8000` for Graphiti
entity extraction, and nomic-embed on `:8001` for embeddings. Graphiti only
calls the LLM during ingestion/seeding, not queries, so the `:8000` endpoint
was mostly idle but still pinning GPU memory that fine-tuning and
dataset-factory work needed. Moving entity extraction to a cloud LLM frees the
GPU without changing query latency.

Gemini was chosen over Groq because (a) `graphiti-core` has a native
`GeminiClient` (no adapter code), (b) the Graphiti docs explicitly recommend
Gemini for structured output, and (c) Gemini 3.1 Pro was already planned for
Forge — one provider across the stack.

Pro on the paid tier (not Flash on the free tier) was chosen after free-tier
429s appeared during concurrent seeding.

## The two access paths

Graphiti is reached two different ways, each with its own config file and its
own venv. Both paths must end up on Gemini for the switch to be complete.

| Path | Used by | Config file | Venv |
|------|---------|-------------|------|
| **Python client** | CLI (`guardkit graphiti *`), AutoBuild, seeding | `<repo>/.guardkit/graphiti.yaml` | `<repo>/.venv` (guardkit's own) |
| **MCP server** | Claude Code sessions (`mcp__graphiti__*` tools) | `graphiti/mcp_server/config/config-<repo>.yaml` launched via `<repo>/.mcp.json` | `graphiti/mcp_server/.venv` (shared across repos) |

The Python client uses graphiti-core's built-in Gemini support. The MCP
server's Gemini support lives in a separate `google-genai` optional dependency
that must be installed into the MCP server's venv — see
[Post-mortem](#post-mortem-the-mcp-server-providers-sync-trap) below.

## Per-repo configuration shape

Every repo that talks to the shared FalkorDB needs both files updated. The
shape below is the canonical Gemini 2.5 Pro form; copy it per-repo and preserve
the per-repo `project_id` and `CONFIG_PATH`.

### `.guardkit/graphiti.yaml` (Python client)

```yaml
# Keep each repo's own project_id — do NOT overwrite with "guardkit".
project_id: <repo-specific>

# LLM — Gemini 2.5 Pro on the paid tier.
llm_provider: gemini
llm_model: gemini-2.5-pro
llm_max_tokens: 4096   # Caps output; prevents 16K default exceeding 32K context.

# Embeddings stay local on GB10:8001. The dimension is resolved from
# guardkit's KNOWN_EMBEDDING_DIMS based on embedding_model (768 for
# nomic-embed-text-v1.5). Set embedding_dimensions explicitly only to
# override the resolver (e.g. Matryoshka truncation). See
# .claude/reviews/TASK-REV-E8D1-review-report.md for the drift
# investigation that removed the previous hard-coded value.
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:8001/v1
embedding_model: nomic-embed-text-v1.5

# FalkorDB on the NAS (unchanged).
graph_store: falkordb
falkordb_host: whitestocks
falkordb_port: 6379

# Conservative for paid-tier start; tune up if no 429s after soak.
max_concurrent_episodes: 3
```

### `.mcp.json` (MCP server launch wrapper)

The MCP server needs `GOOGLE_API_KEY` in its process env and `LLM_MODEL` to
pin Pro (the shared config file defaults to Pro, but the env var overrides it
if the server is reused with a different default).

```jsonc
{
  "mcpServers": {
    "graphiti": {
      "type": "stdio",
      "defer_loading": false,
      "command": "/bin/bash",
      "args": [
        "-c",
        // Source .env first so GOOGLE_API_KEY is present in the exec'd process.
        // ${VAR} substitution from Claude Code's launch env is unreliable for MCP secrets.
        "set -a && . <repo>/.env && set +a && export LLM_MODEL=gemini-2.5-pro && exec /opt/homebrew/bin/uv --directory /Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server run main.py --transport stdio --config <repo>/config/config-<repo>.yaml"
      ],
      "env": {
        "CONFIG_PATH": "<repo-specific path to config-<repo>.yaml>",
        "LLM_MODEL": "gemini-2.5-pro",
        "EMBEDDING_API_URL": "http://promaxgb10-41b1:8001/v1",
        "EMBEDDING_DIM": "1024"
      }
    }
  }
}
```

The bash `-c` wrapper matters — see the companion memory
`feedback_mcp_env_loading.md` for why `${VAR}` substitution in Claude Code's
`env` block doesn't reliably pick up secrets on launch.

## Shared MCP server config

All repos share one `config-guardkit.yaml`-style file per repo inside
`graphiti/mcp_server/config/`. The `llm` block for every such file is:

```yaml
llm:
  provider: "gemini"
  model: ${LLM_MODEL:gemini-2.5-pro}   # Default to Pro; per-repo override via env.
  max_tokens: 4096
  providers:
    gemini:
      api_key: ${GOOGLE_API_KEY}
```

Embedder / database blocks stay as they were.

## Environment

A `GOOGLE_API_KEY` is required in every repo's `.env`. Get one at
<https://aistudio.google.com/apikey>. Never commit the raw key — the `.mcp.json`
wrapper sources `.env`; the CLI reads it from the shell env.

Paid-tier billing is attached at the Google Cloud project level, not the key
itself — make sure the key's project has billing enabled or extraction will
hit free-tier limits and start emitting 429s mid-seed.

## Smoke tests

Per repo, after the config change, run this minimal sequence to validate both
paths. Check 3 (write path) is the one that catches the MCP-server
providers-sync trap described below.

| # | Path | What to run | Pass signal |
|---|------|-------------|-------------|
| 1 | Env/config | `guardkit graphiti status` | Reports `llm_provider: gemini`, `healthy` |
| 2 | MCP read | `mcp__graphiti__search_nodes` against the repo's project group IDs | Returns nodes in <1s |
| 3 | MCP write | `mcp__graphiti__add_memory` with a test episode, then poll `get_episodes` / `search_memory_facts` | Episode or derived fact visible within 90s |
| 4 | Python write | `guardkit graphiti seed-system --force` (a small scope) | Completes, no 503s or 429s |

A time-to-visibility >90s on Check 3 suggests thinking-mode contamination on
`gemini-2.5-pro`. The shared config already caps `max_tokens: 4096`; if stalls
persist, consider falling back to `gemini-2.5-flash-lite` (no reasoning mode)
in that repo only.

## Post-mortem: the MCP server providers-sync trap

The Wave 2 MCP write path initially appeared blocked — `add_memory` returned
`Episode ... queued` but the episode never became visible via `get_episodes`
(waited 21+ minutes). The MCP server log showed:

```
graphiti_mcp_server - WARNING - Failed to create LLM client: Gemini client not available in current graphiti-core version
graphiti_mcp_server - INFO    - No LLM client configured - entity extraction will be limited
```

The warning message was misleading — the actual cause was an **optional
dependency**, not a version issue. `graphiti-core`'s `GeminiClient` does
`from google import genai` inside a try/except that re-raises as that
version-issue message. The `google-genai` package was missing from
`graphiti/mcp_server/.venv`.

The `mcp_server/pyproject.toml` already declares a `providers` optional group
that includes `google-genai`. It just isn't installed by `uv sync` unless
explicitly asked for:

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server
uv sync --extra providers
```

After that, restart Claude Code (the VSCode extension) so the MCP server
relaunches and picks up the newly-installed package. Confirm the startup log
now shows:

```
services.factories - INFO - Creating Gemini client
graphiti_mcp_server - INFO - Using LLM provider: gemini / gemini-2.5-pro
```

With no `Failed to create LLM client` warning underneath. Post-sync, a
smoke-test `add_memory` produced visible facts within 60s.

This install only needs to happen **once** per machine — the MCP server's
`.venv` is shared across all repos that point their `.mcp.json` at
`graphiti/mcp_server`. Adding a repo to the rollout doesn't require re-running
`uv sync --extra providers`.

## Rollout checklist (per repo)

Use this when onboarding a new repo to the shared FalkorDB / Gemini setup.

- [ ] `GOOGLE_API_KEY` present in `<repo>/.env`, billing enabled on the key's
      project.
- [ ] `<repo>/.guardkit/graphiti.yaml` matches the Python-client shape above,
      preserving the repo's own `project_id`. Do **not** set
      `embedding_dimensions` — guardkit resolves it from
      `KNOWN_EMBEDDING_DIMS` based on `embedding_model`. See
      `.claude/reviews/TASK-REV-E8D1-review-report.md`.
- [ ] `<repo>/.mcp.json` (where present) `graphiti` entry matches the
      MCP-launch shape above, `CONFIG_PATH` pointing at the correct
      `config-<repo>.yaml`. Do not touch other MCP entries (e.g.
      `specialist-agent`'s `architect-agent`).
- [ ] `graphiti/mcp_server/config/config-<repo>.yaml` `llm` block matches the
      shared-config shape above. Embedder/database blocks unchanged.
- [ ] MCP server venv has `google-genai` installed
      (`uv sync --extra providers` in `graphiti/mcp_server/`, one-time
      per machine).
- [ ] Claude Code restarted so the MCP server relaunches.
- [ ] Smoke tests 1–4 pass for this repo.
- [ ] Commit the repo's config changes separately with a message referencing
      FEAT-G7B2 / TASK-REV-C7A3.

## GB10 side — nothing to install, net less work

A common question after reading the post-mortem: *does GB10 also need
`uv sync --extra providers`?* No. The MCP server runs on the Mac, not on
GB10. GB10 only ever hosts vLLM HTTP endpoints that the MCP server (and the
Python client) call out to over the network.

```
Claude Code (Mac) ──launches──> graphiti/mcp_server (Mac, one shared .venv)
                                         │
                                         ├──> Google Gemini API (cloud, LLM extraction)
                                         └──> GB10:8001 (nomic embeddings, unchanged)
```

Net effect on GB10:

| GB10 endpoint | Before | After | Action |
|---|---|---|---|
| `:8000` — Qwen2.5-14B vLLM (LLM extraction) | Heavy Graphiti ingestion | **Idle** — no repo calls it | Decommission post-soak |
| `:8001` — nomic-embed-text-v1.5 vLLM (embeddings) | Graphiti + other clients | Unchanged | Keep running |

### Deferred GB10 follow-up (Wave 4, post-soak)

Tracked as TASK-G7B2-006 in `tasks/backlog/graphiti-gemini-rollout/`. Runs
only after Wave 3 soaks for a few days and no repo has regressed:

1. Confirm no repo has fallen back to vLLM (grep for `llm_provider: vllm`
   across all repos' `.guardkit/graphiti.yaml`).
2. Shut down the `:8000` Qwen vLLM process on GB10 — frees ~30 GB VRAM for
   fine-tuning / dataset-factory work (the original driver for this rollout).
3. Leave `:8001` nomic-embed running untouched — embeddings still go there.
4. Retire `docs/reference/graphiti-macbook-offload.md` — MacBook failover for
   the local LLM is no longer relevant.
5. Capture an ADR in Graphiti (`architecture_decisions` group) documenting
   the switch and its rationale.

## Key references

- Research doc (original decision): `docs/research/graphiti-cloud/graphiti-cloud-llm-config.md`
- Feature plan / subtasks: `tasks/backlog/graphiti-gemini-rollout/`
- Parent review: `.claude/reviews/TASK-REV-C7A3-review-report.md`
- Shared Graphiti architecture: `docs/guides/graphiti-claude-code-integration.md`
- MCP vs Python client group IDs: `.claude/rules/graphiti-knowledge-graph.md`,
  `.claude/rules/graphiti-knowledge.md`
