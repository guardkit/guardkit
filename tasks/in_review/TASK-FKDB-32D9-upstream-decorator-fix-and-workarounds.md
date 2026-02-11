---
id: TASK-FKDB-32D9
title: Fix upstream decorator bug and evaluate workarounds
status: completed
created: 2026-02-11T21:00:00Z
updated: 2026-02-11T20:47:00Z
priority: high
tags: [falkordb, upstream, graphiti, decorator, migration]
parent_review: TASK-REV-2A28
feature_id: FEAT-FKDB-001
implementation_mode: direct
wave: 0
complexity: 3
---

# Task: Fix upstream decorator bug and evaluate workarounds

## Description

File an upstream issue and PR on [getzep/graphiti](https://github.com/getzep/graphiti) for the `@handle_multiple_group_ids` decorator bug that blocks the FalkorDB migration (TASK-FKDB-001 AC-006). Evaluate local workaround options to unblock the migration while waiting for upstream acceptance.

## Acceptance Criteria

### Upstream Issue & PR

- [x] AC-001: Issue filed on `getzep/graphiti` with title, diagnostic evidence, and reproduction steps
  - **Already exists**: [Issue #1161](https://github.com/getzep/graphiti/issues/1161) filed by `himorishige` (2026-01-18)
  - Added independent reproduction evidence as [comment](https://github.com/getzep/graphiti/issues/1161#issuecomment-3887027878)

- [x] AC-002: PR submitted with one-line fix (`> 1` to `>= 1` in `decorators.py` line ~53) and regression test
  - **Already exists**: [PR #1170](https://github.com/getzep/graphiti/pull/1170) by `himorishige` (2026-01-22)
  - Exact same fix: `len(group_ids) > 1` → `len(group_ids) >= 1`
  - Open 3 weeks, no reviews as of 2026-02-11

- [x] AC-003: Issue body includes all required content
  - Issue #1161 contains: bug description, reproduction script, root cause analysis, proposed fix

### Workaround Evaluation

- [x] AC-004: Evaluate monkey-patch workaround — see Workaround Evaluation below
- [x] AC-005: Evaluate dual-group-id workaround — see Workaround Evaluation below
- [x] AC-006: Evaluate driver-reset workaround — see Workaround Evaluation below
- [x] AC-007: Recommend preferred workaround — **Option A (monkey-patch)** selected and implemented

### Re-validation

- [x] AC-008: Re-run `validate_falkordb.py` — **8/8 PASS** (2026-02-11T20:47Z). Required fix: re-decorate already-bound Graphiti methods (`search`, `retrieve_episodes`, `build_communities`, `search_`) via `__wrapped__` attribute, not just the module-level decorator function.

## Workaround Evaluation

### Option A: Monkey-patch decorator at import time (RECOMMENDED)

**Approach**: Replace `handle_multiple_group_ids` in `graphiti_core.decorators` module with a fixed version that uses `>= 1` instead of `> 1`. Applied automatically when `_check_graphiti_core()` runs (before any Graphiti client is created).

**Implementation**: `guardkit/knowledge/falkordb_workaround.py`
- `apply_falkordb_workaround()` — applies the patch (idempotent, safe to call multiple times)
- `is_workaround_applied()` — checks current state
- `remove_workaround()` — restores original decorator (testing only)
- Auto-detects if upstream fix already applied (skips patching)
- Auto-detects if source changed unexpectedly (warns and skips)

**Effort**: 30 minutes (completed)

**Risk**: LOW
- Self-contained in one file, easy to remove when upstream PR #1170 merges
- No changes to any of the 40+ `search()`/`add_episode()` call sites
- Idempotent — safe to call multiple times
- Auto-removes itself when upstream fix detected
- 14 tests covering all paths

**Pros**:
- Fixes root cause at the decorator level
- Zero changes to existing GuardKit code
- Easy removal: delete file + 2-line import in `graphiti_client.py`
- Auto-detects upstream fix (becomes no-op when fixed)

**Cons**:
- Monkey-patching is inherently fragile (source changes could break detection)
- Duplicates upstream code (needs monitoring when upgrading graphiti-core)

### Option B: Dual-group-id workaround

**Approach**: Always pass `[group_id, "__noop__"]` to `search()` to trigger the multi-group decorator path.

**Effort**: 15 minutes

**Risk**: MEDIUM
- Relies on unused group_id being harmless (FalkorDB creates a graph per group_id)
- Could create garbage `__noop__` graphs in FalkorDB
- Requires changes to all `search()` call sites (40+ locations)
- Performance overhead: executes search twice (once per group_id)
- `semaphore_gather` creates concurrent tasks — empty results from noop merged in

**Pros**:
- Simpler concept — no monkey-patching
- 15 minutes to implement

**Cons**:
- **40+ call sites** to modify — high blast radius
- Creates garbage FalkorDB graphs
- 2x search overhead (searches noop group every time)
- Hard to remove cleanly (must revert all 40+ call sites)
- Relies on assumption that empty-group searches are cheap

### Option C: Reset driver after each `add_episode()`

**Approach**: After each `add_episode()` call, reset `g.driver` back to the original database to prevent mutation from affecting subsequent `search()` calls.

**Effort**: 1 hour

**Risk**: HIGH
- Must identify and wrap every `add_episode()` call site (50+ locations)
- Easy to miss a call site (new code won't have the reset)
- Invasive — changes the driver lifecycle pattern
- Thread safety concerns with shared Graphiti instances
- Doesn't fix the root cause (decorator still broken for other usage patterns)

**Pros**:
- Prevents driver mutation side effect

**Cons**:
- **50+ call sites** to wrap
- Easy to forget in new code
- Doesn't fix the decorator — only addresses mutation side effect
- Thread-unsafe with `GraphitiClientFactory` (per-thread clients share nothing, but within a thread the reset could race with concurrent async operations)

### Recommendation

**Option A (monkey-patch)** is the clear winner:
1. Lowest risk — self-contained, no blast radius
2. Fixes root cause — same fix as upstream PR #1170
3. Easiest removal — delete one file when upstream merges
4. Auto-detection — becomes no-op when upstream fix is available
5. Zero existing code changes — all 40+ call sites work unmodified

## Files Created/Modified

- **NEW**: `guardkit/knowledge/falkordb_workaround.py` — Monkey-patch workaround module (decorator patch + method re-decoration)
- **NEW**: `tests/knowledge/test_falkordb_workaround.py` — 18 tests (6 apply, 5 behavior, 1 integration, 4 re-decoration, 2 upstream detection)
- **MODIFIED**: `guardkit/knowledge/graphiti_client.py` — 2 lines added in `_check_graphiti_core()`
- **MODIFIED**: `scripts/graphiti-validation/validate_falkordb.py` — Added workaround application before async checks

## Test Results

- 18 tests in `test_falkordb_workaround.py` — all passing (14 original + 4 re-decoration tests)
- 129 existing graphiti client tests — all passing (0 regressions)
- FalkorDB end-to-end validation: 8/8 PASS

## Gate Status

**COMPLETE**: All 8 TASK-FKDB-001 acceptance criteria pass. FalkorDB migration is UNBLOCKED.
- TASK-FKDB-001 AC-006: PASS (workaround applied)
- TASK-FKDB-002 through TASK-FKDB-008: UNBLOCKED

### Key finding during re-validation

The initial monkey-patch only replaced the decorator function on `graphiti_core.decorators` module. This was insufficient because `Graphiti.search` (and 3 other methods) were already decorated with the OLD decorator at class definition time (during import). Fix: also re-decorate already-bound methods using `__wrapped__` (set by `functools.wraps`) to extract the original unwrapped function and re-apply the fixed decorator.
