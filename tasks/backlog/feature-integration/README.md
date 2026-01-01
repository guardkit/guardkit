# Feature Integration: TWD + SEC

## Overview

Integration tasks for combining the AutoBuild task-work Delegation (TWD) and Coach Security Integration (SEC) features.

**Source Review**: [TASK-REV-INT01](../../TASK-REV-INT01-feature-integration-review.md)
**Report**: [.claude/reviews/TASK-REV-INT01-review-report.md](../../../.claude/reviews/TASK-REV-INT01-review-report.md)

## Tasks

| Task | Title | Dependencies | Priority |
|------|-------|--------------|----------|
| TASK-INT-001 | Unified Coach Validation Flow | TWD-008, TWD-009, SEC-001, SEC-003 | HIGH |
| TASK-INT-002 | Integration Tests for Combined Features | INT-001 | MEDIUM |

## Implementation Timeline

These tasks should be executed **after** both TWD and SEC features complete their core waves:

```
TWD Waves 1-3 ─────────┐
                       ├──► INT-001 ──► INT-002
SEC Waves 1-2 ─────────┘
```

## Key Integration Points

1. **Coach Validation Order**:
   - Security checks run BEFORE honesty verification
   - Quick security checks (~30s) always run
   - Full security review conditional on tags/config
   - Honesty verification uses security-gated test results
   - Promise verification runs last

2. **Shared Files**:
   - `.claude/agents/autobuild-coach.md` - Both add sections
   - `guardkit/orchestrator/quality_gates/coach_validator.py` - Both extend

3. **Configuration**:
   - TWD: `autobuild.mode` (tdd/standard)
   - SEC: `autobuild.security.*` (level, timeouts, exclusions)
   - Fully orthogonal, can be merged without conflict
