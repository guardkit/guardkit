---
id: TASK-LCL-012
title: Add weighted-eval .env.example.template with extension-specific vars
status: completed
created: 2026-04-18T00:00:00Z
updated: 2026-04-18T00:00:00Z
completed: 2026-04-18T00:00:00Z
previous_state: in_review
state_transition_reason: "All acceptance criteria satisfied, 99/99 tests pass"
completed_location: tasks/completed/TASK-LCL-012/
priority: low
tags: [templates, langchain-deepagents-weighted-evaluation, env-hygiene, les1-env]
parent_review: TASK-REV-LES1
feature_id: FEAT-LTL1
implementation_mode: direct
wave: 3
conductor_workspace: langchain-template-lessons-wave3-5
complexity: 1
---

# Task: Add weighted-eval .env.example.template with extension-specific vars

## Description

The weighted-evaluation extension introduces `AcceptanceThreshold`,
`MaxRetries`, `AdversarialIntensity` placeholders, but does not ship its
own `.env.example.template`. Consumers relying on env-var override of these
runtime knobs have no documented surface.

## Acceptance Criteria

- [x] New `installer/core/templates/langchain-deepagents-weighted-evaluation/templates/other/other/.env.example.template` that overlays on top of the base `.env.example.template`.
- [x] File documents these env vars (even if only some are wired through code today — including them prepares for future env overrides):
  - `ACCEPTANCE_THRESHOLD` — overrides `adversarial_config.acceptance_threshold` (0.0-1.0)
  - `ADVERSARIAL_INTENSITY` — overrides `adversarial_config.intensity` (full | light | solo)
  - `MAX_RETRIES` — overrides `adversarial_config.max_retries` (positive integer)
- [x] Each var has a one-line comment explaining its effect and default.
- [x] No real-looking secrets (LES1 §3 hygiene) — only knobs and placeholders.
- [x] If the extension's `load_adversarial_config()` does not currently honour these env vars, add the env override (short — maybe 6 lines in `config/adversarial_config.py`). If the scope for the env-wiring is non-trivial, split it into a sub-task but keep this task focused on the `.env.example` surface.

## Implementation Notes

- Env wiring split into two blocks in `load_adversarial_config()`:
  - `ADVERSARIAL_INTENSITY` applied **before** `INTENSITY_OVERRIDES` selection so the correct bucket is used.
  - `ACCEPTANCE_THRESHOLD` / `MAX_RETRIES` applied **after** the bucket so shell overrides beat intensity presets (e.g. solo's 0.0 auto-accept).
- 4 new tests in `TestAdversarialConfig` cover each env var plus the threshold-vs-solo precedence case.
- New file added to `test_required_files_exist` parametrize so future template-validate runs catch deletions.

## Files

- `installer/core/templates/langchain-deepagents-weighted-evaluation/templates/other/other/.env.example.template` (new)
- `installer/core/templates/langchain-deepagents-weighted-evaluation/config/adversarial_config.py` (if env wiring added)

## Links

- Review: [TASK-REV-LES1 report §MEDIUM-3](../../../.claude/reviews/TASK-REV-LES1-review-report.md)
