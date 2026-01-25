---
id: TASK-TWD-006
title: Update documentation for task-work delegation
status: completed
task_type: implementation
created: 2025-12-31T14:00:00Z
updated: 2026-01-02T11:00:00Z
completed: 2026-01-02T11:00:00Z
priority: low
tags: [autobuild, documentation, claude-md, agents]
complexity: 3
parent_feature: autobuild-task-work-delegation
wave: 3
implementation_mode: direct
conductor_workspace: autobuild-twd-wave3-2
source_review: TASK-REV-RW01
depends_on: [TASK-TWD-001, TASK-TWD-002, TASK-TWD-003, TASK-TWD-004]
previous_state: in_review
state_transition_reason: "Verified complete - all documentation updated for task-work delegation architecture"
---

# Task: Update documentation for task-work delegation

## Description

Update all relevant documentation to reflect the new task-work delegation architecture in AutoBuild. This ensures users and developers understand how AutoBuild now leverages the full subagent infrastructure.

## Documentation Updates Required

### 1. CLAUDE.md - AutoBuild Section

Update the AutoBuild section to explain the delegation pattern:

```markdown
## AutoBuild - Autonomous Task Implementation

AutoBuild provides fully autonomous task implementation using a Player-Coach
adversarial workflow. **The Player now delegates to task-work** to leverage
the full subagent infrastructure.

### Architecture

```
AutoBuild Orchestrator
         │
         ├── PreLoop: task-work --design-only
         │              ├── Clarification (Phase 1.6)
         │              ├── Planning (Phase 2)
         │              ├── Architectural Review (Phase 2.5)
         │              └── Human Checkpoint (Phase 2.8)
         │
         └── Loop: Player↔Coach
                    │
                    └── Player: task-work --implement-only --mode=tdd
                                  ├── Stack-specific specialist
                                  ├── test-orchestrator
                                  ├── code-reviewer
                                  └── Phase 4.5 fix loop
```

### Development Mode

Specify the development mode with `--mode`:

```bash
guardkit autobuild task TASK-XXX --mode=tdd      # Test-Driven Development
guardkit autobuild task TASK-XXX --mode=standard # Implementation first
guardkit autobuild task TASK-XXX --mode=bdd      # Behavior-Driven (requires RequireKit)
```

Or set default in task frontmatter:

```yaml
---
id: TASK-XXX
autobuild:
  enabled: true
  mode: tdd
---
```
```

### 2. Agent Documentation Updates

#### .claude/agents/autobuild-player.md

Update to clarify the Player now delegates:

```markdown
## Architecture Change

**Important**: The Player agent no longer directly implements code. Instead,
it delegates to `task-work --implement-only` which invokes stack-specific
specialists.

### What the Player Does Now

1. Receives requirements and (optionally) Coach feedback
2. Delegates to task-work with appropriate mode
3. Monitors task-work execution
4. Reports results back to Coach

### Subagent Benefits

By delegating to task-work, the Player gains:
- Stack-specific implementation specialists
- test-orchestrator for comprehensive testing
- code-reviewer for quality checks
- Phase 4.5 auto-fix loop (3 attempts)

This ensures consistent quality whether using AutoBuild or manual task-work.
```

#### .claude/agents/autobuild-coach.md

Update Coach documentation to reflect the new flow:

```markdown
## Validation Scope

The Coach validates the output of task-work, which includes:
- Implementation by stack-specific specialist
- Tests written by test-orchestrator
- Code reviewed by code-reviewer

### Coach Responsibilities

1. **Independent Verification**: Run tests independently
2. **Requirement Validation**: Check all requirements addressed
3. **Quality Assessment**: Evaluate code quality
4. **Feedback Generation**: Provide actionable must-fix/should-fix items

The Coach feedback is written to a file that task-work reads on the next turn.
```

### 3. Workflow Documentation

#### docs/guides/guardkit-workflow.md

Add section on AutoBuild delegation:

