---
id: TASK-DOC-BDDM-3
title: 'Graphiti episode linking BDDM incident to runner-without-producer rule (R4)'
status: backlog
created: '2026-04-25T00:00:00Z'
updated: '2026-04-25T00:00:00Z'
priority: medium
complexity: 2
task_type: documentation
tags: [graphiti, knowledge-graph, design-rules]
parent_review: TASK-REV-BDDM
feature_id: FEAT-BDDM
implementation_mode: direct
wave: 2
conductor_workspace: bdd-fix-wave2-1
depends_on: [TASK-FIX-BDDM-1, TASK-FIX-BDDM-2, TASK-DOC-BDDM-4]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Graphiti episode for runner-without-producer (R4)

## Description

The Graphiti rule *"runner without producer anti-pattern"* (uuid `184731b0-3cb6-4eb2-a310-883421767dbf`, group `guardkit__project_decisions`) already names `feature-spec.md` as affected (10% wiring rate) and `task-work.md` (34.9% wiring rate). The TASK-REV-BDDM incident is a fresh instance of the same meta-rule that should be cross-linked so future Phase 2.5 architectural reviews surface it during edits to `bdd_runner.py`, `coach_validator.py`, or any new quality-gate runner.

## Acceptance Criteria

- [ ] Write a Graphiti episode in `guardkit__project_decisions` named *"BDD runner silent-bypass on pytest-bdd absence (TASK-REV-BDDM, 2026-04-25)"*.
- [ ] Episode body links to:
  - The "runner without producer" node (uuid `184731b0-3cb6-4eb2-a310-883421767dbf`).
  - TASK-FIX-F584 (invocation-error sibling case).
  - The canonical fix shape (synthesise blocker rather than `return None`).
  - This review report at `.claude/reviews/TASK-REV-BDDM-review-report.md`.
  - The sibling rule in `.claude/rules/namespace-hygiene.md`.
- [ ] Episode adds the meta-rule generalisation: *"if a quality-gate runner has an availability probe, any 'unavailable' branch that occurs while artefacts within scope exist must surface a synthetic failure, not a silent skip."*
- [ ] Verify the episode is searchable via `mcp__graphiti__search_nodes(query="silent skip quality gate", group_ids=["guardkit__project_decisions"])` and that the result surfaces both this episode and the original "runner without producer" node.

## Implementation Notes

**Tool:** `mcp__graphiti__add_memory`

**Approach:** Direct mode — single MCP tool invocation. No code changes.

**Suggested episode body:**

```
TASK-REV-BDDM (2026-04-25) — comprehensive architectural review

Concrete instance of the "runner without producer" anti-pattern in the
runtime BDD oracle:

- DEFECT: bdd_runner.run_bdd_for_task() at lines 466-473 returns None
  when tagged feature files exist AND pytest_bdd is not importable.
- IMPACT: jarvis FEAT-J002 / FEAT-J003 ran with zero BDD verification
  for every tagged task (10/11 silent-skip log lines per history).
- ROOT CAUSE: project's pyproject.toml lacked pytest-bdd dependency.
- FIX (TASK-FIX-BDDM-1, R1): replace return None with a synthetic
  BDDResult(scenarios_failed=1) carrying a FailureDetail
  (scenario_name="pytest_bdd_not_importable").
- DEFENCE-IN-DEPTH (TASK-FIX-BDDM-2, R3): env-level preflight in
  feature_validator catches the gap before any SDK turn burns.
- DOCS (TASK-DOC-BDDM-4, R5): pyproject prerequisite explicit in BDD
  workflow guide.

Sibling cases:
- TASK-FIX-F584 (2026-04-22) — same shape for pytest invocation errors;
  this incident is the case F584 didn't cover.
- Namespace hygiene rule (.claude/rules/namespace-hygiene.md) — same
  meta-class (local design decisions touching externally-defined
  namespaces).

Generalised meta-rule: if a quality-gate runner has an availability
probe, any "unavailable" branch that occurs while artefacts within
scope exist must surface a synthetic failure, not a silent skip.
```

## Notes

- Depends on Wave 1 merging so the episode can cite the canonical fix.
- See review report §F (regression-safety attestation) for full context.
