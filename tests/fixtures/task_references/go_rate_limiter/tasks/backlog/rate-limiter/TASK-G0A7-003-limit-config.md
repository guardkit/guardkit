---
id: TASK-G0A7-003
title: Limit configuration
task_type: declarative
feature_id: FEAT-G0A7
complexity: 2
dependencies:
  - TASK-G0A7-001
---

Add a `Limits` struct to `internal/config/limits.go`, loaded from `config.yaml`.

## Acceptance Criteria

- `Limits.PerMinute` defaults to 60
- `go vet ./...` reports nothing
