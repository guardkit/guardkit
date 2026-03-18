---
id: TASK-GCA-007
title: Document Graphiti group ID strategy in graphiti-knowledge.md
status: completed
created: '2026-03-18T00:00:00Z'
updated: '2026-03-18T00:00:00Z'
completed: '2026-03-18T00:00:00Z'
priority: low
complexity: 2
tags: [graphiti, documentation, group-ids]
parent_review: REV-SD-001
feature_id: FEAT-CD64
implementation_mode: direct
wave: 1
completed_location: tasks/completed/TASK-GCA-007/
---

# Document Graphiti group ID strategy in graphiti-knowledge.md

## Description

Add a "Group ID Registry" section to `.claude/rules/graphiti-knowledge.md` documenting all group IDs used across commands, their purpose, and which commands create/consume them.

## Acceptance Criteria

- [x] New "## Group ID Registry" section added to `.claude/rules/graphiti-knowledge.md`
- [x] Table includes all known groups:
  - `product_knowledge` (seeding, general queries)
  - `command_workflows` (seeding, command patterns)
  - `architecture_decisions` (seeding + /system-arch + /arch-refine)
  - `project_architecture` (/system-arch creates, /system-design + /impact-analysis consume)
  - `project_design` (/system-design creates, /feature-spec + /feature-plan consume)
  - `api_contracts` (/system-design creates, /feature-spec + /feature-plan consume)
  - `project_decisions` (/system-arch creates)
  - `task_outcomes`, `failure_patterns`, `successful_fixes` (AutoBuild learning)
  - `turn_states` (feature-build turn tracking)
- [x] Clarifies that `graphiti.yaml` `group_ids` list is for seeding only, not an exhaustive registry
- [x] Notes that `GraphitiClient.get_group_id()` auto-prefixes with project_id

## Files to Modify

- `.claude/rules/graphiti-knowledge.md`
