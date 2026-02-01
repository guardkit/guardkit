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
status: design_approved
sub_feature: GR-004
task_type: feature
title: Implement InteractiveCaptureSession
wave: 1
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