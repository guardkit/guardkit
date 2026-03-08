---
id: TASK-CSC-007
title: Update documentation and proposal
status: backlog
created: 2026-01-23T11:30:00Z
priority: medium
tags: [context-sensitive-coach, documentation]
task_type: documentation
complexity: 2
parent_review: TASK-REV-CSC1
feature_id: FEAT-CSC
wave: 4
implementation_mode: direct
conductor_workspace: csc-wave4-docs
dependencies:
  - TASK-CSC-005
---

# Task: Update Documentation and Proposal

## Description

Update the original proposal with final implementation details and add usage documentation to CLAUDE.md.

## Acceptance Criteria

- [ ] Update `docs/research/context-sensitive-coach-proposal.md` with final design
- [ ] Add Context-Sensitive Coach section to root CLAUDE.md
- [ ] Document the feature flag (`GUARDKIT_CONTEXT_SENSITIVE_COACH`)
- [ ] Document profile selection behavior
- [ ] Add troubleshooting section

## Implementation Notes

### CLAUDE.md Addition

Add under "Quality Gates" section:

```markdown
## Context-Sensitive Coach (Experimental)

The context-sensitive Coach adapts quality gate thresholds based on what was actually implemented,
rather than applying fixed thresholds based solely on task_type.

### Enabling

Set the feature flag:
```bash
export GUARDKIT_CONTEXT_SENSITIVE_COACH=true
```

### How It Works

1. **Universal Context**: Gathers git diff statistics (LOC, file counts)
2. **Fast Classification**: Trivial (<30 LOC) and complex (>300 LOC) cases get immediate profiles
3. **AI Analysis**: Uncertain cases (30-300 LOC) get AI-based testability analysis
4. **Dynamic Profile**: Profile selected based on actual implementation characteristics

### Profile Selection

| Scenario | Profile | Gates Applied |
|----------|---------|---------------|
| Trivial (<30 LOC, declarative) | minimal | Plan audit only |
| Simple (30-100 LOC, low testability) | light | Tests + 50% coverage |
| Standard (typical code) | standard | Tests + 70% coverage + arch review |
| Complex (>300 LOC or high risk) | strict | Full gates (80% coverage, 60 arch score) |

### Benefits

- Declarative code (DTOs, configs) no longer fail coverage gates
- Simple implementations pass with appropriate rigor
- Complex changes still get full scrutiny
- AI analyzes across all languages (no plugins needed)

### Troubleshooting

**Q: Why did my task get "strict" profile?**
A: Check the logs for "Selected profile:" to see the rationale. Common causes:
- >300 LOC added
- >10 files changed
- Security/payment/database tags in task

**Q: AI analysis seems slow**
A: AI analysis only runs for "uncertain" cases (30-300 LOC). Results are cached between turns.

**Q: Can I force a specific profile?**
A: Not currently. The system is designed to be automatic based on implementation characteristics.
```

### Proposal Update

Update `docs/research/context-sensitive-coach-proposal.md`:

1. Mark "AI-First Approach" as the implemented design
2. Remove plugin-based sections (or mark as "considered but not implemented")
3. Add "Implementation Status" section
4. Add performance benchmarks from testing
5. Add lessons learned

## Notes

This is a documentation-only task. No code changes required.
