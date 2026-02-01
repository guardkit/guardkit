# Interactive Knowledge Capture Guide

Capture project knowledge through guided Q&A sessions to build persistent understanding across Claude sessions.

## Overview

Project knowledge often exists in developers' heads but isn't captured anywhere:

- **Implicit decisions** - "We chose FastMCP because..."
- **Domain knowledge** - "A 'focus area' means..."
- **Constraints** - "We can't use X because of Y"
- **Goals** - "The ultimate objective is..."

Interactive Knowledge Capture provides a natural way to extract and persist this knowledge in Graphiti, making it available to Claude across all future sessions.

**Key Benefits:**

| Benefit | Description |
|---------|-------------|
| **Persistent Memory** | Knowledge persists across Claude sessions |
| **AutoBuild Optimization** | Role constraints and quality gates guide autonomous workflows |
| **Reduced Ambiguity** | Fewer clarifying questions during task execution |
| **Team Knowledge** | Share project understanding across team members |
| **Context-Aware Planning** | `/feature-plan` queries Graphiti for related features and constraints |

---

## Quick Start

```bash
# Start interactive knowledge capture session
guardkit graphiti capture --interactive

# Focus on specific knowledge category
guardkit graphiti capture --interactive --focus project-overview
guardkit graphiti capture --interactive --focus architecture
guardkit graphiti capture --interactive --focus role-customization

# Limit number of questions
guardkit graphiti capture --interactive --max-questions 5
```

---

## Focus Categories

Interactive capture supports 9 focus categories organized into two groups:

### Project Knowledge Categories

These categories capture fundamental project understanding:

| Category | Description | Example Topics |
|----------|-------------|----------------|
| `project-overview` | Project purpose, target users, goals, problem statement | "What problem does this project solve?" |
| `architecture` | High-level architecture, components, services, data flow | "What are the main components or services?" |
| `domain` | Domain-specific terminology, business rules | "What domain-specific terms should I understand?" |
| `constraints` | Technical/business constraints, technologies to avoid | "What technologies should be avoided?" |
| `decisions` | Technology choices, rationale, trade-offs | "Why were these technologies chosen?" |
| `goals` | Key objectives and success criteria | "What are the key goals this project aims to achieve?" |

### AutoBuild Customization Categories

These categories customize autonomous workflow behavior:

| Category | Description | Example Topics |
|----------|-------------|----------------|
| `role-customization` | What AI Player should ask about before implementing, what AI Coach should escalate to humans | "What tasks require human approval?" |
| `quality-gates` | Customize coverage thresholds, architectural review scores | "What test coverage is acceptable?" |
| `workflow-preferences` | Implementation mode preferences, autonomous turn limits | "Should complex tasks use task-work or direct?" |

---

