# Template-Create Fixes: Implementation Guide

**Date**: 2025-11-12
**Context**: Execute TASK-9037, 9038, 9039 to fix template-create issues
**Approach**: Use `/task-work` with parallel execution via Conductor (git worktrees)

---

## Executive Summary

**Goal**: Fix template-create to be fully functional with correct language detection and non-interactive workflow

**Tasks to Execute**:
1. TASK-9037 - Fix build artifact exclusion (2-3 hours)
2. TASK-9038 - Create /template-qa command (3-4 hours)
3. TASK-9039 - Remove Q&A from /template-create (4-5 hours)

**Total Time**: 9-12 hours sequential, **5-8 hours parallel** (45% time savings)

**Parallelization**: ✅ Tasks 9037 and 9038 can run in parallel (independent)

---

## Dependency Analysis

### Task Dependencies

```
TASK-9037 (Build Artifacts)
    ↓ (independent)
    [Can merge anytime]

TASK-9038 (Q&A Command)
    ↓ (TASK-9039 depends on this)
    TASK-9039 (Remove Q&A)
    ↓
    [Final merge]
```

**Parallel Groups**:
- **Group A**: TASK-9037 (independent)
- **Group B**: TASK-9038 → TASK-9039 (sequential chain)

**Execution Strategy**:
1. Start TASK-9037 and TASK-9038 **in parallel** (different worktrees)
2. TASK-9037 completes first (2-3h) → merge to main
3. TASK-9038 completes (3-4h) → merge to main
4. Start TASK-9039 on main (after 9038 merged) (4-5h) → merge to main

**Time Savings**: 2-3 hours (TASK-9037 parallel with TASK-9038 start)

---

## File Conflict Analysis

### Files Modified by Each Task

**TASK-9037** (Build Artifacts):
```
installer/global/lib/template_creation/exclusions.py          (NEW)
installer/global/lib/codebase_analyzer/ai_analyzer.py         (MODIFY)
tests/unit/test_exclusions.py                                 (NEW)
tests/integration/test_build_artifact_exclusion.py            (NEW)
```

**TASK-9038** (Q&A Command):
```
installer/global/commands/template-qa.md                      (NEW)
installer/global/commands/lib/template_qa_orchestrator.py     (NEW)
installer/global/lib/template_creation/qa_session.py          (EXTRACT from orchestrator)
tests/unit/test_template_qa_orchestrator.py                   (NEW)
```

**TASK-9039** (Remove Q&A):
```
installer/global/commands/lib/template_create_orchestrator.py (MODIFY)
installer/global/lib/template_creation/smart_defaults.py      (NEW)
tests/unit/test_smart_defaults.py                             (NEW)
tests/integration/test_template_create_non_interactive.py     (NEW)
```

### Conflict Risk Assessment

**TASK-9037 vs TASK-9038**: ✅ **ZERO CONFLICTS**
- No shared files
- Different modules (codebase_analyzer vs template_creation)
- Safe to run in parallel

**TASK-9038 vs TASK-9039**: ⚠️ **POTENTIAL CONFLICTS**
- Both modify template_create_orchestrator.py (TASK-9038 extracts, TASK-9039 modifies)
- TASK-9039 DEPENDS ON TASK-9038 (needs qa_session.py to exist)
- **Must run sequentially**: TASK-9038 → merge → TASK-9039

**Verdict**: ✅ **TASK-9037 and TASK-9038 can run in parallel safely**

---

## Implementation Strategy

### Option 1: Parallel Execution (Recommended - 45% faster)

**Use Conductor with Git Worktrees**

**Setup**:
```bash
# Terminal 1: Main worktree (for monitoring/merging)
cd ~/Projects/appmilla_github/taskwright
git checkout main
git pull

# Terminal 2: Worktree for TASK-9037
conductor create task-9037
# Creates: ~/Projects/appmilla_github/taskwright-task-9037/
cd ~/Projects/appmilla_github/taskwright-task-9037
/task-work TASK-9037

# Terminal 3: Worktree for TASK-9038
conductor create task-9038
# Creates: ~/Projects/appmilla_github/taskwright-task-9038/
cd ~/Projects/appmilla_github/taskwright-task-9038
/task-work TASK-9038
```

**Timeline**:
```
0:00 - Start TASK-9037 and TASK-9038 in parallel
2:30 - TASK-9037 completes → merge to main
4:00 - TASK-9038 completes → merge to main
4:00 - Start TASK-9039 (on main, after 9038 merged)
8:00 - TASK-9039 completes → merge to main
      DONE (8 hours total)
```

