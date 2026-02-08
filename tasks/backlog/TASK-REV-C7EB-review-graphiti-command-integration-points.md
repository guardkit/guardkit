---
id: TASK-REV-C7EB
title: Review Graphiti integration points in GuardKit commands
status: backlog
task_type: review
created: 2026-02-08T21:00:00Z
updated: 2026-02-08T21:00:00Z
priority: high
tags: [graphiti, commands, integration, review, feature-plan, task-review, task-create, task-work]
complexity: 6
related_tasks: [TASK-REV-0E58, TASK-REV-8BD8, TASK-FIX-GCW3, TASK-FIX-GCW4, TASK-FIX-GCW5]
---

# Task: Review Graphiti Integration Points in GuardKit Commands

## Description

Analyse the Graphiti integration points within four core GuardKit commands (`/feature-plan`, `/task-review`, `/task-create`, `/task-work`) to understand what is specified vs implemented, identify gaps, and assess the consistency and completeness of Graphiti's role across the command surface area.

The autobuild pipeline integration was reviewed in TASK-REV-0E58 (post-GCW fixes). This review focuses on the **command-level** integration - how each command specification envisions Graphiti usage and whether the corresponding implementation exists and functions correctly.

## Reference Documentation

Primary Graphiti documentation index:
- `docs/reviews/graphiti_baseline/graphiti_docs_index.md`

Key Graphiti docs:
- `docs/reviews/graphiti_baseline/graphiti-technical-reference.md` - Technical reference (seeding layer, serialization, orchestrator patterns)
- `docs/reviews/graphiti_baseline/graphiti-storage-theory.md` - Storage theory (episode body conventions, extension checklist)
- `docs/deep-dives/graphiti/episode-metadata.md` - Episode metadata (`_add_episodes()`, seed_helpers.py)
- `docs/guides/graphiti-integration-guide.md` - Integration guide (18 knowledge categories, seeding table)
- `docs/architecture/graphiti-architecture.md` - Architecture (to_episode_body(), seeding orchestrator)
- `docs/architecture/ADR-GBF-001-unified-episode-serialization.md` - ADR: Unified episode serialization

## Review Scope

### Per-Command Analysis

For each of the four commands, determine:

1. **What does the command specification say about Graphiti?** (the "spec")
2. **What is actually implemented?** (the "code")
3. **What gaps exist between spec and implementation?**
4. **Is graceful degradation handled when Graphiti is unavailable?**

### Command 1: `/feature-plan`

**Spec location**: `installer/core/commands/feature-plan.md`

Known Graphiti touchpoints from spec:
- FEAT-GR-003 Graphiti Context Integration section
- Queries knowledge graph to enrich planning with related features, architectural patterns, failed approaches
- Seeds feature spec to knowledge graph
- Context-enriched planning output

**Implementation to examine**:
- `guardkit/knowledge/feature_plan_context.py` - Feature plan context loader
- `guardkit/knowledge/feature_detector.py` - Feature detection
- Any CLI wiring for `--context` flag in feature-plan command

**Key questions**:
- Is Graphiti context retrieval actually called during feature planning?
- Is the feature spec seeded to the knowledge graph as the spec describes?
- Does the `[Graphiti]` log output shown in the spec actually exist in code?

### Command 2: `/task-review`

**Spec location**: `installer/core/commands/task-review.md`

Known Graphiti touchpoints from spec:
- `--capture-knowledge` / `-ck` flag
- Phase 4.5: Knowledge Capture (optional)
- `guardkit.knowledge.review_knowledge_capture.run_review_capture()`
- Graceful degradation if Graphiti unavailable

**Implementation to examine**:
- `guardkit/knowledge/review_knowledge_capture.py` - Review knowledge capture
- `guardkit/knowledge/interactive_capture.py` - Interactive capture session
- Task-review command execution flow for `--capture-knowledge` handling

**Key questions**:
- Is `run_review_capture()` implemented and callable?
- Does the `--capture-knowledge` flag wire through to actual Graphiti operations?
- Are review insights stored as episodes with proper metadata?
- Does the 3-5 context-specific question flow work?

### Command 3: `/task-create`

**Spec location**: `installer/core/commands/task-create.md` (loaded above)

