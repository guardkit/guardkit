---
id: TASK-FIX-ASPF-006
title: Enhance synthetic report with requirements inference
status: in_progress
updated: 2026-02-25T00:00:00Z
previous_state: backlog
state_transition_reason: "Automatic transition for task-work execution"
task_type: implementation
created: 2026-02-24T23:00:00Z
priority: medium
tags: [synthetic-report, criteria-pipeline, requirements]
complexity: 6
parent_review: TASK-REV-953F
feature_id: FEAT-ASPF
wave: 3
implementation_mode: task-work
dependencies: [TASK-FIX-ASPF-005]
---

# Task: Enhance synthetic report with requirements inference

## Description

Currently `build_synthetic_report()` in `synthetic_report.py` hardcodes `requirements_addressed: []`. This means synthetic reports can never verify content-based criteria (e.g., "Settings class has log_level field") — only file-existence promises.

Enhance the synthetic report builder to infer requirements from available evidence.

## Current Behavior

```python
# synthetic_report.py:91
"requirements_addressed": []  # Always empty
```

## Possible Enhancement Strategies

### Strategy A: Test Output Matching
Parse test output (if available) and match test names/descriptions against acceptance criteria text.

### Strategy B: File Content Grep
For content-based criteria like "Settings class has log_level field", grep the created/modified files for keywords from the criterion.

### Strategy C: Git Diff Analysis
Analyze the git diff to extract what was added/changed and match against criteria.

### Strategy D: Coach Text Matching on Synthetic Path
Allow the Coach to use text matching as a fallback even on synthetic reports. This would require modifying `coach_validator.py:1506-1550` to add a text fallback after promise matching fails.

## Design Considerations

- False positives are worse than false negatives (approving unmet criteria)
- Strategy D is the simplest and lowest risk
- Strategies A-C require careful threshold tuning
- This task depends on P5 findings — if vLLM report production is fixed, this becomes lower priority

## Acceptance Criteria

1. Synthetic reports can verify at least some content-based criteria
2. False positive rate is acceptably low (no criteria approved without evidence)
3. Existing synthetic report tests still pass
4. New tests for enhanced inference

## Files to Modify

- `guardkit/orchestrator/synthetic_report.py` — `build_synthetic_report()` (Strategies A-C)
- `guardkit/orchestrator/quality_gates/coach_validator.py` — `validate_requirements()` synthetic path (Strategy D)
