# Implementation Guide: FalkorDB Timeout Fixes

**Feature ID**: FEAT-falkordb-timeout-fixes
**Parent Review**: TASK-REV-1F78
**Review Report**: `.claude/reviews/TASK-REV-1F78-review-report.md`

## Problem Summary

`guardkit init fastapi-python` Step 2.5 (template sync to Graphiti) takes ~113 minutes and produces 64 FalkorDB query timeouts, 33 connection closures, 30 vector embedding dumps, 5 failed episodes, and 5 unawaited coroutine warnings.

**Root Causes** (confirmed with high confidence):
1. **Upstream bug graphiti-core #1272**: `edge_fulltext_search` uses O(n×m) re-MATCH pattern instead of O(n) `startNode(e)/endNode(e)`, turning 2ms queries into 26-118s queries
2. **FalkorDB TIMEOUT=1000ms**: Server-side query timeout of 1 second is far too low for even legitimate graph operations
3. **Full markdown content synced**: `full_content` field in rule episodes causes excessive entity extraction, multiplying the number of FalkorDB queries per episode

## Wave Strategy

### Wave 1: Critical Fixes (Execute First)

These three tasks address the root causes directly. All are independent and can run in parallel.

| Task | Title | Mode | Complexity | Workspace |
|------|-------|------|------------|-----------|
| TASK-FIX-1136 | Patch edge_fulltext_search O(n×m) | task-work | 6 | falkordb-wave1-1 |
| TASK-FIX-fe67 | Raise FalkorDB TIMEOUT to 30000ms | direct | 1 | falkordb-wave1-2 |
| TASK-FIX-6e46 | Remove full_content from rule sync | direct | 2 | falkordb-wave1-3 |

**Expected Impact**: Step 2.5 time from ~6759s to ~60-120s. Query timeouts from 64 → 0.

**Parallel Execution**: All 3 tasks touch different files — safe to run in parallel via Conductor.

### Wave 2: Resilience & UX (Execute After Wave 1)

These tasks improve error handling and user experience. TASK-FIX-143c depends on TASK-FIX-1136.

| Task | Title | Mode | Complexity | Workspace |
|------|-------|------|------------|-----------|
| TASK-FIX-d457 | Fix add_episode return value checking | direct | 2 | falkordb-wave2-1 |
| TASK-FIX-72c1 | Suppress vector embedding logging | direct | 2 | falkordb-wave2-2 |
| TASK-FIX-143c | Add episode-level timeout | task-work | 3 | falkordb-wave2-3 |

**Dependencies**: TASK-FIX-143c depends on TASK-FIX-1136 (both modify `graphiti_client.py`)

**Parallel Execution**: TASK-FIX-d457 and TASK-FIX-72c1 can run in parallel. TASK-FIX-143c should run after TASK-FIX-1136 merges.

## Execution Strategy

### Recommended: Conductor Parallel Execution

```
Wave 1 (3 parallel workspaces):
  falkordb-wave1-1: /task-work TASK-FIX-1136    # Monkey-patch (task-work, complexity 6)
  falkordb-wave1-2: /task-work TASK-FIX-fe67     # Docker config (direct, complexity 1)
  falkordb-wave1-3: /task-work TASK-FIX-6e46     # Remove full_content (direct, complexity 2)

  → Merge all 3 → Redeploy FalkorDB on NAS → Verify with test init

Wave 2 (2 parallel + 1 sequential):
  falkordb-wave2-1: /task-work TASK-FIX-d457    # Return value check (direct, complexity 2)
  falkordb-wave2-2: /task-work TASK-FIX-72c1    # Suppress logging (direct, complexity 2)

  → Merge wave2-1 and wave2-2

  falkordb-wave2-3: /task-work TASK-FIX-143c    # Episode timeout (task-work, complexity 3)

  → Merge wave2-3 → Final verification
```

### Alternative: Sequential Execution

```
1. /task-work TASK-FIX-1136   # Most impactful — patch O(n×m) bug
2. /task-work TASK-FIX-fe67   # Quick config change
3. /task-work TASK-FIX-6e46   # Remove full_content
4. Test init to verify Wave 1 impact
5. /task-work TASK-FIX-d457   # Return value checking
6. /task-work TASK-FIX-72c1   # Suppress logging
7. /task-work TASK-FIX-143c   # Episode timeout
8. Final verification init
```

## File Conflict Analysis

| File | Tasks Touching It |
|------|-------------------|
| `guardkit/knowledge/falkordb_workaround.py` | TASK-FIX-1136 only |
| `docker/nas/docker-compose.falkordb.yml` | TASK-FIX-fe67 only |
| `docker/docker-compose.graphiti.yml` | TASK-FIX-fe67 only |
| `guardkit/knowledge/template_sync.py` | TASK-FIX-6e46, TASK-FIX-d457, TASK-FIX-72c1 |
| `guardkit/knowledge/graphiti_client.py` | TASK-FIX-1136, TASK-FIX-143c |
| `tests/knowledge/test_graphiti_client.py` | TASK-FIX-1136, TASK-FIX-143c |
| `tests/knowledge/test_template_sync.py` | TASK-FIX-6e46, TASK-FIX-d457 |

**Conflict zones**: `template_sync.py` is touched by 3 Wave 2 tasks (but different functions). `graphiti_client.py` is touched by TASK-FIX-1136 (Wave 1) and TASK-FIX-143c (Wave 2, which already depends on 1136).

## Verification Plan

### After Wave 1

```bash
# 1. Redeploy FalkorDB with new TIMEOUT
ssh richardwoollcott@whitestocks
cd /volume1/guardkit/docker && sudo docker-compose -f docker-compose.falkordb.yml up -d

# 2. Verify TIMEOUT setting
redis-cli -h whitestocks GRAPH.CONFIG GET TIMEOUT
# Expected: 30000

# 3. Run test init
guardkit init fastapi-python --project-dir /tmp/test-init

# 4. Check results
# - Step 2.5 should complete in ~60-120s (was 6759s)
# - No query timeout errors
# - No connection closure errors
```

### After Wave 2

```bash
# 1. Run test init again
guardkit init fastapi-python --project-dir /tmp/test-init-v2

# 2. Verify
# - Failed episodes log WARNING (not INFO success)
# - No vector embedding dumps in output
# - Any slow episodes timeout at 120s instead of hanging
# - Clean, readable output
```

## Expected Outcome

| Metric | Before | After Wave 1 | After Wave 2 |
|--------|--------|-------------|-------------|
| Step 2.5 duration | 6759s (~113 min) | ~60-120s | ~60-120s |
| Query timeouts | 64 | 0 | 0 |
| Connection closures | 33 | 0 | 0 |
| Vector dumps in output | 30 | 0 | 0 |
| Failed episode messages | 5 (logged as success) | 0-1 | 0-1 (logged as warning) |
| Total init time | ~120 min | ~8-10 min | ~8-10 min |
