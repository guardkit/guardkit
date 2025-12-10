---
id: TASK-000
title: "Requirements Removal Overview - Taskwright Lite"
created: 2025-10-27
status: backlog
priority: high
complexity: 0
parent_task: none
subtasks:
  - TASK-002
  - TASK-003
  - TASK-004
  - TASK-005
  - TASK-006
  - TASK-007
  - TASK-008
  - TASK-009
  - TASK-010
  - TASK-011
---

# TASK-000: Requirements Removal Overview

## Context

Taskwright (formerly "Agentecflow Lite") is being extracted from the TASK-001 series to focus on lightweight task workflow with quality gates, removing all requirements management features (EARS, BDD, Epic/Feature hierarchy).

## Strategic Goal

Create a pragmatic, lightweight AI-assisted development system that:
- ✅ Provides quality gates (Phase 2.5, 4.5, 2.6, 2.7, 5.5)
- ✅ Manages task workflow (backlog → in_progress → completed)
- ✅ Supports multiple technology stacks
- ❌ Does NOT include requirements management
- ❌ Does NOT include epic/feature hierarchy
- ❌ Does NOT include PM tool synchronization

## Task Breakdown

### Phase 1: Remove Files (3-4 hours)

**TASK-002: Remove Requirements Management Commands** [2h]
- Remove 13 command files (gather-requirements, epic-create, feature-create, etc.)
- Pure deletion task

**TASK-003: Remove Requirements Management Agents** [1h]
- Remove 2 agent files (requirements-analyst, bdd-generator)
- Pure deletion task

**TASK-007: Remove Requirements Library Modules** [1.5h]
- Remove feature_generator.py and related modules
- Verify no broken imports

**TASK-009: Remove Requirements Directory Structure** [1h]
- Remove docs/epics/, docs/features/, docs/requirements/, docs/bdd/
- Update installer scripts

### Phase 2: Modify Commands (5 hours)

**TASK-004: Modify task-create.md** [1.5h]
- Remove epic/feature/requirements frontmatter
- Simplify to 8 fields (from 11)
- Update examples

**TASK-005: Modify task-work.md** [2h]
- Simplify Phase 1 (remove requirements loading)
- Remove agent orchestration for requirements-analyst, bdd-generator
- Keep all quality gate phases (2.5, 2.6, 2.7, 4.5, 5.5)
- Most complex modification task

**TASK-006: Modify task-status.md** [1.5h]
- Remove epic/feature/requirements filters
- Simplify kanban board output
- Remove PM tool sync status

### Phase 3: Update Configuration & Documentation (5 hours)

**TASK-008: Clean Stack Template CLAUDE.md Files** [2h]
- Update 8 template CLAUDE.md files
- Remove requirements references
- Keep stack-specific patterns and quality gates

**TASK-010: Update Manifest and Configuration** [1h]
- Update manifest.json (name, capabilities)
- Remove requirements-engineering, bdd-generation capabilities
- Add architectural-review, test-enforcement capabilities

**TASK-011: Update Root Documentation** [2h]
- Rewrite README.md for taskwright positioning
- Update root CLAUDE.md
- Emphasize lightweight + quality gates
- Remove all requirements management references

## Total Effort Estimate

**13-14 hours** across 10 subtasks

**Sequencing**:
1. Can parallelize Phase 1 tasks (all deletions)
2. Phase 2 tasks have dependencies (do after Phase 1)
3. Phase 3 tasks can be parallelized (documentation updates)

## Success Criteria

### Functional
- [ ] All requirements management features removed
- [ ] Task workflow commands functional
- [ ] Quality gates intact (Phase 2.5, 4.5, 2.6, 2.7, 5.5)
- [ ] All 8 stack templates work
- [ ] Installation succeeds

### Quality
- [ ] No references to EARS/BDD/epics in active code
- [ ] Clear, concise documentation
- [ ] Lightweight positioning evident
- [ ] No broken imports or references

### Positioning
- [ ] README emphasizes pragmatic developers
- [ ] "5-minute quickstart" messaging
- [ ] Quality gates as key differentiator
- [ ] "No ceremony" clear

## What Gets Removed

### Commands (13)
- gather-requirements.md
- formalize-ears.md
- generate-bdd.md
- epic-create.md, epic-status.md, epic-sync.md, epic-generate-features.md
- feature-create.md, feature-status.md, feature-sync.md, feature-generate-tasks.md
- hierarchy-view.md, portfolio-dashboard.md
- task-sync.md

### Agents (2)
- requirements-analyst.md
- bdd-generator.md

### Library Modules
- feature_generator.py
- Any epic/requirement/ears/bdd modules

### Directories
- docs/epics/
- docs/features/
- docs/requirements/
- docs/bdd/

### Documentation Sections
- Stage 1: Specification
- Stage 2: Tasks Definition (epic/feature parts)
- EARS Notation Patterns
- Epic/Feature Hierarchy
- External PM Tool Integration

## What Gets Kept

### Commands (8)
- task-create.md (modified)
- task-work.md (modified)
- task-complete.md
- task-status.md (modified)
- task-refine.md
- debug.md
- figma-to-react.md
- zeplin-to-maui.md

### Agents (15)
- All quality gate agents (architectural-reviewer, test-verifier, etc.)
- All supporting agents (debugging-specialist, devops-specialist, etc.)

### Quality Gates (ALL)
- Phase 2.5: Architectural Review
- Phase 2.6: Human Checkpoint
- Phase 2.7: Complexity Evaluation
- Phase 4.5: Test Enforcement
- Phase 5.5: Plan Audit

### Templates (8)
- All stack templates with cleaned CLAUDE.md files

## Validation Strategy

### Automated Checks
```bash
# No requirements references
grep -r "EARS\|epic.*create\|feature.*create" installer/core/commands/ \
  | grep -v "backup\|Historical"

# Command count
ls -1 installer/core/commands/*.md | wc -l  # Should be 8

# Agent count
ls -1 installer/core/agents/*.md | wc -l    # Should be 15

# No broken imports
python3 -c "import installer.core.commands.lib.*"
```

### Manual Testing
- Install from scratch
- Initialize each template
- Create and work on task
- Verify quality gates execute

## Related Documents

- Original analysis: tasks/backlog/TASK-001-*.md series
- Design decisions: docs/adr/ (to be created)

## Next Steps After Completion

1. Test installation on fresh system
2. Validate all 8 templates
3. Run smoke tests for quality gates
4. Update CHANGELOG.md
5. Create v1.0.0 release
6. Announce taskwright

## Notes

- This is a simplification effort, not a feature addition
- Focus on clarity and removal of complexity
- Keep all quality gates intact - they're the core value
- Document what was removed for reference
- Consider archiving TASK-001 series after extraction
