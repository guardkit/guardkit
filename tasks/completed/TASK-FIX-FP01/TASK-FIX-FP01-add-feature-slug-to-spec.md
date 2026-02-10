---
id: TASK-FIX-FP01
title: Add --feature-slug to feature-plan.md generate-feature-yaml examples
status: completed
created: 2026-02-10T12:00:00Z
updated: 2026-02-10T13:05:00Z
completed: 2026-02-10T13:05:00Z
priority: high
tags: [bug-fix, feature-plan, spec]
task_type: documentation
parent_review: TASK-REV-1BE3
feature_id: FEAT-FP-FIX
wave: 1
implementation_mode: direct
complexity: 1
dependencies: []
---

# Task: Add --feature-slug to feature-plan.md generate-feature-yaml examples

## Description

The `feature-plan.md` spec has example invocations of `generate-feature-yaml` that omit `--feature-slug`. Since the LLM follows these examples literally, this causes `file_path: .` in the generated YAML, which breaks autobuild.

## Changes Required

Update 3 locations in `installer/core/commands/feature-plan.md`:

1. **Line ~1723** (primary example): Add `--feature-slug "{feature_slug}"` to the bash code block
2. **Line ~1740** (OAuth example): Add `--feature-slug "oauth2"`
3. **Line ~1875** (walkthrough example): Fix the task format to match documented `ID:NAME:COMPLEXITY:DEPS` and add `--feature-slug`

Also ensure line 1719's comment about `--feature-slug` is consistent with the examples that follow it.

## Acceptance Criteria

- [x] All `generate-feature-yaml` invocations in feature-plan.md include `--feature-slug`
- [x] The walkthrough example at line ~1875 uses consistent task argument format
- [x] No other spec files reference generate-feature-yaml without --feature-slug

## Evidence

- Review report: `.claude/reviews/TASK-REV-1BE3-review-report.md`
- FEAT-CEE8 YAML showing `file_path: .`: `guardkit-examples/fastapi/.guardkit/features/FEAT-CEE8.yaml`
