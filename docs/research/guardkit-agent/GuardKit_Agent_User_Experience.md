# GuardKit Agent: User Experience & Configuration Guide

> **Purpose**: Clarify how users interact with GuardKit Agent vs GuardKit (Claude Code), model configuration, and the path to a UI.
> **Date**: December 22, 2025

---

## Product Comparison: GuardKit vs GuardKit Agent

| Aspect | GuardKit (Claude Code) | GuardKit Agent (CLI) |
|--------|------------------------|---------------------|
| **Interface** | Claude Code terminal + slash commands | Standalone Python CLI |
| **Subscription** | Requires Claude Max ($200/mo) | No subscription - API/local |
| **Model Lock-in** | Claude only | Any LLM (Anthropic, Mistral, OpenAI, local) |
| **Commands** | `/task-work`, `/feature-plan`, etc. | `gka task work`, `gka feature plan`, etc. |
| **Context** | Loaded once per command | Job-specific context per turn |
| **Automation** | Manual command execution | Autonomous with checkpoints |
| **Quality Gates** | Enforced per command | Built into workflow |
| **Learning** | None | Knowledge Graph stores decisions |

---

## User Journey: GuardKit (Current - Claude Code)

```
┌─────────────────────────────────────────────────────────────────┐
│                    GUARDKIT (CLAUDE CODE)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. User opens Claude Code terminal                             │
│     $ claude                                                    │
│                                                                 │
│  2. User runs slash commands                                    │
│     > /feature-plan "Add dark mode support"                     │
│     > /task-work TASK-001                                       │
│     > /task-complete TASK-001                                   │
│                                                                 │
│  3. Each command executes within Claude Code session            │
│     - Uses Claude's model (Sonnet/Opus)                         │
│     - Markdown files provide context                            │
│     - User approves/rejects changes interactively               │
│                                                                 │
│  4. Manual workflow orchestration                               │
│     - User decides task order                                   │
│     - User runs each command sequentially                       │
│     - User handles errors and retries                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Pros
- Familiar Claude Code environment
- Interactive approval for each change
- No additional setup beyond Claude Max

### Cons
- Requires $200/mo Claude Max subscription
- Manual orchestration of multi-task work
- Single-threaded (one task at a time)
- No learning across sessions

---

## User Journey: GuardKit Agent (New - Standalone CLI)

```
┌─────────────────────────────────────────────────────────────────┐
│                    GUARDKIT AGENT (CLI)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. User initializes project (one-time)                         │
│     $ gka init                                                  │
│     ✓ Created .gka/gka.toml                                     │
│     ✓ Detected stack: react-typescript                          │
│     ✓ Generated 5 specialist agents                             │
│                                                                 │
│  2. User configures models (one-time)                           │
│     $ gka config model --default devstral-2                     │
│     $ gka config model --coach claude-sonnet                    │
│     # Or edit .gka/gka.toml directly                            │
│                                                                 │
│  3. User plans feature                                          │
│     $ gka feature plan "Add dark mode support"                  │
│     ✓ Created FEAT-a3f8 with 4 tasks                            │
│     ✓ Identified parallel groups: [1,2], [3], [4]               │
│                                                                 │
│  4. User starts autonomous execution                            │
│     $ gka feature work FEAT-a3f8 --parallel 2                   │
│                                                                 │
│     🚀 Starting feature: Add dark mode support                  │
│     📦 Stage 1: Running TASK-001, TASK-002 in parallel          │
│        ├── TASK-001: Player implementing... (turn 1/10)         │
│        │   Coach validating... ✅ Approved                       │
│        └── TASK-002: Player implementing... (turn 2/10)         │
│            Coach validating... ✅ Approved                       │
│                                                                 │
│     ⏸️ CHECKPOINT: Stage 1 complete. Review? [Y/n]              │
│                                                                 │
│     📦 Stage 2: Running TASK-003                                │
│        └── TASK-003: Player implementing... (turn 1/10)         │
│            Coach validating... 📝 Feedback                       │
│            Player implementing... (turn 2/10)                   │
│            Coach validating... ✅ Approved                       │
│                                                                 │
│     🎉 Feature FEAT-a3f8 completed!                             │
│        Tasks: 4/4 ✅                                             │
│        Total turns: 8                                            │
│        Time: 23 minutes                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Differences
1. **Autonomous orchestration** - GuardKit Agent handles task sequencing
2. **Parallel execution** - Multiple tasks run simultaneously in git worktrees
3. **Coach-Player loop** - Built-in validation prevents incomplete work
4. **Model flexibility** - Use cheaper models for routine work, expensive for review
5. **Checkpoints** - Human reviews at strategic points, not every change

