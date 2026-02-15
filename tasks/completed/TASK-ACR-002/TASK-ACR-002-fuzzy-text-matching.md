---
id: TASK-ACR-002
title: "Add fuzzy text matching fallback to coach_validator"
status: completed
created: 2026-02-15T10:00:00Z
updated: 2026-02-15T14:35:00Z
completed: 2026-02-15T14:35:00Z
completed_location: tasks/completed/TASK-ACR-002/
priority: high
task_type: feature
parent_review: TASK-REV-B5C4
feature_id: FEAT-F022
wave: 2
implementation_mode: task-work
complexity: 5
previous_state: in_review
state_transition_reason: "All quality gates passed, all acceptance criteria met"
dependencies:
  - TASK-ACR-001
tags: [autobuild, coach, criteria-verification, f2-fix, fuzzy-matching]
test_results:
  status: passed
  total_tests: 235
  passed: 235
  failed: 0
  last_run: 2026-02-15T14:30:00Z
---

# Task: Add fuzzy text matching fallback to coach_validator

## Description

Enhance `_match_by_text()` in `coach_validator.py` with a secondary fuzzy matching strategy when exact normalized matching fails. This catches cases where the Player rephrases acceptance criteria or adds/removes punctuation.

The fuzzy match must be conservative to avoid false positives.

## Files to Modify

- `guardkit/orchestrator/quality_gates/coach_validator.py` — `_match_by_text()` (~line 1096)

## Acceptance Criteria

- [x] AC-001: Strip common prefixes (`- [ ]`, `- [x]`, `* `, numbers) before matching
- [x] AC-002: Substring containment check: if requirement text contains criterion text (or vice versa), count as matched
- [x] AC-003: Keyword overlap fallback: extract significant keywords (>3 chars, not stopwords), match if overlap >= 70%
- [x] AC-004: Fuzzy match only triggers when exact match fails (exact match remains primary)
- [x] AC-005: Log which matching strategy produced each match (exact vs substring vs keyword)
- [x] AC-006: No false positives: unrelated criteria text must NOT match (verified by unit tests with adversarial examples)
- [x] AC-007: Unit tests cover exact match, substring match, keyword match, and rejection cases

## Implementation Notes

Matching priority order:
1. Exact normalized (existing) — highest confidence
2. Substring containment — high confidence
3. Keyword overlap >= 70% — medium confidence

Log format: `"AC-001: Matched via {strategy} (confidence: {level})"`
