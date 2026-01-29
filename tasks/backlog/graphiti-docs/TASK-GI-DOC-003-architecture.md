---
id: TASK-GI-DOC-003
title: Write Graphiti Architecture Documentation
status: in_review
created: 2026-01-29 11:00:00+00:00
updated: 2026-01-29 11:00:00+00:00
priority: medium
tags:
- documentation
- graphiti
- architecture
- api-reference
complexity: 4
feature_id: FEAT-GI-DOC
parent_review: TASK-GI-DOC
implementation_mode: direct
wave: 1
parallel_group: wave1-3
test_results:
  status: pending
  coverage: null
  last_run: null
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-GI-DOC
  base_branch: main
  started_at: '2026-01-29T16:53:46.199251'
  last_updated: '2026-01-29T16:59:50.914206'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-01-29T16:53:46.199251'
    player_summary: "Created comprehensive Graphiti architecture documentation at\
      \ docs/architecture/graphiti-architecture.md.\n\nThe document includes:\n\n\
      1. **System Overview** - ASCII diagram showing Claude Code \u2192 Graphiti \u2192\
      \ FalkorDB data flow with component descriptions\n\n2. **Knowledge Categories**\
      \ - Complete table of all 20+ group_ids with:\n   - Contents description\n \
      \  - Which task seeded each category\n   - Episode count estimates\n   - Which\
      \ context loader uses it\n   - Included FEAT-GE enhancements (turn_state, qual"
    player_success: true
    coach_success: true
---

# Task: Write Graphiti Architecture Documentation

## Description

Create technical deep-dive documentation at `docs/architecture/graphiti-architecture.md`. This serves advanced users and contributors who need to understand internals, extend the system, or debug issues.

## Requirements

### Content Structure

1. **System Overview**
   - ASCII diagram showing Claude Code session → Graphiti flow
   - Components: FalkorDB, Graphiti API, GuardKit client
   - Data flow for context loading

2. **Knowledge Categories**
   - Complete table of all group_ids
   - What each category contains
   - Which TASK-GI-* seeded each category
   - Episode count estimates

3. **Python API Reference**
   - Core Client (`GraphitiClient`, `init_graphiti`, `get_graphiti`)
   - Context Loading (`load_critical_context`, `format_context_for_injection`)
   - ADR Service (`ADRService`, `ADRStatus`, `ADRTrigger`)
   - Outcome Capture (`capture_task_outcome`, `OutcomeType`)
   - Code examples for each major function

4. **Integration Points**
   - task-work integration (Phase 1 context loading)
   - feature-build integration (pre-loop context)
   - How outcomes are captured on completion

5. **Entity Models**
   - ADREntity dataclass fields
   - TaskOutcome dataclass fields
   - CriticalContext structure

6. **Extending the System**
   - Adding new knowledge categories
   - Creating custom entities
   - Seeding custom knowledge

### Source Materials

- `guardkit/knowledge/__init__.py` - Public API and docstrings
- `guardkit/knowledge/graphiti_client.py` - Client implementation
- `guardkit/knowledge/context_loader.py` - Context loading
- `guardkit/knowledge/adr_service.py` - ADR operations
- `guardkit/knowledge/outcome_manager.py` - Outcome capture
- `guardkit/knowledge/seeding.py` - Seeding functions
- `.claude/reviews/TASK-GI-DOC-review-report.md` - Outline

### Style Guidelines

- Include code examples for each API function
- Use ASCII diagrams for architecture visualization
- Target audience: developers extending GuardKit
- Keep to ~500 lines

## Acceptance Criteria

- [ ] File created at `docs/architecture/graphiti-architecture.md`
- [ ] System overview with ASCII diagram
- [ ] Complete knowledge categories table
- [ ] Python API reference with code examples
- [ ] Integration points documented
- [ ] Entity model fields documented
- [ ] Extension guide included

## Implementation Notes

Extract docstrings and type hints from actual Python code for accuracy. All code examples should be runnable.

**Important**: Document what is actually implemented, not just the original FEAT-GI scope. If FEAT-GE (Graphiti Enhancements) has been merged, include:
- Feature Overview Entity (GE-001)
- Turn State Episodes (GE-002)
- Role Constraint Facts (GE-003)
- Failed Approach Episodes (GE-004)
- Quality Gate Config Facts (GE-005)
- Immediate ADR Seeding (GE-007)

Check `guardkit/knowledge/entities/` and `guardkit/knowledge/seeding.py` for current entity/episode types.

## Test Requirements

- [ ] Markdown lints without errors
- [ ] Code examples are syntactically correct Python
- [ ] All links valid
- [ ] API matches actual implementation
