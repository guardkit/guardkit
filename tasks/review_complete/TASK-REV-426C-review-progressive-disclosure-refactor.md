---
id: TASK-REV-426C
title: Review progressive disclosure refactoring for stack templates
status: review_complete
created: 2025-12-03T14:30:00Z
updated: 2025-12-03T16:30:00Z
priority: high
task_type: review
tags: [architecture-review, progressive-disclosure, templates, token-optimization, pre-launch]
complexity: 7
decision_required: true
review_results:
  mode: architectural
  depth: standard
  recommendation: approve
  findings_count: 8
  recommendations_count: 6
  report_path: .claude/reviews/TASK-REV-426C-review-report.md
  completed_at: 2025-12-03T15:00:00Z
  decision: implement
  decision_date: 2025-12-03T16:30:00Z
implementation_tasks:
  folder: tasks/backlog/progressive-disclosure/
  count: 19
  phases: 5
  total_effort_days: 16-18
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review progressive disclosure refactoring for stack templates

## Description

Review the proposed refactoring to implement progressive disclosure in GuardKit's stack templates. This refactoring aims to reduce context window usage by 30-60% while maintaining quality by splitting files into:

1. **Core content**: Always loaded, essential for task execution (~40% of current content)
2. **Extended content**: Loaded on-demand via explicit instructions (~60% of current content)

The refactoring touches **5 major components** across the template generation pipeline and is recommended for implementation BEFORE public launch to avoid migration complexity.

## Source Documents

- [Progressive Disclosure Analysis](docs/research/progressive-disclosure-analysis.md) - Strategic rationale and content analysis
- [Progressive Disclosure Implementation Scope](docs/research/progressive-disclosure-implementation-scope.md) - Technical scope and effort estimates

## Review Scope

### 1. Strategic Analysis Review

Evaluate the business case for progressive disclosure:
- Developer evaluation problem (first impressions within 1-2 hours)
- Token savings projections (30-60% reduction)
- Pre-launch vs post-launch implementation trade-offs (6-8 days saved)
- Positioning as a feature ("loads only what's needed")

### 2. Technical Architecture Review

Assess the proposed file splitting approach:
- CLAUDE.md split (20KB → 8KB core + patterns/reference docs)
- Agent file split (`{name}.md` → `{name}.md` + `{name}-ext.md`)
- Loading instruction mechanism (explicit `cat` commands with visual indicators)
- Impact on agent discovery and quality gates

### 3. Component Impact Analysis

Review changes required across 5 major components:
1. **CLAUDE.md Generator** (`claude_md_generator.py`) - Split generation
2. **Agent Enhancement Command** (`agent-enhance.md`, `enhancer.py`) - New file creation
3. **Enhancement Applier** (`applier.py`) - Complete refactor
4. **Global Agents** (`installer/core/agents/`) - Manual split (10+ files)
5. **Template Validation** - Recognize split structure

### 4. Risk Assessment

Evaluate identified risks and mitigations:
- Agents not loading ext files (Clear loading instructions, validation)
- Token savings less than expected (Measure before/after)
- Increased complexity (Documentation, consistent patterns)
- Discovery system compatibility (Index ext files)

### 5. Implementation Sequencing

Review the proposed 3-phase approach:
1. Phase 1: Foundation (Applier + Enhancer refactor) - 4-5 days
2. Phase 2: CLAUDE.md Split - 2-3 days
3. Phase 3: Migration (Global + template agents) - 4-6 days

## Acceptance Criteria

- [ ] Strategic rationale validated (token savings vs implementation cost)
- [ ] Technical approach assessed for feasibility
- [ ] Component impact analysis complete with accurate effort estimates
- [ ] Risk assessment validated with mitigations
- [ ] Implementation sequencing reviewed for dependencies
- [ ] Decision recommendation provided (Approve/Modify/Reject/Postpone)
- [ ] If Approved: Implementation tasks defined

## Decision Options

| Option | Description |
|--------|-------------|
| **Approve** | Proceed with implementation as proposed |
| **Modify** | Approve with specific modifications (scope reduction, phasing changes) |
| **Reject** | Do not implement (provide rationale) |
| **Postpone** | Implement post-launch with migration support |

## Key Questions to Address

1. Is the 30-60% token reduction estimate realistic based on actual file analysis?
2. Will Claude reliably follow explicit `cat` loading instructions?
3. Is the 10-14 day pre-launch estimate achievable given current priorities?
4. What is the minimum viable scope (MVP) if full implementation isn't feasible?
5. Are there alternative approaches not considered in the analysis?

## Review Deliverables

1. **Review Report**: Detailed analysis with findings and recommendations
2. **Decision**: Clear recommendation with rationale
3. **Implementation Tasks** (if approved): Backlog items for execution
4. **Risk Register**: Updated risks with any new concerns identified

## Implementation Notes

This is a **review task** - use `/task-review TASK-REV-426C` to execute the review workflow.

If the review recommends implementation, subsequent implementation tasks will be created using `/task-create` with appropriate complexity evaluations.

## Test Execution Log

[Automatically populated by /task-review]
