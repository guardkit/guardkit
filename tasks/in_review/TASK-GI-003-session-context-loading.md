---
complexity: 7
conductor_workspace: wave3-1
created_at: 2026-01-24 00:00:00+00:00
dependencies:
- TASK-GI-001
- TASK-GI-002
estimated_minutes: 300
feature_id: FEAT-GI
id: TASK-GI-003
implementation_mode: task-work
parent_review: TASK-REV-GI01
priority: 1
status: in_review
tags:
- graphiti
- context-loading
- session-management
- critical-path
task_type: feature
title: Session Context Loading
wave: 3
updated_at: 2026-01-28T23:15:00+00:00
implementation_completed: true
test_coverage:
  context_loader: 93%
  context_formatter: 79%
  tests_passed: 36
  tests_failed: 0
code_review_score: 8.5/10
---

# TASK-GI-003: Session Context Loading

## Overview

**Priority**: Critical (THIS IS THE ACTUAL FIX)
**Dependencies**: TASK-GI-001 (Core Infrastructure), TASK-GI-002 (System Context Seeding)

## Problem Statement

This is **THE feature** that fixes the memory problem.

Currently, when a Claude Code session starts working on GuardKit:
- It has no knowledge of what GuardKit is
- It doesn't know previous architectural decisions
- It doesn't know what patterns worked or failed
- It makes locally-optimal choices that break the system

**Example failure**: Session implementing task-work delegation chose subprocess CLI invocation instead of SDK query() because it didn't know about the architecture decision.

## Strategic Context

Features 1 and 2 set up Graphiti and seed knowledge. This feature **actually uses** that knowledge by injecting relevant context at the start of Claude Code sessions and commands.

**This is the highest-value feature** in the entire Graphiti integration.

## Goals

