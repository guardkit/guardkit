---
id: TASK-DOC-83F0
title: Create missing guide documents
status: backlog
created: 2025-11-27T02:00:00Z
updated: 2025-11-27T02:00:00Z
priority: high
tags: [documentation, guides, workflows]
complexity: 4
related_to: [TASK-DOC-F3BA]
---

# Task: Create Missing Guide Documents

## Context

Review task TASK-DOC-F3BA identified that several guide documents are referenced in command documentation but don't exist, resulting in broken links:

1. **docs/guides/agent-enhancement-decision-guide.md** - Referenced in TASK-DOC-F3BA, template-create.md
2. **docs/workflows/incremental-enhancement-workflow.md** - Referenced in TASK-DOC-F3BA, TASK-DOC-1E7B

These guides are critical for helping users understand:
- When to use /agent-format vs /agent-enhance
- Option A (hybrid enhancement) vs Option B (/task-work) comparison
- Phase 8 incremental enhancement workflow
- Agent enhancement best practices

## Objective

Create two comprehensive guide documents that fix broken links and provide clear guidance on agent enhancement workflows.

## Scope

### Files to Create

1. **docs/guides/agent-enhancement-decision-guide.md**:
   - Decision matrix: /agent-format vs /agent-enhance
   - Option A (hybrid) vs Option B (/task-work) comparison
   - Use case examples with recommendations
   - Quality vs speed trade-offs

2. **docs/workflows/incremental-enhancement-workflow.md**:
   - Phase 8 workflow overview
   - Task-based vs direct command approach
   - Batch enhancement strategies
   - Best practices and troubleshooting

### Files to Update (Cross-references)

3. **installer/global/commands/template-create.md**:
   - Add link to agent-enhancement-decision-guide.md
   - Add link to incremental-enhancement-workflow.md

4. **installer/global/commands/agent-enhance.md**:
   - Add link to agent-enhancement-decision-guide.md
   - Add link to incremental-enhancement-workflow.md

## Acceptance Criteria

### agent-enhancement-decision-guide.md
- [ ] Decision matrix created: /agent-format vs /agent-enhance
- [ ] Quality comparison documented (6/10 vs 9/10)
- [ ] Duration comparison documented (instant vs 2-5 min)
- [ ] Option A vs Option B comparison table created
- [ ] Use case examples provided (5-7 scenarios)
- [ ] Quality vs speed trade-offs explained
- [ ] Batch enhancement guidance included
- [ ] Cross-references to command docs added

### incremental-enhancement-workflow.md
- [ ] Phase 8 workflow overview documented
- [ ] Task-based approach explained (--create-agent-tasks)
- [ ] Direct command approach explained (--no-create-agent-tasks)
- [ ] Workflow comparison table created
- [ ] Batch enhancement strategies documented (parallel vs sequential)
- [ ] Best practices section added (5-7 practices)
- [ ] Troubleshooting section added (common issues)
- [ ] Code examples included for both approaches
- [ ] Cross-references to command docs added

### Cross-reference Updates
- [ ] template-create.md links updated
- [ ] agent-enhance.md links updated
- [ ] No broken links introduced
- [ ] All references validated

## Implementation Notes

### Content Outline: agent-enhancement-decision-guide.md

