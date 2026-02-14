# Review Report: TASK-REV-2A28

## Review: FalkorDB Search Bug Resolution Research

**Mode**: Technical Decision | **Depth**: Standard | **Date**: 2026-02-11

---

## Executive Summary

The research documented in `falkordb-search-bug-resolution.md` is **methodologically sound** — all 9 upstream PR/issue references are verified as real and correctly described. However, the **root cause hypothesis was wrong**. Re-validation with graphiti-core v0.26.3 (which includes all three identified fixes) shows AC-006 **still fails**. The true root cause is a different bug entirely: the `@handle_multiple_group_ids` decorator in `graphiti_core/decorators.py` only clones the FalkorDB driver for `len(group_ids) > 1`, leaving single-group searches using a driver that was mutated by the prior `add_episode()` to point at the wrong database.

**Revised Decision: APPROVE research quality, MAINTAIN BLOCK.** The migration remains blocked by a newly-identified upstream decorator bug. Next step: file upstream issue/PR with one-line fix.

---

## Acceptance Criteria Results

| AC | Status | Summary |
|----|--------|---------|
| AC-001 | PASS | Research methodology validated — all PRs/issues verified against GitHub API |
| AC-002 | PASS (REVISED) | Root cause mapping assessed — identified fixes were real but NOT the actual root cause |
| AC-003 | PASS | Re-validation plan reviewed — script ran successfully, revealed true bug |
| AC-004 | PASS (REVISED) | Risk assessment evaluated — 20% residual risk materialized via a different bug |
| AC-005 | PASS (REVISED) | Decision: APPROVE research, MAINTAIN BLOCK, file upstream PR |
| AC-006 | PASS | Next steps documented — upstream issue/PR with one-line fix |

---

## AC-001: Research Methodology Validation

### PR/Issue Verification (via GitHub API)

Every PR and issue number referenced in the research was verified against the `getzep/graphiti` repository:

| Ref | Research Claim | Verified Title | Status | Release | Match |
|-----|---------------|----------------|--------|---------|-------|
| PR #835 | GraphID isolation for FalkorDB multi-tenant | "Add GraphID isolation support for FalkorDB multi-tenant architecture" | Merged | v0.23.0 (Nov 8 2025) | EXACT |
| PR #1050 | Enable FalkorDB fulltext search tests | "Enable FalkorDB fulltext search tests" | Merged | v0.23.0 | EXACT |
| PR #1013 | Fix entity edge save bug (source/target UUID None) | "Fix entity edge save" by @galshubeli | Merged | v0.23.1 (Nov 9 2025) | EXACT |
| Issue #1001 | Entity edge save bug report | "[BUG] add_triplet() does not save edges with FalkorDB provider" | Closed (Nov 17 2025) | Fixed by #1013 | MATCH |
| Issue #801 | group_ids filtering returns empty | group_ids filtering bug | Open, label: "bug" | Still open | MATCH |
| Issue #815 | BFS query syntax incompatibility | "[BUG] falkordb query" — Entity\|Episodic label union | Open | Still open | MATCH |
| PR #1105 | Fix search empty results after container restart | "fix(mcp): search returns empty results after container restart" | Open (NOT merged) | N/A | MATCH |
| PR #910 | Integrate MCP for FalkorDB | Listed in v0.23.0 release notes | Merged | v0.23.0 | MATCH |
| PR #911 | FalkorDB Docker Compose support | Listed in v0.23.0 release notes | Merged | v0.23.0 | MATCH |

**Assessment**: 9/9 references verified. All PR numbers, issue numbers, and descriptions match exactly. The research methodology is rigorous — every claim is traceable to a specific upstream artifact.

### Version Verification

| Claim | Verified |
|-------|----------|
| v0.24.3 is a real version | YES — published Dec 8 2025, contains PR #1093 + #1099 |
| v0.23.0 shipped FalkorDB fixes | YES — release notes confirm #835, #1050, #910, #911 |
| v0.23.1 fixed entity edge save | YES — release notes: "Fix entity edge save by @galshubeli in #1013" |
| FalkorDB is default MCP backend | YES — mcp-v1.0.0 tag published Oct 31 2025 |

---

## AC-002: Root Cause Mapping Assessment — REVISED

### Original Hypothesis (Research) vs Actual Root Cause

The research identified three upstream fixes and hypothesized they would resolve AC-006. **All three fixes are real and correctly described, but they did NOT fix AC-006.**

