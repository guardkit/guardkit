---
id: TASK-FCD-002
title: Update CLAUDE.md documentation
status: completed
created: 2026-01-24T16:35:00Z
updated: 2026-01-24T17:15:00Z
priority: medium
tags: [documentation, feature-complete, claude-md]
complexity: 1
parent_review: TASK-REV-FCD
feature_id: FEAT-FCD
implementation_mode: direct
wave: 1
estimated_minutes: 15
---

# Task: Update CLAUDE.md documentation

## Problem Statement

The root CLAUDE.md does not list `/feature-complete` in the AutoBuild workflow section, making the command less discoverable.

## Requirements

Update CLAUDE.md to:
1. Add `/feature-complete` to the AutoBuild workflow section
2. Show syntax and basic flags
3. Clarify when to use vs auto-completion

## Acceptance Criteria

- [x] `/feature-complete` listed in AutoBuild section of root CLAUDE.md
- [x] Syntax shown: `/feature-complete FEAT-XXX [--dry-run] [--force]`
- [x] Brief description of when to use
- [x] Consistent formatting with existing command listings

## Implementation Notes

**Location in CLAUDE.md**: Under "### Autonomous Build Workflow (AutoBuild)" section (around line 65-80)

**Add after `/feature-build`**:
```markdown
### Feature Completion
```bash
/feature-complete FEAT-XXX [--dry-run] [--force]
```

The `/feature-complete` command finalizes a feature after all tasks pass:
- Archives feature folder to `tasks/completed/`
- Displays merge/PR handoff instructions
- Provides cleanup command

**Note**: Features that complete successfully through `/feature-build` are auto-completed. Use `/feature-complete` for:
- Features that failed and need manual completion
- Explicit archival when feature wasn't run through AutoBuild
```

## Files to Modify

- **Edit**: `CLAUDE.md` (root)
- **Edit**: `.claude/CLAUDE.md` (if applicable)

## Testing

After modification:
1. Review CLAUDE.md renders correctly
2. Verify `/feature-complete` appears in command listings
3. Check formatting consistency with other commands
