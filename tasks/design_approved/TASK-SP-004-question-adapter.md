---
autobuild_state:
  base_branch: main
  current_turn: 1
  last_updated: '2026-02-09T12:21:25.949001'
  max_turns: 25
  started_at: '2026-02-09T12:10:32.866126'
  turns:
  - coach_success: true
    decision: approve
    feedback: null
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-02-09T12:10:32.866126'
    turn: 1
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-6EDD
complexity: 5
dependencies:
- TASK-SP-001
feature_id: FEAT-SP-001
id: TASK-SP-004
implementation_mode: task-work
parent_review: TASK-REV-DBBC
status: design_approved
tags:
- system-plan
- questions
- adaptive-flow
task_type: feature
title: Implement adaptive question flow engine
wave: 2
---

# Task: Implement Adaptive Question Flow Engine

## Description

Create the `SetupQuestionAdapter` that controls which questions are asked during `/system-plan setup` mode. Questions adapt based on the selected methodology (Modular/Layered/DDD/Event-Driven) and prior answers (e.g., skip microservice questions for monoliths).

## Acceptance Criteria

- [ ] `SetupQuestionAdapter` class with methodology-aware question flow
- [ ] `get_methodology(answers: dict) -> str` — extracts methodology from answers
- [ ] `should_ask_ddd_questions(answers: dict) -> bool` — True only when methodology=="ddd"
- [ ] `should_ask_event_driven_questions(answers: dict) -> bool` — True for event_driven or DDD
- [ ] `should_ask_microservice_questions(answers: dict) -> bool` — False for monolith deployment
- [ ] `get_categories(answers_so_far: dict) -> list` — returns 6 categories (always all 6)
- [ ] `get_questions_for_category(category: str, answers_so_far: dict) -> list` — adapted questions
- [ ] DDD-specific questions (Q6d, Q7d, Q8d, Q9d) only included when DDD selected
- [ ] Microservice-specific questions filtered out when deployment=="monolith"
- [ ] "Not sure" methodology defaults to modular question set
- [ ] Question data structure includes: id, text, options (if applicable), microservice_only flag
- [ ] 6 categories: domain_and_methodology, system_structure, service_relationships, technology_decisions, crosscutting_concerns, constraints
- [ ] Unit tests for all adaptation logic and edge cases

## Files to Create

- `guardkit/planning/question_adapter.py` — SetupQuestionAdapter + question definitions
- `tests/unit/planning/test_question_adapter.py` — Unit tests

## Implementation Notes

- Follow spec section "Interactive Flow > Mode: Setup"
- Question definitions can be module-level constants (CATEGORY_QUESTIONS dict, DDD_SPECIFIC_QUESTIONS list)
- Use a simple dataclass or namedtuple for individual questions
- The adapter does NOT handle user interaction — it only determines WHICH questions to present
- The actual Q&A interaction is handled by the slash command (spec-driven) or CLI command