# Parallel Execution Strategy for Tasks 18-22

## File Conflict Analysis

### TASK-018 (Audit agents - 1h)
**Files Modified:**
- Move: `installer/global/agents/python-mcp-specialist.md` → `installer/global/templates/python/agents/`
- **No conflicts with any other task**

### TASK-019 (Remove folders - 1h)
**Files Modified:**
- Edit: `installer/scripts/init-project.sh` (lines 148-175 only - folder creation)
- **Conflicts with:** TASK-020, TASK-021 (same file, different sections)

### TASK-020 (Rebrand - 2h)
**Files Modified:**
- Edit: `installer/scripts/install.sh` (lines 472-537 - CLI commands)
- Edit: `installer/scripts/init-project.sh` (lines 36-43 header + 370-462 messages)
- Edit: `CLAUDE.md`
- Edit: `README.md`
- Rename: `docs/guides/agentecflow-lite-workflow.md` → `taskwright-workflow.md`
- **Conflicts with:** TASK-019 (init-project.sh), TASK-021 (init-project.sh), TASK-022 (CLAUDE.md + README.md)

### TASK-021 (Update output - 1.5h)
**Files Modified:**
- Edit: `installer/scripts/init-project.sh` (lines 370-462 - print_next_steps function)
- **Conflicts with:** TASK-020 (same section!), TASK-019 (same file)

### TASK-022 (Fix Phase 1 - 2h) ⭐ CRITICAL
**Files Modified:**
- Edit: `installer/global/agents/task-manager.md` (lines 82-95, workflow section)
- Edit: `CLAUDE.md` (phase list section)
- Edit: `installer/global/commands/task-work.md` (Phase 1 section)
- Edit: `README.md` (workflow section)
- **Conflicts with:** TASK-020 (CLAUDE.md + README.md)

---

## Conflict Matrix

| Task | init-project.sh | install.sh | CLAUDE.md | README.md | task-manager.md | Other |
|------|----------------|------------|-----------|-----------|-----------------|-------|
| 018  | -              | -          | -         | -         | -               | ✅ Move agent |
| 019  | ✅ Lines 148-175 | -        | -         | -         | -               | -     |
| 020  | ✅ Lines 36-43, 370-462 | ✅ Lines 472-537 | ✅ Product name | ✅ Workflow | - | ✅ Guides |
| 021  | ✅ Lines 370-462 | -        | -         | -         | -               | -     |
| 022  | -              | -          | ✅ Phase list | ✅ Workflow | ✅ Phase 1 code | ✅ Commands |

**Key Conflicts:**
- ⚠️ **init-project.sh lines 370-462**: TASK-020 and TASK-021 (HARD CONFLICT)
- ⚠️ **CLAUDE.md**: TASK-020 and TASK-022 (different sections - SOFT CONFLICT)
- ⚠️ **README.md**: TASK-020 and TASK-022 (different sections - SOFT CONFLICT)

---

## Parallelization Strategies

### Strategy A: Maximum Parallelism (Conductor Required) ⭐ RECOMMENDED

**Batch 1: Run in Parallel (3 worktrees)**
```bash
# Worktree 1 - CRITICAL FIX
git worktree add ../taskwright-task-022 -b task-022
cd ../taskwright-task-022
# Work on TASK-022 (Fix Phase 1)

# Worktree 2 - QUICK WIN
git worktree add ../taskwright-task-018 -b task-018
cd ../taskwright-task-018
# Work on TASK-018 (Move agent)

# Worktree 3 - INDEPENDENT
git worktree add ../taskwright-task-019 -b task-019
cd ../taskwright-task-019
# Work on TASK-019 (Remove folders)
```

**Merge Order:**
1. Merge TASK-018 first (no conflicts)
2. Merge TASK-019 second (no conflicts with 018)
3. Merge TASK-022 third (may have SOFT conflicts in docs with none yet merged)
4. Then proceed to TASK-020

**Time Saved:** ~2 hours (parallel execution of 1h + 1h + 2h = 2h wall-clock time)

---

**Batch 2: Sequential (After Batch 1)**
```bash
# Must be sequential due to init-project.sh conflicts
TASK-020 (2h) → TASK-021 (1.5h)
```

**Total Time:**
- Serial: 7.5 hours (1+1+2+2+1.5)
- Parallel (Strategy A): 5.5 hours (2h batch 1 + 3.5h batch 2)
- **Time Saved: 2 hours (27% faster)**

---

### Strategy B: Conservative (Minimal Conflicts)

**Batch 1: Run in Parallel (2 worktrees)**
```bash
# Worktree 1 - CRITICAL + Independent
git worktree add ../taskwright-task-022 -b task-022
# Work on TASK-022 (Fix Phase 1)

# Worktree 2 - Quick + Independent
git worktree add ../taskwright-task-018 -b task-018
# Work on TASK-018 (Move agent)
```

**Batch 2: Sequential**
```bash
# All touch init-project.sh - must be sequential
TASK-019 → TASK-020 → TASK-021
```

**Total Time:**
- Serial: 7.5 hours
- Parallel (Strategy B): 6 hours (2h batch 1 + 4.5h batch 2)
- **Time Saved: 1.5 hours (20% faster)**

---

### Strategy C: Super Aggressive (Advanced Conductor Users)

