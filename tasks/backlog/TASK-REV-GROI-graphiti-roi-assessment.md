---
id: TASK-REV-GROI
title: Graphiti ROI assessment — where it helps, where it doesn't, where to expand
status: review_complete
task_type: review
review_mode: decision
review_depth: deep
created: 2026-02-14T00:00:00Z
updated: 2026-02-14T10:00:00Z
priority: high
tags: [graphiti, roi, architecture, knowledge-graph, mcp, context-injection]
complexity: 7
decision_required: true
review_results:
  mode: decision
  depth: deep
  findings_count: 10
  recommendations_count: 3
  high_value_paths: 0
  potential_paths: 4
  low_value_paths: 4
  dead_paths: 1
  not_applicable: 1
  recommended_strategy: connect_measure_decide
  revision: "R1 — connect 3 disconnected reads before deprecating"
  report_path: .claude/reviews/TASK-REV-GROI-review-report.md
---

# Task: Graphiti ROI Assessment

## Problem Statement

GuardKit has invested heavily in Graphiti integration: 65 files, 22 seed modules, 9 entity types, 18 integration files, 10 CLI commands, a thread-safe factory, FalkorDB migration, and MCP server wiring. But in practice, interactive Claude Code sessions bypass Graphiti entirely by reading markdown files directly, MCP servers fall back to training data, and several write paths have had stub/wiring bugs that undermined trust.

We need an honest assessment of where Graphiti delivers measurable value, where the overhead isn't justified, and where untapped potential exists.

## Review Scope

Evaluate each Graphiti consumption path against three criteria:
1. **Does it work reliably?** (no stub bugs, no silent failures)
2. **Does it provide value that can't be achieved more simply?** (vs reading files directly)
3. **Is it actually used?** (in real workflows, not just theoretically available)

---

## Consumption Path Inventory

### PATH 1: AutoBuild Coach Context Injection

**What it does**: `coach_context_builder.py` queries Graphiti for architecture overview, similar outcomes, and relevant patterns, then injects token-budgeted context into Coach validation prompts.

**Token budget by complexity**:
- 1-3: 0 tokens (no context)
- 4-6: 1,000 tokens (overview only)
- 7-8: 2,000 tokens (overview + impact)
- 9-10: 3,000 tokens (overview + impact)

**Questions to answer**:
- [ ] Does Coach produce measurably better validation with Graphiti context vs without?
- [ ] Are the token budgets right? (1,000 tokens for complexity 4-6 seems low)
- [ ] How often does this path actually fire? (Graphiti must be available AND task complexity >= 4)
- [ ] What percentage of AutoBuild runs have Graphiti available?

### PATH 2: AutoBuild Outcome & Turn State Capture

**What it does**: After each AutoBuild turn, captures `TurnState` and `Outcome` entities to Graphiti. Failed approaches are also logged.

**Questions to answer**:
- [ ] Is this data ever queried back? (by Coach, by feature-plan, by anyone?)
- [ ] Does capturing outcomes improve future AutoBuild runs via "similar outcomes" retrieval?
- [ ] What's the write volume? (22 seed modules + per-turn captures = how many episodes per feature build?)
- [ ] Is the cost of writing justified if reads are rare?

### PATH 3: Feature-Plan Context Assembly

**What it does**: `FeaturePlanContext` pulls feature specs, related features, patterns, and architecture context from Graphiti with a 4,000-token budget for prompt injection into feature decomposition.

**Questions to answer**:
- [ ] Does /feature-plan produce better decomposition with Graphiti context vs without?
- [ ] How often is Graphiti available when /feature-plan runs?
- [ ] Could the same context be achieved by reading `docs/architecture/ARCHITECTURE.md` directly (which is ~60 lines)?

### PATH 4: System Overview / Impact Analysis / Context Switch

**What it does**: Three CLI commands that query Graphiti for architecture context:
- `guardkit system-overview` — assembles architecture summary from Graphiti
- `guardkit impact-analysis` — queries affected components for a proposed change
- `guardkit context-switch` — loads project context when switching between projects

**Questions to answer**:
- [ ] How often are these commands used in real workflows?
- [ ] `system-overview` from Graphiti vs reading `docs/architecture/*.md` directly — what's the difference?
- [ ] `impact-analysis` is the most promising use case (semantic search across components) — does it work reliably?
- [ ] `context-switch` for multi-project: is anyone using GuardKit across multiple projects?

### PATH 5: System-Plan Write Path

**What it does**: `SystemPlanGraphiti` upserts architecture entities (components, ADRs, cross-cutting concerns, system context) to Graphiti during /system-plan execution.

**Questions to answer**:
- [ ] This had the historical stub bug — is the write path now reliable?
- [ ] Are the entities written here actually queried by paths 1, 3, or 4?
- [ ] Does ADR-SP-007 (Markdown Authoritative, Graphiti Queryable) hold? Or is Graphiti a dead copy of markdown?

### PATH 6: Seeding Infrastructure (22 Modules)

