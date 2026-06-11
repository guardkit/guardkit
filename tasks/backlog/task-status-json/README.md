# Feature: /task-status --json (FEAT-9DDE)

Add a `--json` flag to `/task-status` that emits the dashboard as machine-readable JSON.

## Problem

`/task-status` is a markdown-interpreted command — Claude formats the dashboard ad-hoc, so there is no way for scripts, CI pipelines, or other agents to consume task state programmatically. The local spec even advertises an `export:json` format that has no schema and no producer (a documented runner-without-producer orphan).

## Solution

A deterministic Python producer script (`task_status_json.py`) scans `tasks/{state}/` directories, parses frontmatter via the existing `task_utils.py`, and emits stable schema-v1 JSON. Both `task-status.md` specs instruct Claude to shell out to it and emit its stdout verbatim when `--json` is passed. Same pattern as the `/feature-plan` producers (R1/R2).

## Subtasks

| Task | Title | Mode | Complexity | Wave |
|---|---|---|---|---|
| TASK-TSJ-001 | Implement task-status-json producer script | task-work | 4 | 1 |
| TASK-TSJ-002 | Register bin entry and wire --json into specs | direct | 2 | 2 |

## Provenance

- Parent review: TASK-REV-9DDE ([report](../../../.claude/reviews/TASK-REV-9DDE-review-report.md))
- Context A: focus=all, trade-off=balanced
- Context B: approach=Option 1 (producer script), testing=standard

## Next Steps

```bash
/task-work TASK-TSJ-001        # Wave 1
/task-work TASK-TSJ-002        # Wave 2 (after TSJ-001 completes)
# or autonomous:
/feature-build FEAT-9DDE
```
