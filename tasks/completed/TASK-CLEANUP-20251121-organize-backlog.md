# TASK-CLEANUP-20251121: Organize Backlog and Archive Completed Work

**Task ID**: TASK-CLEANUP-20251121
**Priority**: HIGH (P1)
**Status**: BACKLOG
**Created**: 2025-11-21
**Estimated Effort**: 2 hours
**Dependencies**: None

---

## Overview

Organize the backlog directory (currently 80 files) into logical groups, move completed work to proper locations, and archive superseded tasks. This will reduce active backlog from 80 → 42 files (47.5% reduction) and make it easier to prioritize work.

### Current Problems

1. **Flat structure**: All 80 files in one directory
2. **Completed work not moved**: 8 tasks done but still in backlog
3. **Planning docs mixed with tasks**: 18 ADRs/EPICs/reviews in wrong location
4. **Superseded tasks**: 12 old tasks from exploratory work still present
5. **Hard to prioritize**: No grouping by initiative

### Proposed Solution

**Organize into 5 active groups** + move completed/archived/planning docs:

```
tasks/backlog/
  ├── agent-enhancement/        # 7 tasks
  ├── design-url-integration/   # 12 tasks
  ├── documentation/            # 6 tasks
  ├── testing/                  # 5 tasks
  └── standalone/               # 12 tasks

tasks/completed/                # 8 moved here
tasks/archived/                 # 12 moved here
docs/                           # 18 planning docs moved here
```

---

## Acceptance Criteria

### AC1: Completed Work Moved (8 files)

- [ ] **AC1.1**: TASK-PHASE-8-INCREMENTAL-specification.md → tasks/completed/phase-8-work/
- [ ] **AC1.2**: TASK-AGENT-BRIDGE-COMPLETE.md → tasks/completed/
- [ ] **AC1.3**: PRE-IMPLEMENTATION-WORK-COMPLETE.md → tasks/completed/
- [ ] **AC1.4**: TASK-C7A9-REIMPLEMENT-agent-metadata-in-CLAUDE.md → tasks/completed/
- [ ] **AC1.5**: TASK-09E9-comprehensive-template-create-review.md → tasks/completed/
- [ ] **AC1.6**: EPIC-001-COMPREHENSIVE-REVIEW.md → tasks/completed/
- [ ] **AC1.7**: EPIC-001-REVIEW-RESOLUTION.md → tasks/completed/
- [ ] **AC1.8**: EPIC-001-SYSTEM-INTEGRATION-REVIEW.md → tasks/completed/

**Verification**:
```bash
ls tasks/completed/*.md | wc -l  # Should be 7
ls tasks/completed/phase-8-work/*.md | wc -l  # Should be 1
```

### AC2: Planning Documents Moved to docs/ (18 files)

#### ADRs (1 file)
- [ ] **AC2.1**: ADR-002-agent-discovery-strategy.md → docs/adrs/

#### Design Docs (2 files)
- [ ] **AC2.2**: AGENT-STRATEGY-high-level-design.md → docs/design/
- [ ] **AC2.3**: PARALLEL-EXECUTION-STRATEGY.md → docs/design/

#### EPICs (2 files)
- [ ] **AC2.4**: EPIC-001-AGENT-DESIGN-SUMMARY.md → docs/epics/
- [ ] **AC2.5**: EPIC-001-ai-template-creation.md → docs/epics/

#### Initiatives (1 file)
- [ ] **AC2.6**: DEMO-TESTING-INITIATIVE-OVERVIEW.md → docs/initiatives/

#### Reviews (4 files - if not in completed/)
- [ ] **AC2.7**: Reviews moved to docs/reviews/ or kept in tasks/completed/

#### Checkpoints (2 files)
- [ ] **AC2.8**: TASK-PHASE-1-CHECKPOINT.md → docs/checkpoints/
- [ ] **AC2.9**: TASK-PHASE-5-CHECKPOINT.md → docs/checkpoints/

#### Workflows (1 file)
- [ ] **AC2.10**: TEMPLATE-LIFECYCLE-complete-flow.md → docs/workflows/

**Verification**:
```bash
find docs/ -name "*.md" -type f | wc -l  # Should increase by ~14-18
```

### AC3: Superseded Tasks Archived (12 files)

