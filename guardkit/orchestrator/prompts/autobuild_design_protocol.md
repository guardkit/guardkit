# AutoBuild Design Protocol

> Focused protocol for pre-loop design phases (Phases 1.5–2.8).
> Extracted from the full task-work specification for efficient context injection.
> Optimized for autonomous execution (no human interaction required).

---

## Overview

Execute these phases in sequence to produce an approved implementation plan:

1. **Phase 1.5**: Load Task Context
2. **Phase 2**: Implementation Planning
3. **Phase 2.5B**: Architectural Review (inline, simplified)
4. **Phase 2.7**: Complexity Evaluation
5. **Phase 2.8**: Design Checkpoint (auto-approve)

### Skipped Phases (AutoBuild Optimization)

The following phases are skipped in autonomous mode:

| Phase | Name | Reason for Skip |
|---|---|---|
| 1.6 | Clarifying Questions | No human present for interaction |
| 1.7 | Graphiti Context | Loaded separately by orchestrator |
| 2.1 | Library Context Gathering | Context7 not available in SDK |
| 2.5A | Pattern Suggestion | Design Patterns MCP not available in SDK |

---

## Phase 1.5: Load Task Context

Read the task file and extract all required context.

### Task File Location

Search for the task file using this pattern:
```
tasks/*/{task_id}*.md
```

Check directories in order:
1. `tasks/backlog/` (and subdirectories)
2. `tasks/in_progress/`
3. `tasks/design_approved/`

### Required Extraction

From the task file, extract:

| Field | Source | Required |
|---|---|---|
| Title | Frontmatter `title:` | YES |
| Description | `## Description` or `## Objective` section | YES |
| Acceptance Criteria | `## Acceptance Criteria` section | YES |
| Implementation Notes | `## Implementation Notes` or `## Technical Notes` | NO |
| Complexity | Frontmatter `complexity:` | NO (default: 5) |
| Task Type | Frontmatter `task_type:` | NO (default: feature) |
| Tags | Frontmatter `tags:` | NO |
| Dependencies | Frontmatter `dependencies:` | NO |

### Error Handling

If the task file is not found, output:
```
Error: Task file not found for {task_id}
```
and stop execution.

### Output

Display a brief summary of loaded context:
```
Task: {task_id} - {title}
Type: {task_type}
Complexity: {complexity}/10
Acceptance Criteria: {count} items
```

---

## Phase 2: Implementation Planning

Create a structured implementation plan based on the task context.

### Plan Requirements

The plan MUST include:

1. **Overview**: What will be implemented (1-2 sentences)
2. **Files to Create/Modify**: Each file with its purpose
3. **Implementation Approach**: Step-by-step approach
4. **Test Strategy**: What tests to write, how to verify
5. **Dependencies**: New packages or modules needed
6. **Estimated Effort**: Lines of code estimate, rough duration
7. **Risks**: Potential issues and mitigations

### Plan Template

Use this structure for the implementation plan:

```markdown
# Implementation Plan: {task_id}

## Overview
{1-2 sentence summary of what will be implemented}

## Files

### Files to Create
| File | Purpose | Est. LOC |
|------|---------|----------|
| src/module.py | Main implementation | ~100 |
| tests/test_module.py | Unit tests | ~80 |

### Files to Modify
| File | Changes | Est. LOC Delta |
|------|---------|----------------|
| src/existing.py | Add integration point | +15 |

## Implementation Approach
1. Step one...
2. Step two...
3. Step three...

## Test Strategy
- Unit tests for core logic
- Integration tests for module boundaries
- Edge cases: empty input, invalid data, boundary values

## Dependencies
- {package}: {version} — {why needed}

## Estimated Effort
- Lines of code: ~{N}
- Estimated duration: {N} hours
- Complexity: {N}/10

## Risks
| Risk | Severity | Mitigation |
|------|----------|------------|
| {description} | LOW/MEDIUM/HIGH | {mitigation} |
```

### Task Type Considerations

