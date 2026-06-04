---
id: TASK-HMIG-006.2
title: Migrate _extract_partial_from_messages / _track_tool_use to HarnessEvent dispatch
status: in_progress
task_type: implementation
created: 2026-05-20T18:00:00Z
updated: 2026-06-04T00:00:00Z
previous_state: backlog
state_transition_reason: "/task-work TASK-HMIG-006.2 execution"
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

- Parent task: [TASK-HMIG-006](../../completed/2026-05/TASK-HMIG-006-refactor-agent-invoker-cross-repo-dispatch.md)
- Implementation plan §4 D-1 (D-7 cutover blocker)
- Implementation plan §6 (byte-compat parity divergence-inversion contract)
- Wave-2 divergence table: `guardkit/orchestrator/harness/README.md`

---

## Implementation Plan (added 2026-06-04 — handoff brief for /task-work)

> **Context**: This task became unblocked after TASK-HMIG-009A AC-003 batch confirmed 83.3% any-turn-approve / 66.7% first-pass-success parity between SDK and LangGraph harnesses (canary-analysis.md §8.5). The Coach decision was harness-independent during the batch despite this task's helpers being lossy on the LangGraph path — meaning this fix is for **observability/parity quality**, not behavioural correctness. Still cutover-day-blocker per its frontmatter framing. Operator chose Option (a) from `/task-status` recommendation 2026-06-04: land 006.1/006.2/006.3 in sequence before cutover.

### Current code state (scanned 2026-06-04)

**Three call sites in `guardkit/orchestrator/agent_invoker.py` read `event.raw`** (the original SDK message, which is empty/dict on the LangGraph path):

| Line | Helper | What it reads from `event.raw` |
|---|---|---|
| 322  | `_extract_partial_from_messages(response_messages)` | Iterates SDK messages, extracts text + tool_call_count from `AssistantMessage.content` blocks |
| 1253 | `_track_tool_use(message)` | Walks `AssistantMessage.content` for `ToolUseBlock` instances, records tool names |
| 3053 | `_emit_llm_call_event(...)` | Reads `ResultMessage.usage` (token counts) from the raw message |

**Dispatch site** at `agent_invoker.py:2919` currently calls `self._track_tool_use(event.raw)` only when `isinstance(event, AssistantMessageEvent)`. Comment at line 2759-2762 explains the D-1 contract.

**Event variants** already defined in `guardkit/orchestrator/harness/adapter.py`:

```python
@dataclass(frozen=True)
class AssistantMessageEvent:  # line 34
    text: str
    raw: object | None = None

@dataclass(frozen=True)
class ToolUseEvent:  # line 48 — DEFINED BUT NOT YIELDED YET
    tool_use_id: str
    name: str
    input: dict[str, object]

@dataclass(frozen=True)
class ResultMessageEvent:  # line 80
    session_id: str | None
    stop_reason: str | None
    usage: dict[str, object] | None
    raw: object | None = None
```

**SDK harness shape** in `guardkit/orchestrator/harness/sdk_harness.py` (~lines 169-360):

- `invoke()` yields one `AssistantMessageEvent(text=joined_text, raw=message)` per assistant message
- Yields one terminal `ResultMessageEvent(session_id, stop_reason, usage, raw=message)`
- **Does NOT yield `ToolUseEvent`** — docstring line 39 calls this out as Wave-3 deferred work
- This task's AC-002 explicitly recommends approach (a): extend the SDK harness here.

**LangGraph harness** at `../guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py`: Wave-2 skeleton yields one `AssistantMessageEvent` + one `ResultMessageEvent`. **Also needs `ToolUseEvent` yields** for parity. Cross-repo change required.

**Inversion test** at `tests/orchestrator/harness/test_byte_compat_parity.py`:

- Line 313: `assert sdk_partial["tool_call_count"] == 1` (SDK path counts tool uses today)
- Line 321: `assert lg_partial["tool_call_count"] == 0` ← **FLIP TO `== 1` per AC-003**

### Step-by-step execution order

**Step 1: extend SDK harness to yield ToolUseEvent** (guardkit, ~30min)

In `sdk_harness.py:invoke()`, when processing an `AssistantMessage`, iterate its `content` list. For each `ToolUseBlock`, yield a `ToolUseEvent(tool_use_id=block.id, name=block.name, input=block.input)` BEFORE the `AssistantMessageEvent` yield. Keep the existing `AssistantMessageEvent(text=joined_text, raw=message)` yield unchanged — downstream consumers will see ToolUseEvents in addition to AssistantMessageEvents and dispatch correctly.

**Step 2: parallel SDK-shape change in LangGraphHarness** (guardkitfactory, ~30min)

In `../guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py:invoke()`, parse the DeepAgents result stream for tool-call entries and yield `ToolUseEvent` for each, before the terminal `ResultMessageEvent`. The DeepAgents result dict has tool call info under `messages` → look for `AIMessage.tool_calls` (LangChain shape) and map to ToolUseEvent. Cross-repo PR/commit.

**Step 3: migrate `_track_tool_use` to consume ToolUseEvent** (guardkit, ~45min)

