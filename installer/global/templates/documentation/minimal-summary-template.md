# Minimal Mode Summary Template

## Purpose

This template defines the structure for **minimal mode** documentation. Minimal mode prioritizes structured data and speed, generating ~200 lines of output in 8-12 minutes.

**Target**: Complexity 1-3 tasks (simple, low-risk, <4 hours)

## Principles

1. **Structured Data**: Use JSON/YAML for machine-readable output
2. **No Verbosity**: Skip long explanations, focus on facts
3. **Essential Only**: Include only what's needed for task completion
4. **Fast Generation**: Prioritize speed over comprehensiveness

## Template Structure

### 1. Implementation Summary (Required)

```yaml
task_id: TASK-XXX
title: "{Task title}"
status: in_review
complexity: {1-3}
documentation_level: minimal

implementation:
  files_created:
    - path/to/file1.py
    - path/to/file2.py
  files_modified:
    - path/to/existing.py
  lines_of_code: {total}

  patterns_used:
    - "{Pattern name}"

  dependencies:
    - name: "{package}"
      version: "{version}"
      reason: "{brief reason}"

testing:
  total: {count}
  passed: {count}
  coverage: {percentage}%

quality_gates:
  compilation: passed
  tests: passed
  coverage: {passed|warning}
  review: approved
```

### 2. Key Decisions (Optional - Only if Non-Obvious)

```markdown
## Key Decisions

- **Decision**: {What was decided}
  **Rationale**: {One-sentence why}
```

**Include only when**:
- Non-obvious pattern choice
- Trade-off with significant impact
- Deviation from standard approach

**Skip when**:
- Obvious/standard decisions
- Complexity 1-2 tasks
- Straightforward implementations

### 3. Risks/Issues (Optional - Only if Present)

```yaml
risks:
  - severity: {low|medium|high}
    description: "{Brief description}"
    mitigation: "{One-sentence mitigation}"
```

**Include only when**:
- Actual risks identified
- Known limitations
- Follow-up work needed

**Skip when**:
- Zero risks
- Trivial tasks
- Standard implementations

## What NOT to Include

❌ **Skip These Entirely in Minimal Mode**:
- Architecture Decision Records (ADRs)
- Detailed requirement analysis
- Verbose pattern explanations
- Step-by-step implementation guides
- Comprehensive test strategy documents
- Detailed code review narratives
- Long-form rationale
- Diagrams and visual aids
- Extensive examples
- Historical context
- Alternative approaches considered

## Example: Minimal Summary

```yaml
---
task_id: TASK-042
title: Add input validation to login form
status: in_review
complexity: 2
documentation_level: minimal
---

# TASK-042 Implementation Summary

## Implementation

files_created:
  - src/utils/validators.ts

files_modified:
  - src/components/LoginForm.tsx

lines_of_code: 87

patterns_used:
  - Factory pattern (validator creation)

dependencies:
  - name: "validator"
    version: "13.11.0"
    reason: "Email/URL validation"

## Testing

total: 12
passed: 12
coverage: 94%

## Quality Gates

✅ Compilation: passed
✅ Tests: 12/12 passed
✅ Coverage: 94% (≥80%)
✅ Review: approved

## Key Decision

**Validator library**: Chose validator.js over custom implementation
**Rationale**: Battle-tested, 15k+ stars, saves 200 LOC

## Status

Ready for merge. No blockers, no follow-up needed.
```

## Validation Checklist

Minimal mode summaries should:
- [ ] Be ≤200 lines total
- [ ] Use structured data (YAML/JSON)
- [ ] Include only essential information
- [ ] Have zero verbose explanations
- [ ] Take <5 minutes to read
- [ ] Be generated in 8-12 minutes

## Agent Guidance

When generating minimal mode documentation:

1. **Start with YAML frontmatter** for structured data
2. **Use lists/bullets**, not paragraphs
3. **One sentence max** per explanation
4. **Skip optional sections** unless truly needed
5. **No examples** unless critical
6. **Reference external docs** instead of duplicating

## Target Metrics

- **Generation time**: 8-12 minutes
- **Output length**: ~200 lines
- **File count**: 1-2 files (summary + plan)
- **Token usage**: 100-150k tokens
- **Read time**: 3-5 minutes

## Related

- **Standard mode**: See `installer/global/agents/*-standard.md` for enhanced documentation
- **Comprehensive mode**: See `comprehensive-checklist.md` for full documentation suite
- **Agent specs**: See `installer/global/agents/*.md` for agent-specific documentation levels