---

## Model Configuration

### Configuration File: `.gka/gka.toml`

```toml
[project]
name = "my-app"
stack = "react-typescript"

#=============================================================================
# MODEL CONFIGURATION
#=============================================================================

[models]
# Default model for all agents
default = "devstral-2"

# Override per role (cost optimization)
player = "devstral-2"       # Implementation - use cheaper model
coach = "claude-sonnet"     # Validation - use stronger model for reasoning
architect = "claude-sonnet" # Planning - needs good reasoning

#-----------------------------------------------------------------------------
# ANTHROPIC (Direct API)
#-----------------------------------------------------------------------------
[models.claude-sonnet]
provider = "anthropic"
model = "claude-sonnet-4-20250514"
api_key_env = "ANTHROPIC_API_KEY"    # Read from environment variable
max_tokens = 8192

[models.claude-opus]
provider = "anthropic"
model = "claude-opus-4-20250514"
api_key_env = "ANTHROPIC_API_KEY"
# Use sparingly - most expensive

#-----------------------------------------------------------------------------
# MISTRAL (Recommended for cost efficiency)
#-----------------------------------------------------------------------------
[models.devstral-2]
provider = "mistral"
model = "devstral-2"
api_key_env = "MISTRAL_API_KEY"
max_tokens = 32768
# Currently FREE during preview, then ~$0.40/$2.00 per M tokens

[models.devstral-small]
provider = "mistral"
model = "devstral-small-2"
api_key_env = "MISTRAL_API_KEY"
# 24B model - can also run locally

#-----------------------------------------------------------------------------
# AWS BEDROCK (Enterprise - uses IAM credentials)
#-----------------------------------------------------------------------------
[models.bedrock-claude]
provider = "bedrock"
model = "anthropic.claude-sonnet-4-20250514-v1:0"
region = "us-east-1"
# Uses AWS credentials from environment or IAM role

[models.bedrock-mistral]
provider = "bedrock"
model = "mistral.mistral-large-2407-v1:0"
region = "us-east-1"

#-----------------------------------------------------------------------------
# AZURE OPENAI (Enterprise)
#-----------------------------------------------------------------------------
[models.azure-gpt4]
provider = "azure"
model = "gpt-4o"
api_key_env = "AZURE_OPENAI_API_KEY"
endpoint = "https://your-resource.openai.azure.com"
api_version = "2024-02-15-preview"
deployment = "gpt-4o-deployment"

#-----------------------------------------------------------------------------
# OPENAI (Direct)
#-----------------------------------------------------------------------------
[models.openai-gpt4]
provider = "openai"
model = "gpt-4o"
api_key_env = "OPENAI_API_KEY"

#-----------------------------------------------------------------------------
# LOCAL - OLLAMA ($0 cost)
#-----------------------------------------------------------------------------
[models.local-devstral]
provider = "ollama"
model = "devstral:24b"
endpoint = "http://localhost:11434"
# Requires: ollama pull devstral:24b

[models.local-qwen]
provider = "ollama"
model = "qwen2.5-coder:32b"
endpoint = "http://localhost:11434"

#-----------------------------------------------------------------------------
# LOCAL - vLLM (High performance)
#-----------------------------------------------------------------------------
[models.vllm-devstral]
provider = "vllm"
model = "mistralai/Devstral-Small-2505"
endpoint = "http://localhost:8000"
# Requires: vllm serve mistralai/Devstral-Small-2505

#=============================================================================
# COST CONTROLS
#=============================================================================

[models.budget]
daily_limit_usd = 10.0
warn_at_percent = 80
on_limit_reached = "switch_to_cheaper"  # or "warn", "stop"
fallback_model = "local-devstral"
```

### Setting API Keys

