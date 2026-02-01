---
complexity: 4
dependencies:
- TASK-GR3-003
estimate_hours: 2
feature_id: FEAT-0F4A
id: TASK-GR3-004
implementation_mode: task-work
parallel_group: wave1-gr003
parent_review: TASK-REV-0CD7
status: design_approved
sub_feature: GR-003
task_type: feature
title: Integrate with /feature-plan command
wave: 1
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