#### Old Agent Discovery Approach (7 files - Nov 21 exploratory)
- [ ] **AC3.1**: TASK-AGENT-BOUND-20251121-151631.md → tasks/archived/superseded/agent-discovery-old-approach/
- [ ] **AC3.2**: TASK-AGENT-EXAMPLES-20251121-151804.md → tasks/archived/superseded/agent-discovery-old-approach/
- [ ] **AC3.3**: TASK-AGENT-GIT-20251121-152113.md → tasks/archived/superseded/agent-discovery-old-approach/
- [ ] **AC3.4**: TASK-AGENT-STRUCT-20251121-151631.md → tasks/archived/superseded/agent-discovery-old-approach/
- [ ] **AC3.5**: TASK-AGENT-STYLE-20251121-152113.md → tasks/archived/superseded/agent-discovery-old-approach/
- [ ] **AC3.6**: TASK-AGENT-VALIDATE-20251121-160001.md → tasks/archived/superseded/agent-discovery-old-approach/
- [ ] **AC3.7**: TASK-AGENT-ENHANCER-20251121-160000.md → tasks/archived/superseded/agent-discovery-old-approach/

#### Phase 7.5 Approach (1 file)
- [ ] **AC3.8**: TASK-PHASE-7-5-SIMPLE-specification.md → tasks/archived/superseded/phase-7-5-approach/

#### Future Enhancements (2-4 files)
- [ ] **AC3.9**: TASK-004-REDESIGN-ai-agent-discovery.md → tasks/archived/future-enhancements/
- [ ] **AC3.10**: TASK-004A-ai-agent-generator.md → tasks/archived/future-enhancements/ (if superseded)

**Verification**:
```bash
find tasks/archived/ -name "*.md" -type f | wc -l  # Should be ~12
```

### AC4: Active Tasks Organized into Groups (42 files)

#### Group 1: Agent Enhancement (7 files)
- [ ] **AC4.1**: Create tasks/backlog/agent-enhancement/ directory
- [ ] **AC4.2**: Move TASK-AI-2B37-ai-integration-agent-enhancement.md
- [ ] **AC4.3**: Move TASK-DOC-F3A3-documentation-suite-agent-enhancement.md
- [ ] **AC4.4**: Move TASK-E2E-97EB-end-to-end-validation-agent-enhancement.md
- [ ] **AC4.5**: Move TASK-TEST-87F4-comprehensive-test-suite-agent-enhancement.md
- [ ] **AC4.6**: Move TASK-DOC-1E7B-incremental-enhancement-workflow-guide.md
- [ ] **AC4.7**: Move TASK-DOC-4F8A-agent-enhance-command-spec.md
- [ ] **AC4.8**: Move TASK-DOC-5B3E-phase-7-5-vs-8-comparison.md

#### Group 2: Design URL Integration (12 files)
- [ ] **AC4.9**: Create tasks/backlog/design-url-integration/ directory
- [ ] **AC4.10**: Move all TASK-UX-*.md files (12 tasks starting with TASK-UX-7F1E, TASK-UX-C3A3, etc.)

#### Group 3: Documentation (6 files)
- [ ] **AC4.11**: Create tasks/backlog/documentation/ directory
- [ ] **AC4.12**: Move TASK-061A-enable-github-pages-and-update-readme.md
- [ ] **AC4.13**: Move TASK-B479-create-landing-pages.md
- [ ] **AC4.14**: Move TASK-C5AC-create-mkdocs-configuration.md
- [ ] **AC4.15**: Move TASK-DFFA-setup-github-actions-workflow.md
- [ ] **AC4.16**: Move TASK-063-update-documentation-4-templates.md
- [ ] **AC4.17**: Move TASK-187C-update-claude-md.md (if exists)

#### Group 4: Testing (5 files)
- [ ] **AC4.18**: Create tasks/backlog/testing/ directory
- [ ] **AC4.19**: Move TASK-069-demo-test-core-template-usage.md
- [ ] **AC4.20**: Move TASK-070-demo-test-custom-template-from-existing-codebase.md
- [ ] **AC4.21**: Move TASK-071-demo-test-greenfield-template-creation.md
- [ ] **AC4.22**: Move TASK-072-demo-test-end-to-end-workflow.md
- [ ] **AC4.23**: Move TASK-073-create-demo-repositories.md

#### Group 5: Standalone (remaining ~12 files)
- [ ] **AC4.24**: Create tasks/backlog/standalone/ directory
- [ ] **AC4.25**: Move remaining individual tasks (TASK-064, TASK-9039B, TASK-ENH-*, TASK-FIX-*, etc.)

