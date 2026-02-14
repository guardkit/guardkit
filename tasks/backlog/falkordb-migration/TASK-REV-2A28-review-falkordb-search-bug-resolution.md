---
id: TASK-REV-2A28
title: Review FalkorDB search bug resolution research
status: review_complete
created: 2026-02-11T22:00:00Z
updated: 2026-02-11T22:00:00Z
priority: high
tags: [review, falkordb, graphiti, migration, upstream-bug]
task_type: review
parent_task: TASK-FKDB-001
feature_id: FEAT-FKDB-001
complexity: 3
---

# Task: Review FalkorDB search bug resolution research

## Description

Analyse the findings from extended thinking research (conducted in Claude Desktop) documented in `docs/reviews/graphiti-falkordb-migration/falkordb-search-bug-resolution.md`. This research was performed following the execution of TASK-FKDB-001, which validated FalkorDB + graphiti-core end-to-end and found a critical upstream bug: the second `add_episode()` call destroys all previously-indexed search data (AC-006 FAIL).

The research identifies three major FalkorDB-specific fixes shipped in graphiti-core v0.23.0–v0.23.1 that directly address the observed failure modes. The update to v0.24.3 should hopefully resolve the blocking issue.

## Context

### TASK-FKDB-001 Blocking Bug (AC-006)
- Second `add_episode()` destroys searchability of ALL previously-indexed data
- Only the most recently added episode's data remains searchable
- FalkorDB migration BLOCKED pending resolution

### Research Findings (falkordb-search-bug-resolution.md)
Three upstream fixes identified between the version tested (~v0.17.x) and v0.24.3:

1. **v0.23.0**: GraphID isolation (#835), fulltext search tests enabled (#1050), entity edge save fix pipeline
2. **v0.23.1**: Entity edge save bug fixed (PR #1013) — `source_node_uuid`/`target_node_uuid` were `None`
3. **group_ids filtering bug** (Issue #801) — still open but trivially worked around with explicit `group_ids=["_"]`

### Research Confidence Level
- HIGH CONFIDENCE that upgrade to v0.24.3 resolves the blocking bug
- Risk assessment: 20% chance bug still present, 15% group_ids workaround insufficient
- FalkorDB is now the DEFAULT backend for Graphiti MCP server (vote of confidence from Zep)

## Review Objectives

1. **Validate research methodology** — Are the identified PRs/issues genuinely relevant to our failure mode?
2. **Assess root cause mapping** — Do the 3 fixes (index rebuild, edge UUIDs, fulltext tests) map to our AC-006 symptoms?
3. **Evaluate re-validation plan** — Is the proposed test modification (explicit group_ids, sleep delays, search() vs search_()) sufficient?
4. **Risk assessment** — Is 20% residual risk acceptable? Are there unaddressed failure modes?
5. **Decide next action** — Approve re-validation (upgrade + re-run) or identify additional investigation needed

## Acceptance Criteria

- [ ] AC-001: Research methodology validated — PR/issue numbers verified as relevant to observed failure mode
- [ ] AC-002: Root cause mapping assessed — each of the 3 identified fixes evaluated against AC-006 symptoms
- [ ] AC-003: Re-validation plan reviewed — proposed script modifications are sufficient to test the fix
- [ ] AC-004: Risk assessment evaluated — residual risks identified and mitigations confirmed
- [ ] AC-005: Decision made — clear APPROVE/BLOCK/INVESTIGATE recommendation with rationale
- [ ] AC-006: Next steps documented — if approved, concrete action items for re-running TASK-FKDB-001 with v0.24.3

## Input Documents

- Research findings: `docs/reviews/graphiti-falkordb-migration/falkordb-search-bug-resolution.md`
- Original validation task: `tasks/backlog/falkordb-migration/TASK-FKDB-001-validate-falkordb-graphiti-core.md`
- Original review report: `.claude/reviews/TASK-REV-38BC-review-report.md`
- Memory context: `memory/falkordb-migration.md`

## Implementation Notes

This is a review task — use `/task-review TASK-REV-2A28` to execute.

The review should determine whether to:
1. **APPROVE re-validation**: Upgrade to v0.24.3 and re-run TASK-FKDB-001 with modified test script
2. **REQUEST additional research**: Identify gaps in the analysis that need investigation
3. **MAINTAIN BLOCK**: If the evidence is insufficient to justify re-testing
