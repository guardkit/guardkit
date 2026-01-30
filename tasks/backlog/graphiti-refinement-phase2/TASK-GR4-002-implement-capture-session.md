---
id: TASK-GR4-002
title: Implement InteractiveCaptureSession
status: backlog
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-004
wave: 1
parallel_group: wave1-gr004
implementation_mode: task-work
complexity: 5
estimate_hours: 3
dependencies:
  - TASK-GR4-001
---

# Implement InteractiveCaptureSession

## Description

Create the `InteractiveCaptureSession` class that runs an interactive Q&A session to capture project knowledge from the user.

## Acceptance Criteria

- [ ] `run_session(focus, max_questions, ui_callback)` executes Q&A flow
- [ ] Presents questions from gap analysis
- [ ] Supports skip ("s") and quit ("q") commands
- [ ] Processes answers and extracts facts
- [ ] Saves captured knowledge to Graphiti
- [ ] Provides session summary with facts captured per category

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
