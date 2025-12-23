---
id: TASK-AB-6908
title: Update agent definitions to match GuardKit template standards
status: backlog
created: 2025-12-23T07:22:00Z
updated: 2025-12-23T07:22:00Z
priority: high
tags: [autobuild, agents, templates, documentation]
complexity: 3
parent_review: TASK-REV-47D2
wave: 1
conductor_workspace: autobuild-phase1a-wave1-1
implementation_mode: direct
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Update agent definitions to match GuardKit template standards

## Description

Update `autobuild-player.md` and `autobuild-coach.md` to match GuardKit's agent template standards by adding frontmatter metadata and restructuring content into the Boundaries section format.

## Parent Review

This task was generated from review task TASK-REV-47D2.

**Review Findings**: Agent content is well-designed but missing frontmatter and Boundaries sections.

## Acceptance Criteria

### For autobuild-player.md:
- [ ] Add frontmatter with required metadata (name, description, stack, phase, capabilities, keywords, model, tools)
- [ ] Restructure content into Boundaries section (ALWAYS/NEVER/ASK)
- [ ] Preserve all existing content quality
- [ ] Validate against GuardKit template standard (code-reviewer.md as reference)

### For autobuild-coach.md:
- [ ] Add frontmatter with required metadata
- [ ] Restructure content into Boundaries section (ALWAYS/NEVER/ASK)
- [ ] Preserve all existing content quality
- [ ] Validate against GuardKit template standard

## Implementation Details

### Required Frontmatter (autobuild-player.md)

```yaml
---
name: autobuild-player
description: Implementation-focused agent for autonomous code generation in adversarial cooperation workflow
stack: [cross-stack]
phase: autobuild-implementation
capabilities: [code-generation, test-writing, requirement-implementation, feedback-response]
keywords: [autobuild, player, implementation, adversarial-cooperation, autonomous]
model: sonnet
tools: Read, Write, Edit, Bash, Grep, Glob
---
```

### Required Frontmatter (autobuild-coach.md)

```yaml
---
name: autobuild-coach
description: Validation-focused agent for code review and approval in adversarial cooperation workflow
stack: [cross-stack]
phase: autobuild-validation
capabilities: [code-review, test-execution, requirement-validation, feedback-generation]
keywords: [autobuild, coach, validation, adversarial-cooperation, quality-gates]
model: sonnet
tools: Read, Bash, Grep, Glob
---
```

### Boundaries Structure

**ALWAYS**:
- List mandatory behaviors with justification
- Example: "✅ Write tests alongside implementation (ensures testability)"

**NEVER**:
- List prohibited behaviors with justification
- Example: "❌ Never declare task complete - only Coach can approve (prevents false success)"

**ASK**:
- List scenarios requiring clarification
- Example: "⚠️ When requirements are ambiguous: Ask for clarification before implementing"

## Files to Modify

1. `.claude/agents/autobuild-player.md`
2. `.claude/agents/autobuild-coach.md`

## Reference

Review GuardKit template standard: `.claude/agents/code-reviewer.md`

## Estimated Effort

1-2 hours (direct edit, no testing needed)

## Implementation Mode

**Direct** - Simple restructuring, no code changes or tests required
