# Review Report: TASK-REV-D2B5 (Revised)

## Executive Summary

The embedding dimension mismatch (expected 768, got 1024) has **two interacting root causes**:

1. **Sparse per-project `graphiti.yaml`**: youtube-transcript-mcp's config only sets `project_id` and `enabled`, causing embedding provider to default to `openai` (1024-dim) instead of `vllm` (768-dim).
2. **Residual `.env` pollution**: guardkit's `.env` sets `GRAPH_STORE=falkordb` and `FALKORDB_HOST=whitestocks`. When the user runs commands from the guardkit project first, `load_dotenv()` sets these in `os.environ`. python-dotenv does **not** override existing env vars, so when the user `cd`s to youtube-transcript-mcp and runs autobuild, the FalkorDB connection vars persist but embedding vars were never set anywhere — creating a **split-brain config**: FalkorDB connection from residual env vars + OpenAI embeddings from yaml defaults.

**The `.env` file is largely redundant and actively harmful** for infrastructure config. All non-secret settings already have homes in `graphiti.yaml`. The `.env` should only contain secrets (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). Infrastructure config in `.env` creates a hidden config source that competes with `graphiti.yaml` and causes cross-session pollution.

## Review Details

- **Mode**: Root Cause Analysis / Architectural Review (Revised)
- **Depth**: Comprehensive
- **Task ID**: TASK-REV-D2B5
- **Date**: 2026-03-09

---

## C4 Context Diagram: Shared FalkorDB Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Developer Workstation                        │
│                                                                     │
│  ┌──────────────────────┐       ┌──────────────────────┐           │
│  │   guardkit project    │       │ youtube-transcript-   │           │
│  │                       │       │ mcp project           │           │
│  │ .guardkit/            │       │ .guardkit/            │           │
│  │   graphiti.yaml ✅    │       │   graphiti.yaml ❌    │           │
│  │   (FULL config)       │       │   (SPARSE - only      │           │
│  │                       │       │    project_id+enabled) │           │
│  │ .env                  │       │ .env                  │           │
│  │   OPENAI_API_KEY      │       │   OPENAI_API_KEY      │           │
│  │   GRAPH_STORE ⚠️      │       │   (no infra vars)     │           │
│  │   FALKORDB_HOST ⚠️    │       │                       │           │
│  │   FALKORDB_PORT ⚠️    │       │                       │           │
│  └──────────┬───────────┘       └──────────┬───────────┘           │
│             │                              │                        │
│             │ guardkit CLI (pip -e install) │                        │
│             │ shared Python runtime         │                        │
│             └──────────────┬───────────────┘                        │
│                            │                                        │
└────────────────────────────┼────────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
┌──────────────────┐ ┌─────────────┐ ┌───────────────────┐
│ FalkorDB         │ │ Dell GB10   │ │ OpenAI API        │
│ (whitestocks     │ │ (promaxgb10 │ │ (api.openai.com)  │
│  :6379)          │ │  :8001/v1)  │ │                   │
│                  │ │             │ │ text-embedding-3-  │
│ Stores 768-dim   │ │ nomic-embed │ │ small → 1024-dim  │
│ vectors from     │ │ -text-v1.5  │ │ (or 1536-dim)     │
│ vLLM seeding     │ │ → 768-dim   │ │                   │
└──────────────────┘ └─────────────┘ └───────────────────┘
```

## C4 Container Diagram: Config Resolution Chain

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        guardkit Python Package                          │
│                                                                         │
│  ┌─────────────────────┐                                               │
│  │ CLI Entry Point      │                                               │
│  │ (cli/main.py)        │                                               │
│  │                      │                                               │
│  │ 1. _load_env_files() ├──► Load .env from CWD (or walk up)           │
│  │    (module-level)     │    Sets os.environ vars                      │
│  └──────────┬───────────┘    (does NOT override existing!)             │
│             │                                                           │
│             ▼                                                           │
│  ┌─────────────────────┐                                               │
│  │ Config Loader         │                                               │
│  │ (knowledge/config.py) │                                               │
│  │                       │                                               │
│  │ 2. get_config_path()  ├──► Strategy 1: _find_project_root(cwd)      │
│  │    Finds graphiti.yaml│    Walks up from CWD looking for .guardkit/  │
│  │                       │    Returns FIRST .guardkit/ found            │
│  │                       │                                               │
│  │ 3. load_graphiti_     │    Priority (highest to lowest):             │
│  │    config()           │    ┌─────────────────────────────────┐       │
│  │                       │    │ 1. Environment Variables        │       │
│  │                       │    │    (os.environ, from .env or    │       │
│  │                       │    │     shell session)              │       │
│  │                       │    ├─────────────────────────────────┤       │
│  │                       │    │ 2. YAML file values             │       │
│  │                       │    │    (from project graphiti.yaml) │       │
│  │                       │    ├─────────────────────────────────┤       │
│  │                       │    │ 3. Hardcoded Defaults           │       │
│  │                       │    │    embedding_provider: "openai" │       │
│  │                       │    │    graph_store: "neo4j"         │       │
│  │                       │    │    falkordb_host: "localhost"   │       │
│  │                       │    └─────────────────────────────────┘       │
│  └──────────┬───────────┘                                               │
│             │                                                           │
│             ▼                                                           │
│  ┌─────────────────────┐                                               │
│  │ Graphiti Client       │                                               │
│  │ (graphiti_client.py)  │                                               │
│  │                       │                                               │
│  │ 4. _try_lazy_init()   ├──► Also calls load_dotenv() (no path)       │
│  │                       │    Redundant but harmless when CLI           │
│  │                       │    already loaded .env                       │
│  │                       │                                               │
│  │ 5. _build_embedder()  ├──► if provider=="openai": return None       │
│  │                       │    (uses graphiti-core OpenAI default)       │
│  │                       │    if provider=="vllm": return               │
│  │                       │    OpenAIEmbedder(base_url=...)              │
│  └───────────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────────┘
```

