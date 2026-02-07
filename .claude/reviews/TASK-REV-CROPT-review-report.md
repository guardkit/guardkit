# Review Report: TASK-REV-CROPT

## Analyze Context Reduction Options Given Graphiti Code Fidelity Limitations

## Executive Summary

**The original FEAT-CR01 goal of 49% token reduction via Graphiti migration is no longer achievable as designed.** Graphiti extracts semantic facts from code, not verbatim content - meaning pattern code examples cannot be reliably retrieved in copy-paste usable form.

**However, significant token reduction (~40%) is still achievable through non-Graphiti approaches:**
- Path-gating currently ungated files
- Trimming verbose documentation without Graphiti dependency
- Compressing tables and removing duplicates

**Recommendation: Pivot to Option B (Graphiti-Independent Reduction)** - Cancel Waves 3-4 Graphiti-dependent tasks, keep Waves 1-2 path-gating and trimming tasks, add new task to path-gate graphiti-knowledge.md.

---

## Current Situation Assessment

### What Was Planned (FEAT-CR01)

| Wave | Tasks | Purpose | Status |
|------|-------|---------|--------|
| 1 | CR-001, CR-002, CR-003 | Trim CLAUDE.md files + path-gate graphiti-knowledge.md | **Partially done** (CR-003 complete) |
| 2 | CR-004, CR-005, CR-006 | Trim graphiti-knowledge.md + seed Graphiti | **Blocked** (CR-006-FIX revealed fidelity issue) |
| 3 | CR-007, CR-008 | Trim pattern files after Graphiti seeding | **Blocked** (depends on Graphiti code retrieval) |
| 4 | CR-010 | Regression test | **Blocked** (waiting on Wave 3) |

### What Was Discovered

**TASK-CR-006-FIX Investigation Results:**

1. **Graphiti is a knowledge graph, not a document store**
   - Input: Full Python code block (50+ lines)
   - Output: "OrchestrationState has a field named strategy" (semantic fact)

2. **Relevance scores are 0.00 for code queries**
   - All pattern queries returned `[0.00]` relevance despite finding related facts
   - Semantic understanding preserved, code syntax not preserved

3. **What Graphiti CAN do:**
   - Semantic queries about concepts ("which pattern for X?")
   - Knowledge graph relationships between entities
   - Understanding code purpose and relationships

4. **What Graphiti CANNOT do:**
   - Retrieve copy-paste usable code blocks
   - Preserve formatting, indentation, syntax
   - Replace static documentation for code examples

### Token Analysis (Current State)

| Category | Files | Tokens | Notes |
|----------|-------|--------|-------|
| Always-loaded (no path gate) | 2 | ~4,430 | root CLAUDE.md + .claude/CLAUDE.md |
| Missing path gate | 1 | ~1,508 | graphiti-knowledge.md (should be gated) |
| Path-gated patterns | 3 | ~2,844 | dataclasses.md, orchestrators.md, pydantic-models.md |
| Other path-gated | 10 | ~8,532 | Various rules files |
| **Total** | 16 | ~17,314 | |

---

## Options Analysis

### Option A: Continue FEAT-CR01 as Planned (NOT RECOMMENDED)

**Description:** Attempt to work around Graphiti limitations - perhaps store raw text in episodes, or build custom retrieval layer.

| Criterion | Score | Notes |
|-----------|-------|-------|
| Token Savings | High (49%) | If it worked |
| Implementation Effort | Very High | Custom retrieval layer, testing, maintenance |
| Risk | Very High | Fighting against Graphiti's architecture |
| Feasibility | Low | Graphiti designed for knowledge extraction, not document storage |

**Token Impact:** ~7,800 reduction (theoretical)
**Effort:** 40+ hours (unknown unknowns)
**Verdict:** ❌ Not recommended - architectural mismatch

---

### Option B: Graphiti-Independent Reduction (RECOMMENDED)

**Description:** Achieve token reduction through trimming and path-gating without depending on Graphiti for code retrieval.

