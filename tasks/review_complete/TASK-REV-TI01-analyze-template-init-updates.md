---
id: TASK-REV-TI01
title: Analyze template-init command for progressive disclosure and rules structure updates
status: review_complete
created: 2025-12-12T10:00:00Z
updated: 2025-12-12T10:30:00Z
priority: high
tags: [review, template-init, progressive-disclosure, rules-structure, analysis]
task_type: review
complexity: 5
decision_required: true
review_results:
  mode: architectural
  depth: standard
  score: 65
  findings_count: 8
  recommendations_count: 5
  decision: refactor
  report_path: .claude/reviews/TASK-REV-TI01-review-report.md
  completed_at: 2025-12-12T10:30:00Z
---

# Task: Analyze template-init command for progressive disclosure and rules structure updates

## Description

Review the `/template-init` command (and underlying `guardkit init` / `init-project.sh`) to determine what updates are required following the recent implementation of:

1. **Progressive Disclosure** - Split files architecture (`{name}.md` + `{name}-ext.md`)
2. **Claude Rules Structure** - Modular `.claude/rules/` directory with path-specific loading

The `/template-create` command has been updated with these features, but `/template-init` may need corresponding updates to properly initialize projects with the new structure.

## Review Scope

### Files to Analyze

1. **Command Specification**: `installer/core/commands/template-init.md`
2. **Implementation Script**: `installer/scripts/init-project.sh`
3. **Related Documentation**:
   - `docs/guides/template-init-walkthrough.md`
   - `docs/implementation/template-init-implementation-guide.md`
   - `docs/implementation/template-init-feature-porting-tasks.md`
   - `docs/decisions/template-init-vs-template-create-analysis.md`

### Reference Material (What template-init should align with)

1. **Rules Structure Guide**: `docs/guides/rules-structure-guide.md`
2. **Progressive Disclosure Guide**: `docs/guides/progressive-disclosure.md`
3. **Template Create Command**: `installer/core/commands/template-create.md`
4. **Existing Templates**: `installer/core/templates/*/` (to see current structure)

## Key Questions to Answer

### Progressive Disclosure

1. Do templates initialized by `template-init` include split file structure?
2. Are core vs extended files properly separated?
3. Does the initialization process preserve the split structure from source templates?

### Rules Structure

1. Does `template-init` create the `.claude/rules/` directory structure?
2. Are path-specific rules (`paths:` frontmatter) properly copied/generated?
3. Does the `--no-rules-structure` flag exist/work for `template-init`?
4. Is conditional loading set up correctly for initialized projects?

### Consistency

1. Are flags between `/template-create` and `/template-init` consistent?
2. Is the documentation aligned with current capabilities?
3. Are there any deprecated patterns still present?

## Acceptance Criteria

- [ ] Complete analysis of current `template-init` implementation
- [ ] Identify gaps between `template-init` and recent progressive disclosure work
- [ ] Identify gaps between `template-init` and recent rules structure work
- [ ] Document specific updates required (if any)
- [ ] Recommend implementation approach (modify existing vs refactor)
- [ ] Estimate complexity of required changes

## Review Output

The review should produce:

1. **Gap Analysis**: What's missing or inconsistent
2. **Update Recommendations**: Specific changes needed
3. **Implementation Tasks**: Breakdown of work if updates are required
4. **Risk Assessment**: Impact of changes on existing users

## Related Tasks

- Recent progressive disclosure implementation
- Recent rules structure implementation
- TASK-TC-DEFAULT-FLAGS (template-create default flags)

## Notes

This is a **review task** - use `/task-review` workflow, not `/task-work`.

The goal is analysis and recommendations, not implementation. Implementation tasks will be created based on review findings.