```markdown
## AutoBuild with Task-Work Delegation

AutoBuild leverages the same subagent infrastructure as manual task-work:

### Manual Workflow
```bash
/task-create "Feature"
/task-work TASK-XXX --mode=tdd  # Uses subagents
/task-complete TASK-XXX
```

### AutoBuild Workflow
```bash
/task-create "Feature" autobuild:enabled=true
guardkit autobuild task TASK-XXX --mode=tdd  # Also uses subagents!
# Review worktree
/task-complete TASK-XXX
```

Both workflows use the same specialists:
- python-api-specialist (for Python APIs)
- react-specialist (for React apps)
- test-orchestrator (for all stacks)
- code-reviewer (for all stacks)
```

### 4. CLI Help Text

Update `guardkit autobuild task --help`:

```
Usage: guardkit autobuild task [OPTIONS] TASK_ID

  Execute AutoBuild orchestration for a task.

  AutoBuild creates an isolated worktree, runs the Player/Coach adversarial
  loop using task-work delegation, and preserves the worktree for human review.

  The Player delegates to task-work --implement-only, leveraging the full
  subagent infrastructure including stack-specific specialists, test-orchestrator,
  and code-reviewer.

Options:
  --max-turns INTEGER     Maximum adversarial turns (default: 5)
  --model TEXT            Claude model to use
  --mode [tdd|standard|bdd]
                          Development mode for task-work (default: tdd)
  --verbose               Show detailed turn-by-turn output
  --resume                Resume from last saved state
  --help                  Show this message and exit.
```

### 5. Architecture Diagram

Create or update architecture diagram:

```
┌─────────────────────────────────────────────────────────────────┐
│                     AutoBuild Orchestrator                       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    PreLoop Phase                          │   │
│  │                                                           │   │
│  │  task-work --design-only                                  │   │
│  │    └── Phase 1.6: Clarification                          │   │
│  │    └── Phase 2: Planning                                  │   │
│  │    └── Phase 2.5: Architectural Review                    │   │
│  │    └── Phase 2.7: Complexity Evaluation                   │   │
│  │    └── Phase 2.8: Human Checkpoint                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Adversarial Loop                        │   │
│  │                                                           │   │
│  │  ┌─────────────┐         ┌─────────────┐                 │   │
│  │  │   PLAYER    │         │    COACH    │                 │   │
│  │  │             │ report  │             │                 │   │
│  │  │ task-work   │────────▶│  Validates  │                 │   │
│  │  │ --implement │         │  Tests      │                 │   │
│  │  │ --mode=tdd  │◀────────│  Approves/  │                 │   │
│  │  │             │ feedback│  Feedback   │                 │   │
│  │  └─────────────┘         └─────────────┘                 │   │
│  │         │                                                 │   │
│  │         ▼                                                 │   │
│  │  ┌─────────────────────────────────────────────────┐     │   │
│  │  │              Subagent Infrastructure             │     │   │
│  │  │  ┌──────────────┐  ┌──────────────┐            │     │   │
│  │  │  │ Stack-Specific│  │test-orchestr│            │     │   │
│  │  │  │  Specialist   │  │    ator     │            │     │   │
│  │  │  └──────────────┘  └──────────────┘            │     │   │
│  │  │  ┌──────────────┐  ┌──────────────┐            │     │   │
│  │  │  │ code-reviewer │  │ Phase 4.5   │            │     │   │
│  │  │  │              │  │ Fix Loop    │            │     │   │
│  │  │  └──────────────┘  └──────────────┘            │     │   │
│  │  └─────────────────────────────────────────────────┘     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Acceptance Criteria

1. CLAUDE.md AutoBuild section updated with delegation architecture
2. autobuild-player.md updated to reflect delegation pattern
3. autobuild-coach.md updated with new validation scope
4. Workflow guide updated with comparison
5. CLI help text updated with --mode documentation
6. Architecture diagram added/updated

## Files to Modify

- `CLAUDE.md` - AutoBuild section
- `.claude/agents/autobuild-player.md` - Player agent docs
- `.claude/agents/autobuild-coach.md` - Coach agent docs
- `docs/guides/guardkit-workflow.md` - Workflow comparison
- `guardkit/cli/autobuild.py` - CLI help text

## Notes

- Keep documentation concise - link to detailed docs where appropriate
- Include "Before vs After" comparison where helpful
- Update any diagrams that show the old architecture
- Consider adding a "Migration Notes" section if behavior changes
