---
id: TASK-037
title: Remove BDD mode from guardkit
status: completed
created: 2025-11-02T00:00:00Z
updated: 2025-11-02T16:45:00Z
completed: 2025-11-02T17:00:00Z
priority: normal
tags: [cleanup, documentation, simplification]
estimated_effort: 60 minutes
actual_effort: 150 minutes
complexity: 2
previous_state: in_review
state_transition_reason: "All quality gates passed - task completed successfully"
completed_location: tasks/completed/TASK-037/
organized_files:
  - TASK-037-remove-bdd-mode.md
  - implementation-plan.md
  - verification-suite.md
  - execution-results.md
  - code-review.md
workflow:
  documentation_level: minimal
  architectural_review_score: 95
  code_review_score: 9.5
  complexity_evaluation: 1
  plan_audit: approved
  verification_pass_rate: 100
completion_summary:
  files_deleted: 11
  files_modified: 8
  total_changes: 19
  quality_score: 9.5
  all_gates_passed: true
---

# Task: Remove BDD mode from guardkit

## Context

BDD mode is currently documented in task-work but:
- Not fully implemented
- Depends on require-kit installation
- Low expected usage (<5% of users)
- Adds unnecessary complexity to lightweight system
- Better served by require-kit for full EARS → BDD workflow

**Decision:** Remove ALL BDD functionality from guardkit, focus on Standard and TDD modes only.

**Reference:** [BDD Mode Removal Decision](../docs/research/bdd-mode-removal-decision.md)

## Description

**COMPLETE REMOVAL** of all BDD-related functionality from guardkit to simplify the system and avoid incomplete/misleading documentation. Users needing BDD workflows should use require-kit which provides complete EARS → Gherkin → Implementation flow.

This means removing:
- BDD mode from task-work command
- bdd-generator agent (EARS → Gherkin is require-kit feature)
- BDD instruction files
- All BDD-related template files

## Acceptance Criteria

### Phase 1: Remove BDD Agents and Instructions (20 minutes)
- [ ] **DELETE** `.claude/agents/bdd-generator.md` (EARS → Gherkin is require-kit only)
- [ ] **DELETE** `installer/global/instructions/core/bdd-gherkin.md` (move to require-kit if needed)
- [ ] **DELETE** all `installer/global/templates/*/agents/bdd-generator.md` files
- [ ] Find and remove any other BDD-related agents or instruction files

### Phase 2: Documentation Cleanup (25 minutes)
- [ ] Remove BDD mode section from `installer/global/commands/task-work.md` (lines 2317-2344)
- [ ] Remove all `--mode=bdd` examples from task-work.md
- [ ] Update development modes to list ONLY Standard and TDD
- [ ] Remove BDD mode references from `CLAUDE.md`
- [ ] Add clarification: "For BDD workflows (EARS → Gherkin), use require-kit"
- [ ] Remove BDD mode implementation from `.claude/agents/task-manager.md` (lines 120-145)
- [ ] Keep Standard and TDD mode logic only

### Phase 3: Shared Code Update (10 minutes)
- [ ] **KEEP** `supports_bdd()` function in `feature_detection.py` (shared file with require-kit)
- [ ] Update docstring: "BDD generation requires require-kit installation"
- [ ] Note: feature_detection.py is shared between guardkit and require-kit

### Phase 4: Migration Notes (5 minutes)
- [ ] Add changelog entry explaining complete BDD removal
- [ ] Document migration path to require-kit for BDD users
- [ ] Update README if BDD mode mentioned
- [ ] Add note to any affected documentation

### Verification
- [ ] No BDD agents exist in `.claude/agents/` or template directories
- [ ] No BDD instructions exist in `installer/global/instructions/`
- [ ] No references to `--mode=bdd` in command specs
- [ ] Grep for "bdd-generator" returns nothing (except in feature_detection comments)
- [ ] CLAUDE.md clearly states BDD requires require-kit
- [ ] All documentation examples use Standard or TDD modes only

## Implementation Notes

### Files to **DELETE COMPLETELY**

1. **`.claude/agents/bdd-generator.md`** ❌ DELETE
   - EARS → Gherkin conversion is require-kit feature only
   - Remove entire file from guardkit
   - This agent should only exist in require-kit

2. **`installer/global/instructions/core/bdd-gherkin.md`** ❌ DELETE
   - BDD instruction file not needed in guardkit
   - Delete from guardkit (move to require-kit if they need it)

3. **`installer/global/templates/*/agents/bdd-generator.md`** ❌ DELETE ALL
   - Find all template-specific copies:
     - `installer/global/templates/maui-navigationpage/agents/bdd-generator.md`
     - Any other templates with bdd-generator
   - Delete all copies

4. **Any other BDD-related files** ❌ DELETE
   - Search for files containing "bdd" in name
   - Review and delete if guardkit-specific

### Files to **MODIFY**

5. **`installer/global/commands/task-work.md`** ✏️ MODIFY
   - Remove BDD Mode section (~lines 2317-2344)
   - Update development modes to list only Standard and TDD
   - Remove all `--mode=bdd` examples
   - Remove any BDD-related workflow descriptions