## Session Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Interactive Knowledge Capture                        │
│                                                                         │
│  1. Analyze existing knowledge (what we already know)                  │
│         ↓                                                               │
│  2. Identify gaps (what's missing or unclear)                          │
│         ↓                                                               │
│  3. Ask targeted questions                                              │
│         ↓                                                               │
│  4. Parse and structure answers                                         │
│         ↓                                                               │
│  5. Seed episodes to Graphiti                                          │
│         ↓                                                               │
│  6. Summarize what was learned                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Session Flow Details:**

1. **Analyze Existing Knowledge**: Queries Graphiti to understand what's already captured about your project
2. **Identify Gaps**: Compares existing knowledge against question templates to find missing information
3. **Ask Targeted Questions**: Presents high-priority gaps as natural questions
4. **Parse Answers**: Extracts structured facts from your responses
5. **Seed to Graphiti**: Stores captured knowledge in appropriate knowledge groups
6. **Summarize**: Shows what was captured and stored

**Session Commands:**
- Type your answer to capture knowledge
- `skip` or `s` to skip a question
- `quit` or `q` to end session early

---

## AutoBuild Customization Examples

### Role Customization

Define boundaries for autonomous AI behavior:

```bash
$ guardkit graphiti capture --interactive --focus role-customization

[1/3] ROLE_CUSTOMIZATION
Context: Prevents autonomous changes to sensitive areas

What tasks should the AI Player ALWAYS ask about before implementing?
Your answer: Database schema changes, auth/security changes, deployment configs

✓ Captured:
  - Player ask_before: Database schema changes...
  - Player ask_before: auth/security changes...
  - Player ask_before: deployment configs...

[2/3] ROLE_CUSTOMIZATION
Context: Defines human oversight boundaries

What decisions should the AI Coach escalate to humans rather than auto-approve?
Your answer: Architecture changes, breaking API changes, anything touching payments

✓ Captured:
  - Coach escalate_when: Architecture changes...
  - Coach escalate_when: breaking API changes...
  - Coach escalate_when: anything touching payments...

[3/3] ROLE_CUSTOMIZATION
Context: Defines hard boundaries for autonomous work

Are there any areas where the AI should NEVER make changes autonomously?
Your answer: Production database, secrets files, CI/CD pipelines

✓ Captured:
  - No auto zone: Production database...
  - No auto zone: secrets files...
  - No auto zone: CI/CD pipelines...
```

### Quality Gate Customization

Set project-specific quality thresholds:

```bash
$ guardkit graphiti capture --interactive --focus quality-gates

[1/2] QUALITY_GATES
Context: Customizes quality gate thresholds

What test coverage threshold is acceptable for this project?
Your answer: 85% for core business logic, 70% for utilities, 60% for scaffolding

✓ Captured:
  - Quality gate: coverage 85% for core business logic
  - Quality gate: coverage 70% for utilities
  - Quality gate: coverage 60% for scaffolding

[2/2] QUALITY_GATES
Context: Prevents threshold drift during sessions

What architectural review score should block implementation?
Your answer: Below 60 should block, 60-75 should warn

✓ Captured:
  - Quality gate: arch review block below 60
  - Quality gate: arch review warn 60-75
```

### Workflow Preferences

Configure implementation mode preferences:

```bash
$ guardkit graphiti capture --interactive --focus workflow-preferences

[1/2] WORKFLOW_PREFERENCES
Context: Clarifies implementation mode preferences

Should complex tasks use task-work mode or direct implementation?
Your answer: Use task-work for anything touching auth or payments, direct for UI changes

✓ Captured:
  - Workflow: task-work for auth and payment changes
  - Workflow: direct implementation for UI changes

[2/2] WORKFLOW_PREFERENCES
Context: Prevents infinite loops in AutoBuild

How many autonomous turns should feature-build attempt before asking for help?
Your answer: 3-5 turns for most tasks, 1-2 for complex changes

✓ Captured:
  - Workflow: max 3-5 auto turns for standard tasks
  - Workflow: max 1-2 auto turns for complex changes
```

---

## CLI Reference

### `guardkit graphiti capture`

Capture project knowledge through interactive Q&A.

**Usage:**
```bash
guardkit graphiti capture --interactive [OPTIONS]
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--interactive`, `-i` | Run interactive Q&A session | Required |
| `--focus CATEGORY` | Focus on specific knowledge category | All categories |
| `--max-questions N` | Maximum questions to ask | 10 |

**Focus Categories:**
- `project-overview` - Project purpose and goals
- `architecture` - System architecture
- `domain` - Domain-specific terminology
- `constraints` - Technical/business constraints
- `decisions` - Technology decisions
- `goals` - Key objectives
- `role-customization` - AutoBuild role boundaries
- `quality-gates` - Quality thresholds
- `workflow-preferences` - Implementation preferences

**Examples:**

```bash
# Full capture session (all categories)
guardkit graphiti capture --interactive

# Focus on architecture only
guardkit graphiti capture --interactive --focus architecture

# Quick session with 5 questions
guardkit graphiti capture --interactive --max-questions 5

# AutoBuild customization
guardkit graphiti capture --interactive --focus role-customization
guardkit graphiti capture --interactive --focus quality-gates
guardkit graphiti capture --interactive --focus workflow-preferences
```

---

## Full Session Example

```
$ guardkit graphiti capture --interactive

╔══════════════════════════════════════════════════════════════════╗
║              Interactive Knowledge Capture Session                ║
╠══════════════════════════════════════════════════════════════════╣
║  I've identified 8 knowledge gaps for your project.              ║
║  4 are high priority.                                            ║
║                                                                  ║
║  Commands:                                                       ║
║    - Type your answer to capture knowledge                       ║
║    - 'skip' or 's' to skip a question                           ║
║    - 'quit' or 'q' to end session early                         ║
╚══════════════════════════════════════════════════════════════════╝

[1/8] PROJECT_OVERVIEW
Context: Helps Claude understand the 'why' behind implementation decisions

What is the primary purpose of this project?
Your answer: youtube-mcp is an MCP server that extracts insights from YouTube videos
and podcasts, making content consumable during activities like driving or walking
when full attention isn't available.

✓ Captured:
  - Project: youtube-mcp is an MCP server that extracts insights from YouTube v...
  - Project: making content consumable during activities like driving or walking...

[2/8] PROJECT_OVERVIEW
Context: Guides prioritization and feature decisions

What are the key goals this project aims to achieve?
Your answer: Extract actionable entrepreneurial strategies and investment trends.
Support focus area presets. Integrate with Claude Desktop for natural conversation.

✓ Captured:
  - Project: Extract actionable entrepreneurial strategies and investment trends...
  - Project: Support focus area presets...
  - Project: Integrate with Claude Desktop for natural conversation...

[3/8] ARCHITECTURE
Context: Essential for understanding how components fit together

What is the high-level architecture of this project?
Your answer: Three-phase architecture where Claude orchestrates between YouTube MCP,
Podcast MCP, and Google Sheets MCP. Each MCP is a separate server.

✓ Captured:
  - Architecture: Three-phase architecture where Claude orchestrates between You...
  - Architecture: Each MCP is a separate server...

...

Session Summary:
----------------------------------------
  project_overview: 5 facts captured
  architecture: 3 facts captured
  constraints: 2 facts captured
----------------------------------------
  Total: 10 facts added to Graphiti
```

---

## Knowledge Storage

Captured knowledge is stored in Graphiti knowledge groups:

| Category | Graphiti Group ID |
|----------|-------------------|
| `project-overview` | `project_overview` |
| `architecture` | `project_architecture` |
| `domain` | `domain_knowledge` |
| `constraints` | `project_constraints` |
| `decisions` | `project_decisions` |
| `goals` | `project_overview` |
| `role-customization` | `role_constraints` |
| `quality-gates` | `quality_gate_configs` |
| `workflow-preferences` | `implementation_modes` |

You can query captured knowledge using:

```bash
# Search captured knowledge
guardkit graphiti search "architecture"

# View specific knowledge group
guardkit graphiti list features
```

---

## Integration with Other Commands

### /feature-plan

The `/feature-plan` command automatically queries Graphiti for:
- Related features from previous planning sessions
- Role constraints (Player/Coach boundaries)
- Quality gate configurations
- Implementation mode preferences

### /feature-build

AutoBuild workflows use captured knowledge to:
- Determine when to ask for human approval (role constraints)
- Apply correct quality thresholds (quality gates)
- Choose implementation modes (workflow preferences)
- Track turn state across sessions

---

## Best Practices

1. **Start with project overview** - Capture fundamental project understanding first
   ```bash
   guardkit graphiti capture --interactive --focus project-overview
   ```

2. **Capture architecture early** - Architecture knowledge helps Claude scope tasks
   ```bash
   guardkit graphiti capture --interactive --focus architecture
   ```

3. **Set AutoBuild constraints** - Define boundaries before running autonomous workflows
   ```bash
   guardkit graphiti capture --interactive --focus role-customization
   ```

4. **Update periodically** - Re-run capture when project evolves
   ```bash
   guardkit graphiti capture --interactive --max-questions 5
   ```

5. **Use focused sessions** - Target specific areas rather than capturing everything at once
   ```bash
   guardkit graphiti capture --interactive --focus constraints
   ```

---

## Troubleshooting

### No gaps identified

If capture reports "No knowledge gaps identified":
- Your project knowledge is comprehensive, or
- Run `guardkit graphiti status` to verify Graphiti connection

### Session not starting

Ensure Graphiti is enabled and connected:
```bash
guardkit graphiti status
```

### Knowledge not persisting

Verify episodes were created:
```bash
guardkit graphiti search "your project name"
```

### Wrong category detected

Use `--focus` to target specific categories:
```bash
guardkit graphiti capture --interactive --focus architecture
```

---

## See Also

- [Graphiti Commands Guide](graphiti-commands.md) - Complete CLI reference
- [Graphiti Integration Guide](graphiti-integration-guide.md) - Overall integration architecture
- [AutoBuild Workflow Guide](autobuild-workflow.md) - Player-Coach workflow details
- [FEAT-GR-004: Interactive Knowledge Capture](../research/graphiti-refinement/FEAT-GR-004-interactive-knowledge-capture.md) - Technical specification
