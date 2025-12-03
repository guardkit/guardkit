# Testing Documentation

**Location**: `docs/testing/`
**Purpose**: Test plans, strategies, and execution guides for GuardKit validation
**Updated**: 2025-11-29

---

## Current Testing Plans

### Pre-Launch Testing (2025-11-29)

**Location**: [pre-launch-2025-11-29/](./pre-launch-2025-11-29/)

**Quick Start**:
1. Read: [pre-launch-2025-11-29/TEST-PLAN-SUMMARY.md](./pre-launch-2025-11-29/TEST-PLAN-SUMMARY.md)
2. Execute: [pre-launch-2025-11-29/PARALLELS-VM-TEST-PLAN-FOCUSED.md](./pre-launch-2025-11-29/PARALLELS-VM-TEST-PLAN-FOCUSED.md)
3. Print: [pre-launch-2025-11-29/PARALLELS-VM-TEST-QUICK-REFERENCE-FOCUSED.md](./pre-launch-2025-11-29/PARALLELS-VM-TEST-QUICK-REFERENCE-FOCUSED.md)

**Purpose**: Validate recent changes (BDD mode, template init Q&A, subagent discovery) before public launch

**Duration**: 1.5-2 hours (focused) or 2.5-3 hours (comprehensive)

---

## Folder Structure

```
docs/testing/
├── README.md (this file)
├── pre-launch-2025-11-29/    # Current test plans
│   ├── TEST-PLAN-SUMMARY.md
│   ├── PARALLELS-VM-TEST-PLAN-FOCUSED.md (recommended)
│   ├── PARALLELS-VM-TEST-QUICK-REFERENCE-FOCUSED.md
│   ├── PARALLELS-VM-TEST-PLAN.md (comprehensive)
│   ├── PARALLELS-VM-TEST-QUICK-REFERENCE.md
│   ├── PARALLELS-VM-TEST-RESULTS-TEMPLATE.md
│   └── TESTING-STRATEGY-PRE-PUBLIC-LAUNCH.md
└── archive/                   # Historical test docs
    ├── template-analysis-task.md
    ├── TASK-062-* (template validation)
    ├── manual-testing-checklist.md
    └── ... (other historical tests)
```

---

## Quick Start Guide

### For Pre-Launch Testing (Today)

```bash
# 1. Navigate to pre-launch folder
cd docs/testing/pre-launch-2025-11-29

# 2. Read decision guide
open TEST-PLAN-SUMMARY.md

# 3. Execute focused test plan (recommended)
open PARALLELS-VM-TEST-PLAN-FOCUSED.md

# 4. Print quick reference
open PARALLELS-VM-TEST-QUICK-REFERENCE-FOCUSED.md
# Keep on second monitor or print

# 5. Execute tests on Parallels VM (1.5-2 hours)

# 6. Document results
cp PARALLELS-VM-TEST-RESULTS-TEMPLATE.md \
   test-results-$(date +%Y%m%d).md
```

---

## What Gets Tested

### Pre-Launch Testing (Focused - 1.5-2 hours)

✅ **BDD Mode Restoration** (40 min)
- Error handling without RequireKit
- Full workflow with RequireKit
- Scenario loading and step generation

✅ **Template Init Q&A** (20 min)
- Interactive questions during `guardkit init`
- Configuration generation

✅ **Subagent Discovery** (15 min)
- Stack detection and routing

✅ **Conductor Integration** (15 min)
- State management across worktrees

**Skips**: Hash IDs (stable), Quality gates (not changed), Basic workflow (core stable)

---

## Archived Tests

**Location**: [archive/](./archive/)

Historical test documentation from early development (Nov 3-9, 2025):
- Template creation testing (`/template-create` command)
- Template validation (TASK-062 series)
- Integration testing approaches
- Manual testing checklists

**Status**: Archived for reference, not actively maintained

---

## Adding New Test Plans

When creating new test plans:

1. **Create dated subfolder**: `YYYY-MM-DD-description/`
2. **Include core files**:
   - Summary/decision guide
   - Detailed test plan
   - Quick reference card
   - Results template
3. **Update this README**: Add to "Current Testing Plans" section
4. **Archive old plans**: Move to `archive/` when superseded

---

## Related Documentation

- **[docs/guides/](../guides/)** - Workflow and feature guides
- **[docs/workflows/](../workflows/)** - Detailed workflow documentation
- **[docs/deep-dives/](../deep-dives/)** - Technical architecture docs

---

**Ready to test? Start with [pre-launch-2025-11-29/](./pre-launch-2025-11-29/)! 🚀**
