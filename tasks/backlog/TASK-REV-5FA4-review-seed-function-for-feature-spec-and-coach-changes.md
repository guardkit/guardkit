---
id: TASK-REV-5FA4
title: Review seed function for feature-spec and autobuild coach changes
task_type: review
status: review_complete
created: 2026-02-23T12:00:00Z
updated: 2026-02-23T14:30:00Z
priority: high
tags: [graphiti, seeding, feature-spec, autobuild-coach, review]
complexity: 5
review_results:
  mode: architectural
  depth: comprehensive
  score: 58
  findings_count: 12
  recommendations_count: 12
  decision: implement
  report_path: .claude/reviews/TASK-REV-5FA4-review-report.md
  implementation_feature: FEAT-SFC
  implementation_tasks: 6
  completed_at: 2026-02-23T14:30:00Z
---

# Task: Review Seed Function for Feature-Spec and Autobuild Coach Changes

## Description

Review the current Graphiti seed function (`seed_command_workflows` and the broader `seed_all_system_context` orchestrator) to determine what updates are needed to reflect:

1. **The new `/feature-spec` command** — A BDD Gherkin specification generator using Propose-Review methodology (added via the `feature-spec-command` branch, now merged to main). This is a significant new command that is not currently represented in the `seed_command_workflows` episodes.

2. **Changes to the Autobuild Coach agent** — The coach now includes Promise Verification (`criteria_verification` array), Honesty Verification (pre-validated by `CoachVerifier`), and structured acceptance criteria validation with `criterion_id` tracking. These changes affect how the coach validates against acceptance criteria and assumptions — directly relevant to `/feature-spec` output.

3. **Assumptions Manifest (D9)** — `/feature-spec` generates a structured YAML Assumptions Manifest alongside Gherkin. The Coach should be checking implementation against this manifest. Verify whether the seed function captures this workflow connection.

## Review Scope

### 1. Seed Command Workflows (`seed_command_workflows.py`)

- **Missing**: No episode for `/feature-spec` command
- **Check**: Does the existing `workflow_overview` episode need updating to include the feature-spec flow?
- **Check**: Does the `workflow_feature_to_build` episode need a step for `/feature-spec` before `/feature-plan`?
- **Propose**: New episode(s) for `/feature-spec` covering:
  - Command purpose and syntax
  - Propose-Review methodology
  - Outputs (`.feature` files, test scaffolding, assumptions manifest, feature summary)
  - Integration with `/feature-plan` and AutoBuild

### 2. Seed Feature Build Architecture (`seed_feature_build_architecture.py`)

- **Check**: Does the current architecture seed capture the Coach's Promise Verification workflow?
- **Check**: Does it capture the Honesty Verification flow (Player → CoachVerifier → Coach)?
- **Check**: Does it describe how `/feature-spec` Gherkin becomes Coach validation criteria?

### 3. Assumptions Flow

- **Check**: Is the Assumptions Manifest (from `/feature-spec` D9) represented anywhere in the seed data?
- **Check**: Does the Coach validation seed describe checking assumptions vs implementation?
- **Assumption to verify**: The current seed data may assume the Coach only validates against acceptance criteria text, not structured Gherkin scenarios or assumption manifests

### 4. Autobuild Coach Seed Data

- **Check**: Are the Coach's new capabilities (criteria_verification, honesty_score) reflected in seed data?
- **Check**: Does any seed module describe the `completion_promises` → `criteria_verification` workflow?

## Acceptance Criteria

- [ ] Identify all seed modules that need updating for `/feature-spec`
- [ ] Identify all seed modules that need updating for Coach changes
- [ ] List specific episodes/content that should be added or modified
- [ ] Flag any assumptions in the current seed data that are now incorrect
- [ ] Provide a prioritised list of changes (must-have vs nice-to-have)
- [ ] Confirm whether the Assumptions Manifest workflow is captured anywhere

## Key Files to Review

| File | What to check |
|------|---------------|
| `guardkit/knowledge/seeding.py` | Orchestrator — any new seed modules needed? |
| `guardkit/knowledge/seed_command_workflows.py` | Missing `/feature-spec` episode |
| `guardkit/knowledge/seed_feature_build_architecture.py` | Coach Promise/Honesty verification |
| `guardkit/knowledge/seed_quality_gate_phases.py` | New quality gate phases from Coach changes |
| `.claude/agents/autobuild-coach.md` | Source of truth for Coach capabilities |
| `installer/core/commands/feature-spec.md` | Source of truth for `/feature-spec` command |
| `docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md` | Full feature spec including D9 (Assumptions) |
| `docs/commands/feature-spec.md` | Command reference documentation |

## Assumptions to Verify

1. The current seed data assumes no structured specification format exists for features
2. The current seed data assumes Coach validates against plain-text acceptance criteria only
3. The current seed data may not capture the Assumptions Manifest → Coach validation flow
4. The `seed_command_workflows` episodes were last updated before the `/feature-spec` command was added

## Success Metric

A clear, actionable list of seed function changes needed, with specific episode content proposals that can be implemented via `/task-work`.

## Suggested Review Approach

Use `/task-review TASK-REV-5FA4 --mode=architectural --depth=comprehensive` to systematically review each seed module against the current state of the codebase.
