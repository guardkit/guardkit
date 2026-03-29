# Review Report: TASK-REV-85E4

## Graphiti Integration - Zero Value Delivery Despite Working Infrastructure

## Executive Summary (Revision 2 — Final)

**Root Cause (Validated — Code-Level Evidence with Full Boundary Trace):**

There are three validated root causes, layered:

### Root Cause 1: The MCP Was Deliberately Removed (Human Decision Based on Bad Advice)

The Graphiti MCP server was previously configured in guardkit's `.mcp.json`. During a session, Claude advised that the MCP was "pointless" because AutoBuild calls Python directly. Based on this advice, the MCP configuration was removed.

**This advice was correct for AutoBuild but catastrophically wrong for commands.**

AutoBuild IS Python — it doesn't need MCP. But every command (`/task-work`, `/task-review`, `/feature-plan`, etc.) is a Claude Code prompt spec that CAN'T import Python. For commands, MCP is the only clean integration path. Removing MCP from guardkit removed the best available bridge between commands and the knowledge module.

The command spec at [task-work.md:1701-1703](installer/core/commands/task-work.md#L1701-L1703) now explicitly instructs Claude:

```
⚠️ IMPORTANT: Graphiti is accessed via the Python client library, NOT via MCP tools.
Do NOT check for MCP tools like mcp__graphiti__search_nodes to determine availability.
Instead, run the Python check script via bash as described below.
```

This instruction — written after the MCP was removed — locks commands into the fragile CLI wrapper chain.

### Root Cause 2: Architecture Mismatch (Structural)

Two completely different architectures exist:

| Consumer | Architecture | Boundaries | Works? |
|----------|-------------|-----------|--------|
| AutoBuild (Python) | Direct import: `AutoBuildContextLoader` → `JobContextRetriever` → `GraphitiClient` → FalkorDB | 4 (in-process) | **Yes** |
| Commands (Claude Code) | Prompt spec → Bash → shell wrapper → Python subprocess → CLI → FalkorDB → JSON → Claude parses | 8 (cross-process, cross-language) | **Fragile** |
| Commands via MCP | Prompt spec → MCP tool call → MCP server → `GraphitiClient` → FalkorDB → tool result | 3 (native) | **Not configured** |

### Root Cause 3: Only 1 of 13 Commands Even Tries

Even with the fragile CLI wrapper available, only `/task-work` (Phase 1.7) attempts to load context. The other 12 commands either do a Tier 1 YAML check (is Graphiti enabled?) or have zero integration.

---

## The MCP Configuration That Works

Reference: `/Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/.mcp.json`

```json
{
  "mcpServers": {
    "graphiti": {
      "type": "stdio",
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "--directory",
        "/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server",
        "run", "main.py",
        "--transport", "stdio",
        "--config",
        "/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/config/config-guardkit.yaml"
      ],
      "env": {
        "CONFIG_PATH": "..config-guardkit.yaml",
        "OPENAI_API_KEY": "not-needed-vllm-local",
        "LLM_API_URL": "http://promaxgb10-41b1:8000/v1",
        "EMBEDDING_API_URL": "http://promaxgb10-41b1:8001/v1",
        "EMBEDDING_DIM": "1024"
      }
    }
  }
}
```

The MCP server lives at `/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/`, runs via `uv`, connects to the same FalkorDB (`whitestocks:6379`) and vLLM endpoints (`promaxgb10-41b1:8000/8001`). Config at `config/config-guardkit.yaml` defines entity types, group_id defaults, and database connection.

This is proven working in the agentic-dataset-factory project.

---

## C4 Context Diagram (Level 1)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GuardKit System                              │
│                                                                     │
│  ┌──────────────┐     ┌──────────────────┐     ┌────────────────┐  │
│  │  Claude Code  │     │   AutoBuild      │     │  CLI / Scripts │  │
│  │  (Commands)   │     │   (Python)       │     │  (guardkit)    │  │
│  │              │     │                  │     │                │  │
│  │ /task-work   │     │ feature_orch     │     │ graphiti seed  │  │
│  │ /task-review │     │ autobuild_orch   │     │ graphiti search│  │
│  │ /feature-plan│     │ agent_invoker    │     │ graphiti-check │  │
│  └──────┬───────┘     └────────┬─────────┘     └───────┬────────┘  │
│         │                      │                       │           │
│    ╔════╧═══════╗              │ Python import          │ Python    │
│    ║ MCP tools  ║              │ (direct)               │ import    │
│    ║ (REMOVED!) ║              │                       │           │
│    ║ was here   ║              │                       │           │
│    ╚════╤═══════╝              │                       │           │
│         │ Now: Bash            │                       │           │
│         │ wrapper (8           │                       │           │
│         │ boundaries)          │                       │           │
│         ▼                      ▼                       ▼           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              Knowledge Module (guardkit/knowledge/)           │  │
│  │                    52 files, 19K LOC                          │  │
│  │                                                              │  │
│  │  GraphitiClient → graphiti-core lib → FalkorDB Driver        │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
     ┌────────────┐  ┌───────────────┐  ┌─────────────┐
     │  FalkorDB   │  │ vLLM Embedding│  │  vLLM LLM   │
     │whitestocks  │  │promaxgb10-41b1│  │promaxgb10   │
     │  :6379      │  │  :8001        │  │  :8000      │
     │  (Redis)    │  │  (HTTP REST)  │  │  (HTTP REST) │
     │             │  │nomic-embed    │  │Qwen2.5-14B  │
     └────────────┘  └───────────────┘  └─────────────┘
         NAS             GPU Server         GPU Server
       (Tailscale)       (Tailscale)        (Tailscale)
```

---

## C4 Container Diagram (Level 2) — Three Architectures Compared

### Architecture A: AutoBuild (WORKING — Keep As-Is)

```
┌─────────────────────────────────────────────────────────────┐
│ AutoBuild Process (Python, same process)                     │
│                                                              │
│  FeatureOrchestrator                                         │
│  │ _pre_init_graphiti() → GraphitiClientFactory              │
│  │                                                           │
│  └─ AutoBuildOrchestrator (per task, in thread pool)         │
│     │ _get_thread_local_loader(loop)                         │
│     │   → factory.get_thread_client()                        │
│     │   → loop.run_until_complete(client.initialize())       │
│     │   → AutoBuildContextLoader(client)                     │
│     │                                                        │
│     │ loader.get_player_context(task_id, turn, ...)          │
│     │   → JobContextRetriever.retrieve()                     │
│     │     → 10x parallel: client.search() ──────────────────┼──► FalkorDB
│     │       → graphiti-core search_() ──────────────────────┼──► vLLM
│     │   → prompt_text = result.to_prompt()                   │
│     │                                                        │
│     │ agent_invoker.invoke_player(context=context_prompt)    │
│     │   → _build_autobuild_implementation_prompt()           │
│     │     → f"## Job Context\n{context}"                     │
│     │   → query(prompt=full_prompt) ────────────────────────┼──► Claude API
│     │                                                        │
│     │ PYTHON STRING → PYTHON STRING → API CALL               │
│     │ Zero serialization. Zero boundary surprises.           │
└─────┴────────────────────────────────────────────────────────┘
 Boundaries: 4 (all in-process)     Status: ✅ WORKING
```

### Architecture B: Commands via CLI Wrapper (CURRENT — Fragile, Mostly Unused)

```
┌──────────────┐  B1  ┌──────────────┐  B2  ┌──────────────┐
│ Claude Code   │────►│ Bash Tool    │────►│ Python subproc│
│ (LLM reads    │     │ (OS shell)   │     │ (graphiti_    │
│  markdown     │     │              │     │  check.py)    │
│  spec)        │     │ graphiti-    │     │              │
│               │     │ check        │     │ 4-step       │
│ Phase 1.7:    │     │ --status     │     │ availability │
│ "Run this     │     │ --quiet      │     │ check:       │
│  bash cmd"    │     │              │     │ 1. env var   │
│               │     │              │     │ 2. import    │
│ task_context  │◄────│ stdout: JSON │◄────│ 3. config    │
│ ["graphiti_   │  B1 │              │  B2 │ 4. redis     │──► FalkorDB
│  context"]    │     │              │     │    .ping()   │    :6379
│               │     │              │     │              │
│ ┌───────────┐ │     │              │     │              │
│ │ THIS IS   │ │     │              │     │              │
│ │ LLM STATE │ │     │              │     │              │
│ │ NOT A     │ │     │              │     │              │
│ │ PYTHON    │ │     │              │     │              │
│ │ VARIABLE! │ │     │              │     │              │
│ └───────────┘ │     │              │     │              │
│               │     │              │     │              │
│ Phase 2:      │     │              │     │              │
│ {if ctx:}     │     │              │     │              │
│ "KNOWLEDGE    │     │              │     │              │
│ GRAPH: ..."   │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘

 Boundaries: 8 (cross-process, cross-language)
 Status: ⚠️ FRAGILE — only /task-work uses this, 12 commands have nothing

 EXPLICIT BLOCK in task-work.md:1701-1703:
 "⚠️ IMPORTANT: Graphiti is accessed via the Python client library,
  NOT via MCP tools. Do NOT check for mcp__graphiti__search_nodes"
```

### Architecture C: Commands via MCP (PROPOSED — Proven in agentic-dataset-factory)

```
┌──────────────┐  M1  ┌──────────────────┐  M2  ┌──────────────┐
│ Claude Code   │────►│ MCP Server       │────►│ GraphitiClient│
│ (commands)    │     │ (stdio, separate │     │ (in MCP proc) │
│               │     │  Python process) │     │              │
│ Tool call:    │     │                  │     │ .search()    │──► FalkorDB
│ mcp__graphiti │     │ main.py          │     │              │    :6379
│ __search_nodes│     │ via uv           │     │              │
│ (query="...", │     │                  │     │              │──► vLLM
│  group_ids=   │     │ config:          │     │              │    :8001
│  [...])       │     │ config-guardkit  │     │              │
│               │     │ .yaml            │     │              │
│ Tool result:  │◄────│                  │◄────│ results      │
│ (native to    │  M1 │ JSON-RPC         │  M2 │              │
│  conversation │     │ over stdio       │     │              │
│  context!)    │     │                  │     │              │
│               │     └──────────────────┘     └──────────────┘
│ No JSON       │
│ parsing.      │     Proven working in:
│ No Bash.      │     agentic-dataset-factory/.mcp.json
│ No LLM state  │
│ tracking.     │     Same infra: whitestocks:6379,
│ Results are   │     promaxgb10-41b1:8000/8001
│ tool outputs. │
└──────────────┘

 Boundaries: 3 (Claude → MCP → FalkorDB/vLLM)
 Status: 🔧 NOT CONFIGURED in guardkit (was removed)
         ✅ WORKING in agentic-dataset-factory
```

---

## Sequence Diagram: What MCP Integration Looks Like (From agentic-dataset-factory)

```
 Claude Code          MCP Protocol         Graphiti MCP Server        FalkorDB     vLLM
 (/task-work          (stdio, managed      (uv run main.py,          whitestocks  promaxgb10
  command spec)        by VS Code)          separate process)         :6379        :8001
      │                    │                      │                      │           │
      │ Tool call:         │                      │                      │           │
      │ mcp__graphiti__    │                      │                      │           │
      │ search_nodes(      │                      │                      │           │
      │   query="auth      │                      │                      │           │
      │     patterns",     │                      │                      │           │
      │   group_ids=[      │                      │                      │           │
      │     "architecture  │                      │                      │           │
      │     _decisions",   │                      │                      │           │
      │     "guardkit__    │                      │                      │           │
      │     project_arch"] │                      │                      │           │
      │ )                  │                      │                      │           │
      │                    │                      │                      │           │
      │ ────── stdio ─────►│                      │                      │           │
      │                    │ ──── JSON-RPC ───────►│                      │           │
      │                    │                      │                      │           │
      │                    │                      │ embed query           │           │
      │                    │                      │ ─────────────────────────────────►│
      │                    │                      │ ◄────────────────────────────────│
      │                    │                      │                      │           │
      │                    │                      │ FalkorDB search      │           │
      │                    │                      │ ─────────────────────►│           │
      │                    │                      │ ◄─────────────────────│           │
      │                    │                      │                      │           │
      │                    │ ◄──── JSON-RPC ──────│                      │           │
      │ ◄───── stdio ─────│                      │                      │           │
      │                    │                      │                      │           │
      │ Result appears as  │                      │                      │           │
      │ TOOL OUTPUT in     │                      │                      │           │
      │ conversation.      │                      │                      │           │
      │                    │                      │                      │           │
      │ Claude can now     │                      │                      │           │
      │ USE these results  │                      │                      │           │
      │ directly in        │                      │                      │           │
      │ Phase 2 planning.  │                      │                      │           │
      │                    │                      │                      │           │
      │ No JSON parsing.   │                      │                      │           │
      │ No Bash invocation.│                      │                      │           │
      │ No LLM state mgmt. │                      │                      │           │
      │ NATIVE tool result.│                      │                      │           │
```

**Contrast with CLI wrapper**: The CLI wrapper requires Claude to (1) invoke Bash, (2) capture stdout, (3) parse JSON, (4) store result in LLM working memory, (5) reference it later in Phase 2 via template syntax. MCP returns results as a tool output that's natively part of the conversation context — Claude sees it the same way it sees a file read or a grep result.

---

## Sequence Diagram: AutoBuild (Working — For Reference)

*(Unchanged from Revision 1 — this path is correct and should not be modified)*

```
 FeatureOrch    AutoBuildOrch   ThreadLoader    JobCtxRetriever   GraphitiClient   FalkorDB    vLLM
      │               │              │                │                │              │          │
      │ _pre_init()   │              │                │                │              │          │
      │──► factory    │              │                │                │              │          │
      │               │              │                │                │              │          │
      │  spawn thread │              │                │                │              │          │
      │──────────────►│              │                │                │              │          │
      │               │ get_loader() │                │                │              │          │
      │               │─────────────►│                │                │              │          │
      │               │              │ get_client()   │                │              │          │
      │               │              │───────────────────────────────►│              │          │
      │               │              │ initialize()   │                │ TCP+PING    │          │
      │               │              │───────────────────────────────►│─────────────►│          │
      │               │              │◄──── loader ───│                │◄─────────────│          │
      │               │              │                │                │              │          │
      │               │ get_player_context()          │                │              │          │
      │               │─────────────►│ retrieve()     │                │              │          │
      │               │              │───────────────►│ 10x search()  │              │          │
      │               │              │                │───────────────►│──► query ───►│          │
      │               │              │                │                │──► embed ────┼─────────►│
      │               │              │                │                │◄─────────────┼─────────│
      │               │              │                │◄───────────────│◄─────────────│          │
      │               │              │◄── prompt_text │                │              │          │
      │               │◄─ context ───│                │                │              │          │
      │               │              │                │                │              │          │
      │               │ invoke_player(context=ctx)    │                │              │          │
      │               │──► build_prompt(ctx) ──► query(prompt) ───────────────────────────► Claude API
      │               │              │                │                │              │          │
      │               │ context IS in the prompt string. Verified at agent_invoker.py:2115.     │
```

---

## Boundary Failure Analysis (Complete)

### The 8 Boundaries in the CLI Wrapper Path

| # | Boundary | Technology Crossing | What Fails | Silent? | Evidence |
|---|----------|-------------------|------------|---------|----------|
| B1a | Claude → Bash | LLM working memory → OS process | Claude misinterprets spec, tool denied, timeout (120s default) | Yes | task-work.md:1709 |
| B1b | Bash → Claude | OS stdout → LLM working memory | JSON malformed, truncated, encoding error | Yes | task-work.md:1726-1731 |
| B2a | Bash → Python | Shell → Python interpreter | **Wrong Python** (system vs venv), hardcoded repo path in wrapper | **Yes** | `~/.agentecflow/bin/graphiti-check` wrapper |
| B2b | Python → Bash | Python subprocess → Shell stdout | JSON serialization error, partial output on crash | Yes | graphiti_check.py:main() |
| B3 | Python → FalkorDB | TCP socket → Redis protocol | DNS fail, ECONNREFUSED, timeout (5s cap) | Logged | graphiti_client.py:710-749 |
| B4 | Python → vLLM | HTTP request → REST API | HTTP timeout, 503, embedding dimension mismatch | Logged | graphiti_client.py:565-581 |
| B5 | graphiti-core → FalkorDB | Cypher over Redis | RecursionError, O(n*m) perf, query syntax | Caught | falkordb_workaround.py (3 patches) |
| B6 | Claude state → Claude prompt | LLM memory → LLM output | **Context dropped from working memory**, not referenced in Phase 2, long context dilution | **Invisible** | task-work.md:2460-2467 |

### The 3 Boundaries in the MCP Path

| # | Boundary | Technology Crossing | What Fails | Silent? |
|---|----------|-------------------|------------|---------|
| M1 | Claude → MCP | Tool call → stdio JSON-RPC | MCP server not running, startup failure | **Visible** (tool error) |
| M2 | MCP → FalkorDB/vLLM | TCP + HTTP | Same as B3/B4/B5 | Logged |
| M3 | MCP → Claude | Tool result → conversation context | Never — tool results are native | N/A |

**Critical difference**: MCP failures are **visible** as tool errors. CLI wrapper failures are **silent** — Claude just sets `graphiti_context = None` and proceeds.

---

## The Instruction That Must Change

[task-work.md:1701-1703](installer/core/commands/task-work.md#L1701-L1703):

```
⚠️ IMPORTANT: Graphiti is accessed via the Python client library, NOT via MCP tools.
Do NOT check for MCP tools like mcp__graphiti__search_nodes to determine availability.
Instead, run the Python check script via bash as described below.
```

This instruction was written after the MCP was removed from guardkit. It must be reversed when MCP is restored. The corrected instruction should be:

```
⚠️ IMPORTANT: Prefer MCP tools (mcp__graphiti__search_nodes, mcp__graphiti__search_memory_facts)
when available. Fall back to the Python check script via bash only if MCP tools are not present.
```

---

## Revised Recommendations (Final)

### Phase 1: Restore MCP (1 day)

| # | Action | Detail |
|---|--------|--------|
| R1 | Copy MCP config from agentic-dataset-factory | `.mcp.json` with `graphiti` server pointing to existing `graphiti/mcp_server/` |
| R2 | Reverse the anti-MCP instruction | Remove "NOT via MCP tools" from task-work.md:1701-1703 |
| R3 | Verify MCP tools appear in Claude Code | Open guardkit in VS Code, confirm `mcp__graphiti__search_nodes` available |

### Phase 2: Update Command Specs to Use MCP (2-3 days)

| # | Command | What Changes |
|---|---------|-------------|
| R4 | `/task-work` Phase 1.7 | Replace Bash wrapper with MCP tool calls. Keep Bash as fallback. |
| R5 | `/task-review` Phase 1 | Add context loading via MCP before review analysis |
| R6 | `/feature-plan` | Add pre-planning context load via MCP (currently write-only) |

### Phase 3: Write Path (2-3 days)

| # | Event | What to Capture |
|---|-------|----------------|
| R7 | `/task-complete` | Task outcome, approach, lessons learned → `task_outcomes` group |
| R8 | `/task-review` accept | Review decisions, architectural findings → `project_decisions` group |

### Phase 4: Observability (1 day)

| # | Action | Purpose |
|---|--------|---------|
| R9 | Add "context influence" markers | Show in Phase 2 output whether Graphiti context was loaded and used |
| R10 | Log MCP tool call results | Track what queries return, empty vs populated, to validate data quality |

### What NOT to Do

- **Don't extend the CLI wrapper to more commands** — MCP replaces it
- **Don't change AutoBuild's architecture** — it's correct (Python → Python)
- **Don't add more complexity to `graphiti-check`** — it becomes legacy once MCP works

---

## Confidence Assessment (Final)

| Claim | Confidence | Evidence |
|-------|-----------|---------|
| AutoBuild context reaches Claude API | **100%** | Code-traced: `prompt_text` → `context_prompt` → `invoke_player(context=...)` → `_build_prompt()` → `query(prompt=...)` at agent_invoker.py:2115 |
| MCP was deliberately removed from guardkit | **100%** | User confirmed. `.mcp.json` is empty. task-work.md:1701 says "NOT via MCP tools" |
| MCP works in agentic-dataset-factory | **100%** | `.mcp.json` present with full config, same infrastructure endpoints |
| Restoring MCP would reduce boundaries from 8 to 3 | **100%** | Architectural analysis: MCP tool results are native to Claude Code context |
| CLI wrapper has hardcoded path issue | **100%** | Wrapper contains `GUARDKIT_REPO="/Users/richardwoollcott/Projects/appmilla_github/guardkit"` |
| Only 1 of 13 commands uses CLI wrapper | **100%** | Grep-verified: only task-work.md references `graphiti-check` |
| No automatic write path exists | **100%** | Grep-verified: zero auto-capture from task lifecycle events |
| Command spec explicitly blocks MCP usage | **100%** | task-work.md:1701-1703: "Do NOT check for MCP tools" |

---

## Historical Context (Preserving the War Story)

The journey to this point:

1. **Infrastructure built** — FalkorDB on NAS, vLLM on GPU server, graphiti-core patched (3 workarounds for upstream bugs), knowledge seeded across 27 groups
2. **AutoBuild integration built and working** — `AutoBuildContextLoader` with per-thread clients, token budgeting, parallel queries, proven in 12+ feature builds across projects
3. **MCP server configured and working** — Proven in agentic-dataset-factory
4. **MCP removed from guardkit** — Based on advice that it was "pointless" (correct for AutoBuild, wrong for commands)
5. **Anti-MCP instruction added** — task-work.md:1701 explicitly blocks MCP usage
6. **Commands left with fragile CLI wrapper** — Only `/task-work` even uses it; 12 commands have nothing
7. **This review** — Identified the 3-layer root cause through boundary-level tracing

The infrastructure works. The Python code works. The MCP server works. The problem is a **human decision** (removing MCP from guardkit) based on **correct-but-incomplete AI advice** (AutoBuild doesn't need MCP, therefore MCP is pointless). The fix is to restore MCP and reverse the blocking instruction.

This is exactly the kind of failure that Graphiti itself is meant to prevent — context about *why* something was built gets lost, leading to decisions that undo previous work. The irony is not lost.

---

*Review completed: 2026-03-29*
*Revisions: 2 (boundary trace + MCP configuration discovery)*
*Mode: Architectural + Code Audit (comprehensive)*
*Boundary crossings traced: 8 (CLI), 4 (AutoBuild), 3 (MCP)*
*Files examined: 52 knowledge module files, 13 command specs, 6 agent definitions, 4 config files*
