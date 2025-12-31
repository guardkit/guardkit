---
id: TASK-REV-0414
title: "Review Quality Gates Integration Seams - Ensure Code Reuse from task-work"
status: backlog
task_type: review
created: 2025-12-30T10:00:00Z
priority: high
tags: [quality-gates, autobuild, code-reuse, integration-review, seams]
complexity: 6
review_mode: architectural
review_depth: comprehensive
related_tasks:
  - TASK-QG-P1-PRE
  - TASK-QG-P2-COACH
  - TASK-QG-P3-POST
  - TASK-QG-P4-TEST
parent_review: TASK-REV-B601
---

# Review: Quality Gates Integration Seams - Code Reuse Analysis

## Overview

This review task ensures the quality gates integration tasks (TASK-QG-P1-PRE, TASK-QG-P2-COACH, TASK-QG-P3-POST) are complete without gaps at the seams where slash commands meet Python implementation, and validates that we are reusing existing tried-and-tested code from `/task-work` rather than creating new implementations.

## Review Objectives

### Primary Objectives

1. **Gap Analysis**: Identify any gaps at integration seams between:
   - Slash command specifications (markdown) → Python orchestrator code
   - Python orchestrator code → Claude agent prompts
   - Pre-loop gates → Adversarial loop → Post-loop audit

2. **Code Reuse Validation**: Ensure maximum reuse of existing `/task-work` implementations:
   - Phase 1.6: Clarifying Questions (`clarification-questioner` agent, `lib/clarification/`)
   - Phase 2: Implementation Planning (`plan_markdown_parser.py`, `plan_persistence.py`)
   - Phase 2.5A: Pattern Suggestions (MCP design-patterns integration)
   - Phase 2.5B: Architectural Review (`architectural-reviewer` agent)
   - Phase 2.7: Complexity Evaluation (`guardkit/planning/complexity.py`, `lib/complexity_factors.py`)
   - Phase 4.5: Test Enforcement (`lib/phase_gate_validator.py`)
   - Phase 5: Code Review (`code-reviewer` agent)
   - Phase 5.5: Plan Audit (`lib/plan_audit.py`)

3. **Completeness Check**: Verify all acceptance criteria are achievable and testable.

## Existing Code to Reuse

### Phase 1.6 - Clarifying Questions
**Existing Implementation**:
- Agent: `clarification-questioner` at `~/.agentecflow/agents/clarification-questioner.md`
- Library: `installer/core/commands/lib/clarification/`
  - `detection.py` - Complexity gating logic
  - `templates/implementation_planning.py` - Question templates
  - `generators/planning_generator.py` - Question generation

**Integration Point**:
```python
# From lib/clarification/detection.py
def should_ask_questions(complexity: int) -> bool:
    return complexity >= 3
```

### Phase 2 - Implementation Planning
**Existing Implementation**:
- `installer/core/commands/lib/plan_markdown_parser.py` - Parse existing plans
- `installer/core/commands/lib/plan_markdown_renderer.py` - Render plans to markdown
- `installer/core/commands/lib/plan_persistence.py` - Save/load plans

**Integration Point**: These modules handle the plan lifecycle that `/task-work` uses.

### Phase 2.5A - Pattern Suggestions
**Existing Implementation**:
- MCP server: `design-patterns`
- Integration via `mcp__design-patterns__find_patterns`, `mcp__design-patterns__get_pattern_details`

**Integration Point**: MCP tool calls in agent prompts, no Python wrapper needed.

### Phase 2.5B - Architectural Review
**Existing Implementation**:
- Agent: `architectural-reviewer` at `installer/core/agents/architectural-reviewer.md`
- Task tool invocation with `subagent_type: "architectural-reviewer"`

**Integration Point**: Agent invocation via SDK, already used by `/task-work`.

### Phase 2.7 - Complexity Evaluation
**Existing Implementation**:
- `guardkit/planning/complexity.py` - `ComplexityAnalyzer`, `ComplexityFactors`
- `installer/core/commands/lib/complexity_factors.py` - Alternative implementation
- `installer/core/commands/lib/upfront_complexity_adapter.py` - Adapter for task-create

**Integration Point**:
```python
from guardkit.planning.complexity import ComplexityAnalyzer

analyzer = ComplexityAnalyzer()
factors = analyzer.analyze_task(task_dict)
score = factors.calculate_score()  # Returns 1-10
```

### Phase 2.8 - Human Checkpoint
**Existing Implementation**:
- `installer/core/commands/lib/checkpoint_display.py` - Terminal display
- `installer/core/commands/lib/user_interaction.py` - Input handling

**Integration Point**: These modules handle the user decision flow.

### Phase 4.5 - Test Enforcement
**Existing Implementation**:
- `installer/core/commands/lib/phase_gate_validator.py` - Gate validation logic
- Agent: `test-orchestrator`, `test-verifier`
- Auto-fix loop concept exists in task-work flow

**Integration Point**: The gate validator and test agents handle enforcement.

### Phase 5 - Code Review
**Existing Implementation**:
- Agent: `code-reviewer` at `installer/core/agents/code-reviewer.md`
- Task tool invocation with `subagent_type: "code-reviewer"`

**Integration Point**: Agent invocation via SDK.

### Phase 5.5 - Plan Audit
**Existing Implementation**:
- `installer/core/commands/lib/plan_audit.py` - Full `PlanAuditor` class
  - `audit_implementation()` - Main entry point
  - `_compare_files()` - File comparison
  - `_compare_loc()` - LOC variance
  - `_calculate_severity()` - Severity determination
  - `format_audit_report()` - Human-readable output