```markdown
# Agent Enhancement Decision Guide

## Overview
[Brief introduction to agent enhancement and why choices matter]

## Decision 1: Format vs Enhance

### When to Use /agent-format
- Template creation (automatic in /template-create)
- Quick structural fixes
- Consistency across templates
- **Quality**: 6/10 (basic structure)
- **Duration**: Instant

### When to Use /agent-enhance
- Adding template-specific content
- Code examples and best practices
- Boundary section validation
- **Quality**: 9/10 (AI-powered)
- **Duration**: 2-5 minutes

### Decision Matrix

| Scenario | Recommended Command | Rationale |
|----------|---------------------|-----------|
| Creating template from codebase | `/agent-format` (auto) | Ensures structural consistency |
| Enhancing with code examples | `/agent-enhance` | AI analyzes templates for relevant content |
| Quick structure fix | `/agent-format` | Fast, no AI needed |
| Template-specific guidance | `/agent-enhance` | AI-powered content generation |
| Batch structural updates | `/agent-format` | Fast for multiple agents |
| Batch content enhancement | `/agent-enhance` | Use `--hybrid` for reliability |

## Decision 2: Hybrid vs Task-Work

### Option A: Hybrid Enhancement (Recommended)
```bash
/agent-enhance my-template/api-specialist --hybrid
```
- **Duration**: 2-5 minutes per agent
- **Quality**: 9/10 (AI-powered with fallback)
- **Reliability**: 100% (falls back to static on AI failure)
- **Use when**: Need fast, reliable enhancement

### Option B: Full Workflow with /task-work
```bash
/task-work TASK-AGENT-XXX
```
- **Duration**: 30-60 minutes per agent
- **Quality**: 9/10 (same AI logic + quality gates)
- **Reliability**: 100% (comprehensive testing)
- **Use when**: Need full quality gates and traceability

### Comparison Table

| Feature | Option A (Hybrid) | Option B (Task-Work) |
|---------|-------------------|----------------------|
| Duration | 2-5 min | 30-60 min |
| Quality | 9/10 | 9/10 |
| Phases | Enhancement only | Full workflow (2-5.5) |
| Testing | Validation only | Full test suite |
| Traceability | Command output | Task tracking |
| Best for | Fast iteration | Production templates |

## Use Case Examples

[7 detailed scenarios with recommendations]

## Batch Enhancement Strategies

### Parallel Enhancement (Recommended)
[How to enhance multiple agents simultaneously]

### Sequential Enhancement
[When to enhance agents one at a time]

## Quality vs Speed Trade-offs

[Detailed analysis of trade-offs]

## See Also
[Cross-references to related documentation]
```

### Content Outline: incremental-enhancement-workflow.md

```markdown
# Incremental Enhancement Workflow (Phase 8)

## Overview
[Introduction to Phase 8 and incremental enhancement concept]

## Workflow Approaches

### Approach 1: Task-Based (Default)

**When**: `/template-create` with default behavior (tasks created automatically)

**Workflow**:
```bash
# Step 1: Create template (tasks auto-created)
/template-create --path ~/my-project
# Output: 5 agent enhancement tasks created in tasks/backlog/

# Step 2: Review tasks
/task-status

# Step 3: Enhance agents via tasks
/task-work TASK-AGENT-001  # Full workflow (30-60 min)
/task-work TASK-AGENT-002
# OR use hybrid for speed:
/agent-enhance my-template/agent-1 --hybrid  # 2-5 min
/task-complete TASK-AGENT-001

# Step 4: Complete template
[All agents enhanced, template ready]
```

### Approach 2: Direct Commands

**When**: `/template-create --no-create-agent-tasks`

**Workflow**:
```bash
# Step 1: Create template (no tasks)
/template-create --path ~/my-project --no-create-agent-tasks

# Step 2: Enhance agents directly
/agent-enhance my-template/api-specialist --hybrid
/agent-enhance my-template/testing-specialist --hybrid
/agent-enhance my-template/domain-specialist --hybrid

# Step 3: Validate (optional)
/template-validate my-template
```

## Workflow Comparison

[Detailed comparison table of both approaches]

## Batch Enhancement Strategies

### Parallel Enhancement (Conductor)
[Using Conductor.build for parallel agent enhancement]

### Sequential Enhancement
[One agent at a time, dependency-aware]

## Best Practices

1. **Use hybrid strategy for reliability**
2. **Enhance related agents together**
3. **Preview with --dry-run first**
4. **Commit after each agent** (version control)
5. **Validate before distribution** (/template-validate)
6. **Use tasks for production templates** (traceability)
7. **Use direct commands for experimentation** (speed)

## Troubleshooting

### Issue: AI Enhancement Times Out
[Solution with fallback to static]

### Issue: Enhancement Tasks Not Created
[Check --no-create-agent-tasks flag]

### Issue: Enhancement Quality Low
[Use /task-work for full quality gates]

## Code Examples

[Complete examples for common scenarios]

## See Also
[Cross-references to related documentation]
```

## Source

**Review Report**: [TASK-DOC-F3BA Review Report](../../../.claude/task-plans/TASK-DOC-F3BA-review-report.md)
**Priority**: P2 (High)
**Estimated Effort**: 3-4 hours

## Method

**Claude Code Direct** - New file creation, documentation only
