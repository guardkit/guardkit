---
id: TASK-REV-OCRC
title: Diagnose orchestrator cancellation residual cleanup — `Task TASK-J004-013 not found in any state`
status: review_complete
task_type: review
review_mode: diagnostic
review_depth: quick
created: 2026-04-28T12:30:00Z
updated: 2026-04-28T13:05:00Z
priority: low
tags: [autobuild, review, sidequest, cancellation-bug, orchestrator-hygiene, FEAT-ABSR-9C6E-related]
parent_review: TASK-REV-WORS
related_reviews:
  - TASK-REV-WORS  # Surfaced this as a sidequest (orphan J004-013 START at events.jsonl line 49)
  - TASK-REV-COSE  # Sibling sidequest (Coach SDK opaque-stderr)
related_features:
  - FEAT-ABSR-9C6E  # autobuild-stall-resilience
complexity: 4
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: diagnostic
  depth: quick
  verdict: real-bug-confirmed
  findings_count: 3
  recommendations_count: 3
  decision: file-follow-up-implementation-task
  report_path: .claude/reviews/TASK-REV-OCRC-report.md
  completed_at: 2026-04-28T13:05:00Z
---

# TASK-REV-OCRC — Diagnose orchestrator cancellation residual cleanup

## Stakes

**Low priority sidequest.** Not blocking the demo. File and triage; full review only if confirmed real and worth fixing.

## Symptom

In `jarvis/.guardkit/autobuild/FEAT-J004-702C/events.jsonl`, the run-3 era of the file (after the run-2 wave-5 fail at line 44) shows an anomalous cluster:

```
Line 45: 2026-04-28T07:50:08.177Z  router  wave-1 record (queue_depth_start=4 end=0 completed=4)
Line 46: 2026-04-28T07:50:08.200Z  router  wave-2 record (queue_depth_start=5 end=0 completed=5)
Line 47: 2026-04-28T07:50:08.219Z  router  wave-3 record (queue_depth_start=1 end=0 completed=1)
Line 48: 2026-04-28T07:50:08.237Z  router  wave-4 record (queue_depth_start=2 end=0 completed=2)
Line 49: 2026-04-28T07:50:08.257Z  player  TASK-J004-013 START (orphan — no matching END)
```

These five events fire within an 80 ms window. Then 23 seconds later, line 50 emits the *actual* Wave 1 player START at 07:50:31.913. So waves 1-4 appear to be "completed" for an instant, then re-run from scratch.

The user reported a separate observation: attempt-1 of run-3 (~06:50 UTC, before this 07:50 cluster) was an accidental `--fresh` that was cancelled mid-clear, and the cancellation produced the runtime error:

```
Player failed: Unexpected error: Task TASK-J004-013 not found in any state
```

The hypothesis is that some state from prior `--fresh`/`--resume` attempts is being replayed before the fresh worktree is fully reset. This is *not* load-bearing for the Wave-4 failure documented in TASK-REV-WORS, but it's a real orchestrator hygiene bug.

## Investigation scope

### Quick triage (≤30 min)

1. **Read** `events.jsonl` lines 45-50 in detail. Confirm timestamp clustering and the orphan J004-013 START with no matching END.
2. **Find the code path** that emits router records on autobuild startup. Likely candidate: `autobuild.py` or `feature_orchestrator.py`. Search for places that emit "wave_id" event records.
3. **Determine whether the cluster is**:
   (a) A legitimate "summary of already-completed waves before resume" replay, OR
   (b) A bug where stale state from an earlier cancelled attempt is mis-attributed to the current attempt.
4. **Reproduce locally**: `guardkit autobuild feature FEAT-X --fresh`, cancel mid-startup with Ctrl-C, then `guardkit autobuild feature FEAT-X --fresh` again. Does the second run emit similar orphan records?

### If real bug confirmed (full review)

1. Identify the state-tracking module (probably `state_tracker.py` or `feature_orchestrator.py`).
2. Trace the cancellation path: when `--fresh` is interrupted mid-clear, what state remains?
3. Identify what causes the second `--fresh` to emit cached router records before the fresh start.
4. Recommend fix: either fully clear state on interrupted `--fresh`, OR don't emit router records for cached state when starting a new run, OR explicitly distinguish "resume" from "fresh" in the event journal.

## Acceptance criteria

- [ ] AC-001: Triage decision documented: real bug or normal replay-summary behaviour?
- [ ] AC-002: If real: full diagnostic with file:line evidence and recommended fix sketch.
- [ ] AC-003: If not real: documentation of the replay-summary semantics (so future readers don't get misled by similar clusters).
- [ ] AC-004: Cross-reference with [TASK-REV-WORS report v2 §3.3](../../.claude/reviews/TASK-REV-WORS-report.md#33-the-orphan-j004-013-start-at-075008-bug-to-file-as-sidequest) confirming this is the bug surfaced there.
- [ ] AC-005: Sidequest verdict: file follow-up implementation task (if real) or close (if not).

## Out of scope

- Wave-4 failure mode investigation — covered by [TASK-REV-WORS](../../.claude/reviews/TASK-REV-WORS-report.md).
- Coach SDK opaque-stderr bug — covered by TASK-REV-COSE.
- Any production-blocking work — this is a low-priority hygiene sidequest.

## Source artefacts

- `jarvis/.guardkit/autobuild/FEAT-J004-702C/events.jsonl` lines 44-50.
- User-reported terminal log from attempt-1 (~06:50 UTC) showing `Task TASK-J004-013 not found in any state`.
- Cross-reference: [TASK-REV-WORS report v2 §3.3](../../.claude/reviews/TASK-REV-WORS-report.md).
