# graphiti-core: `@handle_multiple_group_ids` Decorator Bug — Single Group ID Not Cloned

**Upstream Issue**: [getzep/graphiti#1161](https://github.com/getzep/graphiti/issues/1161)
**Upstream PR**: [getzep/graphiti#1170](https://github.com/getzep/graphiti/pull/1170)
**Affected Version**: graphiti-core v0.26.3 (and all prior versions with FalkorDB support)
**Graph Backend**: FalkorDB (FalkorDriver)
**Severity**: Critical — FalkorDB is unusable for multi-group workloads without fix

---

## Bug Summary

The `@handle_multiple_group_ids` decorator in `graphiti_core/decorators.py` only clones the FalkorDB driver when `len(group_ids) > 1`. For single `group_id` searches, it falls through to normal execution using `self.clients.driver` — which may have been mutated by a prior `add_episode()` call to point at a **different FalkorDB database**.

**One-line fix**: Change `len(group_ids) > 1` to `len(group_ids) >= 1` at `decorators.py` line ~53.

---

## Root Cause Analysis

### The Bug Location

**File**: `graphiti_core/decorators.py`, line 53

```python
# CURRENT (BUGGY):
if (
    hasattr(self, 'clients')
    and hasattr(self.clients, 'driver')
    and self.clients.driver.provider == GraphProvider.FALKORDB
    and group_ids
    and len(group_ids) > 1       # <-- BUG: should be >= 1
):
```

### The Driver Mutation

**File**: `graphiti_core/graphiti.py`, lines 860-861

When `add_episode()` is called, it permanently mutates the shared driver:

```python
async def add_episode(self, ..., group_id: str = ...):
    # ... (earlier code)
    self.driver = self.driver.clone(database=group_id)   # line 860
    self.clients.driver = self.driver                     # line 861
```

This mutation persists across method calls because `self.driver` is an instance attribute on the `Graphiti` object.

### The Interaction

1. `add_episode("ep1", group_id="A")` → `self.driver` mutated to point at database `A`
2. `search(query, group_ids=["A"])` → decorator sees `len(["A"]) == 1` → **falls through** → searches database `A` → **correct** (coincidence: driver already points at A)
3. `add_episode("ep2", group_id="B")` → `self.driver` mutated to point at database `B`
4. `search(query, group_ids=["A"])` → decorator sees `len(["A"]) == 1` → **falls through** → searches database `B` → **WRONG** (returns 0 results for group A)
5. `search(query, group_ids=["A", "B"])` → decorator sees `len > 1` → **clones per group** → searches correct databases → **correct**

The bug is non-deterministic in production: it only manifests when `add_episode()` is called with a different `group_id` before a single-group `search()`. This makes it especially insidious.

### Affected Methods

Four methods on the `Graphiti` class use `@handle_multiple_group_ids`:

| Method | Location | Impact |
|--------|----------|--------|
| `search()` | graphiti.py:~1293 | Primary search API — returns wrong results |
| `search_()` | graphiti.py:~1369 | Internal search variant — same bug |
| `retrieve_episodes()` | graphiti.py:~706 | Episode retrieval — returns wrong episodes |
| `build_communities()` | graphiti.py (class method) | Community building — builds on wrong data |

### Why Neo4j Is Not Affected

The condition explicitly checks for `GraphProvider.FALKORDB`. Neo4j does not use the `clone(database=group_id)` pattern — it handles multi-database differently. The entire `if` block is a FalkorDB-specific code path.

---

## The Fix

### One-Line Change

```diff
--- a/graphiti_core/decorators.py
+++ b/graphiti_core/decorators.py
@@ -50,7 +50,7 @@ def handle_multiple_group_ids(func: F) -> F:
             hasattr(self, 'clients')
             and hasattr(self.clients, 'driver')
             and self.clients.driver.provider == GraphProvider.FALKORDB
             and group_ids
-            and len(group_ids) > 1
+            and len(group_ids) >= 1
         ):
```

This ensures that even single `group_id` searches get a freshly cloned driver pointing at the correct FalkorDB database, rather than relying on the (potentially mutated) shared driver.

### Why `>= 1` and Not Removing the Length Check

The `and group_ids` check already handles `None` and empty list. The `len(group_ids) >= 1` is technically redundant with `and group_ids`, but keeping it:
1. Makes the intent explicit (process ALL non-empty group_id lists through the clone path)
2. Matches the existing code style
3. Is the minimal diff (one character change: `>` → `>=`)

---

## Reproduction

### Minimal Reproduction Script

```python
"""
Minimal reproduction of graphiti-core FalkorDB decorator bug.

Requires:
  - pip install graphiti-core[falkordb]
  - FalkorDB running on localhost:6379
  - OPENAI_API_KEY set (for LLM entity extraction)

Usage:
  docker run -d -p 6379:6379 falkordb/falkordb:latest
  python repro_decorator_bug.py
"""

import asyncio
import os
from datetime import datetime

from graphiti_core import Graphiti
from graphiti_core.llm_client import OpenAIClient, LLMConfig
from graphiti_core.driver.falkor_driver import FalkorDriver


async def reproduce():
    # Setup
    driver = FalkorDriver(
        host="localhost",
        port=6379,
        database=f"repro_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    )
    llm_client = OpenAIClient(
        LLMConfig(api_key=os.environ["OPENAI_API_KEY"])
    )
    g = Graphiti(graph_driver=driver, llm_client=llm_client)
    await g.build_indices_and_constraints()

    group_a = "group_a"
    group_b = "group_b"
    now = datetime.now()

    # Step 1: Add episode to Group A
    print("Adding episode to Group A...")
    await g.add_episode(
        name="ep1",
        episode_body="Alice is a software engineer at Acme Corp.",
        source_description="test",
        group_id=group_a,
        reference_time=now,
    )

    # Step 2: Search Group A — should find results
    result_1 = await g.search("Alice engineer", group_ids=[group_a])
    print(f"Search Group A (before mutation): {len(result_1.edges)} edges")
    # Expected: > 0 (driver happens to point at A after step 1)

    # Step 3: Add episode to Group B — THIS MUTATES self.driver TO POINT AT B
    print("Adding episode to Group B...")
    await g.add_episode(
        name="ep2",
        episode_body="Bob is a designer at Beta Inc.",
        source_description="test",
        group_id=group_b,
        reference_time=now,
    )

    # Step 4: Search Group A with SINGLE group_id — BUG MANIFESTS HERE
    result_2 = await g.search("Alice engineer", group_ids=[group_a])
    print(f"Search Group A (after mutation, single gid): {len(result_2.edges)} edges")
    # BUG: Returns 0 — searches Group B's database instead of Group A's

    # Step 5: Search Group A with MULTIPLE group_ids — works correctly
    result_3 = await g.search("Alice engineer", group_ids=[group_a, group_b])
    print(f"Search Group A+B (multi gid): {len(result_3.edges)} edges")
    # Correct: Returns > 0 — decorator clones driver for each group

    # Diagnostic: Show which database the driver is pointing at
    print(f"\nDriver database after all operations: {g.driver._database}")
    print(f"Expected: should not matter (decorator should clone)")
    print(f"Actual: points at Group B's database (mutation from step 3)")

    # Verdict
    if len(result_2.edges) == 0 and len(result_3.edges) > 0:
        print("\n** BUG CONFIRMED **")
        print("Single group_id search returns 0 results (wrong DB)")
        print("Multi group_id search returns correct results (decorator clones)")
    else:
        print("\nBug NOT reproduced (may be fixed upstream)")


if __name__ == "__main__":
    asyncio.run(reproduce())
```

### Expected vs Actual Output

**Expected** (with fix applied):
```
Adding episode to Group A...
Search Group A (before mutation): 2 edges
Adding episode to Group B...
Search Group A (after mutation, single gid): 2 edges    <-- CORRECT
Search Group A+B (multi gid): 3 edges
```

**Actual** (without fix):
```
Adding episode to Group A...
Search Group A (before mutation): 2 edges
Adding episode to Group B...
Search Group A (after mutation, single gid): 0 edges    <-- BUG
Search Group A+B (multi gid): 3 edges

** BUG CONFIRMED **
Single group_id search returns 0 results (wrong DB)
Multi group_id search returns correct results (decorator clones)
```

---

## Test Cases

### Test 1: Single Group ID After Driver Mutation (Bug Regression Test)

```python
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from graphiti_core.decorators import handle_multiple_group_ids
from graphiti_core.driver.driver import GraphProvider


def make_mock_graphiti(provider=GraphProvider.FALKORDB):
    """Create a mock Graphiti instance with FalkorDB provider."""
    mock = MagicMock()
    mock.clients = MagicMock()
    mock.clients.driver = MagicMock()
    mock.clients.driver.provider = provider
    mock.clients.driver.clone = MagicMock(
        return_value=MagicMock(name="cloned_driver")
    )
    mock.max_coroutines = None
    return mock


class TestHandleMultipleGroupIds:
    """Tests for the @handle_multiple_group_ids decorator."""

    def test_single_group_id_triggers_clone(self):
        """
        REGRESSION TEST: Single group_id MUST trigger driver clone.

        This is the core bug — single group_id falls through without
        cloning, using whatever database the driver was last mutated to.
        """
        @handle_multiple_group_ids
        async def search(self, query, group_ids=None, driver=None):
            return [f"result_from_{driver}"]

        mock_self = make_mock_graphiti()
        asyncio.run(search(mock_self, "test query", group_ids=["group_a"]))

        # CRITICAL ASSERTION: clone MUST be called for single group_id
        mock_self.clients.driver.clone.assert_called_once_with(database="group_a")

    def test_multiple_group_ids_clone_each(self):
        """Multiple group_ids should clone the driver for each group."""
        @handle_multiple_group_ids
        async def search(self, query, group_ids=None, driver=None):
            return ["result"]

        mock_self = make_mock_graphiti()
        asyncio.run(search(mock_self, "test", group_ids=["a", "b"]))

        assert mock_self.clients.driver.clone.call_count == 2

    def test_no_group_ids_falls_through(self):
        """No group_ids should fall through without cloning."""
        call_count = 0

        @handle_multiple_group_ids
        async def search(self, query, group_ids=None, driver=None):
            nonlocal call_count
            call_count += 1
            return ["result"]

        mock_self = make_mock_graphiti()
        asyncio.run(search(mock_self, "test"))

        mock_self.clients.driver.clone.assert_not_called()
        assert call_count == 1

    def test_empty_group_ids_falls_through(self):
        """Empty group_ids list should fall through without cloning."""
        call_count = 0

        @handle_multiple_group_ids
        async def search(self, query, group_ids=None, driver=None):
            nonlocal call_count
            call_count += 1
            return ["result"]

        mock_self = make_mock_graphiti()
        asyncio.run(search(mock_self, "test", group_ids=[]))

        mock_self.clients.driver.clone.assert_not_called()
        assert call_count == 1

    def test_neo4j_provider_not_affected(self):
        """Neo4j provider should not trigger the FalkorDB clone path."""
        call_count = 0

        @handle_multiple_group_ids
        async def search(self, query, group_ids=None, driver=None):
            nonlocal call_count
            call_count += 1
            return ["result"]

        mock_self = make_mock_graphiti(provider=GraphProvider.NEO4J)
        asyncio.run(search(mock_self, "test", group_ids=["group_a"]))

        mock_self.clients.driver.clone.assert_not_called()
        assert call_count == 1

    def test_sequential_add_then_search_different_groups(self):
        """
        End-to-end scenario: add_episode to group B, then search group A.

        Simulates the exact production failure pattern:
        1. add_episode(group_id="B") mutates self.driver to point at B
        2. search(group_ids=["A"]) should still search A (via clone)
        """
        search_results = {}

        @handle_multiple_group_ids
        async def search(self, query, group_ids=None, driver=None):
            # Record which driver was used for each search
            db_name = getattr(driver, '_database', 'unknown') if driver else 'shared'
            search_results[db_name] = True
            return [f"result_from_{db_name}"]

        mock_self = make_mock_graphiti()

        # Simulate driver mutation (what add_episode does)
        mock_self.clients.driver._database = "group_b_db"  # driver now points at B

        # Configure clone to return driver pointing at correct database
        def clone_side_effect(database=None):
            cloned = MagicMock()
            cloned._database = database
            return cloned

        mock_self.clients.driver.clone = MagicMock(side_effect=clone_side_effect)

        # Search for group A — should clone to A, NOT use B
        asyncio.run(search(mock_self, "test", group_ids=["group_a"]))

        mock_self.clients.driver.clone.assert_called_once_with(database="group_a")
```

### Test 2: Unit Test for the Fix (Can Run Without FalkorDB)

```python
def test_fix_applied_correctly():
    """
    Verify the fix: inspect decorator source for >= 1 condition.

    This test can be used post-fix to confirm the change was applied.
    """
    import inspect
    from graphiti_core.decorators import handle_multiple_group_ids

    source = inspect.getsource(handle_multiple_group_ids)

    # After fix: should contain >= 1
    assert "len(group_ids) >= 1" in source, (
        "Fix not applied: decorator still uses > 1 condition. "
        "Change line ~53 from 'len(group_ids) > 1' to 'len(group_ids) >= 1'"
    )

    # Should NOT contain the buggy > 1 (without >=)
    # Note: careful with this assertion — ">= 1" contains "> 1" as substring
    lines = source.split('\n')
    for line in lines:
        if 'len(group_ids)' in line and '> 1' in line and '>= 1' not in line:
            pytest.fail(
                f"Buggy condition found: {line.strip()}\n"
                "Expected: len(group_ids) >= 1"
            )
```

---

## Workaround (for consumers waiting on upstream fix)

GuardKit implements a monkey-patch workaround in `guardkit/knowledge/falkordb_workaround.py`:

```python
from guardkit.knowledge.falkordb_workaround import apply_falkordb_workaround

# Call once at startup, before creating any Graphiti clients
applied = apply_falkordb_workaround()
# Returns True if patch applied, False if graphiti-core not installed
```

**Key implementation detail**: Patching the decorator function on the `graphiti_core.decorators` module only affects NEW uses of the decorator. Methods already decorated at class definition time (during import) retain the OLD wrapper. The workaround must also re-decorate already-bound methods using `__wrapped__` (set by `functools.wraps`) to extract the original unwrapped function and re-apply the fixed decorator.

**Affected methods requiring re-decoration**:
- `Graphiti.search`
- `Graphiti.search_`
- `Graphiti.retrieve_episodes`
- `Graphiti.build_communities`

The workaround auto-detects the upstream fix and becomes a no-op when PR #1170 is merged.

---

## Impact Assessment

| Scenario | Impact |
|----------|--------|
| Single Graphiti instance, single group_id | **Works** (driver not mutated between calls) |
| Single Graphiti instance, multiple group_ids sequentially | **BROKEN** (driver mutated by add_episode) |
| Multiple Graphiti instances | **BROKEN** (each instance has own driver, but within an instance, mutation persists) |
| Neo4j backend | **Not affected** (decorator condition checks for FALKORDB provider) |
| Application with only one group_id ever | **Works** (driver always points at same DB) |
| Knowledge graph with multi-tenant data | **BROKEN** (different tenants = different group_ids) |

---

## Timeline

| Date | Event |
|------|-------|
| 2026-01-18 | Issue [#1161](https://github.com/getzep/graphiti/issues/1161) filed by `himorishige` |
| 2026-01-22 | PR [#1170](https://github.com/getzep/graphiti/pull/1170) submitted by `himorishige` (same fix) |
| 2026-02-11 | Independent reproduction and root cause confirmation (GuardKit team) |
| 2026-02-11 | Reproduction evidence added as [comment on #1161](https://github.com/getzep/graphiti/issues/1161#issuecomment-3887027878) |

---

## References

- **Upstream Issue**: https://github.com/getzep/graphiti/issues/1161
- **Upstream PR**: https://github.com/getzep/graphiti/pull/1170
- **GuardKit Workaround**: `guardkit/knowledge/falkordb_workaround.py`
- **Validation Script**: `scripts/graphiti-validation/validate_falkordb.py`
- **GuardKit Task**: TASK-FKDB-32D9
- **GuardKit Review**: TASK-REV-2A28