**Integration Point**:
```python
from lib.plan_audit import PlanAuditor, format_audit_report

auditor = PlanAuditor(workspace_root=worktree_path)
report = auditor.audit_implementation(task_id)
print(format_audit_report(report))
```

## Review Checklist

### 1. Seam Analysis: Slash Command → Python

| Task | Slash Command Spec | Python Implementation | Gap Status |
|------|-------------------|----------------------|------------|
| TASK-QG-P1-PRE | `installer/core/commands/feature-build.md` | `guardkit/orchestrator/quality_gates/pre_loop.py` | [ ] TBD |
| TASK-QG-P2-COACH | `.claude/agents/autobuild-coach.md` | `guardkit/orchestrator/autobuild.py` | [ ] TBD |
| TASK-QG-P3-POST | `installer/core/commands/feature-build.md` | `guardkit/orchestrator/quality_gates/post_loop.py` | [ ] TBD |

### 2. Code Reuse Validation

| Phase | Existing Code | Task Spec Mentions Reuse? | Actual Reuse Plan |
|-------|--------------|---------------------------|-------------------|
| 1.6 | `lib/clarification/` | [ ] TBD | [ ] TBD |
| 2 | `plan_persistence.py` | [ ] TBD | [ ] TBD |
| 2.5A | MCP design-patterns | [ ] TBD | [ ] TBD |
| 2.5B | `architectural-reviewer` | [ ] TBD | [ ] TBD |
| 2.7 | `guardkit/planning/complexity.py` | [ ] TBD | [ ] TBD |
| 2.8 | `checkpoint_display.py` | [ ] TBD | [ ] TBD |
| 4.5 | `phase_gate_validator.py` | [ ] TBD | [ ] TBD |
| 5 | `code-reviewer` | [ ] TBD | [ ] TBD |
| 5.5 | `lib/plan_audit.py` | [ ] TBD | [ ] TBD |

### 3. Completeness Verification

For each task (P1-PRE, P2-COACH, P3-POST):
- [ ] All acceptance criteria have clear test strategies
- [ ] Files to create/modify are correctly identified
- [ ] Dependencies are correctly specified
- [ ] Integration points are explicitly documented

## Key Questions to Answer

1. **Are the tasks proposing to create NEW implementations where existing code exists?**
   - Example: TASK-QG-P3-POST proposes creating `post_loop.py` - does this duplicate `lib/plan_audit.py`?

2. **Are there gaps at the seams?**
   - How does the slash command `/feature-build` invoke the Python orchestrator?
   - How does the Python orchestrator invoke agents via SDK?
   - How are results passed between phases?

3. **Is the Python package structure appropriate?**
   - Proposed: `guardkit/orchestrator/quality_gates/`
   - Question: Should this reuse `installer/core/commands/lib/` instead?

4. **Are agent prompts complete?**
   - TASK-QG-P2-COACH modifies `autobuild-coach.md` with Phase 4.5 + 5 instructions
   - Question: Are the instructions sufficient for the agent to execute correctly?

5. **Is test strategy realistic?**
   - Unit tests proposed for each module
   - Question: Can these be tested without SDK integration?

## Expected Deliverables

1. **Gap Report**: Document any gaps found at seams
2. **Reuse Recommendations**: Specific code reuse recommendations per phase
3. **Task Amendments**: List of changes needed to P1/P2/P3 task specs
4. **Risk Assessment**: Identify risks of NOT reusing existing code
5. **Implementation Order Recommendation**: Confirm or revise sequential execution order

## Acceptance Criteria

- [ ] All seams between slash commands and Python code identified
- [ ] All existing `/task-work` code that can be reused is documented
- [ ] Gap report generated with specific findings
- [ ] Task amendments documented (if any)
- [ ] Risk assessment completed
- [ ] Recommendations are actionable and specific

## Review Approach

1. **Phase 1**: Read existing `/task-work` implementation flow
2. **Phase 2**: Map existing code to proposed quality gates tasks
3. **Phase 3**: Identify gaps and redundancies
4. **Phase 4**: Generate recommendations
5. **Phase 5**: Document findings in review report

## Related Files

### Task Specifications (Under Review)
- `tasks/backlog/quality-gates-integration/TASK-QG-P1-PRE-pre-loop-quality-gates.md`
- `tasks/backlog/quality-gates-integration/TASK-QG-P2-COACH-enhanced-coach-agent.md`
- `tasks/backlog/quality-gates-integration/TASK-QG-P3-POST-post-loop-plan-audit.md`
- `tasks/backlog/quality-gates-integration/README.md`

### Existing Code to Audit for Reuse
- `guardkit/planning/complexity.py` - Complexity analyzer
- `guardkit/orchestrator/autobuild.py` - Current AutoBuild orchestrator
- `installer/core/commands/lib/plan_audit.py` - Plan auditor
- `installer/core/commands/lib/clarification/` - Clarifying questions
- `installer/core/commands/lib/phase_gate_validator.py` - Gate validation
- `installer/core/commands/lib/checkpoint_display.py` - Human checkpoints
- `installer/core/commands/lib/plan_persistence.py` - Plan storage

### Review Reports
- `docs/reviews/TASK-REV-B601-quality-gates-integration-report-v3.md` - Parent review
- `tasks/in_review/TASK-REV-B601-feature-build-quality-gates-integration.md` - Parent task

## Notes

- This review should identify WHERE to integrate, not HOW to implement
- Focus on seams and code reuse, not on implementation details
- The goal is to prevent duplicate code and ensure smooth integration
- Review should be completed BEFORE starting implementation tasks
