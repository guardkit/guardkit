---
id: TASK-FIX-GCI3
title: Wire --capture-knowledge flag in task-review CLI
status: completed
task_type: implementation
created: 2026-02-08T23:00:00Z
updated: 2026-02-09T00:00:00Z
completed: 2026-02-09T00:00:00Z
priority: high
parent_review: TASK-REV-C7EB
tags: [graphiti, task-review, cli, capture-knowledge]
complexity: 2
wave: 2
dependencies: [TASK-FIX-GCI2]
---

# Wire --capture-knowledge Flag in Task-Review CLI

## Description

The `--capture-knowledge` / `-ck` flag is specified in the task-review command spec and a parser exists (`ReviewCaptureConfig.from_args()` in `guardkit/knowledge/review_knowledge_capture.py`), but **nothing in the CLI layer calls it**. Grep for `capture_knowledge` in `guardkit/cli/` returns zero matches.

This task wires the flag through the CLI so that `/task-review TASK-XXX --capture-knowledge` triggers Phase 4.5: Knowledge Capture after the review completes.

## Existing Infrastructure

- `ReviewCaptureConfig.from_args(args)` - Parses `--capture-knowledge` and `-ck` flags
- `run_review_capture(task_context, review_findings, capture_knowledge)` - Main entry point
- `ReviewKnowledgeCapture` - Generates questions, runs abbreviated capture
- `InteractiveCaptureSession.run_abbreviated()` - Executes capture (must be fixed by GCI2 first)

## Changes Required

### 1. Add CLI flag to task-review command

In the task-review CLI handler (likely in `guardkit/cli/` or in the task-review skill spec), add:
```python
@click.option("--capture-knowledge", "-ck", is_flag=True, default=False,
              help="Trigger knowledge capture after review completes")
```

### 2. Call run_review_capture() after review completes

After the review phase produces findings:
```python
if capture_knowledge:
    from guardkit.knowledge.review_knowledge_capture import run_review_capture
    capture_result = await run_review_capture(
        task_context={"task_id": task_id, "review_mode": review_mode},
        review_findings={"mode": review_mode, "findings": findings},
        capture_knowledge=True
    )
```

### 3. Display capture results

Show whether knowledge was captured:
```
[Knowledge Capture] Captured 3 insights from architectural review
```
Or:
```
[Knowledge Capture] Skipped (Graphiti unavailable)
```

## CRITICAL: No Stubs Policy

**All code written for this task MUST be fully functional.** No placeholder methods, no pass-through flags that aren't connected to real logic. The flag must actually trigger `run_review_capture()` end-to-end.

## Graphiti API Reference

### run_review_capture() signature (the function to call)

```python
# guardkit/knowledge/review_knowledge_capture.py
async def run_review_capture(
    task_context: Dict[str, Any],     # Must include: task_id, review_mode
    review_findings: Dict[str, Any],  # Must include: mode, findings (list)
    capture_knowledge: bool           # True to run capture
) -> Dict[str, Any]:
    # Returns: {
    #   "capture_executed": bool,
    #   "task_id": str,
    #   "task_context": dict,
    #   "review_mode": str,
    #   "findings_count": int,
    #   "error": str (optional, if capture failed)
    # }
```

### Graceful degradation (mandatory)

```python
# run_review_capture() already handles graceful degradation internally.
# The CLI layer just needs to:
# 1. Pass the flag through
# 2. Display the result
# 3. NOT crash if capture fails
```

## Acceptance Criteria

- [x] `--capture-knowledge` / `-ck` flag accepted by task-review CLI
- [x] Flag triggers `run_review_capture()` after review completes
- [x] Review findings from the review phase are passed to `run_review_capture()`
- [x] Capture results displayed to user (captured count or skipped/failed message)
- [x] Flag is optional and defaults to False (no behaviour change without it)
- [x] Graceful handling when Graphiti unavailable (message to user, no crash)
- [x] Tests for CLI flag parsing and integration

## Files to Modify

- Task-review CLI handler or skill spec (identify exact location)
- New or updated tests for CLI integration

## Files for Reference (read before implementing)

- `guardkit/knowledge/review_knowledge_capture.py` - `run_review_capture()` and `ReviewCaptureConfig.from_args()`
- `guardkit/cli/autobuild.py` - Reference for how `--enable-context` flag is wired
- `guardkit/knowledge/interactive_capture.py` - `run_abbreviated()` (must be implemented by GCI2 first)

## Graphiti Documentation Reference

- `docs/guides/graphiti-integration-guide.md` - Integration patterns
