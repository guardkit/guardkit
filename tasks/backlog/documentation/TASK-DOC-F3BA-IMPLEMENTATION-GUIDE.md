# Documentation Update Implementation Guide

**Created**: 2025-11-27
**Source**: TASK-DOC-F3BA Review Report
**Total Tasks**: 5 high-priority documentation updates
**Status**: ✅ **ALL TASKS COMPLETED** (2025-11-27)
**Actual Total Effort**: 9-12 hours (within estimate)
**Actual Duration**: 1 day (parallel execution in Conductor worktrees)

---

## ✅ IMPLEMENTATION COMPLETE

**All 5 tasks completed successfully on 2025-11-27**

### Final Task Status

| Task ID | Title | Status | Commit | Worktree Branch |
|---------|-------|--------|--------|-----------------|
| **TASK-DOC-0801** | Update CLAUDE.md | ✅ **COMPLETED** | [8a979de6](commit://8a979de6) | RichWoollcott/doc-claude-md-cmds |
| **TASK-DOC-443B** | Review task detection | ✅ **COMPLETED** | [7a92d13](commit://7a92d13) | RichWoollcott/doc-review-detection |
| **TASK-DOC-9FFC** | Agent-format relationship | ✅ **COMPLETED** | [8b060176](commit://8b060176) | RichWoollcott/agent-format-docs |
| **TASK-DOC-EDB0** | Task-work integration | ✅ **COMPLETED** | [3b0f2a2a](commit://3b0f2a2a) | RichWoollcott/task-work-integration |
| **TASK-DOC-83F0** | Create missing guides | ✅ **COMPLETED** | [98d7aaa7](commit://98d7aaa7) | RichWoollcott/doc-missing-guides |

**Completion Rate**: 5/5 (100%)
**Lines Added**: 521 lines of documentation
**Files Modified**: 7 files
**New Files Created**: 2 comprehensive guides

---

## Executive Summary

**Total Tasks**: 5 documentation tasks (all completed)
**Critical Path**: None - all tasks were independent
**Parallelization**: 100% achieved using Conductor worktrees
**Execution**: 2-wave parallel execution as planned

### Task Completion Statistics

| Wave | Tasks Completed | Lines Added | Duration | Method |
|------|----------------|-------------|----------|--------|
| **Wave 1** | 2 (TASK-DOC-0801, TASK-DOC-443B) | 107 lines | 3-4 hours | Claude Code Direct |
| **Wave 2** | 3 (TASK-DOC-9FFC, TASK-DOC-EDB0, TASK-DOC-83F0) | 414 lines | 6-8 hours | Claude Code Direct |

**Note**: Task completions were committed in worktrees but `/task-complete` was not run until 2025-11-27T08:10-08:15, discovered during TASK-DEBUG-A21C investigation.

---

## Success Summary

### Deliverables Completed

**Wave 1 Deliverables** ✅:
- ✅ CLAUDE.md updated with 3 new commands (Agent & Template Management section)
- ✅ task-review.md updated with "Automatic Review Task Detection" section (99 lines)
- ✅ Cross-references added to task-create.md (4 lines)

**Wave 2 Deliverables** ✅:
- ✅ agent-enhance.md updated with "Relationship with /agent-format" section (101 lines)
- ✅ task-review.md updated with "Integration with /task-work" section (157 lines)
- ✅ Created docs/guides/agent-enhancement-decision-guide.md (new file, comprehensive guide)
- ✅ Created docs/workflows/incremental-enhancement-workflow.md (new file, comprehensive workflow)
- ✅ Cross-references updated in template-create.md and agent-enhance.md

### Key Achievements

1. **Documentation Coverage**: All identified gaps from TASK-DOC-F3BA review addressed
2. **Parallel Execution**: Successfully used 5 Conductor worktrees in parallel
3. **Zero Merge Conflicts**: Despite 2 tasks modifying task-review.md (different sections)
4. **Consistent Quality**: All documentation follows existing formatting standards
5. **Comprehensive Guides**: 2 new guide files providing end-to-end workflows
6. **Complete Traceability**: All commits linked to task IDs

### Impact

- **User Experience**: Clearer command relationships and workflow guidance
- **Discoverability**: New cross-references improve navigation
- **Completeness**: Filled critical documentation gaps identified in review
- **Maintainability**: Consistent formatting enables easier future updates

---

## Lessons Learned from TASK-DEBUG-A21C Investigation

This implementation guide perfectly demonstrates the finding from TASK-DEBUG-A21C investigation:

**Original Issue Report**: "/task-complete not moving files in Conductor workspaces"

**Actual Finding**: All 5 tasks were **successfully implemented** in Conductor worktrees and **properly merged** to main. However, `/task-complete TASK-XXX` was not run on 4 of the 5 task files (TASK-DOC-443B, TASK-DOC-9FFC, TASK-DOC-EDB0, TASK-DOC-83F0) until discovered during the investigation.

**Root Cause**: Human workflow step missed - implementation commits were made, but task management step (marking task as complete) was overlooked.

**Lesson**: When working in Conductor worktrees:
1. ✅ Implement the feature/documentation
2. ✅ Commit changes with proper message
3. ✅ Merge worktree to main
4. ⚠️ **Don't forget**: `/task-complete TASK-XXX` to move task file to completed/

**Result**: Investigation validated that Conductor + `/task-complete` work perfectly together. The "issue" was a workflow oversight, not a technical problem.

---

## Original Implementation Strategy (Historical Reference)

### 🌊 Wave 1: Quick Wins (Parallel - 3-4 hours)

**Strategy**: High-impact, low-effort updates
**Parallelization**: Run both tasks simultaneously using Conductor
**Dependencies**: None
**Method**: **Claude Code Direct** (both tasks)

#### Worktree 1: Update CLAUDE.md
**Task**: [TASK-DOC-0801](TASK-DOC-0801-update-claude-md-missing-commands.md)
**Method**: **Claude Code Direct**
**Complexity**: 2/10 (Simple)
**Duration**: 1-2 hours
**Output**: CLAUDE.md with 3 new commands added

**Why Claude Code Direct**:
- Simple content addition (3 commands to Essential Commands section)
- No code changes, no testing required
- Clear structure to follow (existing command format)
- Can validate with manual review (no build needed)

**Prompt**:
```
Update CLAUDE.md Essential Commands section to add three missing commands:

1. Add new section "Agent & Template Management" after "Review Workflow"
2. Add these commands:
   - /agent-format <template>/<agent> - Format agent to template standards
   - /agent-validate <agent-file> - Validate agent quality
   - /template-validate <template-path> - Comprehensive template audit
3. Add cross-references to command markdown files
4. Follow existing command format (syntax, description, cross-reference)

Reference: installer/global/commands/agent-format.md (if exists)
Reference: installer/global/commands/agent-validate.md (if exists)
Reference: installer/global/commands/template-validate.md (if exists)

Requirements from TASK-DOC-0801:
- Consistent formatting with existing commands
- One-line descriptions
- Cross-references to command specs
- No broken links
```

#### Worktree 2: Document Review Task Detection
**Task**: [TASK-DOC-443B](TASK-DOC-443B-review-task-detection.md)
**Method**: **Claude Code Direct**
**Complexity**: 2/10 (Simple)
**Duration**: 1-2 hours
**Output**: task-review.md with detection section

**Why Claude Code Direct**:
- Documentation update (no code changes)
- Clear content outline provided in task
- Can validate with manual review
- No testing or build required

**Prompt**:
```
Add "Automatic Review Task Detection" section to installer/global/commands/task-review.md.

Location: After "Overview" section, before "Examples" section

Content to add (from TASK-DOC-443B):
1. Detection criteria (4 triggers: task_type, decision_required, tags, keywords)
2. Suggestion behavior with example output
3. Detection examples (5 scenarios)
4. Why detection helps (4 benefits)
5. Overriding detection explanation

Requirements:
- Follow existing section formatting in task-review.md
- Add cross-references to task-create.md
- Include code blocks for examples
- Use consistent emoji/formatting style
```

---

### 🌊 Wave 2: Comprehensive Updates (Parallel - 6-10 hours)

**Strategy**: Larger documentation updates and new file creation
**Parallelization**: Run all 3 tasks simultaneously using Conductor
**Dependencies**: None (all tasks independent)
**Method**: **Claude Code Direct** (all tasks)

#### Worktree 1: Agent Enhancement Relationship
**Task**: [TASK-DOC-9FFC](TASK-DOC-9FFC-agent-format-relationship.md)
**Method**: **Claude Code Direct**
**Complexity**: 3/10 (Medium)
**Duration**: 2-3 hours
**Output**: agent-enhance.md with new "Relationship with /agent-format" section

**Why Claude Code Direct**:
- Documentation update with clear content outline
- Decision matrix and comparison tables (straightforward)
- No code changes, no testing
- Can validate with manual review

**Prompt**:
```
Add "Relationship with /agent-format" section to installer/global/commands/agent-enhance.md.

Location: After "Enhancement Strategies" section

Content to add (from TASK-DOC-9FFC):
1. Two-tier enhancement system explanation
   - Template-level (agent-format): 6/10 quality, instant
   - Project-level (agent-enhance): 9/10 quality, 2-5 min
2. Decision matrix table (when to use each)
3. Workflow integration code example
4. Quality comparison section

Requirements:
- Follow existing section formatting in agent-enhance.md
- Add cross-references to template-create.md Phase 5.5
- Include decision matrix table (markdown format)
- Use consistent formatting with rest of document
- Add code examples for both commands
```

#### Worktree 2: Task-Work Integration
**Task**: [TASK-DOC-EDB0](TASK-DOC-EDB0-task-work-integration.md)
**Method**: **Claude Code Direct**
**Complexity**: 3/10 (Medium)
**Duration**: 2-3 hours
**Output**: task-review.md with comprehensive integration section

**Why Claude Code Direct**:
- Documentation update with detailed content outline provided
- Workflow examples clearly specified in task
- No code changes, no testing
- Can validate with manual review

**Prompt**:
```
Add "Integration with /task-work" section to installer/global/commands/task-review.md.

Location: After "Review Modes (Detailed)" section, before "Task States and Transitions"

Content to add (from TASK-DOC-EDB0 - complete outline provided):
1. Review → Implementation workflow (6 steps)
2. Task state flow diagram
3. Real-world example: Security audit workflow
4. Benefits of integration (5 points)
5. See Also cross-references

Requirements:
- Follow existing section formatting in task-review.md
- Include complete code examples (realistic task IDs)
- Add task state flow diagram (text format acceptable)
- Cross-reference to CLAUDE.md Review Workflow
- Use consistent formatting with rest of document
```

#### Worktree 3: Create Missing Guide Documents
**Task**: [TASK-DOC-83F0](TASK-DOC-83F0-create-missing-guides.md)
**Method**: **Claude Code Direct**
**Complexity**: 4/10 (Medium)
**Duration**: 3-4 hours
**Output**: 2 new guide files + cross-reference updates

**Why Claude Code Direct**:
- New file creation (documentation only)
- Complete content outlines provided in task
- No code changes, no testing
- Can validate with manual review and link checking

**Prompt**:
```
Create two new guide documents and update cross-references.

Files to create:
1. docs/guides/agent-enhancement-decision-guide.md
2. docs/workflows/incremental-enhancement-workflow.md

Content outlines provided in TASK-DOC-83F0 (complete markdown structure).

After creating files, update cross-references in:
- installer/global/commands/template-create.md
- installer/global/commands/agent-enhance.md

Requirements:
- Follow existing guide formatting in docs/guides/ and docs/workflows/
- Include all sections from content outlines in TASK-DOC-83F0
- Add cross-references to related command docs
- Ensure no broken links
- Use consistent markdown formatting
```

---

## Implementation Decision Matrix

| Task ID | Task Name | Method | Complexity | Duration | Dependencies | Wave |
|---------|-----------|--------|------------|----------|--------------|------|
| **TASK-DOC-0801** | Update CLAUDE.md | **Claude Code Direct** | 2/10 | 1-2h | None | Wave 1 |
| **TASK-DOC-443B** | Review task detection | **Claude Code Direct** | 2/10 | 1-2h | None | Wave 1 |
| **TASK-DOC-9FFC** | Agent-format relationship | **Claude Code Direct** | 3/10 | 2-3h | None | Wave 2 |
| **TASK-DOC-EDB0** | Task-work integration | **Claude Code Direct** | 3/10 | 2-3h | None | Wave 2 |
| **TASK-DOC-83F0** | Create missing guides | **Claude Code Direct** | 4/10 | 3-4h | None | Wave 2 |

---

## Why Claude Code Direct (NOT /task-work)?

### All 5 Tasks Use Claude Code Direct Because:

1. **Pure Documentation Updates**:
   - No code changes (only markdown files)
   - No compilation required
   - No test execution needed
   - No quality gates beneficial

2. **Clear Content Outlines**:
   - All tasks have complete content structures provided
   - Decision matrices, tables, and examples specified
   - No ambiguity about what to write

3. **Manual Validation Sufficient**:
   - Can verify with `mkdocs serve` (optional)
   - Visual review of markdown is adequate
   - No automated testing infrastructure needed

4. **Fast Iteration**:
   - Direct editing much faster than full /task-work workflow
   - Can preview changes immediately
   - No overhead of planning, architectural review, etc.

### When Would We Use /task-work?

**Use /task-work when**:
- Multi-file code changes requiring validation
- Testing infrastructure needs to be run
- Quality gates would catch issues (build, lint, test)
- Complex refactoring across multiple files
- Architectural review would add value

**None of these apply to pure documentation tasks.**

---

## Conductor.build Parallel Development Strategy

### Wave 1: Parallel Execution

```bash
# Create worktrees for Wave 1 tasks
conductor create-worktree docs-claude-md main
conductor create-worktree docs-review-detection main

# Terminal 1: Update CLAUDE.md
cd docs-claude-md
# [Work on TASK-DOC-0801]

# Terminal 2: Document review task detection
cd docs-review-detection
# [Work on TASK-DOC-443B]
```

**Duration**: 3-4 hours (run simultaneously)

**Merge After Completion**:
```bash
# From main branch
git checkout main
git merge docs-claude-md
git merge docs-review-detection

# Delete worktrees
conductor delete-worktree docs-claude-md
conductor delete-worktree docs-review-detection
```

### Wave 2: Parallel Execution

```bash
# Create worktrees for Wave 2 tasks
conductor create-worktree docs-agent-format main
conductor create-worktree docs-task-work main
conductor create-worktree docs-missing-guides main

# Terminal 1: Agent-format relationship
cd docs-agent-format
# [Work on TASK-DOC-9FFC]

# Terminal 2: Task-work integration
cd docs-task-work
# [Work on TASK-DOC-EDB0]

# Terminal 3: Create missing guides
cd docs-missing-guides
# [Work on TASK-DOC-83F0]
```

**Duration**: 6-10 hours (run simultaneously)

**Merge After Completion**:
```bash
# From main branch
git checkout main
git merge docs-agent-format
git merge docs-task-work
git merge docs-missing-guides

# Delete worktrees
conductor delete-worktree docs-agent-format
conductor delete-worktree docs-task-work
conductor delete-worktree docs-missing-guides
```

---

## Merge Conflict Risk Assessment

### Risk Level: **LOW** 🟢

**Why Low Risk?**

1. **Different Files per Task**:
   - TASK-DOC-0801: CLAUDE.md
   - TASK-DOC-443B: task-review.md
   - TASK-DOC-9FFC: agent-enhance.md
   - TASK-DOC-EDB0: task-review.md (different section than 443B)
   - TASK-DOC-83F0: New files (no conflicts possible)

2. **Independent Sections**:
   - Even TASK-DOC-443B and TASK-DOC-EDB0 both modify task-review.md
   - They edit **different sections** of the file
   - 443B: After "Overview", before "Examples"
   - EDB0: After "Review Modes", before "Task States"
   - **No overlap = no conflicts**

3. **No Shared Content**:
   - Each task has unique content
   - No cross-task dependencies
   - Cross-references added independently

### Conflict Mitigation Strategy

**If conflicts occur** (unlikely):

1. **Use 3-way merge**:
   ```bash
   git merge --no-ff docs-task-work
   # If conflict in task-review.md
   git mergetool
   ```

2. **Manual merge**:
   - Both sections are additions (not modifications)
   - Easy to combine: keep both changes
   - Verify section ordering correct

3. **Verification**:
   ```bash
   # After merge, validate no broken links
   mkdocs build
   # Check for broken markdown
   markdownlint docs/ installer/global/commands/
   ```

---

## Execution Workflow

### Step-by-Step Execution

#### Phase 1: Setup (5 minutes)

```bash
# Ensure on main branch
cd ~/Projects/appmilla_github/taskwright
git checkout main
git pull

# Create all worktrees at once
conductor create-worktree docs-claude-md main
conductor create-worktree docs-review-detection main
conductor create-worktree docs-agent-format main
conductor create-worktree docs-task-work main
conductor create-worktree docs-missing-guides main
```

#### Phase 2: Wave 1 Execution (3-4 hours)

**Terminal 1**:
```bash
cd docs-claude-md

# Execute TASK-DOC-0801
# [Provide prompt from Wave 1, Worktree 1]

# After completion
git add CLAUDE.md
git commit -m "docs: add missing commands to CLAUDE.md Essential Commands

- Add /agent-format, /agent-validate, /template-validate
- Add cross-references to command specs
- Follow existing command format

Related: TASK-DOC-0801"
```

**Terminal 2**:
```bash
cd docs-review-detection

# Execute TASK-DOC-443B
# [Provide prompt from Wave 1, Worktree 2]

# After completion
git add installer/global/commands/task-review.md
git commit -m "docs: add review task detection section to task-review.md

- Document detection criteria (4 triggers)
- Add suggestion behavior examples
- Include override instructions
- Cross-reference to task-create.md

Related: TASK-DOC-443B"
```

**Merge Wave 1**:
```bash
# Switch to main
cd ~/Projects/appmilla_github/taskwright
git checkout main

# Merge both worktrees
git merge docs-claude-md
git merge docs-review-detection

# Push to remote
git push

# Delete worktrees
conductor delete-worktree docs-claude-md
conductor delete-worktree docs-review-detection
```

#### Phase 3: Wave 2 Execution (6-10 hours)

**Terminal 1**:
```bash
cd docs-agent-format

# Execute TASK-DOC-9FFC
# [Provide prompt from Wave 2, Worktree 1]

# After completion
git add installer/global/commands/agent-enhance.md
git commit -m "docs: add relationship with agent-format to agent-enhance.md

- Explain two-tier enhancement system
- Add decision matrix for command selection
- Include workflow integration examples
- Document quality comparison (6/10 vs 9/10)

Related: TASK-DOC-9FFC"
```

**Terminal 2**:
```bash
cd docs-task-work

# Execute TASK-DOC-EDB0
# [Provide prompt from Wave 2, Worktree 2]

# After completion
git add installer/global/commands/task-review.md
git commit -m "docs: add task-work integration section to task-review.md

- Document review → implementation workflow (6 steps)
- Add task state flow diagram
- Include real-world security audit example
- Add benefits and cross-references

Related: TASK-DOC-EDB0"
```

**Terminal 3**:
```bash
cd docs-missing-guides

# Execute TASK-DOC-83F0
# [Provide prompt from Wave 2, Worktree 3]

# After completion
git add docs/guides/agent-enhancement-decision-guide.md
git add docs/workflows/incremental-enhancement-workflow.md
git add installer/global/commands/template-create.md
git add installer/global/commands/agent-enhance.md
git commit -m "docs: create missing guide documents

- Add agent-enhancement-decision-guide.md
- Add incremental-enhancement-workflow.md
- Update cross-references in command docs
- Fix broken links

Related: TASK-DOC-83F0"
```

**Merge Wave 2**:
```bash
# Switch to main
cd ~/Projects/appmilla_github/taskwright
git checkout main

# Merge all three worktrees
git merge docs-agent-format
git merge docs-task-work
git merge docs-missing-guides

# Push to remote
git push

# Delete worktrees
conductor delete-worktree docs-agent-format
conductor delete-worktree docs-task-work
conductor delete-worktree docs-missing-guides
```

---

## Success Criteria

### Wave 1 Complete ✅ when:
- [ ] CLAUDE.md has 3 new commands in Essential Commands section
- [ ] task-review.md has "Automatic Review Task Detection" section
- [ ] Both worktrees merged to main
- [ ] No broken links introduced
- [ ] Consistent formatting maintained

### Wave 2 Complete ✅ when:
- [ ] agent-enhance.md has "Relationship with /agent-format" section
- [ ] task-review.md has "Integration with /task-work" section
- [ ] Two new guide files created and properly formatted
- [ ] Cross-references updated in command docs
- [ ] All three worktrees merged to main
- [ ] No broken links introduced

### Final Validation

After all waves complete:

```bash
# Check for broken links
grep -r "\[.*\](.*\.md)" docs/ installer/global/commands/ | \
  while read line; do
    # Extract link and verify file exists
    # [Manual validation or use link checker]
  done

# Validate markdown formatting
markdownlint docs/ installer/global/commands/ CLAUDE.md

# Optional: Build docs to verify no issues
cd ~/Projects/appmilla_github/taskwright
mkdocs build

# If MkDocs config exists
mkdocs serve
# Open http://127.0.0.1:8000 and verify navigation
```

---

## Risk Mitigation

### Risk 1: Merge Conflicts in task-review.md
**Risk**: TASK-DOC-443B and TASK-DOC-EDB0 both modify task-review.md
**Likelihood**: Low (different sections)
**Mitigation**:
- Sections are well-separated (Overview vs Review Modes)
- Both are additions, not modifications
- If conflict: accept both changes, verify section order

### Risk 2: Broken Cross-References
**Risk**: New guides reference files that don't exist yet
**Likelihood**: Medium
**Mitigation**:
- Create all files in TASK-DOC-83F0 first
- Validate all links after merge
- Use relative paths for cross-references
- Test with `mkdocs build` if config exists

### Risk 3: Inconsistent Formatting
**Risk**: Different worktrees use different markdown styles
**Likelihood**: Low
**Mitigation**:
- All tasks reference existing section formatting
- Run `markdownlint` after completion
- Manual review of formatting consistency
- Use existing documents as templates

---

## Estimated Timeline

### Optimistic (Parallel Development)
- **Wave 1**: 3-4 hours (run simultaneously)
- **Wave 2**: 6-10 hours (run simultaneously)
- **Total**: 9-14 hours over 1-2 days

### Conservative (Sequential Development)
- **TASK-DOC-0801**: 1-2 hours
- **TASK-DOC-443B**: 1-2 hours
- **TASK-DOC-9FFC**: 2-3 hours
- **TASK-DOC-EDB0**: 2-3 hours
- **TASK-DOC-83F0**: 3-4 hours
- **Total**: 9-14 hours over 2-3 days

### Recommended: Wave-Based Parallel
- **Wave 1** (Quick Wins): 3-4 hours
- **Wave 2** (Comprehensive): 6-10 hours
- **Total**: 9-14 hours over 1-2 days

**Speedup Factor**: 1-2x faster than sequential

---

## Appendix: Task File Locations

All tasks located in: `tasks/backlog/documentation/`

- [TASK-DOC-0801-update-claude-md-missing-commands.md](TASK-DOC-0801-update-claude-md-missing-commands.md)
- [TASK-DOC-443B-review-task-detection.md](TASK-DOC-443B-review-task-detection.md)
- [TASK-DOC-9FFC-agent-format-relationship.md](TASK-DOC-9FFC-agent-format-relationship.md)
- [TASK-DOC-EDB0-task-work-integration.md](TASK-DOC-EDB0-task-work-integration.md)
- [TASK-DOC-83F0-create-missing-guides.md](TASK-DOC-83F0-create-missing-guides.md)

Review report: `.claude/task-plans/TASK-DOC-F3BA-review-report.md`

---

## Quick Reference: Claude Code Prompts

### Wave 1, Worktree 1 (TASK-DOC-0801)
```
Update CLAUDE.md Essential Commands section to add three missing commands:

1. Add new section "Agent & Template Management" after "Review Workflow"
2. Add these commands:
   - /agent-format <template>/<agent> - Format agent to template standards
   - /agent-validate <agent-file> - Validate agent quality
   - /template-validate <template-path> - Comprehensive template audit
3. Add cross-references to command markdown files
4. Follow existing command format

Requirements from TASK-DOC-0801:
- Consistent formatting with existing commands
- One-line descriptions
- Cross-references to command specs
- No broken links
```

### Wave 1, Worktree 2 (TASK-DOC-443B)
```
Add "Automatic Review Task Detection" section to installer/global/commands/task-review.md.

Location: After "Overview", before "Examples"

Include:
1. Detection criteria (4 triggers)
2. Suggestion behavior with example
3. Detection examples (5 scenarios)
4. Why detection helps
5. Overriding detection

Follow existing section formatting in task-review.md.
Reference: TASK-DOC-443B for complete content outline.
```

### Wave 2, Worktree 1 (TASK-DOC-9FFC)
```
Add "Relationship with /agent-format" section to installer/global/commands/agent-enhance.md.

Location: After "Enhancement Strategies"

Include:
1. Two-tier enhancement system
2. Decision matrix table
3. Workflow integration
4. Quality comparison

Follow existing section formatting.
Reference: TASK-DOC-9FFC for complete content outline.
```

### Wave 2, Worktree 2 (TASK-DOC-EDB0)
```
Add "Integration with /task-work" section to installer/global/commands/task-review.md.

Location: After "Review Modes", before "Task States"

Include:
1. Review → Implementation workflow (6 steps)
2. Task state flow
3. Real-world security example
4. Benefits

Follow existing section formatting.
Reference: TASK-DOC-EDB0 for complete content outline.
```

### Wave 2, Worktree 3 (TASK-DOC-83F0)
```
Create two new guide documents:

1. docs/guides/agent-enhancement-decision-guide.md
2. docs/workflows/incremental-enhancement-workflow.md

Then update cross-references in:
- installer/global/commands/template-create.md
- installer/global/commands/agent-enhance.md

Reference: TASK-DOC-83F0 for complete content outlines.
Follow existing guide formatting in docs/guides/ and docs/workflows/.
```

---

**End of Implementation Guide**
