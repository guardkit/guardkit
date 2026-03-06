---
id: TASK-REV-acbc
title: Review seed function scope — unnecessary template seeding
status: review_complete
created: 2026-03-06T13:00:00Z
updated: 2026-03-06T15:00:00Z
review_results:
  mode: decision
  depth: comprehensive
  findings_count: 5
  recommendations_count: 5
  decision: implement
  report_path: .claude/reviews/TASK-REV-acbc-review-report.md
  implementation_tasks: [TASK-daab, TASK-a912]
priority: high
task_type: review
review_mode: decision
review_depth: comprehensive
complexity: 6
tags: [graphiti, seeding, templates, performance, waste, decision]
---

# Review: Seed Function Scope — Unnecessary Template Seeding

## Review Scope

Analyse the behaviour of the `guardkit graphiti seed` function to determine whether it is seeding far more content into the Graphiti Knowledge Graph than is necessary. Specifically, the seed function appears to seed **all built-in templates** (and their associated rules, agents, and patterns) regardless of which template the user's project actually uses.

### Core Question

**Is the seed function wasting hours seeding templates the user will never use?**

### Evidence Available

Multiple seed run outputs are available for analysis in:
`docs/reviews/reduce-static-markdown/`

Key files:
- `reseed_guardkit_3.md` — most recent run (263m, 124/171 episodes, 47 timeouts)
- `reseed_guardkit_2.md` — previous run (2 runs: 209m + 261m)
- Previous reseed/init logs in the same directory

### What We Know From Prior Reviews

From TASK-REV-8A31 and TASK-REV-FFD3:
- Seeding takes **~263 minutes** (~4.4 hours) per run
- 17 categories are seeded, including templates, rules, and agents for **all** stacks
- Templates: 4/7 succeed, 3 timeout at 180s (fastapi_python, react_fastapi_monorepo, react_typescript)
- Agents: 9/18 succeed, 9 timeout at 150s — many are stack-specific agents for templates the project may not use
- Rules: 40/72 succeed — broken down by template (fastapi-python, fastmcp-python, mcp-typescript, nextjs-fullstack, react-fastapi-monorepo, react-typescript, default)
- The **rules alone** have 72 episodes across 7 template-specific categories

### Quantifying the Waste

If a project uses `fastapi-python`, it should NOT need to seed:
- `rules/react-typescript` (9 episodes)
- `rules/react-fastapi-monorepo` (21 episodes)
- `rules/nextjs-fullstack` (12 episodes)
- `rules/mcp-typescript` (4 episodes)
- `rules/fastmcp-python` (11 episodes)
- `template_react_typescript`, `template_react_fastapi_monorepo`, `template_nextjs_fullstack`
- All agents for non-fastapi templates

That's potentially **57+ unnecessary rule episodes** out of 72, plus unnecessary template and agent episodes.

## Key Questions

### 1. What does the seed function actually seed?

- Enumerate all 17 categories and what determines their content
- Which categories are project-specific vs universal?
- Is the category list hardcoded or derived from project config?

### 2. How much time is spent on irrelevant templates?

- Break down the ~263m duration by template-relevance
- Calculate: time spent on universally-useful categories vs template-specific categories
- What percentage of the total duration is wasted on unused templates?

### 3. What would a "seed only what you need" approach look like?

- Seed universal categories (product_knowledge, architecture_decisions, etc.) always
- Seed template-specific categories only for the project's detected/configured template
- What's the estimated time savings?

### 4. Are there any cross-template dependencies?

- Do any template-specific rules/agents reference content from other templates?
- Would selective seeding break any knowledge graph relationships?

### 5. What changes would be needed?

- Where is the seed category list defined?
- How does `guardkit graphiti seed` determine what to seed?
- What's the implementation complexity of adding template filtering?

## Acceptance Criteria

- [x] Seed function behaviour fully documented (what it seeds and why)
- [x] Time breakdown by category relevance (universal vs template-specific)
- [x] Waste quantification (time/episodes spent on irrelevant templates)
- [x] "Seed only what you need" approach designed
- [x] Estimated time savings calculated
- [x] Cross-template dependency analysis completed
- [x] Implementation recommendation with complexity estimate
- [x] Decision: implement both selective rule loading + seed template filtering

## Review Outcome

**Decision: Implement** — two implementation tasks created:

1. **TASK-daab** (Wave 1): Selective rule loading for AutoBuild worktrees — removes ~46 KB of non-essential rules per turn
2. **TASK-a912** (Wave 2): Template filtering in `guardkit graphiti seed` — reduces seed time by 40-60%

Report: `.claude/reviews/TASK-REV-acbc-review-report.md`
