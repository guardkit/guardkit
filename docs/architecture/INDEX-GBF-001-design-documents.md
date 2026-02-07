# Design Documentation Index: TASK-GBF-001

## Overview

Complete design documentation for **TASK-GBF-001: Unify Episode Serialization Pattern Across Entities**

All documents are ready for implementation. Start with the summary, then dive into specific documents as needed.

---

## Document Guide

### 1. Executive Summary (Start Here)
**File:** `DESIGN-SUMMARY-GBF-001.md`
**Length:** 3-4 pages
**Audience:** Everyone
**Key Sections:**
- Quick reference table
- Core problem statement
- Core solution
- Risk assessment
- Success criteria

**When to Read:** First - gives you the 30-second version

---

### 2. Architecture Decision Record (For Architects)
**File:** `ADR-GBF-001-unified-episode-serialization.md`
**Length:** 5-6 pages
**Audience:** Architects, decision makers
**Key Sections:**
- Status: Proposed
- Context (current problems)
- Decision (use client-level injection)
- Consequences (positive/negative)
- Alternatives considered
- Implementation strategy

**When to Read:** After summary - formal architecture decision

**Key Decision:**
> Use `GraphitiClient.add_episode()` as the single point for metadata injection. Entities return clean domain data via `to_episode_body()`.

---

### 3. Comprehensive Design Document (For Implementers)
**File:** `DESIGN-GBF-001-episode-serialization-unification.md`
**Length:** 8-10 pages
**Audience:** Implementation engineers, code reviewers
**Key Sections:**
- Executive summary
- Current architecture analysis (3-path problem)
- Proposed architecture (single path)
- Architectural principles applied (SOLID)
- Type system changes
- Data flow examples (2 detailed examples)
- Testing strategy
- Implementation checklist
- Risk assessment

**When to Read:** Before implementation - deep understanding

**Key Concepts:**
- Current: 3 parallel serialization paths
- Proposed: 1 canonical client-level path
- Benefit: Consistency, maintainability, type safety

---

### 4. Visual Architecture (For Visual Learners)
**File:** `DESIGN-GBF-001-visual-architecture.md`
**Length:** 6-8 pages
**Audience:** Everyone (especially visual learners)
**Key Sections:**
- Current state diagram (dual paths problem)
- Proposed state diagram (single path solution)
- Entity serialization before/after comparison
- Metadata injection flow comparison
- Seeding helper transformation
- Data structure changes (Graphiti episode structure)
- Summary table: current vs proposed

**When to Read:** Alongside comprehensive design - complements written documentation

**Visual Elements:**
- ASCII diagrams of current vs proposed
- Before/after comparison tables
- Migration examples with code

---

### 5. Implementation Plan (For Execution)
**File:** `../../../tasks/in_progress/TASK-GBF-001-IMPLEMENTATION-PLAN.md`
**Length:** 10-12 pages
**Audience:** Implementation engineers
**Key Sections:**
- Overview (complexity 4/10, 2-3 hours)
- Architecture decision summary
- Scope & deliverables (6 deliverables, 14 files)
- Refactoring patterns
- Special case: TaskOutcome (str → dict conversion)
- Implementation order (5 phases)
- Acceptance criteria mapping
- Testing strategy
- Risk analysis
- Success metrics
- Notes for implementation

**When to Read:** Start of implementation - your detailed task breakdown

**Key Structure:**
```
Deliverable 1: Entity cleanup (8 files, 40 min)
Deliverable 2: Seeding helper (1 file, 20 min)
Deliverable 3: Seeding call sites (6 files, 30 min)
Deliverable 4: Manager call sites (2 files, 20 min)
Deliverable 5: Consistency tests (1 file, 30 min)
Total: 2-2.5 hours
```

---

### 6. Implementation Checklist (For Execution)
**File:** `IMPLEMENTATION-CHECKLIST-GBF-001.md`
**Length:** 8-10 pages
**Audience:** Implementation engineers
**Key Sections:**
- Pre-implementation verification
- Phase 1-6 detailed checklists (✓ boxes)
- Troubleshooting guide
- File changes summary table
- Time breakdown
- Sign-off & completion

**When to Read:** During implementation - check off items as you complete them

**Usage:**
- Open in split window while coding
- Check off items as completed
- Use for progress tracking
- Reference troubleshooting if issues arise

---

## Quick Navigation

