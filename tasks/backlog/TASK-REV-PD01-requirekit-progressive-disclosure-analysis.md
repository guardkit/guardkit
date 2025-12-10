---
id: TASK-REV-PD01
title: Analyze applying progressive disclosure to RequireKit repository
status: completed
created: 2025-12-09T00:30:00Z
updated: 2025-12-09T10:30:00Z
priority: medium
tags: [progressive-disclosure, requirekit, analysis, reuse, cross-repo]
task_type: review
review_mode: architectural
review_depth: standard
complexity: 6
decision_required: true
related_tasks: [TASK-PD-001]
review_results:
  mode: architectural
  depth: standard
  score: 78
  findings_count: 8
  recommendations_count: 6
  decision: customize
  report_path: .claude/reviews/TASK-REV-PD01-review-report.md
  completed_at: 2025-12-09T10:30:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyze applying progressive disclosure to RequireKit repository

## Description

Perform a comprehensive analysis of how progressive disclosure techniques (successfully implemented in GuardKit) can be applied to the RequireKit repository. This review should identify opportunities to reuse existing scripts, patterns, and methodologies from GuardKit's progressive disclosure refactoring.

## Background

GuardKit successfully implemented progressive disclosure (TASK-PD-001) with:
- Split-file architecture (`{name}.md` + `{name}-ext.md`)
- 55-60% token reduction in typical tasks
- Core content always loaded, extended content on-demand
- Scripts for splitting and validation

The goal is to apply the same techniques to RequireKit to achieve similar benefits.

## Target Repository

**Location**: `/Users/richardwoollcott/Projects/appmilla_github/require-kit`
**Relationship**: Sibling repository to GuardKit, used for formal requirements management (EARS notation, BDD scenarios)

## Analysis Objectives

### 1. Content Inventory
- [ ] Identify all agent files in RequireKit
- [ ] Identify CLAUDE.md and documentation files
- [ ] Measure current token usage for key files
- [ ] Identify files that exceed recommended sizes

### 2. Reusable Assets from GuardKit

Analyze which GuardKit assets can be reused:

**Scripts** (from `installer/core/lib/`):
- [ ] `agent_enhancement/applier.py` - Split file creation methods
- [ ] Progressive disclosure validation logic
- [ ] Token counting utilities

**Patterns** (from `docs/guides/`):
- [ ] `progressive-disclosure.md` - Implementation guide
- [ ] Core vs extended content categorization rules

**Templates**:
- [ ] Split file structure templates
- [ ] Loading instruction templates

### 3. RequireKit-Specific Considerations
- [ ] EARS requirements format compatibility
- [ ] BDD scenario file structure
- [ ] Cross-reference handling between requirements and tasks
- [ ] Integration points with GuardKit

### 4. Implementation Feasibility
- [ ] Effort estimate for applying progressive disclosure
- [ ] Risk assessment (breaking changes, compatibility)
- [ ] Recommended approach (incremental vs full refactor)

## Acceptance Criteria

- [ ] Complete inventory of RequireKit files suitable for progressive disclosure
- [ ] Token usage analysis (before/after estimates)
- [ ] List of reusable GuardKit scripts with modification requirements
- [ ] Recommended implementation approach
- [ ] Risk assessment and mitigation strategies
- [ ] Effort estimate for implementation

## Deliverables

1. **Analysis Report** (`docs/reviews/requirekit-progressive-disclosure-analysis.md`)
   - Content inventory with token measurements
   - Reusability assessment
   - Implementation recommendations
   - Risk matrix

2. **Reuse Mapping** (table of GuardKit assets → RequireKit application)

3. **Implementation Recommendation** (one of):
   - Full adoption with minimal changes
   - Partial adoption (selected files only)
   - Fork and customize approach
   - Not recommended (with justification)

## Review Scope

### In Scope
- RequireKit agent files analysis
- RequireKit CLAUDE.md and documentation
- GuardKit progressive disclosure scripts
- Token usage estimation
- Implementation planning

### Out of Scope
- Actual implementation (separate task if approved)
- GuardKit code modifications
- Performance benchmarking

## GuardKit Reference Files

Key files to reference during analysis:

```
guardkit/
├── docs/guides/progressive-disclosure.md          # Implementation guide
├── installer/core/lib/agent_enhancement/
│   ├── applier.py                                 # Split file methods
│   └── models.py                                  # SplitContent dataclass
└── installer/core/templates/*/
    └── agents/*-ext.md                            # Extended file examples
```

## Decision Framework

After review, recommend one of:

| Decision | When to Use |
|----------|-------------|
| **[A]dopt** | High token savings, minimal modifications needed |
| **[C]ustomize** | Significant savings, but RequireKit-specific adaptations needed |
| **[D]efer** | Low priority, savings don't justify effort now |
| **[R]eject** | Not applicable or negative ROI |

## Estimated Effort

- Analysis: 2-4 hours
- Report generation: 1-2 hours
- Total: 3-6 hours

## Next Steps

After creating this task:
1. Execute review: `/task-review TASK-REV-PD01 --mode=architectural --depth=standard`
2. Review findings and make decision
3. If [A]dopt or [C]ustomize: Create implementation task