**Verification**:
```bash
ls tasks/backlog/agent-enhancement/*.md | wc -l  # Should be 7
ls tasks/backlog/design-url-integration/*.md | wc -l  # Should be 12
ls tasks/backlog/documentation/*.md | wc -l  # Should be 6
ls tasks/backlog/testing/*.md | wc -l  # Should be 5
ls tasks/backlog/standalone/*.md | wc -l  # Should be ~12
ls tasks/backlog/*.md | wc -l  # Should be 0 (all moved to subdirs)
```

### AC5: Create Archive README (1 file)

- [ ] **AC5.1**: Create tasks/archived/README.md explaining archive structure
- [ ] **AC5.2**: README documents why tasks were archived
- [ ] **AC5.3**: README links to replacement tasks/approaches

---

## Implementation Plan

### Step 1: Create Directory Structure (5 minutes)

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/taskwright

# Create new directories
mkdir -p tasks/completed/phase-8-work
mkdir -p tasks/archived/superseded/agent-discovery-old-approach
mkdir -p tasks/archived/superseded/phase-7-5-approach
mkdir -p tasks/archived/future-enhancements
mkdir -p tasks/backlog/agent-enhancement
mkdir -p tasks/backlog/design-url-integration
mkdir -p tasks/backlog/documentation
mkdir -p tasks/backlog/testing
mkdir -p tasks/backlog/standalone
mkdir -p docs/adrs
mkdir -p docs/design
mkdir -p docs/epics
mkdir -p docs/initiatives
mkdir -p docs/reviews
mkdir -p docs/checkpoints
mkdir -p docs/workflows
```

### Step 2: Move Completed Work (15 minutes)

**Review each file before moving** to confirm work is actually complete:

```bash
# Verify Phase 8 is complete
ls -la installer/global/lib/agent_enhancement/
ls -la installer/global/commands/agent-enhance.py
# If both exist, Phase 8 is complete

# Move completed tasks
mv tasks/backlog/TASK-PHASE-8-INCREMENTAL-specification.md tasks/completed/phase-8-work/
mv tasks/backlog/TASK-AGENT-BRIDGE-COMPLETE.md tasks/completed/
mv tasks/backlog/PRE-IMPLEMENTATION-WORK-COMPLETE.md tasks/completed/

# Verify C7A9 is complete before moving
grep -r "agent metadata" installer/global/ && \
mv tasks/backlog/TASK-C7A9-REIMPLEMENT-agent-metadata-in-CLAUDE.md tasks/completed/

