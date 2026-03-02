# Review Report: TASK-REV-7530

## Executive Summary

FEAT-CF57 run_2 failed with `Invalid task_type value: enhancement` on TASK-INST-012 despite all 9 FEAT-CD4C (ABFIX) fixes being completed on main. The root cause is **twofold**:

1. **Worktree staleness**: The `autobuild/FEAT-CF57` branch diverged from main at commit `ad955f0e` — **before any ABFIX commits landed**. The resume path does not rebase or merge main, so the worktree ran with stale code.
2. **Dual alias table**: Even on main, `coach_validator.py` maintains its own `TASK_TYPE_ALIASES` dict that **does not include `enhancement`**, while `task_types.py` does. TASK-ABFIX-001 only added `enhancement` to `task_types.py:257` — it missed the duplicate alias table in the coach_validator.

**Bottom line**: Even a fresh worktree from current main would still fail on `task_type: enhancement` in the Coach validation path, because the coach_validator's local alias table is out of sync.

## Review Details

- **Mode**: Diagnostic Review
- **Depth**: Standard
- **Task**: TASK-REV-7530
- **Related Features**: FEAT-CF57 (under test), FEAT-CD4C (fix feature)

---

## Finding 1: Worktree Staleness (Confirmed)

### Evidence

| Item | Value |
|------|-------|
| Worktree branch | `autobuild/FEAT-CF57` |
| Merge base with main | `ad955f0e` ("split into additional waves") |
| ABFIX commits on main after divergence | 15 commits (`1d1e0568` through `642b1dec`) |
| `enhancement` in worktree `task_types.py` | **Not present** (line 35 mentions "enhancements" in docstring only) |
| `enhancement` in worktree `coach_validator.py` ALIASES | **Not present** |

The worktree was created from main at `ad955f0e` (pre-ABFIX), and FEAT-CF57 run_1 completed 6 tasks. When run_2 used `[R]esume`, the feature_orchestrator reused the existing worktree at `.guardkit/worktrees/FEAT-CF57` without any rebase or merge from main.

### Resume Path Analysis

Searching `feature_orchestrator.py` for `rebase`, `merge.*main`, `git.*pull`, `git.*fetch` returns **zero matches**. The resume path:

1. Detects incomplete state via `FeatureLoader.is_incomplete()`
2. Prompts user `[R]esume / [F]resh`
3. If resume: reuses existing worktree path as-is
4. Skips completed tasks, continues from current wave

**There is no mechanism to incorporate main branch changes into a resumed worktree.**

### Impact

Any fix that lands on main between feature runs will not be available to resumed worktrees. This affects all features, not just FEAT-CF57.

---

## Finding 2: Dual Alias Table Desynchronization (Critical)

### Evidence

**`guardkit/models/task_types.py` (main)** — line 253-258:
```python
TASK_TYPE_ALIASES: Dict[str, TaskType] = {
    "implementation": TaskType.FEATURE,
    "bug-fix": TaskType.FEATURE,
    "bug_fix": TaskType.FEATURE,
    "benchmark": TaskType.TESTING,
    "research": TaskType.DOCUMENTATION,
    "enhancement": TaskType.FEATURE,  # ✅ Added by TASK-ABFIX-001
}
```

**`guardkit/orchestrator/quality_gates/coach_validator.py` (main)** — line 69-75:
```python
TASK_TYPE_ALIASES: Dict[str, TaskType] = {
    "implementation": TaskType.FEATURE,
    "bug-fix": TaskType.FEATURE,
    "bug_fix": TaskType.FEATURE,
    "benchmark": TaskType.TESTING,
    "research": TaskType.DOCUMENTATION,
    # ❌ "enhancement" is MISSING
}
```

### Root Cause

TASK-ABFIX-001 added `enhancement` to `task_types.py` but **did not update the coach_validator's local copy** of the alias table. The coach_validator imports `TaskType` and `get_profile` from `task_types.py` (line 53) but defines its own `TASK_TYPE_ALIASES` locally (line 69).

### Impact

**Even on current main, a fresh worktree running TASK-INST-012 would fail identically** in the Coach validation phase. The Player phase (which uses `task_types.py` directly) would succeed, but Coach validation uses its local alias table → `enhancement` is unrecognised → `CONFIGURATION_ERROR`.

This is the **true blocking bug** — worktree staleness is a contributing factor but not the sole cause.

---

## Finding 3: TASK-INST-012 Uses Non-Canonical task_type

### Evidence

`tasks/backlog/autobuild-instrumentation/TASK-INST-012-enrich-system-seeding.md` line 4:
```yaml
task_type: enhancement
```

All other 13 FEAT-CF57 task files use canonical values: `scaffolding`, `feature`, `integration`, `refactor`, `testing`.

### Assessment

