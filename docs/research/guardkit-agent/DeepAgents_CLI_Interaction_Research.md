# DeepAgents CLI Interaction Research: Stepping Stone to Purpose-Built GUI

> **Purpose**: Analyze how users will interact with GuardKit's DeepAgents implementation and evaluate the DeepAgents CLI as a transition path from Claude Code to a future purpose-built GUI.
> **Date**: December 24, 2025
> **Context**: Builds on `GuardKit_Agent_User_Experience.md` and `DeepAgents_Integration_Analysis.md`

---

## Executive Summary

The DeepAgents CLI provides an excellent stepping-stone from Claude Code's slash-command workflow to a future GUI. Its conversational interface, persistent memory, and skills system closely mirror the Claude Code experience while running on any LLM. This research validates Rich's intuition that raw Python shell commands would be too jarring for developers used to Claude Code.

**Key Finding**: The DeepAgents CLI can serve as GuardKit Agent's primary interface with minimal adaptation, preserving the conversational development experience while enabling model flexibility, cost optimization, and our custom adversarial cooperation patterns.

---

## Interaction Paradigm Comparison

### Current: Claude Code with GuardKit

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLAUDE CODE + GUARDKIT                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  $ claude                                                       │
│                                                                 │
│  > /feature-plan "Add dark mode support"                        │
│    ✓ Created FEAT-001 with 4 tasks                              │
│                                                                 │
│  > /task-work TASK-001                                          │
│    Agent working... reviewing files... writing code...          │
│    [Interactive approval for each change]                       │
│                                                                 │
│  > /task-complete TASK-001                                      │
│    ✓ Task marked complete                                       │
│                                                                 │
│  Interaction Style: Slash commands trigger workflows            │
│  Context: Single session, markdown files provide guidance       │
│  Model: Claude only                                             │
│  Approval: Per-change interactive                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Alternative Rejected: Raw Python Commands

```
┌─────────────────────────────────────────────────────────────────┐
│              PURE PYTHON CLI (NOT RECOMMENDED)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  $ python -m guardkit.agent plan "Add dark mode support"        │
│  $ python -m guardkit.agent work TASK-001 --model devstral     │
│  $ python -m guardkit.agent complete TASK-001                   │
│                                                                 │
│  Problems:                                                      │
│  ❌ No conversational flow - each command is isolated           │
│  ❌ No memory between commands                                   │
│  ❌ Feels like scripting, not development assistance            │
│  ❌ Jarring transition for Claude Code users                     │
│  ❌ No interactive approval workflow                             │
│  ❌ Requires learning new command syntax                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Proposed: DeepAgents CLI with GuardKit Skills

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEEPAGENTS CLI + GUARDKIT                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  $ deepagents --agent guardkit-dev                              │
│                                                                 │
│  You: Plan a feature for adding dark mode support               │
│                                                                 │
│  Agent: I'll create a structured feature plan for dark mode.    │
│         ⚙ read_file(/skills/feature-plan/SKILL.md)              │
│         ⚙ write_file(/features/FEAT-001.yaml)                   │
│         ✓ Created FEAT-001 with 4 tasks                         │
│         Dependencies: [1,2] → [3] → [4]                         │
│                                                                 │
│  You: Work on the first task                                    │
│                                                                 │
│  Agent: Starting TASK-001: Create ThemeContext                  │
│         ⚙ read_file(/memories/project-conventions.md)           │
│         ⚙ write_file(src/context/ThemeContext.tsx)              │
│         [Approval prompt with diff preview]                     │
│         ⚙ write_file(src/context/__tests__/ThemeContext.test.tsx)│
│         [Approval prompt]                                       │
│         ✓ TASK-001 implementation complete                      │
│                                                                 │
│  Interaction Style: Natural conversation triggers skills        │
│  Context: Persistent memory + project conventions               │
│  Model: Any (Devstral, Claude, GPT-4o, local)                   │
│  Approval: Configurable HITL with --auto-approve option         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## DeepAgents CLI Key Features for GuardKit

### 1. Conversational Interface (Claude Code Parity)

The DeepAgents CLI provides a **chat-like terminal interface** rather than discrete commands:

```bash
$ deepagents --agent guardkit-dev

You: I want to add a user authentication system

Agent: I'll help you plan that feature. Let me check your project 
       conventions and create a structured plan.
       
       ⚙ read_file(/memories/architecture.md)
       ⚙ read_file(.deepagents/agent.md)
       
       Based on your React/TypeScript stack and your preference
       for Supabase, I'll create a feature plan...
