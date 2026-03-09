---
id: TASK-RFX-C9D9
title: Deprioritise TASK-CRV-B275 and TASK-CRV-7DBC
status: backlog
task_type: implementation
created: 2026-03-09T16:00:00Z
updated: 2026-03-09T16:00:00Z
priority: low
complexity: 1
wave: 1
implementation_mode: direct
parent_review: TASK-REV-A8C6
feature_id: FEAT-RFX
tags: [housekeeping, coach-runtime-verification]
dependencies: []
---

# Task: Deprioritise TASK-CRV-B275 and TASK-CRV-7DBC

## Description

Update the priority of TASK-CRV-B275 (Rate limit detection) and TASK-CRV-7DBC (MCP Coach integration) to low priority based on the TASK-REV-A8C6 review findings.

## Rationale

- **TASK-CRV-B275**: No rate limit errors observed in any autobuild run (Run 2 or Run 3). This is a defensive improvement with no evidence of current need.
- **TASK-CRV-7DBC**: Depends on TASK-CRV-9914 which itself depends on other work. Long dependency chain; MCP integration is a future capability not needed for current autobuild reliability.

## Acceptance Criteria

- [ ] TASK-CRV-B275 priority updated to low in frontmatter
- [ ] TASK-CRV-7DBC priority updated to low in frontmatter
- [ ] CRV README updated to reflect deprioritisation with rationale