## Sequence Diagram: Successful Seeding (from guardkit project)

```
User                CLI main.py              config.py                graphiti_client.py         FalkorDB          vLLM (GB10)
 │                      │                       │                          │                      │                  │
 │  cd guardkit/        │                       │                          │                      │                  │
 │  guardkit graphiti   │                       │                          │                      │                  │
 │  seed --force        │                       │                          │                      │                  │
 │─────────────────────►│                       │                          │                      │                  │
 │                      │ _load_env_files()     │                          │                      │                  │
 │                      │ Load guardkit/.env    │                          │                      │                  │
 │                      │  ┌────────────────┐   │                          │                      │                  │
 │                      │  │OPENAI_API_KEY=…│   │                          │                      │                  │
 │                      │  │GRAPH_STORE=    │   │                          │                      │                  │
 │                      │  │  falkordb      │   │                          │                      │                  │
 │                      │  │FALKORDB_HOST=  │   │                          │                      │                  │
 │                      │  │  whitestocks   │   │                          │                      │                  │
 │                      │  │FALKORDB_PORT=  │   │                          │                      │                  │
 │                      │  │  6379          │   │                          │                      │                  │
 │                      │  └────────────────┘   │                          │                      │                  │
 │                      │                       │                          │                      │                  │
 │                      │  get_config_path()────►│                          │                      │                  │
 │                      │                       │ Strategy 1: find         │                      │                  │
 │                      │                       │ guardkit/.guardkit/      │                      │                  │
 │                      │                       │                          │                      │                  │
 │                      │  load_graphiti_config()│                          │                      │                  │
 │                      │                       │ YAML: embedding_provider │                      │                  │
 │                      │                       │   = vllm ✅              │                      │                  │
 │                      │                       │ YAML: graph_store        │                      │                  │
 │                      │                       │   = falkordb ✅          │                      │                  │
 │                      │                       │ ENV overrides: GRAPH_    │                      │                  │
 │                      │                       │   STORE=falkordb (same)  │                      │                  │
 │                      │                       │ Final: ALL CONSISTENT ✅ │                      │                  │
 │                      │                       │◄─────────────────────────│                      │                  │
 │                      │                       │                          │                      │                  │
 │                      │  initialize()─────────────────────────────────────►│                      │                  │
 │                      │                       │                          │ _build_embedder()    │                  │
 │                      │                       │                          │ provider=vllm        │                  │
 │                      │                       │                          │ → OpenAIEmbedder     │                  │
 │                      │                       │                          │   (base_url=         │                  │
 │                      │                       │                          │    promaxgb10:8001)  │                  │
 │                      │                       │                          │                      │                  │
 │                      │  add_episode()────────────────────────────────────►│                      │                  │
 │                      │                       │                          │  embed("text")───────────────────────────►│
 │                      │                       │                          │                      │                  │
 │                      │                       │                          │  ◄──────────────────────768-dim vector──│
 │                      │                       │                          │                      │                  │
 │                      │                       │                          │  store(768-dim)──────►│                  │
 │                      │                       │                          │                      │ ✅ Stored        │
 │                      │                       │                          │  ◄─────────────ok────│                  │
```

