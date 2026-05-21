---
id: TASK-HMIG-006.2
title: Migrate _extract_partial_from_messages / _track_tool_use to HarnessEvent dispatch
status: backlog
task_type: implementation
created: 2026-05-20T18:00:00Z
priority: high
complexity: 6
parent_task: TASK-HMIG-006
parent_review: TASK-REV-HMIG
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
intensity: standard
effort_hours: 5
depends_on:
  - TASK-HMIG-006   # Establishes the event taxonomy + raw channel
tags:
  - autobuild
  - harness
  - langgraph-migration
  - cutover-day-blocker
---

# Task: Migrate downstream helpers to HarnessEvent dispatch (restore byte-compat parity)

## Description

TASK-HMIG-006 Phase 3b kept `_extract_partial_from_messages`,
`_track_tool_use`, and `_emit_llm_call_event` operating on
`event.raw` (the original SDK message) per Design Decision D-1. This
keeps the SDK path byte-compatible and the AC-008 surface intact, at
the cost of LangGraph-path lossiness — these helpers return empty
lists / zero counts when `event.raw` is a LangChain result dict.

This task migrates the helpers to dispatch on `HarnessEvent` variants
directly (`AssistantMessageEvent.text`, future `ToolUseEvent` blocks),
so the LangGraph path achieves true byte-compat parity with the SDK
path.

## Why this is a separate task

Per the parent task implementation plan §4 D-1:

> AC-008 (existing tests pass under `GUARDKIT_HARNESS=sdk`) is the
> hardest gate. Existing tests patch `claude_agent_sdk.query` and feed
> `AssistantMessage(content=[TextBlock, ToolUseBlock])` shapes. If we
> migrate the downstream functions to HarnessEvent dispatch in this
> task, every test fixture changes.
>
> Migration of these helper functions to HarnessEvent dispatch is a
> separate task (`TASK-HMIG-006.2`) before the cutover-day flip.

## Cutover-day dependency

This task **must land before D-7 (2026-06-08)** — the day the default
`GUARDKIT_HARNESS` flips from `sdk` to `langgraph`. After the flip,
the LangGraph path becomes the primary substrate and lossy partial-
extract / progress logging is no longer acceptable.

## Acceptance Criteria

- [ ] AC-001: `_extract_partial_from_messages` reads from
      `HarnessEvent` variants (or a unified shape extracted at the
      harness boundary), not from `event.raw`. Output schema is
      unchanged.
- [ ] AC-002: `_track_tool_use` reads from `ToolUseEvent` blocks (which
      need to be emitted by both harnesses — Wave-2 SDK harness yields
      `AssistantMessageEvent` with raw=SDK message containing ToolUseBlocks;
      this task either (a) extends the SDK harness to break out
      `ToolUseEvent`s from the AssistantMessage, or (b) makes
      `_track_tool_use` consume the typed events). Pick (a) for
      symmetry with LangGraph and clean DIP.
- [ ] AC-003: The byte-compat parity tests at
      `tests/orchestrator/harness/test_byte_compat_parity.py`
      INVERT — the `TestDocumentedDivergences::test_tool_use_divergence_documented`
      assertion changes from `lg_partial["tool_call_count"] == 0` to
      `lg_partial["tool_call_count"] == 1` (parity). This inversion is
      the verifiable signal the migration is complete.
- [ ] AC-004: The Wave-2 divergences table in
      `guardkit/orchestrator/harness/README.md` updates to mark these
      rows as "Fixed in 006.2 (this task)".
- [ ] AC-005: AC-008 surface (existing 133 tests) continues to pass
      with `GUARDKIT_HARNESS=sdk`.
- [ ] AC-006: New tests verify `_track_tool_use` and
      `_extract_partial_from_messages` work end-to-end on the LangGraph
      path (no longer return empty lists for tool-use turns).

## References

- Parent task: [TASK-HMIG-006](../../design_approved/autobuild-harness-migration/TASK-HMIG-006-refactor-agent-invoker-cross-repo-dispatch.md)
- Implementation plan §4 D-1 (D-7 cutover blocker)
- Implementation plan §6 (byte-compat parity divergence-inversion contract)
- Wave-2 divergence table: `guardkit/orchestrator/harness/README.md`
