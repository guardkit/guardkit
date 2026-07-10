# Outcome-Label Sidecar (FEAT-0D1C)

## Problem

Outcome labels (`coach_correct` / `operator_caught` / `merge_review_caught` /
`live_gate_caught`) on autobuild evidence are today manual post-hoc joins from
retros and TASK-REV/TASK-FIX archaeology at every dataset harvest — gap **G6**
in the 2026-07-09 observability analysis. The backward-edge episode schema is
contract-pinned with zero producers wired; "outcome labels for free" is
aspiration, not mechanism.

## Solution

When a disposition lands, write a structured, append-only JSONL label record
adjacent to the `.guardkit/autobuild/{task_id}/` artifacts it judges:

- **One producer** (`guardkit/labels/writer.py`), consumed by a hybrid surface:
  automatic EXECUTE hooks in the three disposition markdown commands + a manual
  CLI (`guardkit label record`) for operator/live-gate labels.
- **Content-addressed `label_id`** (timestamp excluded) — retries idempotent,
  dedupe mechanical, matches the WS4-S1 content-addressing precedent.
- **9F43 identity join** — `run_id`/`attempt` resolved from `events.jsonl`
  (nullable; absent stays absent) so Chronicler rows correlate.
- **80FE archive-safe** — labels beside `events.jsonl` are swept by the shipped
  archiver for free; post-archival dispositions write to the D-OBS-4 archive
  home via the shared root resolver.
- **D-S10-1 consumer** — `guardkit label coverage` reports per-DC-class counts
  against the Coach v4 ≥10-per-class floor (DC-03/05/08/14).

Node-local, no fleet infra, observer-never-gate (all hooks non-blocking).

## Subtasks

| Wave | Task | Title | Cx |
|---|---|---|---|
| 1 | TASK-LBL-001 | Labels package: schema + label_id + append-only writer | 2 |
| 2 | TASK-LBL-002 | identity.py: absence-safe run_id/attempt resolver | 3 |
| 2 | TASK-LBL-003 | paths.py: live vs archive target resolver | 3 |
| 3 | TASK-LBL-004 | CLI: `guardkit label record` + `guardkit label coverage` | 4 |
| 4 | TASK-LBL-005 | Wire EXECUTE hooks into disposition commands | 2 |
| 4 | TASK-LBL-006 | Regression test suite | 3 |

## Consumers

- agentic-dataset-factory QAV/coach harvest transforms (join by file read)
- WS4-S7 Chronicler (correlates via run_id/attempt)

## References

- Review: `.claude/reviews/TASK-REV-3359-review-report.md`
- Spec: `features/outcome-label-sidecar/` (21 BDD scenarios, 7 resolved assumptions)
- Upstream: FEAT-OBSC (9F43 identity, 80FE archive seam), OBS-6 / gap G6,
  D-S10-1 (ai-transition ws4-s10 scope doc)
