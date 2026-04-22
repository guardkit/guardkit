---
id: TASK-FP-NDG1
title: Add /feature-plan nudge when features/*.feature exists without any @task tags (interim R2 ergonomics)
status: backlog
task_type: implementation
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T00:00:00Z
priority: medium
complexity: 2
tags: [feature-plan, r2, ergonomics, nudge, interim, bdd-oracle]
parent_review: TASK-REV-4D190
feature_id: FEAT-R2GP
implementation_mode: direct
wave: 1
conductor_workspace: r2-pipeline-closure-wave1-r2-nudge
depends_on: []
---

# Task: Add /feature-plan nudge for missing @task: tags (interim R2 ergonomics)

## Problem Statement

Interim ergonomics step for the period between now and TASK-FP-LINK landing. If a user runs `/feature-plan` and there's an existing `features/*.feature` file with no `@task:` tags, they are one edit away from activating R2 — but they don't know that. Print a nudge.

This task ships fast (hours, not days). When TASK-FP-LINK lands, the nudge can either stay (as a fallback for edge cases where linking was skipped) or be removed.

## Scope

### In-Scope

- In `/feature-plan` (post-task-creation), detect whether a `features/*.feature` file exists for the feature.
- If it exists but contains zero `@task:` tag strings, print a clearly-formatted notice:

  ```
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ℹ️  BDD oracle (R2) not activated
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  A features/*.feature file was found but no scenarios carry @task:<TASK-ID> tags.
  Task-level BDD oracle (R2) will not fire during autobuild.

  To activate: edit features/<name>.feature and add @task:<TASK-ID> on the line
  above each Scenario: that should run for a given task.

  Example:
      @key-example @task:TASK-XXX-001
      Scenario: User signs in with valid credentials

  See installer/core/commands/feature-spec.md § "Task-scope tag convention".
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ```

- If the file exists and *some* scenarios have tags, no notice (partial activation is fine).
- If no `features/*.feature` exists, no notice.

### Out-of-Scope

- Any rewriting of the `.feature` file (that's TASK-FP-LINK).
- Scenario-to-task matching.
- Any change to R1 or R3 surfaces.

## Acceptance Criteria

- [ ] Notice fires when `features/*.feature` exists with zero `@task:` tags.
- [ ] Notice does not fire when file has at least one `@task:` tag.
- [ ] Notice does not fire when no `features/*.feature` exists.
- [ ] Notice text includes a copy-pasteable example and a link to the canonical docs.
- [ ] Unit test covers all three branches (missing file, tagged file, untagged file).
- [ ] Notice is suppressible via `--no-questions` or equivalent quiet flag (do not spam CI logs).

## Implementation Notes

- This is pure output text, no file mutation. Low risk.
- Place the detection near the end of `/feature-plan`, after task creation but before final summary, so the user sees it with the rest of the run report.
- When TASK-FP-LINK ships, this notice should only fire when LINK was unable to tag any scenarios (low-confidence, skipped by user in interactive mode). Coordinate the interaction in TASK-FP-LINK's implementation.

## Related

- Parent review: `docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md` (§Addendum A, Option 3)
- Follow-on companion: `TASK-FP-LINK` (the architectural fix)
- R2 task: `tasks/completed/TASK-BDD-E8954/TASK-BDD-E8954.md`
