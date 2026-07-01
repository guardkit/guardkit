---
complexity: 4
dependencies: []
feature_id: FEAT-MEM-08
id: TASK-MEM08-001
implementation_mode: task-work
parent_review: TASK-REV-MEM08
status: completed
task_type: declarative
title: Produce the group_id → fleet-memory identity mapping table
wave: 1
---

# TASK-MEM08-001 — group_id → (project, payload_type, domain_tags) mapping

> **This is the core design task — produced FIRST. It drives every other task in the feature.**
> Source: brief §"Write-side mapping" / plan §2a. Reference the verified group inventory in
> `guardkit/_group_defs.py` (9 project + 20 system groups).

## Goal

Collapse guardkit's **9 project** + **20 system** Graphiti `group_id`s onto fleet-memory's identity
triple `(project, payload_type, domain_tags)`, and decide **migrate vs. retire** per group. Emit it as
**both** a human-readable table (markdown) **and** a machine-readable mapping module so downstream
tasks consume one source of truth (no drift).

## Deliverables

1. `docs/design/specs/memory-cutover/group-id-mapping.md` — the decision table: every `group_id` →
   `(fleet-memory project, payload_type, domain_tags, identifier-convention, migrate|retire, note)`.
2. `guardkit/knowledge/fleet_memory_mapping.py` — a constants/data module exposing:
   - `GROUP_ID_MAP: dict[str, GroupMapping]` where `GroupMapping` carries `project`, `payload_type`,
     `domain_tags: list[str]`, `disposition: Literal["migrate","retire"]`.
   - `resolve(group_id: str) -> GroupMapping | None` (None = unmapped/retired → caller skips, fail-open).
   - PEP 503-style group_id normalisation (underscores only — no hyphens; matches fleet-memory's
     `project` regex `^[a-z0-9_]+$`).

## Mapping rules (from the brief)

- Project groups → `project="guardkit"` + a `payload_type`/`domain_tag`:
  - `task_outcomes` → `build_outcome` (identifier = task_id) — recommended typed home.
  - `project_decisions` / `architecture_decisions` (system) → `adr`.
  - `feature_specs`, `domain_knowledge`, `project_overview`, `project_architecture` → `document` + domain_tag.
- System groups → mostly **RETIRE** (the harvest corpus already covers product_knowledge,
  command_workflows, patterns, rules, agents, templates…). Mark each `migrate` or `retire` explicitly
  with a one-line reason. Anything genuinely runtime (e.g. `failure_patterns`, `failed_approaches`) →
  `warning` payload + domain_tag, `migrate`.
- `turn_states` → decide: `document` typed or `retire` (note the call-site `turn_state_operations.py`).

## Acceptance Criteria

- [ ] Every one of the 9 project + 20 system group_ids from `guardkit/_group_defs.py` appears in both the
      markdown table and `GROUP_ID_MAP` with a non-ambiguous `(project, payload_type, domain_tags, disposition)`.
- [ ] `payload_type` values are restricted to the 7 registered fleet-memory types
      (`adr, review_report, build_outcome, pattern, warning, seed_module, document`).
- [ ] Each `migrate` row names its identifier-derivation convention (e.g. task_outcomes → `task_id`).
- [ ] Each `retire` row states why (one line: "covered by harvest corpus" or "no fleet-memory analogue").
- [ ] `resolve()` returns `None` for an unknown/retired group (fail-open) and a `GroupMapping` for a mapped one.
- [ ] All group_id normalisation produces underscore-only output (no hyphens — RediSearch/PG-safe).
- [ ] Unit tests cover: every mapped group resolves; unknown group → None; normalisation strips hyphens.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

```bash
pytest tests/unit/knowledge/test_fleet_memory_mapping.py -v
python -c "from guardkit.knowledge.fleet_memory_mapping import GROUP_ID_MAP, resolve; assert resolve('task_outcomes').payload_type=='build_outcome'; assert resolve('nope') is None"
```

## Implementation Notes

This module is the §4 Integration Contract producer for TASK-MEM08-002/004/006/008. Keep it pure data +
a thin resolver; no I/O, no network. The disposition (`migrate`/`retire`) is the authority for the
"retire seeds the harvest covers" decision — do not migrate a group the table marks `retire`.