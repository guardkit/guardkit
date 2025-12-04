---
id: TASK-FW-007
title: Create README.md generator for features
status: backlog
created: 2025-12-04T11:00:00Z
updated: 2025-12-04T11:00:00Z
priority: medium
tags: [feature-workflow, documentation, generator]
complexity: 3
implementation_mode: direct
parallel_group: 1
conductor_workspace: feature-workflow-1
parent_review: TASK-REV-FW01
---

# Create README.md Generator for Features

## Description

Generate a README.md file for each feature subfolder, providing documentation of scope, decisions, and structure.

## Acceptance Criteria

- [ ] Generate README.md with feature overview
- [ ] Include problem statement from review
- [ ] Include solution summary
- [ ] Include scope (in/out)
- [ ] Include success criteria
- [ ] Include links to related documents
- [ ] Include subtask summary

## Implementation Details

### Template Structure

```markdown
# Feature: {Feature Name}

## Overview

{Brief description from review findings}

**Parent Review**: [TASK-REV-XXXX](../TASK-REV-XXXX.md)
**Review Report**: [.claude/reviews/TASK-REV-XXXX-review-report.md](...)

## Problem Statement

{Extracted from review - what problem does this solve?}

## Solution

{High-level solution approach from recommendations}

## Scope

### In Scope
{List of what's included}

### Out of Scope
{List of what's excluded/deferred}

## Success Criteria

{List of measurable success criteria}

## Subtasks

| ID | Title | Method | Status |
|----|-------|--------|--------|
{subtask rows}

## Related Documents

{Links to research docs, ADRs, etc.}
```

### Generator Function

```python
def generate_feature_readme(
    feature_name: str,
    feature_slug: str,
    review_task_id: str,
    review_report_path: str,
    subtasks: list[dict],
    output_path: str
) -> str:
    """
    Generate README.md for feature subfolder.

    Extracts key sections from review report:
    - Problem statement
    - Solution approach
    - Scope
    - Success criteria
    """
```

### Content Extraction

Parse review report for:
- Executive Summary → Overview
- Findings → Problem Statement
- Recommendations → Solution
- Scope section if present
- Acceptance criteria if present

## Files to Create/Modify

- `installer/global/lib/readme_generator.py` (NEW)

## Test Cases

1. Generate README from complete review report
2. Handle missing optional sections gracefully
3. Correctly link to parent review task
4. Correctly link to review report

## Dependencies

None - simple template generation.

## Notes

Low complexity (3) - straightforward template filling.
Can run in parallel with FW-001, FW-002 (Wave 1).
