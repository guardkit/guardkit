---
id: TASK-NIIF-003
title: Document --timeout override for local LLM users
status: completed
created: 2026-04-04T14:00:00Z
updated: 2026-04-04T16:00:00Z
completed: 2026-04-04T16:00:00Z
completed_location: tasks/completed/TASK-NIIF-003/
priority: low
tags: [docs, cli, timeout, local-llm]
parent_review: TASK-REV-2266
feature_id: FEAT-NIIF
implementation_mode: direct
wave: 2
complexity: 1
organized_files: ["TASK-NIIF-003.md"]
---

# Task: Document --timeout override for local LLM users

## Description

When using a local LLM (e.g., MacBook Pro instead of GB10 vLLM), episode creation timeouts are expected since the tiered timeout configuration is calibrated for GB10 performance. The `--timeout` CLI override exists but isn't discoverable.

Add guidance so users know to increase the timeout for local LLM scenarios.

## Acceptance Criteria

- [x] Add a note to `guardkit init --help` or init output about `--timeout` flag
- [x] Consider adding a hint in the timeout warning message suggesting `--timeout` usage
- [x] Document expected performance difference (local ~2x slower than GB10)

## Implementation Notes

The timeout override is at `graphiti_client.py:1172-1174`. The warning message at line 1213-1216 currently says "Episode creation timed out after Xs" — could append "Use --timeout to increase".
