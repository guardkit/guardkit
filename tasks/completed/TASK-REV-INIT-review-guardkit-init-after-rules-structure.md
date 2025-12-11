---
id: TASK-REV-INIT
title: Review guardkit init command and documentation after rules structure changes
status: completed
task_type: review
review_mode: code-quality
review_depth: standard
created: 2025-12-11T18:00:00Z
updated: 2025-12-11T19:50:00Z
review_results:
  mode: code-quality
  depth: standard
  score: 60
  findings_count: 3
  recommendations_count: 4
  decision: implement
  report_path: .claude/reviews/TASK-REV-INIT-review-report.md
  completed_at: 2025-12-11T19:30:00Z
  implementation_tasks:
    - TASK-GI-001
    - TASK-GI-002
    - TASK-GI-003
  implementation_folder: tasks/backlog/guardkit-init-rules-fix/
priority: high
tags: [review, guardkit-init, rules-structure, progressive-disclosure, documentation]
complexity: 5
decision_required: false
related_to: [TASK-REV-CB0F, TASK-TC-DEFAULT-FLAGS, TASK-RULES-ENHANCE, TASK-GI-001, TASK-GI-002, TASK-GI-003]
---

# Task: Review guardkit init Command After Rules Structure Changes

## Background

Following the progressive disclosure refactoring and Claude rules structure implementation (TASK-CRS-014), and the recent changes to `/template-create` defaults (TASK-TC-DEFAULT-FLAGS), the `guardkit init` command and related documentation may need updates to reflect:

1. **New default behavior**: `--use-rules-structure` now default true, `--claude-md-size-limit` now 50KB
2. **New output structure**: Templates now generate `.claude/rules/` directory by default
3. **Progressive disclosure**: Agents split into core + extended files
4. **New documentation**: Recently created guide explaining subagents, templates, settings, and manifest files

## Review Scope

### 1. guardkit init Command

**Files to Review**:
- `installer/scripts/install.sh`
- `installer/core/commands/guardkit-init.md` (if exists)
- Any Python scripts related to `guardkit init`

**Review Questions**:
- Does `guardkit init <template>` correctly handle templates with rules structure?
- Does it copy `.claude/rules/` directory properly?
- Does it handle both old-style (single CLAUDE.md) and new-style (rules structure) templates?
- Are there any hardcoded paths that assume `agents/` but not `rules/guidance/`?

### 2. Template Initialization Flow

**Files to Review**:
- Template initialization logic
- File copying/linking mechanisms
- Path resolution for rules structure

**Review Questions**:
- When initializing a project with `guardkit init react-typescript`, does it:
  - Copy `.claude/CLAUDE.md` (core file)?
  - Copy `.claude/rules/` directory structure?
  - Copy `agents/` directory with enhanced agents?
  - Preserve `paths:` frontmatter in rules files?
- Are symlinks handled correctly (if any)?

### 3. Documentation Updates

**Files to Review**:
- `CLAUDE.md` (root) - Installation & Setup section
- `docs/guides/template-philosophy.md`
- `docs/guides/progressive-disclosure.md`
- `docs/guides/rules-structure-guide.md`
- Recently created subagents/templates/manifest documentation (need to identify file)

**Review Questions**:
- Does documentation reflect new default flags?
- Are examples updated to show rules structure output?
- Is the subagents/templates/manifest guide accurate after changes?
- Are there any outdated references to `rules/agents/` (should be `rules/guidance/`)?

### 4. Reference Templates

**Files to Review**:
- `installer/core/templates/react-typescript/`
- `installer/core/templates/fastapi-python/`
- `installer/core/templates/nextjs-fullstack/`
- `installer/core/templates/default/`

**Review Questions**:
- Do reference templates use rules structure?
- If not, should they be updated to demonstrate new defaults?
- Are template READMEs accurate about what will be generated?

### 5. Post-Init Verification

**Review Questions**:
- After `guardkit init`, does the project have correct structure?
- Can Claude Code load rules correctly based on `paths:` frontmatter?
- Are there any missing files or broken references?

## Acceptance Criteria

- [ ] `guardkit init` command reviewed for rules structure compatibility
- [ ] Template initialization flow verified to handle `.claude/rules/`
- [ ] Documentation checked for accuracy with new defaults
- [ ] Reference templates evaluated for rules structure adoption
- [ ] Subagents/templates/manifest documentation reviewed for accuracy
- [ ] No orphaned `rules/agents/` references found
- [ ] Recommendations documented for any required updates

## Decision Options

After review:
- **[A]ccept** - Everything is up to date, no changes needed
- **[I]mplement** - Create tasks to fix identified issues
- **[R]evise** - Request deeper analysis on specific areas

## Related Context

### Recent Changes
- TASK-CRS-014: Renamed `rules/agents/` to `rules/guidance/`
- TASK-REV-CB0F: Analyzed `/template-create` and `/agent-enhance` output
- TASK-TC-DEFAULT-FLAGS: Changing defaults to `--use-rules-structure` and 50KB

### Key Files to Locate
- Subagents/templates/manifest documentation (recently created)
- `guardkit init` implementation script
- Template copying logic

## Notes

- This review should identify ALL places that need updating
- Focus on user-facing experience after running `guardkit init`
- Consider backward compatibility with existing templates
- Document any breaking changes that require migration guidance
