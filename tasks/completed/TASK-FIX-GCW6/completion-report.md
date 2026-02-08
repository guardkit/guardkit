# Completion Report: TASK-FIX-GCW6

## Summary
Fixed the Graphiti client lifecycle bug where `get_graphiti()` always returned `None` during autobuild runs because `init_graphiti()` (async) was never called from any production code path.

## Solution: Lazy-Init in `get_graphiti()`
Implemented **Option 2** from the task description — added lazy initialization to `get_graphiti()` so the singleton auto-initializes from `load_graphiti_config()` on first access.

### Changes
| File | Action | Description |
|------|--------|-------------|
| `guardkit/knowledge/graphiti_client.py` | Modified | Added `_graphiti_init_attempted` flag, `_try_lazy_init()` function, modified `get_graphiti()` and `init_graphiti()` |
| `tests/knowledge/test_graphiti_lazy_init.py` | Created | 18 new tests covering all lazy-init paths |

### Key Design Decisions
1. **`_graphiti_init_attempted` flag** — prevents repeated connection attempts after failure (only tries once per process)
2. **Async/sync bridging** — detects running event loop via `asyncio.get_running_loop()`:
   - Sync context: uses `asyncio.run(client.initialize())`
   - Async context: creates client but defers connection (will connect on first async use)
3. **Graceful degradation** — returns `None` on any failure (ImportError, ConnectionError, disabled config)
4. **No changes to `autobuild.py`** — the existing auto-init block already calls `get_graphiti()`, which now lazy-inits

## Quality Gates
| Gate | Result |
|------|--------|
| New tests (lazy-init) | 18/18 passed |
| Existing context integration tests | 33/33 passed |
| Existing graphiti client tests | 48/48 passed + 2 skipped |
| Total related tests | 99 passed, 2 skipped, 0 failures |
| Regressions | None |

## Acceptance Criteria
- [x] `get_graphiti()` returns a usable client during autobuild when Graphiti/Neo4j is available
- [x] Auto-init block at `autobuild.py:594-608` successfully creates `AutoBuildContextLoader` when Graphiti is available
- [x] Graceful degradation preserved — no crash when Neo4j unavailable
- [x] Existing `guardkit graphiti` CLI commands continue to work (unchanged)
- [x] Tests cover: lazy-init success, lazy-init when Neo4j unavailable, singleton reuse, config loading
- [x] Init log correctly shows context_loader status when Graphiti is available
