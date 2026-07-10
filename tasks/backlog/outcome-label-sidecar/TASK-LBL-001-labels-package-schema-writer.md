---
id: TASK-LBL-001
title: "Labels package: schema, content-addressed label_id, append-only writer"
status: backlog
created: 2026-07-10T12:40:00Z
updated: 2026-07-10T12:40:00Z
priority: high
task_type: scaffolding
parent_review: TASK-REV-3359
feature_id: FEAT-0D1C
wave: 1
implementation_mode: direct
complexity: 2
dependencies: []
tags: [observability, labels, obs-6]
---

# Task: Labels package — schema, content-addressed label_id, append-only writer

## Description

Create the new `guardkit/labels/` package (sibling of `guardkit/knowledge/`,
`guardkit/qa/`, `guardkit/worktrees/`) containing the outcome-label record schema
and the ONE append-only writer that every surface (CLI, markdown-command hooks)
routes through.

**Do NOT name anything in this feature "disposition"** — `guardkit/qa/formats/
disposition_record.py` (F8, DF-017) already owns that term with incompatible
`run_id` semantics. This domain is `labels` (see TASK-REV-3359 finding F5).

## Deliverables

1. `guardkit/labels/__init__.py` — public exports.
2. `guardkit/labels/schema.py`:
   - `VerdictClass` — closed enum: `coach_correct`, `operator_caught`,
     `merge_review_caught`, `live_gate_caught`. Unknown values are rejected at
     construction (Pydantic).
   - `OutcomeLabelRecord` (Pydantic v2 model, per `.claude/rules/patterns/pydantic-models.md`):
     `schema_version: int = 1`, `label_id: str`, `task_id: str` (required,
     pattern `^[A-Za-z0-9._-]+$` — rejects path separators / traversal),
     `feature_id: Optional[str]`, `verdict_class: VerdictClass`,
     `source_ref: str` (disposition source, e.g. `TASK-REV-3359`,
     `merge-review:FEAT-0D1C`), `evidence_ref: str` (task-id-anchored relative,
     e.g. `autobuild/TASK-XXX/` — never absolute), `dc_class: Optional[str]`,
     `run_id: Optional[str]`, `attempt: Optional[int]` (nullable is LOAD-BEARING:
     most non-autobuild dispositions have no events.jsonl — review finding F3),
     `timestamp: str` (ISO 8601 UTC).
   - `compute_label_id(task_id, verdict_class, source_ref, dc_class) -> str` —
     SHA-256 over the canonical field join, **timestamp excluded** (ASSUM-006):
     a retry re-emission is idempotent by id; a re-judgment changing any judged
     field gets a new id. Prefix `LBL-`, 16 hex chars.
3. `guardkit/labels/writer.py`:
   - `append_label_record(record: OutcomeLabelRecord, target_dir: Path) -> LabelWriteResult`
     — appends ONE JSON line to `target_dir / "outcome_labels.jsonl"`.
   - `LabelWriteResult` dataclass: `success: bool`, `path: Optional[Path]`,
     `error: Optional[str]` (per `.claude/rules/patterns/dataclasses.md`).
   - **Fail-open**: never raises. `OSError`/unwritable destination → `success=False`
     with the error message; the caller's disposition flow continues.
   - Append-only: single `open(path, "a")` write of one complete line; no
     read-modify-write, no truncation, never rewrites existing lines.

## Acceptance Criteria

- [ ] `compute_label_id` is deterministic: identical (task_id, verdict_class, source_ref, dc_class) → identical id; timestamp variation does NOT change the id
- [ ] Constructing a record with an unrecognised verdict class raises a validation error naming the allowed classes
- [ ] Constructing a record without a task id (or with path separators in it) raises a validation error
- [ ] Constructing a record whose evidence_ref is not anchored to the record's own task_id raises a validation error (cross-task mislabel guard)
- [ ] `append_label_record` appends without modifying prior lines; two sequential writes yield two lines in write order
- [ ] `append_label_record` on an unwritable destination returns `success=False` with a non-empty error and does not raise
- [ ] `run_id`/`attempt` accept `None` and serialize as JSON `null`
- [ ] Package importable standalone: `python -c "from guardkit.labels import append_label_record, OutcomeLabelRecord"` exits 0

## Test Requirements

- [ ] Unit tests in `tests/unit/labels/test_schema.py` and `tests/unit/labels/test_writer.py` (LBL-006 extends these; this task ships the basic happy/reject paths)

## Implementation Notes

- Mirror the writer-result shape of `guardkit/knowledge/outcome_manager.py`
  (the canonical one-producer-many-callers precedent).
- No new dependencies; Pydantic v2 is already a project dependency.
