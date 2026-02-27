---
id: TASK-SFC-002
title: Update seed_feature_build_architecture.py with Coach and Assumptions Manifest changes
task_type: implementation
status: completed
created: 2026-02-23T14:00:00Z
updated: 2026-02-26T00:00:00Z
completed: 2026-02-26T00:00:00Z
priority: high
tags: [graphiti, seeding, autobuild-coach, assumptions-manifest, promise-verification, honesty-verification]
complexity: 3
parent_review: TASK-REV-5FA4
feature_id: FEAT-SFC
wave: 1
implementation_mode: task-work
dependencies: []
completed_location: tasks/completed/TASK-SFC-002/
organized_files: [TASK-SFC-002.md]
---

# Task: Update Feature Build Architecture Seed with Coach and Assumptions Changes

## Description

Update the `feature_build_coach_agent` episode in `seed_feature_build_architecture.py` to reflect the Coach's new Promise Verification and Honesty Verification capabilities, and add a new episode for the Assumptions Manifest pipeline.

This addresses findings F5, F6, F7, and F8 from the TASK-REV-5FA4 review (all HIGH).

## Context

- Source of truth for Coach capabilities: `.claude/agents/autobuild-coach.md`
- Source of truth for Assumptions Manifest flow: `docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md` (Section 4.3)
- Current episode count: 7 (update to 8 after adding)

## Changes Required

### 1. Update `feature_build_coach_agent` episode

Replace the existing `validation_approach` list with:

```python
("feature_build_coach_agent", {
    "entity_type": "agent",
    "name": "AutoBuild Coach Agent",
    "file": ".claude/agents/autobuild-coach.md",
    "purpose": "Validate Player's implementation independently",
    "critical_behavior": "Coach has READ-ONLY access - validates but cannot modify",
    "tools_available": ["Read", "Bash (read-only commands only)"],
    "validation_approach": [
        "Read task_work_results.json from Player's execution",
        "Run tests independently (trust but verify)",
        "Check acceptance criteria",
        "Create criteria_verification entry for each completion_promise (criterion_id tracking)",
        "Factor in Honesty Verification results (honesty_score from CoachVerifier)",
        "Validate against Gherkin scenarios when available (from /feature-spec)",
        "Validate against Assumptions Manifest when available",
        "Either APPROVE or provide FEEDBACK"
    ],
    "promise_verification": {
        "description": "Structured tracking of acceptance criteria completion",
        "schema": "criteria_verification array with criterion_id, result (verified/rejected), notes",
        "rule": "APPROVE only if ALL criteria verified; FEEDBACK if ANY rejected"
    },
    "honesty_verification": {
        "description": "Pre-validated by CoachVerifier before Coach is invoked",
        "flow": "Player Report -> CoachVerifier -> Honesty Context -> Coach",
        "honesty_score": "0.0 to 1.0 (1.0 = all claims verified)",
        "discrepancy_types": ["test_result (critical)", "file_existence (critical)", "test_count (warning)"],
        "rule": "honesty_score < 0.5 = MUST provide feedback; < 0.8 with critical discrepancies = strongly consider feedback"
    }
}),
```

### 2. Add `feature_build_assumptions_flow` episode (NEW)

Insert after `feature_build_feature_yaml_schema`:

```python
("feature_build_assumptions_flow", {
    "entity_type": "architecture",
    "name": "Assumptions Manifest Pipeline",
    "description": "How /feature-spec assumptions flow through the AutoBuild pipeline",
    "flow": [
        "1. /feature-spec generates _assumptions.yaml with confidence levels (high/medium/low)",
        "2. Human reviews assumptions during Gherkin curation (Phase 5)",
        "3. /feature-plan reads assumptions, flags low-confidence in task metadata",
        "4. AutoBuild Player reads assumptions as Graphiti context",
        "5. Coach validates implementation against BOTH Gherkin AND assumptions manifest",
        "6. If Player silently changed an assumption, Coach detects divergence"
    ],
    "gating_rules": {
        "high_confidence": "Auto-proceed",
        "medium_confidence": "Coach reviews, may auto-approve",
        "low_confidence": "Mandatory human review before implementation"
    },
    "key_insight": "Assumptions are defence-in-depth Layer 1 - they reduce ambiguity upstream before AutoBuild begins",
    "integration_with_coach": "Coach reads _assumptions.yaml alongside .feature file to detect divergence from specification"
}),
```

### 3. Update module docstring

Change "Creates 7 episodes" to "Creates 8 episodes".

## Acceptance Criteria

- [x] `feature_build_coach_agent` episode includes `promise_verification` section
- [x] `feature_build_coach_agent` episode includes `honesty_verification` section with score thresholds
- [x] `feature_build_coach_agent` `validation_approach` includes criteria_verification, honesty, Gherkin, and Assumptions items
- [x] New `feature_build_assumptions_flow` episode exists with complete pipeline flow
- [x] `feature_build_assumptions_flow` includes gating rules by confidence level
- [x] Module docstring updated to reflect 8 episodes
- [x] `ruff check guardkit/knowledge/seed_feature_build_architecture.py` passes

## Files Modified

| File | Action |
|------|--------|
| `guardkit/knowledge/seed_feature_build_architecture.py` | Updated coach episode + added assumptions episode + updated docstring |
