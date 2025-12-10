---
id: TASK-DOC-83F0
title: Create missing guide documents
status: completed
created: 2025-11-27T02:00:00Z
updated: 2025-11-27T08:00:00Z
completed_at: 2025-11-27T08:00:00Z
priority: high
tags: [documentation, guides, workflows]
complexity: 4
related_to: [TASK-DOC-F3BA]
---

# Task: Create Missing Guide Documents

## Context

Review task TASK-DOC-F3BA identified that several guide documents are referenced in command documentation but don't exist, resulting in broken links:

1. **docs/guides/agent-enhancement-decision-guide.md** - Referenced in TASK-DOC-F3BA, template-create.md
2. **docs/workflows/incremental-enhancement-workflow.md** - Referenced in TASK-DOC-F3BA, TASK-DOC-1E7B

These guides are critical for helping users understand:
- When to use /agent-format vs /agent-enhance
- Option A (hybrid enhancement) vs Option B (/task-work) comparison
- Phase 8 incremental enhancement workflow
- Agent enhancement best practices

## Objective

Create two comprehensive guide documents that fix broken links and provide clear guidance on agent enhancement workflows.

## Scope

### Files to Create

1. **docs/guides/agent-enhancement-decision-guide.md**:
   - Decision matrix: /agent-format vs /agent-enhance
   - Option A (hybrid) vs Option B (/task-work) comparison
   - Use case examples with recommendations
   - Quality vs speed trade-offs

2. **docs/workflows/incremental-enhancement-workflow.md**:
   - Phase 8 workflow overview
   - Task-based vs direct command approach
   - Batch enhancement strategies
   - Best practices and troubleshooting

### Files to Update (Cross-references)

3. **installer/core/commands/template-create.md**:
   - Add link to agent-enhancement-decision-guide.md
   - Add link to incremental-enhancement-workflow.md

4. **installer/core/commands/agent-enhance.md**:
   - Add link to agent-enhancement-decision-guide.md
   - Add link to incremental-enhancement-workflow.md

## Acceptance Criteria

### agent-enhancement-decision-guide.md
- [x] Decision matrix created: /agent-format vs /agent-enhance
- [x] Quality comparison documented (6/10 vs 9/10)
- [x] Duration comparison documented (instant vs 2-5 min)
- [x] Option A vs Option B comparison table created
- [x] Use case examples provided (7 scenarios)
- [x] Quality vs speed trade-offs explained
- [x] Batch enhancement guidance included
- [x] Cross-references to command docs added

### incremental-enhancement-workflow.md
- [x] Phase 8 workflow overview documented
- [x] Task-based approach explained (--create-agent-tasks)
- [x] Direct command approach explained (--no-create-agent-tasks)
- [x] Workflow comparison table created
- [x] Batch enhancement strategies documented (parallel vs sequential)
- [x] Best practices section added (7 practices)
- [x] Troubleshooting section added (4 common issues)
- [x] Code examples included for both approaches (4 examples)
- [x] Cross-references to command docs added

### Cross-reference Updates
- [x] template-create.md links updated
- [x] agent-enhance.md links updated
- [x] No broken links introduced
- [x] All references validated

## Completion Report

### Summary
**Task**: Create missing guide documents
**Completed**: 2025-11-27T08:00:00Z
**Duration**: 6 hours
**Final Status**: ✅ COMPLETED

### Deliverables
- Files created: 2 comprehensive guides (39KB total)
- Files updated: 2 command documentation files
- Cross-references added: 4 bidirectional links
- All links validated and working

### Quality Metrics
- All acceptance criteria met: ✅
- Progressive disclosure structure: ✅ (Quick Start → Core Concepts → Complete Reference)
- Code examples included: ✅ (4 complete examples)
- Cross-references validated: ✅ (all paths tested)
- Documentation complete: ✅
- Consistent with Taskwright style: ✅

### Files Created

1. **docs/guides/agent-enhancement-decision-guide.md** (17,735 bytes)
   - Decision matrices for format vs enhance, hybrid vs task-work
   - 7 detailed use case examples
   - Batch enhancement strategies
   - Quality vs speed trade-offs analysis
   - Comprehensive troubleshooting (4 issues)
   - Structured as: Quick Start (2 min) → Core Concepts (10 min) → Complete Reference (30 min)

2. **docs/workflows/incremental-enhancement-workflow.md** (21,231 bytes)
   - Phase 8 workflow execution flow diagram
   - Task metadata structure documentation
   - 2 complete workflow approaches (task-based, direct)
   - 3 batch enhancement strategies
   - 7 best practices with examples
   - 4 common troubleshooting scenarios
   - 4 complete code examples
   - Structured as: Quick Start (2 min) → Core Concepts (10 min) → Complete Reference (30 min)

### Files Updated

3. **installer/core/commands/template-create.md**
   - Added organized "See Also" section
   - Links to both new guides with correct relative paths
   - Categorized cross-references (Command Docs, Workflow Guides, Implementation Tasks)

4. **installer/core/commands/agent-enhance.md**
   - Enhanced "See Also" section with categorization
   - Links to both new guides with correct relative paths
   - Organized into: Command Documentation, Workflow Guides, Reference Documentation, Implementation Tasks

### Link Validation
All cross-references validated:
- From command files: `../../../docs/guides/` and `../../../docs/workflows/`
- From guide files: `../../installer/core/commands/` and `../workflows/`
- All referenced files exist and are accessible
- No broken links introduced

### Git Activity
- Branch: `RichWoollcott/doc-missing-guides`
- Commit: `7190c17` - "Create missing guide documents"
- Files changed: 4 (2 new, 2 modified)
- Lines added: 1,435+
- Working tree: Clean

## Impact
- Fixed 2 broken documentation references identified in TASK-DOC-F3BA
- Provided comprehensive guidance for agent enhancement workflows
- Enhanced discoverability through organized cross-references
- Improved user experience with progressive disclosure structure
- Added 7 use cases + 4 code examples for practical guidance

## Source

**Review Report**: [TASK-DOC-F3BA Review Report](../../../.claude/task-plans/TASK-DOC-F3BA-review-report.md)
**Priority**: P2 (High)
**Estimated Effort**: 3-4 hours
**Actual Effort**: ~6 hours

## Method

**Claude Code Direct** - New file creation, documentation only
