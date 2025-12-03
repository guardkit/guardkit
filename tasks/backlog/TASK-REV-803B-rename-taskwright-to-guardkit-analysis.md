---
id: TASK-REV-803B
title: "Rename Taskwright to GuardKit - Comprehensive Analysis"
status: completed
task_type: review
created: 2025-12-03T09:37:53Z
updated: 2025-12-03T10:30:00Z
priority: critical
tags: [rename, refactoring, breaking-change, infrastructure]
complexity: 8
decision_required: true
review_results:
  mode: architectural
  depth: comprehensive
  score: 85
  findings_count: 15
  recommendations_count: 8
  decision: implement
  report_path: .claude/reviews/TASK-REV-803B-review-report.md
  completed_at: 2025-12-03T10:30:00Z
---

# Review Task: Rename Taskwright to GuardKit - Comprehensive Analysis

## Background

A naming conflict has been discovered with an existing AI-oriented application called "Taskwright". To avoid confusion and potential trademark issues, we need to rename the project from **Taskwright** to **GuardKit**.

This review task will:
1. Identify all locations where the name appears
2. Determine the correct order of operations
3. Create implementation subtasks for the refactoring

## Scope of Analysis

### Areas to Investigate

1. **GitHub Infrastructure**
   - Organisation name (taskwright-dev → guardkit-dev?)
   - Repository name (taskwright → guardkit)
   - GitHub Actions workflows
   - Release tags and versions

2. **Installer & Configuration**
   - `installer/scripts/install.sh`
   - Marker files (`~/.agentecflow/*.marker*`)
   - Symlink targets
   - Binary/script names (`taskwright` CLI command)

3. **Documentation**
   - `CLAUDE.md` (root and `.claude/`)
   - `README.md`
   - All markdown files in `docs/`
   - Command specifications in `installer/global/commands/`

4. **Code References**
   - Python modules and imports
   - Template names containing "taskwright"
   - Agent references
   - Error messages and logging

5. **User-Facing Elements**
   - CLI command name (`taskwright init`, etc.)
   - Template references
   - Help text and usage examples

## Order of Operations Analysis

### Recommended Sequence

**Phase 1: External Infrastructure (User Action Required)**
1. Fork/backup the repository
2. Rename GitHub organisation (taskwright-dev → guardkit-dev)
3. Rename repository (taskwright → guardkit)
4. Update any DNS/domain references

**Phase 2: Core Identity (Implementation Tasks)**
1. Update marker files and detection logic
2. Rename CLI command (`taskwright` → `guardkit`)
3. Update installer scripts

**Phase 3: Documentation**
1. Update CLAUDE.md files
2. Update README.md
3. Update all docs/*.md files

**Phase 4: Code & Templates**
1. Update Python code references
2. Update template references
3. Update agent references

**Phase 5: Validation**
1. Run full test suite
2. Test fresh installation
3. Verify all commands work

## Decision Points

### Q1: Organisation Rename Strategy

**Option A**: Rename existing organisation
- Pros: Clean transition, no duplicate
- Cons: May break existing forks/links

**Option B**: Create new organisation, archive old
- Pros: Preserves old links, gradual migration
- Cons: Maintenance of two orgs

**Recommendation**: Option A (clean rename) with proper redirects

### Q2: CLI Command Name

**Option A**: `guardkit` (matches new name)
**Option B**: `gkit` (shorter, easier to type)
**Option C**: Keep `taskwright` temporarily for backward compatibility

**Recommendation**: Option A with alias support for transition period

### Q3: Marker File Strategy

Current: `~/.agentecflow/taskwright.marker.json`
New: `~/.agentecflow/guardkit.marker.json`

**Question**: Should we detect and migrate old marker files?

**Recommendation**: Yes, with one-time migration on first run

## Acceptance Criteria

- [ ] Complete inventory of all "taskwright" references
- [ ] Documented order of operations
- [ ] Risk assessment for each change type
- [ ] Implementation tasks created and prioritized
- [ ] Rollback strategy defined
- [ ] Communication plan for users

## Implementation Tasks to Create

After review, create these implementation tasks:

1. **TASK-IMP-RENAME-INFRA**: Update installer and marker files
2. **TASK-IMP-RENAME-CLI**: Rename CLI command to guardkit
3. **TASK-IMP-RENAME-DOCS**: Update all documentation
4. **TASK-IMP-RENAME-CODE**: Update Python code references
5. **TASK-IMP-RENAME-TEMPLATES**: Update template references
6. **TASK-IMP-RENAME-VALIDATE**: Full validation and testing

## Notes

- The `.agentecflow` directory name can remain unchanged (it's the ecosystem name, not product name)
- Version should bump to v1.0.0 to mark the rename
- Consider creating a migration guide for existing users
