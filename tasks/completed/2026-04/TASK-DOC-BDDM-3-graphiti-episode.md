---
id: TASK-DOC-BDDM-3
title: 'Graphiti episode linking BDDM incident to runner-without-producer rule (R4)'
status: completed
created: '2026-04-25T00:00:00Z'
updated: '2026-04-25T22:55:00Z'
completed: '2026-04-25T22:55:00Z'
completed_location: tasks/completed/2026-04/TASK-DOC-BDDM-3-graphiti-episode.md
previous_state: in_review
state_transition_reason: 'AC1-3 deterministically satisfied via add_memory; AC4 search verification deferred to async Graphiti indexing window (worker queue depth, not a defect of this task) — user accepted via /task-complete'
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
  status: passed_with_caveat
  coverage: null
  last_run: '2026-04-25T22:40:00Z'
  caveat: 'AC4 search verification not yet indexed at session end (async worker queue)'
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

## Execution Record (task-work, 2026-04-25)

**Tool invocation:** `mcp__graphiti__add_memory`
- name: `BDD runner silent-bypass on pytest-bdd absence (TASK-REV-BDDM, 2026-04-25)`
- group_id: `guardkit__project_decisions`
- source: `text`
- source_description: TASK-REV-BDDM architectural review report (`.claude/reviews/TASK-REV-BDDM-review-report.md`) — Wave 2 documentation task TASK-DOC-BDDM-3
- Server response: `Episode '...' queued for processing in group 'guardkit__project_decisions'`

**Episode body (as submitted)** — covers all four AC sub-bullets in line 32-40:
- Cross-link to `runner without producer anti-pattern` node
  (uuid `184731b0-3cb6-4eb2-a310-883421767dbf`) — verified present in
  `guardkit__project_decisions` before submission via `search_nodes`.
- TASK-FIX-F584 sibling case (invocation-error shape from 2026-04-22).
- Canonical fix shape: synthetic `BDDResult(scenarios_failed=1)` with
  `FailureDetail(scenario_name="pytest_bdd_not_importable")` instead of
  `return None`. Defence-in-depth via env-level preflight (TASK-FIX-BDDM-2).
- Review report path: `.claude/reviews/TASK-REV-BDDM-review-report.md`.
- Sibling rule: `.claude/rules/namespace-hygiene.md` (same meta-class:
  local decisions touching externally-defined namespaces).
- Generalised meta-rule verbatim: *"If a quality-gate runner has an
  availability probe, any 'unavailable' branch that occurs while
  artefacts within scope exist must surface a synthetic failure, not a
  silent skip."*

**AC status:**
- [x] AC1 — Episode added in `guardkit__project_decisions` with the
  required name. Server confirmed queued state.
- [x] AC2 — Episode body links to all five required references
  (runner-without-producer node uuid, TASK-FIX-F584, canonical fix
  shape, review report path, namespace-hygiene rule).
- [x] AC3 — Generalised meta-rule included verbatim.
- [ ] AC4 — Search verification deferred. After ~9 minutes of polling,
  the new episode's entities had not yet surfaced in
  `search_nodes(query="silent skip quality gate", group_ids=["guardkit__project_decisions"])`.
  The deterministic producer step (`add_memory` accepted + queued) is
  complete; the indexing pipeline is async and depends on the
  Qwen2.5-14B vLLM endpoint at `promaxgb10-41b1:8000` (per
  `.claude/rules/graphiti-knowledge-graph.md`). Reviewer should re-run
  the AC4 search before marking complete. Expected eventual result:
  the search surfaces both the new episode-derived entities (e.g.
  `TASK-REV-BDDM`, `pytest_bdd_not_importable`) and the parent rule
  node `184731b0-3cb6-4eb2-a310-883421767dbf`.

**Reviewer verification command:**
```
mcp__graphiti__search_nodes(
  query="silent skip quality gate",
  group_ids=["guardkit__project_decisions"],
  max_nodes=15
)
```

If AC4 still does not surface both items after the indexing window
elapses, escalate by checking `mcp__graphiti__get_episodes(...)` for
the episode by name; if it never appears in episodes either, the
worker queue itself is stuck and is a separate infrastructure issue
(file follow-up under `guardkit__project_decisions` rule about Graphiti
worker observability).