```

This preserves the **conversational flow** developers expect from Claude Code while operating independently of any specific LLM provider.

### 2. Skills System (Replaces Slash Commands)

GuardKit's slash commands map directly to DeepAgents skills:

| Claude Code | DeepAgents Skill | Trigger Pattern |
|-------------|------------------|-----------------|
| `/feature-plan` | `feature-plan/SKILL.md` | "plan a feature", "create feature for" |
| `/task-work` | `task-work/SKILL.md` | "work on task", "implement TASK-" |
| `/task-complete` | `task-complete/SKILL.md` | "complete task", "finish TASK-" |

**Skill Structure** (following Anthropic's specification):

```
~/.deepagents/guardkit-dev/skills/
├── feature-plan/
│   ├── SKILL.md           # Instructions for planning
│   └── templates/
│       └── feature.yaml   # YAML template
├── task-work/
│   ├── SKILL.md           # Instructions for implementation
│   └── quality-gates.md   # Validation criteria
└── task-complete/
    └── SKILL.md           # Completion workflow
```

**Example SKILL.md** for feature planning:

```yaml
---
name: feature-plan
description: Create structured feature plans with task decomposition, 
  dependency analysis, and complexity estimation. Use when the user 
  wants to plan, design, or structure a new feature.
---

# Feature Planning Workflow

When the user wants to plan a feature:

1. **Gather Requirements**
   - Ask clarifying questions about scope
   - Check /memories/ for relevant context
   - Read project conventions from .deepagents/agent.md

2. **Analyze Dependencies**
   - Review existing code structure
   - Identify impacted modules
   - Determine testing requirements

3. **Create Feature File**
   - Use template from templates/feature.yaml
   - Decompose into 3-7 tasks
   - Estimate complexity (S/M/L)
   - Identify parallel execution groups

4. **Output Location**
   - Save to: .guardkit/features/FEAT-{id}.yaml
   - Report summary to user
```

### 3. Persistent Memory (Knowledge Retention)

DeepAgents memory system maps to GuardKit's context requirements:

```
~/.deepagents/guardkit-dev/
├── agent.md              # Personality + base conventions
├── memories/
│   ├── project-stack.md        # React, TypeScript, Supabase
│   ├── coding-conventions.md   # Style preferences
│   ├── architecture.md         # System design decisions
│   └── past-decisions.md       # Why we chose X over Y
└── skills/
    └── ...
```

**Memory-First Protocol** aligns with GuardKit's context management:

1. **Before planning** → Check `/memories/` for architecture decisions
2. **Before implementing** → Load coding conventions
3. **After completing** → Save learnings for future tasks

### 4. Human-in-the-Loop (Quality Gates)

DeepAgents HITL maps to GuardKit's quality gate requirements:

```python
# How GuardKit Agent could configure approval gates
agent = create_deep_agent(
    model="devstral-2",
    interrupt_on={
        # Require approval before modifying files
        "write_file": {
            "allowed_decisions": ["approve", "edit", "reject"]
        },
        # Require approval before completing tasks
        "complete_task": {
            "allowed_decisions": ["approve", "reject"]
        },
        # Require approval before merging
        "merge_worktree": {
            "allowed_decisions": ["approve", "reject"]
        },
    }
)
```

**CLI Approval Flow**:

```
Agent: I want to write the ThemeContext component.

⚙ write_file(src/context/ThemeContext.tsx)

╭─ File Change ──────────────────────────────────────────────────╮
│ + import { createContext, useContext, useState } from 'react'; │
│ +                                                              │
│ + export const ThemeContext = createContext<ThemeContextType>  │
│ + ...                                                          │
╰────────────────────────────────────────────────────────────────╯

[a]pprove  [e]dit  [r]eject  [v]iew full
> 
```

---

## Architecture: GuardKit Agent on DeepAgents CLI

### Component Mapping

```
┌─────────────────────────────────────────────────────────────────┐
│                    GUARDKIT AGENT ARCHITECTURE                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 DeepAgents CLI Layer                     │   │
│  │  - Conversational interface                              │   │
│  │  - Rich terminal UI (diffs, progress)                    │   │
│  │  - Session management                                    │   │
│  │  - HITL approval workflows                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              GuardKit Skills Layer                       │   │
│  │  - feature-plan skill                                    │   │
│  │  - task-work skill (with Player/Coach loop)              │   │
│  │  - task-complete skill                                   │   │
│  │  - quality-gates skill                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           DeepAgents Core + Custom Middleware            │   │
│  │  - FilesystemMiddleware (replaces Blackboard)            │   │
│  │  - SubAgentMiddleware (Player + Coach agents)            │   │
│  │  - AdversarialLoopMiddleware (our custom addition)       │   │
│  │  - SummarizationMiddleware (context management)          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   LangGraph Core                         │   │
│  │  - State machine execution                               │   │
│  │  - Checkpoint/resume                                     │   │
│  │  - Multi-model support                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Custom CLI Extension for GuardKit

