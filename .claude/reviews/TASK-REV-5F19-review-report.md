# Review Report: TASK-REV-5F19

## Reduce Context Window Usage via Graphiti Migration

## Executive Summary

Analysis of 15 static files (~15,800 tokens always loaded) reveals that **~7,400 tokens (47%) can be eliminated or migrated** to Graphiti on-demand retrieval, reducing always-loaded context to **~8,400 tokens**. However, the migration is not straightforward: Graphiti currently lacks code-example retrieval fidelity, and the highest-value migrations require seeding structured content that Graphiti doesn't yet hold. A phased approach is recommended: eliminate redundancy first (quick wins), then seed Graphiti gaps, then trim static files.

---

## Phase 2: File-by-File Classification

### Classification Legend
- **KEEP STATIC**: Must be present in every conversation (command syntax, core workflow, behavioral rules)
- **TRIM**: Keep file but remove sections that duplicate Graphiti or are rarely needed
- **MIGRATE**: Move to Graphiti for on-demand retrieval
- **ELIMINATE**: Redundant content already covered elsewhere

---

### 1. CLAUDE.md (root) - 996 lines, ~3,980 tokens

**Classification: TRIM (aggressive)**

| Section | Lines | ~Tokens | Action | Rationale |
|---------|------:|--------:|--------|-----------|
| Core Features + Principles | ~20 | 80 | KEEP | Identity/orientation |
| Essential Commands (syntax only) | ~40 | 160 | KEEP | Used every session |
| /feature-plan detailed example | ~90 | 360 | MIGRATE | Verbose example, only needed during feature planning |
| /feature-build documentation | ~50 | 200 | MIGRATE | Only needed during autobuild |
| /feature-complete documentation | ~40 | 160 | MIGRATE | Only needed at completion |
| Security Validation section | ~25 | 100 | MIGRATE | Only needed during autobuild |
| Agent & Template Mgmt commands | ~15 | 60 | KEEP (condensed) | Reference syntax |
| Design-First Workflow | ~20 | 80 | KEEP (1-liner) | Referenced often |
| Review vs Implementation table | ~80 | 320 | MIGRATE | Already in task-review command spec |
| Review Modes/Depth/Examples | ~60 | 240 | MIGRATE | Already in task-review command spec |
| Task Workflow Phases | ~35 | 140 | KEEP | Core orientation |
| Complexity Evaluation | ~40 | 160 | TRIM | Compress to table only |
| Quality Gates table | ~30 | 120 | KEEP | Core behavioral rules |
| Task States & Transitions | ~40 | 160 | KEEP | Core orientation |
| Project Structure | ~20 | 80 | KEEP | Rarely changes |
| Installation & Setup | ~60 | 240 | MIGRATE | Only needed once per project |
| Conductor Integration | ~30 | 120 | MIGRATE | Niche usage |
| Testing by Stack | ~15 | 60 | KEEP | Referenced during testing |
| Template Philosophy/Quality | ~50 | 200 | MIGRATE | Only during template work |
| Progressive Disclosure | ~20 | 80 | ELIMINATE | Self-referential meta docs |
| Rules Structure sections | ~40 | 160 | ELIMINATE | Already in rules/ structure docs |
| MCP Integration | ~60 | 240 | MIGRATE | Already in Graphiti + MCP docs |
| Graphiti Knowledge section | ~40 | 160 | ELIMINATE | Already in graphiti-knowledge.md |
| Troubleshooting/Known Limitations | ~40 | 160 | MIGRATE | Rarely needed |
| When to Use GuardKit | ~30 | 120 | MIGRATE | Orientation, not operational |

**Estimated reduction**: 3,980 -> ~1,600 tokens (**-2,380 tokens, -60%**)

**Approach**: Create a lean CLAUDE.md with command syntax, core principles, quality gates, task states, and testing commands. Everything else becomes Graphiti-retrievable or already exists in path-gated rules files.

---

### 2. .claude/CLAUDE.md - 113 lines, ~450 tokens

**Classification: TRIM**

