# Implementation Guide: Template-Create Fixes

## Execution Strategy

This guide organizes implementation into **3 waves** with clear guidance on whether each task should be implemented **directly with Claude Code** or via the full **/task-work** workflow.

### Decision Criteria

| Criteria | Direct Implementation | /task-work Workflow |
|----------|----------------------|---------------------|
| Complexity | ≤5/10 | ≥6/10 |
| Files affected | 1-2 | 3+ |
| Risk level | Low-Medium | High |
| Requires tests | Few unit tests | Integration tests |
| Architecture impact | None | Significant |

---

## Wave 1: Blocking Issues (Implement First)

**Duration**: 2-4 hours
**Parallel execution**: Yes - tasks are independent
**Conductor workspaces**: `template-fix-wave1-clmd`, `template-fix-wave1-agent`

### TASK-FIX-CLMD-SIZE: Fix CLAUDE.md Size Validation

| Attribute | Value |
|-----------|-------|
| **Method** | `/task-work` |
| **Complexity** | 7/10 |
| **Est. LOC** | 150-200 |
| **Files** | 2 (`claude_md_generator.py`, `models.py`) |
| **Conductor Workspace** | `template-fix-wave1-clmd` |

**Why /task-work**: High complexity, requires quality gates, significant behavior change.

**Execution**:
```bash
/task-work TASK-FIX-CLMD-SIZE
```

---

### TASK-FIX-AGENT-GEN: Ensure Agent Generation

| Attribute | Value |
|-----------|-------|
| **Method** | `/task-work` |
| **Complexity** | 6/10 |
| **Est. LOC** | 100-150 |
| **Files** | 2 (`agent_generator.py`, `template_create_orchestrator.py`) |
| **Conductor Workspace** | `template-fix-wave1-agent` |

**Why /task-work**: Medium-high complexity, adds new method, requires testing fallback behavior.

**Execution**:
```bash
/task-work TASK-FIX-AGENT-GEN
```

---

## Wave 2: Quality Improvements (After Wave 1)

**Duration**: 1-2 hours
**Parallel execution**: Yes - tasks are independent
**Conductor workspaces**: `template-fix-wave2-layer`, `template-fix-wave2-flag`
**Prerequisite**: Wave 1 complete (for integration testing)

### TASK-FIX-LAYER-CLASS: Add C# Layer Classification

| Attribute | Value |
|-----------|-------|
| **Method** | **Direct** |
| **Complexity** | 4/10 |
| **Est. LOC** | 80-100 |
| **Files** | 1 (`layer_classifier.py`) |
| **Conductor Workspace** | `template-fix-wave2-layer` |

**Why Direct**: Single file, pattern-based addition, low risk, follows existing pattern.

**Execution**:
```bash
# Direct implementation with Claude Code
# Add CSharpLayerClassifier class following JavaScriptLayerClassifier pattern
# Register in ChainedLayerClassifier.__init__
```

**Quick Start**:
1. Open `installer/global/lib/template_generator/layer_classifier.py`
2. Add `CSharpLayerClassifier` class after `JavaScriptLayerClassifier`
3. Add to `ChainedLayerClassifier` strategies list
4. Run unit tests: `pytest tests/lib/template_generator/test_layer_classifier.py -v`

---

### TASK-ENH-SIZE-LIMIT: Add Size Limit Flag

| Attribute | Value |
|-----------|-------|
| **Method** | **Direct** |
| **Complexity** | 3/10 |
| **Est. LOC** | 40-50 |
| **Files** | 3 (`template-create.md`, `template_create_orchestrator.py`, `models.py`) |
| **Conductor Workspace** | `template-fix-wave2-flag` |

**Why Direct**: Low complexity, additive change, no behavior change to defaults.

**Execution**:
```bash
# Direct implementation with Claude Code
# Add config field, parse method, pass to generator
```

**Quick Start**:
1. Add `claude_md_size_limit: int = 10 * 1024` to `OrchestrationConfig`
2. Add `parse_size_limit()` static method
3. Update `_write_claude_md_split()` to pass limit
4. Update `validate_size_constraints()` to accept parameter
5. Document flag in `template-create.md`

---

## Wave 3: Technical Debt (Schedule Separately)

**Duration**: 1-2 hours
**Parallel execution**: No - requires test freeze
**Prerequisite**: Full test suite passing, no active development

### TASK-RENAME-GLOBAL: Rename installer/global Directory

| Attribute | Value |
|-----------|-------|
| **Method** | **Direct** (with caution) |
| **Complexity** | 5/10 |
| **Est. LOC** | 0 (refactor only) |
| **Files** | ~20 files (44 references) |
| **Conductor Workspace** | Not recommended - use main branch |

**Why Direct**: Pure rename operation, no logic changes, but requires careful execution.

**Execution**:
```bash
# IMPORTANT: Execute during test freeze period
# 1. Ensure all tests pass
# 2. Create backup branch
# 3. Execute rename
# 4. Run full test suite
# 5. Merge if passing
```

