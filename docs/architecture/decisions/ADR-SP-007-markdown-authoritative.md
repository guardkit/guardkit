# ADR-SP-007: Markdown Authoritative, Graphiti Queryable

- **Date**: 2026-01
- **Status**: Accepted

## Context

Architecture knowledge needs to be both human-readable and machine-queryable. Duplicating content creates drift.

## Decision

Markdown files in docs/ are the authoritative source of truth. Graphiti stores semantic facts extracted from those documents, providing queryability. Never duplicate -- if it's authoritative in markdown, Graphiti provides a reference/summary, not the full content.

## Consequences

**Positive:**
- Single source of truth
- Human-editable architecture docs
- Machine-queryable context

**Negative:**
- Requires re-ingestion when markdown changes
- Graphiti facts may lag behind markdown edits