1. Load critical context at Claude Code session/command start
2. Inject context into command entry points
3. Scope context to the specific task/feature being worked on
4. Keep context concise (don't overwhelm with irrelevant info)

## Non-Goals

- Real-time context updates during session
- Interactive context exploration
- Context caching/persistence

## Technical Approach

### Context Loading Function

```python
# guardkit/knowledge/context_loader.py

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class CriticalContext:
    """Context loaded at session start."""

    # System knowledge
    system_context: List[Dict[str, Any]]  # What GuardKit is
    quality_gates: List[Dict[str, Any]]   # How quality is enforced

    # Decision knowledge
    architecture_decisions: List[Dict[str, Any]]  # How things SHOULD work

    # Learning knowledge
    failure_patterns: List[Dict[str, Any]]  # What NOT to do
    successful_patterns: List[Dict[str, Any]]  # What worked

    # Task-specific (when applicable)
    similar_task_outcomes: List[Dict[str, Any]]  # Similar tasks and results
    relevant_adrs: List[Dict[str, Any]]  # Decisions affecting this work

    # Template/pattern knowledge (when applicable)
    applicable_patterns: List[Dict[str, Any]]
    relevant_rules: List[Dict[str, Any]]


async def load_critical_context(
    task_id: Optional[str] = None,
    feature_id: Optional[str] = None,
    command: Optional[str] = None
) -> CriticalContext:
    """Load must-know context at session/command start."""

    graphiti = get_graphiti()

    if not graphiti.enabled:
        return CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[],
            failure_patterns=[],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )

    # 1. Always load: System context
    system_context = await graphiti.search(
        query="GuardKit product workflow quality gate",
        group_ids=["product_knowledge", "command_workflows"],
        num_results=5
    )

    # 2. Always load: Quality gates (critical for all commands)
    quality_gates = await graphiti.search(
        query="quality gate phase approval",
        group_ids=["quality_gate_phases"],
        num_results=5
    )

    # 3. Always load: Architecture decisions
    architecture_decisions = await graphiti.search(
        query="architecture decision SDK subprocess worktree",
        group_ids=["architecture_decisions"],
        num_results=10
    )

    # 4. Always load: Failure patterns (what NOT to do)
    failure_patterns = await graphiti.search(
        query="failure error bug anti-pattern",
        group_ids=["failure_patterns"],
        num_results=5
    )

    # 5. Command-specific context
    if command == "feature-build":
        # Load feature-build specific knowledge
        fb_context = await graphiti.search(
            query="feature-build Player Coach delegation task-work",
            group_ids=["feature_build_architecture"],
            num_results=10
        )
        system_context.extend(fb_context)

    return CriticalContext(
        system_context=system_context,
        quality_gates=quality_gates,
        architecture_decisions=architecture_decisions,
        failure_patterns=failure_patterns,
        successful_patterns=[],  # Populated by Episode Capture feature
        similar_task_outcomes=[],
        relevant_adrs=[],
        applicable_patterns=[],
        relevant_rules=[]
    )
```

### Context Formatting for Injection

```python
def format_context_for_injection(context: CriticalContext) -> str:
    """Format context for injection into Claude Code session."""

    sections = []

    # Critical decisions (always show)
    if context.architecture_decisions:
        sections.append("## Architecture Decisions (MUST FOLLOW)\n")
        for decision in context.architecture_decisions[:5]:
            body = decision.get('body', {})
            sections.append(f"- **{body.get('title', 'Unknown')}**: {body.get('decision', '')}")
        sections.append("")

    # Failure patterns (always show)
    if context.failure_patterns:
        sections.append("## Known Failures (AVOID THESE)\n")
        for pattern in context.failure_patterns[:3]:
            body = pattern.get('body', {})
            sections.append(f"- {body.get('description', '')}")
        sections.append("")

    # Quality gates (for task-work and feature-build)
    if context.quality_gates:
        sections.append("## Quality Gates\n")
        for gate in context.quality_gates[:3]:
            body = gate.get('body', {})
            sections.append(f"- {body.get('phase', '')}: {body.get('requirement', '')}")
        sections.append("")

    return "\n".join(sections)
```

### Integration with Commands

```python
# In each command entry point:

# guardkit/commands/task_work.py
async def task_work(task_id: str, **options):
    """Execute task-work with context."""

    # Load context BEFORE starting work
    context = await load_critical_context(
        task_id=task_id,
        command="task-work"
    )

    # Inject context into session
    context_text = format_context_for_injection(context)

    # This context becomes part of the prompt/system message
    # for the Claude Code session

    # ... rest of task-work implementation


# guardkit/commands/feature_build.py
async def feature_build(feature_id: str, **options):
    """Execute feature-build with context."""

    context = await load_critical_context(
        feature_id=feature_id,
        command="feature-build"
    )

    context_text = format_context_for_injection(context)

    # Critical: feature-build context includes Player-Coach architecture
    # and delegation patterns

    # ... rest of feature-build implementation
```

## Acceptance Criteria

- [x] **Context loads at command start**
  - `task-work` loads task-specific context
  - `feature-build` loads feature-build architecture context
  - Context includes architecture decisions

- [x] **Architecture decisions are visible**
  - "Use SDK query() not subprocess" decision appears in context
  - "Use FEAT-XXX worktree paths" decision appears in context

- [x] **Failure patterns are visible**
  - Known failures appear as warnings
  - Sessions can avoid repeating mistakes

- [x] **Context is scoped appropriately**
  - Task-specific context appears for task commands
  - Feature-specific context appears for feature commands
  - Not overwhelmed with irrelevant information

- [x] **Graceful degradation**
  - When Graphiti unavailable, commands still work
  - Empty context doesn't break anything

## Testing Strategy

1. **Unit tests**: Mock Graphiti, verify context structure
2. **Integration tests**: Real Graphiti, verify correct queries
3. **E2E tests**: Run command, verify context appears in session

## Files to Create/Modify

### New Files
- `guardkit/knowledge/context_loader.py`
- `guardkit/knowledge/context_formatter.py`
- `tests/knowledge/test_context_loader.py`

### Modified Files
- `guardkit/commands/task_work.py` (add context loading)
- `guardkit/commands/feature_build.py` (add context loading)
- `guardkit/commands/feature_plan.py` (add context loading)

## The Expected Outcome

**Before this feature:**
```
Claude Code Session starts...
"I need to implement task-work delegation"
[No context about SDK vs subprocess]
-> Chooses subprocess (WRONG)
-> Breaks system
```

**After this feature:**
```
Claude Code Session starts...
[Context loaded from Graphiti]
"Architecture Decisions:
- Use SDK query() for task-work invocation, NOT subprocess"
"I need to implement task-work delegation"
-> Uses SDK query() (CORRECT)
-> System works
```

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Context too verbose | Limit results per category, prioritize critical decisions |
| Context latency | Load asynchronously, cache if needed |
| Stale context | Context is read-fresh each session |
| Wrong context scope | Use task/feature ID to scope queries |

## Open Questions

1. How do we inject context into Claude Code sessions? (CLAUDE.md vs prompt vs other)
2. Should context be refreshed during long sessions?
3. How much context is "too much"? (token budget)

---

## Related Documents

- [TASK-GI-001: Core Infrastructure](./TASK-GI-001-core-infrastructure.md)
- [TASK-GI-002: System Context Seeding](./TASK-GI-002-system-context-seeding.md)
- [Unified Data Architecture Decision](../../docs/research/knowledge-graph-mcp/unified-data-architecture-decision.md)