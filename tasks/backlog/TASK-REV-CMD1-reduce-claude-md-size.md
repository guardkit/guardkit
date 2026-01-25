---
id: TASK-REV-CMD1
title: Reduce CLAUDE.md file size below 40k character limit
status: review_complete
created: 2026-01-13T10:00:00Z
updated: 2026-01-13T11:30:00Z
priority: high
tags: [documentation, performance, claude-code]
task_type: review
complexity: 5
review_results:
  mode: architectural
  depth: standard
  score: 72
  findings_count: 8
  recommendations_count: 5
  report_path: .claude/reviews/TASK-REV-CMD1-review-report.md
  completed_at: 2026-01-13T11:30:00Z
---

# Task: Reduce CLAUDE.md file size below 40k character limit

## Problem Statement

Claude Code displays a performance warning when the CLAUDE.md file exceeds 40,000 characters:

```
⚠Large CLAUDE.md will impact performance (53.2k chars > 40.0k) • /memory to edit
```

The current CLAUDE.md is **53.2k characters**, which is **33% over the recommended limit**.

## Analysis Scope

### Files to Analyze
- `/CLAUDE.md` (root) - Primary file, likely the largest contributor
- `/.claude/CLAUDE.md` - Project-specific instructions
- Any other CLAUDE.md files in the hierarchy

### Analysis Goals
1. **Measure current state**: Exact character counts per file and section
2. **Identify redundancy**: Content duplicated across files or with rules/
3. **Evaluate necessity**: Which content is essential vs. nice-to-have
4. **Propose structure**: Leverage progressive disclosure and rules structure

## Acceptance Criteria

- [ ] Document current character counts per CLAUDE.md file
- [ ] Identify top 5 largest sections by character count
- [ ] List content that can be moved to `rules/` structure
- [ ] List content that can be moved to `docs/` (extended content)
- [ ] Identify redundant/duplicate content
- [ ] Propose specific reductions with estimated character savings
- [ ] Final recommendation achieves < 40k total characters
- [ ] Ensure no critical functionality is lost

## Constraints

- Must maintain all critical workflow instructions
- Must preserve progressive disclosure capability
- Must keep essential command references
- Should leverage existing `rules/` infrastructure
- Should follow GuardKit's own template philosophy

## Success Metrics

- Combined CLAUDE.md content < 40,000 characters
- No loss of critical AI guidance
- Clear loading instructions for extended content
- Performance warning eliminated

## Review Approach

1. **Audit**: Measure all CLAUDE.md files and sections
2. **Classify**: Essential (always load) vs. Extended (load on-demand)
3. **Restructure**: Move content to appropriate locations
4. **Validate**: Ensure character count < 40k
5. **Test**: Verify Claude Code no longer shows warning

## Related Documentation

- [Progressive Disclosure Guide](docs/guides/progressive-disclosure.md)
- [Rules Structure Guide](docs/guides/rules-structure-guide.md)
- [Template Philosophy Guide](docs/guides/template-philosophy.md)
