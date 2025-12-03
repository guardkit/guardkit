# Test Plan Summary - Which One to Use?

**Created**: 2025-11-29
**Decision**: Choose based on your needs

---

## ⚠️ Bugs Discovered During Testing

### Bug 1: BDD Mode Validation (HIGH Priority)

**Step 3.1 of FOCUSED plan identified a critical bug**:

**Issue**: BDD mode (`/task-work TASK-XXX --mode=bdd`) doesn't validate RequireKit before execution. It shows a warning but continues with standard workflow instead of stopping.

**Severity**: HIGH - Blocks BDD mode functionality entirely

**Details**: See [BUG-BDD-MODE-VALIDATION.md](./BUG-BDD-MODE-VALIDATION.md)

**Status**: Bug documented, fix required before public launch

### Bug 2: Task-Create Import Error (HIGH Priority) ✅ FIXED

**Fresh VM installation identified regression**:

**Issue**: `/task-create` failed with "No module named 'id_generator'" because curl installation deleted repository files after install.

**Severity**: HIGH - Task creation completely broken on fresh installations

**Details**: See [BUG-TASK-CREATE-ID-GENERATOR-IMPORT.md](./BUG-TASK-CREATE-ID-GENERATOR-IMPORT.md)

**Status**: ✅ FIXED - Curl install now clones repository permanently

**Changes**:
1. Curl install now clones repo to `~/Projects/guardkit` (permanent)
2. Marker file includes `repo_path` field
3. task-create.md includes repository path resolution
4. Works with git clone OR tarball download

**Architecture**: See [CURL-INSTALL-ARCHITECTURE.md](./CURL-INSTALL-ARCHITECTURE.md)

---

## Quick Decision Guide

### Use FOCUSED Plan (Recommended)

**File**: [PARALLELS-VM-TEST-PLAN-FOCUSED.md](PARALLELS-VM-TEST-PLAN-FOCUSED.md)
**Quick Ref**: [PARALLELS-VM-TEST-QUICK-REFERENCE-FOCUSED.md](PARALLELS-VM-TEST-QUICK-REFERENCE-FOCUSED.md)

**Duration**: 1.5-2 hours
**Tests**: Recent changes only

✅ **Use when**:
- You want to validate recent changes before launch
- Hash IDs are working fine (no need to test)
- Quality gates stable (not changed recently)
- Want efficient testing (best ROI)

**What it tests**:
1. BDD mode restoration (TASK-BDD-001 to BDD-005)
2. Template init greenfield Q&A
3. Subagent discovery (if recently changed)
4. Conductor integration (if recently changed)

**What it skips**:
- Hash-based task IDs (stable, documented)
- Quality gates Phase 2.5, 4.5 (not changed)
- Basic task workflow (core functionality)
- KartLog demo (optional, separate)

---

### Use FULL Plan

**File**: [PARALLELS-VM-TEST-PLAN.md](PARALLELS-VM-TEST-PLAN.md)
**Quick Ref**: [PARALLELS-VM-TEST-QUICK-REFERENCE.md](PARALLELS-VM-TEST-QUICK-REFERENCE.md)

**Duration**: 2.5-3 hours
**Tests**: Everything, comprehensive

✅ **Use when**:
- First time testing on clean VM
- Want comprehensive validation
- Have time for thorough testing
- Want to document baseline state

**What it tests**:
1. All installation steps
2. Template init with full Q&A
3. Hash-based task IDs (all formats)
4. Complete task workflow
5. Quality gates (Phase 2.5, 4.5)
6. BDD integration (full workflow)
7. Subagent discovery
8. Conductor integration
9. KartLog demo (optional)

---

## My Recommendation

### Use FOCUSED Plan ⭐

**Why**:
1. **Efficient**: Tests only what changed (1.5 hours vs 3 hours)
2. **Relevant**: Hash IDs working fine, no need to test
3. **Recent changes**: BDD mode is the big change to validate
4. **Time-sensitive**: Going public next week

**After focused testing**:
- If issues found → Fix → Re-test
- If all passes → Proceed to shared agents Phase 0
- Full test can be done post-launch if needed

---

## Test Coverage Comparison

| Area | Focused | Full | Notes |
|------|---------|------|-------|
| **Installation** | ✅ | ✅ | Both test clean install |
| **Template Init Q&A** | ✅ | ✅ | Both test greenfield workflow |
| **Hash-based IDs** | ❌ | ✅ | **Stable - skip in focused** |
| **BDD Mode** | ✅ | ✅ | **Critical - test in both** |
| **Subagent Discovery** | ✅ | ✅ | Both validate routing |
| **Quality Gates** | ❌ | ✅ | **Not changed - skip in focused** |
| **Task Workflow** | ❌ | ✅ | **Core stable - skip in focused** |
| **Conductor** | ✅ | ✅ | Both test state management |
| **KartLog Demo** | ❌ | ✅ | Optional in full, skip in focused |

