---
id: TASK-REV-5F19
title: Reduce context window usage by migrating static content to Graphiti on-demand retrieval
status: review_complete
created: 2026-02-05T12:00:00Z
updated: 2026-02-05T14:00:00Z
priority: high
tags: [context-optimization, graphiti, performance, token-reduction]
task_type: review
complexity: 6
related_tasks: [TASK-REV-CMD1]
review_results:
  mode: architectural
  depth: standard
  score: 82
  findings_count: 15
  recommendations_count: 5
  decision: implement
  feature_id: FEAT-CR01
  report_path: .claude/reviews/TASK-REV-5F19-review-report.md
---

# Task: Reduce Context Window Usage via Graphiti Migration

## Problem Statement

Static CLAUDE.md and .claude/rules/ files load ~15,800 tokens into every conversation, contributing to weekly usage limits. Graphiti is fully operational (163 episodes seeded) but underutilized - most knowledge is still served via static files rather than on-demand retrieval.

## Prior Work

TASK-REV-CMD1 addressed the 40k character limit by moving content between static files (rules/ structure). This task goes further: migrate eligible content to Graphiti for on-demand retrieval, reducing the always-loaded static context.

## Current State (Validated)

### Static Files (~15,800 tokens always loaded)

| File | Lines | ~Tokens |
|------|------:|--------:|
| CLAUDE.md (root) | 996 | 3,980 |
| .claude/CLAUDE.md | 113 | 450 |
| rules/autobuild.md | 389 | 1,556 |
| rules/clarifying-questions.md | 141 | 564 |
| rules/feature-build-invariants.md | 64 | 256 |
| rules/graphiti-knowledge.md | 377 | 1,508 |
| rules/guidance/agent-development.md | 185 | 740 |
| rules/hash-based-ids.md | 86 | 344 |
| rules/patterns/dataclasses.md | 180 | 720 |
| rules/patterns/orchestrators.md | 385 | 1,540 |
| rules/patterns/pydantic-models.md | 146 | 584 |
| rules/patterns/template.md | 159 | 636 |
| rules/python-library.md | 215 | 860 |
| rules/task-workflow.md | 306 | 1,224 |
| rules/testing.md | 211 | 844 |

### Graphiti Knowledge (163 episodes)

| Group | Episodes | Coverage Quality |
|-------|----------|-----------------|
| command_workflows | 67 | Good - commands covered |
| architecture_decisions | 26 | Good - ADRs seeded |
| product_knowledge | 21 | Good - core concepts |
| patterns | 19 | Partial - relationships only, no code examples |
| failure_patterns | 19 | Good |
| agents | 11 | Partial - names, not guidance |
| project_overview | 0 | Gap |
| project_architecture | 0 | Gap |
| feature_specs | 0 | Gap |

## Analysis Scope

### 1. Content Classification
For each static file, classify content as:
- **KEEP STATIC**: Must always be present (command syntax, core workflow)
- **MIGRATE TO GRAPHITI**: Factual knowledge retrievable on-demand
- **ELIMINATE**: Redundant or already in Graphiti

### 2. Graphiti Gap Analysis
- What's in static files but missing from Graphiti?
- What needs seeding before files can be trimmed?
- What's the seeding approach (add-context, manual episodes)?

### 3. Retrieval Validation
- Can Graphiti reliably return the migrated content?
- What relevance scores do queries return?
- Are there retrieval latency concerns?

## Acceptance Criteria

- [ ] Each static file classified: KEEP / MIGRATE / ELIMINATE with rationale
- [ ] Graphiti gaps identified with seeding plan
- [ ] Estimated token reduction calculated (target: 40-60% reduction)
- [ ] Retrieval test plan for migrated content
- [ ] Risk assessment for content that might be lost
- [ ] Implementation subtasks generated

## Constraints

- Must not break existing /task-work, /feature-build, /feature-plan workflows
- Must maintain code pattern guidance (pydantic, dataclass examples)
- Graphiti queries add latency - content needed at conversation start should stay static
- Path-gated rules files already only load when relevant (patterns/)

## Success Metrics

- Total always-loaded context reduced from ~15,800 to ~8,000 tokens (50%)
- All migrated content retrievable via Graphiti with >0.6 relevance
- No workflow regressions
- Weekly token usage meaningfully reduced