Known Graphiti touchpoints from spec:
- `library_context` frontmatter field with graphiti-core example
- Phase 1.5 (Load Task Context) - parsing library_context
- Phase 2.1 (Implementation Planning) - merging with Context7 results
- `graphiti-core` used as example in Context7 auto-detection

**Implementation to examine**:
- Task creation code for `library_context` field handling
- Whether `library_context` frontmatter is parsed during task-work Phase 1.5
- Context7 + manual context merge logic

**Key questions**:
- Is `library_context` actually parsed and used, or is it spec-only?
- Does the merge with Context7 results happen as described?
- Is this purely a Context7 integration point, or does it interact with Graphiti knowledge graph?

### Command 4: `/task-work`

**Spec location**: `installer/core/commands/task-work.md`

Known Graphiti touchpoints from spec:
- Phase 1.5 library auto-detection mentioning `graphiti-core`
- Context7 MCP integration for library documentation
- `library_context` frontmatter processing
- graphiti-core listed as a detected library example

**Implementation to examine**:
- `guardkit/knowledge/context_loader.py` - Task-level context loading
- `guardkit/knowledge/task_analyzer.py` - Task analysis for context
- Phase 1.5 implementation in task-work execution flow
- Context7 resolution logic for graphiti-core

**Key questions**:
- Does Phase 1.5 actually detect and resolve graphiti-core via Context7?
- Is there any direct Graphiti knowledge graph integration in task-work beyond the autobuild path (already reviewed in TASK-REV-0E58)?
- How does `library_context` flow from task frontmatter into implementation planning?

### Cross-Cutting Concerns

1. **Consistency**: Do all four commands handle Graphiti availability the same way? Is there a shared pattern for graceful degradation?
2. **Knowledge graph lifecycle**: Which commands READ from Graphiti vs WRITE to Graphiti? Is the read/write pattern balanced?
3. **Spec vs reality gap**: Are there features described in specs that are entirely unimplemented? Conversely, are there implemented features not described in specs?
4. **Configuration surface**: How does a user enable/disable Graphiti across commands? Is it consistent?
5. **Error handling**: What happens in each command when Neo4j is down, Graphiti client fails to init, or knowledge graph is empty?

### Files to Analyse

#### Command Specifications
- `installer/core/commands/feature-plan.md`
- `installer/core/commands/task-review.md`
- `installer/core/commands/task-create.md` (loaded in /task-create skill)
- `installer/core/commands/task-work.md`

#### Knowledge Module (Implementation)
- `guardkit/knowledge/__init__.py` - `get_graphiti()` function
- `guardkit/knowledge/graphiti_client.py` - Graphiti client wrapper
- `guardkit/knowledge/config.py` - Configuration
- `guardkit/knowledge/feature_plan_context.py` - Feature plan context
- `guardkit/knowledge/review_knowledge_capture.py` - Review knowledge capture
- `guardkit/knowledge/context_loader.py` - General context loading
- `guardkit/knowledge/task_analyzer.py` - Task analysis
- `guardkit/knowledge/interactive_capture.py` - Interactive capture
- `guardkit/knowledge/autobuild_context_loader.py` - AutoBuild-specific (reference from TASK-REV-0E58)

#### Graphiti Documentation (Baseline Reference)
- `docs/reviews/graphiti_baseline/graphiti_docs_index.md` - Full index
- `docs/reviews/graphiti_baseline/graphiti-technical-reference.md`
- `docs/reviews/graphiti_baseline/graphiti-storage-theory.md`
- `docs/deep-dives/graphiti/episode-metadata.md`
- `docs/guides/graphiti-integration-guide.md`
- `docs/architecture/graphiti-architecture.md`
- `docs/architecture/ADR-GBF-001-unified-episode-serialization.md`

## Acceptance Criteria

- [ ] Per-command analysis: spec vs implementation gap assessment for all 4 commands
- [ ] Identify which Graphiti integrations are implemented, partially implemented, or spec-only
- [ ] Assess graceful degradation handling across all commands
- [ ] Map the knowledge graph read/write pattern across commands
- [ ] Identify configuration consistency (or inconsistency) across commands
- [ ] Produce review report at `.claude/reviews/TASK-REV-C7EB-review-report.md`
- [ ] Provide prioritised recommendations for closing any gaps

## Review Mode

Recommended: `/task-review TASK-REV-C7EB --mode=deep-analysis --depth=comprehensive`
