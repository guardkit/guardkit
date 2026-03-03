---
id: TASK-IGR-004
title: Increase FalkorDB MAX_QUEUED_QUERIES on Synology
status: completed
created: 2026-03-03T00:00:00Z
updated: 2026-03-03T00:00:00Z
completed: 2026-03-03T00:00:00Z
priority: high
complexity: 1
tags: [infrastructure, falkordb, synology]
parent_review: TASK-REV-21D3
feature_id: FEAT-IGR
wave: 1
implementation_mode: direct
dependencies: []
completed_location: tasks/completed/TASK-IGR-004/
organized_files:
  - TASK-IGR-004-falkordb-max-queued-queries.md
---

# Task: Increase FalkorDB MAX_QUEUED_QUERIES on Synology

## Description

Increase the `MAX_QUEUED_QUERIES` setting on the Synology FalkorDB container to handle graphiti-core's parallel query pattern during seeding.

## Context

The default `MAX_QUEUED_QUERIES` limit (typically 25) is exceeded when graphiti-core fires concurrent edge-scoring queries during `add_episode()`. This caused episode 3 to fail permanently during `guardkit init`.

## Implementation

1. SSH to Synology
2. Update FalkorDB container environment: `MAX_QUEUED_QUERIES=100` (or equivalent config)
3. Restart the FalkorDB container
4. Verify with a test seeding run

## What Was Done

Updated `docker/nas/docker-compose.falkordb.yml` to add the `FALKORDB_ARGS` environment variable:

```yaml
environment:
  - FALKORDB_ARGS=MAX_QUEUED_QUERIES 100 TIMEOUT 1000 RESULTSET_SIZE 10000
```

- The FalkorDB Docker image default is `MAX_QUEUED_QUERIES 25` (set via `FALKORDB_ARGS` env var in the image Dockerfile)
- Increased to 100 to handle graphiti-core's parallel edge-scoring queries during `add_episode()`
- Preserved other FalkorDB defaults: `TIMEOUT 1000`, `RESULTSET_SIZE 10000`

### Deployment Steps

```bash
# Copy updated compose file to NAS
scp ~/Projects/appmilla_github/guardkit/docker/nas/docker-compose.falkordb.yml \
    richardwoollcott@whitestocks:/volume1/guardkit/docker/docker-compose.falkordb.yml

# SSH and restart
ssh richardwoollcott@whitestocks
cd /volume1/guardkit/docker
sudo docker-compose -f docker-compose.falkordb.yml up -d

# Verify
redis-cli -h whitestocks -p 6379 GRAPH.CONFIG GET MAX_QUEUED_QUERIES
# Expected: MAX_QUEUED_QUERIES 100
```

## Acceptance Criteria

- [x] FalkorDB container has increased `MAX_QUEUED_QUERIES` setting (docker-compose updated)
- [ ] No "Max pending queries exceeded" errors during a full `guardkit init` seeding run (pending deployment)

## Effort Estimate

~15 minutes
