# Feature: Fix nats-infrastructure init failures

## Problem Statement

Running `guardkit init nats-asyncio-service` on the nats-infrastructure project produced YAML frontmatter parse failures on 9 rule files. The nats-asyncio-service template uses comma-separated quoted strings (`paths: "glob1", "glob2"`) which is invalid YAML — distinct from the unquoted glob bug fixed in TASK-NIF-001.

## Solution Approach

- Fix comma-separated quoted paths in 15 rule files across 4 templates (nats-asyncio-service, default, langchain-deepagents-orchestrator, fastmcp-python)
- Add path-gating validation to template-validate to catch this class of bug
- Document `--timeout` override for local LLM users

## Parent Review

TASK-REV-2266 — [Review Report](../../../.claude/reviews/TASK-REV-2266-review-report.md)

## Related Work

- TASK-NIF-001 (completed) — Fixed unquoted globs in python-library, langchain-deepagents, langchain-deepagents-orchestrator templates
- TASK-REV-A8C2 — Companion review for nats-core init failures

## Subtasks

| Task | Title | Wave | Mode | Priority |
|------|-------|------|------|----------|
| TASK-NIIF-001 | Fix comma-separated quoted paths in 4 templates (15 files) | 1 | direct | high |
| TASK-NIIF-002 | Add YAML paths validation to template-validate pipeline | 2 | task-work | medium |
| TASK-NIIF-003 | Document --timeout override for local LLM users | 2 | direct | low |

## Execution Strategy

**Wave 1** (immediate, 20 min): TASK-NIIF-001 — fix 15 rule files across 4 templates
**Wave 2** (backlog, parallel): TASK-NIIF-002 + TASK-NIIF-003 — independent improvements
