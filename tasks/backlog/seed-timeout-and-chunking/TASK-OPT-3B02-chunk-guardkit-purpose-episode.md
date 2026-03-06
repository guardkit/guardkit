---
id: TASK-OPT-3B02
title: Chunk guardkit_purpose episode into smaller focused episodes
status: backlog
created: 2026-03-06T17:30:00Z
updated: 2026-03-06T17:30:00Z
priority: high
task_type: implementation
complexity: 4
tags: [graphiti, seeding, performance, chunking]
parent_review: TASK-REV-95B1
feature_id: FEAT-seed-timeout-chunking
wave: 1
implementation_mode: task-work
---

# Task: Chunk guardkit_purpose Episode

## Description

The `guardkit_purpose` episode is the single longest successful episode at **151.6s**, extracting 23 nodes and 42 edges. It processes the project overview section of CLAUDE.md which contains multiple distinct concepts:
- GuardKit purpose and mission
- Core features list
- Core principles
- Essential commands overview
- Quality gates overview

This is doing too much in one episode, causing:
- Near-timeout processing time (151.6s vs 120s default timeout — only survived because it's in project_overview group with 240s timeout)
- Potentially lower extraction quality (LLM processing too much context at once)
- Risk of becoming a timeout failure as the graph grows

## Proposed Change

Split `guardkit_purpose` into 2-3 focused episodes in the seeding configuration:

1. **guardkit_mission** — Purpose, value proposition, core principles (~500 words)
2. **guardkit_commands_overview** — Command reference and workflow (~500 words)
3. **guardkit_quality_gates** — Quality gates, states, and testing (~500 words)

### Files to Modify

- `guardkit/knowledge/seeding.py` — Where episode content is defined for the `project_overview` category
- Possibly `guardkit/knowledge/seed_templates/` if episode content is templated

## Acceptance Criteria

- [ ] `guardkit_purpose` episode replaced with 2-3 smaller episodes
- [ ] Each sub-episode completes in <60s (based on current average)
- [ ] Total node/edge count across sub-episodes >= original (23 nodes, 42 edges)
- [ ] No loss of knowledge coverage
- [ ] Code compiles and existing tests pass

## Evidence

- Episode profile from reseed_5: `guardkit_purpose` — 151.6s, 23 nodes, 42 edges
- Review report: `.claude/reviews/TASK-REV-95B1-review-report.md`

## Notes

Also consider whether `component_stream_parser` (118.5s, 18 nodes, 21 edges) warrants similar chunking. It's the second-longest episode but is within the 120s timeout (barely). Address in a follow-up task if needed.