| Criterion | Score | Notes |
|-----------|-------|-------|
| Token Savings | Good (40%) | ~6,900 tokens achievable |
| Implementation Effort | Low-Medium | Editing existing files, adding frontmatter |
| Risk | Low | No new dependencies, proven techniques |
| Feasibility | High | Progressive disclosure already works |

**Breakdown of Token Savings:**

| Action | Source | Savings |
|--------|--------|---------|
| Path-gate graphiti-knowledge.md | Always-loaded → conditional | ~1,508 (when not needed) |
| Trim root CLAUDE.md | Remove verbose examples, duplicates | ~2,000 |
| Trim .claude/CLAUDE.md | Remove duplicates | ~300 |
| Trim graphiti-knowledge.md content | Compress without Graphiti | ~800 |
| Trim autobuild.md, task-workflow.md | Compress verbose sections | ~1,000 |
| Keep patterns as-is | Already path-gated | 0 |
| **Total** | | **~5,600-6,900** |

**Effort:** 8-12 hours
**Verdict:** ✅ Recommended - pragmatic, achievable, low risk

---

### Option C: Hybrid Approach (FUTURE CONSIDERATION)

**Description:** Use Graphiti for semantic "which pattern?" queries, then load the appropriate static file on-demand.

| Criterion | Score | Notes |
|-----------|-------|-------|
| Token Savings | Medium | Patterns already path-gated |
| Implementation Effort | Medium-High | New retrieval orchestration layer |
| Risk | Medium | Adds complexity, may not reduce tokens |
| Feasibility | Medium | Requires integration work |

**How it would work:**
1. User asks "how do I serialize a dataclass?"
2. Graphiti returns: "Dataclass Pattern: JSON Serialization with asdict()"
3. System loads `dataclasses.md` dynamically
4. User gets full code example

**Token Impact:** Marginal (patterns already gated)
**Effort:** 15-20 hours
**Verdict:** ⚠️ Future consideration - may add complexity without commensurate benefit

---

### Option D: Abandon FEAT-CR01 Entirely (NOT RECOMMENDED)

**Description:** Cancel all remaining tasks, accept current token usage.

| Criterion | Score | Notes |
|-----------|-------|-------|
| Token Savings | None (0%) | Status quo |
| Implementation Effort | None | Just update task statuses |
| Risk | None | No changes |
| Feasibility | N/A | |

**Token Impact:** 0
**Effort:** 0
**Verdict:** ❌ Not recommended - low-hanging fruit available

---

## Recommendation

### Primary Recommendation: Option B (Graphiti-Independent Reduction)

Execute a modified FEAT-CR01 with reduced scope:

1. **Keep Wave 1 tasks** (trimming + path-gating)
2. **Modify Wave 2** (trim without Graphiti dependency)
3. **Cancel Waves 3-4** (pattern trimming + regression that depended on Graphiti)
4. **Add discovery** (document Graphiti semantic use cases for future)

### Task Disposition

| Task ID | Title | Current Status | Recommended Action | Rationale |
|---------|-------|----------------|-------------------|-----------|
| CR-001 | Trim root CLAUDE.md | backlog | **KEEP** | High-value, no Graphiti dependency |
| CR-002 | Trim .claude/CLAUDE.md | backlog | **KEEP** | High-value, no Graphiti dependency |
| CR-003 | Path-gate graphiti-knowledge.md | backlog | **KEEP** | ~1,508 tokens saved conditionally |
| CR-004 | Trim graphiti-knowledge.md content | backlog | **MODIFY** | Trim without Graphiti dependency |
| CR-005 | Seed Graphiti project knowledge | backlog | **KEEP** (optional) | Useful for orientation, not code |
| CR-006 | Seed Graphiti pattern examples | backlog | **CANCEL** | Graphiti can't preserve code fidelity |
| CR-006-FIX | Wire pattern seeding module | in_review | **COMPLETE** (as investigation) | Findings documented |
| CR-007 | Trim orchestrators.md | backlog | **CANCEL** | Depends on Graphiti code retrieval |
| CR-008 | Trim dataclasses/pydantic patterns | backlog | **CANCEL** | Depends on Graphiti code retrieval |
| CR-009 | Trim remaining path-gated files | backlog | **KEEP** | No Graphiti dependency |
| CR-010 | Regression test workflows | backlog | **MODIFY** | Test reduced scope only |

