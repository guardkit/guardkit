---
id: TASK-TI-029
title: Align pattern attribution in base and extension manifests
status: completed
created: 2026-03-30T12:00:00Z
updated: 2026-03-30T18:00:00Z
completed: 2026-03-30T18:00:00Z
completed_location: tasks/completed/TASK-TI-029/
priority: low
tags: [template, manifest, documentation, consistency]
task_type: implementation
complexity: 2
parent_review: TASK-REV-4F71
feature_id: FEAT-TI
implementation_mode: direct
wave: 5
depends_on: []
---

# Task: Align Pattern Attribution in Base and Extension Manifests

## Description

The extension manifest lists "HITL Checkpoints" and "Sprint Contracts" as extension-only patterns, but the underlying libraries (`lib/checkpoint_hooks.py`, `lib/sprint_contract.py`) live in the *base* template. The extension provides higher-level integration hooks in `hooks/` that wire these into the weighted evaluation pipeline.

This creates confusion about which template provides which capability.

## Finding Reference

TASK-REV-4F71, Finding F2 (LOW severity).

## What to Do

1. Add "HITL Checkpoints" and "Sprint Contracts" to the base template's `manifest.json` patterns array (since the base includes these libraries)
2. Update both CLAUDE.md files to clarify:
   - Base provides the *library* implementations (`lib/checkpoint_hooks.py`, `lib/sprint_contract.py`)
   - Extension provides the *integration hooks* (`hooks/hitl.py`, `hooks/sprint_contract.py`) that wire them into weighted evaluation
3. Optionally add a note in the extension manifest distinguishing inherited vs added patterns

## Acceptance Criteria

- [x] Base manifest patterns array includes "HITL Checkpoints" and "Sprint Contracts"
- [x] Both CLAUDE.md files clarify library vs integration hook distinction
- [x] No functional changes to either template