| Section | ~Tokens | Action | Rationale |
|---------|--------:|--------|-----------|
| Project Context | 60 | KEEP | Orientation |
| Core Principles | 80 | ELIMINATE | Duplicate of root CLAUDE.md |
| Workflow Overview | 100 | ELIMINATE | Duplicate of root CLAUDE.md |
| Technology Stack Detection | 60 | KEEP | Useful context |
| Getting Started | 80 | ELIMINATE | Duplicate |
| Dev Mode Selection | 50 | ELIMINATE | Duplicate |
| Clarifying Questions ref | 20 | KEEP (1-liner) | Pointer only |

**Estimated reduction**: 450 -> ~140 tokens (**-310 tokens, -69%**)

---

### 3. rules/autobuild.md - 389 lines, ~1,556 tokens

**Classification: TRIM + path-gated (already gated: `guardkit/**/*.py, .guardkit/**/*`)**

This file is already path-gated, so it only loads when working on AutoBuild Python files. However, it's very large for what it provides.

| Section | ~Tokens | Action | Rationale |
|---------|--------:|--------|-----------|
| How It Works + Delegation | 200 | KEEP | Core architecture reference |
| Player-Coach Workflow | 160 | KEEP | Behavioral rules |
| Configuration YAML | 120 | KEEP | Reference syntax |
| Pre-Loop Configuration | 280 | TRIM to 100 | Very verbose; compress to table |
| SDK Timeout Configuration | 200 | MIGRATE | Reference detail; rarely needed inline |
| Recommended Timeout Values | 80 | KEEP (table) | Quick reference |
| Workflow Examples | 200 | MIGRATE | Examples retrievable on-demand |
| Agent Reports | 80 | MIGRATE | Reference detail |
| Troubleshooting | 160 | MIGRATE | Needed only when debugging |
| Best Practices | 60 | KEEP | Behavioral rules |
| Integration section | 120 | ELIMINATE | Repeats root CLAUDE.md content |

**Estimated reduction**: 1,556 -> ~720 tokens (**-836 tokens, -54%**)

**Note**: Since this is path-gated, the token savings only apply when working on AutoBuild files, not globally. The global savings from trimming this file are 0 for non-AutoBuild work.

---

### 4. rules/clarifying-questions.md - 141 lines, ~564 tokens

**Classification: KEEP (already efficient, path-gated)**

Path-gated to `installer/core/commands/*.md, installer/core/agents/clarification-questioner.md`. Only loads when editing command specs. Already concise and well-structured.

**No change recommended**. Already gated and compact.

---

### 5. rules/feature-build-invariants.md - 64 lines, ~256 tokens

**Classification: KEEP (already efficient, path-gated)**

Path-gated to `guardkit/orchestrator/**/*.py, guardkit/commands/feature_build.py`. Small file with critical invariants.

**No change recommended**. This is exactly the kind of file that should stay static: short, behavioral, critical.

---

### 6. rules/graphiti-knowledge.md - 377 lines, ~1,508 tokens

**Classification: TRIM (aggressive)**

This is the largest irony: the Graphiti documentation is itself a large static file. Most of this content describes how to use Graphiti and could be in Graphiti itself, or trimmed to a minimal reference.

| Section | ~Tokens | Action | Rationale |
|---------|--------:|--------|-----------|
| Interactive Capture overview | 100 | KEEP (condensed) | Reference syntax |
| Focus Categories table | 80 | KEEP | Quick reference |
| AutoBuild Customization examples | 200 | MIGRATE | Verbose examples |
| Session Flow diagram | 80 | ELIMINATE | Illustrative, not operational |
| Knowledge Query Commands | 200 | TRIM to 60 | Compress to syntax only |
| Turn State Tracking | 160 | MIGRATE | Detail for autobuild only |
| Turn State Schema | 100 | MIGRATE | Detail for autobuild only |
| Job-Specific Context Retrieval | 300 | MIGRATE | Implementation detail |
| Budget Allocation tables | 100 | MIGRATE | Implementation detail |
| Troubleshooting | 200 | MIGRATE | Needed only when debugging |

**Estimated reduction**: 1,508 -> ~340 tokens (**-1,168 tokens, -77%**)

---

### 7. rules/guidance/agent-development.md - 185 lines, ~740 tokens

**Classification: KEEP (path-gated, well-sized)**