### By Role

**If you are an ARCHITECT:**
1. Read: DESIGN-SUMMARY-GBF-001.md (overview)
2. Read: ADR-GBF-001 (decision record)
3. Review: DESIGN-GBF-001 (comprehensive)
4. Approve/reject architecture

**If you are an IMPLEMENTER:**
1. Read: DESIGN-SUMMARY-GBF-001.md (overview)
2. Read: DESIGN-GBF-001-visual-architecture.md (visualize)
3. Read: TASK-GBF-001-IMPLEMENTATION-PLAN.md (detailed plan)
4. Use: IMPLEMENTATION-CHECKLIST-GBF-001.md (during work)
5. Request code review

**If you are a CODE REVIEWER:**
1. Skim: DESIGN-SUMMARY-GBF-001.md (context)
2. Reference: DESIGN-GBF-001 (details on decisions)
3. Check: IMPLEMENTATION-CHECKLIST-GBF-001.md (verify all items done)
4. Review: Code changes against checklist

**If you are a TESTER:**
1. Read: DESIGN-GBF-001-visual-architecture.md (understand changes)
2. Focus: Section on "Testing Strategy" in DESIGN-GBF-001.md
3. Reference: Test cases in TASK-GBF-001-IMPLEMENTATION-PLAN.md (Phase 5)
4. Use: IMPLEMENTATION-CHECKLIST-GBF-001.md Phase 5 section

---

### By Time Availability

**5 minutes:** DESIGN-SUMMARY-GBF-001.md (Quick Reference section)

**15 minutes:** DESIGN-SUMMARY-GBF-001.md + DESIGN-GBF-001-visual-architecture.md (overview + diagrams)

**30 minutes:** DESIGN-SUMMARY-GBF-001.md + DESIGN-GBF-001-visual-architecture.md + ADR-GBF-001.md (decision record)

**60+ minutes:** Read all documents in order (architect/implementer review)

---

### By Phase

**Pre-Implementation (Architect Review):**
1. DESIGN-SUMMARY-GBF-001.md
2. ADR-GBF-001-unified-episode-serialization.md
3. DESIGN-GBF-001-episode-serialization-unification.md
4. DESIGN-GBF-001-visual-architecture.md

**During Implementation:**
1. TASK-GBF-001-IMPLEMENTATION-PLAN.md (reference)
2. IMPLEMENTATION-CHECKLIST-GBF-001.md (execute)

**During Code Review:**
1. DESIGN-SUMMARY-GBF-001.md (context)
2. IMPLEMENTATION-CHECKLIST-GBF-001.md (verification)
3. ADR-GBF-001 (rationale for decisions)

---

## Key Decisions Summary

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Client-level metadata injection (not entity-level) | Single responsibility, fewer bugs | Cleaner separation of concerns |
| All entities return `dict` (not `str`) | Type consistency, easier to test | TaskOutcome refactoring required |
| Remove metadata from entity bodies | Infrastructure concerns separated | Client becomes authoritative |
| Use 4-tuple format for `_add_episodes()` | Explicit metadata parameters, no manual injection | Seeding call sites must update |
| Phase-based implementation | Lower risk, verification points | Takes slightly longer but safer |
| Comprehensive tests added | Prevent regression, ensure consistency | 1 new test file required |

---

## Acceptance Criteria Checklist

From the task definition:

- [ ] All episodes use a single, documented serialization pattern
- [ ] No episode is missing any standard metadata field
- [ ] Existing tests continue to pass
- [ ] New test verifying metadata consistency across entity types

**How to Verify:**
1. Read ADR-GBF-001 (documents the single pattern)
2. Run consistency tests (verify no missing metadata)
3. Run full test suite (verify no regressions)
4. Review test_episode_serialization.py (verify new tests exist)

---

## Files in This Design Package

```
docs/architecture/
├── INDEX-GBF-001-design-documents.md          ← You are here
├── DESIGN-SUMMARY-GBF-001.md                  ✓ Executive summary
├── ADR-GBF-001-unified-episode-serialization.md  ✓ Architecture decision
├── DESIGN-GBF-001-episode-serialization-unification.md  ✓ Comprehensive
├── DESIGN-GBF-001-visual-architecture.md      ✓ Diagrams & visuals
└── IMPLEMENTATION-CHECKLIST-GBF-001.md        ✓ Execution checklist

tasks/in_progress/
└── TASK-GBF-001-IMPLEMENTATION-PLAN.md        ✓ Detailed plan
```

