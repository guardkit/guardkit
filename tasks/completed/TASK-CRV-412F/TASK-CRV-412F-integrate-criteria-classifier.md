---
id: TASK-CRV-412F
title: Integrate criteria classifier into Coach validation pipeline
status: completed
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T00:00:00Z
completed: 2026-03-09T00:00:00Z
completed_location: tasks/completed/TASK-CRV-412F/
priority: high
tags: [coach, criteria-classifier, verification, autobuild]
task_type: feature
parent_review: TASK-REV-3F40
feature_id: FEAT-8290
wave: 1
implementation_mode: task-work
complexity: 3
dependencies: []
---

# Task: Integrate criteria classifier into Coach validation pipeline

## Description

Integrate the existing criteria classifier POC (`guardkit/orchestrator/quality_gates/criteria_classifier.py`) into the Coach validation pipeline in `coach_validator.py`. The classifier categorizes acceptance criteria as `file_content`, `command_execution`, or `manual`, enabling the Coach to route verification through the appropriate path.

Currently, all criteria go through the same text-matching pipeline. After this change, the Coach will:
1. Classify all criteria before validation
2. Route `file_content` criteria through existing Path A/B/C **unchanged**
3. Route `command_execution` criteria through new Path D (TASK-CRV-537E)
4. Skip or flag `manual` criteria as unverifiable

**Critical design constraint**: The classifier must act as a **routing layer on top of** the existing verification paths, NOT a replacement. All `file_content` criteria must continue to flow through the existing promise/hybrid/text matching paths exactly as before. The classifier defaults to `file_content` at confidence 0.3, which is conservative by design — a false positive (file_content classified as command_execution) is far less dangerous than the reverse.

## Acceptance Criteria

- [ ] `classify_acceptance_criteria()` called at start of `validate_requirements()` in `coach_validator.py`
- [ ] `file_content` criteria routed through existing promise/hybrid/text matching paths **with zero behaviour change** — existing Path A/B/C logic untouched
- [ ] `command_execution` criteria excluded from text-matching verification (to be verified by TASK-CRV-537E)
- [ ] `manual` criteria logged as skipped and not counted against verification threshold
- [ ] Classification is a **routing layer on top**, not a replacement — if classifier is disabled or errors, all criteria fall through to existing paths as before
- [ ] Classification results logged at DEBUG level for diagnostics
- [ ] Existing tests in `tests/unit/test_coach_validator.py` continue to pass with **identical results** (regression check)
- [ ] New test verifying classification routing in Coach pipeline
- [ ] New test verifying graceful fallback when classifier raises an exception

## Implementation Notes

Integration point is `validate_requirements()` at line 1739 of `coach_validator.py`. The classification should happen before the matching loop, and the results should be used to partition criteria into separate verification paths.

```python
from guardkit.orchestrator.quality_gates.criteria_classifier import (
    classify_acceptance_criteria,
    CriterionType,
)

# At start of validate_requirements():
classification = classify_acceptance_criteria(acceptance_criteria)

# Route file_content through existing matching
file_criteria = [c.text for c in classification.file_content_criteria]
# command_execution criteria handled separately (by orchestrator or Path D)
cmd_criteria = classification.command_criteria
# manual criteria flagged
for c in classification.manual_criteria:
    logger.debug("Skipping manual criterion: %s", c.text[:80])
```

## Files to Modify

- `guardkit/orchestrator/quality_gates/coach_validator.py` (primary)
- `tests/unit/test_coach_validator.py` (add routing test)