**Quick Start**:
```bash
# Step 1: Verify clean state
git status  # Should be clean
pytest      # All tests pass

# Step 2: Create backup
git checkout -b backup/pre-rename-global

# Step 3: Rename directory
git mv installer/global installer/core

# Step 4: Update all references
find . -name "*.py" -exec sed -i '' 's/installer\.global/installer.core/g' {} \;
find . -name "*.py" -exec sed -i '' 's/installer\/global/installer\/core/g' {} \;
find . -name "*.md" -exec sed -i '' 's/installer\/global/installer\/core/g' {} \;
find . -name "*.json" -exec sed -i '' 's/installer\/global/installer\/core/g' {} \;

# Step 5: Verify
pytest  # All tests should pass

# Step 6: Commit
git add -A
git commit -m "refactor: rename installer/global to installer/core

Eliminates Python reserved keyword issue and importlib workarounds.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Parallel Execution Summary

```
┌─────────────────────────────────────────────────────────────────────┐
│ Wave 1 (Blocking)                                                   │
│                                                                     │
│   ┌─────────────────────┐     ┌─────────────────────┐              │
│   │ TASK-FIX-CLMD-SIZE  │     │ TASK-FIX-AGENT-GEN  │              │
│   │ /task-work          │     │ /task-work          │              │
│   │ Workspace: wave1-   │     │ Workspace: wave1-   │              │
│   │            clmd     │     │            agent    │              │
│   └─────────────────────┘     └─────────────────────┘              │
│              │                          │                          │
│              └──────────┬───────────────┘                          │
│                         ▼                                          │
│              ┌─────────────────────┐                               │
│              │ Integration Test    │                               │
│              │ /template-create    │                               │
│              │ on MyDrive         │                               │
│              └─────────────────────┘                               │
│                         │                                          │
└─────────────────────────┼──────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Wave 2 (Quality)                                                    │
│                                                                     │
│   ┌─────────────────────┐     ┌─────────────────────┐              │
│   │ TASK-FIX-LAYER-     │     │ TASK-ENH-SIZE-      │              │
│   │      CLASS          │     │      LIMIT          │              │
│   │ Direct              │     │ Direct              │              │
│   │ Workspace: wave2-   │     │ Workspace: wave2-   │              │
│   │            layer    │     │            flag     │              │
│   └─────────────────────┘     └─────────────────────┘              │
│              │                          │                          │
│              └──────────┬───────────────┘                          │
│                         ▼                                          │
│              ┌─────────────────────┐                               │
│              │ Verification Test   │                               │
│              │ C# classification   │                               │
│              │ + flag behavior     │                               │
│              └─────────────────────┘                               │
│                         │                                          │
└─────────────────────────┼──────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Wave 3 (Tech Debt) - Schedule Separately                           │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────┐      │
│   │ TASK-RENAME-GLOBAL                                      │      │
│   │ Direct (sequential, requires test freeze)               │      │
│   │ NO Conductor - execute on main branch                   │      │
│   └─────────────────────────────────────────────────────────┘      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Verification Checklist

### After Wave 1

- [ ] `/template-create` on MyDrive produces CLAUDE.md ≤15KB
- [ ] `/template-create` on MyDrive produces 3+ agents
- [ ] No "size validation failed" errors
- [ ] No silent Phase 5 failures

### After Wave 2

- [ ] `MauiProgram.cs` classified as "bootstrap"
- [ ] `*Tests.cs` files classified as "testing"
- [ ] `--claude-md-size-limit 50KB` works correctly
- [ ] Default behavior unchanged (10KB limit)

### After Wave 3

- [ ] All imports work without `importlib` workaround
- [ ] All tests pass
- [ ] Documentation updated
- [ ] install.sh works correctly

---

## Rollback Plan

### Wave 1/2 Rollback
```bash
# If issues found, revert specific task
git revert <commit-hash>
```

### Wave 3 Rollback
```bash
# If rename causes issues
git checkout backup/pre-rename-global
git branch -D clarifying-questions  # Or current branch
git checkout -b clarifying-questions
```

---

## Notes

1. **Wave 1 is blocking** - Complete before proceeding to Wave 2
2. **Wave 2 can run in parallel** - Tasks are independent
3. **Wave 3 should be scheduled separately** - Requires coordination with team
4. **Use Conductor for Wave 1 & 2** - Enables parallel development
5. **Wave 3 on main branch** - Too many files affected for worktree

## Task Files

- [TASK-FIX-CLMD-SIZE.md](./TASK-FIX-CLMD-SIZE.md)
- [TASK-FIX-AGENT-GEN.md](./TASK-FIX-AGENT-GEN.md)
- [TASK-FIX-LAYER-CLASS.md](./TASK-FIX-LAYER-CLASS.md)
- [TASK-ENH-SIZE-LIMIT.md](./TASK-ENH-SIZE-LIMIT.md)
- [TASK-RENAME-GLOBAL.md](./TASK-RENAME-GLOBAL.md)
