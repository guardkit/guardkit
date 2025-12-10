# Implementation Plan: TASK-037 - Remove BDD Mode from Taskwright

**Task ID**: TASK-037
**Complexity**: 2/10 (Simple cleanup/documentation task)
**Stack**: default
**Estimated Duration**: 2-3 hours
**Estimated LOC**: ~50 lines removed, ~200 lines modified
**Documentation Level**: minimal

## Overview

Remove BDD mode functionality from taskwright while preserving the supports_bdd() function in shared code for backward compatibility with require-kit package.

## Architecture Decisions

### AD-1: Preserve supports_bdd() Function
**Decision**: Keep the supports_bdd() function in shared code
**Rationale**: The function is part of the feature detection interface used by require-kit (separate package). Removing it would break external integrations.
**Impact**: Minimal - function will return False but remain callable

### AD-2: Remove BDD Mode from task-work
**Decision**: Remove all BDD mode references from task-work command
**Rationale**: BDD mode is not being used in taskwright and adds unnecessary complexity
**Impact**: Users can no longer specify --mode=bdd flag

### AD-3: Maintain Clear Migration Path
**Decision**: Add migration notes to CHANGELOG.md explaining removal
**Rationale**: Users need to understand why BDD mode was removed and what alternatives exist
**Impact**: Clear communication, no breaking changes for active users (BDD mode not in use)

## Implementation Phases

### Phase 1: Delete BDD Agent Files (10 minutes)
**Objective**: Remove BDD-specific agent and instruction files

**Files to Delete**:
- `installer/core/agents/bdd-generator.md` (if exists)
- `installer/core/instructions/bdd-workflow.md` (if exists)

**Steps**:
1. Verify files exist before deletion
2. Delete agent file
3. Delete instruction file
4. Confirm no other files reference these agents

**Success Criteria**:
- BDD agent files no longer exist
- No broken references remain

### Phase 2: Update task-work Command Documentation (45 minutes)
**Objective**: Remove BDD mode references from command specification

**Files to Modify**:
1. `installer/core/commands/task-work.md`
   - Remove BDD mode section (~lines 2336-2344)
   - Update development modes table
   - Remove BDD examples from usage section
   - Update mode flag description

**Changes**:
- Remove "#### BDD Mode" section
- Update mode flag to only show: `--mode=standard|tdd`
- Remove BDD mode from agent selection table
- Update examples to remove BDD references

**Success Criteria**:
- No BDD mode references in task-work.md
- Documentation clearly shows only standard and TDD modes
- All examples valid for remaining modes

### Phase 3: Update Main Documentation (45 minutes)
**Objective**: Remove BDD references from project-level documentation

**Files to Modify**:
1. `CLAUDE.md` (root level)
   - Update command syntax: `/task-work TASK-XXX [--mode=standard|tdd]`
   - Remove BDD workflow references
   - Update feature list

2. `.claude/CLAUDE.md` (local config)
   - Update workflow description
   - Remove BDD test specification references

3. `.claude/settings.json`
   - Update testing specification from "BDD/Gherkin" to "automated"
   - Preserve JSON structure

**Changes**:
- Remove all BDD/Gherkin references
- Update mode flags to exclude BDD
- Simplify testing approach description

**Success Criteria**:
- No BDD references in documentation
- Settings.json valid JSON
- Documentation accurate for current features

### Phase 4: Add Migration Notes (20 minutes)
**Objective**: Document BDD mode removal for users

**Files to Modify**:
1. `CHANGELOG.md`
   - Add entry under "Removed" section
   - Explain rationale
   - Provide migration path

**Content**:
```markdown
### Removed
- **BDD Mode**: Removed `--mode=bdd` flag from `/task-work` command
  - Rationale: BDD mode was not actively used and added unnecessary complexity
  - Migration: Use `--mode=tdd` for test-driven development or `--mode=standard` for standard workflow
  - Note: `supports_bdd()` function preserved in shared code for backward compatibility with require-kit package
```

**Success Criteria**:
- CHANGELOG.md updated with clear migration notes
- Users understand why BDD mode removed
- Alternative approaches documented

### Phase 5: Verification (30 minutes)
**Objective**: Ensure no broken references or missing documentation

**Verification Steps**:
1. Search for remaining "bdd" references (case-insensitive)
2. Verify supports_bdd() function still exists in shared code
3. Check all documentation files render correctly
4. Verify no broken links or references

**Success Criteria**:
- No unexpected BDD references remain
- supports_bdd() function intact
- All documentation valid

