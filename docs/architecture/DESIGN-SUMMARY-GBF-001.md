# Design Summary: Episode Serialization Unification (TASK-GBF-001)

**Prepared by:** Software Architecture Team
**Date:** 2026-02-07
**Status:** Design Complete - Ready for Implementation
**Review Status:** Pending Architect Approval

---

## Quick Reference

| Aspect | Current State | Proposed State | Impact |
|--------|---------------|----------------|--------|
| Serialization Paths | 3 (entity, client, manual) | 1 (client-level) | Simplified |
| Entity Return Types | Mixed (str + dict) | Unified (dict) | Type-safe |
| Metadata Injection | Multiple, inconsistent | Single, consistent | Maintainable |
| Double Injection Risk | Yes (seeding) | No | Reduced risk |
| Complexity Score | 4/10 (medium) | 4/10 (medium) | Same effort |
| Risk Level | Low | Low | No change |

---

## Design Documents

This design is documented across 4 comprehensive documents:

### 1. Architecture Decision Record (ADR)
**File:** `docs/architecture/ADR-GBF-001-unified-episode-serialization.md`

- **Purpose:** Formal architecture decision documentation
- **Content:** Status, context, decision rationale, consequences, alternatives
- **Audience:** Architects, senior engineers, decision makers
- **Key Decision:** Use client-level metadata injection as canonical pattern

**Key Extract:**
> The entity layer should define domain data structure via `to_episode_body()` returning clean dicts. The client layer (`GraphitiClient.add_episode()`) handles all metadata injection. This single point of injection ensures consistency and eliminates the dual-path problem.

### 2. Implementation Plan
**File:** `tasks/in_progress/TASK-GBF-001-IMPLEMENTATION-PLAN.md`

- **Purpose:** Detailed task breakdown and execution strategy
- **Content:** 6 deliverables, 14 files to modify, phase-by-phase plan
- **Audience:** Implementation engineers
- **Format:** Checklist-driven, 2-3 hour estimated duration

**Key Extract:**
> **Deliverable 1:** Entity Serialization Cleanup (8 files)
> - Remove all metadata fields from `to_episode_body()` returns
> - Convert `TaskOutcome` from `str` to `dict`
> - Keep only domain-specific fields

### 3. Design Document
**File:** `docs/architecture/DESIGN-GBF-001-episode-serialization-unification.md`

- **Purpose:** Comprehensive design explanation with context
- **Content:** Current analysis, proposed architecture, principles, examples
- **Audience:** Architects, implementers, code reviewers
- **Format:** Narrative with code examples and data flows

**Key Extract:**
> **Single Responsibility Principle:** Entity layer responsibility is to return clean domain data. Client layer responsibility is to generate and inject infrastructure metadata. This separation prevents concerns from mixing.

### 4. Visual Architecture
**File:** `docs/architecture/DESIGN-GBF-001-visual-architecture.md`

- **Purpose:** Diagrams and visual comparisons
- **Content:** ASCII diagrams, before/after comparisons, data structure examples
- **Audience:** Visual learners, code reviewers
- **Format:** Diagrams and structured tables

**Key Extract:**
> [Multiple ASCII diagrams showing current 3-path problem vs proposed single-path solution]

---

## Core Problem Statement

### The Issue

GuardKit has **three parallel serialization paths** for storing episodes in Graphiti:

```
Path 1: Entity embeds metadata
    TurnStateEntity.to_episode_body() → {"entity_type": "...", ...}

Path 2: Client injects metadata
    GraphitiClient.add_episode() → _inject_metadata() → metadata added

Path 3: Manual injection in seeding
    seed_helpers._add_episodes() → manually creates _metadata dict
    → THEN calls add_episode() which ALSO injects metadata
    → Result: DOUBLE INJECTION
```

### Why This Matters

1. **Maintenance Burden:** Three paths to maintain and test
2. **Inconsistency:** Entity bodies have different metadata fields
3. **Type Safety:** TaskOutcome returns `str` instead of `dict` (breaks pattern)
4. **Double Injection:** Seeding creates metadata twice (dict + markdown)
5. **Fragility:** Risk of divergence as codebase evolves

---

## Core Solution

### Single Canonical Pattern

**Use `GraphitiClient.add_episode()` as the ONLY point for metadata injection.**

### Entity Responsibility
```python
def to_episode_body(self) -> dict:
    """Return clean domain data (no metadata fields)."""
    return {
        "id": self.id,
        "feature_id": self.feature_id,
        # ... only domain fields
    }
```