# Move reviews
mv tasks/backlog/TASK-09E9-comprehensive-template-create-review.md tasks/completed/
mv tasks/backlog/EPIC-001-COMPREHENSIVE-REVIEW.md tasks/completed/
mv tasks/backlog/EPIC-001-REVIEW-RESOLUTION.md tasks/completed/
mv tasks/backlog/EPIC-001-SYSTEM-INTEGRATION-REVIEW.md tasks/completed/
```

**Verify**:
```bash
ls tasks/completed/*.md
# Should show 7 files + 1 in phase-8-work/
```

### Step 3: Move Planning Documents (20 minutes)

```bash
# ADRs
mv tasks/backlog/ADR-002-agent-discovery-strategy.md docs/adrs/

# Design docs
mv tasks/backlog/AGENT-STRATEGY-high-level-design.md docs/design/
mv tasks/backlog/PARALLEL-EXECUTION-STRATEGY.md docs/design/

# EPICs
mv tasks/backlog/EPIC-001-AGENT-DESIGN-SUMMARY.md docs/epics/
mv tasks/backlog/EPIC-001-ai-template-creation.md docs/epics/

# Initiatives
mv tasks/backlog/DEMO-TESTING-INITIATIVE-OVERVIEW.md docs/initiatives/

# Checkpoints
mv tasks/backlog/TASK-PHASE-1-CHECKPOINT.md docs/checkpoints/
mv tasks/backlog/TASK-PHASE-5-CHECKPOINT.md docs/checkpoints/

# Workflows
mv tasks/backlog/TEMPLATE-LIFECYCLE-complete-flow.md docs/workflows/
```

**Note**: Reviews already moved to tasks/completed/ in Step 2

**Verify**:
```bash
find docs/ -name "*.md" -type f
# Should show ADR, design docs, EPICs, etc.
```

### Step 4: Archive Superseded Tasks (20 minutes)

```bash
# Old agent discovery approach (Nov 21 exploratory work)
mv tasks/backlog/TASK-AGENT-BOUND-20251121-151631.md tasks/archived/superseded/agent-discovery-old-approach/
mv tasks/backlog/TASK-AGENT-EXAMPLES-20251121-151804.md tasks/archived/superseded/agent-discovery-old-approach/
mv tasks/backlog/TASK-AGENT-GIT-20251121-152113.md tasks/archived/superseded/agent-discovery-old-approach/
mv tasks/backlog/TASK-AGENT-STRUCT-20251121-151631.md tasks/archived/superseded/agent-discovery-old-approach/
mv tasks/backlog/TASK-AGENT-STYLE-20251121-152113.md tasks/archived/superseded/agent-discovery-old-approach/
mv tasks/backlog/TASK-AGENT-VALIDATE-20251121-160001.md tasks/archived/superseded/agent-discovery-old-approach/
mv tasks/backlog/TASK-AGENT-ENHANCER-20251121-160000.md tasks/archived/superseded/agent-discovery-old-approach/

# Phase 7.5 (replaced by Phase 8)
mv tasks/backlog/TASK-PHASE-7-5-SIMPLE-specification.md tasks/archived/superseded/phase-7-5-approach/

# Future enhancements
mv tasks/backlog/TASK-004-REDESIGN-ai-agent-discovery.md tasks/archived/future-enhancements/
mv tasks/backlog/TASK-004A-ai-agent-generator.md tasks/archived/future-enhancements/ 2>/dev/null || echo "Already archived or not found"
```

**Verify**:
```bash
find tasks/archived/ -name "*.md" -type f | wc -l
# Should be ~10-12
```

### Step 5: Organize Active Task Groups (30 minutes)

```bash
# Group 1: Agent Enhancement (7 tasks)
mv tasks/backlog/TASK-AI-2B37-ai-integration-agent-enhancement.md tasks/backlog/agent-enhancement/
mv tasks/backlog/TASK-DOC-F3A3-documentation-suite-agent-enhancement.md tasks/backlog/agent-enhancement/
mv tasks/backlog/TASK-E2E-97EB-end-to-end-validation-agent-enhancement.md tasks/backlog/agent-enhancement/
mv tasks/backlog/TASK-TEST-87F4-comprehensive-test-suite-agent-enhancement.md tasks/backlog/agent-enhancement/
mv tasks/backlog/TASK-DOC-1E7B-incremental-enhancement-workflow-guide.md tasks/backlog/agent-enhancement/
mv tasks/backlog/TASK-DOC-4F8A-agent-enhance-command-spec.md tasks/backlog/agent-enhancement/
mv tasks/backlog/TASK-DOC-5B3E-phase-7-5-vs-8-comparison.md tasks/backlog/agent-enhancement/

# Group 2: Design URL Integration (12 tasks - all TASK-UX-*)
mv tasks/backlog/TASK-UX-*.md tasks/backlog/design-url-integration/

# Group 3: Documentation (6 tasks)
mv tasks/backlog/TASK-061A-enable-github-pages-and-update-readme.md tasks/backlog/documentation/
mv tasks/backlog/TASK-B479-create-landing-pages.md tasks/backlog/documentation/
mv tasks/backlog/TASK-C5AC-create-mkdocs-configuration.md tasks/backlog/documentation/
mv tasks/backlog/TASK-DFFA-setup-github-actions-workflow.md tasks/backlog/documentation/
mv tasks/backlog/TASK-063-update-documentation-4-templates.md tasks/backlog/documentation/
mv tasks/backlog/TASK-187C-update-claude-md.md tasks/backlog/documentation/ 2>/dev/null || echo "Not found"

# Group 4: Testing (5 tasks)
mv tasks/backlog/TASK-069-demo-test-core-template-usage.md tasks/backlog/testing/
mv tasks/backlog/TASK-070-demo-test-custom-template-from-existing-codebase.md tasks/backlog/testing/
mv tasks/backlog/TASK-071-demo-test-greenfield-template-creation.md tasks/backlog/testing/
mv tasks/backlog/TASK-072-demo-test-end-to-end-workflow.md tasks/backlog/testing/
mv tasks/backlog/TASK-073-create-demo-repositories.md tasks/backlog/testing/

# Group 5: Standalone (remaining tasks)
# Move any remaining tasks to standalone/
find tasks/backlog/ -maxdepth 1 -name "TASK-*.md" -exec mv {} tasks/backlog/standalone/ \;
```

**Verify**:
```bash
ls tasks/backlog/agent-enhancement/*.md | wc -l  # Should be 7
ls tasks/backlog/design-url-integration/*.md | wc -l  # Should be 12
ls tasks/backlog/documentation/*.md | wc -l  # Should be ~6
ls tasks/backlog/testing/*.md | wc -l  # Should be 5
ls tasks/backlog/standalone/*.md | wc -l  # Should be ~12
ls tasks/backlog/*.md 2>/dev/null | wc -l  # Should be 0
```

### Step 6: Create Archive README (10 minutes)

```bash
cat > tasks/archived/README.md << 'EOF'
# Archived Tasks

This directory contains tasks that have been archived for reference.

## Directory Structure

### superseded/
Tasks that have been replaced by newer approaches or completed through different means.

#### agent-discovery-old-approach/ (7 tasks)
**Archived**: 2025-11-21
**Reason**: Exploratory work on agent discovery using structured templates. Superseded by simpler Phase 8 incremental approach.

**Tasks**:
- TASK-AGENT-BOUND-20251121-151631.md
- TASK-AGENT-EXAMPLES-20251121-151804.md
- TASK-AGENT-GIT-20251121-152113.md
- TASK-AGENT-STRUCT-20251121-151631.md
- TASK-AGENT-STYLE-20251121-152113.md
- TASK-AGENT-VALIDATE-20251121-160001.md
- TASK-AGENT-ENHANCER-20251121-160000.md

**Replacement**: Phase 8 INCREMENTAL specification (TASK-PHASE-8-INCREMENTAL, completed Nov 21)

#### phase-7-5-approach/ (1 task)
**Archived**: 2025-11-21
**Reason**: Phase 7.5 batch processing approach was implemented, tested, and then removed in favor of Phase 8 incremental approach.

**Tasks**:
- TASK-PHASE-7-5-SIMPLE-specification.md

**Replacement**: Phase 8 INCREMENTAL specification

**Git History**:
- Commit: "feat: Implement TASK-PHASE-8-INCREMENTAL" (Nov 21)
- Commit: "feat: Complete TASK-SIMP-9ABE - Remove Phase 7.5 agent enhancement" (Nov 21)

### future-enhancements/
Tasks for future phases or optional features not currently prioritized.

#### External Agent Discovery (2 tasks)
**Archived**: 2025-11-21
**Reason**: Phase 2 optional feature. Current focus is Phase 1 (core template creation).

**Tasks**:
- TASK-004-REDESIGN-ai-agent-discovery.md (External discovery)
- TASK-004A-ai-agent-generator.md (Agent generation)

**Status**: Deferred to Phase 2

## When to Review Archived Tasks

- **Learning**: Understand evolution of approaches (why certain designs were rejected)
- **Historical context**: Reference for design decisions
- **Feature resurrection**: If requirements change, archived features might become relevant again

## Do NOT Use These Tasks

Tasks in this directory are archived for reference only. Do not implement them unless:
1. Requirements have changed significantly
2. New context makes the approach viable
3. You've discussed with the team and updated the task

For current work, see:
- Active tasks: `tasks/backlog/`
- Completed tasks: `tasks/completed/`
EOF
```

### Step 7: Final Verification (10 minutes)

```bash
# Count files in each directory
echo "=== Verification ==="
echo ""
echo "Completed tasks:"
find tasks/completed/ -name "*.md" -type f | wc -l
echo "Expected: 8"
echo ""
echo "Archived tasks:"
find tasks/archived/ -name "*.md" -type f | wc -l
echo "Expected: ~10-12"
echo ""
echo "Planning docs:"
find docs/ -name "*.md" -type f | wc -l
echo "Expected: Previous count + 10-14"
echo ""
echo "Active backlog groups:"
echo "  agent-enhancement: $(ls tasks/backlog/agent-enhancement/*.md 2>/dev/null | wc -l) (expected: 7)"
echo "  design-url-integration: $(ls tasks/backlog/design-url-integration/*.md 2>/dev/null | wc -l) (expected: 12)"
echo "  documentation: $(ls tasks/backlog/documentation/*.md 2>/dev/null | wc -l) (expected: 6)"
echo "  testing: $(ls tasks/backlog/testing/*.md 2>/dev/null | wc -l) (expected: 5)"
echo "  standalone: $(ls tasks/backlog/standalone/*.md 2>/dev/null | wc -l) (expected: ~12)"
echo ""
echo "Files remaining in tasks/backlog/ root:"
ls tasks/backlog/*.md 2>/dev/null | wc -l
echo "Expected: 0 (all moved to subdirectories)"
echo ""

# Tree view
echo "=== Directory Structure ==="
tree -L 2 tasks/ docs/ 2>/dev/null || find tasks/ docs/ -type d | sort
```

---

## Success Metrics

### Before Cleanup
- Total tasks in backlog: 80 files
- Structure: Flat (all in one directory)
- Mix of active tasks, completed work, planning docs, superseded tasks
- Hard to navigate and prioritize

### After Cleanup
- **Active tasks**: 42 files (47.5% reduction)
- **Organized**: 5 logical groups
- **Completed**: 8 files moved to tasks/completed/
- **Archived**: 12 files moved to tasks/archived/
- **Planning docs**: 18 files moved to docs/
- **Easy to navigate**: Clear initiative grouping

### Quality Improvements
- ✅ Active backlog reduced by 47.5%
- ✅ Clear priority groups (agent-enhancement, design-url-integration)
- ✅ Planning docs in correct location (docs/ not tasks/)
- ✅ Completed work properly archived
- ✅ Superseded tasks documented with rationale

---

## Post-Cleanup Actions

### 1. Update README.md Index (if it exists)

Update any backlog index or task listing in README.md to reflect new structure.

### 2. Create Initiative READMEs

Create README.md in each group folder explaining the initiative:

```bash
# Example: tasks/backlog/agent-enhancement/README.md
cat > tasks/backlog/agent-enhancement/README.md << 'EOF'
# Agent Enhancement Initiative

**Status**: Core implementation complete (Phase 8), polish/testing in progress
**Priority**: HIGH
**Estimated Effort**: 60-80 hours total

## Overview

Polish and testing for the agent enhancement workflow (Phase 8 INCREMENTAL).

Core functionality exists:
- `/agent-enhance` command implemented
- `lib/agent_enhancement/` module created
- Incremental enhancement workflow operational

## Tasks (7 total)

**Start Here**:
1. TASK-AI-2B37 - AI integration (20 hours)
2. TASK-TEST-87F4 - Comprehensive test suite (20 hours)

**Then**:
3. TASK-DOC-F3A3 - Documentation suite (8 hours)
4. TASK-E2E-97EB - End-to-end validation (8 hours)
5. TASK-DOC-1E7B - Workflow guide (4 hours)
6. TASK-DOC-4F8A - Command spec (4 hours)
7. TASK-DOC-5B3E - Phase comparison (2 hours)

## Dependencies

None - core implementation complete, these are polish/testing tasks.
EOF
```

### 3. Commit Changes

```bash
git add tasks/ docs/
git commit -m "refactor: Organize backlog (80 → 42 active tasks)

- Move 8 completed tasks to tasks/completed/
- Move 18 planning docs to docs/ (ADRs, EPICs, reviews)
- Archive 12 superseded tasks to tasks/archived/
- Organize 42 active tasks into 5 groups:
  - agent-enhancement/ (7 tasks)
  - design-url-integration/ (12 tasks)
  - documentation/ (6 tasks)
  - testing/ (5 tasks)
  - standalone/ (12 tasks)

Backlog size reduced by 47.5%, easier to navigate and prioritize."
```

---

## Notes

### Why These Specific Archives?

**Old Agent Discovery Approach** (7 tasks):
- Created Nov 21 as exploratory work
- Detailed templates for boundaries, examples, structure, etc.
- Superseded by simpler Phase 8 incremental approach
- Archived for reference (good ideas, but over-engineered for current needs)

**Phase 7.5** (1 task):
- Batch processing approach
- Implemented, tested, then removed per git history
- Phase 8 incremental approach proved superior
- Archived to document evolution

**Future Enhancements** (2 tasks):
- External agent discovery (TASK-004)
- Optional Phase 2 feature
- Not currently prioritized
- Might be useful later if requirements change

### Decision: Keep or Archive?

If unsure whether to archive a task:
1. **Check git history**: Is work already done?
2. **Check for duplicates**: Is another task doing the same thing?
3. **Check priority**: Has this been deprioritized or superseded?
4. **When in doubt**: Keep in backlog/standalone/ (can archive later)

---

## Completion Checklist

- [ ] All 5 acceptance criteria met (AC1-AC5)
- [ ] Directory structure created
- [ ] 8 completed tasks moved
- [ ] 18 planning docs moved to docs/
- [ ] 12 superseded tasks archived
- [ ] 42 active tasks organized into 5 groups
- [ ] Archive README.md created
- [ ] Verification script run successfully
- [ ] Changes committed to git
- [ ] README.md updated (if needed)

---

**Created**: 2025-11-21
**Status**: BACKLOG
**Ready for Implementation**: YES
