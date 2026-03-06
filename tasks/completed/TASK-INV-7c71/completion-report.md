# Completion Report: TASK-INV-7c71

## Task Summary

**Title**: Investigate Episode 3 (tech_stack) structural slowdown from ~99s to ~249s
**Feature**: FEAT-GIP (Graphiti Init Performance)
**Complexity**: 6 (Medium)
**Duration**: Single session investigation

## Decision: Accept ~249s as Episode 3 Baseline

### Root Cause

**Edge Resolution Scaling with Graph Density** (Confidence: 8/10)

After clear+reseed populates ~120-124 episodes with technology-related entities and edges, Episode 3's edge resolution phase (Phase 4b in graphiti-core's `add_episode`) encounters significantly more candidate edges, requiring more LLM deduplication calls per extracted edge.

The ~99s timing (init_10, init_11 R1) was the outlier — it occurred against a sparse graph state. The ~249s timing is the structural baseline for a properly seeded graph.

### Key Evidence

1. Inflection correlates with clear+reseed, not vLLM state (TASK-REV-8A31 refuted vLLM hypothesis)
2. Episode 2 unaffected (low entity overlap with seeded technology content)
3. Same CLAUDE.md template across all runs (content not the variable)
4. Graphiti-core Phase 4b makes LLM calls proportional to candidate edge count
5. `duplicate_facts` warnings doubled with denser graph (~190 → ~370)

### Recommendation

- **Accept ~249s as baseline** — graph density is a feature, not a bug
- **Do NOT optimize content** — content isn't the variable
- **Do NOT reduce graph density** — would degrade AI context quality
- **600s timeout provides adequate headroom** (249s = 41.5% of ceiling)

## Deliverables

| # | Deliverable | File |
|---|-----------|------|
| 1 | Investigation report | `docs/reviews/TASK-INV-7c71-investigation-report.md` |
| 2 | Episode profiling instrumentation | `guardkit/knowledge/graphiti_client.py` (entity/edge count logging in `_create_episode`) |
| 3 | Graph stats command | `guardkit/cli/graphiti.py` (`guardkit graphiti stats`) + `graphiti_client.py` (`graph_stats()`) |
| 4 | Task completion | `tasks/completed/TASK-INV-7c71/` |

## Quality Gates

- [x] All 315 tests pass
- [x] Code imports cleanly (no syntax errors)
- [x] Investigation report covers all acceptance criteria
- [x] Root cause identified with supporting evidence

## FEAT-GIP Progress

| Task | Status | Priority |
|------|--------|----------|
| TASK-FIX-cc7e (project_purpose timeout) | in_review | HIGH |
| **TASK-INV-7c71 (Episode 3 investigation)** | **COMPLETED** | **MEDIUM** |
| TASK-OPS-64fe (close FEAT-SPR) | completed | MEDIUM |
| TASK-FIX-303e (agent timeout 240s) | backlog | LOW |
