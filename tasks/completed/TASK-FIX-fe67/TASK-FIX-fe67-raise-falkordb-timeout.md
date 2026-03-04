---
id: TASK-FIX-fe67
title: Raise FalkorDB TIMEOUT to 30000ms
status: completed
completed: 2026-03-04T00:00:00Z
updated: 2026-03-04T00:00:00Z
task_type: implementation
created: 2026-03-04T00:00:00Z
priority: critical
tags: [falkordb, configuration, docker, nas]
complexity: 1
parent_review: TASK-REV-1F78
feature_id: FEAT-falkordb-timeout-fixes
wave: 1
implementation_mode: direct
dependencies: []
completed_location: tasks/completed/TASK-FIX-fe67/
---

# Task: Raise FalkorDB TIMEOUT to 30000ms

## Description

Update the FalkorDB Docker Compose configuration on the NAS to raise the query execution timeout from 1000ms (1 second) to 30000ms (30 seconds). The current 1s timeout is far too low for graphiti-core's queries, even after the O(n×m) fix is applied.

## Current Configuration

`docker/nas/docker-compose.falkordb.yml` line 55:
```yaml
FALKORDB_ARGS=MAX_QUEUED_QUERIES 100 TIMEOUT 1000 RESULTSET_SIZE 10000
```

## Target Configuration

```yaml
FALKORDB_ARGS=MAX_QUEUED_QUERIES 100 TIMEOUT 30000 RESULTSET_SIZE 10000
```

## Why 30000ms

- The `GraphitiConfig.timeout` default is 30.0 seconds
- Aligns FalkorDB server-side timeout with client-side timeout
- Provides safety margin for heavy graph operations (community building, etc.)
- Per FalkorDB docs: TIMEOUT applies to read queries only; write queries don't timeout

## Files Modified

- `docker/nas/docker-compose.falkordb.yml` — TIMEOUT 1000 → 30000
- `docker/docker-compose.graphiti.yml` — added FALKORDB_ARGS with TIMEOUT 30000

## Deployment Steps

1. ~~Update docker-compose files~~ DONE
2. SSH to NAS: `ssh richardwoollcott@whitestocks`
3. Redeploy: `cd /volume1/guardkit/docker && sudo docker-compose -f docker-compose.falkordb.yml up -d`
4. Verify: `redis-cli -h whitestocks GRAPH.CONFIG GET TIMEOUT`

## Acceptance Criteria

- [x] NAS docker-compose updated with TIMEOUT 30000
- [x] Local dev docker-compose updated for parity
- [ ] FalkorDB redeployed on NAS (manual step)
- [ ] `redis-cli GRAPH.CONFIG GET TIMEOUT` returns 30000 (post-deploy verification)