**All 3 init-project.sh tasks in parallel IF:**
- TASK-019 only edits lines 148-175 (folder creation)
- TASK-020 only edits lines 36-43 (header) + 370-462 (messages)
- TASK-021 only edits lines 370-462 (messages)

**Problem:** TASK-020 and TASK-021 both edit lines 370-462 (HARD CONFLICT)

**Solution:** Merge TASK-019 first, then TASK-020, then TASK-021

**Batch 1: All 5 in Parallel (5 worktrees)**
```bash
git worktree add ../taskwright-task-018 -b task-018
git worktree add ../taskwright-task-019 -b task-019
git worktree add ../taskwright-task-020 -b task-020
git worktree add ../taskwright-task-021 -b task-021
git worktree add ../taskwright-task-022 -b task-022
```

**Merge Order (Critical!):**
1. TASK-018 (no conflicts)
2. TASK-019 (init-project.sh lines 148-175)
3. TASK-022 (docs only at this point)
4. TASK-020 (init-project.sh lines 36-43, 370-462 + CLI + docs) - resolve doc conflicts
5. TASK-021 (init-project.sh lines 370-462) - resolve init-project.sh conflict

**Risk:** High - requires manual conflict resolution for TASK-020 vs TASK-021

**Total Time:**
- Parallel: 2 hours wall-clock (longest task)
- **Time Saved: 5.5 hours (73% faster)**
- **Risk: HIGH** (manual merge conflicts)

---

## Recommended Execution Plan: Strategy A

### Step 1: Setup Conductor (If Not Already Installed)
```bash
# Install Conductor.build
# See: https://conductor.build

# Verify taskwright is Conductor-ready
cd ~/Projects/appmilla_github/taskwright
ls -la ~/.claude/commands  # Should be symlink to ~/.agentecflow/commands
```

### Step 2: Create Worktrees for Batch 1
```bash
# From main taskwright repo
cd ~/Projects/appmilla_github/taskwright

# Create 3 worktrees
git worktree add ../taskwright-task-018 -b task/018-audit-agents
git worktree add ../taskwright-task-019 -b task/019-remove-folders
git worktree add ../taskwright-task-022 -b task/022-fix-phase1

# Verify worktrees
git worktree list
```

### Step 3: Open 3 Conductor Windows
```bash
# Terminal 1 - TASK-022 (CRITICAL)
cd ~/Projects/appmilla_github/taskwright-task-022
conductor open  # Opens Claude Code in this worktree

# Terminal 2 - TASK-018 (Quick)
cd ~/Projects/appmilla_github/taskwright-task-018
conductor open

# Terminal 3 - TASK-019 (Independent)
cd ~/Projects/appmilla_github/taskwright-task-019
conductor open
```

### Step 4: Execute in Parallel (Claude Code in each window)
```bash
# Window 1: TASK-022 (2 hours)
/task-work TASK-022

# Window 2: TASK-018 (1 hour)
/task-work TASK-018

# Window 3: TASK-019 (1 hour)
/task-work TASK-019
```

### Step 5: Merge in Order
```bash
# Back to main repo
cd ~/Projects/appmilla_github/taskwright

# 1. Merge TASK-018 (no conflicts)
git merge task/018-audit-agents
git push

# 2. Merge TASK-019 (no conflicts with 018)
git merge task/019-remove-folders
git push

# 3. Merge TASK-022 (may have doc conflicts - easy to resolve)
git merge task/022-fix-phase1
# If conflicts in CLAUDE.md or README.md:
#   - Accept both changes (they're in different sections)
git push

# Cleanup worktrees
git worktree remove ../taskwright-task-018
git worktree remove ../taskwright-task-019
git worktree remove ../taskwright-task-022
```

### Step 6: Sequential Execution (Batch 2)
```bash
# TASK-020 and TASK-021 must be sequential (same file/section)
cd ~/Projects/appmilla_github/taskwright

/task-work TASK-020  # 2 hours
/task-complete TASK-020

/task-work TASK-021  # 1.5 hours
/task-complete TASK-021
```

---

## Benefits of Strategy A

✅ **Time Savings**: 2 hours (27% faster)
✅ **Low Risk**: Only soft conflicts in docs (easy to resolve)
✅ **High Priority First**: TASK-022 (critical) done in parallel
✅ **Clean Merge Path**: Clear order prevents hard conflicts
✅ **Conductor Compatible**: Designed for parallel worktree execution

---

## Alternative: If No Conductor

If you don't have Conductor.build installed, you can still use git worktrees manually:

```bash
# Create worktrees
git worktree add ../task-018 -b task-018
git worktree add ../task-019 -b task-019
git worktree add ../task-022 -b task-022

# Open 3 terminal tabs/windows
# Tab 1: cd ../task-018 && code . (VSCode with Claude Code)
# Tab 2: cd ../task-019 && code .
# Tab 3: cd ../task-022 && code .

# Work in each VSCode instance
# Merge as described in Step 5
```

---

## Summary

**Recommended: Strategy A with Conductor**
- **3 tasks in parallel**: TASK-018, TASK-019, TASK-022
- **2 tasks sequential**: TASK-020 → TASK-021
- **Wall-clock time**: 5.5 hours (vs 7.5 serial)
- **Complexity**: Low (minimal merge conflicts)
- **Prioritizes**: TASK-022 (critical fix) done first

Would you like me to help you set up the Conductor worktrees and start parallel execution?
