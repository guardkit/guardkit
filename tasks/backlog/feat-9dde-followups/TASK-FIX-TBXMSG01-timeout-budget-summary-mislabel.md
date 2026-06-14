---
id: TASK-FIX-TBXMSG01
title: TIMEOUT_BUDGET_EXHAUSTED summary box renders misleading "Unknown error occurred"
status: backlog
task_type: fix
created: 2026-06-14T11:10:00Z
updated: 2026-06-14T11:10:00Z
priority: low
complexity: 2
related: [TASK-PERF-SPECLAT01, FEAT-9DDE]
implementation_mode: task-work
tags: [autobuild, ux, summary, messaging, timeout-budget]
---

# Task: fix misleading summary message for timeout_budget_exhausted

## Why this task exists

When an autobuild task ends with decision `timeout_budget_exhausted`, the
final summary panel renders:

```
╭─ AutoBuild Summary (TIMEOUT_BUDGET_EXHAUSTED) ─╮
│ Status: TIMEOUT_BUDGET_EXHAUSTED               │
│ Unknown error occurred. Worktree preserved ... │
╰────────────────────────────────────────────────╯
```

The decision is a **clean, well-classified budget exhaustion** (the log is
explicit: `Timeout budget exhausted for TASK-XXX at turn N: remaining=<X>s <
min=600s`). Labelling it "Unknown error occurred" sends an operator chasing a
non-existent crash. The message should state that the task ran out of its time
budget and how (turns used, remaining vs minimum).

## Symptom

- Summary box for `timeout_budget_exhausted` shows the generic
  "Unknown error occurred. Worktree preserved for inspection."
- The structured log line one step earlier is precise
  (`Timeout budget exhausted ... remaining=397.4s < min=600s`), so the box
  message is purely a template/mapping gap.

## Evidence (run 6)
- `.guardkit/autobuild/FEAT-9DDE-run6-stdout.log` L580 (precise budget line)
  vs L613-615 (the misleading "Unknown error occurred" box).
- Preserved: `docs/retro/run6-evidence/FEAT-9DDE-run6-stdout.log`.

## Acceptance Criteria

- [ ] The summary panel for decision `timeout_budget_exhausted` shows a
      message that names the cause (time budget exhausted) and includes
      turns-used and remaining-vs-minimum, not "Unknown error occurred".
- [ ] Genuine unknown-error decisions still render the generic message.
- [ ] A unit test asserts the `timeout_budget_exhausted` decision maps to the
      budget message (and the unknown-error path is unchanged).

## Detection recipe
```bash
rg -n "Unknown error occurred" guardkit/orchestrator/
rg -n "timeout_budget_exhausted|TIMEOUT_BUDGET_EXHAUSTED" guardkit/orchestrator/ guardkit/cli/
```
