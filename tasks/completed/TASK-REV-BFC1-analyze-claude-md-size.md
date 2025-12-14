---
id: TASK-REV-BFC1
title: Analyze CLAUDE.md size exceeding Claude Code performance threshold
status: review_complete
task_type: review
created: 2025-12-14T10:00:00Z
updated: 2025-12-14T10:30:00Z
priority: high
tags: [performance, documentation, claude-code, optimization]
complexity: 5
decision_required: true
review_results:
  mode: architectural
  depth: standard
  findings_count: 5
  recommendations_count: 7
  report_path: .claude/reviews/TASK-REV-BFC1-review-report.md
  decision: implement
  implementation_tasks:
    - TASK-OPT-8085.1
    - TASK-OPT-8085.2
    - TASK-OPT-8085.3
    - TASK-OPT-8085.4
    - TASK-OPT-8085.5
---

# Task: Analyze CLAUDE.md size exceeding Claude Code performance threshold

## Problem Statement

Claude Code v2.0.69 displays a performance warning when loading the GuardKit repository:

```
⚠ Large /Users/richardwoollcott/Projects/appmilla_github/guardkit/CLAUDE.md will impact performance (57.0k chars > 40.0k)
```

The main CLAUDE.md file is **57,000 characters**, exceeding the recommended **40,000 character** threshold by 42.5%.

## Review Objectives

1. **Size Analysis**: Determine current size breakdown by section
2. **Content Audit**: Identify redundant, duplicated, or overly verbose content
3. **Optimization Opportunities**: Recommend specific reductions
4. **Architecture Assessment**: Evaluate if progressive disclosure or rules structure should be applied
5. **Decision**: Recommend approach to bring file under threshold

## Scope

### In Scope
- `/CLAUDE.md` (root) - 57k chars
- `/.claude/CLAUDE.md` - secondary file
- Current progressive disclosure implementation
- Rules structure configuration

### Out of Scope
- Template CLAUDE.md files
- Agent markdown files (separate concern)

## Key Questions

1. What sections consume the most characters?
2. Is content duplicated between root CLAUDE.md and .claude/CLAUDE.md?
3. Can sections be moved to rules/ structure for conditional loading?
4. Should we implement more aggressive progressive disclosure?
5. What is the minimum viable content for the root CLAUDE.md?

## Acceptance Criteria

- [ ] Complete size breakdown by section
- [ ] Identify top 5 largest sections
- [ ] Document any content duplication
- [ ] Provide specific reduction recommendations
- [ ] Estimate character savings per recommendation
- [ ] Present decision options with trade-offs

## Review Mode

**Recommended**: `/task-review TASK-REV-BFC1 --mode=architectural --depth=standard`

This is an analysis task - use `/task-review` NOT `/task-work`.

## Expected Deliverables

1. Size analysis report with section breakdown
2. Optimization recommendations with estimated savings
3. Decision framework: Options with pros/cons
4. Implementation plan if reduction approved
