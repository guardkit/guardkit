---
id: TASK-CR-006
title: Seed Graphiti patterns group with code examples
status: in_review
created: 2026-02-05 14:00:00+00:00
updated: 2026-02-05 14:00:00+00:00
priority: medium
tags:
- graphiti
- knowledge-seeding
- patterns
parent_review: TASK-REV-5F19
feature_id: FEAT-CR01
implementation_mode: direct
wave: 2
complexity: 4
task_type: scaffolding
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-CR01
  base_branch: main
  started_at: '2026-02-05T17:27:40.763033'
  last_updated: '2026-02-05T17:31:44.141603'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-05T17:27:40.763033'
    player_summary: Created seed_pattern_examples.py module to seed Graphiti patterns
      group with concrete code examples from .claude/rules/patterns/*.md files. The
      module extracts 17 pattern episodes (5 dataclass, 5 Pydantic, 7 orchestrator)
      with actual Python code, not just descriptions. Each pattern includes complete
      code examples, usage guidance, and 'When to use' sections. Comprehensive test
      suite validates extraction, seeding, error handling, and retrieval fidelity.
    player_success: true
    coach_success: true
---

# Task: Seed Graphiti Patterns Group with Code Examples

## Description

The Graphiti patterns group has 19 episodes but only contains relationship data (e.g., "dataclass pattern exists"), not the actual Python code examples that Claude needs for guidance. Seed the group with concrete code examples from the pattern files.

## Acceptance Criteria

- [ ] Dataclass patterns seeded: basic state containers, optional fields, JSON serialization, computed properties, field() usage
- [ ] Pydantic patterns seeded: basic model structure, field definitions, nested models, serialization, JSON schema
- [ ] Orchestrator patterns seeded: pipeline step execution, checkpoint-resume, validation chain, state management, error recovery, progress reporting, strategy routing
- [ ] Each pattern episode includes actual Python code, not just descriptions
- [ ] Retrievable via: `guardkit graphiti search "dataclass JSON serialization" --group patterns`
- [ ] Relevance scores >0.6 for pattern queries

## Implementation Notes

This is the blocker for Wave 3 pattern file trimming (TASK-CR-007, TASK-CR-008). Must verify retrieval fidelity of code examples before those tasks proceed.

Key concern: Graphiti may not preserve code formatting well. If retrieval fidelity is poor, pattern files should remain static (path-gated) and this approach should be abandoned for code examples specifically.