**What it does**: Seeds Graphiti with system-level knowledge: product info, command workflows, quality gate phases, tech stack, failure patterns, ADRs, patterns, rules, templates, agents, role constraints, quality gate configs.

**Questions to answer**:
- [ ] How long does full seeding take? (22 modules × N episodes each)
- [ ] Is seeded content ever updated, or does it go stale?
- [ ] Which seed categories are actually queried by the read paths?
- [ ] Could some seed categories be eliminated without impact?

### PATH 7: Add-Context CLI (Document Ingestion)

**What it does**: `guardkit graphiti add-context <path>` parses markdown documents (ADRs, feature specs, project overviews) and ingests them as episodes.

**Questions to answer**:
- [ ] How often is this used?
- [ ] Is the parser registry (ADR, feature-spec, project-overview, full-doc) reliable?
- [ ] Historical issue: `add_episode` returned errors silently — is this fixed?

### PATH 8: Interactive Capture & Search

**What it does**: `guardkit graphiti capture --interactive` runs Q&A capture. `guardkit graphiti search` queries knowledge.

**Questions to answer**:
- [ ] How often is interactive capture used?
- [ ] Is search useful for developers, or do they just read files?
- [ ] Could search be valuable for AI agents that don't have file paths memorised?

### PATH 9: MCP Servers (context7, design-patterns)

**What it does**: Optional MCP servers for library documentation retrieval and design pattern recommendations.

**Questions to answer**:
- [ ] Are MCP servers actually configured in any real project?
- [ ] The codebase says "falls back gracefully to training data" — does this mean they're never needed?
- [ ] What's the setup cost vs value delivered?

### PATH 10: Quality Gate Config from Graphiti

**What it does**: `CoachValidator` queries Graphiti for task-type specific quality gate thresholds, with hardcoded fallback defaults.

**Questions to answer**:
- [ ] Does anyone customise quality gate thresholds via Graphiti?
- [ ] Or does everyone use the hardcoded defaults in `task_types.py`?
- [ ] If always falling back to defaults, this is dead code

---

## Assessment Framework

For each path, categorise as:

| Category | Criteria | Action |
|----------|----------|--------|
| **HIGH VALUE** | Works reliably, provides unique value, actually used | Keep, invest further |
| **POTENTIAL** | Could provide value but not yet proven/reliable | Fix or test hypothesis |
| **LOW VALUE** | Works but same result achievable more simply | Simplify or deprecate |
| **DEAD** | Not used, broken, or always falls back to default | Remove or archive |

## Specific Hypotheses to Test

### H1: Coach context improves AutoBuild quality
**Test**: Run 5 identical tasks with Graphiti context enabled vs disabled. Compare Coach feedback quality and turn count.

### H2: Outcome capture enables learning across tasks
**Test**: Check if "similar outcomes" retrieval ever returns results during feature builds. If outcome writes are never read, the write path is waste.

### H3: Semantic search provides value over file reads
**Test**: For a complex impact analysis query, compare Graphiti search results vs `grep` across `docs/architecture/`. Does Graphiti surface connections that grep misses?

### H4: Seeding ROI is positive
**Test**: Measure seeding time and episode count. Map which seed categories are queried by read paths. Eliminate any category with zero reads.

## Where Graphiti Could Be Expanded

Assess whether these untapped use cases would deliver value:

1. **Cross-session task continuity** — When a new Claude Code session starts, Graphiti could provide "here's what happened last session" context without reading task files
2. **Pattern mining from completed tasks** — Analyse outcomes across many tasks to identify which approaches succeed/fail for which task types
3. **Architecture drift detection** — Compare Graphiti's architecture model against actual code structure to detect when implementation drifts from design
4. **Multi-project knowledge sharing** — If teams use GuardKit across projects, shared patterns and failure knowledge could transfer
5. **Embedding-powered code search** — Use Graphiti's embeddings for semantic code search (vs keyword grep)

## Acceptance Criteria

- [ ] Each of the 10 consumption paths assessed with evidence (not opinion)
- [ ] Each path categorised as HIGH VALUE / POTENTIAL / LOW VALUE / DEAD
- [ ] At least 2 hypotheses tested with real data
- [ ] Recommended actions: what to keep, what to fix, what to deprecate, what to expand
- [ ] Cost analysis: FalkorDB hosting cost + seeding time + maintenance overhead vs value delivered
- [ ] Decision: continue investing, simplify, or pivot Graphiti strategy

## Related

- **ADR-SP-001**: FalkorDB over Neo4j (should this be revisited if ROI is low?)
- **ADR-SP-007**: Markdown Authoritative, Graphiti Queryable (is Graphiti actually queryable in practice?)
- **TASK-REV-66B4**: Feature YAML schema drift (symptom of insufficient integration testing)
- **Seam S4/S5**: Python→Graphiti→FalkorDB seam tests (from FEAT-AC1A testing strategy)

## Review Mode

Suggested: `--mode=decision --depth=deep`