Different task types have different planning requirements:

| Task Type | Plan Focus |
|---|---|
| FEATURE | Full plan with architecture, tests, dependencies |
| REFACTOR | Focus on before/after structure, migration steps |
| SCAFFOLDING | File structure, interfaces, integration points |
| INFRASTRUCTURE | Configuration, deployment, monitoring |
| INTEGRATION | Wiring, data flow, error handling at boundaries |

### Documentation Level Guidance

| Level | Plan Detail |
|---|---|
| minimal | Structured data focus: file list, phases, estimates |
| standard | Brief architecture notes and key decisions |
| comprehensive | Detailed rationale, alternatives considered, ADRs |

### Save Location

Write the plan to:
```
.claude/task-plans/{task_id}-implementation-plan.md
```

Create the directory if needed:
```bash
mkdir -p .claude/task-plans
```

### Output Marker (Required)

After saving, output this exact line:
```
Plan saved to: .claude/task-plans/{task_id}-implementation-plan.md
```

This marker is parsed programmatically. Do NOT modify the format.

---

## Phase 2.5B: Architectural Review (Simplified)

Perform an inline architectural review of the implementation plan.

NOTE: In AutoBuild mode, this is an inline self-review. Do NOT invoke a subagent or external tool. Evaluate the plan yourself.

### Evaluation Criteria

Score each principle from 0-100:

**SOLID Principles** (weighted 30%):
- **Single Responsibility**: Each class/module has one reason to change. A service that both validates input AND writes to the database has two responsibilities — split them.
- **Open/Closed**: Open for extension, closed for modification. Use strategy patterns, configuration, or dependency injection rather than modifying existing classes.
- **Liskov Substitution**: Subtypes must be substitutable for base types. If you override a method, the contract (preconditions, postconditions) must be preserved.
- **Interface Segregation**: No forced dependency on unused interfaces. Split large interfaces into smaller, role-specific ones.
- **Dependency Inversion**: High-level modules depend on abstractions, not concretions. Use protocols (Python), interfaces (TypeScript/.NET), or abstract base classes.