### Client Responsibility
```python
async def add_episode(self, name, episode_body, group_id,
                     source, entity_type, entity_id):
    """Inject all metadata, then store."""
    body_dict = json.loads(episode_body)
    enriched = self._inject_metadata(body_dict, source, entity_type, entity_id)
    # Store enriched with _metadata section
```

### Result
```json
{
  // Domain fields from entity
  "id": "TURN-001",
  "feature_id": "FEAT-001",
  "turn_number": 1,

  // Metadata injected by client
  "_metadata": {
    "entity_id": "TURN-001",
    "entity_type": "turn_state",
    "source": "guardkit_seeding",
    "version": "1.0.0",
    "created_at": "2025-02-07T12:00:00Z",
    "updated_at": "2025-02-07T12:00:00Z",
    "source_hash": null
  }
}
```

---

## Implementation Overview

### 6 Deliverables

1. **Entity Cleanup** (8 files)
   - Remove metadata fields from `to_episode_body()` returns
   - Make all returns `dict` (not `str`)

2. **Seeding Helper** (1 file)
   - Remove manual metadata injection
   - Change signature: `_add_episodes(episodes)` where episodes are 4-tuples

3. **Seeding Call Sites** (6 files)
   - Update episode construction to include `entity_type` and `entity_id`

4. **Manager Call Sites** (2 files)
   - Ensure `add_episode()` calls pass `entity_type` parameter
   - Handle TaskOutcome's new dict return

5. **Tests** (1 file)
   - New `test_episode_serialization.py` with consistency tests

6. **Documentation** (docstrings + type hints)
   - Update all affected docstrings and type hints

### Execution Timeline

| Phase | Task | Duration | Risk |
|-------|------|----------|------|
| 1 | Entity cleanup | 40 min | Low |
| 2 | Seeding helper | 20 min | Low |
| 3 | Call sites (seeding) | 30 min | Low |
| 4 | Call sites (managers) | 20 min | Low |
| 5 | Tests + validation | 30 min | Low |
| **TOTAL** | | **2-2.5 hours** | **Low** |

---

## Architectural Principles Applied

### 1. Single Responsibility Principle ✓
- **Entity Layer:** Define and serialize domain data
- **Client Layer:** Handle infrastructure concerns (metadata)
- **Clear separation** prevents mixing concerns

### 2. Dependency Inversion ✓
- Entities don't depend on metadata generation logic
- Client doesn't depend on entity implementations
- Both depend on abstraction (dict interface)

### 3. Open/Closed Principle ✓
- Open for extension: Add new entities without changing existing code
- Closed for modification: Client metadata logic stays stable
- New entities just implement `to_episode_body()` → metadata automatically added

### 4. DRY (Don't Repeat Yourself) ✓
- Metadata injection logic in ONE place: `_inject_metadata()`
- No duplication across entity types
- No manual metadata dict construction

---

## Quality Attributes

### Maintainability: Improved
**Current:** Multiple paths with inconsistent patterns
**Proposed:** Single, consistent pattern
**Impact:** Easier to understand, easier to modify, fewer bugs

### Type Safety: Improved
**Current:** `to_episode_body()` returns `str` or `dict` (inconsistent)
**Proposed:** All return `dict` (consistent)
**Impact:** Type checkers can verify, fewer runtime surprises

### Consistency: Improved
**Current:** Entity bodies have different metadata fields
**Proposed:** No metadata in entity bodies (all injected by client)
**Impact:** Uniform structure, predictable behavior

### Simplicity: Improved
**Current:** Must choose between 3 serialization paths
**Proposed:** Single canonical path
**Impact:** Easier mental model, fewer decisions to make

### Extensibility: Improved
**Current:** New entities must decide which path to follow
**Proposed:** All new entities use same pattern
**Impact:** Faster development, fewer errors

---

## Risk Assessment

### Overall Risk Level: **LOW**

#### Why?
1. **Internal Only:** Refactoring doesn't change public APIs
2. **Isolated Scope:** Changes confined to entity layer + seeding layer
3. **Well-Tested:** Comprehensive test suite planned
4. **Incremental:** Phase approach allows verification at each step
5. **Reversible:** Changes can be rolled back if issues arise

#### Mitigation Strategies
1. Write tests before modifying implementation
2. Run full test suite after each phase
3. Code review at completion
4. Keep changes focused (no scope creep)

#### Rollback Plan
If critical issues discovered:
1. Revert entity changes
2. Revert seeding changes
3. Restore manual metadata injection
4. Post-mortem analysis

---

## Success Criteria

### Code Quality
- ✓ All `to_episode_body()` return `dict` (no `str`)
- ✓ No metadata fields in entity bodies
- ✓ Type hints correct and consistent
- ✓ Docstrings comprehensive

