# Pre-Launch Testing Plans

**Date**: 2025-11-29
**Purpose**: Validate recent changes before public launch next week
**Location**: `docs/testing/pre-launch-2025-11-29/`

---

## Quick Start

**Read this first**: [TEST-PLAN-SUMMARY.md](./TEST-PLAN-SUMMARY.md) ⭐

**Recommended**: Use FOCUSED plan (1.5-2 hours)
1. Read: [PARALLELS-VM-TEST-PLAN-FOCUSED.md](./PARALLELS-VM-TEST-PLAN-FOCUSED.md)
2. Print: [PARALLELS-VM-TEST-QUICK-REFERENCE-FOCUSED.md](./PARALLELS-VM-TEST-QUICK-REFERENCE-FOCUSED.md)
3. Execute tests on Parallels VM
4. Document: Copy [PARALLELS-VM-TEST-RESULTS-TEMPLATE.md](./PARALLELS-VM-TEST-RESULTS-TEMPLATE.md)

---

## Files in This Folder

1. **[TEST-PLAN-SUMMARY.md](./TEST-PLAN-SUMMARY.md)** ⭐ START HERE
   - Decision guide: Which test plan to use?
   - Focused vs Full comparison

2. **[TESTING-STRATEGY-PRE-PUBLIC-LAUNCH.md](./TESTING-STRATEGY-PRE-PUBLIC-LAUNCH.md)**
   - Overall testing strategy and context
   - Timeline to launch

### FOCUSED Testing (Recommended - 1.5-2 hours)

3. **[PARALLELS-VM-TEST-PLAN-FOCUSED.md](./PARALLELS-VM-TEST-PLAN-FOCUSED.md)**
   - Detailed test plan (recent changes only)
   - Tests: BDD mode, template Q&A, subagent discovery

4. **[PARALLELS-VM-TEST-QUICK-REFERENCE-FOCUSED.md](./PARALLELS-VM-TEST-QUICK-REFERENCE-FOCUSED.md)**
   - Quick reference card (print this!)
   - Command snippets and checklists

### FULL Testing (Comprehensive - 2.5-3 hours)

5. **[PARALLELS-VM-TEST-PLAN.md](./PARALLELS-VM-TEST-PLAN.md)**
   - Comprehensive test plan
   - Tests everything including stable features

6. **[PARALLELS-VM-TEST-QUICK-REFERENCE.md](./PARALLELS-VM-TEST-QUICK-REFERENCE.md)**
   - Full quick reference

### Results

7. **[PARALLELS-VM-TEST-RESULTS-TEMPLATE.md](./PARALLELS-VM-TEST-RESULTS-TEMPLATE.md)**
   - Results template (fill-in-the-blank)
   - Copy and rename: `test-results-YYYYMMDD.md`

---

## What Gets Tested

### FOCUSED Plan (Recent Changes Only)

✅ **BDD Mode** (40 min) - Error handling, full workflow, scenarios
✅ **Template Init Q&A** (20 min) - Interactive questions, config generation
✅ **Subagent Discovery** (15 min) - Stack detection, agent routing
✅ **Conductor** (15 min) - State management across worktrees

**Skips**: Hash IDs (stable), Quality gates (not changed), Basic workflow

### FULL Plan (Everything)

All of FOCUSED plus:
- Hash-based task IDs (all formats)
- Quality gates (Phase 2.5, 4.5)
- Complete task workflow
- KartLog demo (optional)

---

## Workflow

```bash
# 1. Read summary
open TEST-PLAN-SUMMARY.md

# 2. Execute focused plan
open PARALLELS-VM-TEST-PLAN-FOCUSED.md

# 3. Print reference
open PARALLELS-VM-TEST-QUICK-REFERENCE-FOCUSED.md

# 4. Create VM snapshot: "Pre-TaskWright-Install"

# 5. Run tests (1.5-2 hours)

# 6. Document results
cp PARALLELS-VM-TEST-RESULTS-TEMPLATE.md \
   test-results-$(date +%Y%m%d).md
```

---

## After Testing

**If pass** ✅:
- Document results
- Proceed to shared agents Phase 0
- Ready for launch next week

**If issues** ⚠️:
- Categorize (critical/high/medium/low)
- Fix critical only
- Re-test focused areas

---

**Ready to validate your work! 🚀**