## Files to Modify

### High Priority (Must Change)
1. `installer/core/commands/task-work.md` - Remove BDD mode documentation
2. `CLAUDE.md` - Update command syntax and features
3. `.claude/CLAUDE.md` - Update workflow description
4. `CHANGELOG.md` - Add migration notes

### Medium Priority (Update References)
1. `.claude/settings.json` - Update testing specification

### Low Priority (Verification Only)
1. Shared code files - Verify supports_bdd() not removed

## Files to Delete
1. `installer/core/agents/bdd-generator.md` (if exists)
2. `installer/core/instructions/bdd-workflow.md` (if exists)

## External Dependencies
None - This is a pure documentation and cleanup task

## Risk Assessment

### Low Risk Items
- Documentation updates (easily reversible)
- File deletions (backed up in git history)
- CHANGELOG.md updates (informational only)

### Mitigation Strategies
- Commit each phase separately for easy rollback
- Verify no active users relying on BDD mode
- Preserve supports_bdd() function for external compatibility
- Provide clear migration path in documentation

## Testing Strategy

### Verification Tests
1. **Documentation Integrity**
   - Read all modified markdown files
   - Verify no broken links
   - Check all code examples valid

2. **Search Verification**
   - Search for "bdd" (case-insensitive)
   - Confirm only expected references remain (supports_bdd function)
   - Verify no orphaned references

3. **Settings Validation**
   - Parse .claude/settings.json
   - Verify valid JSON structure
   - Confirm no BDD-specific settings remain

### Manual Review Checklist
- [ ] BDD mode removed from task-work.md
- [ ] Command syntax updated in CLAUDE.md files
- [ ] Migration notes added to CHANGELOG.md
- [ ] Settings.json updated and valid
- [ ] supports_bdd() function still exists
- [ ] No broken documentation links

## Success Criteria

### Functional Requirements
- [x] FR-1: BDD mode removed from task-work command documentation
- [x] FR-2: bdd-generator agent file deleted (if exists)
- [x] FR-3: BDD instruction files deleted (if exists)
- [x] FR-4: Documentation updated to reflect removal
- [x] FR-5: Migration notes added to CHANGELOG.md

### Quality Gates
- No compilation errors (N/A for documentation task)
- All markdown files render correctly
- No broken links or references
- Settings.json parses as valid JSON
- supports_bdd() function preserved

## Implementation Notes

### Key Considerations
1. **Backward Compatibility**: Must preserve supports_bdd() function for require-kit
2. **Documentation Accuracy**: All examples must work with remaining modes (standard, tdd)
3. **Migration Path**: Users need clear guidance on alternatives to BDD mode

### Potential Challenges
1. **Finding All References**: BDD may be referenced in multiple places
   - Solution: Comprehensive search before and after changes

2. **Preserving supports_bdd()**: Must not accidentally delete function
   - Solution: Explicitly verify function exists after changes

3. **Documentation Consistency**: Multiple CLAUDE.md files must stay in sync
   - Solution: Update all documentation files in single phase

## Rollback Plan

If issues discovered:
1. Git revert to commit before changes
2. Review what went wrong
3. Address issues in new commit

All changes tracked in git for easy rollback.

## Post-Implementation

### Verification Steps
1. Run global search for "bdd" references
2. Verify documentation renders correctly
3. Check that supports_bdd() function still exists
4. Validate settings.json parses correctly

### Success Metrics
- Zero broken documentation links
- Zero references to BDD mode in commands
- supports_bdd() function still callable
- Clear migration path documented

## Time Breakdown

| Phase | Duration | Description |
|-------|----------|-------------|
| Phase 1 | 10 min | Delete BDD agent files |
| Phase 2 | 45 min | Update task-work.md |
| Phase 3 | 45 min | Update main documentation |
| Phase 4 | 20 min | Add migration notes |
| Phase 5 | 30 min | Verification |
| **Total** | **2.5 hours** | **Complete cleanup** |

## Architectural Review Notes

### SOLID Principles: N/A
- Documentation task, not applicable

### DRY Principle: ✅ Good
- Removing unused code reduces duplication
- Simplifies documentation maintenance

### YAGNI Principle: ✅ Excellent
- Removing unused feature aligns perfectly with YAGNI
- Reduces cognitive load for users and maintainers

### Overall Assessment
This is a straightforward cleanup task that improves codebase maintainability by removing unused features while preserving backward compatibility.