Path-gated to `**/agents/**/*.md`. Only loads when working on agent files. Content is structural (frontmatter format, boundary sections) that Claude needs inline when editing agents.

**No change recommended**. Path-gating keeps it efficient.

---

### 8. rules/hash-based-ids.md - 86 lines, ~344 tokens

**Classification: TRIM**

Path-gated to `tasks/**/*.md, guardkit/cli/**/*.py`. Some content duplicates root CLAUDE.md.

| Section | ~Tokens | Action | Rationale |
|---------|--------:|--------|-----------|
| Format + Benefits | 80 | KEEP | Core reference |
| Common Prefixes | 40 | KEEP | Quick reference |
| Examples | 60 | KEEP | Usage patterns |
| PM Tool Integration | 80 | MIGRATE | Niche usage, detailed |
| For Developers links | 40 | ELIMINATE | Links to docs, not operational |
| FAQ | 44 | MIGRATE | Rarely needed inline |

**Estimated reduction**: 344 -> ~180 tokens (**-164 tokens, -48%**)

---

### 9. rules/patterns/dataclasses.md - 180 lines, ~720 tokens

**Classification: MIGRATE (partial)**

Path-gated (patterns load when relevant files are open). Contains code examples that Graphiti's current `patterns` group (19 episodes) only has as relationships, not full code.

| Section | ~Tokens | Action | Rationale |
|---------|--------:|--------|-----------|
| Basic State Containers | 100 | KEEP | Primary pattern |
| Optional Fields | 60 | KEEP | Primary pattern |
| JSON Serialization | 80 | KEEP | Primary pattern |
| When to Use table | 60 | KEEP | Decision guide |
| Common Patterns (3 examples) | 200 | MIGRATE | Retrievable examples |
| field() usage | 60 | KEEP | Common pitfall |
| Computed Properties | 80 | MIGRATE | Secondary pattern |
| Loading from JSON | 40 | MIGRATE | Secondary pattern |

**Estimated reduction**: 720 -> ~360 tokens (**-360 tokens, -50%**)

**Blocker**: Graphiti patterns group currently has relationships only, not code examples. Must seed code examples before trimming.

---

### 10. rules/patterns/orchestrators.md - 385 lines, ~1,540 tokens

**Classification: MIGRATE (significant)**

The largest patterns file. Contains 7 detailed orchestrator patterns with full code examples. Path-gated but very large when loaded.

| Section | ~Tokens | Action | Rationale |
|---------|--------:|--------|-----------|
| Pipeline Step Execution | 260 | KEEP (condensed to 80) | Primary pattern |
| Checkpoint-Resume | 400 | MIGRATE | Detailed implementation |
| Validation Chain | 200 | MIGRATE | Can be retrieved |
| State Management | 120 | KEEP (condensed to 40) | Primary pattern |
| Error Recovery | 120 | MIGRATE | Can be retrieved |
| Progress Reporting | 200 | MIGRATE | Can be retrieved |
| Strategy Routing | 120 | MIGRATE | Can be retrieved |

**Estimated reduction**: 1,540 -> ~320 tokens (**-1,220 tokens, -79%**)

**Blocker**: Same as dataclasses - Graphiti needs code examples seeded.

---

### 11. rules/patterns/pydantic-models.md - 146 lines, ~584 tokens

**Classification: MIGRATE (partial)**

Similar to dataclasses.md. Path-gated.

| Section | ~Tokens | Action | Rationale |
|---------|--------:|--------|-----------|
| Basic Model Structure | 100 | KEEP | Primary pattern |
| Field Definitions | 120 | KEEP | Core reference |
| Nested Models | 60 | KEEP (condensed) | Reference |
| When to Use table | 40 | KEEP | Decision guide |
| Serialization | 60 | MIGRATE | Secondary |
| JSON Schema Examples | 80 | MIGRATE | Secondary |
| Dynamic Defaults | 40 | MIGRATE | Secondary |
| Custom Exceptions | 24 | MIGRATE | Secondary |

**Estimated reduction**: 584 -> ~320 tokens (**-264 tokens, -45%**)

---

### 12. rules/patterns/template.md - 159 lines, ~636 tokens

**Classification: KEEP (path-gated, well-sized)**

