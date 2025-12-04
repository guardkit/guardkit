---
id: TASK-PD-017
title: Update CLAUDE.md with loading instructions documentation
status: backlog
created: 2025-12-03T16:00:00Z
updated: 2025-12-03T16:00:00Z
priority: medium
tags: [progressive-disclosure, phase-5, documentation, claude-md]
complexity: 3
blocked_by: [TASK-PD-016]
blocks: [TASK-PD-018]
review_task: TASK-REV-426C
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Update CLAUDE.md with loading instructions documentation

## Phase

**Phase 5: Validation & Documentation**

## Description

Update the main GuardKit CLAUDE.md to document the progressive disclosure feature and explain how loading instructions work.

## Content to Add

### Add to CLAUDE.md

Add new section after "Template Quality Standards":

```markdown
## Progressive Disclosure

GuardKit uses progressive disclosure to optimize context window usage while maintaining comprehensive documentation.

### How It Works

Agent and template files are split into:

1. **Core files** (`{name}.md`): Essential content always loaded
   - Quick Start examples (5-10)
   - Boundaries (ALWAYS/NEVER/ASK)
   - Capabilities summary
   - Phase integration
   - Loading instructions

2. **Extended files** (`{name}-ext.md`): Detailed reference loaded on-demand
   - Detailed code examples (30+)
   - Best practices with full explanations
   - Anti-patterns with code samples
   - Technology-specific guidance
   - Troubleshooting scenarios

### Loading Extended Content

When implementing detailed code, load the extended reference:

```bash
# For agents
cat agents/{agent-name}-ext.md

# For template patterns
cat docs/patterns/README.md

# For reference documentation
cat docs/reference/README.md
```

### Benefits

- **55-60% token reduction** in typical tasks
- **Faster responses** from reduced context
- **Same comprehensive content** available when needed
- **Competitive positioning** vs other AI dev tools

### For Template Authors

When creating templates with `/template-create`:
- CLAUDE.md is automatically split into core + docs/
- Agent files are automatically split during `/agent-enhance`
- Use `--no-split` flag for single-file output (not recommended)

See [Progressive Disclosure Guide](docs/guides/progressive-disclosure.md) for details.
```

## Acceptance Criteria

- [ ] Progressive Disclosure section added to CLAUDE.md
- [ ] Loading instructions explained
- [ ] Benefits documented
- [ ] Template author guidance included
- [ ] Links to detailed guide (if created)

## Files to Modify

1. `CLAUDE.md` - Add Progressive Disclosure section
2. `.claude/CLAUDE.md` - Add corresponding section if different

## Estimated Effort

**0.5 days**

## Dependencies

- TASK-PD-016 (validation updated)
