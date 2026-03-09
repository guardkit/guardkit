---
id: TASK-RFX-5FED
title: Replace Graphiti turn state capture with local file-based approach
status: backlog
task_type: implementation
created: 2026-03-09T16:00:00Z
updated: 2026-03-09T16:00:00Z
priority: high
complexity: 5
wave: 2
implementation_mode: task-work
parent_review: TASK-REV-A8C6
feature_id: FEAT-RFX
tags: [autobuild, graphiti, turn-state, performance]
dependencies: []
---

# Task: Replace Graphiti Turn State Capture with Local File-Based Approach

## Description

Cross-turn Graphiti learning is 100% non-functional -- the `add_episode` LLM pipeline consistently exceeds the 30s hardcoded timeout on every turn. Replace the Graphiti-based capture/retrieve with local file-based approach using existing `work_state_turn_N.json` files. This saves ~30s per turn (3.5+ minutes per 7-turn run) and enables instant cross-turn context loading.

## Root Cause

`autobuild.py:3520` wraps `capture_turn_state()` with `asyncio.wait_for(..., timeout=30)`. The graphiti-core `add_episode` runs a full LLM extraction pipeline (entity extraction, edge extraction, node resolution, attribute extraction, embeddings, graph writes) requiring 4+ LLM calls that take 17-60+ seconds. The 30s timeout is structurally insufficient.

## Design: Option E (Local File-Based)

1. **Write path**: `MultiLayeredStateTracker.save_state()` already writes `work_state_turn_N.json` to `.guardkit/autobuild/{task_id}/`. Ensure this JSON includes all TurnStateEntity fields (Player summary, Coach decision, AC status, lessons learned, suggested focus).

2. **Read path**: Modify `load_turn_continuation_context()` in `turn_state_operations.py` to read from local `work_state_turn_N.json` files instead of querying Graphiti. Fall back to Graphiti query if local files are not found (backward compatibility).

3. **Remove Graphiti capture**: Remove or disable the `asyncio.wait_for(capture_turn_state(...), timeout=30)` call in `autobuild.py:3517-3520`. Optionally fire-and-forget the Graphiti write for cross-session learning.

## Acceptance Criteria

- [ ] `load_turn_continuation_context()` reads from local `work_state_turn_N.json` when available
- [ ] Local file read provides: Player summary, Coach decision, Coach feedback, blockers, lessons learned, suggested focus, AC status
- [ ] Falls back to Graphiti query if local files not found
- [ ] The 30s blocking `asyncio.wait_for(capture_turn_state(...))` is removed from the turn loop
- [ ] Optionally: fire-and-forget Graphiti `add_episode` for cross-session learning (non-blocking)
- [ ] Unit tests verify local file turn state loading
- [ ] Unit tests verify fallback to Graphiti when local files missing
- [ ] Integration test: multi-turn task context includes previous turn data
- [ ] Performance: turn state capture takes <1ms (local file write) vs previous 30s timeout

## Impact

- Saves ~30s per turn (~3.5 minutes on a 7-turn run like FEAT-2AAA)
- Enables cross-turn context that has never worked in production
- VID-005-style multi-turn tasks would get previous turn's Coach feedback and AC status
