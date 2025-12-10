# Template-Init Feature Porting Tasks

This directory contains all 11 tasks for porting features from `/template-create` to `/template-init`, as specified in TASK-5E55 decision (Option B: Port Features).

## Overview

**Parent Review**: TASK-5E55  
**Decision**: Option B - Port Features (Approved)  
**Timeline**: 5 weeks, 60 hours  
**Status**: Ready for implementation

## Task Files

| Task ID | Title | Week | Hours | Priority | Dependencies |
|---------|-------|------|-------|----------|--------------|
| [TASK-INIT-001](TASK-INIT-001-boundary-sections.md) | Port boundary sections | 1 | 8 | HIGH | None |
| [TASK-INIT-002](TASK-INIT-002-agent-enhancement-tasks.md) | Port agent enhancement tasks | 1 | 6 | HIGH | TASK-INIT-001 |
| [TASK-INIT-003](TASK-INIT-003-level1-validation.md) | Port Level 1 validation | 2 | 4 | MEDIUM | None |
| [TASK-INIT-004](TASK-INIT-004-level2-validation.md) | Port Level 2 validation | 2 | 4 | MEDIUM | TASK-INIT-003 |
| [TASK-INIT-005](TASK-INIT-005-level3-integration.md) | Integrate Level 3 audit | 2 | 4 | MEDIUM | TASK-INIT-004 |
| [TASK-INIT-006](TASK-INIT-006-quality-scoring.md) | Port quality scoring | 3 | 6 | MEDIUM | TASK-INIT-003-005 |
| [TASK-INIT-007](TASK-INIT-007-two-location-output.md) | Port two-location output | 3 | 4 | HIGH | None |
| [TASK-INIT-008](TASK-INIT-008-discovery-metadata.md) | Port discovery metadata | 4 | 4 | MEDIUM | TASK-INIT-001 |
| [TASK-INIT-009](TASK-INIT-009-exit-codes.md) | Port exit codes | 4 | 2 | LOW | TASK-INIT-006 |
| [TASK-INIT-010](TASK-INIT-010-documentation.md) | Update documentation | 5 | 4 | HIGH | All 1-9 |
| [TASK-INIT-011](TASK-INIT-011-comprehensive-testing.md) | Comprehensive testing | 5 | 8 | HIGH | All 1-9 |

**Total**: 54 hours across 11 tasks (Week 5 testing is 8 hours, bringing total to 58 hours, plus 2 hours buffer = 60 hours)

## Quick Start

```bash
# Week 1: Critical Features (sequential)
/task-work TASK-INIT-001
/task-work TASK-INIT-002

# Week 2: Validation Framework (can parallelize)
/task-work TASK-INIT-003
/task-work TASK-INIT-004
/task-work TASK-INIT-005

# Week 3: Quality & Distribution (can parallelize)
/task-work TASK-INIT-006
/task-work TASK-INIT-007

# Week 4: Discovery & Automation (can parallelize)
/task-work TASK-INIT-008
/task-work TASK-INIT-009

# Week 5: Polish (sequential)
/task-work TASK-INIT-010
/task-work TASK-INIT-011
```

## Implementation Guides

- **[Implementation Guide](../../docs/implementation/template-init-implementation-guide.md)**: Complete guide with /task-work commands, wave-based strategy, Conductor parallel development
- **[Master Task Guide](../../docs/implementation/template-init-feature-porting-tasks.md)**: Detailed specifications for all 11 tasks

## Parallel Development

### Conductor Integration

For teams wanting to work in parallel:

**Week 2** (3 developers):
```bash
# Developer 1
conductor create task-init-003
/task-work TASK-INIT-003

# Developer 2
conductor create task-init-004
/task-work TASK-INIT-004

# Developer 3
conductor create task-init-005
/task-work TASK-INIT-005
```

**Week 3** (2 developers):
```bash
# Developer 1
conductor create task-init-006
/task-work TASK-INIT-006

# Developer 2
conductor create task-init-007
/task-work TASK-INIT-007
```

**Week 4** (2 developers):
```bash
# Developer 1
conductor create task-init-008
/task-work TASK-INIT-008

# Developer 2
conductor create task-init-009
/task-work TASK-INIT-009
```

See [Implementation Guide](../../docs/implementation/template-init-implementation-guide.md) for complete Conductor workflow.

## Key Principles

### MINIMAL SCOPE

All tasks enforce **MINIMAL SCOPE** principle:

- ❌ **DO NOT**: Refactor existing code, modify Q&A workflow, change template format
- ✅ **DO ONLY**: Add new functions, integrate at specified points, maintain backward compatibility

### Task Structure

Each task file includes:

1. **Problem Statement**: What's missing and why
2. **Analysis Findings**: From TASK-5E55 review
3. **Recommended Fix**: Approach with MINIMAL SCOPE emphasis
4. **Code Changes Required**: BEFORE/AFTER with line numbers
5. **Scope Constraints**: Explicit DO/DON'T lists
6. **Files to Modify vs NOT Touch**: Clear boundaries
7. **Testing Requirements**: Unit, integration, regression tests
8. **Acceptance Criteria**: Definition of done
9. **Dependencies**: What must complete first
10. **Risk Assessment**: Risks and mitigation strategies

## Quality Gates

After each week:

1. All tasks completed
2. All tests pass
3. No regressions in existing Q&A
4. Feature demo/review
5. Decision: Continue or pause

## Success Metrics

- ✅ 100% feature parity with /template-create
- ✅ 0 breaking changes to existing Q&A
- ✅ <5% performance impact
- ✅ 90%+ test coverage
- ✅ All 11 tasks completed

## References

- **Parent Review**: [TASK-5E55](../../tasks/in_review/TASK-5E55-review-greenfield-initialization-workflow.md)
- **Decision Analysis**: [template-init-vs-template-create-analysis.md](../../docs/decisions/template-init-vs-template-create-analysis.md)
- **Implementation File**: [installer/core/commands/lib/greenfield_qa_session.py](../../../installer/core/commands/lib/greenfield_qa_session.py)

## Questions?

See [Implementation Guide FAQ](../../docs/implementation/template-init-implementation-guide.md#questions) for common questions about workflow, TDD mode, quality gates, and Conductor usage.
