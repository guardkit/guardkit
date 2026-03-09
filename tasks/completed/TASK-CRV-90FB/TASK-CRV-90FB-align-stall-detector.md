---
id: TASK-CRV-90FB
title: Align stall detector criteria count with Coach validator
status: completed
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T00:00:00Z
completed: 2026-03-09T00:00:00Z
priority: low
tags: [stall-detection, coach, criteria-count, alignment]
task_type: feature
parent_review: TASK-REV-3F40
feature_id: FEAT-8290
wave: 2
implementation_mode: task-work
complexity: 2
dependencies: []
---

# Task: Align stall detector criteria count with Coach validator

## Description

The stall detector reported "2 criteria passing" while the Coach consistently reported 0/3 verified from turn 3 onwards in the FEAT-2AAA run. This discrepancy suggests they use different counting sources. The stall detector may be counting `requirements_addressed` inferred by the synthetic report, while the Coach uses its own verification pipeline.

Align both to use the same verified criteria count from the Coach's actual decision.

## Acceptance Criteria

- [x] Stall detector's criteria count sourced from Coach validator's actual verified count (not synthetic report inference)
- [x] Stall detection log message accurately reflects Coach's verified/total ratio
- [x] Extended stall threshold (for partial progress) only triggers when Coach reports genuine progress
- [x] Existing stall detection tests continue to pass
- [x] New test verifying count alignment between stall detector and Coach

## Implementation Notes

Search for where the stall detector gets its criteria count (likely in `autobuild.py` or `state_detection.py`) and replace with the Coach's actual `criteria_met` / `total_criteria` from the `CoachValidationResult`.

## Files to Modify

- `guardkit/orchestrator/autobuild.py` (stall detection section)
- `guardkit/orchestrator/state_detection.py` (if stall logic lives here)
- Relevant test files