While DeepAgents CLI provides the foundation, we'll create a thin wrapper:

```bash
# Option A: Use deepagents directly with guardkit-dev agent
$ deepagents --agent guardkit-dev

# Option B: Create guardkit wrapper (recommended)
$ gka  # Alias for deepagents --agent guardkit-dev with defaults
$ gka --model devstral-2  # Override model
$ gka --auto-approve  # Skip approval prompts
```

**Implementation** (`guardkit-cli/cli.py`):

```python
#!/usr/bin/env python
"""GuardKit Agent CLI - Thin wrapper around DeepAgents CLI."""
import subprocess
import sys
import os

def main():
    # Set default agent to guardkit-dev
    agent = os.environ.get("GKA_AGENT", "guardkit-dev")
    
    # Build command
    cmd = ["deepagents", "--agent", agent] + sys.argv[1:]
    
    # Run with our environment
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
```

---

## Migration Path: Claude Code → DeepAgents CLI → GUI

### Phase 1: Current State (Claude Code)

**Developer Experience**:
- Open Claude Code terminal
- Use `/feature-plan`, `/task-work`, `/task-complete` commands
- Each command runs within Claude's context
- Manual task orchestration

**Limitations**:
- Requires Claude Max subscription ($200/mo)
- Single-threaded task execution
- No persistent memory across sessions
- Claude-only model lock-in

### Phase 2: DeepAgents CLI (2025 Target)

**Developer Experience**:
- Open terminal, run `gka` or `deepagents --agent guardkit-dev`
- Conversational interface triggers skills
- Persistent memory retains project knowledge
- Multi-model support for cost optimization

**Key Transitions**:

| From (Claude Code) | To (DeepAgents CLI) |
|--------------------|---------------------|
| `/feature-plan "X"` | "Plan a feature for X" |
| `/task-work TASK-001` | "Work on TASK-001" |
| `/task-complete` | "Complete this task" |
| Markdown files | Skills + Memories |
| Claude model | Any model (Devstral, Claude, GPT-4o) |

**User Experience Preservation**:
- ✅ Conversational flow maintained
- ✅ Interactive approval preserved
- ✅ File-based context (skills/memories)
- ✅ Terminal-native interface
- ✅ Similar mental model

### Phase 3: Purpose-Built GUI (2026 Target)

**Vision** (based on Auto-Claude reference):
- Kanban board for task/feature visualization
- Multiple agent terminals for parallel work
- Real-time progress tracking
- Chat interface for spec creation
- Visual dependency graphs

**GUI Components**:

```
┌─────────────────────────────────────────────────────────────────┐
│  GuardKit Agent - Feature Dashboard              [Settings] [?] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─ Feature Pipeline ──────────────────────────────────────────┐│
│  │                                                             ││
│  │  PLANNING      IN PROGRESS    REVIEW        DONE           ││
│  │  ┌───────┐     ┌───────┐      ┌───────┐    ┌───────┐       ││
│  │  │FEAT-03│     │FEAT-02│      │       │    │FEAT-01│       ││
│  │  │ 📝    │     │ ⚙️ 67%│      │       │    │ ✅    │       ││
│  │  │3 tasks│     │4 tasks│      │       │    │4 tasks│       ││
│  │  └───────┘     └───────┘      └───────┘    └───────┘       ││
│  │                                                             ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─ FEAT-002: User Authentication ─────────────────────────────┐│
│  │                                                             ││
│  │  Task Progress:                                             ││
│  │  ● TASK-001 Create auth context     ✅ Done    (3 turns)   ││
│  │  ● TASK-002 Login component         ✅ Done    (2 turns)   ││
│  │  ● TASK-003 Protected routes        🔄 Turn 2  (45 sec)    ││
│  │  ○ TASK-004 Integration tests       ⏸ Pending             ││
│  │                                                             ││
│  │  [View Details] [Pause] [Skip Task]                        ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─ Agent Terminal ────────────────────────────────────────────┐│
│  │ 🎮 Player: Implementing ProtectedRoute wrapper...           ││
│  │    Modified: src/components/ProtectedRoute.tsx              ││
│  │ 🏀 Coach: Validating implementation...                      ││
│  │    Tests: 8/8 passing                                       ││
│  │    Coverage: 92%                                            ││
│  │    FEEDBACK: Add loading state for auth check               ││
│  │ 🎮 Player: Adding loading state...                          ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─ Chat Interface ────────────────────────────────────────────┐│
│  │ You: Add social login support                               ││
│  │ Agent: I'll create a feature plan for social login.         ││
│  │        Which providers should I include?                    ││
│  │        □ Google  □ GitHub  □ Apple  □ Microsoft             ││
│  │ [Type your message...                                    📎]││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

**GUI Technology Recommendation**:
1. **Web-first** (FastAPI + React): Team sharing, remote access
2. **Tauri wrapper** for desktop: Native feel, smaller binary than Electron

---

## Implementation Strategy

### Immediate (Week 1-2)

1. **Create GuardKit agent configuration**
   ```bash
   mkdir -p ~/.deepagents/guardkit-dev/{memories,skills}
   ```

2. **Port existing slash commands to skills**
   - `feature-plan/SKILL.md`
   - `task-work/SKILL.md`
   - `task-complete/SKILL.md`

3. **Create agent.md with project conventions**
   ```markdown
   # GuardKit Development Agent
   
   ## Project Conventions
   - React with TypeScript
   - Vitest for testing
   - 90% coverage requirement
   ...
   ```

4. **Test interaction flow**
   ```bash
   $ deepagents --agent guardkit-dev
   You: Plan a feature for adding dark mode
   ```

### Short-term (Week 3-4)

1. **Implement AdversarialLoopMiddleware**
   - Player/Coach subagent coordination
   - FilesystemMiddleware for coordination state

2. **Create `gka` CLI wrapper**
   - Default model configuration
   - Project-specific settings

3. **Integrate with git worktrees**
   - Parallel task execution
   - Branch management

### Medium-term (Month 2-3)

1. **TUI Enhancement** (Textual/Rich)
   - Progress visualization
   - Multi-task dashboard

2. **Backlog.md integration**
   - Visual task management
   - Sync with skills

### Long-term (2026)

1. **Web GUI prototype**
   - FastAPI backend wrapping DeepAgents
   - React frontend with Kanban view

2. **Desktop app (Tauri)**
   - Offline support
   - Local model integration

---

## Risk Assessment

### Risks of DeepAgents CLI Approach

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| DeepAgents API instability | Medium | Medium | Pin version, wrap in adapter |
| Skills system limitations | Low | Medium | Custom middleware can extend |
| Learning curve for users | Low | Low | Similar UX to Claude Code |
| Performance with local models | Medium | Low | Test thoroughly, provide config |

### Risks of NOT Using DeepAgents CLI

| Risk | Likelihood | Impact | Notes |
|------|------------|--------|-------|
| Poor UX with raw Python | High | High | Users expect conversational flow |
| Reinventing CLI infrastructure | High | High | DeepAgents already solved this |
| No persistent memory | High | Medium | Would need to build from scratch |
| Harder GUI transition | Medium | Medium | DeepAgents provides clean abstractions |

---

## Recommendations

### 1. Adopt DeepAgents CLI as Primary Interface

**Confidence: High**

The DeepAgents CLI provides:
- Conversational interface familiar to Claude Code users
- Skills system that maps to our slash commands
- Persistent memory for project context
- HITL workflows for quality gates
- Multi-model support for cost optimization

### 2. Create GuardKit-Specific Agent Profile

**Confidence: High**

Create `guardkit-dev` agent with:
- Skills for feature-plan, task-work, task-complete
- Memory templates for project conventions
- Custom system prompt for GuardKit workflows

### 3. Build Thin `gka` CLI Wrapper

**Confidence: Medium**

Simple wrapper that:
- Sets default agent to `guardkit-dev`
- Configures project-specific defaults
- Provides familiar command for users

### 4. Preserve Transition Path to GUI

**Confidence: High**

Ensure architecture supports:
- Web API exposure of agent capabilities
- Event streaming for real-time UI updates
- State inspection for dashboard views

---

## Conclusion

The DeepAgents CLI is the right stepping stone from Claude Code to a purpose-built GUI. It preserves the conversational development experience that developers value while enabling model flexibility and cost optimization. The skills system provides a clean mapping from GuardKit's slash commands, and the persistent memory aligns with our context management requirements.

The key insight is that **developers don't want to learn new command syntax** – they want to have a conversation about their work. DeepAgents CLI provides this while running on any LLM, which is exactly what GuardKit Agent needs.

---

## References

- [DeepAgents CLI Documentation](https://docs.langchain.com/oss/python/deepagents/cli)
- [Introducing DeepAgents CLI](https://blog.langchain.com/introducing-deepagents-cli/)
- [Using Skills with Deep Agents](https://blog.langchain.com/using-skills-with-deep-agents/)
- [DeepAgents GitHub Repository](https://github.com/langchain-ai/deepagents)
- [Anthropic Agent Skills Specification](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- `GuardKit_Agent_User_Experience.md` (internal)
- `DeepAgents_Integration_Analysis.md` (internal)

---

*Document created: December 24, 2025*