Path-gated to `installer/core/templates/**/*`. Only loads during template work. Content is structural.

**No change recommended**. Path-gating keeps it efficient.

---

### 13. rules/python-library.md - 215 lines, ~860 tokens

**Classification: TRIM**

Path-gated to `installer/core/lib/**/*.py`. Good code examples but some are verbose.

| Section | ~Tokens | Action | Rationale |
|---------|--------:|--------|-----------|
| Module Documentation | 120 | KEEP | Primary pattern |
| Public API Exports | 60 | KEEP | Primary pattern |
| Module-Level Constants | 80 | KEEP | Primary pattern |
| Compiled Regex | 60 | KEEP | Primary pattern |
| Thread-Safe Caching | 120 | MIGRATE | Advanced pattern, rarely needed |
| Type Hints | 60 | KEEP | Primary pattern |
| Error Handling | 60 | KEEP | Primary pattern |
| Logging Setup | 60 | MIGRATE | Standard pattern, well-known |
| Path Operations | 60 | KEEP | Project-specific |
| Relative Imports | 40 | KEEP | Project-specific |

**Estimated reduction**: 860 -> ~620 tokens (**-240 tokens, -28%**)

---

### 14. rules/task-workflow.md - 306 lines, ~1,224 tokens

**Classification: TRIM**

Path-gated to `tasks/**/*`. Contains important structural info but also verbose examples.

| Section | ~Tokens | Action | Rationale |
|---------|--------:|--------|-----------|
| Frontmatter Format | 160 | KEEP | Core reference |
| Required/Optional Fields | 100 | KEEP | Core reference |
| Provenance Fields | 240 | MIGRATE | Detailed docs, rarely referenced |
| Provenance Chain Example | 160 | MIGRATE | Extended example |
| Task ID Format | 40 | KEEP | Quick reference |
| Directory Organization | 40 | KEEP | Quick reference |
| Status Transitions | 60 | KEEP | Already in root CLAUDE.md too |
| Task Content Sections | 60 | KEEP | Template reference |
| Feature Folder Structure | 100 | TRIM to 40 | Compress |
| Moving Tasks | 60 | KEEP | Behavioral rule |
| Intensity Levels | 120 | TRIM to 40 | Compress to table ref |

**Estimated reduction**: 1,224 -> ~700 tokens (**-524 tokens, -43%**)

---

### 15. rules/testing.md - 211 lines, ~844 tokens

**Classification: TRIM**

Path-gated to `tests/**/*.py`. Good patterns but some are standard pytest knowledge.

| Section | ~Tokens | Action | Rationale |
|---------|--------:|--------|-----------|
| Test File Documentation | 40 | KEEP | Project convention |
| Fixture Patterns (3) | 200 | KEEP | Project-specific |
| Dynamic Module Imports | 80 | KEEP | Project-specific quirk |
| Test Class Organization | 80 | KEEP | Project convention |
| Mock Patterns | 100 | MIGRATE | Standard pytest knowledge |
| Performance Tests | 60 | MIGRATE | Standard pattern |
| Assertion Patterns | 80 | MIGRATE | Standard pytest knowledge |
| Coverage Requirements | 40 | KEEP | Behavioral rules |

**Estimated reduction**: 844 -> ~520 tokens (**-324 tokens, -38%**)

---

## Token Reduction Summary

### Always-Loaded Files (no path gating)

| File | Current | After Trim | Savings |
|------|--------:|----------:|--------:|
| CLAUDE.md (root) | 3,980 | 1,600 | -2,380 |
| .claude/CLAUDE.md | 450 | 140 | -310 |
| **Subtotal** | **4,430** | **1,740** | **-2,690** |

### Path-Gated Files (conditional load)

