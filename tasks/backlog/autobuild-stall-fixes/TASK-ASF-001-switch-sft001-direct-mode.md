---
id: TASK-ASF-001
title: Switch TASK-SFT-001 to direct implementation mode
task_type: configuration
parent_review: TASK-REV-SFT1
feature_id: FEAT-ASF
wave: 1
implementation_mode: direct
complexity: 1
dependencies: []
priority: critical
status: backlog
tags: [autobuild, stall-fix, R1, phase-1]
---

# Task: Switch TASK-SFT-001 to direct implementation mode

## Description

Change TASK-SFT-001's `implementation_mode` from `task-work` to `direct` in both the task spec and feature YAML. The task-work delegation path adds session preamble, skill expansion, and multi-phase workflow overhead that consumed the entire 1800s SDK timeout on Turns 2 and 4 (zero messages processed). Direct mode bypasses all of this — TASK-SFT-002 used direct mode and completed in 1 turn.

## Root Cause Addressed

- **F1**: Zero-message SDK timeouts caused by session preamble overhead (`agent_invoker.py:2536`)
- Direct mode uses `_invoke_player_direct()` which sends a custom prompt directly — no skill expansion, no `/task-work` command wrapping

## Files to Modify

1. `tasks/backlog/seam-first-testing/TASK-SFT-001-scaffolding.md` — Change `implementation_mode: task-work` to `implementation_mode: direct`
2. `.guardkit/features/FEAT-AC1A.yaml` — Change `implementation_mode: task-work` to `implementation_mode: direct` for TASK-SFT-001
3. `.guardkit/features/FEAT-AC1A.yaml` — Reset `status: failed` to `status: pending` for TASK-SFT-001 and feature level

## Acceptance Criteria

- [ ] TASK-SFT-001 `implementation_mode` is `direct` in task spec
- [ ] FEAT-AC1A YAML has `implementation_mode: direct` for TASK-SFT-001
- [ ] FEAT-AC1A status reset to `pending`
- [ ] TASK-SFT-001 status reset to `pending`
- [ ] TASK-SFT-001 `autobuild_state` cleared for fresh re-run

## Regression Risk

**None** — This only changes how TASK-SFT-001 is invoked. The direct path uses `_invoke_player_direct()` which sends a custom prompt with full requirements — no phases skipped, just no skill expansion overhead.

## Reference

- Review report: `.claude/reviews/TASK-REV-SFT1-review-report.md` (Finding 1, Recommendation R1)
- Diagnostic diagrams: `docs/reviews/feature-build/autobuild-diagnostic-diagrams.md` (Diagram 2, SDK_WRAP node)