| Research Hypothesis | Actual Finding |
|--------------------|----|
| Index rebuild destroying data (#835) | NOT the cause — data is intact in correct FalkorDB databases |
| Entity edge save broken UUIDs (#1013) | NOT the cause — edges save correctly in v0.26.3 |
| Fulltext search tests now pass (#1050) | These tests likely don't cover the multi-group scenario |

### True Root Cause: `@handle_multiple_group_ids` Decorator Bug

**File**: `graphiti_core/decorators.py` line 53
**Verified in source**: v0.26.3 installed at `.venv/lib/python3.14/site-packages/graphiti_core/decorators.py`

**The bug**: The decorator condition `len(group_ids) > 1` (line 53) only clones the FalkorDB driver when multiple group_ids are passed. For single group_id searches, it falls through to line 96 (`return await func(self, *args, **kwargs)`) using `self.driver` directly — which was mutated by the prior `add_episode()`.

**The mutation mechanism** (verified in `graphiti.py` lines 858-861):
```python
# In add_episode():
if group_id != self.driver._database:
    self.driver = self.driver.clone(database=group_id)  # line 860
    self.clients.driver = self.driver                     # line 861
```

This means after `add_episode(group_id="B")`, `self.driver._database` is permanently set to "B". A subsequent `search(group_ids=["A"])` hits the decorator, which sees `len(["A"]) == 1` and falls through WITHOUT cloning, so it searches database "B" instead of "A".

**Proof from re-validation** (2026-02-11T20:12Z, graphiti-core v0.26.3):
```
Single group_id - Group A: 0, Group B: 1   ← BROKEN (searches wrong DB)
Multi  group_id - Both groups: 3            ← WORKS  (decorator clones correctly)
Current driver._database: fkdb_validation_b_20260211_201210  ← mutated to B
```

**Fix**: Change `len(group_ids) > 1` to `len(group_ids) >= 1` in `decorators.py` line 53.

### Why the Research Missed This

The research correctly identified real FalkorDB bugs that were fixed in v0.23.0-v0.23.1, but the AC-006 symptoms were coincidentally similar to what those bugs would produce. The research did not have access to a running FalkorDB instance to test the hypothesis — it was desk research based on PR descriptions and issue reports. The decorator bug is a separate, still-extant issue that manifests identically: "search returns 0 results after second add_episode()."

Key insight: FalkorDB uses **separate graph databases per group_id** (via `driver.clone(database=group_id)`). This is fundamentally different from Neo4j, which uses a shared database with group_id as a node property. The decorator pattern works for multi-group searches but has a gap for single-group searches after driver mutation.

---

## AC-003: Re-validation Plan Review

### Plan Outcome

The re-validation plan was sufficient to **run the test**, and the diagnostic additions to the validation script (Test 1 vs Test 2 comparison) were essential for isolating the true root cause. The research's recommendation to re-run the script was correct, even though the expected outcome ("AC-006 passes") did not materialize.

### Script Modifications Made (by user during re-validation)

The validation script was enhanced with:
1. **Test 1**: Single group_id search (reveals broken path)
2. **Test 2**: Multi group_id search (reveals working path via decorator clone)
3. **Driver state inspection**: `g.driver._database` printed to show mutation
4. **Diagnostic output**: Root cause identification when single fails but multi succeeds

These modifications were exactly the right diagnostic approach — they definitively proved the bug is in the decorator's group_id length check, not in index destruction or edge saves.

---

## AC-004: Risk Assessment Evaluation — REVISED

### What the Risk Assessment Got Right

The research identified a 20% residual risk that the bug would persist. That risk **materialized** — but via a completely different bug than anticipated.

### What It Missed

The research focused on risks related to the three identified fixes (#835, #1013, #1050). The actual persisting bug (`@handle_multiple_group_ids` decorator) was outside the scope of the research because:
1. It's not in any open issue or PR on graphiti-core (as of review date)
2. It only manifests with FalkorDB (Neo4j doesn't use per-group databases)
3. It requires multi-group `add_episode()` followed by single-group `search()` — a specific call pattern

### Updated Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Upstream rejects one-line fix PR | LOW (10%) | Migration stays blocked | Monkey-patch or dual-group workaround |
| Fix introduces regressions | LOW (5%) | Other FalkorDB users affected | Fix is additive (clone for ==1 where previously fell through) |
| Additional FalkorDB bugs exist | MEDIUM (25%) | New blockers after fix | Extended multi-episode test (5-10 episodes) should surface them |
| Performance impact of extra clone | NEGLIGIBLE | Slightly more memory per search | Clone is lightweight (copies connection params, not data) |

---

## AC-005: Decision — REVISED

### APPROVE Research Quality, MAINTAIN BLOCK, File Upstream PR

**Rationale**:

1. **Research methodology was excellent** (8.4/10): All PR/issue references verified, risk assessment was calibrated correctly (20% residual risk materialized), re-validation plan was actionable.

2. **Root cause hypothesis was wrong but reasonable**: The identified fixes genuinely addressed real FalkorDB bugs. The symptoms matched. Without a running FalkorDB instance, desk research could not have identified the decorator bug.

3. **True root cause is now confirmed**: The `@handle_multiple_group_ids` decorator bug is verified in source (decorators.py line 53) with diagnostic proof from re-validation.

4. **Fix is trivial**: One character change (`>` to `>=`) in a single line of `decorators.py`. Low risk of regression.

5. **Migration remains BLOCKED**: Until the decorator bug is fixed upstream (or patched locally), FalkorDB cannot support GuardKit's single-group search pattern.

---

## AC-006: Next Steps

### Immediate Actions (Ordered by Priority)

**Step 1: File upstream issue on graphiti-core** (P0)

File at https://github.com/getzep/graphiti/issues with:
- Title: `[BUG] FalkorDB: search(group_ids=["X"]) returns wrong results after add_episode() with different group_id`
- Body: Diagnostic evidence from re-validation, proposed one-line fix
- Labels: `bug`, `falkordb`

**Step 2: Submit upstream PR** (P0)

```python
# decorators.py line 53
# Before:
            and len(group_ids) > 1
# After:
            and len(group_ids) >= 1
```

Include the diagnostic test script as a regression test.

**Step 3: Evaluate workarounds while waiting** (P1)

Three workaround options if upstream PR takes time:

| Option | Approach | Effort | Risk |
|--------|----------|--------|------|
| A | Monkey-patch decorator at import time | 30 min | LOW — self-contained |
| B | Always pass `[group_id, "__noop__"]` to trigger multi-group path | 15 min | MEDIUM — relies on unused group being harmless |
| C | Reset `g.driver` after each `add_episode()` | 1 hr | HIGH — invasive, easy to miss call sites |

**Step 4: Re-validate after fix** (P1)

Once fix is applied (upstream or local patch), re-run `validate_falkordb.py` to confirm AC-006 passes, then run extended 5-10 episode test.

**Step 5: If all pass, unblock migration**

- Mark TASK-FKDB-001 AC-006 as PASS
- Update status from `blocked` to `completed`
- Unblock TASK-FKDB-002 through TASK-FKDB-008

---

## Appendix A: Version Timeline

```
v0.17.x (Jul 2025)  ← Estimated version when TASK-FKDB-001 first ran
    ... 15+ releases ...
v0.23.0 (Nov 8 2025) ← FIX: GraphID isolation (#835) + fulltext tests (#1050)
v0.23.1 (Nov 9 2025) ← FIX: Entity edge save (#1013)
v0.24.0 (Nov 14 2025)
v0.24.3 (Dec 8 2025) ← Research target version
    ... 7 releases ...
v0.26.3 (Jan 22 2026) ← Currently installed — @handle_multiple_group_ids bug STILL PRESENT
v0.27.0 (Feb 11 2026) ← Latest available — NOT checked, likely still has bug
```

## Appendix B: Research Quality Score (Revised)

| Criterion | Score | Notes |
|-----------|-------|-------|
| PR/Issue accuracy | 10/10 | Every reference verified |
| Root cause analysis | 5/10 | **REVISED**: Identified real bugs but wrong root cause for AC-006 |
| Version accuracy | 7/10 | Targeted v0.24.3; didn't check installed version (actually v0.26.3) |
| Risk calibration | 8/10 | **REVISED UP**: 20% residual risk was accurate — the bug DID persist |
| Actionability | 9/10 | Re-validation plan was executable and led to true root cause discovery |
| Workaround identification | 4/10 | **REVISED**: Proposed workaround (group_ids=["_"]) doesn't fix the decorator bug |
| Completeness | 5/10 | **REVISED**: Missed the decorator pattern entirely; FalkorDB per-group-database architecture not analyzed |

**Overall: 6.9/10 (revised from 8.4)** — Methodologically rigorous desk research, but incorrect root cause hypothesis. The research was nonetheless valuable: it verified that the originally-suspected bugs ARE fixed, narrowing the search space. The re-validation it recommended directly led to discovering the true root cause.

## Appendix C: Decorator Bug Source Verification

**File**: `.venv/lib/python3.14/site-packages/graphiti_core/decorators.py`

```python
# Lines 48-53 — the bug
if (
    hasattr(self, 'clients')
    and hasattr(self.clients, 'driver')
    and self.clients.driver.provider == GraphProvider.FALKORDB
    and group_ids
    and len(group_ids) > 1    # ← BUG: should be >= 1
):
```

**File**: `.venv/lib/python3.14/site-packages/graphiti_core/graphiti.py`

```python
# Lines 858-861 — the driver mutation that causes the bug
if group_id != self.driver._database:
    # if group_id is provided, use it as the database name
    self.driver = self.driver.clone(database=group_id)
    self.clients.driver = self.driver
```

The combination: `add_episode()` mutates `self.driver` (line 860-861), then `search()` with a single group_id doesn't clone (decorator line 53 condition fails), so it uses the mutated driver pointing at the wrong FalkorDB graph database.