- `_track_tool_use(message)` at line 1253 — change signature to `_track_tool_use(event: ToolUseEvent)`. Strip the `AssistantMessage.content` walk; directly record `event.name`, `event.tool_use_id`.
- Dispatch site at line 2919: replace `if isinstance(event, AssistantMessageEvent): self._track_tool_use(event.raw)` with `elif isinstance(event, ToolUseEvent): self._track_tool_use(event)`. The AssistantMessageEvent branch stops calling `_track_tool_use` — that's now a separate event-type case.

**Step 4: migrate `_extract_partial_from_messages` to event-list dispatch** (guardkit, ~45min)

- Change `_extract_partial_from_messages(response_messages: List[Any])` at line 322 to accept the event list and dispatch on event types. For text content read `AssistantMessageEvent.text`; for tool_call_count count `ToolUseEvent` instances. The `response_messages` list can stay populated (it's used for backward-compat with SDK debug preservation), but the helper consumes events now.
- Call site at line 2968: pass the events list (already collected in the loop) instead of `response_messages` derived from `event.raw`.

**Step 5: migrate `_emit_llm_call_event` to read from ResultMessageEvent** (guardkit, ~30min)

- `_emit_llm_call_event` at line 3053 currently reads token usage from `event.raw.usage`. Change to read from `ResultMessageEvent.usage` (already populated by both harnesses). Call site at line 2997 changes accordingly.

**Step 6: invert the byte-compat parity test** (guardkit, ~10min — the verifiable AC-003 signal)

- `tests/orchestrator/harness/test_byte_compat_parity.py:321`: change `assert lg_partial["tool_call_count"] == 0` → `assert lg_partial["tool_call_count"] == 1, "TASK-HMIG-006.2 migration: LangGraph now counts tool uses via ToolUseEvent dispatch"`.
- Search the file for any other `== 0` divergence assertions covering the same helpers; flip those too.
- The `TestDocumentedDivergences::test_tool_use_divergence_documented` test name itself may want renaming (no longer "divergence") — optional polish.

**Step 7: AC-005 regression run** (guardkit, ~30min — the load-bearing risk)

- `pytest tests/orchestrator/` under `GUARDKIT_HARNESS=sdk` (or no env, since sdk is default).
- The 133-test AC-008 surface must still pass. Risk: tests that patch `claude_agent_sdk.query` with `AssistantMessage(content=[TextBlock, ToolUseBlock])` and then check downstream tool tracking. With Step 1's change, the SDK harness now ALSO yields ToolUseEvents for the patched ToolUseBlocks. If any test asserts on the exact event sequence (rare), it'll need updating. More likely: tests assert on the resulting `_track_tool_use` state, which should be unchanged since both old (`event.raw` walk) and new (ToolUseEvent dispatch) paths count the same blocks.
- If tests break: fix the test fixtures, not the new dispatch — the old SDK-shape tests were testing the WRONG abstraction (raw SDK objects); the new shape is the abstraction we want long-term.

**Step 8: new tests for LangGraph parity** (guardkit, ~30min — AC-006)

- Add tests under `tests/orchestrator/harness/` that exercise `_track_tool_use` + `_extract_partial_from_messages` against synthetic `ToolUseEvent` streams (no SDK message required). Verify non-zero counts where they would have been zero on the old LangGraph path.

**Step 9: documentation** (~15min — AC-004)

- `guardkit/orchestrator/harness/README.md` divergence table: mark the rows for `_extract_partial_from_messages` / `_track_tool_use` as "Fixed in 006.2".

### Cross-repo coordination

This task spans **two repos**. Recommended commit/PR pattern:

1. Commit guardkitfactory's LangGraphHarness ToolUseEvent extraction (Step 2) FIRST, pinned to a version tag.
2. Update guardkit's pyproject.toml to require that version (or rely on editable install).
3. Commit guardkit's changes (Steps 1, 3-9) referencing the guardkitfactory commit hash.
4. Verify the inverted byte-compat parity test runs green against both packages installed.

### Effort estimate

- Steps 1+2 (event yields): ~1h
- Steps 3-5 (helper migration): ~2h
- Steps 6-9 (test + docs): ~1.5h
- AC-005 regression fixing if breaks: ~30min-1h buffer
- **Total: ~5h** — matches spec's `effort_hours: 5`

### What "done" looks like

- ✅ AC-003 falsifier flipped: `lg_partial["tool_call_count"] == 1` (was `== 0`) is the verifiable signal.
- ✅ AC-005 regression: 133-test AC-008 surface still passes under `GUARDKIT_HARNESS=sdk`.
- ✅ AC-006: new tests prove LangGraph parity end-to-end.
- ✅ Both repos updated; cross-repo install verified.

### Next task in cutover chain (after this lands)

Per operator's 2026-06-04 Option (a) choice: TASK-HMIG-006.3 (Coach independent SDK invocation migration) → TASK-HMIG-006.1 (direct-mode TaskWork dispatch migration) → TASK-HMIG-010 (full feature validation) → cutover ceremony (no dedicated task file yet — confirm with parent review §7.3 Wave 4).
