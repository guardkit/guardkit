---
paths: "**/agents/**/*.md", ".claude/agents/**/*.md", installer/core/agents/**/*.md
---

# Agent Development Patterns

Patterns for creating and maintaining GuardKit agent files.

## Agent Frontmatter

Every agent file requires this frontmatter:

```yaml
---
name: task-manager
description: Manages tasks through kanban workflow with test verification
tools: Read, Write, Edit, Bash, Grep
model: sonnet
model_rationale: "Task orchestration requires reasoning for phase transitions"

# Discovery metadata (REQUIRED for agent discovery)
stack: [cross-stack]
phase: orchestration
capabilities:
  - Workflow orchestration (TDD, BDD, standard)
  - Phase transition management
  - Quality gate coordination
keywords: [task-management, orchestration, workflow, phases]
---
```

### Required Fields

- `name`: Agent identifier (kebab-case)
- `description`: One-line description
- `tools`: Comma-separated tool list
- `model`: sonnet or haiku
- `stack`: Array of technology stacks
- `phase`: implementation | review | testing | orchestration | debugging
- `capabilities`: Array of specific skills
- `keywords`: Array of searchable terms

### Stack Options

```yaml
# Cross-stack agents
stack: [cross-stack]

# Stack-specific agents
stack: [python, fastapi]
stack: [react, typescript]
stack: [dotnet, maui]
```

### Phase Options

```yaml
phase: implementation    # Phase 3 - code generation
phase: review            # Phase 2.5B, 5 - architecture/code review
phase: testing           # Phase 4 - test execution
phase: orchestration     # Workflow coordination
phase: debugging         # Problem diagnosis
```

## Boundary Sections

Every agent MUST have ALWAYS/NEVER/ASK boundaries:

```markdown
## Boundaries

### ALWAYS
- Run build verification before tests (block if compilation fails)
- Execute in technology-specific test runner
- Report failures with actionable error messages
- Enforce 100% test pass rate
- Validate test coverage thresholds

### NEVER
- Never approve code with failing tests
- Never skip compilation check
- Never modify tests to make tests pass
- Never ignore coverage below threshold
- Never run tests without dependency installation

### ASK
- Coverage 70-79%: Ask if acceptable given task complexity
- Performance tests failing: Ask if acceptable for non-production
- Flaky tests detected: Ask if should quarantine or fix
```

### Boundary Format

Each item uses: `[emoji] [action] ([brief rationale])`

- ALWAYS prefix
- NEVER prefix
- ASK prefix

## Quick Start Section

Provide 5-10 concrete examples:

```markdown
## Quick Start Commands

### Create a New Task
```bash
/task-create "Add user authentication" --priority high
```

**Expected Output:**
```yaml
id: TASK-042
title: Add user authentication
status: backlog
```
```

## Progressive Disclosure Split

### Core File ({agent}.md): 6-10KB
- Frontmatter with discovery metadata
- Quick Start examples (5-10)
- Boundaries (ALWAYS/NEVER/ASK)
- Capabilities summary
- Phase integration
- Loading instructions for extended

### Extended File ({agent}-ext.md): 15-25KB
- Detailed code examples (30+)
- Best practices with explanations
- Anti-patterns with code samples
- Technology-specific guidance
- Troubleshooting scenarios

## Size Guidelines

| Component | Core | Extended |
|-----------|------|----------|
| Examples | 5-10 | 30+ |
| Boundaries | Full | N/A |
| Best Practices | Summary | Detailed |
| Anti-patterns | List | With code |
| Total Size | 6-10KB | 15-25KB |

## Discovery Metadata

For agent discovery to work, agents MUST have:

1. `stack`: Technology stack(s) supported
2. `phase`: Workflow phase
3. `capabilities`: Specific skills
4. `keywords`: Searchable terms

Agents without metadata are skipped during discovery.

## Agent Precedence

When multiple agents match:

1. **Local** (`.claude/agents/`) - Highest priority
2. **User** (`~/.agentecflow/agents/`)
3. **Global** (`installer/core/agents/`)
4. **Template** (`installer/core/templates/*/agents/`) - Lowest

## Model Selection

```yaml
# Use Sonnet for:
model: sonnet
# - Architectural decisions
# - Complex reasoning
# - Review and analysis
# - Orchestration

# Use Haiku for:
model: haiku
# - Code generation
# - Test execution
# - Fast iteration
# - Pattern application
```

Include `model_rationale` explaining the choice.