## Sequence Diagram: Failing AutoBuild (from youtube-transcript-mcp)

```
User                CLI main.py              config.py                graphiti_client.py         FalkorDB          OpenAI API
 │                      │                       │                          │                      │                  │
 │  (SAME terminal      │                       │                          │                      │                  │
 │   session - ran      │                       │                          │                      │                  │
 │   guardkit earlier)  │                       │                          │                      │                  │
 │                      │                       │                          │                      │                  │
 │  os.environ already  │                       │                          │                      │                  │
 │  has from prior run: │                       │                          │                      │                  │
 │  GRAPH_STORE=falkordb│                       │                          │                      │                  │
 │  FALKORDB_HOST=      │                       │                          │                      │                  │
 │    whitestocks       │                       │                          │                      │                  │
 │  FALKORDB_PORT=6379  │                       │                          │                      │                  │
 │                      │                       │                          │                      │                  │
 │  cd youtube-         │                       │                          │                      │                  │
 │  transcript-mcp/     │                       │                          │                      │                  │
 │  guardkit autobuild  │                       │                          │                      │                  │
 │  feature FEAT-2AAA   │                       │                          │                      │                  │
 │─────────────────────►│                       │                          │                      │                  │
 │                      │ _load_env_files()     │                          │                      │                  │
 │                      │ Load yt-mcp/.env      │                          │                      │                  │
 │                      │  ┌────────────────┐   │                          │                      │                  │
 │                      │  │OPENAI_API_KEY=…│   │                          │                      │                  │
 │                      │  │(no GRAPH_STORE) │   │                          │                      │                  │
 │                      │  │(no FALKORDB_*)  │   │                          │                      │                  │
 │                      │  │(no EMBEDDING_*) │   │                          │                      │                  │
 │                      │  └────────────────┘   │                          │                      │                  │
 │                      │  load_dotenv does NOT  │                          │                      │                  │
 │                      │  override existing     │                          │                      │                  │
 │                      │  GRAPH_STORE etc!      │                          │                      │                  │
 │                      │                       │                          │                      │                  │
 │                      │  get_config_path()────►│                          │                      │                  │
 │                      │                       │ Strategy 1: find         │                      │                  │
 │                      │                       │ yt-mcp/.guardkit/        │                      │                  │
 │                      │                       │ (NOT guardkit's!)        │                      │                  │
 │                      │                       │                          │                      │                  │
 │                      │  load_graphiti_config()│                          │                      │                  │
 │                      │                       │ YAML has only:           │                      │                  │
 │                      │                       │   project_id: yt-mcp     │                      │                  │
 │                      │                       │   enabled: true          │                      │                  │
 │                      │                       │                          │                      │                  │
 │                      │                       │ DEFAULTS fill gaps:      │                      │                  │
 │                      │                       │   embedding_provider:    │                      │                  │
 │                      │                       │     "openai" ❌          │                      │                  │
 │                      │                       │   graph_store: "neo4j"   │                      │                  │
 │                      │                       │                          │                      │                  │
 │                      │                       │ ENV OVERRIDES:           │                      │                  │
 │                      │                       │   GRAPH_STORE=falkordb   │                      │                  │
 │                      │                       │     (from prior session!)│                      │                  │
 │                      │                       │   FALKORDB_HOST=         │                      │                  │
 │                      │                       │     whitestocks          │                      │                  │
 │                      │                       │   EMBEDDING_PROVIDER:    │                      │                  │
 │                      │                       │     NOT SET → stays      │                      │                  │
 │                      │                       │     "openai" ❌          │                      │                  │
 │                      │                       │                          │                      │                  │
 │                      │                       │ RESULT: SPLIT-BRAIN ❌   │                      │                  │
 │                      │                       │   graph_store=falkordb ✅│                      │                  │
 │                      │                       │   falkordb_host=         │                      │                  │
 │                      │                       │     whitestocks ✅       │                      │                  │
 │                      │                       │   embedding_provider=    │                      │                  │
 │                      │                       │     openai ❌            │                      │                  │
 │                      │                       │◄─────────────────────────│                      │                  │
 │                      │                       │                          │                      │                  │
 │                      │  initialize()─────────────────────────────────────►│                      │                  │
 │                      │                       │                          │ _build_embedder()    │                  │
 │                      │                       │                          │ provider=openai      │                  │
 │                      │                       │                          │ → returns None       │                  │
 │                      │                       │                          │ (use graphiti-core   │                  │
 │                      │                       │                          │  OpenAI default)     │                  │
 │                      │                       │                          │                      │                  │
 │                      │                       │                          │ Connect to FalkorDB──►│                  │
 │                      │                       │                          │ whitestocks:6379 ✅  │  ✅ Connected    │
 │                      │                       │                          │                      │                  │
 │                      │  search("query")──────────────────────────────────►│                      │                  │
 │                      │                       │                          │  embed("query")──────────────────────────►│
 │                      │                       │                          │                      │                  │
 │                      │                       │                          │  ◄────────────────────1024-dim vector───│
 │                      │                       │                          │                      │                  │
 │                      │                       │                          │ search(1024-dim)─────►│                  │
 │                      │                       │                          │                      │                  │
 │                      │                       │                          │  ◄──── ❌ DIMENSION ──│                  │
 │                      │                       │                          │        MISMATCH:     │                  │
 │                      │                       │                          │        expected 768  │                  │
 │                      │                       │                          │        got 1024      │                  │
```