| File | Current | After Trim | Savings | Gate |
|------|--------:|----------:|--------:|------|
| autobuild.md | 1,556 | 720 | -836 | guardkit/**/*.py |
| clarifying-questions.md | 564 | 564 | 0 | commands/*.md |
| feature-build-invariants.md | 256 | 256 | 0 | orchestrator/*.py |
| graphiti-knowledge.md | 1,508 | 340 | -1,168 | (no path gate!) |
| agent-development.md | 740 | 740 | 0 | agents/**/*.md |
| hash-based-ids.md | 344 | 180 | -164 | tasks/**/*.md |
| dataclasses.md | 720 | 360 | -360 | (patterns/) |
| orchestrators.md | 1,540 | 320 | -1,220 | (patterns/) |
| pydantic-models.md | 584 | 320 | -264 | (patterns/) |
| template.md | 636 | 636 | 0 | templates/**/* |
| python-library.md | 860 | 620 | -240 | lib/**/*.py |
| task-workflow.md | 1,224 | 700 | -524 | tasks/**/* |
| testing.md | 844 | 520 | -324 | tests/**/*.py |
| **Subtotal** | **11,376** | **6,276** | **-5,100** |

### Key Finding: graphiti-knowledge.md Has No Path Gate

**Critical discovery**: `rules/graphiti-knowledge.md` has no `paths:` frontmatter, meaning it loads unconditionally in every conversation. At 1,508 tokens, this is the second-highest always-loaded file after root CLAUDE.md. Adding a path gate or trimming this file has the highest ROI.

### Total Potential Reduction

| Category | Current | After | Savings | % |
|----------|--------:|------:|--------:|---|
| Always-loaded (root + .claude/CLAUDE.md) | 4,430 | 1,740 | -2,690 | 61% |
| Conditionally-loaded (worst case: all active) | 11,376 | 6,276 | -5,100 | 45% |
| **Grand Total** | **15,806** | **8,016** | **-7,790** | **49%** |
| **Realistic Session** (2-3 rules active) | ~6,900 | ~3,700 | ~-3,200 | 46% |