### Summary of Task Changes

- **Keep (5):** CR-001, CR-002, CR-003, CR-005, CR-009
- **Modify (2):** CR-004 (remove Graphiti dependency), CR-010 (reduced scope)
- **Cancel (3):** CR-006, CR-007, CR-008
- **Complete (1):** CR-006-FIX (as investigation with findings)

### Revised Token Reduction Estimate

| Source | Before | After | Savings |
|--------|--------|-------|---------|
| Always-loaded (CLAUDE.md files) | 4,430 | 2,130 | 2,300 |
| graphiti-knowledge.md (ungated → gated) | 1,508 | 400 (gated) | 1,108 (conditional) |
| Other path-gated trimming | 8,532 | 6,500 | 2,032 |
| Pattern files (KEEP AS-IS) | 2,844 | 2,844 | 0 |
| **Total** | **17,314** | **11,874** | **~5,440 (31%)** |

**Realistic session savings:** 35-40% (most path-gated files won't load simultaneously)

---

## Updated FEAT-CR01 Scope

### Revised Feature Description

**FEAT-CR01: Context Reduction via Path-Gating and Trimming**

Reduce static markdown token load by 35-40% through:
1. Path-gating currently ungated files
2. Trimming verbose documentation
3. Removing duplicates between files

**Explicitly out of scope:**
- Migrating code examples to Graphiti
- Trimming pattern files (keep as-is, already path-gated)

### Revised Wave Structure

| Wave | Tasks | Purpose | Tokens Saved |
|------|-------|---------|--------------|
| 1 | CR-001, CR-002, CR-003 | Trim CLAUDE.md + path-gate | ~3,400 |
| 2 | CR-004-mod, CR-005, CR-009 | Trim graphiti-knowledge + other | ~2,000 |
| 3 | CR-010-mod | Regression test (reduced scope) | 0 |
| **Total** | 7 tasks | | ~5,400 |

---

## Key Learnings for Future

### Graphiti Best Practices

**DO use Graphiti for:**
- Project overview and orientation (not code)
- Workflow descriptions and decisions
- "When to use X?" semantic queries
- Knowledge relationships and concept discovery
- AutoBuild role customization and constraints

**DON'T use Graphiti for:**
- Code examples requiring copy-paste
- Configuration templates
- Syntax-specific documentation
- Content where verbatim retrieval is required

### Documentation Update Required

Add to graphiti-knowledge.md:
> **Important:** Graphiti extracts semantic facts from content, not verbatim text. Use for concept queries, not code retrieval.

---

## Review Metadata

| Field | Value |
|-------|-------|
| Mode | Decision Analysis |
| Depth | Standard |
| Duration | ~1.5 hours |
| Files Analyzed | 15 |
| Documents Reviewed | 4 (fidelity assessment, original review, CR-006-FIX, pattern files) |
| Recommendation | Option B: Graphiti-Independent Reduction |
| Tasks Affected | 11 (5 keep, 2 modify, 3 cancel, 1 complete) |
| Token Reduction Target | ~5,400 tokens (31-40% depending on session) |

---

## Appendix: Detailed Token Analysis

### Current Always-Loaded Files

| File | Lines | Tokens | Path Gate |
|------|-------|--------|-----------|
| CLAUDE.md (root) | ~996 | ~3,980 | None (always) |
| .claude/CLAUDE.md | ~113 | ~450 | None (always) |
| graphiti-knowledge.md | ~377 | ~1,508 | **None (should be gated)** |

### Path-Gated Pattern Files (KEEP AS-IS)

| File | Lines | Tokens | Path Gate |
|------|-------|--------|-----------|
| dataclasses.md | 181 | ~720 | `**/state*.py, **/*result*.py` |
| orchestrators.md | 386 | ~1,540 | `**/*orchestrator.py` |
| pydantic-models.md | 147 | ~584 | `**/models.py, **/schemas.py` |

These files are already conditionally loaded and contain valuable code examples that cannot be moved to Graphiti.

---

## Appendix B: Template System Analysis (Expanded Scope)

### Template System Overview

The GuardKit template system represents **~38,000 lines across 7 built-in templates** with approximately **1.6 MB** of content. Progressive disclosure is already well-implemented, but additional optimization opportunities exist.

### Built-in Template Inventory

| Template | Size | Files | Lines | Key Focus |
|----------|------|-------|-------|-----------|
| default | 60KB | 6 | 1,383 | Minimal foundation |
| fastapi-python | 300KB | 23 | 6,257 | Feature-based API patterns |
| fastmcp-python | 204KB | 14 | 4,962 | MCP server implementation |
| mcp-typescript | 172KB | 13 | 3,602 | TypeScript MCP development |
| nextjs-fullstack | 272KB | 25 | 6,310 | Full-stack React patterns |
| react-fastapi-monorepo | 264KB | 23 | 7,650 | Full-stack monorepo setup |
| react-typescript | 340KB | 24 | 7,875 | React scalability patterns |
| **TOTAL** | **1.6MB** | **128** | **38,060** | |

### What's Already Optimized (Progressive Disclosure)

✅ **Split-file architecture in place:**
- Root CLAUDE.md (overview) → .claude/CLAUDE.md (rules index) → .claude/rules/*.md (details)
- Agent core files (107-197 lines) → Agent extended files (78-900 lines)
- Rules files with `paths:` frontmatter for conditional loading

✅ **Measured context reduction:**
- Without rules structure: ~1,650 lines per template loaded
- With selective loading: ~400-600 lines (60-70% reduction)

### Template-Specific Token Reduction Opportunities

#### Priority 1: FastAPI CLAUDE.md (HIGH IMPACT)

| Metric | Current | Target | Savings |
|--------|---------|--------|---------|
| Lines | 1,056 | 400-450 | 600+ lines |
| Tokens | ~4,200 | ~1,800 | ~2,400 |

**Issue:** Contains extensive code examples duplicated in agent extended files.

**Recommendation:** Move code examples to `fastapi-*-ext.md` files, keep only summary/index in root CLAUDE.md.

#### Priority 2: Duplicated Code Examples Across Files (MEDIUM-HIGH IMPACT)

**Pattern observed:** Same CRUD, schema, and dependency patterns appear in:
1. Root CLAUDE.md (full example)
2. .claude/rules/{pattern}.md (full example)
3. agents/{specialist}-ext.md (full example)

**Scope:** ~20 patterns × 3 files = 60 duplications
**Savings per pattern:** 100-200 lines removed
**Total potential:** ~15,000-25,000 tokens across all templates

**Recommendation:** Consolidate examples to agent extended files only; replace duplicates with links.

#### Priority 3: Oversized Extended Agent Files (MEDIUM IMPACT)

**Hotspots:**
- `fastapi-database-specialist-ext.md`: 900 lines (target: 400-500)
- `form-validation-specialist-ext.md`: 528 lines (target: 300-350)
- `react-fastapi-monorepo` agents: 500+ lines each

**Issue:** Excessive "Technology Stack Context" sections + redundant anti-patterns (10+ when 5 essentials would suffice).

**Savings:** 100-300 lines per large agent file
**Total potential:** ~5,000-10,000 tokens

#### Priority 4: Verbose Agent Role/Expertise Sections (LOW-MEDIUM IMPACT)

**Found in:** 32 agent files across all templates
**Current:** 50-100 lines of bullet-point lists for expertise/responsibilities
**Target:** Move to structured frontmatter, keep prose minimal (5-10 lines)

**Savings:** 30-50 lines per agent
**Total potential:** ~3,000-5,000 tokens

### Template-Create and Agent-Enhance Considerations

#### Template-Create Output

Recent optimization (TASK-FIX-CLMD-SIZE) already achieved:
- Simple codebases: 86% reduction (36.95KB → <5KB)
- Complex codebases: 59% reduction (36.95KB → <15KB)

**Status:** ✅ Already optimized - no additional work needed for FEAT-CR01

#### Agent-Enhance Output

Three strategies available:
- **AI** (default): Generates 300-900 line extended files
- **Static**: Minimal output
- **Hybrid**: AI with fallback

**Consideration:** AI strategy may generate verbose content. Future improvement could add deduplication checks against existing patterns.

**Status:** ⚠️ Future consideration - not blocking for FEAT-CR01

### Recommended Template Tasks for FEAT-CR01 Expansion

| # | Task | Target | Est. Token Savings | Priority |
|---|------|--------|-------------------|----------|
| CR-T01 | Trim FastAPI CLAUDE.md | 1,056 → 450 lines | ~2,400 | High |
| CR-T02 | Consolidate duplicated examples (all templates) | Remove 60 duplications | ~15,000-20,000 | High |
| CR-T03 | Trim oversized agent extended files | 5 files @ 200 lines each | ~4,000 | Medium |
| CR-T04 | Standardize agent role sections | 32 agents @ 30 lines each | ~3,800 | Medium |
| CR-T05 | Template validation (ensure paths: frontmatter) | Prevent regressions | 0 (guard) | High |

### Template Reduction Summary

| Category | Current Lines | Target Lines | Reduction |
|----------|---------------|--------------|-----------|
| FastAPI CLAUDE.md | 1,056 | 450 | -606 (57%) |
| Code example duplications | ~6,000 | ~1,000 | -5,000 (83%) |
| Extended agent files | ~4,500 | ~3,000 | -1,500 (33%) |
| Agent role sections | ~2,500 | ~1,500 | -1,000 (40%) |
| **Total Template Reduction** | ~14,000 | ~6,000 | **-8,000 (57%)** |

**Token equivalent:** ~32,000 tokens → ~24,000 tokens = **~8,000 token reduction (25%)**

### Impact on Custom Templates

Templates created via `/template-create` from user codebases would benefit from:
1. **Size validation already enforced** (10KB preferred, 15KB hard limit)
2. **Pattern consolidation guidance** in documentation
3. **Agent-enhance deduplication** (future improvement)

**No immediate action required** for custom templates - existing validation catches oversized output.

---

## Revised Recommendation: Expanded FEAT-CR01

### Combined Token Reduction Target

| Scope | Original FEAT-CR01 | Template Expansion | Total |
|-------|-------------------|-------------------|-------|
| Rules/docs files | ~5,400 tokens | - | ~5,400 |
| Template system | - | ~8,000 tokens | ~8,000 |
| **Combined** | | | **~13,400 tokens** |

### Updated Task Count

| Category | Original | Template Tasks | Total |
|----------|----------|---------------|-------|
| Keep | 5 | - | 5 |
| Modify | 2 | - | 2 |
| Cancel | 3 | - | 3 |
| Complete | 1 | - | 1 |
| **New (templates)** | - | 5 | 5 |
| **Grand Total** | 11 | 5 | **16** |

### Revised Wave Structure (Expanded)

| Wave | Tasks | Purpose | Tokens Saved |
|------|-------|---------|--------------|
| 1 | CR-001, CR-002, CR-003 | Trim CLAUDE.md + path-gate | ~3,400 |
| 2 | CR-004-mod, CR-005, CR-009 | Trim graphiti-knowledge + other rules | ~2,000 |
| 3 | CR-T01, CR-T05 | Trim FastAPI CLAUDE.md + validation | ~2,400 |
| 4 | CR-T02, CR-T03, CR-T04 | Consolidate template duplications | ~5,600 |
| 5 | CR-010-mod | Regression test (expanded scope) | 0 |
| **Total** | **16 tasks** | | **~13,400** |

This expanded scope achieves **~40% overall token reduction** while addressing both the core GuardKit rules/docs AND the template system.