---

## Related Files in Codebase

**Current Implementation (to be changed):**
- `guardkit/knowledge/entities/outcome.py`
- `guardkit/knowledge/entities/turn_state.py`
- `guardkit/knowledge/entities/failed_approach.py`
- `guardkit/knowledge/entities/feature_overview.py`
- `guardkit/knowledge/facts/quality_gate_config.py`
- `guardkit/knowledge/facts/role_constraint.py`
- `guardkit/knowledge/seed_helpers.py`
- `guardkit/knowledge/seed_failed_approaches.py`
- `guardkit/knowledge/seed_feature_overviews.py`
- `guardkit/knowledge/failed_approach_manager.py`
- `guardkit/knowledge/outcome_manager.py`

**Tests (will be modified):**
- `tests/unit/test_*.py` (existing tests)
- `tests/unit/test_episode_serialization.py` (NEW)

**External Reference:**
- `tasks/backlog/TASK-REV-C632-graphiti-usage-baseline-analysis.md` (Finding 6)

---

## Glossary

**Entity:** Domain model class that represents a concept (TaskOutcome, TurnStateEntity, etc.)

**Episode:** A persisted event or state change stored in Graphiti knowledge graph

**Metadata:** Infrastructure fields describing the episode (entity_type, source, timestamps, etc.)

**Seeding:** Initial population of knowledge graph with predefined entities

**Graphiti Client:** Interface to Graphiti knowledge graph API

**Double Injection:** Problem where metadata is added twice (once manually, once by client)

**4-tuple:** Format `(name, body_dict, entity_type, entity_id)` for episode data

**SOLID:** Software design principles (Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion)

---

## Success Metrics

After implementation, you should be able to answer YES to:

1. **Consistency:** Can I explain why all entities return the same dict type? ✓
2. **Clarity:** Can I trace the metadata injection path from entity to storage? ✓
3. **Simplicity:** Can I add a new entity in 5 minutes? ✓
4. **Testing:** Can I write a test to verify an entity returns clean data? ✓
5. **Maintainability:** Is there only one place to change metadata structure? ✓

---

## Getting Help

**Questions about the design?**
- Read the relevant design document
- Check the ADR for decision rationale
- Review the visual architecture for examples

**Questions about implementation?**
- Consult IMPLEMENTATION-CHECKLIST-GBF-001.md
- Check the troubleshooting guide
- Review the detailed plan in TASK-GBF-001-IMPLEMENTATION-PLAN.md

**Found an issue?**
- Post-mortem with team
- Update relevant design document
- Create a follow-up issue/task

---

## Next Steps

### For Architects
1. Read DESIGN-SUMMARY-GBF-001.md
2. Review ADR-GBF-001-unified-episode-serialization.md
3. Approve or request modifications
4. Sign off on architecture decision

### For Implementers
1. Read all design documents (2-3 hours total)
2. Run through IMPLEMENTATION-CHECKLIST-GBF-001.md mentally
3. Ask clarifying questions if needed
4. Begin Phase 1 (entity cleanup)

### For Code Reviewers
1. Read DESIGN-SUMMARY-GBF-001.md
2. Bookmark IMPLEMENTATION-CHECKLIST-GBF-001.md
3. Review code against checklist
4. Verify all acceptance criteria met

---

## Document Status

| Document | Status | Date | Ready? |
|----------|--------|------|--------|
| DESIGN-SUMMARY-GBF-001.md | ✓ Complete | 2026-02-07 | ✓ |
| ADR-GBF-001 | ✓ Complete | 2026-02-07 | ✓ |
| DESIGN-GBF-001 | ✓ Complete | 2026-02-07 | ✓ |
| DESIGN-GBF-001-visual | ✓ Complete | 2026-02-07 | ✓ |
| TASK-GBF-001-PLAN | ✓ Complete | 2026-02-07 | ✓ |
| CHECKLIST-GBF-001 | ✓ Complete | 2026-02-07 | ✓ |
| INDEX (this file) | ✓ Complete | 2026-02-07 | ✓ |

**All design documentation complete and ready for implementation.**

---

**Prepared by:** Architecture Team
**Date:** 2026-02-07
**Status:** Design Phase Complete
**Next Phase:** Implementation (TASK-GBF-001)
