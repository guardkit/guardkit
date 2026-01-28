# Implementation Guide: Pre-Loop Documentation Enhancement

## Overview

This guide outlines the execution strategy for enhancing pre-loop documentation based on TASK-REV-PL01 review findings.

## Wave Breakdown

### Wave 1: Documentation Updates (Parallel)

Two documentation-only tasks that can execute simultaneously:

| Task | File | Method | Est. Duration |
|------|------|--------|---------------|
| TASK-PLD-001 | CLAUDE.md | direct | 15 min |
| TASK-PLD-002 | docs/guides/guardkit-workflow.md | direct | 15 min |

**Conductor Workspaces** (if using parallel execution):
- `preloop-docs-wave1-1` → TASK-PLD-001
- `preloop-docs-wave1-2` → TASK-PLD-002

**Execution**:
```bash
# Option A: Sequential (simple)
# Edit CLAUDE.md directly
# Edit docs/guides/guardkit-workflow.md directly

# Option B: Parallel with Conductor
conductor create preloop-docs-wave1-1
conductor create preloop-docs-wave1-2
# Work on both simultaneously
```

### Wave 2: CLI Update (Sequential)

Depends on Wave 1 completion (references documentation URLs):

| Task | File | Method | Est. Duration |
|------|------|--------|---------------|
| TASK-PLD-003 | guardkit/cli/autobuild.py | task-work | 30 min |

**Execution**:
```bash
/task-work TASK-PLD-003
```

## Total Estimated Duration

| Approach | Duration |
|----------|----------|
| Sequential (all tasks) | ~60 min |
| Parallel Wave 1 + Sequential Wave 2 | ~45 min |

## Success Verification

After all tasks complete:

1. **Check CLAUDE.md**:
   - Pre-Loop section has "Why" explanations
   - "When to Override" guidance present

2. **Check Workflow Guide**:
   - Decision tree present
   - Quick reference table included

3. **Check CLI Help**:
   ```bash
   guardkit autobuild feature --help | grep -A3 "enable-pre-loop"
   guardkit autobuild task --help | grep -A3 "no-pre-loop"
   ```

## Notes

- No code changes in Wave 1 (documentation only)
- Wave 2 requires code changes but minimal (help string updates)
- All tasks are low-risk
- No tests expected to break
