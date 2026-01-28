---
id: TASK-REV-FB16
title: "Workflow optimization strategy: Adversarial intensity and conditional phases"
status: review_complete
created: 2026-01-16T10:00:00Z
updated: 2026-01-16T14:30:00Z
priority: high
review_results:
  mode: decision
  depth: standard
  report_path: .claude/reviews/TASK-REV-FB16-review-report.md
  completed_at: 2026-01-17T14:45:00Z
  key_decisions:
    - D1: "Intensity parameter - Option B (replace --micro with --intensity, keep alias)"
    - D2: "MCP gating - Option A (complexity threshold + quality filtering)"
    - D3: "Phase skipping - Option A (hardcoded now, migrate if needed)"
    - D4: "NEW: Provenance-aware intensity - tasks from /task-review or /feature-plan auto-detect to lighter intensity"
  recommendation: "Complete TASK-TWP Wave 1 first, then implement provenance-aware intensity system"
  decision: "[I]mplement"
  implementation_tasks:
    - TASK-INT-a1b2
    - TASK-INT-c3d4
    - TASK-INT-e5f6
    - TASK-INT-g7h8
    - TASK-INT-i9j0
  implementation_feature: provenance-intensity
tags:
  - review
  - performance
  - optimization
  - adversarial-intensity
  - feature-build
task_type: review
complexity: 5
review_mode: decision
review_depth: standard
related_tasks:
  - TASK-REV-FB14
  - TASK-REV-FB15
depends_on:
  - TASK-REV-FB15
---

# Workflow Optimization Strategy: Adversarial Intensity and Conditional Phases

## Review Objective

Evaluate and prioritize optimization strategies for `/task-work` and `/feature-build` based on the root cause analysis from TASK-REV-FB15. Focus on **adaptive ceremony** - matching process intensity to task complexity.

## Background Context

### Key Insight from Research
From the adversarial intensity research:

> "Adversarial intensity should scale with complexity scoring, extending the adaptive ceremony principle to the Player-Coach dialectical loop."

The existing `--micro` flag proves adaptive ceremony works - the question is how to systematize it.

### Proposed Intensity Gradient
```
Complexity 1-2 (Minimal):
├── Skip clarifying questions
├── Skip architectural review
├── Auto-proceed (no checkpoint)
├── Player-only OR Coach validates tests pass only
└── Skip plan audit

Complexity 3-4 (Standard-Light):
├── Quick clarifying questions (with timeout)
├── Architectural review (auto-approve if score >60)
├── Quick checkpoint (10s timeout)
├── Minimal adversarial - Coach validates requirements met
└── Plan audit (flag variance >50%)

Complexity 5-6 (Standard):
├── Full clarifying questions
├── Architectural review with recommendations
├── Quick checkpoint
├── Standard adversarial - Coach reviews requirements + tests
└── Plan audit (flag variance >20%)

Complexity 7-10 (Strict):
├── Full clarifying questions (blocking)
├── Architectural review (human checkpoint if score <70)
├── Mandatory checkpoint
├── Full adversarial - Coach reviews requirements + arch + integration
└── Plan audit (flag any variance)
```

### Prior Recommendations (TASK-REV-FB14)

| Option | Description | Time Savings | Effort | Risk |
|--------|-------------|--------------|--------|------|
| A. SDK Session Reuse | Keep single SDK session | 60-70% | High | Medium |
| B. Streaming Output | Real-time progress | 0% (UX) | Medium | Low |
| C. Wave Parallelization | Parallel task execution | 40-60% | Low | Low |
| D. Context Caching | Cache parsed CLAUDE.md | 20-30% | Medium | Low |
| E. Conditional MCP | Skip MCPs for simple tasks | Variable | Low | Low |

## Analysis Requirements

### 1. Evaluate Adversarial Intensity Gradient
For the proposed intensity levels:
- Is the complexity threshold mapping correct?
- What phases should be skipped at each level?
- How does this interact with existing `--micro` flag?
- Should `--micro` become `--intensity=minimal`?

### 2. Conditional MCP Invocation
Evaluate the proposed conditional logic:

```python
def should_invoke_design_patterns_mcp(task_context):
    if task_context.complexity <= 3:
        return False
    if task_context.task_type == "bugfix":
        return False
    # ... etc
```

Questions:
- Is complexity threshold of 3 correct?
- What other criteria should gate MCP invocation?
- Should context7 MCP also be conditional?

### 3. Quick Wins vs Long-Term
Categorize optimizations by implementation timeline:

**Quick Wins (< 1 day effort)**:
- ?

**Short-Term (1-3 days)**:
- ?

**Medium-Term (1-2 weeks)**:
- ?

**Long-Term (requires external changes)**:
- SDK Session Reuse (requires Anthropic support)

### 4. Risk Assessment
For each proposed optimization:
- What could break?
- How do we test it?
- Can it be feature-flagged?

### 5. Implementation Recommendations
Produce prioritized list:
1. What to implement first (highest impact, lowest risk)
2. What to implement next
3. What to defer
4. What to abandon

## Success Criteria

- [ ] Intensity gradient evaluated with specific phase/threshold recommendations
- [ ] Conditional MCP logic defined with testable criteria
- [ ] Quick wins identified (ready for immediate implementation)
- [ ] Implementation roadmap with priority order
- [ ] Risk mitigation strategies for top 3 optimizations
- [ ] Decision: Should `--micro` evolve into `--intensity` parameter?

## Output

Generate report at: `.claude/reviews/TASK-REV-FB16-review-report.md`

Include implementation task specifications for approved optimizations.

## Key Decision Points

### Decision 1: Intensity Parameter Design
Options:
A. Keep `--micro` as-is, add separate `--intensity=<level>` parameter
B. Replace `--micro` with `--intensity=minimal`
C. Auto-detect intensity from complexity score only (no manual override)

### Decision 2: MCP Gating Strategy
Options:
A. Gate by complexity only (< threshold = skip)
B. Gate by task type + complexity
C. Gate by explicit flag (--skip-mcp-patterns)
D. All of the above (hierarchical)

### Decision 3: Phase Skipping Implementation
Options:
A. Hardcoded in workflow (if complexity < X: skip_phase_Y())
B. Configuration-driven (yaml config per intensity level)
C. Phase-level complexity thresholds

## Related Tasks

- **TASK-REV-FB14**: Original performance analysis
- **TASK-REV-FB15**: Root cause analysis (should complete first)

## Notes

This review should result in actionable implementation tasks. The goal is not just analysis but a clear path forward.

The user is treating this as a learning opportunity - we should capture the design decisions and rationale for future reference.
