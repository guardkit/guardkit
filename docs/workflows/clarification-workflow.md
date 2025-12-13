# Clarification Workflow

## Overview

GuardKit uses a unified `clarification-questioner` subagent to collect user preferences before making assumptions during planning. This reduces rework from incorrect assumptions by approximately 15%.

## How It Works

All commands that need clarification invoke the same `clarification-questioner` agent with different context types. The agent adapts its questions based on the context and task complexity.

### Unified Agent Pattern

```
subagent_type: "clarification-questioner"
prompt: "Execute clarification...
  CONTEXT TYPE: {review_scope|implementation_prefs|implementation_planning}
  COMPLEXITY: {score}
  MODE: {skip|quick|full}
  ..."
```

## Three Clarification Contexts

### 1. Review Scope (Context A)

**Used by:** `/task-review`, `/feature-plan` (initial phase)

**Purpose:** Guide what to analyze

**Typical Questions:**
- What aspects should be prioritized?
- What depth of analysis is needed?
- Are there specific concerns to address?

**Example:**
```bash
/feature-plan "implement dark mode"

# Agent asks (if complexity ≥ 3):
# - Focus areas: UI, state management, persistence, or all?
# - Analysis depth: Quick overview vs comprehensive?
# - Special considerations: Accessibility, browser support?
```

### 2. Implementation Preferences (Context B)

**Used by:** `/feature-plan` at [I]mplement decision point

**Purpose:** Guide subtask creation approach and constraints

**Typical Questions:**
- Implementation approach preferences?
- Technology/library constraints?
- Parallel vs sequential execution?

**Example:**
```bash
# After /feature-plan review completes:
# User chooses [I]mplement

# Agent asks (if complexity ≥ 3):
# - Use existing theme library or custom implementation?
# - CSS variables, styled-components, or Tailwind?
# - Split UI and state tasks or keep together?
```

### 3. Implementation Planning (Context C)

**Used by:** `/task-work` at Phase 1.6

**Purpose:** Guide implementation scope and approach

**Typical Questions:**
- Implementation scope (minimal/standard/complete)?
- Testing approach (unit/integration/full)?
- Error handling strategy?

**Example:**
```bash
/task-work TASK-a3f8

Phase 1: Loading context...
Phase 1.6: Clarifying Questions (complexity: 5)

# Agent asks:
# - Scope: Minimal, standard, or complete?
# - Testing: Unit only, integration, or full coverage?
# - Deployment: Dev environment or production-ready?
```

## Complexity Gating

Questions are automatically gated by task complexity to avoid unnecessary overhead on simple tasks:

| Complexity | task-work | task-review | feature-plan |
|------------|-----------|-------------|--------------|
| 1-2 | Skip | Skip | Skip |
| 3-4 | Quick (15s timeout) | Skip | Quick |
| 5-6 | Full (blocking) | Quick | Full |
| 7+ | Full (blocking) | Full | Full |

### Modes Explained

- **Skip**: No questions asked, use defaults
- **Quick**: Time-limited questions (15s timeout), then proceed with defaults
- **Full**: Blocking questions, must be answered before proceeding

## Command-Line Control

All commands support these flags for automation and control:

### Skip Clarification

```bash
# Skip all questions (use defaults)
/task-work TASK-a3f8 --no-questions
/feature-plan "dark mode" --no-questions
/task-review TASK-b2c4 --no-questions
```

### Force Clarification

```bash
# Force questions even for simple tasks (complexity 1-2)
/task-work TASK-a3f8 --with-questions
```

### Use Defaults Silently

```bash
# Use defaults without prompting
/task-work TASK-a3f8 --defaults
```

### Inline Answers

```bash
# Provide answers inline for automation
/task-work TASK-a3f8 --answers="scope:standard testing:integration"
/feature-plan "dark mode" --answers="focus:ui depth:standard"
```

### Re-run Clarification

```bash
# Re-ask questions even if previous answers exist
/task-work TASK-a3f8 --reclarify
```

## Persistence

All clarification decisions are saved to task frontmatter for audit trail and reproducibility:

```yaml
clarification:
  context: implementation_planning
  timestamp: 2025-12-08T14:30:00Z
  mode: full
  decisions:
    - question_id: scope
      question: "Implementation scope?"
      answer: standard
      default_used: false
    - question_id: testing
      question: "Testing strategy?"
      answer: integration
      default_used: true
```

### Benefits of Persistence

1. **Task Resumption**: Re-run commands without re-answering questions
2. **Audit Trail**: See what decisions were made and when
3. **Reproducibility**: Understand why AI made certain choices
4. **Team Communication**: Share decision context with team

## Clarification Agent

