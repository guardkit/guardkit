---
id: TASK-GI-DOC-003
title: Write Graphiti Architecture Documentation
status: backlog
created: 2026-01-29T11:00:00Z
updated: 2026-01-29T11:00:00Z
priority: medium
tags: [documentation, graphiti, architecture, api-reference]
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

## Test Requirements

- [ ] Markdown lints without errors
- [ ] Code examples are syntactically correct Python
- [ ] All links valid
- [ ] API matches actual implementation