```bash
# Option 1: Environment variables
export ANTHROPIC_API_KEY="sk-ant-..."
export MISTRAL_API_KEY="..."
export OPENAI_API_KEY="sk-..."

# Option 2: Secure keyring storage
gka config set-secret ANTHROPIC_API_KEY "sk-ant-..."
gka config set-secret MISTRAL_API_KEY "..."

# Option 3: AWS credentials (for Bedrock)
aws configure  # Uses ~/.aws/credentials
```

### Switching Models

```bash
# Set default model
gka config model --default devstral-2

# Set model for specific role
gka config model --coach claude-sonnet
gka config model --player devstral-2

# Override for single command
gka task work TASK-001 --model claude-opus

# List available models
gka config model --list
```

---

## Cost Comparison

Assuming ~50k input tokens, ~10k output tokens per task:

| Model Config | Cost per Task | Monthly (100 tasks) | vs Claude Max |
|--------------|---------------|---------------------|---------------|
| Claude Max (GuardKit) | ~$0.50 | $200 (flat) | Baseline |
| Claude API (Sonnet) | ~$0.30 | ~$30 | 85% cheaper |
| Devstral 2 (all) | ~$0.04 | ~$4 | 98% cheaper |
| Mixed (Devstral + Claude coach) | ~$0.10 | ~$10 | 95% cheaper |
| Local (Ollama) | $0 | $0 | 100% cheaper |

---

## The Path to a UI

### Phase 1: CLI-First (Current Focus)

```
┌─────────────────────────────────────────────────────────────────┐
│                          CLI Interface                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  $ gka feature work FEAT-001 --parallel 2                       │
│                                                                 │
│  🚀 Feature: Add dark mode support                              │
│  ════════════════════════════════════════════════════════════   │
│                                                                 │
│  Stage 1 [2/2] ████████████████████████████████ 100%            │
│  ├── TASK-001: ✅ Completed (2 turns)                           │
│  └── TASK-002: ✅ Completed (3 turns)                           │
│                                                                 │
│  Stage 2 [1/1] ██████████████░░░░░░░░░░░░░░░░░░ 45%             │
│  └── TASK-003: 🔄 Turn 2/10 - Coach reviewing...                │
│                                                                 │
│  [ESC] Pause  [Q] Quit  [L] View logs  [R] Rewind               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 2: TUI (Terminal User Interface)

Using Rich/Textual for a more visual terminal experience:

```
┌─────────────────────────────────────────────────────────────────┐
│  GuardKit Agent                                      v0.2.0     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─ Features ──────────────────────────────────────────────────┐│
│  │ FEAT-001 Add dark mode      ▓▓▓▓▓▓▓▓░░░░  67%  In Progress ││
│  │ FEAT-002 User auth          ░░░░░░░░░░░░   0%  Planned     ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─ FEAT-001 Tasks ────────────────────────────────────────────┐│
│  │ ● TASK-001  Create ThemeContext     ✅ Done     2 turns     ││
│  │ ● TASK-002  Add toggle component    ✅ Done     3 turns     ││
│  │ ● TASK-003  Update components       🔄 Turn 2   45 sec      ││
│  │ ○ TASK-004  Integration tests       ⏸ Pending              ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─ Live Output (TASK-003) ────────────────────────────────────┐│
│  │ Coach: Checking test coverage...                            ││
│  │ Coach: Found 3 components without dark mode styles          ││
│  │ Coach: FEEDBACK - Please update Modal, Tooltip, Toast       ││
│  │ Player: Updating Modal.tsx with theme tokens...             ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  [F] New Feature  [T] New Task  [P] Pause  [Q] Quit             │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 3: Desktop/Web UI (Like Auto-Claude)

Auto-Claude is a great reference - it provides:
- **Kanban Board** - Track tasks from "Planning" to "Done"
- **Multiple Terminals** - Up to 12 AI-powered terminals
- **Git Worktrees** - Isolated workspaces for safe parallel development
- **Memory Layer** - Agents remember insights across sessions
- **Visual Progress** - Real-time tracking of agent work

