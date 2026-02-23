---
id: TASK-SFC-001
title: Add /feature-spec episode and update workflow episodes in seed_command_workflows.py
task_type: implementation
status: backlog
created: 2026-02-23T14:00:00Z
updated: 2026-02-23T14:00:00Z
priority: high
tags: [graphiti, seeding, feature-spec, seed-command-workflows]
complexity: 3
parent_review: TASK-REV-5FA4
feature_id: FEAT-SFC
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Add /feature-spec Episode and Update Workflow Episodes

## Description

Add a new `command_feature_spec` episode to `seed_command_workflows.py` and update two existing workflow episodes to include the `/feature-spec` command in the development pipeline.

This addresses findings F1-F4 from the TASK-REV-5FA4 review (all CRITICAL).

## Context

- Source of truth for `/feature-spec`: `installer/core/commands/feature-spec.md`
- Source of truth for methodology: `docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md`
- Current episode count in module: 19 (update docstring to 20 after adding)
- All episodes follow the `(name, dict)` tuple pattern with `_add_episodes()` helper

## Changes Required

### 1. Add `command_feature_spec` episode (NEW)

Insert after `command_feature_build` (line ~108), before `workflow_feature_to_build`:

```python
("command_feature_spec", {
    "entity_type": "command",
    "name": "/feature-spec",
    "purpose": "Generate BDD Gherkin specifications using Propose-Review methodology",
    "syntax": '/feature-spec "description" [--from file] [--output dir] [--auto] [--stack name] [--context file]',
    "methodology": "Specification by Example (Gojko Adzic) - AI proposes, human curates",
    "phases": [
        "Phase 1: Context Gathering (stack detection, codebase scan, Graphiti context)",
        "Phase 2: Initial Proposal (grouped: @key-example, @boundary, @negative, @edge-case)",
        "Phase 3: Human Curation (Accept/Reject/Modify/Add/Defer per group)",
        "Phase 4: Edge Case Expansion (security, concurrency, data integrity - optional)",
        "Phase 5: Assumption Resolution (confidence levels: high/medium/low)",
        "Phase 6: Output Generation (.feature, _assumptions.yaml, _summary.md)"
    ],
    "outputs": {
        "feature_file": "{name}.feature - Gherkin scenarios in domain language",
        "assumptions_manifest": "{name}_assumptions.yaml - structured assumptions with confidence levels",
        "summary": "{name}_summary.md - feature summary for /feature-plan consumption"
    },
    "key_principles": [
        "AI proposes concrete examples, human curates (not elicitation/interrogation)",
        "Scenarios use domain language, not implementation language",
        "Every inferred value is an explicit assumption with confidence level",
        "Purely additive - does not modify existing files"
    ],
    "integration": "/feature-plan --context features/{name}/{name}_summary.md",
    "tags": ["@key-example", "@boundary", "@negative", "@edge-case", "@smoke", "@regression"]
}),
```

### 2. Update `workflow_overview` episode

Add a fourth alternative flow:
```python
"Spec-first flow: /feature-spec -> /feature-plan --context summary.md -> /feature-build"
```

### 3. Update `workflow_feature_to_build` episode

Add optional step 0 and update step 1:
```python
"steps": [
    "0. (Optional) /feature-spec 'description' -> generates Gherkin + assumptions + summary",
    "1. /feature-plan 'description' [--context features/{name}/{name}_summary.md]",
    "2. /feature-build FEAT-A1B2",
    "3. Review worktree: cd .guardkit/worktrees/FEAT-A1B2 && git diff main",
    "4. Merge: git checkout main && git merge autobuild/FEAT-A1B2",
    "5. /task-complete TASK-001 TASK-002 (bulk complete)"
],
```

Also add to `benefits`:
```python
"Gherkin-driven specifications when /feature-spec is used upstream"
```

### 4. Update module docstring

Change "Creates 19 episodes" to "Creates 20 episodes" in the `seed_command_workflows` function docstring.

## Acceptance Criteria

- [ ] New `command_feature_spec` episode exists in `seed_command_workflows.py`
- [ ] Episode includes all 6 phases of the Propose-Review methodology
- [ ] Episode includes output file descriptions (.feature, _assumptions.yaml, _summary.md)
- [ ] `workflow_overview` `alternative_flows` includes spec-first flow
- [ ] `workflow_feature_to_build` `steps` includes optional /feature-spec step
- [ ] Module docstring updated to reflect new episode count
- [ ] `pytest tests/ -k seed_command` passes (if applicable)
- [ ] `ruff check guardkit/knowledge/seed_command_workflows.py` passes

## Files to Modify

| File | Action |
|------|--------|
| `guardkit/knowledge/seed_command_workflows.py` | Modify (add episode, update 2 episodes, update docstring) |
