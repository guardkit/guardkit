# AutoBuild Harness Migration: From Claude Code to LangGraph

**Date:** 19 May 2026  
**Author:** Rich Woollcott (with Claude AI research assistance)  
**Status:** URGENT — Decision Required by 1 June 2026  
**Deadline:** Anthropic enforces API key validation 15 June 2026  
**Related:** DECISION-DF-001 (no cloud API on critical path), autobuild_local_vllm.md, guardkitfactory, adk-a2a-agent-framework-assessment.md

---

## 1. The Problem

AutoBuild currently uses Claude Code as the coding agent harness. The local-inference pattern works by setting `ANTHROPIC_BASE_URL` to point at llama-swap (or vLLM) on GB10, with a dummy `ANTHROPIC_API_KEY`. This makes Claude Code think it's talking to Anthropic's API but actually routes inference to local models.

From **15 June 2026**, Anthropic will enforce real API key validation. This breaks the redirect pattern — Claude Code will refuse to operate without a valid Anthropic API key, regardless of where the base URL points.

This is not a theoretical risk. In January 2026, Anthropic blocked OpenCode from using Claude via consumer OAuth tokens. The pattern of tightening third-party access to Claude infrastructure is clear and accelerating. Anthropic's track record with their developer customer base over the past six months gives no reason to expect this trajectory to reverse.

**Impact:** AutoBuild — the core build engine of the entire software factory — stops working on local models. This directly violates DECISION-DF-001 (no cloud API on critical path).

**Timeline:** 27 days to migrate. The replacement must be validated before June 15.

---

## 2. The Broader Decision: Replace Claude Code Entirely

This migration should not be scoped narrowly to AutoBuild alone. The question is: **what replaces Claude Code for both automated builds and interactive daily coding?**

Framing it this way avoids throwaway work. A tactical fix for AutoBuild that doesn't address the interactive coding question creates two tools to maintain and a second migration later. Instead, we adopt one tool for interactive coding and one framework for agent development, with both decisions made together.

### 2.1 Empirical Evidence: LangChain/DeepAgents vs Claude Agents SDK

The fleet's own build history provides the strongest signal:

| Agent | Framework | Build Experience |
|-------|-----------|-----------------|
| **agentic-dataset-factory** | LangChain/DeepAgents | 90-95% working out of the box |
| **specialist-agent (forge)** | LangChain/DeepAgents | 90-95% working out of the box |
| **jarvis** | LangChain/DeepAgents | 90-95% working out of the box |
| **study-tutor** | LangChain/DeepAgents | 90-95% working out of the box |
| **AutoBuild (guardkit)** | Claude Agents SDK / Claude Code | Consistently problematic, significant debugging |

This isn't coincidence. LangChain/LangGraph has massive real-world adoption (90M+ monthly downloads, used by Uber, JP Morgan, Klarna, Elastic). The Claude Agents SDK is a niche tool Anthropic built to showcase their own models, not to be a general-purpose agent framework. The training data, community support, and battle-testing reflect this gap directly.

The LangChain DeepAgents MCP server and documentation plugin mean that AI assistants (including Claude itself) have deep knowledge of how to build on this stack — which is why the agents built on it come together so much more easily.

### 2.2 The Two Decisions

| Concern | Tool | Rationale |
|---------|------|-----------|
| **Interactive daily coding** | OpenCode | Best-in-class open-source coding agent, model-agnostic, cross-platform |
| **Automated agent development (AutoBuild)** | LangGraph/DeepAgents | Proven stack, same framework as all other fleet agents, Python-native |

---

## 3. Interactive Coding: OpenCode

### 3.1 Why OpenCode

OpenCode is the community's answer to Claude Code — an open-source, provider-agnostic coding agent that does everything Claude Code does but without vendor lock-in.

**Key facts (May 2026):**
- 160K+ GitHub stars, 900+ contributors, 7.5M monthly developers
- 75+ model providers including local models via Ollama at zero API cost
- Available as CLI (TUI), desktop app, and IDE extensions (VS Code, Cursor, Zed, Windsurf)
- MIT licensed, fully open source
- LSP-driven self-correction (feeds compiler diagnostics back to the model)
- MCP support (Model Context Protocol)
- Built-in agents: Build (full development), Plan (read-only analysis)

