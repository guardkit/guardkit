---
id: TASK-REV-3359
title: "Plan: Outcome-Label Sidecar"
status: review_complete
created: 2026-07-10T12:13:06Z
updated: 2026-07-10T12:35:00Z
review_results:
  mode: decision
  depth: standard
  score: 88
  findings_count: 6
  recommendations_count: 6
  decision: implement
  feature_id: FEAT-0D1C
  report_path: .claude/reviews/TASK-REV-3359-review-report.md
priority: high
task_type: review
tags: [observability, dataset-harvest, obs-6, planning]
complexity: 0
decision_required: true
context_files:
  - features/outcome-label-sidecar/outcome-label-sidecar_summary.md
  - features/outcome-label-sidecar/outcome-label-sidecar.feature
  - features/outcome-label-sidecar/outcome-label-sidecar_assumptions.yaml
clarification:
  context_a:
    timestamp: 2026-07-10T12:13:06Z
    decisions:
      focus: architecture
      tradeoff: maintainability
      concerns:
        - archive-seam-correctness
        - writer-integration-points
        - consumer-contract-stability
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Plan: Outcome-Label Sidecar

## Description

Plan the OBS-6 outcome-label sidecar: when a TASK-REV / TASK-FIX / merge-review
disposition lands, write a structured, append-only JSONL label record (task/feature
ids, verdict class — `coach_correct` | `operator_caught` | `merge_review_caught` |
`live_gate_caught` — evidence-dir reference, timestamp, 9F43 `run_id`/`attempt`
identity, content-addressed `label_id`, optional `dc_class`) adjacent to the
corresponding `.guardkit/autobuild/{task_id}/` artifacts, so dataset harvests
(agentic-dataset-factory QAV/coach transforms, WS4-S7 Chronicler) join labels by
file read instead of retro archaeology.

Closes gap G6 from the 2026-07-09 observability analysis ("outcome labels for
free"). Node-local, append-only, no fleet infra.

**Riders:**
- Reconcile placement with the SHIPPED 80FE archive-before-prune seam
  (`guardkit/worktrees/archive.py`, hooked at `WorktreeManager.cleanup`): labels
  written adjacent to live artifacts must survive the archive move; dispositions
  landing post-archival write to the D-OBS-4 archive home directly.
- Labels join the 9F43 `run_id`/`attempt` identity fields so Chronicler rows correlate.
- Consume the D-S10-1 trigger taxonomy: label class-coverage feeds the Coach v4
  ≥10-per-DC-class floor (DC-03/05/08/14).

**Resolved design decisions (from /feature-spec Phase 5):**
- ASSUM-006: content-addressed `label_id` over (task_id, verdict_class, source_ref,
  dc_class), timestamp excluded — dedupe centralized in the writer.
- ASSUM-007: hybrid writer surface — automatic disposition-command writes + manual
  CLI for `operator_caught`/`live_gate_caught`; explicit disposition→class mapping
  table; both surfaces route through ONE shared writer module (per
  `.claude/rules/cli-wrapper-shares-client-acquisition-path.md`).

## Review Scope (Context A)

- **Focus**: architecture (placement/seam decisions dominate)
- **Trade-off priority**: maintainability (dataset-integrity seam with two external consumers)
- **Specific concerns**: archive-seam correctness; writer integration points; consumer contract stability

## Acceptance Criteria (for the review)

- [ ] Technical options analysed for writer-module placement and archive-seam reconciliation
- [ ] Recommended approach with task breakdown, waves, and complexity scores
- [ ] Decision checkpoint presented (Accept/Revise/Implement/Cancel)

## Source Specification

BDD spec: `features/outcome-label-sidecar/` (21 scenarios, 7 resolved assumptions,
no open low-confidence items). See summary for scenario counts and key design
resolutions.
