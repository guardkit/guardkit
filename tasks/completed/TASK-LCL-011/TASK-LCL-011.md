---
id: TASK-LCL-011
title: Align weighted-eval manifest pattern attribution with actual library location
status: completed
created: 2026-04-18T00:00:00Z
updated: 2026-04-18T00:00:00Z
completed: 2026-04-18T00:00:00Z
completed_location: tasks/completed/TASK-LCL-011/
previous_state: in_review
state_transition_reason: "Task complete — acceptance criteria met, Option B applied"
priority: low
tags: [templates, manifests, les1-doc-code-co-evolution]
parent_review: TASK-REV-LES1
feature_id: FEAT-LTL1
implementation_mode: direct
wave: 3
conductor_workspace: langchain-template-lessons-wave3-4
complexity: 1
---

# Task: Align weighted-eval manifest pattern attribution

## Description

`installer/core/templates/langchain-deepagents-weighted-evaluation/manifest.json`
lists "HITL Checkpoints" and "Sprint Contracts" in its `patterns` array.
TASK-REV-4F71 Finding F2 already noted these libraries live in the base
template (`lib/checkpoint_hooks.py`, `lib/sprint_contract.py`); the
extension only supplies the integration hooks. The `patterns_note` was
added, but the `patterns` array still claims ownership of inherited
patterns.

## Acceptance Criteria

- [ ] ~~Option A (preferred): Add "HITL Checkpoints", "Sprint Contracts" to the **base** template's `manifest.json` `patterns` array (since the base ships the libraries). Keep the extension's entries.~~ *(Not taken — base manifest already lists both patterns, and Option A does not resolve the extension's ownership claim.)*
- [x] **Option B applied**: Renamed extension's entries from `"HITL Checkpoints"` → `"HITL Hooks"` and `"Sprint Contracts"` → `"Sprint Contract Hooks"` to reflect that the extension adds integration hooks, not the patterns themselves. Matches existing CLAUDE.md terminology (`hooks/hitl.py`, `hooks/sprint_contract.py`).
- [x] `patterns_note` updated: now explicitly names the base-template libraries (`lib/checkpoint_hooks.py`, `lib/sprint_contract.py`) and the extension hook files (`hooks/hitl.py`, `hooks/sprint_contract.py`).
- [x] No behavioural change — metadata-only edit; zero code/test references to the renamed strings (verified via grep across `guardkit/`, `tests/`, template tree).

## Files

- `installer/core/templates/langchain-deepagents-weighted-evaluation/manifest.json` *(edited)*
- `installer/core/templates/langchain-deepagents/manifest.json` *(unchanged — already has HITL Checkpoints and Sprint Contracts)*

## Links

- Review: [TASK-REV-LES1 report §LOW-1](../../../.claude/reviews/TASK-REV-LES1-review-report.md)
- Prior review: [TASK-REV-4F71 Finding F2](../../../.claude/reviews/TASK-REV-4F71-review-report.md)
