---
id: TASK-CRS-014
title: Update Agent-Enhance Command for Rules Structure Support
status: backlog
task_type: review
created: 2025-12-11T14:30:00Z
updated: 2025-12-11T14:30:00Z
priority: medium
tags: [agent-enhance, rules-structure, installer, integration]
complexity: 5
parent_feature: claude-rules-structure
wave: 3
implementation_mode: task-work
conductor_workspace: claude-rules-wave3-4
estimated_hours: 3-4
dependencies:
  - TASK-CRS-002
---

# Task: Update Agent-Enhance Command for Rules Structure Support

## Description

Review and plan updates to the `/agent-enhance` command and related installer components to support the new Claude Code rules structure. Currently, agent-enhance outputs to `agents/` directory with progressive disclosure split. For rules structure compatibility, it needs to optionally output to `rules/agents/` with `paths:` frontmatter for conditional loading.

## Review Scope

### 1. Current Agent-Enhance Behavior
- Outputs enhanced agents to `agents/` directory
- Uses progressive disclosure: `{agent}.md` + `{agent}-ext.md`
- Generates boundary sections (ALWAYS/NEVER/ASK)
- Supports `--strategy=ai|static|hybrid`

### 2. Required Changes for Rules Structure

**Output Path Options:**
- Default: `agents/` (current behavior, backward compatible)
- Rules mode: `rules/agents/` (when `--use-rules-structure` active)

**Paths Frontmatter Generation:**
- Infer `paths:` patterns from agent capabilities and technologies
- Example: `fastapi-specialist` → `paths: **/router*.py, **/api/**/*.py`
- Example: `react-query-specialist` → `paths: **/*query*, **/*api*`

**Integration Points:**
- Detect if template uses rules structure (check for `rules/` directory)
- Coordinate with `RulesStructureGenerator` from CRS-002
- Update `PathPatternInferrer` from CRS-004 to support agent paths

### 3. Files to Analyze

1. `installer/core/commands/agent-enhance.md` - Command specification
2. `installer/core/agents/agent-content-enhancer.md` - Enhancement agent
3. `installer/core/lib/template_generator/` - Template generation utilities
4. `installer/scripts/install.sh` - Installer script (symlinks)

### 4. Questions to Answer

1. Should agent-enhance auto-detect rules structure or require explicit flag?
2. How should path patterns be inferred from agent metadata?
3. Should existing `agents/` output be migrated to `rules/agents/`?
4. What happens to extended files (`-ext.md`) in rules structure?
5. How does this interact with template validation?

## Acceptance Criteria

- [ ] Current agent-enhance behavior documented
- [ ] Required changes identified and specified
- [ ] Path pattern inference strategy defined
- [ ] Integration points with CRS-002 and CRS-004 clarified
- [ ] Implementation subtasks created if needed
- [ ] Backward compatibility approach confirmed

## Review Deliverables

1. **Analysis Report**: Current state vs required state
2. **Design Document**: Path inference algorithm
3. **Implementation Plan**: Subtasks if complex enough
4. **Integration Notes**: Coordination with CRS-002, CRS-004

## Notes

- This is a **review task** (`task_type: review`)
- Use `/task-review TASK-CRS-014 --mode=architectural` to execute
- Wave 3 task (parallel with CRS-003, CRS-004, CRS-005)
- May spawn implementation subtask(s) based on review findings
- Consider whether this should be split into multiple implementation tasks