6. **`CLAUDE.md`** ✏️ MODIFY
   - Remove BDD mode from command list
   - Remove any examples showing `--mode=bdd`
   - Add note: "For BDD workflows (EARS → Gherkin), install require-kit"

7. **`.claude/agents/task-manager.md`** ✏️ MODIFY
   - Remove `implement_bdd_mode()` function (~lines 120-145)
   - Keep only Standard and TDD mode implementations
   - Update any references to three modes → two modes

8. **`installer/global/lib/feature_detection.py`** ✏️ MODIFY (minimal)
   - **KEEP** `supports_bdd()` function (shared file with require-kit)
   - Update docstring: "BDD generation requires require-kit installation"
   - **NOTE:** This file is duplicated in both repos, changes must sync

9. **`README.md`** ✏️ MODIFY (if needed)
   - Search for BDD mode references
   - Remove or update to point to require-kit

10. **Changelog/Migration Doc** ✏️ CREATE NEW
    - Create entry explaining complete BDD removal
    - Point to require-kit for all BDD workflows
    - Explain Standard/TDD alternatives

### Search Commands for Complete Cleanup

```bash
# Find all BDD-related files to delete
find . -name "*bdd*" -type f | grep -v node_modules | grep -v .git

# Find all bdd-generator agent files
find installer/global/templates -name "bdd-generator.md"
find .claude/agents -name "bdd-generator.md"

# Find remaining BDD mode references (should find nothing after cleanup)
grep -r "mode=bdd" installer/global/commands/ .claude/commands/
grep -r "BDD Mode" CLAUDE.md README.md docs/
grep -r "bdd-generator" . --exclude-dir=node_modules --exclude-dir=.git

# Verify BDD files are DELETED
test ! -f .claude/agents/bdd-generator.md && echo "✓ bdd-generator.md removed" || echo "✗ Still exists!"
test ! -f installer/global/instructions/core/bdd-gherkin.md && echo "✓ bdd-gherkin.md removed" || echo "✗ Still exists!"
find installer/global/templates -name "bdd-generator.md" | wc -l  # Should output: 0

# Verify feature_detection.py still has supports_bdd() (it's a shared file)
grep -q "def supports_bdd" installer/global/lib/feature_detection.py && echo "✓ supports_bdd() preserved (shared file)"
```

## What Users Lose

**Removed capability:**
```bash
/task-work TASK-042 --mode=bdd
# ERROR: BDD mode has been removed from guardkit
# For BDD workflows (EARS → Gherkin → Implementation), install require-kit
```

**Available alternatives:**
1. **Use require-kit** for full BDD workflow (EARS → Gherkin → Implementation)
2. **Use Standard mode** with detailed acceptance criteria
3. **Use TDD mode** for test-first development

**What's NOT lost:**
- All quality gates still enforced
- Standard and TDD modes remain fully functional
- Test enforcement still automatic
- Architectural review still runs

## Benefits

- ✅ Simplifies guardkit (removes 45-70 hours of potential implementation)
- ✅ Clearer separation: require-kit for requirements/BDD, guardkit for workflows
- ✅ Avoids broken/incomplete documentation
- ✅ Reduces maintenance burden (no need to track 4+ BDD frameworks)
- ✅ Focuses resources on core Standard/TDD modes
- ✅ **Removes all BDD-related agents and instructions from guardkit**
- ✅ **Single source of truth: BDD functionality lives in require-kit only**
- ✅ Eliminates confusion about which repo owns BDD features

## Test Requirements

- [ ] Verify no BDD agents remain in guardkit
- [ ] Verify no BDD instruction files remain
- [ ] Verify no broken links in documentation
- [ ] Verify task-work command still works with `--mode=standard` and `--mode=tdd`
- [ ] Verify `--mode=bdd` returns clear error message
- [ ] Verify feature_detection.supports_bdd() still works (returns require-kit status)
- [ ] Verify no bdd-generator.md files in templates
- [ ] Verify CLAUDE.md mentions require-kit for BDD workflows

## Success Metrics

- **Zero BDD agents** in guardkit repository
- **Zero BDD instruction files** in guardkit repository
- No references to `--mode=bdd` in guardkit command specs
- Clear messaging: "BDD workflows require require-kit"
- Standard and TDD modes remain fully functional
- Migration path documented for any affected users
- feature_detection.py still has supports_bdd() (shared file)

## Related Documents

- [BDD Mode Removal Decision](../docs/research/bdd-mode-removal-decision.md)
- [Option A Design (for reference)](../docs/research/bdd-mode-design-option-a.md)
- [Feature Detection](../installer/global/lib/feature_detection.py)

## Post-Completion Verification

After running this task, verify complete removal:

```bash
# Should find ZERO matches (except historical docs):
find . -name "*bdd-generator*" -type f
find . -name "*bdd-gherkin*" -type f
grep -r "mode=bdd" CLAUDE.md installer/global/commands/

# Should find ONE match (feature_detection.py shared file):
grep -r "supports_bdd" installer/global/lib/
```