## Root Cause: Three Config Sources Create Split-Brain

The config resolution has **three competing sources** with a layered priority that creates a fragile system:

```
┌───────────────────────────────────────────────────────────────┐
│                    Config Resolution Order                     │
│                                                               │
│  Priority 1: os.environ (from .env + shell session residue)  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ GRAPH_STORE=falkordb     ← from guardkit .env (residual)│ │
│  │ FALKORDB_HOST=whitestocks ← from guardkit .env (residual)│ │
│  │ FALKORDB_PORT=6379        ← from guardkit .env (residual)│ │
│  │ EMBEDDING_PROVIDER        ← NOT SET (never in any .env)  │ │
│  │ EMBEDDING_BASE_URL        ← NOT SET (never in any .env)  │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          │                                    │
│                     fills gaps                                │
│                          ▼                                    │
│  Priority 2: graphiti.yaml (per-project)                     │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ project_id: youtube-transcript-mcp                      │ │
│  │ enabled: true                                           │ │
│  │ (ALL OTHER FIELDS: absent → fall through to defaults)   │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          │                                    │
│                     fills gaps                                │
│                          ▼                                    │
│  Priority 3: Hardcoded Defaults                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ embedding_provider: "openai"  ← USED ❌                 │ │
│  │ embedding_base_url: None      ← USED (OpenAI default)   │ │
│  │ embedding_model: "text-embedding-3-small" ← USED        │ │
│  │ graph_store: "neo4j"          ← OVERRIDDEN by env ✅    │ │
│  │ falkordb_host: "localhost"    ← OVERRIDDEN by env ✅    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  RESULT: FalkorDB=whitestocks ✅ + Embeddings=OpenAI ❌     │
│          = DIMENSION MISMATCH                                 │
└───────────────────────────────────────────────────────────────┘
```

### Why This Is Fragile

The issue is **non-deterministic** because it depends on terminal session history:

| Scenario | FalkorDB Connection | Embedding Provider | Result |
|----------|--------------------|--------------------|--------|
| Fresh terminal, run from yt-mcp | `neo4j`/`localhost` (default) | `openai` (default) | **Graphiti disabled** (can't connect to neo4j) |
| After running guardkit first, then cd to yt-mcp | `falkordb`/`whitestocks` (residual env) | `openai` (default) | **DIMENSION MISMATCH** |
| With complete yt-mcp graphiti.yaml | `falkordb`/`whitestocks` (yaml) | `vllm` (yaml) | **Works correctly** |

In the first scenario, Graphiti would silently disable itself (no FalkorDB at localhost). In the second scenario (the one observed), it connects but mismatches. Only the third works.

## Analysis: Is `.env` Redundant?

### What `.env` Currently Provides

**guardkit/.env:**
```
OPENAI_API_KEY=sk-proj-...     ← SECRET (needed)
GRAPH_STORE=falkordb            ← Infrastructure (REDUNDANT - in graphiti.yaml)
FALKORDB_HOST=whitestocks       ← Infrastructure (REDUNDANT - in graphiti.yaml)
FALKORDB_PORT=6379              ← Infrastructure (REDUNDANT - in graphiti.yaml)
```

**youtube-transcript-mcp/.env:**
```
OPENAI_API_KEY=sk-proj-...     ← SECRET (needed for OpenAI LLM, not for vLLM embeddings)
```

### What `graphiti.yaml` Already Handles

Looking at guardkit's `graphiti.yaml` — it already has ALL the infrastructure config:

```yaml
graph_store: falkordb
falkordb_host: whitestocks
falkordb_port: 6379
llm_provider: vllm
llm_base_url: http://promaxgb10-41b1:8000/v1
llm_model: claude-sonnet-4-6
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:8001/v1
embedding_model: nomic-embed-text-v1.5
```

### `.env` Should ONLY Contain Secrets

| Setting | Belongs In | Reason |
|---------|-----------|--------|
| `OPENAI_API_KEY` | `.env` | Secret - must not be committed |
| `ANTHROPIC_API_KEY` | `.env` | Secret - must not be committed |
| `GRAPH_STORE` | `graphiti.yaml` | Infrastructure config - committed, versioned |
| `FALKORDB_HOST` | `graphiti.yaml` | Infrastructure config - committed, versioned |
| `FALKORDB_PORT` | `graphiti.yaml` | Infrastructure config - committed, versioned |
| `EMBEDDING_PROVIDER` | `graphiti.yaml` | Infrastructure config - committed, versioned |
| `EMBEDDING_BASE_URL` | `graphiti.yaml` | Infrastructure config - committed, versioned |
| `EMBEDDING_MODEL` | `graphiti.yaml` | Infrastructure config - committed, versioned |
| `LLM_PROVIDER` | `graphiti.yaml` | Infrastructure config - committed, versioned |
| `LLM_BASE_URL` | `graphiti.yaml` | Infrastructure config - committed, versioned |
| `LLM_MODEL` | `graphiti.yaml` | Infrastructure config - committed, versioned |

### Why Duplicating Infra Config in `.env` Is Harmful

1. **Cross-session pollution**: `load_dotenv()` puts values in `os.environ`. If user runs guardkit from project A, then `cd`s to project B, project A's env vars persist and override project B's defaults. This is the exact bug we're investigating.

2. **Hidden config source**: Developers forget `.env` exists. `graphiti.yaml` is the documented, versioned config. `.env` is gitignored and invisible.

3. **Precedence confusion**: Env vars override yaml values. So a stale `.env` with `GRAPH_STORE=neo4j` would silently override a correct `graphiti.yaml` that says `graph_store: falkordb`.

4. **`--copy-graphiti` only copies yaml**: `guardkit init --copy-graphiti` copies `graphiti.yaml` but NOT `.env`. So the "copy config to new project" workflow only works if all infra config lives in yaml.

### Recommendation: Clean `.env` of Infrastructure Config

**guardkit/.env** should become:
```
# GuardKit Environment Variables
# Only secrets go here - infrastructure config is in .guardkit/graphiti.yaml

OPENAI_API_KEY=sk-proj-...
```

**youtube-transcript-mcp/.env** should become:
```
# GuardKit Environment Variables
# Only secrets go here - infrastructure config is in .guardkit/graphiti.yaml

# Only needed if using OpenAI providers (not needed for vLLM-only)
# OPENAI_API_KEY=sk-proj-...
```

## Findings (Revised)

### Finding 1 (PRIMARY): youtube-transcript-mcp graphiti.yaml is sparse

**Severity:** HIGH
**Files:** `~/Projects/appmilla_github/youtube-transcript-mcp/.guardkit/graphiti.yaml`

Only has `project_id` and `enabled`. All infrastructure config defaults to OpenAI/neo4j.

### Finding 2 (CONTRIBUTING): guardkit .env contains infrastructure config

**Severity:** HIGH
**File:** `/Users/richardwoollcott/Projects/appmilla_github/guardkit/.env`

`GRAPH_STORE`, `FALKORDB_HOST`, `FALKORDB_PORT` in `.env` creates residual env var pollution across terminal sessions. These values duplicate what's already in `graphiti.yaml`.

### Finding 3: `--copy-graphiti` flag exists but wasn't used for youtube-transcript-mcp

**Severity:** MEDIUM

`guardkit init --copy-graphiti` or `guardkit init --copy-graphiti-from ~/path/to/guardkit` would have copied the full `graphiti.yaml` including embedding config. This flag exists but isn't prominent enough in the workflow.

### Finding 4: Default `guardkit init` only writes project_id to graphiti.yaml

**Severity:** MEDIUM
**File:** `guardkit/cli/init.py:319-370`

`write_graphiti_config()` only sets `project_id`. It doesn't copy infrastructure config from any source. Users must know to use `--copy-graphiti` flag.

### Finding 5: No validation warns about embedding dimension mismatch risk

**Severity:** LOW

When Graphiti connects to FalkorDB, there's no check that the configured embedding model's dimensions match the stored vector dimensions.

### Finding 6: coach_validator.py env stripping (unchanged from initial review)

**Severity:** MEDIUM
**File:** `guardkit/orchestrator/quality_gates/coach_validator.py:1191`

`env={"PYTHONPATH": new_pythonpath}` replaces entire environment. Should merge.

## Recommendations (Revised)

### Fix 1: Complete youtube-transcript-mcp graphiti.yaml (Immediate)

**Priority:** P0 — Fixes the dimension mismatch immediately.

```yaml
# Graphiti Knowledge Graph Configuration
project_id: youtube-transcript-mcp
enabled: true

# Shared FalkorDB infrastructure (must match guardkit config)
graph_store: falkordb
falkordb_host: whitestocks
falkordb_port: 6379
timeout: 30.0
max_concurrent_episodes: 3

# LLM provider for entity extraction
llm_provider: vllm
llm_base_url: http://promaxgb10-41b1:8000/v1
llm_model: claude-sonnet-4-6

# Embedding provider - MUST match seeding model for shared FalkorDB
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:8001/v1
embedding_model: nomic-embed-text-v1.5
```

### Fix 2: Remove infrastructure config from guardkit .env (Immediate)

**Priority:** P0 — Prevents cross-session pollution.

Change `guardkit/.env` from:
```
OPENAI_API_KEY=sk-proj-...
GRAPH_STORE=falkordb
FALKORDB_HOST=whitestocks
FALKORDB_PORT=6379
```

To:
```
# Only secrets go here — infrastructure config is in .guardkit/graphiti.yaml
OPENAI_API_KEY=sk-proj-...
```

This also means youtube-transcript-mcp's `.env` only needs `OPENAI_API_KEY` if OpenAI is actually used. With vLLM-only config, it may not need a `.env` at all (the key is passed via `api_key="local-key"` placeholder in `_build_embedder()`).

### Fix 3: Make `--copy-graphiti` the default for `guardkit init` when graphiti.yaml exists in parent

**Priority:** P1 — Prevents sparse configs for new projects.

When `guardkit init` detects a `.guardkit/graphiti.yaml` in a parent directory (Strategy 1 walkup), automatically offer to copy it:

```
guardkit init
  ✓ Applied template: default
  ℹ Found existing graphiti.yaml at ../guardkit/.guardkit/graphiti.yaml
  Copy infrastructure config to this project? [Y/n]:
```

This is the most ergonomic fix — users don't need to remember `--copy-graphiti`.

### Fix 4: Fix coach_validator env stripping (Quick)

**Priority:** P1

In `coach_validator.py:1191`:
```python
env={**os.environ, "PYTHONPATH": new_pythonpath},
```

### Fix 5: Add embedding dimension pre-flight check (Defensive)

**Priority:** P2

During `GraphitiClient.initialize()`, after building the embedder and connecting to FalkorDB, do a test embedding and compare dimensions with an existing stored vector. Log a clear error if mismatched.

### Fix 6: Log warning when config has sparse graphiti.yaml with shared FalkorDB

**Priority:** P3

When `load_graphiti_config()` reads a yaml that has `enabled: true` but is missing `embedding_provider` (using default), and the resolved `graph_store` is `falkordb`, emit a warning:

```
WARNING: Graphiti enabled with FalkorDB but embedding_provider defaulting to 'openai'.
If this FalkorDB instance was seeded with a different embedding provider,
search will fail with dimension mismatch. Set embedding_provider in graphiti.yaml.
```

## Decision Matrix (Revised)

| Fix | Impact | Effort | Risk | Recommendation |
|-----|--------|--------|------|----------------|
| Fix 1: Complete yt-mcp yaml | Fixes immediate issue | 5 min | None | **Do Now** |
| Fix 2: Clean guardkit .env | Prevents cross-session pollution | 2 min | Low | **Do Now** |
| Fix 3: Auto-copy graphiti init | Prevents for new projects | 2 hours | Low | Next sprint |
| Fix 4: Coach env merge | Prevents latent bugs | 10 min | Low | **Do Now** |
| Fix 5: Dimension pre-flight | Prevents future mismatch | 2 hours | Low | Next sprint |
| Fix 6: Sparse config warning | Early detection | 1 hour | None | Next sprint |

## Appendix

### Embedding Dimension Details

| Provider | Model | Default Dimensions | Configurable Range |
|----------|-------|-------------------|-------------------|
| vLLM (Dell GB10) | nomic-embed-text-v1.5 | **768** | 64-768 (Matryoshka) |
| OpenAI | text-embedding-3-small | **1536** | Reducible via `dimensions` param |

Note: The 1024 in the error (expected 768, got 1024) may indicate graphiti-core internally requests `dimensions=1024` from OpenAI, or the vector indexing uses 1024. Regardless, it doesn't match the 768 from nomic-embed-text-v1.5.

Even if OpenAI could be configured to output 768 dimensions, the embeddings would be in a **different semantic space** than nomic-embed-text-v1.5. Matching dimensions is necessary but not sufficient — the same model must be used for write and search.

### python-dotenv Behavior

`load_dotenv()` does **NOT** override existing environment variables by default. This means:
- If `GRAPH_STORE=falkordb` was set by loading guardkit's `.env` earlier in the session
- Then `load_dotenv("youtube-transcript-mcp/.env")` will NOT clear it
- The value persists silently across directory changes

To override, you'd need `load_dotenv(override=True)`, which guardkit does NOT use.

### Config Source Inventory

| Source | Scope | Persistence | Contains Secrets | Versioned |
|--------|-------|-------------|-----------------|-----------|
| `.env` | Per-project (gitignored) | Session (via os.environ) | Yes (API keys) | No |
| `graphiti.yaml` | Per-project (committed) | Permanent | No | Yes |
| Hardcoded defaults | Package-level | Permanent | No | Yes |
| Shell env vars | Session-wide | Until terminal closes | Possible | No |

### `guardkit init` Config Copy Paths

```
guardkit init                           → writes project_id only (SPARSE)
guardkit init --copy-graphiti           → auto-discovers parent yaml, copies all fields
guardkit init --copy-graphiti-from PATH → copies from explicit path
```

The default path (`guardkit init`) creates the sparse config that led to this bug. The `--copy-graphiti` path exists but requires the user to know about it.
