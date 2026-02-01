---
complexity: 5
dependencies:
- TASK-GR4-001
estimate_hours: 3
feature_id: FEAT-0F4A
id: TASK-GR4-002
implementation_mode: task-work
parallel_group: wave1-gr004
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-004
task_type: feature
title: Implement InteractiveCaptureSession
wave: 1
completed_at: 2026-02-01T13:15:00Z
test_results:
  total: 58
  passed: 58
  failed: 0
  coverage: 95
---

# Implement InteractiveCaptureSession

## Description

Create the `InteractiveCaptureSession` class that runs an interactive Q&A session to capture project knowledge from the user.

## Acceptance Criteria

- [x] `run_session(focus, max_questions, ui_callback)` executes Q&A flow
- [x] Presents questions from gap analysis
- [x] Supports skip ("s") and quit ("q") commands
- [x] Processes answers and extracts facts
- [x] Saves captured knowledge to Graphiti
- [x] Provides session summary with facts captured per category

## Technical Details

**Location**: `guardkit/knowledge/interactive_capture.py`

**Session Flow**:
1. Analyze gaps
2. Display intro
3. Ask questions (with skip/quit support)
4. Process answers → extract facts
5. Save to Graphiti
6. Display summary

**Reference**: See FEAT-GR-004 interactive session flow diagram.

## Implementation Summary

### Files Implemented
- `guardkit/knowledge/interactive_capture.py` (413 lines)

### Test Coverage
- `tests/knowledge/test_interactive_capture.py` (58 tests, 95% coverage)

### Key Components
1. **CapturedKnowledge dataclass** - Stores captured knowledge with category, question, answer, extracted facts
2. **InteractiveCaptureSession class** - Main session orchestrator
   - `run_session()` - Main entry point for Q&A flow
   - `_get_gaps()` - Delegates to KnowledgeGapAnalyzer
   - `_process_answer()` - Converts answers to CapturedKnowledge
   - `_extract_facts()` - Splits answers into sentences with category prefixes
   - `_save_captured_knowledge()` - Persists to Graphiti grouped by category
   - `_format_intro()` / `_format_summary()` - UI formatting helpers
