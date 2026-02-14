---
id: TASK-REV-1294
title: Review add-context output for FalkorDB errors and unsupported parsers
status: review_complete
created: 2026-02-13T00:00:00Z
updated: 2026-02-13T00:00:00Z
priority: high
tags: [review, falkordb, graphiti, add-context]
task_type: review
complexity: 0
review_results:
  mode: technical
  depth: standard
  findings_count: 4
  recommendations_count: 9
  report_path: .claude/reviews/TASK-REV-1294-review-report.md
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review add-context output for FalkorDB errors and unsupported parsers

## Description

Analyse the output from `guardkit graphiti add-context docs/architecture/` captured in `docs/reviews/system-plan-overview/add-context output.md`. The run completed but exhibited multiple issues that need investigation and remediation.

## Source Output

`docs/reviews/system-plan-overview/add-context output.md` (640 lines)

## Observed Issues

### 1. FalkorDB "Max pending queries exceeded" Errors (P0)
- **6 ERROR-level** occurrences from `graphiti_core.driver.falkordb_driver`
- **2 WARNING-level** occurrences from `guardkit.knowledge.graphiti_client` (episode creation failed)
- Errors occur during edge search queries (both full-text and vector cosine similarity)
- Despite errors, the affected files still show `✓` success — investigate whether episodes were actually persisted or silently dropped
- Root cause: FalkorDB query queue saturation — may need rate limiting, connection pooling, or sequential processing

### 2. Unsupported File Types (P1)
- **20 files** skipped with "No parser found" — all are generic `.md` files
- Only `adr` parser exists; no parser for generic architecture docs, design docs, implementation checklists, etc.
- Skipped files include critical architecture docs: `ARCHITECTURE.md`, `components.md`, `guardkit-system-spec.md`, `quality-gate-pipeline.md`, `system-context.md`, `failure-patterns.md`
- These contain valuable project knowledge that should be ingested

### 3. Missing ADR "Status" Section Warnings (P2)
- All 8 successfully processed ADRs have warning: "Missing required section: Status"
- ADR files in `docs/architecture/decisions/` lack a `## Status` section
- Either: (a) add Status sections to ADRs, or (b) make Status section optional in the ADR parser

### 4. Excessive Index-Already-Exists Log Noise (P3)
- ~30 lines of `INFO:graphiti_core.driver.falkordb_driver:Index already exists` at startup
- Not harmful but clutters output — consider suppressing or logging at DEBUG level

## Acceptance Criteria

- [ ] AC-001: Determine whether episodes marked `✓` despite preceding errors were actually persisted to FalkorDB
- [ ] AC-002: Identify root cause of "Max pending queries exceeded" and recommend fix (rate limiting, backoff, sequential mode, connection pool tuning)
- [ ] AC-003: Catalogue all unsupported file types and assess which need new parsers (generic markdown, design docs, checklists)
- [ ] AC-004: Recommend approach for ADR Status section warnings (fix ADRs vs make parser lenient)
- [ ] AC-005: Assess log noise reduction options for index-already-exists messages
- [ ] AC-006: Produce review report with prioritised recommendations

## Review Focus Areas

1. **Data integrity** — Were all 9 episodes actually stored? Query FalkorDB to verify.
2. **Rate limiting** — Does `add-context` fire concurrent queries? Should it throttle?
3. **Parser coverage** — What's the effort to add a generic markdown parser?
4. **ADR template** — Should the ADR template in `docs/architecture/decisions/` include a Status section?

## Implementation Notes

Review task — analysis only, no code changes.
Output: Review report at `.claude/reviews/TASK-REV-1294-review-report.md`

## Test Execution Log
[Automatically populated by /task-work]
