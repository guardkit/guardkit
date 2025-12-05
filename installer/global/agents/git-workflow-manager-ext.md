# git-workflow-manager - Extended Documentation

This file contains detailed examples, patterns, and implementation guides for the git-workflow-manager agent.

**Load this file when**: You need comprehensive examples, troubleshooting guidance, or deep implementation details.

**Generated**: 2025-12-05

---


## Related
- Task: TASK-042
- Agent: @git-workflow-manager
PREOF
)"
```

## Related
Closes TASK-042
PREOF
)"
```

**Why This Works**:
- Branch name includes task ID and description
- Commits follow Conventional Commits format
- PR created AFTER tests pass (Phase 4.5 complete)
- PR description includes test results and checklist

---

## Related
Closes TASK-042
Fixes #123
```

---

## Related
Closes TASK-XXX
Fixes #123
PREOF
)"
```

**PR Checklist Requirements** (from test-orchestrator):
- Build verification: 100% (compilation must succeed)
- Test pass rate: 100% (zero failing tests)
- Line coverage: ≥80%
- Branch coverage: ≥75%

**Cross-Reference**: For test threshold details, see test-orchestrator agent (Phase 4 execution)

---

## Reference