**Time Savings**: 4 hours saved vs sequential (12h → 8h)

---

### Option 2: Sequential Execution (Simpler, but slower)

**Use Single Main Branch**

**Timeline**:
```
0:00 - Start TASK-9037
2:30 - TASK-9037 completes → commit to main
2:30 - Start TASK-9038
6:30 - TASK-9038 completes → commit to main
6:30 - Start TASK-9039
11:30 - TASK-9039 completes → commit to main
       DONE (11.5 hours total)
```

**Advantages**:
- Simpler workflow (no worktree management)
- No merge conflicts to resolve
- Single context switching

**Disadvantages**:
- 44% longer (11.5h vs 8h)
- Idle time while waiting for sequential tasks

---

## Recommended Approach: Parallel with Conductor

### Phase 1: Setup Conductor Worktrees (5 minutes)

**Verify Conductor is installed**:
```bash
conductor --version
# Should show Conductor version
```

**If not installed**, follow Conductor setup (or skip to Option 2 - Sequential)

**Create worktrees**:
```bash
# Terminal 1: Main repo (for coordination)
cd ~/Projects/appmilla_github/taskwright
git checkout main
git pull origin main

# Terminal 2: Worktree for TASK-9037
conductor create task-9037
cd ~/Projects/appmilla_github/taskwright-task-9037
git checkout -b fix/task-9037-build-artifacts

# Terminal 3: Worktree for TASK-9038
conductor create task-9038
cd ~/Projects/appmilla_github/taskwright-task-9038
git checkout -b feature/task-9038-qa-command
```

---

### Phase 2: Execute TASK-9037 and TASK-9038 in Parallel (2-4 hours)

**Terminal 2 (TASK-9037)**:
```bash
cd ~/Projects/appmilla_github/taskwright-task-9037

# Execute task-work (uses taskwright workflow)
/task-work TASK-9037

# Monitor progress
# Expected: 2-3 hours
# Output: Build artifact exclusion implemented, tests passing
```

**Terminal 3 (TASK-9038)**:
```bash
cd ~/Projects/appmilla_github/taskwright-task-9038

# Execute task-work (uses taskwright workflow)
/task-work TASK-9038

# Monitor progress
# Expected: 3-4 hours
# Output: /template-qa command created, tests passing
```

**What /task-work Does** (Automatic):
1. Phase 1: Load task context
2. Phase 2: Implementation planning
3. Phase 2.5B: Architectural review
4. Phase 2.7: Complexity evaluation
5. Phase 3: Implementation (agent writes code)
6. Phase 4: Testing (agent creates tests, runs tests)
7. Phase 4.5: Fix loop (auto-fix failing tests)
8. Phase 5: Code review

**Human Involvement**:
- Phase 2.8: Optional checkpoint (if complexity ≥ 7)
- Final review: Verify implementation meets acceptance criteria

---

### Phase 3: Merge TASK-9037 First (10 minutes)

**When TASK-9037 completes in Terminal 2**:

```bash
# Terminal 2: TASK-9037 worktree
cd ~/Projects/appmilla_github/taskwright-task-9037

# Verify tests pass
pytest tests/unit/test_exclusions.py -v
pytest tests/integration/test_build_artifact_exclusion.py -v

# Verify quality gates
# - All tests passing ✅
# - Coverage ≥ 80% ✅
# - Code review approved ✅

# Commit and push (if not already done by /task-work)
git add .
git commit -m "Complete TASK-9037: Fix build artifact exclusion

- Add DEFAULT_EXCLUSIONS for all stacks
- Implement should_exclude_path() function
- Integrate with ai_analyzer.py
- Add comprehensive tests

Fixes language detection (C# no longer detected as Java)
All tests passing, coverage 86%"

git push origin fix/task-9037-build-artifacts

# Create PR (or merge directly)
gh pr create --title "Fix build artifact exclusion (TASK-9037)" \
             --body "Fixes critical bug in language detection. See TASK-9037 for details."

# Or merge directly to main
git checkout main
git merge fix/task-9037-build-artifacts
git push origin main
```

**Terminal 1: Main repo**:
```bash
# Pull latest changes
git pull origin main

# Verify TASK-9037 changes merged
ls installer/global/lib/template_creation/exclusions.py
# Should exist ✅

# Test on real project (AI-native mode)
cd ~/Projects/DeCUK.Mobile.MyDrive
/template-create

# Expected:
# - Detects as C# (not Java) ✅
# - Excludes obj/, bin/ ✅
# - Correct file counts ✅
```