While `enhancement` is a valid alias (in `task_types.py`), it creates a dependency on alias resolution. Best practice is to use canonical enum values (`feature`) in task frontmatter.

---

## Finding 4: Resume Path Has No Freshness Mechanism

### Evidence

- `feature_orchestrator.py` has no `rebase`, `merge`, `pull`, or `fetch` operations
- The `--fresh` flag creates a new worktree from scratch but discards all prior work
- There is no `--refresh` or `--rebase` flag

### Trade-offs of Adding Rebase-on-Resume

| Pro | Con |
|-----|-----|
| Picks up bug fixes from main | May introduce merge conflicts |
| Keeps worktree code current | Could break partially-completed work |
| Prevents stale-code failures | Adds complexity to resume path |

---

## Finding 5: FEAT-CD4C Fix Validation

| ABFIX Task | Fix | On Main? | Working? |
|------------|-----|----------|----------|
| ABFIX-001 | `enhancement` alias in `task_types.py` | ✅ | ⚠️ Partial — not in coach_validator |
| ABFIX-002 | Feature-load task_type validation | ✅ | ✅ (but doesn't catch coach-only aliases) |
| ABFIX-003 | Config error flag and fast-exit | ✅ | ✅ |
| ABFIX-004 | Per-turn timeout budgeting | ✅ | ✅ |
| ABFIX-005 | Coach test isolation | ✅ | ✅ |
| ABFIX-006 | Timeout vs cancelled logging | ✅ | ✅ |
| ABFIX-007 | Feature validate CLI command | ✅ | ✅ |
| ABFIX-008 | Doc level false positives | ✅ | ✅ |
| ABFIX-009 | Integration tests | ✅ | ✅ |

**ABFIX-001 is incomplete**: It added the alias to `task_types.py` but not to the coach_validator's duplicate alias table.

---

## Finding 6: Remaining FEAT-CF57 Risk Assessment

| Task | task_type | Status | Risk |
|------|-----------|--------|------|
| TASK-INST-004 | feature | pending | Low |
| TASK-INST-005a | scaffolding | pending | Low |
| TASK-INST-005b | feature | pending | Low |
| TASK-INST-005c | feature | pending | Low |
| TASK-INST-006 | feature | pending | Low |
| TASK-INST-008 | feature | pending | Low |
| TASK-INST-009 | testing | pending | Low |
| TASK-INST-012 | **enhancement** | failed | **High — blocked by dual alias bug** |

Only TASK-INST-012 uses a non-canonical task_type. All 7 other pending tasks use canonical values and would succeed (assuming fresh worktree with all fixes).

---

## Recommendations

### R1: Fix the Dual Alias Table (Critical — Must Do)

**Option A (Recommended)**: Make `coach_validator.py` import and use the alias table from `task_types.py` instead of maintaining its own copy:

```python
# In coach_validator.py, replace local TASK_TYPE_ALIASES with:
from guardkit.models.task_types import TASK_TYPE_ALIASES
```

**Option B**: Add `enhancement` to `coach_validator.py`'s local table (quick fix, but doesn't prevent future drift).

### R2: Fix TASK-INST-012 Task File (Quick Win)

Change `task_type: enhancement` to `task_type: feature` in `TASK-INST-012-enrich-system-seeding.md`. This is a belt-and-suspenders fix — canonical values should always be preferred in task frontmatter.

### R3: Add Rebase-on-Resume Option (Medium Priority)

Add a `--refresh` flag to `guardkit autobuild feature` that rebases the worktree branch onto current main before resuming. This prevents stale-code failures for any future feature runs.

### R4: Add Feature Planner Guard (Low Priority)

The feature planner that generated FEAT-CF57 tasks should validate task_type values against the canonical `TaskType` enum (not aliases) when creating task files.

---

## Acceptance Criteria Status

- [x] Root cause of worktree staleness confirmed with evidence (merge base `ad955f0e`, 15 missing commits)
- [x] Gap identified: resume path does NOT rebase main
- [x] All 9 ABFIX fixes verified present on main (ABFIX-001 found incomplete — dual alias table)
- [x] Recommendation: fix BOTH the dual alias table AND TASK-INST-012 task_type
- [x] Risk assessment for remaining 8 FEAT-CF57 tasks (7 low risk, 1 high risk)
- [x] Actionable recommendations provided (R1-R4)

---

## Priority Order for Unblocking FEAT-CF57

1. **R1 (Option A)**: Consolidate coach_validator alias table → single source of truth
2. **R2**: Change TASK-INST-012 `task_type: enhancement` → `feature`
3. Delete or recreate the FEAT-CF57 worktree (fresh start from main)
4. Resume FEAT-CF57 with `--fresh` flag

After steps 1-3, a fresh run should succeed for all remaining tasks.