### Functionality
- ✓ All episodes properly stored with metadata
- ✓ No double metadata injection
- ✓ Metadata fields consistent across episodes
- ✓ All call sites updated

### Testing
- ✓ New consistency tests added and passing
- ✓ Existing tests still pass (no regressions)
- ✓ Coverage maintained or improved

### Review
- ✓ Architect approval
- ✓ Code review approval
- ✓ Documentation approval

---

## Files Created by Design Team

1. ✓ `docs/architecture/ADR-GBF-001-unified-episode-serialization.md`
   - Formal architecture decision record
   - Decision rationale and consequences
   - Alternatives considered

2. ✓ `tasks/in_progress/TASK-GBF-001-IMPLEMENTATION-PLAN.md`
   - Detailed task breakdown
   - 6 deliverables with specific files and changes
   - Phase-by-phase execution plan

3. ✓ `docs/architecture/DESIGN-GBF-001-episode-serialization-unification.md`
   - Comprehensive design explanation
   - Current architecture analysis
   - Proposed architecture with examples
   - Data flow examples

4. ✓ `docs/architecture/DESIGN-GBF-001-visual-architecture.md`
   - ASCII diagrams of current vs proposed
   - Before/after comparisons
   - Data structure examples
   - Migration examples

5. ✓ `docs/architecture/DESIGN-SUMMARY-GBF-001.md` (this file)
   - Executive summary
   - Quick reference table
   - Key documents and their purpose

---

## Dependencies & Assumptions

### Assumption 1: GraphitiClient API Support
**Assumption:** `GraphitiClient.add_episode()` can accept optional parameters:
- `source` (str)
- `entity_type` (Optional[str])
- `entity_id` (Optional[str])

**If not currently supported:** Minor enhancement needed before implementation

### Assumption 2: No External Dependencies
**Assumption:** No external code calls `_add_episodes()` with 2-tuple format

**Verification:** Search codebase for direct calls to `_add_episodes()`

### Assumption 3: Metadata Injection Already Works
**Assumption:** `GraphitiClient._inject_metadata()` already produces correct format

**Verification:** Review `_inject_metadata()` implementation before starting

---

## Next Steps

### For Architects
1. Review all 4 design documents
2. Approve or request modifications
3. Sign off on ADR-GBF-001

### For Implementation Team
1. Read implementation plan thoroughly
2. Understand architectural principles
3. Follow the 6 deliverables in order
4. Run tests frequently
5. Request code review at completion

### For Code Reviewers
1. Verify all metadata fields removed from entity bodies
2. Check all `to_episode_body()` methods return `dict`
3. Confirm all call sites pass `entity_type`
4. Review new test coverage

---

## Related Documentation

**Review Finding That Triggered This:**
- `tasks/backlog/TASK-REV-C632-graphiti-usage-baseline-analysis.md` (Finding 6)

**Implementation Task:**
- `tasks/in_progress/TASK-GBF-001-unify-episode-serialization.md`

**Graphiti Integration Guide:**
- `docs/deep-dives/mcp-integration/graphiti-integration.md`

**Entity Patterns:**
- `.claude/rules/patterns/pydantic-models.md`
- `.claude/rules/patterns/dataclasses.md`

---

## Decision Summary

| Decision Point | Option A | Option B | **Selected** | Rationale |
|---|---|---|---|---|
| **Metadata Injection Point** | Entity level | Client level (**selected**) | Separation of concerns, single point of injection |
| **Entity Return Type** | str (like TaskOutcome) | dict (unified (**selected**)) | Type consistency, easier to handle |
| **Seeding Call Signature** | 2-tuple (current) | 4-tuple (**selected**) | Explicit metadata parameters, no double injection |
| **Migration Approach** | All at once | Phased (**selected**) | Lower risk, allows verification between phases |

---

## Conclusion

The **unified episode serialization pattern** represents a significant improvement in code organization and maintainability. By consolidating metadata injection to a single client-level point, the design achieves:

- ✓ **Consistency:** All episodes have the same metadata structure
- ✓ **Maintainability:** Single path to maintain and test
- ✓ **Type Safety:** Consistent return types across all entities
- ✓ **Simplicity:** Clear separation of domain vs infrastructure concerns
- ✓ **Extensibility:** Easy to add new entities without special handling

The implementation is low-risk, well-scoped, and can be completed in 2-2.5 hours with high confidence.

---

**Prepared by:** Architecture Team
**Date:** 2026-02-07
**Status:** Ready for Implementation
**Next Review:** Code review after implementation
