---
id: TASK-ILCT-005
title: Standardise installer template display
status: completed
completed: 2026-04-03T23:45:00Z
created: 2026-04-03T23:15:00Z
priority: medium
tags: [installer, display, confidence-score]
parent_review: TASK-REV-81AA
feature_id: FEAT-ILCT
implementation_mode: task-work
wave: 2
complexity: 3
depends_on:
  - TASK-ILCT-001
  - TASK-ILCT-002
  - TASK-ILCT-004
---

# Task: Standardise installer template display

## Description

The template listing in `install.sh` (lines 1646-1692) has several display inconsistencies. This task standardises the output so all templates show descriptions and confidence ratings in a consistent format.

## Changes Required

### 1. Add score label to header (line 1646)

Change:
```bash
echo -e "${BOLD}Available Templates:${NC}"
```
To:
```bash
echo -e "${BOLD}Available Templates${NC} (confidence = AI analysis accuracy)${BOLD}:${NC}"
```

### 2. Filter `common` template from display

The `common` directory contains only internal infrastructure (graphiti template file), not a user-facing project template. Add a case for it that outputs nothing:

```bash
common)
    # Internal template, not user-facing
    ;;
```

### 3. Standardise score format to `(confidence: X/10)`

Update all template lines to use consistent format. Current mix:
- `(9+/10)` — bare number
- `(7.0/10)` — bare decimal

Target format: `(confidence: 9+/10)` or `(confidence: 7.0/10)`

### 4. Add scores to missing templates

- `fastmcp-python`: Add `(confidence: 9.0/10)` — manifest has 90
- `mcp-typescript`: Add `(confidence: 8.8/10)` — after TASK-ILCT-004 adds score

### 5. Update nats and orchestrator scores after enrichment

After TASK-ILCT-001 and TASK-ILCT-002 complete, update the hardcoded scores to reflect improved confidence.

### 6. Add source comment

Add comment above the case statement:
```bash
# Confidence scores sourced from installer/core/templates/*/manifest.json → confidence_score
# Update these when running template-validate or template-create
```

## Acceptance Criteria

- [x] Header includes score label explanation
- [x] `common` template filtered from display
- [x] All user-facing templates show `(confidence: X/10)` format
- [x] fastmcp-python and mcp-typescript show confidence scores
- [x] Source comment added above case statement
- [x] install.sh remains valid bash

## References

- Installer: `installer/scripts/install.sh` lines 1646-1692
- Review report: `.claude/reviews/TASK-REV-81AA-review-report.md` (Findings 9, 10, 11)
