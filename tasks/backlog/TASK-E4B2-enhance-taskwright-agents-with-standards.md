---
id: TASK-E4B2
title: "Enhance Taskwright's .claude agents with discovery metadata and boundary sections"
status: backlog
created: 2025-11-26T09:45:00Z
updated: 2025-11-26T09:45:00Z
priority: high
tags: [agent-enhancement, discovery-metadata, boundary-sections, github-best-practices]
complexity: 4
estimated_hours: 2
task_type: implementation
related_tasks: [TASK-D3A1, TASK-BAA5]
---

# Task: Enhance Taskwright's .claude Agents with Discovery Metadata and Boundary Sections

## Problem Statement

The Taskwright repository's `.claude/agents/` directory contains 7 agents that are missing:
1. **Discovery metadata** (frontmatter with stack/phase/capabilities/keywords)
2. **Boundary sections** (ALWAYS/NEVER/ASK per GitHub best practices)

These are current standards we've implemented for all templates and agents, but Taskwright's own agents haven't been updated yet.

## Context

**Current State** (`.claude/agents/`):
- code-reviewer.md
- debugging-specialist.md
- qa-tester.md
- software-architect.md
- task-manager.md
- test-orchestrator.md
- test-verifier.md

**All agents currently have**:
- Basic frontmatter (name, description, model, tools)
- Agent instructions and responsibilities

**All agents are MISSING**:
- Discovery metadata (stack, phase, capabilities, keywords)
- Boundary sections (ALWAYS/NEVER/ASK)

## Requirements

### 1. Add Discovery Metadata

Add to each agent's frontmatter:

```yaml
---
name: agent-name
description: agent description
stack: [cross-stack]  # or specific stack if applicable
phase: orchestration|review|testing|implementation
capabilities: [list of specific capabilities]
keywords: [searchable terms for agent discovery]
model: sonnet
tools: [list of tools]
---
```

**Examples**:

**code-reviewer.md**:
```yaml
stack: [cross-stack]
phase: review
capabilities: [code-quality, SOLID-compliance, test-coverage, security-review]
keywords: [code-review, quality-gates, phase-5, maintainability]
```

**task-manager.md**:
```yaml
stack: [cross-stack]
phase: orchestration
capabilities: [workflow-management, phase-orchestration, tdd, bdd, standard-mode]
keywords: [task-orchestration, workflow, phases, development-modes]
```

**test-orchestrator.md**:
```yaml
stack: [cross-stack]
phase: testing
capabilities: [test-execution, quality-gates, compilation-check, coverage-analysis]
keywords: [testing, phase-4, quality-gates, test-enforcement]
```

### 2. Add Boundary Sections

Add to each agent after "Quick Start" or similar introductory section, before detailed instructions:

```markdown
## Boundaries

### ALWAYS
- ✅ [Non-negotiable action 1] ([rationale])
- ✅ [Non-negotiable action 2] ([rationale])
- ✅ [Non-negotiable action 3] ([rationale])
- ✅ [Non-negotiable action 4] ([rationale])
- ✅ [Non-negotiable action 5] ([rationale])
[5-7 rules total]

### NEVER
- ❌ [Prohibited action 1] ([rationale])
- ❌ [Prohibited action 2] ([rationale])
- ❌ [Prohibited action 3] ([rationale])
- ❌ [Prohibited action 4] ([rationale])
- ❌ [Prohibited action 5] ([rationale])
[5-7 rules total]

### ASK
- ⚠️ [Escalation scenario 1] ([rationale])
- ⚠️ [Escalation scenario 2] ([rationale])
- ⚠️ [Escalation scenario 3] ([rationale])
[3-5 scenarios total]
```

**Example for test-orchestrator.md**:

```markdown
## Boundaries

### ALWAYS
- ✅ Run build verification before tests (block if compilation fails)
- ✅ Execute in technology-specific test runner (pytest/vitest/dotnet test)
- ✅ Report failures with actionable error messages (aid debugging)
- ✅ Enforce 100% test pass rate (zero tolerance for failures)
- ✅ Validate test coverage thresholds (ensure quality gates met)

### NEVER
- ❌ Never approve code with failing tests (zero tolerance policy)
- ❌ Never skip compilation check (prevents false positive test runs)
- ❌ Never modify test code to make tests pass (integrity violation)
- ❌ Never ignore coverage below threshold (quality gate bypass prohibited)
- ❌ Never run tests without dependency installation (environment consistency required)

### ASK
- ⚠️ Coverage 70-79%: Ask if acceptable given task complexity and risk level
- ⚠️ Performance tests failing: Ask if acceptable for non-production changes
- ⚠️ Flaky tests detected: Ask if should quarantine or fix immediately
```

## Implementation Approach

### Phase 1: Discovery Metadata (1 hour)

For each agent:
1. Read agent file to understand role, phase, and capabilities
2. Add appropriate discovery metadata to frontmatter
3. Ensure keywords match how agents are discovered during `/task-work`

**Stack categorization**:
- `[cross-stack]` - Used by all templates (code-reviewer, task-manager, test-orchestrator, test-verifier, software-architect, qa-tester, debugging-specialist)

**Phase categorization**:
- `orchestration` - task-manager
- `review` - code-reviewer, software-architect
- `testing` - test-orchestrator, test-verifier, qa-tester
- `debugging` - debugging-specialist

### Phase 2: Boundary Sections (1 hour)

For each agent:
1. Analyze agent's responsibilities and instructions
2. Extract 5-7 ALWAYS rules (non-negotiable actions)
3. Extract 5-7 NEVER rules (prohibited actions)
4. Extract 3-5 ASK scenarios (human escalation points)
5. Insert boundary section after introduction, before detailed instructions

**Placement**: After "Core Philosophy" or similar introductory section, before detailed workflows

## Files to Modify

All files in `.claude/agents/`:
1. code-reviewer.md
2. debugging-specialist.md
3. qa-tester.md
4. software-architect.md
5. task-manager.md
6. test-orchestrator.md
7. test-verifier.md

## Acceptance Criteria

- [ ] All 7 agents have discovery metadata in frontmatter (stack, phase, capabilities, keywords)
- [ ] All 7 agents have boundary sections (ALWAYS/NEVER/ASK)
- [ ] ALWAYS sections have 5-7 rules with emojis and rationales
- [ ] NEVER sections have 5-7 rules with emojis and rationales
- [ ] ASK sections have 3-5 scenarios with emojis and rationales
- [ ] Boundary sections placed consistently (after intro, before detailed instructions)
- [ ] Discovery metadata enables agent routing during `/task-work`
- [ ] All agents follow GitHub best practices (from 2,500+ repo analysis)

## References

- **GitHub Best Practices**: docs/analysis/github-agent-best-practices-analysis.md
- **Agent Discovery**: docs/guides/agent-discovery-guide.md
- **Template Examples**: installer/global/agents/*.md (reference implementations)
- **Related Reviews**: TASK-D3A1, TASK-BAA5

## Success Metrics

When complete:
- ✅ Taskwright's agents match quality standards of template agents
- ✅ Agent discovery works for Taskwright development
- ✅ Boundary sections provide clear behavioral guidelines
- ✅ All agents follow consistent format and structure