---

## Files Overview

### Focused Testing Files

1. **[PARALLELS-VM-TEST-PLAN-FOCUSED.md](PARALLELS-VM-TEST-PLAN-FOCUSED.md)**
   - Detailed instructions (recent changes only)
   - 1.5-2 hours duration
   - Streamlined workflow

2. **[PARALLELS-VM-TEST-QUICK-REFERENCE-FOCUSED.md](PARALLELS-VM-TEST-QUICK-REFERENCE-FOCUSED.md)**
   - Quick reference card (print this!)
   - Command snippets
   - Checklists

### Full Testing Files

3. **[PARALLELS-VM-TEST-PLAN.md](PARALLELS-VM-TEST-PLAN.md)**
   - Comprehensive instructions
   - 2.5-3 hours duration
   - All features tested

4. **[PARALLELS-VM-TEST-QUICK-REFERENCE.md](PARALLELS-VM-TEST-QUICK-REFERENCE.md)**
   - Full quick reference
   - All commands
   - Complete checklists

### Supporting Files

5. **[PARALLELS-VM-TEST-RESULTS-TEMPLATE.md](PARALLELS-VM-TEST-RESULTS-TEMPLATE.md)**
   - Results documentation template
   - Use with either plan
   - Fill-in-the-blank format

6. **[TESTING-STRATEGY-PRE-PUBLIC-LAUNCH.md](TESTING-STRATEGY-PRE-PUBLIC-LAUNCH.md)**
   - Overall testing strategy
   - Context and rationale
   - Decision framework

---

## Quick Start (Recommended Path)

```bash
# 1. Create VM and snapshot
# Name: "Pre-GuardKit-Install"

# 2. Print quick reference
open PARALLELS-VM-TEST-QUICK-REFERENCE-FOCUSED.md
# Print or keep on second monitor

# 3. Follow detailed plan
open PARALLELS-VM-TEST-PLAN-FOCUSED.md

# 4. Document results
cp PARALLELS-VM-TEST-RESULTS-TEMPLATE.md TEST-RESULTS-FOCUSED.md
# Fill in as you test
```

---

## What to Do After Testing

### If Focused Test Passes ✅

1. **Document**: Complete results template
2. **Proceed**: Start shared agents Phase 0 (TASK-SHA-000)
3. **Demo prep**: Use validated workflow for content
4. **Launch**: Confident for next week

### If Issues Found ⚠️

1. **Categorize**: Critical vs High vs Medium
2. **Fix**: Address critical issues only
3. **Re-test**: Focused re-test of fixed areas
4. **Decide**: Launch or postpone

### If Need More Coverage

1. **Run full test**: Use comprehensive plan
2. **Document**: More detailed results
3. **Baseline**: Full system state documented

---

## Timeline to Launch

**Recommended Path**:

```
Today (Friday):
  └─ Focused testing (1.5-2 hours)
  └─ Document results (30 min)
  └─ Fix critical issues if found (variable)

Monday-Next Week:
  └─ Shared agents Phase 0-5 (7-11 days)
  └─ Post-implementation test (1-2 hours)
  └─ Demo content creation

Next Week (End):
  └─ GO PUBLIC 🚀
```

---

## Success Criteria

### Focused Test Success

✅ **Must Pass**:
- BDD mode works with RequireKit
- BDD mode errors clearly without RequireKit
- Template init Q&A functions
- Installation completes cleanly

✅ **Should Pass**:
- Subagent discovery correct
- Scenarios load from RequireKit
- Step definitions generated
- Conductor state synced

### Launch Readiness

After focused test passes:
- ✅ Recent changes validated
- ✅ Baseline documented
- ✅ Critical path working
- ✅ Ready for shared agents work
- ✅ Confident for public launch

---

## Questions?

**Which test plan?**
→ Use FOCUSED unless you need comprehensive baseline

**How long will it take?**
→ FOCUSED: 1.5-2 hours | FULL: 2.5-3 hours

**What if I find issues?**
→ Categorize, fix critical, re-test focused areas

**Can I skip testing?**
→ Not recommended - 1.5 hours validates last 2 weeks of work

**Should I test hash IDs?**
→ No - stable, documented, working fine

---

**My strong recommendation: Use FOCUSED plan today! 🎯**
