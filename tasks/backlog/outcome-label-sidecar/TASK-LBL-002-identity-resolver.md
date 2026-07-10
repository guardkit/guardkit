---
id: TASK-LBL-002
title: "identity.py: absence-safe run_id/attempt resolver over events.jsonl"
status: backlog
created: 2026-07-10T12:40:00Z
updated: 2026-07-10T12:40:00Z
priority: high
task_type: feature
parent_review: TASK-REV-3359
feature_id: FEAT-0D1C
wave: 2
implementation_mode: direct
complexity: 3
dependencies: [TASK-LBL-001]
tags: [observability, labels, obs-6, 9f43-identity]
---

# Task: identity.py — absence-safe run_id/attempt resolver over events.jsonl

## Description

Add `guardkit/labels/identity.py` resolving the FEAT-OBSC 9F43 correlation
identity (`run_id`, `attempt`) for a task at disposition time, by reading
`events.jsonl` in the task's evidence directory. This is what lets Chronicler
rows correlate labels to instrumentation events.

## Critical constraints (from TASK-REV-3359 findings F3/F4)

1. **There is NO `event_type` field in the real schema.** The instrumentation
   guide's `jq 'select(.event_type == ...)'` examples are doc drift —
   `BaseEvent` and all subclasses (`guardkit/orchestrator/instrumentation/schemas.py:107-353`)
   declare no discriminator, and `JSONLFileBackend.emit()`
   (`guardkit/orchestrator/instrumentation/emitter.py:176-190`) injects none.
   Type must be sniffed **structurally**: `verification_status` + `turn_count`
   present ⇒ TaskCompleted-shaped; `failure_category` present ⇒ TaskFailed-shaped.
2. **Scan for the last lifecycle-shaped record, not the last line** — a crashed
   run can leave a trailing `llm.call`-shaped record; fall back to the last
   record of ANY shape carrying `run_id` if no lifecycle event exists.
3. **Absence-safe** (per `.claude/rules/absence-of-failure-is-not-success.md`
   family): missing file, empty file, corrupt/truncated lines, or no
   `run_id`-bearing record → return `(None, None)`. NEVER raise, NEVER fabricate
   an identity. `NullEmitter` is the default outside autobuild
   (`guardkit/orchestrator/agent_invoker.py:1488`), so the no-events case is the
   COMMON case, not an edge.

## Deliverables

- `guardkit/labels/identity.py`:
  - `resolve_run_identity(evidence_dir: Path) -> tuple[Optional[str], Optional[int]]`
  - Skips undecodable JSON lines individually (one corrupt line must not orphan
    the rest — mirrors the corrupt-record tolerance the sidecar itself promises).

## Acceptance Criteria

- [ ] Given an events.jsonl whose last lifecycle-shaped record carries run_id and attempt, the resolver returns them
- [ ] Given an events.jsonl whose final line is an llm.call-shaped record, the resolver returns the identity from the last lifecycle-shaped record before it
- [ ] Missing events.jsonl, empty file, or a file with only corrupt lines returns (None, None) without raising
- [ ] A corrupt line among valid records is skipped and the valid records are still used
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Test Requirements

- [ ] Unit tests in `tests/unit/labels/test_identity.py` with synthetic events.jsonl fixtures (completed-shape, failed-shape, trailing llm.call, corrupt-line, absent-file cases)

## Implementation Notes

- run_id provenance: minted once per orchestration at
  `guardkit/orchestrator/autobuild.py:1567-1569`; attempt is the 1-indexed turn
  number (clamped ≥1 per the FEAT-OBSC `cc416cd2` fix).
- Pure stdlib + pathlib; no import of orchestrator modules (read the JSONL
  directly — this module must work against archived copies too).
