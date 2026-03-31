---
id: TASK-REV-CROPT
title: Analyze context reduction options given Graphiti code fidelity limitations
status: review_complete
created: 2026-02-05T23:15:00+00:00
updated: 2026-02-06T00:30:00+00:00
priority: high
tags:
- context-optimization
- graphiti
- architecture-decision
- review
task_type: review
decision_required: true
complexity: 5
parent_feature: FEAT-CR01
related_documents:
- docs/reviews/graphiti_enhancement/graphiti_code_retrieval_fidelity.md
- .claude/reviews/TASK-REV-5F19-review-report.md
review_results:
  mode: decision
  depth: standard
  options_evaluated: 4
  recommendation: "Option B: Graphiti-Independent Reduction (Expanded to Templates)"
  token_reduction_target: "~13,400 tokens (40% overall)"
  scope_expansion: "Added template system analysis per user request"
  tasks_to_keep: 5
  tasks_to_modify: 2
  tasks_to_cancel: 3
  tasks_to_complete: 1
  new_template_tasks: 5
  total_tasks: 16
  report_path: .claude/reviews/TASK-REV-CROPT-review-report.md
  completed_at: 2026-02-06T00:30:00+00:00
  revised_at: 2026-02-06T01:00:00+00:00
---

# Review: Analyze Context Reduction Options Given Graphiti Code Fidelity Limitations

## Background

The FEAT-CR01 feature (Context Reduction via Graphiti Migration) had 10 tasks planned across 4 waves to reduce token usage from ~15,800 tokens to ~8,000 tokens (49% reduction). Waves 1 and 2 partially executed before a critical discovery: **Graphiti extracts semantic facts from code, it does not preserve verbatim code blocks**.

### Failed Tasks

TASK-CR-006 (seed pattern code examples) and TASK-CR-006-FIX (wire pattern seeding) revealed:
- Graphiti is a **knowledge graph**, not a document store
- Code blocks are processed into semantic facts (e.g., "OrchestrationState has a field named strategy")
- Copy-paste usable code cannot be reliably retrieved
- Relevance scores were 0.00 for pattern queries (even when related facts were found)

### What This Means for FEAT-CR01

| Wave | Tasks | Status | Impact |
|------|-------|--------|--------|
| 1 | CR-001, CR-002, CR-003 | Partially done | Path-gating graphiti-knowledge.md works |
| 2 | CR-004, CR-005, CR-006 | Blocked | CR-006 revealed fidelity issue |
| 3 | CR-007, CR-008, CR-009 | **Cancelled** | Cannot trim pattern files if Graphiti can't serve code |
| 4 | CR-010 | Blocked | No point in regression test until approach clear |

## Review Objectives

1. **Assess the original goal** - Reduce static markdown tokens loaded into context
2. **Document what Graphiti CAN do** - Semantic queries, concept relationships, pattern discovery
3. **Document what Graphiti CANNOT do** - Verbatim code retrieval, syntax preservation
4. **Evaluate alternative approaches** - What else could achieve token reduction?
5. **Recommend path forward** - Which tasks to keep, cancel, or modify

## Key Questions to Address

### Q1: What's the actual token problem?

- How many tokens are loaded in a typical session?
- How much of that is from pattern files (already path-gated)?
- What's the ROI of further optimization given progressive disclosure already helps?

### Q2: What content types are suitable for Graphiti migration?

**Likely suitable:**
- Project overview/orientation (not code)
- Workflow descriptions (not code)
- Troubleshooting guidance (not code)
- "When to use X" decisions (not code)

**Not suitable:**
- Code examples with specific syntax
- Pattern implementations requiring copy-paste
- Configuration file templates

### Q3: Could a hybrid approach work?

The fidelity assessment mentioned "Option C: Hybrid Approach":
- Keep code in static files (path-gated)
- Use Graphiti for semantic "which pattern should I use?" queries
- Retrieve pattern file on-demand based on semantic match

**Questions:**
- Is this architecturally feasible?
- Would it reduce tokens or just add complexity?
- Could Graphiti return a file path instead of content?

### Q4: Are there non-Graphiti approaches to reduce tokens?

- More aggressive path-gating (e.g., graphiti-knowledge.md had no path gate)
- Lazy loading of examples (keep headers, load code on demand)
- Compression of verbose sections to tables
- Elimination of duplicate content between files

### Q5: What's the cost-benefit of continuing FEAT-CR01?

Given:
- Progressive disclosure already reduces typical session load
- Pattern files are already path-gated
- The biggest always-loaded files (CLAUDE.md) can be trimmed without Graphiti

Is further Graphiti migration worth the complexity?

## Input Documents for Analysis

1. **Graphiti Code Retrieval Fidelity Assessment**
   - Path: `docs/reviews/graphiti_enhancement/graphiti_code_retrieval_fidelity.md`
   - Contains: Investigation findings, test results, options analysis

2. **Original Review Report (TASK-REV-5F19)**
   - Path: `.claude/reviews/TASK-REV-5F19-review-report.md`
   - Contains: File-by-file analysis, token counts, original recommendations

3. **TASK-CR-006-FIX**
   - Path: `tasks/backlog/context-reduction/TASK-CR-006-FIX-wire-pattern-seeding-module.md`
   - Contains: Wiring attempt and fidelity threshold criteria

4. **Current Pattern Files**
   - `.claude/rules/patterns/dataclasses.md` (~720 tokens)
   - `.claude/rules/patterns/orchestrators.md` (~1,540 tokens)
   - `.claude/rules/patterns/pydantic-models.md` (~584 tokens)

## Expected Deliverables

1. **Options Matrix** - Evaluate 3-4 approaches with trade-offs
2. **Recommendation** - Clear path forward with rationale
3. **Task Disposition** - Which CR-XXX tasks to keep/cancel/modify
4. **Updated FEAT-CR01 Scope** - If continuing, what's the realistic scope?

## Review Mode

- **Mode**: decision (technical decision analysis with options evaluation)
- **Depth**: standard (1-2 hours)
- **Focus**: Architecture decision on context reduction strategy

## Acceptance Criteria

- [x] Options matrix with at least 4 alternatives evaluated
- [x] Each option assessed for: token savings, implementation effort, risk, feasibility
- [x] Clear recommendation with supporting rationale
- [x] Task disposition for all 10 CR-XXX tasks
- [x] Updated FEAT-CR01 scope document (if feature continues)
- [x] Human decision checkpoint executed
- [x] Template system analysis added (scope expansion per user request)
- [x] 5 new template tasks created (CR-T01 through CR-T05)
- [x] README and IMPLEMENTATION-GUIDE updated

## Next Steps After Review

Based on decision checkpoint:
- **[A]ccept** - Approve recommendations, update task statuses
- **[I]mplement** - Create new tasks if different approach chosen
- **[R]evise** - Request deeper analysis on specific option
- **[C]ancel** - Abandon FEAT-CR01 entirely
