# ADR-SP-001: FalkorDB over Neo4j for Knowledge Graph

- **Date**: 2026-01
- **Status**: Accepted

## Context

Neo4j required 5GB+ Docker image, complex licensing, and heavy resource usage. FalkorDB is a lightweight Redis-compatible graph database.

## Decision

Migrate from Neo4j to FalkorDB for all Graphiti knowledge graph operations.

## Consequences

**Positive:**
- Smaller footprint (~500MB vs 5GB+)
- Redis-compatible (familiar ops)
- Runs on Synology NAS (low-resource environments)

**Negative:**
- Less mature ecosystem
- Required upstream workaround for single group_id search bug (two-layer monkey-patch)
