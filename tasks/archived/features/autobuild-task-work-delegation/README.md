# Feature: AutoBuild task-work Delegation

## Problem Statement

The current AutoBuild Player-Coach workflow uses a generic SDK prompt for the Player phase, bypassing GuardKit's established subagent infrastructure. This means:

- Stack-specific specialists (python-api-specialist, react-specialist, etc.) are NOT used
- TDD mode is prompt-based (honor system) rather than structurally enforced
- Quality gates (Phase 4.5 fix loop, code-reviewer) are not included
- Two parallel systems to maintain instead of one

## Solution

Route the AutoBuild Player phase through `task-work --implement-only --mode=tdd` to leverage:

1. **Stack-specific subagents** - Agent discovery selects optimal specialist
2. **TDD enforcement** - Structural RED→GREEN→REFACTOR workflow
3. **Quality gates** - Phase 4, 4.5, and 5 included automatically
4. **Single system** - All task-work improvements benefit AutoBuild

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PROPOSED AUTOBUILD FLOW                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PreLoopQualityGates (unchanged)                                            │
│       │                                                                     │
│       ▼                                                                     │
│  task-work --design-only                                                    │
│       │                                                                     │
│       ▼ (returns plan, complexity)                                          │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════    │
│  ADVERSARIAL LOOP                                                           │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  PLAYER TURN:                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ task-work --implement-only --mode=tdd                               │    │
│  │     │                                                               │    │
│  │     ├── Phase 3: Implementation (stack-specific agent)             │    │
│  │     ├── Phase 4: Testing (test-orchestrator)                       │    │
│  │     ├── Phase 4.5: Fix Loop (auto-fix)                             │    │
│  │     └── Phase 5: Code Review (code-reviewer)                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                     │
│       ▼                                                                     │
│  COACH TURN (unchanged - validates independently)                           │
│       │                                                                     │
│       ▼                                                                     │
│  (repeat until approved or max_turns)                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Subtasks

### Core Delegation (Waves 1-3)

| Task ID | Title | Method | Wave |
|---------|-------|--------|------|
| TASK-TWD-001 | Modify AgentInvoker.invoke_player() for task-work delegation | task-work | 1 |
| TASK-TWD-002 | Implement task state bridging for design_approved state | task-work | 1 |
| TASK-TWD-003 | Implement Coach feedback integration | task-work | 2 |
| TASK-TWD-004 | Add development mode parameter to AutoBuild CLI | task-work | 2 |
| TASK-TWD-005 | Create integration tests for delegation flow | task-work | 3 |
| TASK-TWD-006 | Update documentation (CLAUDE.md, agent docs) | direct | 3 |

### Quality Enhancements (Waves 4-5)

| Task ID | Title | Method | Wave | Priority |
|---------|-------|--------|------|----------|
| TASK-TWD-007 | Implement Escape Hatch Pattern for blocked task reports | task-work | 4 | HIGH |
| TASK-TWD-008 | Implement Coach honesty verification for Player claims | task-work | 4 | MEDIUM |
| TASK-TWD-009 | Implement Promise-Based Completion Verification | task-work | 5 | HIGH |

## Benefits

- **100% code reuse** - Leverages existing task-work infrastructure
- **Stack-specific quality** - Python gets python-api-specialist, React gets react-specialist
- **TDD actually enforced** - Not just a prompt suggestion
- **Quality gates included** - Phase 4.5 auto-fix, code-reviewer
- **Single system** - Future task-work improvements benefit AutoBuild

## Source

Created from review: [TASK-REV-RW01](./../TASK-REV-RW01-ralph-wiggum-analysis.md)
Review report: [.claude/reviews/TASK-REV-RW01-review-report.md](../../../.claude/reviews/TASK-REV-RW01-review-report.md)

## Estimated Effort

### Core Delegation (Waves 1-3)
- **Effort**: 8-12 hours
- **Risk**: Low-Medium (using proven infrastructure)
- **ROI**: Very High

### Quality Enhancements (Waves 4-5)
- **Effort**: 5-8 hours additional
- **Risk**: Very Low
- **ROI**: High (complements core delegation)