**Cross-platform support:**
- **macOS:** `brew install anomalyco/tap/opencode` (CLI) or `brew install --cask opencode-desktop` (desktop app)
- **Windows:** `scoop install opencode` or `choco install opencode` (CLI), `scoop install extras/opencode-desktop` (desktop app). WSL recommended for best experience, native support also available.
- **Linux:** `brew install opencode`, `sudo pacman -S opencode` (Arch), `nix run nixpkgs#opencode`, or install script `curl -fsSL https://opencode.ai/install | bash`
- **All platforms:** `npm i -g opencode-ai@latest`

**Local model integration:** Configure OpenCode to point at llama-swap:

```json
{
  "provider": {
    "openai-compatible": {
      "apiKey": "local",
      "baseURL": "http://gb10:9000/v1",
      "models": {
        "qwen36-workhorse": {
          "name": "qwen36-workhorse",
          "maxTokens": 32768
        }
      }
    }
  }
}
```

**What it replaces:** Claude Code for all interactive coding on MacBook (planning, debugging, code review, ad-hoc development). Rich uses this daily instead of Claude Code.

### 3.2 Why Not Other Interactive Tools

- **Cursor/Copilot:** IDE-locked. Rich works terminal-first.
- **Aider:** Strong but pair-programming oriented, not autonomous agent. Less extensible.
- **Pi:** TypeScript/Node ecosystem, RPC mode feels wrong. Not a natural fit.
- **Gemini CLI:** Gemini models only — violates DECISION-DF-001.

---

## 4. AutoBuild: LangGraph/DeepAgents Coding Agent

### 4.1 The Core Insight

A coding agent is fundamentally an LLM with tools (read, write, edit, bash) in a loop. This is exactly what LangGraph does. The Player-Coach pattern is already proven in specialist-agent. The tools are standard file I/O and shell execution. There is no magic in Claude Code's harness that can't be built in LangGraph — and built better, because it becomes the same stack as everything else in the fleet.

### 4.2 What the Harness Actually Does

Before designing the replacement, here's what Claude Code provides in the AutoBuild context:

| Capability | How AutoBuild Uses It | LangGraph Equivalent |
|-----------|----------------------|---------------------|
| File read/write/edit | Player reads codebase, writes implementations | Custom tools (trivial — Python `pathlib` + diff) |
| Bash execution | Run tests, linters, type checkers | Custom tool (Python `subprocess`) |
| Session management | Multi-turn Player-Coach loop | LangGraph state + checkpointing |
| System prompt | CLAUDE.md defines Player/Coach behaviour | LangGraph node prompts |
| Tool calling | Model decides which tools to invoke | LangGraph `ToolNode` + `bind_tools` |
| Headless execution | Build Agent invokes as subprocess | Python module — direct invocation, no subprocess needed |
| Context management | Conversation history within context window | LangGraph state with summarisation/compaction |

### 4.3 Architecture

