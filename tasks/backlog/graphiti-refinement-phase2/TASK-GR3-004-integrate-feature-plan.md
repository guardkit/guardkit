---
id: TASK-GR3-004
title: Integrate with /feature-plan command
status: backlog
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-003
wave: 1
parallel_group: wave1-gr003
implementation_mode: task-work
complexity: 4
estimate_hours: 2
dependencies:
  - TASK-GR3-003
---

# Integrate with /feature-plan command

## Description

Integrate the `FeaturePlanContextBuilder` into the `/feature-plan` command so that feature context is automatically retrieved and injected into the planning prompt.

## Acceptance Criteria

- [ ] `/feature-plan "implement FEAT-XXX"` auto-detects feature ID
- [ ] Feature spec is seeded to Graphiti before planning
- [ ] Context is retrieved and formatted for prompt injection
- [ ] Planning prompt includes enriched context section
- [ ] Logging shows context retrieval progress

## Technical Details

**Integration Point**: `installer/core/commands/feature-plan.md` execution flow

**Workflow**:
1. Parse feature description
2. Build context via `FeaturePlanContextBuilder`
3. Format context for prompt with `to_prompt_context()`
4. Inject into planning prompt
5. Continue with normal feature planning

**Reference**: See FEAT-GR-003-feature-spec-integration.md workflow diagram.