```
┌─────────────────────────────────────────────────────────────────┐
│  GuardKit Agent                              ☐ □ ✕              │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    KANBAN BOARD                            │ │
│  │                                                            │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │ │
│  │  │ BACKLOG │ │IN PROG  │ │ REVIEW  │ │  DONE   │          │ │
│  │  ├─────────┤ ├─────────┤ ├─────────┤ ├─────────┤          │ │
│  │  │         │ │ ┌─────┐ │ │         │ │ ┌─────┐ │          │ │
│  │  │ TASK-04 │ │ │T-003│ │ │         │ │ │T-001│ │          │ │
│  │  │         │ │ │ 🔄  │ │ │         │ │ │ ✅  │ │          │ │
│  │  │         │ │ │Turn2│ │ │         │ │ └─────┘ │          │ │
│  │  │         │ │ └─────┘ │ │         │ │ ┌─────┐ │          │ │
│  │  │         │ │         │ │         │ │ │T-002│ │          │ │
│  │  │         │ │         │ │         │ │ │ ✅  │ │          │ │
│  │  │         │ │         │ │         │ │ └─────┘ │          │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─ Agent Terminals ───────────────────────────────────────────┐│
│  │ [Terminal 1: TASK-003]  [Terminal 2: Idle]  [+ New]        ││
│  │                                                             ││
│  │ 🎮 Player: Updating Modal.tsx with theme tokens...          ││
│  │    Modified: src/components/Modal.tsx                       ││
│  │    Added: ThemeContext import                               ││
│  │    Changed: backgroundColor from #fff to theme.background   ││
│  │ 🏀 Coach: Validating changes...                             ││
│  │    Running tests: 14/14 passed                              ││
│  │    Coverage: 87% (above 80% threshold)                      ││
│  │    ✅ APPROVED                                               ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  [▶ Start Feature] [⏸ Pause All] [⚙ Settings] [📊 Analytics]   │
└─────────────────────────────────────────────────────────────────┘
```

### UI Technology Options

| Option | Pros | Cons |
|--------|------|------|
| **Textual (TUI)** | Terminal-native, fast, cross-platform | Limited visuals |
| **Tauri (Desktop)** | Small binary, Rust backend, web frontend | More complex build |
| **Electron** | Full web stack, proven (like Auto-Claude) | Large binary |
| **Web (FastAPI + React)** | Team sharing, remote access | Requires server |
| **VS Code Extension** | IDE integration, familiar | VS Code only |

### Recommended Path

```
Phase 1 (Now):      CLI with Rich progress display
                    ↓
Phase 2 (v0.2):     Textual TUI for better task management
                    ↓
Phase 3 (v0.5):     Web UI (FastAPI + React) for team visibility
                    - Kanban board
                    - Live terminal output
                    - Analytics dashboard
                    ↓
Phase 4 (v1.0):     Desktop app (Tauri) for offline + local models
                    - Electron alternative (smaller binary)
                    - Native OS integration
```

---

## Integration with Task Backends

GuardKit Agent can optionally integrate with task management systems:

### Native (Default)
```toml
[tasks]
backend = "markdown"
path = ".guardkit/tasks/"
```

### Backlog.md Integration
```toml
[tasks]
backend = "backlog_md"
# Uses Backlog.md's markdown format and web UI
```

### Beads Integration
```toml
[tasks]
backend = "beads"
# Hash-based task IDs, agent memory, bd ready support
```

---

## Summary: When to Use What

| Scenario | Use | Why |
|----------|-----|-----|
| Already have Claude Max, simple tasks | **GuardKit** | No extra setup, familiar |
| Cost-conscious, want Devstral/local | **GuardKit Agent** | 7x-100% cheaper |
| Parallel task execution | **GuardKit Agent** | Git worktrees, concurrent work |
| Team visibility needed | **GuardKit Agent + UI** | Kanban, shared progress |
| Enterprise (Bedrock/Azure) | **GuardKit Agent** | Native cloud provider support |
| Offline development | **GuardKit Agent + Ollama** | Full local, no API needed |
| Learning/decision memory | **GuardKit Agent** | Knowledge Graph stores patterns |

---

## Next Steps

1. **CLI MVP** - Complete `gka task work` and `gka feature work`
2. **Model Abstraction** - Implement provider interface for multi-model
3. **TUI Enhancement** - Add Rich/Textual progress display
4. **Backend Integration** - Add Beads and Backlog.md backends
5. **Web UI** - FastAPI server + React frontend for visual management

---

*Document created: December 22, 2025*