---

### Phase 4: Merge TASK-9038 Second (10 minutes)

**When TASK-9038 completes in Terminal 3**:

```bash
# Terminal 3: TASK-9038 worktree
cd ~/Projects/appmilla_github/taskwright-task-9038

# Verify tests pass
pytest tests/unit/test_template_qa_orchestrator.py -v

# Test new command
/template-qa
# Should run Q&A session ✅
# Should save config to .template-create-config.json ✅

# Commit and push (if not already done by /task-work)
git add .
git commit -m "Complete TASK-9038: Create /template-qa command

- Extract Q&A logic from template_create_orchestrator
- Create new /template-qa command
- Save config to .template-create-config.json
- Add --resume flag for editing configs

All tests passing, command functional"

git push origin feature/task-9038-qa-command

# Create PR (or merge directly)
gh pr create --title "Create /template-qa command (TASK-9038)" \
             --body "New optional Q&A command for customization. See TASK-9038 for details."

# Or merge directly to main
git checkout main
git merge feature/task-9038-qa-command
git push origin main
```

**Terminal 1: Main repo**:
```bash
# Pull latest changes
git pull origin main

# Verify TASK-9038 changes merged
/template-qa --help
# Should show command help ✅

# Test Q&A workflow
cd ~/Projects/test-project
/template-qa
# Should run Q&A, save config ✅
```

---

### Phase 5: Execute TASK-9039 (4-5 hours)

**IMPORTANT**: Start TASK-9039 **only after** TASK-9038 is merged to main

**Terminal 1 or new worktree**:
```bash
# Option A: Work directly on main (simpler)
cd ~/Projects/appmilla_github/taskwright
git checkout main
git pull origin main
/task-work TASK-9039

# Option B: Use new worktree (cleaner)
conductor create task-9039
cd ~/Projects/appmilla_github/taskwright-task-9039
git checkout -b refactor/task-9039-remove-qa
/task-work TASK-9039
```

**What /task-work Does**:
1. Loads TASK-9039 context
2. Plans refactor of template_create_orchestrator.py
3. Implements smart defaults
4. Removes Q&A prompts from default flow
5. Adds --config flag support
6. Tests non-interactive workflow
7. Runs all tests (integration + unit)
8. Code review

**Expected Duration**: 4-5 hours

---

### Phase 6: Merge TASK-9039 Final (10 minutes)

**When TASK-9039 completes**:

```bash
# Verify tests pass
pytest tests/integration/test_template_create_non_interactive.py -v

# Test non-interactive workflow
cd ~/Projects/test-project
/template-create
# Should work without prompts ✅
# Should use smart defaults ✅
# Should detect language automatically ✅

# Test with config file
/template-qa
/template-create --config .template-create-config.json
# Should use config values ✅

# Commit and merge
git add .
git commit -m "Complete TASK-9039: Remove Q&A from /template-create

- Implement smart defaults for language/framework detection
- Removed Q&A prompts entirely (TASK-51B2)
- AI analyzes codebase automatically
- --skip-qa flag removed (no longer needed)

Template-create now uses AI-native analysis by default"

git push origin refactor/task-9039-remove-qa

# Merge to main
git checkout main
git merge refactor/task-9039-remove-qa
git push origin main
```

---

### Phase 7: Final Integration Testing (30 minutes)

**Verify all fixes work together**:

```bash
cd ~/Projects/appmilla_github/taskwright
git checkout main
git pull origin main

# Test 1: Language detection (TASK-9037)
cd ~/Projects/DeCUK.Mobile.MyDrive
/template-create
# Expected:
# ✅ Detects as C# (not Java)
# ✅ Excludes obj/, bin/
# ✅ Correct file counts

# Test 2: Non-interactive workflow (TASK-9039)
cd ~/Projects/test-react-project
/template-create
# Expected:
# ✅ No blocking prompts
# ✅ Smart defaults applied
# ✅ Template generated successfully

# Test 3: Optional Q&A (TASK-9038)
/template-qa
# Expected:
# ✅ Q&A session runs
# ✅ Config saved to .template-create-config.json

/template-create --config .template-create-config.json
# Expected:
# ✅ Uses config values
# ✅ Template generated with custom settings

# Test 4: End-to-end workflow
cd ~/Projects/new-project
/template-create
# Expected:
# ✅ Auto-detects language
# ✅ Excludes build artifacts
# ✅ Generates 7-9 agents (TMPL-4E89 already done)
# ✅ Creates template successfully
# ✅ No manual intervention needed
```

