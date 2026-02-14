---
id: TASK-FKDB-004
title: FalkorDB Docker Compose configuration
status: completed
completed: 2026-02-11T21:25:00Z
created: 2026-02-11T17:00:00Z
updated: 2026-02-11T21:25:00Z
previous_state: in_review
priority: high
tags: [falkordb, docker, infrastructure, migration]
parent_review: TASK-REV-38BC
feature_id: FEAT-FKDB-001
implementation_mode: direct
wave: 1
complexity: 2
depends_on:
  - TASK-FKDB-001
---

# Task: FalkorDB Docker Compose configuration

## Description

Update `docker/docker-compose.graphiti.yml` to use FalkorDB instead of Neo4j. Keep the file name unchanged for backwards compatibility.

## Acceptance Criteria

- [x] AC-001: Docker Compose uses `falkordb/falkordb:latest` image
- [x] AC-002: Ports mapped: 6379 (Redis/FalkorDB), 3000 (FalkorDB Browser)
- [x] AC-003: Health check uses `redis-cli ping`
- [x] AC-004: Volume `falkordb_data` for persistence
- [x] AC-005: APOC plugin reference removed
- [x] AC-006: Comments updated (no Neo4j references in active config)
- [x] AC-007: `docker compose up -d` starts FalkorDB successfully

## Files to Modify

- `docker/docker-compose.graphiti.yml` — Replace Neo4j service with FalkorDB

## Implementation Notes

Replace the current Neo4j service with:
```yaml
services:
  falkordb:
    image: falkordb/falkordb:latest
    container_name: guardkit-falkordb
    ports:
      - "6379:6379"   # Redis protocol (FalkorDB connection)
      - "3000:3000"   # FalkorDB Browser UI
    volumes:
      - falkordb_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - guardkit-knowledge
```