**DRY (Don't Repeat Yourself)** (weighted 25%):
- No duplicated logic across modules
- Shared functionality properly extracted into utility functions or base classes
- Constants and configuration centralized (not magic numbers scattered across files)
- Common patterns abstracted (but not prematurely — see YAGNI)

**YAGNI (You Aren't Gonna Need It)** (weighted 25%):
- No speculative features or over-engineering beyond acceptance criteria
- Minimum complexity needed for the requirements
- No unnecessary abstractions, wrapper classes, or configuration points
- No "just in case" code or unused parameters
- Three similar lines of code is better than a premature abstraction

**Testability** (weighted 20%):
- Dependencies injectable (not hard-coded)
- Side effects isolated (I/O at edges, logic in core)
- Test seams available (no private methods doing all the work)
- State changes observable (return values or inspectable state)

### Scoring Guide

For each principle, use this rubric:

| Score | Meaning |
|---|---|
| 90-100 | Excellent: Clean, well-structured, follows principle fully |
| 80-89 | Good: Minor opportunities for improvement |
| 70-79 | Acceptable: Some violations but not critical |
| 60-69 | Marginal: Needs improvement before implementation |
| 0-59 | Poor: Significant violations, requires redesign |

Calculate overall score as weighted average:
`Overall = SOLID × 0.30 + DRY × 0.25 + YAGNI × 0.25 + Testability × 0.20`

### Common Issues to Check

1. **God classes/modules**: Single file doing too much
2. **Tight coupling**: Modules directly referencing concrete implementations
3. **Missing error handling**: Happy path only, no error recovery
4. **Untestable code**: Hard-coded dependencies, global state
5. **Premature abstraction**: Interface with only one implementation
6. **Scope creep**: Files or features not in acceptance criteria

### Output Markers (Required)

Output scores in these exact formats:
```
Architectural Score: N/100
SOLID: N, DRY: N, YAGNI: N
```

Where N is the calculated score (0-100) for each.

### Thresholds

| Score | Action |
|---|---|
| >= 80 | Good architecture, proceed |
| 60-79 | Acceptable with recommendations |
| < 60 | Needs revision, flag issues |

If score < 60, list specific issues that need to be addressed before implementation can proceed.

---

## Phase 2.7: Complexity Evaluation

Evaluate implementation complexity on a 1-10 scale.

### Scoring Factors

| Factor | Score Range | Criteria |
|---|---|---|
| File complexity | 0-3 | 1-2 files = 1, 3-5 = 2, 6+ = 3 |
| Pattern complexity | 0-2 | Known patterns = 0, novel = 1, complex integration = 2 |
| Risk level | 0-3 | No risks = 0, external deps = 1, security/schema = 2, breaking changes = 3 |
| Dependencies | 0-2 | None = 0, internal = 1, external = 2 |

Total score = sum of factors (cap at 10).

### Complexity Level Mapping

| Score | Level | Max Turns | Review Mode |
|---|---|---|---|
| 1-3 | Simple | 3 | AUTO_PROCEED |
| 4-6 | Medium | 5 | QUICK_OPTIONAL |
| 7-10 | Complex | 7 | FULL_REQUIRED |

The complexity score determines:
1. **Max turns** for the adversarial loop — simple tasks get fewer turns
2. **Review mode** — complex tasks require full human review (but auto-approved in AutoBuild)
3. **Timeout configuration** — higher complexity = longer SDK timeout

### High-Risk Keywords

The following keywords in the task description force complexity to at least 7, regardless of calculated score:

- Security: `security`, `auth`, `authentication`, `authorization`, `oauth`, `jwt`, `encryption`, `crypto`
- Data: `schema`, `migration`, `database`
- Breaking: `breaking`, `breaking change`, `api`, `endpoint`
- Financial: `financial`, `payment`, `billing`
- Vulnerabilities: `injection`, `xss`, `csrf`

If any high-risk keyword is detected, set: `complexity = max(calculated_score, 7)`

### Output Marker (Required)

Output the score in this exact format:
```
Complexity: N/10
```

Where N is the calculated score (1-10).

---

## Phase 2.8: Design Checkpoint

In AutoBuild mode, the design checkpoint is auto-approved (no human present).

### Output Markers (Required)

Output these exact lines:
```
Phase 2.8: checkpoint approved
State: DESIGN_APPROVED
```

---

## Output Summary

After completing all phases, provide a brief summary:

```
Design Phase Complete for {task_id}
- Plan: .claude/task-plans/{task_id}-implementation-plan.md
- Architectural Score: N/100
- Complexity: N/10
- Checkpoint: approved
```

---

## Critical Output Format Requirements

The following output markers MUST appear exactly as shown. They are parsed programmatically by TaskWorkStreamParser:

| Marker | Format | Example |
|---|---|---|
| Plan saved | `Plan saved to: .claude/task-plans/{task_id}-implementation-plan.md` | `Plan saved to: .claude/task-plans/TASK-001-implementation-plan.md` |
| Complexity | `Complexity: N/10` | `Complexity: 5/10` |
| Checkpoint | `Phase 2.8: checkpoint approved` | (exact match) |
| State | `State: DESIGN_APPROVED` | (exact match) |
| Arch score | `Architectural Score: N/100` | `Architectural Score: 85/100` |
| Arch subscores | `SOLID: N, DRY: N, YAGNI: N` | `SOLID: 88, DRY: 82, YAGNI: 85` |

Do NOT modify these marker formats. Automated processing depends on exact matches.

---

## Summary

This protocol defines the complete design phase for AutoBuild:
1. **Phase 1.5**: Read task file, extract context
2. **Phase 2**: Create and save implementation plan
3. **Phase 2.5B**: Inline architectural review (self-assessment)
4. **Phase 2.7**: Calculate complexity score
5. **Phase 2.8**: Auto-approve checkpoint