---

## Timeline Comparison

### Sequential Execution (Option 2)
```
Hour 0:00  → Start TASK-9037
Hour 2:30  → TASK-9037 done, start TASK-9038
Hour 6:30  → TASK-9038 done, start TASK-9039
Hour 11:30 → TASK-9039 done
            TOTAL: 11.5 hours
```

### Parallel Execution (Option 1 - Recommended)
```
Hour 0:00  → Start TASK-9037 and TASK-9038 in parallel
Hour 2:30  → TASK-9037 done (merge to main)
Hour 4:00  → TASK-9038 done (merge to main)
Hour 4:00  → Start TASK-9039 (depends on 9038)
Hour 8:00  → TASK-9039 done (merge to main)
            TOTAL: 8 hours (30% faster!)
```

**Time Savings**: 3.5 hours (30% reduction)

---

## Risk Management

### Risk 1: Merge Conflicts

**Likelihood**: LOW
**Impact**: LOW (5-10 minutes to resolve)

**Mitigation**:
- TASK-9037 and TASK-9038 have zero overlapping files
- Pull main frequently during development
- Use conductor's automatic state sync

**Resolution** (if conflicts occur):
```bash
git pull origin main
# Fix conflicts in conflicting files
git add .
git commit -m "Resolve merge conflicts"
```

---

### Risk 2: TASK-9039 Started Before TASK-9038 Merged

**Likelihood**: MEDIUM (user error)
**Impact**: HIGH (wasted 4-5 hours, needs rework)

**Mitigation**:
- ⚠️ **DO NOT START TASK-9039 until TASK-9038 merged to main**
- Check for qa_session.py existence before starting TASK-9039
- Use dependency checklist

**Prevention**:
```bash
# Before starting TASK-9039, verify:
ls installer/global/lib/template_creation/qa_session.py
# Should exist ✅

ls installer/global/commands/template-qa.md
# Should exist ✅

# If files don't exist, WAIT for TASK-9038 merge
```

---

### Risk 3: Conductor Worktree State Sync Issues

**Likelihood**: LOW (conductor handles this automatically)
**Impact**: LOW (state committed to git)

**Mitigation**:
- Taskwright uses symlinks for commands/agents (shared across worktrees)
- State files in `docs/state/` committed to git (synced automatically)
- Conductor docs confirm full state preservation

**Verification**:
```bash
# Check state sync
ls -la ~/.claude/commands
# Should be symlink to ~/.agentecflow/commands ✅

ls docs/state/TASK-9037/
# Should exist in all worktrees after commit ✅
```

---

## Conductor-Specific Notes

### Worktree Management

**Create worktrees**:
```bash
conductor create <task-name>
# Creates: ~/Projects/appmilla_github/taskwright-<task-name>/
```

**List worktrees**:
```bash
conductor list
# Shows all active worktrees with current branches
```

**Switch between worktrees**:
```bash
conductor switch <task-name>
# Or use cd directly
cd ~/Projects/appmilla_github/taskwright-<task-name>/
```

**Delete worktrees** (after merge):
```bash
conductor delete task-9037
conductor delete task-9038
conductor delete task-9039
```

### State Preservation

**Automatic State Sync**:
- ✅ Commands: Symlinked to `~/.agentecflow/commands/` (shared)
- ✅ Agents: Symlinked to `~/.agentecflow/agents/` (shared)
- ✅ Task files: In `tasks/` directory (git tracked)
- ✅ State files: In `docs/state/` (git tracked)
- ✅ Implementation plans: In `.claude/task-plans/` (git tracked)

**Manual Sync** (if needed):
```bash
# In each worktree after making changes
git add .
git commit -m "Save state"
git push origin <branch-name>

# In main worktree
git pull origin main
# State synced ✅
```

---

## Checklist

### Pre-Execution Checklist

- [ ] Conductor installed and configured
- [ ] Main branch up to date (`git pull origin main`)
- [ ] No uncommitted changes in main worktree
- [ ] All three tasks (9037, 9038, 9039) in backlog state
- [ ] DeCUK.Mobile.MyDrive project available for testing
- [ ] Test projects available (React, Python, etc.)

### During Execution Checklist

**TASK-9037**:
- [ ] Worktree created: `taskwright-task-9037`
- [ ] `/task-work TASK-9037` executed
- [ ] Tests passing (100%)
- [ ] Coverage ≥ 80%
- [ ] Language detection verified on real project
- [ ] Merged to main