**Target met**: 50% reduction achievable (49% grand total, higher for typical sessions since most path-gated files won't load simultaneously).

---

## Phase 3: Graphiti Gap Analysis

### Current Graphiti Coverage

| Group | Episodes | Has Code Examples? | Has Behavioral Rules? |
|-------|----------|-------------------|----------------------|
| command_workflows | 67 | No | Partial |
| architecture_decisions | 26 | No | Yes |
| product_knowledge | 21 | No | Partial |
| patterns | 19 | **No (relationships only)** | No |
| failure_patterns | 19 | No | Yes |
| agents | 11 | No | **No (names only)** |
| project_overview | 0 | N/A | N/A |
| project_architecture | 0 | N/A | N/A |
| feature_specs | 0 | N/A | N/A |

### Gaps That Block Migration

1. **patterns group lacks code examples**: The 3 pattern files (dataclasses, orchestrators, pydantic) contain ~60% code examples by volume. Graphiti has 19 pattern episodes but only captures relationships ("dataclass pattern exists"), not the actual Python code examples. **Must seed code examples before trimming pattern files.**

2. **project_overview and project_architecture are empty**: These would receive content from root CLAUDE.md sections like "When to Use GuardKit", "Project Structure", "Core Principles". **Must seed before eliminating from CLAUDE.md.**

3. **agents group is names only**: Would need agent development guidance, boundary patterns, and frontmatter formats. However, `agent-development.md` is already path-gated, so this is low priority.

### Seeding Plan

#### Wave 1: Quick Wins (No Graphiti needed)
- Add `paths:` frontmatter to `graphiti-knowledge.md` (e.g., `paths: config/graphiti.yaml, guardkit/graphiti/**/*.py`)
- Remove duplicate content between root CLAUDE.md and .claude/CLAUDE.md
- Remove self-referential meta-documentation (Progressive Disclosure section describes itself)
- Compress verbose sections to tables/one-liners

#### Wave 2: Seed Graphiti Gaps
- Seed `project_overview` group with: project purpose, principles, when to use
- Seed `project_architecture` group with: project structure, task states, conductor integration
- Seed `patterns` group with actual code examples (dataclass, pydantic, orchestrator patterns)
- Seed `feature_specs` with installation/setup content

#### Wave 3: Trim After Verification
- For each migrated section: query Graphiti to verify retrieval with >0.6 relevance
- Only trim static file after confirming Graphiti returns the content reliably
- Keep a "migrated-content-registry.md" mapping what moved where

---

## Phase 4: Risk Assessment

### High Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Graphiti unavailable (Docker/Neo4j down) | Claude loses all migrated knowledge | Keep trimmed files as "lean" versions, not empty; Graphiti is supplementary, not sole source |
| Code examples lose formatting in Graphiti | Pattern guidance degrades | Test retrieval fidelity before trimming; patterns may need to stay static |
| Latency on Graphiti queries delays responses | User experience degrades | Only migrate content not needed at conversation start |

### Medium Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Relevance scores too low for migrated content | Content not retrieved when needed | Pre-test all queries; tune group names and episode descriptions |
| Breaking existing workflows | Commands fail silently | Test /task-work, /feature-build, /feature-plan after each wave |
| Over-trimming root CLAUDE.md | Claude loses core orientation | Keep identity, commands, quality gates, states always static |

### Low Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Path-gating reduces visibility | Developer misses relevant rule | Rules structure is designed for this; Claude Code discovers rules by path |
| Token savings less than estimated | Smaller impact than expected | Even 30% reduction is meaningful for weekly usage |

---

## Phase 5: Recommendations

### Recommendation 1: Trim Always-Loaded Files First (Quick Win)

**Estimated savings: ~2,690 tokens (17% of total)**

No Graphiti dependency. Pure editing work:
1. Trim root CLAUDE.md from ~996 lines to ~300 lines (command syntax, quality gates, states, testing)
2. Remove duplicates from .claude/CLAUDE.md (reduce to 30 lines)
3. Add `paths:` frontmatter to graphiti-knowledge.md

### Recommendation 2: Add Path Gate to graphiti-knowledge.md

**Estimated savings: ~1,508 tokens when not working on Graphiti**

This file currently loads in every conversation but is only needed when working on Graphiti integration. Adding a path gate like `paths: config/graphiti.yaml, guardkit/graphiti/**/*.py, docs/**/graphiti*` would prevent it loading unnecessarily.

### Recommendation 3: Seed Graphiti Code Examples Before Trimming Patterns

**Estimated savings: ~1,844 tokens from pattern files**

The three pattern files are the largest opportunity in path-gated content, but Graphiti needs code examples seeded first. Use `guardkit graphiti capture --interactive --focus patterns` or manual episode creation.

### Recommendation 4: Compress Verbose Path-Gated Files

**Estimated savings: ~2,248 tokens from autobuild, task-workflow, testing, python-library, hash-based-ids**

Compress verbose examples and duplicate content within path-gated files. This doesn't require Graphiti and can be done incrementally.

### Recommendation 5: Phased Implementation

Execute in waves to minimize risk:
- **Wave 1**: Trim always-loaded files + add path gates (0 Graphiti dependency)
- **Wave 2**: Seed Graphiti gaps + verify retrieval
- **Wave 3**: Trim path-gated files after verification

---

## Implementation Subtasks (Proposed)

| # | Task | Type | Wave | Est. Tokens Saved |
|---|------|------|------|-------------------|
| 1 | Trim root CLAUDE.md to lean version | task-work | 1 | 2,380 |
| 2 | Trim .claude/CLAUDE.md remove duplicates | task-work | 1 | 310 |
| 3 | Add path gate to graphiti-knowledge.md | direct | 1 | 1,508 (conditional) |
| 4 | Trim graphiti-knowledge.md content | task-work | 1 | 1,168 |
| 5 | Seed Graphiti project_overview + project_architecture | direct | 2 | (enables #1) |
| 6 | Seed Graphiti patterns with code examples | direct | 2 | (enables #7-9) |
| 7 | Trim orchestrators.md after Graphiti verification | task-work | 3 | 1,220 |
| 8 | Trim dataclasses.md + pydantic-models.md after verification | task-work | 3 | 624 |
| 9 | Trim autobuild.md, task-workflow.md, testing.md, python-library.md, hash-based-ids.md | task-work | 3 | 2,088 |
| 10 | Regression test: verify /task-work, /feature-build, /feature-plan workflows | task-work | 3 | 0 |

---

## Review Metadata

- **Mode**: Architectural Review (decision analysis)
- **Depth**: Standard
- **Reviewer**: Architectural analysis with file-by-file classification
- **Files Analyzed**: 15
- **Total Current Tokens**: ~15,800
- **Projected After Optimization**: ~8,000
- **Reduction**: ~49%
