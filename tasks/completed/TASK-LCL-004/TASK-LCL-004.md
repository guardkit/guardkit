---
id: TASK-LCL-004
title: Add pyproject.toml.template with [providers] extras to orchestrator template
status: completed
created: 2026-04-18T00:00:00Z
updated: 2026-04-18T00:00:00Z
completed: 2026-04-18T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/TASK-LCL-004/
priority: high
tags: [templates, langchain-deepagents-orchestrator, packaging, les1-provider-parity]
parent_review: TASK-REV-LES1
feature_id: FEAT-LTL1
implementation_mode: direct
wave: 2
conductor_workspace: langchain-template-lessons-wave2-1
complexity: 2
depends_on:
  - TASK-LCL-002
---

# Task: Add pyproject.toml.template with [providers] extras to orchestrator template

## Description

The `langchain-deepagents-orchestrator` template currently ships **no
packaging descriptor**. Its `.claude/CLAUDE.md` promises `pip install -r
requirements.txt` but no `requirements.txt.template` exists. Add a
`pyproject.toml.template` matching the base template's shape (per
TASK-LCL-002) and align the Quick Start.

## Acceptance Criteria

- [x] New file `installer/core/templates/langchain-deepagents-orchestrator/templates/other/other/pyproject.toml.template` that mirrors TASK-LCL-002's `[providers]` extras pattern (same version pins).
- [x] `dependencies` include `deepagents>=0.4.11`, `langchain>=1.2.11`, `langchain-core>=1.2.18`, `langgraph>=0.2`, `langchain-community>=0.3`, `python-dotenv>=1.0`, `pyyaml>=6.0`, plus a default provider (`langchain-anthropic>=0.2`).
- [x] `[project.optional-dependencies].providers` lists `langchain-openai>=0.2`, `langchain-google-genai>=2.0` (with a header comment citing LES1 §3 LCOI).
- [x] `dev` group includes `pytest>=9.0.2`.
- [x] `.claude/CLAUDE.md` "Quick Start" updated to `pip install .[providers]` — remove `pip install -r requirements.txt`.
- [x] `manifest.json` requires/frameworks metadata stays consistent with the pyproject (no drift).

## Files

- `installer/core/templates/langchain-deepagents-orchestrator/templates/other/other/pyproject.toml.template` (new)
- `installer/core/templates/langchain-deepagents-orchestrator/.claude/CLAUDE.md`

## Implementation Notes

Use TASK-LCL-002's pyproject as the source of truth — version pins must
match across the template family.

## Interface Contract

The `pyproject.toml.template` MUST produce, after rendering, a file that
passes `pip install .[providers]` in a fresh venv with Python 3.11+.
TASK-LCL-003's smoke test will verify this.

## Links

- Review: [TASK-REV-LES1 report §BLOCKER-2, §MEDIUM-4](../../../.claude/reviews/TASK-REV-LES1-review-report.md)