**TASK-9038**:
- [ ] Worktree created: `taskwright-task-9038`
- [ ] `/task-work TASK-9038` executed
- [ ] Tests passing (100%)
- [ ] `/template-qa` command works
- [ ] Config file saved correctly
- [ ] Merged to main

**TASK-9039**:
- [ ] ⚠️ **VERIFIED TASK-9038 MERGED** (critical!)
- [ ] Worktree created: `taskwright-task-9039`
- [ ] `/task-work TASK-9039` executed
- [ ] Tests passing (100%)
- [ ] Non-interactive workflow verified
- [ ] Smart defaults working
- [ ] Merged to main

### Post-Execution Checklist

- [ ] All worktrees deleted
- [ ] Main branch has all changes
- [ ] Integration tests pass
- [ ] Language detection works (TASK-9037)
- [ ] Non-interactive workflow works (TASK-9039)
- [ ] Optional Q&A works (TASK-9038)
- [ ] Template-create fully functional
- [ ] Documentation updated

---

## Troubleshooting

### Issue: /task-work Not Found

**Problem**: Command not recognized in worktree

**Solution**:
```bash
# Verify symlinks exist
ls -la ~/.claude/commands/task-work.md
# Should be symlink to ~/.agentecflow/commands/task-work.md

# If not, re-run installer
cd ~/Projects/appmilla_github/taskwright
./installer/scripts/install.sh
```

---

### Issue: Conductor Create Fails

**Problem**: `conductor create` command not found

**Solution**:
```bash
# Install Conductor from conductor.build
# Or fall back to Option 2 (Sequential execution)

# Alternative: Manual worktree creation
git worktree add ../taskwright-task-9037 -b fix/task-9037-build-artifacts
cd ../taskwright-task-9037
/task-work TASK-9037
```

---

### Issue: Tests Failing in Worktree

**Problem**: Tests fail due to import path issues

**Solution**:
```bash
# Verify PYTHONPATH
echo $PYTHONPATH
# Should include taskwright root

# If not set, add to shell profile
export PYTHONPATH="/Users/richardwoollcott/Projects/appmilla_github/taskwright:$PYTHONPATH"
export PYTHONPATH="/Users/richardwoollcott/Projects/appmilla_github/taskwright/installer/global:$PYTHONPATH"

# Re-run tests
pytest tests/unit/test_exclusions.py -v
```

---

### Issue: Merge Conflicts

**Problem**: Conflicts when merging branches

**Solution**:
```bash
# Pull main first
git pull origin main

# Resolve conflicts manually
# Edit conflicting files

# Stage resolved files
git add <conflicted-files>

# Complete merge
git commit -m "Resolve merge conflicts"
```

---

### Issue: TASK-9039 Started Too Early

**Problem**: TASK-9039 started before TASK-9038 merged, missing qa_session.py

**Solution**:
```bash
# Stop TASK-9039 work immediately
# Wait for TASK-9038 to merge to main

# Pull latest main
git checkout main
git pull origin main

# Verify qa_session.py exists
ls installer/global/lib/template_creation/qa_session.py

# Restart TASK-9039
/task-work TASK-9039
```

---

## Summary

**Recommended Approach**: Parallel execution with Conductor (Option 1)

**Timeline**:
1. Setup (5 min)
2. TASK-9037 + TASK-9038 parallel (2-4 hours)
3. Merge TASK-9037 (10 min)
4. Merge TASK-9038 (10 min)
5. TASK-9039 sequential (4-5 hours)
6. Merge TASK-9039 (10 min)
7. Integration testing (30 min)

**Total Time**: 8 hours (vs 11.5 hours sequential)
**Time Savings**: 30% faster

**Key Success Factors**:
- ✅ Use /task-work for all tasks (automatic quality gates)
- ✅ Run TASK-9037 and TASK-9038 in parallel (independent)
- ⚠️ **DO NOT start TASK-9039 until TASK-9038 merged**
- ✅ Test integration at the end
- ✅ Use Conductor for worktree management

---

**Next Step**: Execute Phase 1 (Setup Conductor worktrees)

```bash
# Terminal 1: Main coordination
cd ~/Projects/appmilla_github/taskwright
git checkout main
git pull origin main

# Terminal 2: TASK-9037
conductor create task-9037
cd ~/Projects/appmilla_github/taskwright-task-9037
/task-work TASK-9037

# Terminal 3: TASK-9038
conductor create task-9038
cd ~/Projects/appmilla_github/taskwright-task-9038
/task-work TASK-9038
```

**Ready to begin?** Start Phase 1 setup now.
