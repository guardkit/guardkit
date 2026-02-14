---
id: TASK-REV-A1E7
title: "Review /system-overview Graphiti integration and .env loading gap"
status: completed
created: 2026-02-12T12:45:00Z
updated: 2026-02-12T13:30:00Z
review_results:
  mode: architectural
  depth: standard
  findings_count: 5
  recommendations_count: 1
  decision: implement
  report_path: .claude/reviews/TASK-REV-A1E7-review-report.md
priority: medium
tags: [graphiti, dotenv, system-overview, review]
task_type: review
complexity: 4
---

# Task: Review /system-overview Graphiti integration and .env loading gap

## Description

The `/system-overview` command fails to load the OpenAI API key from the `.env` file when invoked outside the `guardkit` CLI entry point. The root cause is that `load_dotenv()` is only called in `guardkit/cli/main.py` (the CLI entry point), so any code path that calls `get_graphiti()` without going through the CLI will not have environment variables loaded from `.env`.

This review should analyse:

1. **The current .env loading architecture** — `load_dotenv()` is called only in `guardkit/cli/main.py:38`. All other entry points (direct Python imports, scripts, tests, `/system-overview` spec execution by Claude Code) bypass this.

2. **The /system-overview command's Graphiti usage** — The command spec instructs Claude to call `get_graphiti()` directly via Python. Since Claude Code executes this as inline Python (not via the `guardkit` CLI), `load_dotenv()` is never invoked.

3. **The two execution models** — The `guardkit` CLI (Click commands) vs Claude Code spec-driven commands (`.md` files read as prompts). The former loads `.env` via Click group init; the latter does not.

4. **Impact assessment** — Which other commands/integrations are affected by this gap?

## Acceptance Criteria

- [x] AC-001: Document all code paths that call `get_graphiti()` and whether they go through the CLI entry point
- [x] AC-002: Identify all spec-driven commands that use Graphiti and are affected by this gap
- [x] AC-003: Assess whether `load_dotenv()` should be added to `get_graphiti()` / `_try_lazy_init()` or to a shared init function
- [x] AC-004: Evaluate trade-offs of each fix approach (lazy dotenv in graphiti_client.py vs shared bootstrap vs other)
- [x] AC-005: Recommend a single fix approach with justification

## Key Files

- `guardkit/cli/main.py` — CLI entry point, only place `load_dotenv()` is called
- `guardkit/knowledge/graphiti_client.py` — `get_graphiti()`, `_try_lazy_init()`, OPENAI_API_KEY check at line 479
- `guardkit/knowledge/config.py` — `load_graphiti_config()`
- `installer/core/commands/system-overview.md` — Command spec

## Context

From investigation: the `.env` file exists at the project root with a valid `OPENAI_API_KEY` (164 chars). When `load_dotenv()` is called before `get_graphiti()`, the client initialises successfully (`Graphiti available: True`). The issue is purely about when/where `load_dotenv()` is invoked.

## Implementation Notes

This is a review-only task. Findings should recommend a fix approach for a follow-up implementation task.