The `clarification-questioner` agent is the single source of truth for all clarification needs.

### Location

- **Global installation**: `~/.agentecflow/agents/clarification-questioner.md`
- **Installed by**: GuardKit installer (`./installer/scripts/install.sh`)

### Implementation

The agent uses Python modules from `lib/clarification/*`:
- `question_bank.py`: Question definitions per context
- `complexity_gate.py`: Complexity-based gating logic
- `persistence.py`: Save/load decisions to task frontmatter
- `formatter.py`: Format questions for display

### Integration Points

The agent is invoked via the Task tool at these points:

1. **task-work**: Phase 1.6 (after context loading, before planning)
2. **feature-plan**: Phase 1 (before review) and at [I]mplement decision
3. **task-review**: Phase 1 (before analysis)

## Workflow Examples

### Example 1: Simple Task (No Questions)

```bash
/task-create "Fix typo in README"
# Created: TASK-a3f8 (complexity: 1)

/task-work TASK-a3f8
# Complexity 1 → Skip clarification
# Proceeds directly to Phase 2
```

### Example 2: Medium Task (Quick Questions)

```bash
/task-create "Add validation to login form"
# Created: TASK-b2c4 (complexity: 4)

/task-work TASK-b2c4
# Complexity 4 → Quick mode (15s timeout)
# Shows 2-3 key questions
# If no response in 15s, uses defaults
```

### Example 3: Complex Task (Full Questions)

```bash
/task-create "Refactor authentication system"
# Created: TASK-c5d7 (complexity: 8)

/task-work TASK-c5d7
# Complexity 8 → Full mode (blocking)
# Shows comprehensive questions
# Must answer before proceeding
# Saves all decisions to frontmatter
```

### Example 4: Feature Planning

```bash
/feature-plan "implement dark mode"
# Creates review task (complexity: 5)

# Phase 1: Review Scope Clarification (full mode)
# - Focus areas?
# - Analysis depth?
# - Special considerations?

# ... review executes ...

# Decision checkpoint: [I]mplement chosen

# Phase 2: Implementation Preferences Clarification (full mode)
# - Theme library preference?
# - CSS approach?
# - Task organization?

# ... creates subtasks based on answers ...
```

## Troubleshooting

### Questions Not Appearing

**Symptoms:**
- Expected questions but none shown
- Command proceeds directly to next phase

**Possible Causes:**
1. Task complexity too low (< 3 for most commands)
2. Using `--no-questions` flag
3. Previous clarification exists in frontmatter

**Solutions:**
```bash
# Force questions regardless of complexity
/task-work TASK-a3f8 --with-questions

# Re-run clarification even if previous answers exist
/task-work TASK-a3f8 --reclarify

# Check task complexity
cat tasks/backlog/TASK-a3f8.md | grep "complexity:"
```

### Questions Timing Out (Quick Mode)

**Symptoms:**
- Questions appear then disappear
- Defaults used without explicit choice

**Explanation:**
- Quick mode has 15s timeout
- Designed for automation and optional input

**Solutions:**
```bash
# Force full mode (no timeout)
/task-work TASK-a3f8 --with-questions

# Or provide answers inline
/task-work TASK-a3f8 --answers="scope:standard testing:integration"
```

### Want to See Previous Decisions

**View frontmatter:**
```bash
cat tasks/in_progress/TASK-a3f8.md | grep -A 20 "clarification:"
```

**Or use task-status:**
```bash
/task-status TASK-a3f8
# Shows clarification section if present
```

## Design Rationale

### Why Unified Agent?

**Before**: Each command had its own clarification logic scattered across Python orchestrators.

**After**: Single `clarification-questioner` agent invoked with context parameter.

**Benefits:**
1. **Consistency**: Same question style across all commands
2. **Maintainability**: Update questions in one place
3. **Extensibility**: Add new contexts without duplicating code
4. **Testability**: Test one agent instead of N orchestrators

### Why Three Contexts?

Different commands need different information at different times:

1. **review_scope**: "What should I look for?" (before analysis)
2. **implementation_prefs**: "How should I structure this?" (before task creation)
3. **implementation_planning**: "How should I build this?" (before implementation)

### Why Complexity Gating?

Avoids unnecessary overhead on simple tasks while ensuring guidance on complex ones:

- **Simple tasks (1-2)**: Clear requirements, skip questions
- **Medium tasks (3-4)**: Quick questions with timeout (optional)
- **Complex tasks (5+)**: Full questions (required for quality)

## See Also

- [Complexity Management Workflow](complexity-management-workflow.md)
- [Task Review Workflow](task-review-workflow.md)
- [Design-First Workflow](design-first-workflow.md)
- Main CLAUDE.md → Clarifying Questions section
