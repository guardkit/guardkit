---
id: TASK-G0A7-001
title: Token bucket in internal/ratelimit
task_type: feature
feature_id: FEAT-G0A7
complexity: 4
dependencies: []
---

Add a token bucket type to `internal/ratelimit/bucket.go`.

## Acceptance Criteria

- `bucket.Allow()` returns false once the per-minute allowance is used
- `go test ./internal/ratelimit/...` passes
