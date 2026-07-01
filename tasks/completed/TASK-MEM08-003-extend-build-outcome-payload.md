---
id: TASK-MEM08-003
title: "Extend fleet-memory BuildOutcomePayload (task_id/lessons/approach) [cross-repo]"
task_type: declarative
parent_review: TASK-REV-MEM08
feature_id: FEAT-MEM-08
wave: 2
implementation_mode: direct
complexity: 3
dependencies:
  - TASK-MEM08-001
target_repo: fleet-memory
---

# TASK-MEM08-003 — Extend `BuildOutcomePayload` with task_id / lessons / approach

> **CROSS-REPO task.** Deliverable lands in the sibling **fleet-memory** repo
> (`../fleet-memory`), reached via the worktree `evidence_repos` declaration. This is the resolved
> fork: carry guardkit's rich task-outcome text into structured retrieval by extending the typed payload
> (rather than dropping it via `extra="ignore"`).

## Why

`fleet_memory.payloads.models.BuildOutcomePayload` today is only `status: str` + `duration_seconds: int`.
`BasePayload` is `ConfigDict(extra="ignore")`, so any extra fields guardkit sends (`task_id`, `lessons`,
`approach`) are **silently dropped before embedding** — they would never reach retrieval. Add them as
declared optional fields so the prose is stored and embedded.

## Deliverable (in ../fleet-memory)

`fleet-memory/src/fleet_memory/payloads/models.py` — extend `BuildOutcomePayload`:

```python
class BuildOutcomePayload(BasePayload):
    payload_type: ClassVar[str] = "build_outcome"
    status: str
    duration_seconds: int
    task_id: str | None = None      # NEW — links the outcome to its task/feature
    lessons: str | None = None      # NEW — lessons-learned prose (embedded for retrieval)
    approach: str | None = None     # NEW — approach/methodology prose (embedded for retrieval)
```

Plus: confirm the chunk/embed path includes the new prose fields in the embedded content (if the
embedding text is assembled from declared fields, the new fields must be included).

## Acceptance Criteria

- [ ] `BuildOutcomePayload` accepts `task_id`, `lessons`, `approach` as optional fields (back-compatible —
      existing 2-field payloads still validate; `version` unchanged unless the team bumps it).
- [ ] The three new fields participate in the embedded/searchable content (not merely stored structurally) —
      a `build_outcome` written with `lessons="..."` is retrievable by a query matching that prose.
- [ ] fleet-memory's own payload tests cover the extended fields (round-trip + retrieval-text inclusion).
- [ ] Natural-key behaviour unchanged (`build_outcome:{project}:{identifier}`; identifier still required).
- [ ] All modified files pass fleet-memory's configured lint/format checks with zero errors.

## Coach Validation

```bash
cd ../fleet-memory && pytest tests/ -k build_outcome -v
cd ../fleet-memory && python -c "from fleet_memory.payloads.models import BuildOutcomePayload as B; B(project='guardkit', identifier='T1', source_ref='x', status='success', duration_seconds=1, task_id='TASK-X', lessons='l', approach='a')"
```

## Implementation Notes

Coordinate with fleet-memory's owner conventions (ASSUM-009 forward-compat). This is the only file this
feature writes outside the guardkit worktree — the feature YAML declares `evidence_repos: [../fleet-memory]`
so the Coach collects this write (see `.claude/rules/evidence-boundary-narrower-than-write-surface.md`).
TASK-MEM08-004 (guardkit) is the consumer of this extended contract.