```
guardkit autobuild feature FEAT-XXX
    │
    ▼
┌─────────────────────────────────────────────┐
│  GuardKit AutoBuild Orchestrator (Python)    │
│  - Loads feature YAML + build plan           │
│  - Iterates waves and tasks                  │
│  - Manages Player-Coach turn-taking          │
│                                              │
│  ┌─────────────────────────────────────────┐ │
│  │  LangGraph Coding Agent                 │ │
│  │                                         │ │
│  │  State: files_modified, test_results,   │ │
│  │         coach_feedback, turn_count      │ │
│  │                                         │ │
│  │  Tools:                                 │ │
│  │   - read_file(path) → content           │ │
│  │   - write_file(path, content)           │ │
│  │   - edit_file(path, old, new)           │ │
│  │   - bash(command) → stdout/stderr       │ │
│  │   - list_directory(path) → entries      │ │
│  │                                         │ │
│  │  Nodes:                                 │ │
│  │   player_implement → tool_executor      │ │
│  │        ↕                                │ │
│  │   coach_validate → bash(tests/lint)     │ │
│  │        ↕                                │ │
│  │   [pass] → complete                     │ │
│  │   [fail] → player_implement (iterate)   │ │
│  │                                         │ │
│  │  LLM: ChatOpenAI(                       │ │
│  │    base_url="http://gb10:9000/v1",      │ │
│  │    model="qwen36-workhorse"             │ │
│  │  )                                      │ │
│  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### 4.4 Why This Works Better Than Claude Code

1. **Same stack as everything else.** One framework for all agents in the fleet. Same patterns, same debugging, same tooling.
2. **Python-native.** No subprocess invocation, no RPC, no TypeScript bridges. GuardKit imports the agent directly.
3. **LangGraph state and checkpointing.** Built-in persistence means the Player-Coach loop can survive crashes and resume — something Claude Code doesn't offer.
4. **LangSmith tracing.** Every tool call, every LLM invocation, every routing decision is traced. Better observability than Claude Code's logs.
5. **Model-agnostic by design.** `ChatOpenAI(base_url=...)` works with llama-swap, vLLM, Ollama, or any cloud API. No vendor-specific SDK.
6. **DeepAgents for higher-level patterns.** If the coding agent needs planning, sub-agents, or file system awareness, DeepAgents provides these on top of LangGraph.
7. **A2A future path.** The coding agent can be exposed as an A2A endpoint, enabling cloud-based build triggers to delegate to the local GB10 builder.
8. **Proven Player-Coach pattern.** specialist-agent already implements this exact loop in LangGraph with 0.93 architect / 0.90 PO scores. The template exists.

### 4.5 Cross-Platform Support

LangGraph is pure Python (MIT licensed, `pip install langgraph`). It runs anywhere Python runs:

- **macOS:** Native Python, homebrew Python, or conda
- **Windows:** Native Python, WSL, or conda
- **Linux:** System Python, pyenv, conda, or container
- **GB10 (Ubuntu):** System Python at `/usr/bin/python3` — already running all fleet agents
- **Docker:** Standard Python container — already the deployment model for fleet agents

LangGraph 1.0 is compatible with Python 3.9+ (tested through 3.13). LangGraph Studio CLI is also cross-platform (macOS, Windows, Linux).

No additional runtime dependencies beyond Python and the model provider. No Node.js, no Go, no Rust, no Bun.

---

## 5. Migration Plan

### Phase 1: OpenCode for Interactive Coding (This Week)

1. Install OpenCode on MacBook (`brew install anomalyco/tap/opencode`)
2. Configure for llama-swap (GB10:9000) as primary provider
3. Configure Anthropic API as fallback for complex tasks (if needed)
4. Create `AGENTS.md` in each fleet repo encoding project-specific context
5. Validate on a real coding task in the jarvis or specialist-agent repo
6. If satisfied, stop using Claude Code for daily interactive work

**Risk:** Low. OpenCode is a direct replacement for interactive use. If it doesn't work well with local models, fall back to Anthropic API through OpenCode (still no Claude Code dependency).

### Phase 2: LangGraph Coding Agent for AutoBuild (Weeks 2-3)

1. **Create the coding agent tools** — `read_file`, `write_file`, `edit_file`, `bash`, `list_directory`. These are trivial Python implementations (~50 lines each).
2. **Build the Player-Coach graph** — Adapt the specialist-agent Player-Coach pattern. The graph topology is: `player_implement` → `tool_executor` → `coach_validate` → `tool_executor` → `[pass/fail routing]`.
3. **Wire LLM connection** — `ChatOpenAI(base_url="http://gb10:9000/v1", model="qwen36-workhorse")`. Already proven in all fleet agents.
4. **Integrate with GuardKit** — Replace the Claude Code subprocess invocation with a direct Python import of the LangGraph agent. The `guardkit autobuild` CLI interface stays the same.
5. **Validate on known task** — Run TASK-GLI-004 (the existing test case from `autobuild_local_vllm.md`).
6. **Full feature build** — Run a complete multi-wave feature build to validate end-to-end.

**Risk:** Medium. The coding agent tools are simple but the `edit_file` tool (applying diffs reliably) is the hardest part. The specialist-agent's existing tools and LangGraph patterns significantly reduce this risk.

### Phase 3: Cutover (Week 4, Before June 15)

1. Switch `guardkit autobuild` to use the LangGraph coding agent
2. Remove Claude Code dependency from guardkit
3. Document the migration in an ADR
4. Update `autobuild_local_vllm.md` with new setup instructions

---

## 6. What This Preserves

| Concern | Status |
|---------|--------|
| DECISION-DF-001 (no cloud API on critical path) | **Strengthened** — no Anthropic SDK dependency at all |
| Player-Coach methodology | **Unchanged** — same loop, different execution engine |
| GuardKit CLI interface | **Unchanged** — `guardkit autobuild` still works the same way |
| Feature specs, build plans, slash commands | **Unchanged** — methodology layer is harness-agnostic |
| NATS integration | **Unchanged** — `--nats` flag still works |
| Graphiti knowledge capture | **Unchanged** — happens at GuardKit level, not harness level |
| Fleet architecture direction | **Strengthened** — one framework (LangGraph) for all agents |
| A2A/ADK future path | **Enabled** — LangGraph agents can be wrapped as A2A endpoints |

---

## 7. What This Changes

| Before | After |
|--------|-------|
| Claude Code as interactive coding tool | OpenCode (model-agnostic, open source) |
| Claude Agents SDK as AutoBuild harness | LangGraph coding agent (same stack as fleet) |
| `ANTHROPIC_BASE_URL` redirect hack | `ChatOpenAI(base_url=...)` — first-class pattern |
| Subprocess invocation of Claude Code | Direct Python import of LangGraph agent |
| Anthropic SDK dependency on critical path | Zero vendor SDK dependency on critical path |
| Two agent frameworks (Claude SDK + LangGraph) | One agent framework (LangGraph) |

---

## 8. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| `edit_file` tool reliability with local models | Medium | Study how specialist-agent handles file edits. Consider whole-file write for small files, diff-based for large. Test with Qwen3.6-35B-A3B specifically. |
| LangGraph coding agent not ready by June 15 | Medium | OpenCode can also run headless (`opencode -m "..."` single-shot mode). Emergency fallback: use OpenCode in headless mode as interim AutoBuild harness. |
| Context window management for 32K models | Medium | LangGraph supports state summarisation and compaction. specialist-agent already handles this. |
| Losing Claude Code's model-specific optimisations | Low | Claude Code optimises for Claude models. We're running Qwen — those optimisations don't apply to us anyway. |
| OpenCode learning curve for daily use | Low | Same mental model as Claude Code (terminal agent with read/write/edit/bash). AGENTS.md replaces CLAUDE.md. |

---

## 9. Open Questions

| # | Question | Notes |
|---|----------|-------|
| 1 | Should the LangGraph coding agent live in `guardkit` or `guardkitfactory`? | Probably `guardkitfactory` — it's the build pipeline orchestrator. GuardKit CLI invokes it. |
| 2 | Can we reuse specialist-agent's tool implementations directly? | Yes for bash execution and file reading. Edit tool may need adaptation for code-specific diff patterns. |
| 3 | Should the coding agent use DeepAgents' file system tools or custom implementations? | Evaluate DeepAgents' built-in tools first — they may already cover read/write/edit/bash. |
| 4 | How does the coding agent handle git operations? | Same as today — GuardKit handles git externally, not the coding agent. |
| 5 | Should we expose the coding agent as an A2A endpoint immediately or defer? | Defer — get it working first, add A2A in a later phase. |
| 6 | Does OpenCode work well enough with Qwen3.6-35B-A3B for daily interactive use? | Validate this week. If not, use OpenCode with a cloud API fallback for interactive work while keeping local-only for AutoBuild. |

---

## 10. Decision Record

**Decision:** Adopt OpenCode for interactive coding + LangGraph coding agent for AutoBuild.

**Proposed ADRs:**
- `ADR-ARCH-031-opencode-replaces-claude-code-interactive.md`
- `ADR-ARCH-032-langgraph-coding-agent-replaces-claude-sdk-autobuild.md`

**Key principle:** One agent framework for the entire fleet. LangGraph is that framework. Interactive coding is a different concern — solved by the best available open-source tool (OpenCode), not by the agent framework.

---

## 11. References

### OpenCode
- [OpenCode website](https://opencode.ai)
- [OpenCode GitHub](https://github.com/anomalyco/opencode) — 160K+ stars
- [OpenCode download page](https://opencode.ai/download) — macOS, Windows, Linux
- [OpenCode docs](https://opencode.ai/docs/)
- [OpenCode vs Claude Code — Nimbalyst](https://nimbalyst.com/blog/opencode-vs-claude-code/) — May 2026
- [OpenCode vs Claude Code — DataCamp](https://www.datacamp.com/blog/opencode-vs-claude-code) — February 2026

### LangGraph / LangChain
- [LangGraph GitHub](https://github.com/langchain-ai/langgraph) — MIT licensed
- [LangGraph 1.0 announcement](https://blog.langchain.com/langchain-langgraph-1dot0/) — full backward compat
- [LangGraph docs](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangGraph Studio — cross-platform CLI](https://deepwiki.com/langchain-ai/langgraph-studio/2.1-installation)
- [Deep Agents SDK](https://github.com/langchain-ai/deep-agents)

### Landscape
- [Awesome CLI Coding Agents](https://github.com/bradAGI/awesome-cli-coding-agents) — curated directory
- [Best AI Coding Agents 2026 — MightyBot](https://mightybot.ai/blog/coding-ai-agents-for-accelerating-engineering-workflows/)
- [Claude Code Alternatives 2026 — MorphLLM](https://www.morphllm.com/comparisons/claude-code-alternatives)
