# Feature Spec Summary: Outcome-Label Sidecar

**Stack**: python
**Generated**: 2026-07-10T12:13:06Z
**Scenarios**: 21 total (4 smoke, 2 regression)
**Assumptions**: 7 total (2 high / 3 medium / 2 low confidence — all 7 resolved interactively)
**Review required**: No

## Scope

When a TASK-REV / TASK-FIX / merge-review disposition lands, a structured, append-only
label record (task/feature ids, one of four verdict classes — `coach_correct` |
`operator_caught` | `merge_review_caught` | `live_gate_caught` — evidence reference,
timestamp, and the 9F43 `run_id`/`attempt` correlation identity) is written as a JSONL
sidecar adjacent to the `.guardkit/autobuild/{task_id}/` artifacts it judges, so dataset
harvests (agentic-dataset-factory QAV/coach transforms, WS4-S7 Chronicler) join labels by
file read instead of retro archaeology. Labels are node-local (no fleet infra), survive the
shipped 80FE archive-before-prune move (post-archival dispositions write to the D-OBS-4
archive home directly), and carry an optional `dc_class` so class coverage feeds the
Coach v4 ≥10-per-DC-class floor (DC-03/05/08/14) from D-S10-1. This is the OBS-6
"outcome labels for free" enabler closing gap G6 from the 07-09 observability analysis.

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 4 |
| Boundary conditions (@boundary) | 4 |
| Negative cases (@negative) | 7 |
| Edge cases (@edge-case) | 10 |

(Categories overlap: boundary/edge scenarios that assert refusal also carry @negative.)

## Key Design Resolutions (from assumption review)

- **Dedupe (ASSUM-006, human-decided)**: content-addressed `label_id` over
  (task_id, verdict_class, source_ref, dc_class), timestamp excluded — dedupe lives in
  the writer, not re-implemented per consumer; matches the WS4-S1 content-addressed
  row-id precedent.
- **Writer surface (ASSUM-007, human-decided)**: hybrid — automatic writes from
  disposition commands plus a manual CLI for `operator_caught` / `live_gate_caught`.
  Riders: an explicit disposition-source → verdict-class mapping table, and both
  surfaces routing through one shared writer module
  (per `.claude/rules/cli-wrapper-shares-client-acquisition-path.md`).
- **Non-blocking posture**: label writes are observers, never gates — a failed write
  warns and lets the disposition complete (live and archive-home variants both pinned).

## Deferred Items

None. All four proposal groups accepted; the 6-scenario edge-case expansion
(security / data integrity / integration boundaries) accepted in full.

## Open Assumptions (low confidence)

None outstanding. ASSUM-006 and ASSUM-007 were proposed at low confidence but both
were resolved by explicit human decision during Phase 5 (see `human_response` in
`outcome-label-sidecar_assumptions.yaml`).

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "Outcome-Label Sidecar" --context features/outcome-label-sidecar/outcome-label-sidecar_summary.md
