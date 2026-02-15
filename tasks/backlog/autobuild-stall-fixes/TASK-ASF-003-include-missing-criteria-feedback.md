---
id: TASK-ASF-003
title: Include missing_criteria in Coach feedback text
task_type: bugfix
parent_review: TASK-REV-SFT1
feature_id: FEAT-ASF
wave: 2
implementation_mode: task-work
complexity: 3
dependencies:
  - TASK-ASF-001
  - TASK-ASF-002
priority: high
status: backlog
tags: [autobuild, stall-fix, R3, phase-2, feedback-loop]
---

# Task: Include missing_criteria in Coach feedback text

## Description

The `_extract_feedback()` method in `autobuild.py` currently extracts only the generic `issues[].description` field ("Not all acceptance criteria met") while discarding the specific `rationale` and `missing_criteria` that contain actionable details. This means the Player receives no information about *which* criteria are missing, leading to blind retries and eventual stall.

This is the **highest-impact fix** — the diagnostic integration contract diagram (Diagram 9) shows this is a lossy data contract between Coach and Player.

## Root Cause Addressed

- **F4**: Coach feedback text extraction loses specificity (`autobuild.py:3124-3141`)

## Current Behavior

```python
# autobuild.py:3124-3141
issues = coach_report.get("issues", [])
if not issues:
    return coach_report.get("rationale", "No specific feedback provided")
# When issues exist, rationale is NEVER used:
for issue in issues[:3]:
    desc = issue.get("description", "")  # = "Not all acceptance criteria met"
    feedback_lines.append(f"- {desc}")   # Generic line
```

Player receives: `"- Not all acceptance criteria met"`

## Proposed Fix

```python
# autobuild.py:3124-3146 (modified)
issues = coach_report.get("issues", [])
if not issues:
    return coach_report.get("rationale", "No specific feedback provided")

for issue in issues[:3]:
    desc = issue.get("description", "")
    missing = issue.get("missing_criteria", [])
    if missing:
        feedback_lines.append(f"- {desc}:")
        for criterion in missing[:5]:
            feedback_lines.append(f"  • {criterion[:100]}")
        if len(missing) > 5:
            feedback_lines.append(f"  ({len(missing) - 5} more)")
    else:
        suggestion = issue.get("suggestion", "")
        feedback_lines.append(f"- {desc}")
        if suggestion:
            feedback_lines.append(f"  Suggestion: {suggestion}")
```

Player receives:
```
- Not all acceptance criteria met:
  • Create tests/seam/ directory
  • Add conftest.py with 4 fixtures
  • Register seam pytest marker
  (5 more)
```

## Files to Modify

1. `guardkit/orchestrator/autobuild.py` — Modify `_extract_feedback()` (~line 3124)

## Acceptance Criteria

- [ ] `_extract_feedback()` includes `missing_criteria` items when present in issue
- [ ] Each missing criterion is truncated to 100 chars to avoid prompt bloat
- [ ] Maximum 5 criteria listed with "(N more)" overflow
- [ ] When `missing_criteria` is empty, falls back to `description` + `suggestion` (current behavior)
- [ ] Existing tests for `_extract_feedback()` updated
- [ ] Stall detection MD5 hash will now differ across turns with different missing criteria (desirable)

## Regression Risk

**Low** — Only changes the text content of feedback passed to the Player. The Coach's validation logic, decision-making, and stall detection control flow are unaffected. The MD5 hash used for stall detection will change (different feedback text per set of missing criteria), which is desirable — stalls only trigger when the same *specific* criteria are stuck.

## Interaction Notes

- **With R4-lite (TASK-ASF-004)**: These are independent changes. R3 changes feedback text; R4-lite adds logging. No interaction risk.
- **Stall detector impact**: Stall detection uses `MD5(feedback_text)`. With specific criteria in the text, the hash changes when different criteria are missing. This *improves* stall detection accuracy — identical feedback now genuinely means the same problem persists.

## Reference

- Review report: `.claude/reviews/TASK-REV-SFT1-review-report.md` (Finding 4, Recommendation R3)
- Diagnostic diagrams: `docs/reviews/feature-build/autobuild-diagnostic-diagrams.md` (Diagram 4, Diagram 9)
