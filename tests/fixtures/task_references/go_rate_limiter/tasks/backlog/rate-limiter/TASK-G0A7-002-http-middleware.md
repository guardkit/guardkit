---
id: TASK-G0A7-002
title: HTTP middleware
task_type: feature
feature_id: FEAT-G0A7
complexity: 3
dependencies:
  - TASK-G0A7-001
---

Wrap the router in `cmd/api/main.go` with a middleware that uses the bucket.

## Acceptance Criteria

- Requests over the allowance get `429 Too Many Requests`
- Reads the per-client limit from the `Limits` struct added by TASK-G0A7-003
