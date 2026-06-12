---
id: TASK-QAWE-002
title: UNWIRED_PATH bundle integration — coach_evidence fields, gather_evidence, render
task_type: feature
parent_task: TASK-HMIG-BDDWIRE
feature_id: FEAT-C332
wave: 2
implementation_mode: task-work
complexity: 5
dependencies: [TASK-QAWE-001]
priority: medium
---

# Task: UNWIRED_PATH bundle integration (Wave 1)

## Description

Wire the Wave-0 `WiringAnalyzer` UNWIRED_PATH output into the Coach evidence path via
the verified, unchanged seams in `docs/features/qa-verifier-wiring-probes-scope.md` §5.
guardkit consumes guardkitfactory's `analyze_wiring(...)` lazily (the BDDWIRE pattern)
and stores the returned **dict** (never the dataclass), so `coach_evidence.py` keeps
zero guardkitfactory import.

## Acceptance Criteria

- [ ] **AC-002 (bundle fields):** add `wiring`, `mocked_seam`, `spec_gap`
  `Optional[Dict]` fields after `tests:` at `coach_evidence.py:169`; `to_dict()`
  (`asdict`, `:180-191`) unchanged.
- [ ] **AC (gather population):** populate at the **complete-path return only**
  (`coach_validator.py:2120`); partial returns (2030/2058/2103) leave them `None`.
  Authored set from `_compute_own_authored` (`:775-783`, extract or duplicate — not
  `files_modified`). `detect_stack_template` (`:64`) supplies the language.
- [ ] **AC-008 (task-type gate):** SCAFFOLDING/DOCUMENTATION or zero-target turns →
  all three fields `None`.
- [ ] **AC-011 (reaches verdict):** `_render_evidence_bundle_section`
  (`agent_invoker.py:3098`) surfaces the fields; advisory guard sentence #7 appended
  after guard #6 (`:3320-3332`).
- [ ] **AC-016 (truncation):** `>20` findings → first 20 + "... and N more" mirroring
  `bdd.discoveries` (`agent_invoker.py:3138-3152`).
- [ ] **AC-015 (absent-vs-empty):** `findings:[]` + positive status is distinct from
  `None`.
- [ ] **AC-017 (graceful import absence):** with guardkitfactory/tree-sitter absent,
  the lazy seam catches `ImportError`, all three fields `None`, `gather_evidence`
  does not crash.
- [ ] **AC-018 (no regression):** existing guardkit + guardkitfactory suites green.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation
- `pytest tests/orchestrator -k "wiring or coach_evidence" -v`
- Lint/format pass with zero errors.
