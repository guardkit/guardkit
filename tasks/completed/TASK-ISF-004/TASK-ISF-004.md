---
id: TASK-ISF-004
title: Seed Graphiti fidelity knowledge into Graphiti
status: completed
completed: 2026-03-04T00:00:00Z
completed_location: tasks/completed/TASK-ISF-004/
priority: high
complexity: 2
parent_review: TASK-REV-C043
feature_id: FEAT-ISF
wave: 2
implementation_mode: direct
tags: [graphiti, knowledge, fidelity, architectural-decision]
---

# TASK-ISF-004: Seed Graphiti Fidelity Knowledge

## Problem

A critical architectural insight from the Feb 5 fidelity assessment is not captured in Graphiti:

> "Graphiti is a knowledge graph that extracts semantic facts, not a document store that preserves verbatim content."

This insight led to:
- Cancellation of TASK-CR-006, CR-007, CR-008
- Pivot of FEAT-CR01 to Graphiti-independent reduction (TASK-REV-CROPT)
- Understanding that code examples cannot be retrieved in copy-paste usable form

Without this in Graphiti, future sessions may re-attempt the same failed approach.

## Solution

Add this knowledge as an episode in Graphiti so it can be retrieved during future planning sessions. This should be seeded as a system-scoped episode (applies across all projects).

### Episode Content

```
Name: "Graphiti Fidelity Limitation: Facts Not Documents"
Group: "architectural_decisions" (or appropriate system group)
Body:
  Graphiti is a knowledge graph that extracts semantic facts, not a document store
  that preserves verbatim content. Code examples cannot be reliably retrieved in
  copy-paste usable form.

  Implications:
  - Do NOT attempt to store/retrieve Python code blocks via Graphiti
  - Pattern files (.claude/rules/patterns/) must remain as static markdown
  - Use Graphiti for semantic search ("which pattern?"), not code retrieval
  - Content preview (500 chars) is sufficient for semantic search episodes
  - FEAT-CR01 context reduction is Graphiti-independent (path-gating + trimming)

  Evidence: docs/reviews/graphiti_enhancement/graphiti_code_retrieval_fidelity.md
  Decision: TASK-REV-CROPT (pivot to Graphiti-independent reduction)
  Date: 2026-02-05
```

## Implementation

Can be done via:
1. `guardkit graphiti capture --interactive` (manual)
2. Adding an episode to an existing seeding module
3. Creating a dedicated seeding function in `project_seeding.py`

Option 2/3 preferred — ensures the knowledge persists across `graphiti clear` operations.

## Acceptance Criteria

- [x] Fidelity knowledge seeded into Graphiti
- [x] Retrievable via `guardkit graphiti search "Graphiti fidelity"`
- [x] Retrievable via `guardkit graphiti search "code retrieval"`
- [x] Includes reference to the Feb 5 assessment document
- [x] System-scoped (not project-scoped) so it persists across projects

## Source Document

`docs/reviews/graphiti_enhancement/graphiti_code_retrieval_fidelity.md`
