# Review Report: TASK-REV-3D53

## Branch Changes Relevance Review - Option D Architecture Alignment

**Review Mode**: Architectural + Code Quality
**Review Depth**: Standard
**Task ID**: TASK-REV-3D53
**Date**: 2025-12-30
**Reviewer**: Claude Code (Opus 4.5)

---

## Executive Summary

This review analyzes uncommitted changes on the `autobuild-automation` branch to determine their relevance given the **Option D: Task-Work Delegation** architecture decision from TASK-REV-0414.

**Overall Assessment**: 68/100

**Key Findings**:
1. **`install.sh` changes**: **KEEP** - Python package installation is required for Option D's CLI invocation
2. **`guardkit/planning/` module**: **REMOVE** - Duplicates existing `lib/complexity_*` functionality; Option D delegates to `/task-work` which already uses the existing implementation
3. **Risk Level**: LOW - Removing the planning module has no downstream impact (not yet integrated)

**Recommendation**: Remove `guardkit/planning/` module, keep `install.sh` Python package changes.

---

## 1. Changes Under Review

### 1.1 `installer/scripts/install.sh` Additions (~100 LOC)

| Addition | Purpose | Lines |
|----------|---------|-------|
| `install_python_package()` | Pip-install guardkit package in editable mode | 337-392 |
| Autobuild CLI routing | Find and invoke `guardkit-py autobuild` | 845-879 |
| Help text updates | Document autobuild commands | 800-815 |
| Python package detection | Check multiple locations for guardkit-py | 846-858 |

### 1.2 `guardkit/planning/` Module (New Directory)

| File | Classes/Functions | LOC |
|------|------------------|-----|
| `__init__.py` | Module exports | 34 |
| `complexity.py` | `ComplexityAnalyzer`, `ComplexityFactors` | 251 |
| `dependencies.py` | `DependencyAnalyzer`, `TaskDependency` | 299 |
| `feature_writer.py` | `FeatureWriter`, `FeatureFile`, `TaskSpec` | 339 |
| **Total** | 7 classes | **~923 LOC** |

---

## 2. Analysis: `install.sh` Changes

### 2.1 Relevance to Option D

Option D architecture requires invoking `/task-work` as a subprocess or SDK call. The `guardkit autobuild task TASK-XXX` CLI command provides:

- **Entry point** for AutoBuild execution
- **Worktree management** via Python CLI
- **Player-Coach loop orchestration**

**Question**: Is Python package installation needed for Option D?

**Answer**: **YES**, for CLI-based invocation.

The `guardkit` shell command at lines 845-879 routes `autobuild` subcommands to the Python CLI:

```bash
autobuild)
    # Find guardkit-py CLI - check multiple locations
    if command -v guardkit-py &> /dev/null; then
        GUARDKIT_PY="guardkit-py"
    elif [ -x "/Library/Frameworks/Python.framework/Versions/Current/bin/guardkit-py" ]; then
        GUARDKIT_PY="/Library/Frameworks/Python.framework/.../guardkit-py"
    ...
    exec "$GUARDKIT_PY" autobuild "$@"
```

**Alternative**: Could use Task tool agents directly (slash command only), but this limits:
- Shell/CI usage
- Worktree isolation (requires Python `git` library)
- State persistence across sessions

### 2.2 Decision: KEEP

**Rationale**:
1. Option D delegates to `/task-work`, which runs as a Claude command
2. **But** the orchestration layer (`PreLoopQualityGates`, `CoachValidator`) needs a runtime:
   - **CLI mode**: `guardkit autobuild task TASK-XXX`
   - **Slash command mode**: `/feature-build TASK-XXX` → Task tool agents
3. Python package provides worktree management, state files, and progress tracking
4. Removing would break CLI invocation entirely

**Impact if Kept**: None (already working)
**Impact if Removed**: `guardkit autobuild` becomes unavailable; only slash command works

---

## 3. Analysis: `guardkit/planning/` Module

### 3.1 Comparison with Existing Functionality

The `guardkit/planning/` module implements functionality that **already exists** in `installer/core/commands/lib/`:

| Planning Module | Existing Implementation | Overlap |
|-----------------|------------------------|---------|
| `ComplexityAnalyzer` | `lib/complexity_calculator.py` → `ComplexityCalculator` | **95%** |
| `ComplexityFactors` | `lib/complexity_factors.py` → `FileComplexityFactor`, `PatternFamiliarityFactor`, `RiskLevelFactor` | **90%** |
| `DependencyAnalyzer` | *(None - new functionality)* | **0%** |
| `FeatureWriter` | *(None - new functionality)* | **0%** |

#### 3.1.1 Complexity Analysis Comparison

**`guardkit/planning/complexity.py`**:
```python
class ComplexityFactors:
    files_to_modify: int = 0  # Weight: 1.5
    integration_points: int = 0  # Weight: 2.0
    test_requirements: int = 0  # Weight: 1.0
    risk_factors: List[str] = field(default_factory=list)

    def calculate_score(self) -> int:
        raw = (files * 1.5 + integrations * 2.0 + tests * 1.0 + risks * 1.5)
        return min(10, max(1, int(raw / 2.5)))
```

**`lib/complexity_calculator.py`** (existing):
```python
class ComplexityCalculator:
    def calculate(self, context: EvaluationContext) -> ComplexityScore:
        factor_scores = self._evaluate_factors(context)  # FileComplexityFactor, PatternFamiliarityFactor, RiskLevelFactor
        total_score = self._aggregate_scores(factor_scores)
        forced_triggers = self._detect_forced_triggers(context)
        review_mode = self._determine_review_mode(total_score, forced_triggers)
        return ComplexityScore(total_score, factor_scores, forced_triggers, review_mode, ...)
```

**Key Difference**: The existing implementation has:
- ✅ Force-review trigger detection (security keywords, schema changes, hotfix)
- ✅ Review mode routing (AUTO_PROCEED, QUICK_OPTIONAL, FULL_REQUIRED)
- ✅ Fail-safe defaults (score=10 on error)
- ✅ Type-safe models (`ComplexityScore`, `FactorScore`, `ReviewDecision`)

The new `guardkit/planning/complexity.py` is a **simpler reimplementation** that lacks these features.

### 3.2 Relevance to Option D

**Option D Architecture**:
```
/feature-build TASK-XXX
    ├── PRE-LOOP: /task-work --design-only
    │   └── Phases 1.6, 2, 2.5A, 2.5B, 2.7, 2.8  ← Uses lib/complexity_*
    ├── ADVERSARIAL LOOP
    │   └── PLAYER: /task-work --implement-only
    └── FINALIZE
```

**Critical Insight**: Option D **delegates** complexity evaluation to `/task-work --design-only`, which already:
1. Invokes Phase 2.7 (Complexity Evaluation)
2. Uses `lib/complexity_calculator.py` → `ComplexityCalculator`
3. Determines `max_turns` from complexity score
4. Routes to appropriate review mode

**Therefore**: The `guardkit/planning/complexity.py` module is **never called** in Option D. It duplicates functionality that `/task-work` already provides.

### 3.3 Dependency Analysis and Feature Writer

`DependencyAnalyzer` and `FeatureWriter` are **not duplicates** - they provide new functionality:
- **DependencyAnalyzer**: Task dependency detection and parallel group building
- **FeatureWriter**: YAML feature file output for `.guardkit/features/FEAT-XXX.yaml`

**However**, with Option D's task-work delegation:
- Dependencies are handled by task ordering in the feature subfolder
- Feature files are **markdown** in `tasks/backlog/{feature}/`, not YAML in `.guardkit/features/`
- Parallel groups are determined by the human via wave assignments in `IMPLEMENTATION-GUIDE.md`

**Conclusion**: These classes were designed for a **different architecture** (original AutoBuild approach) that has been superseded by Option D.

### 3.4 Decision: REMOVE

**Rationale**:
1. `ComplexityAnalyzer` duplicates `lib/complexity_calculator.py` (90-95% overlap)
2. `DependencyAnalyzer` is not used - Option D uses subfolder wave organization
3. `FeatureWriter` produces YAML, but Option D uses markdown task files
4. No downstream code references `guardkit.planning` module yet
5. Keeping creates maintenance burden: two complexity implementations to maintain

**Impact if Removed**: None - module is not integrated anywhere
**Impact if Kept**:
- Technical debt (duplicate complexity logic)
- Confusion about which to use
- Divergent behavior risk (bugs fixed in one, not the other)

---

## 4. Decision Matrix

| Component | Decision | Rationale | Effort |
|-----------|----------|-----------|--------|
| `install.sh` → `install_python_package()` | **KEEP** | Required for CLI invocation | 0 |
| `install.sh` → autobuild routing | **KEEP** | Routes to Python CLI | 0 |
| `guardkit/planning/__init__.py` | **REMOVE** | Module obsolete for Option D | <5 min |
| `guardkit/planning/complexity.py` | **REMOVE** | Duplicates lib/complexity_* | <5 min |
| `guardkit/planning/dependencies.py` | **REMOVE** | Not used in Option D | <5 min |
| `guardkit/planning/feature_writer.py` | **REMOVE** | Option D uses markdown, not YAML | <5 min |

---

## 5. TASK-REV-0414 Reference Clarification

The TASK-REV-0414 review report mentions:

> **Phase 2.7: Complexity Evaluation**
> - IMPORT: `from guardkit.planning.complexity import ComplexityAnalyzer`
> - USE: `analyzer.analyze_task(task_dict)` NOT new `evaluate_complexity()` function

This recommendation was made **before** Option D was selected. With Option D:
- Complexity evaluation is handled **inside** `/task-work --design-only` (Phase 2.7)
- The orchestrator doesn't call `ComplexityAnalyzer` directly
- The orchestrator receives the complexity score **as output** from task-work

**Corrected Architecture** (Option D):
```python
# guardkit/orchestrator/quality_gates/pre_loop.py
class PreLoopQualityGates:
    def execute(self, task_id: str) -> PreLoopResult:
        # Delegate to task-work - complexity is calculated internally
        result = run_task_work(task_id, flags=["--design-only"])

        # Extract complexity from task-work output
        complexity = result.get("complexity_score")
        max_turns = self._calculate_max_turns(complexity)

        return PreLoopResult(
            plan=result.get("plan"),
            complexity=complexity,
            max_turns=max_turns,
        )
```

No direct import of `ComplexityAnalyzer` needed.

---

## 6. Safe Removal Process

### 6.1 Pre-Removal Validation

```bash
# 1. Check for imports of guardkit.planning
grep -r "from guardkit.planning" --include="*.py" .
grep -r "import guardkit.planning" --include="*.py" .

# Expected: Only guardkit/planning/__init__.py (self-reference)

# 2. Check for YAML feature file usage
find . -path ".guardkit/features/*.yaml" -type f

# Expected: No files (directory doesn't exist)

# 3. Check pyproject.toml for module reference
grep "guardkit.planning" pyproject.toml

# Expected: No reference (not a package entry point)
```

### 6.2 Removal Commands

```bash
# Remove the planning module
rm -rf guardkit/planning/

# Remove associated tests (if any)
rm -f tests/unit/test_planning_*.py

# Update pyproject.toml if needed (likely no changes required)
```

### 6.3 Post-Removal Validation

```bash
# 1. Verify Python package still installs
pip install -e . --break-system-packages

# 2. Verify CLI still works
guardkit --help
guardkit doctor

# 3. Run existing tests
pytest tests/unit/ -v
```

---

## 7. Recommendations Summary

### 7.1 Immediate Actions

1. **KEEP** `install.sh` changes (Python package installation, autobuild routing)
2. **REMOVE** `guardkit/planning/` directory entirely
3. **REMOVE** any unit tests for the planning module (`tests/unit/test_planning_*.py`)
4. **UPDATE** TASK-QG-P1-PRE to NOT import `guardkit.planning.complexity`

### 7.2 Task Updates Required

| Task | Change |
|------|--------|
| TASK-QG-P1-PRE | Remove reference to `guardkit.planning.complexity` import |
| TASK-REV-0414 | Update Appendix B to remove `guardkit.planning` imports |

### 7.3 Git Operations

```bash
# Option 1: Discard planning module changes only
git checkout HEAD -- guardkit/planning/

# Option 2: Stage everything except planning module
git add .
git reset HEAD -- guardkit/planning/

# Option 3: If planning module tests exist
git checkout HEAD -- tests/unit/test_planning_*.py
```

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing functionality | Very Low | None | Planning module not integrated |
| Loss of useful code | Low | Low | DependencyAnalyzer could be reimplemented if needed |
| Confusion about architecture | Medium | Medium | This review clarifies the decision |
| CI/CD failures | Very Low | Low | Run tests after removal |

**Overall Risk Level**: LOW

---

## 9. Decision Options

### Option A: Accept Recommendations (Recommended)

**Action**: Remove `guardkit/planning/`, keep `install.sh` changes

**Effort**: <30 minutes
**Risk**: Low
**Benefit**: Clean codebase, single source of truth for complexity

### Option B: Keep Everything

**Action**: Keep all uncommitted changes as-is

**Effort**: 0
**Risk**: Medium (technical debt, duplicate implementations)
**Benefit**: No work required now

### Option C: Remove Everything

**Action**: Discard all uncommitted changes

**Effort**: <5 minutes
**Risk**: High (breaks CLI invocation)
**Benefit**: Clean slate

---

## Appendix A: Files to Remove

```
guardkit/planning/
├── __init__.py          (34 LOC)
├── complexity.py        (251 LOC)
├── dependencies.py      (299 LOC)
└── feature_writer.py    (339 LOC)

tests/unit/
├── test_planning_complexity.py    (if exists)
├── test_planning_dependencies.py  (if exists)
└── test_planning_feature_writer.py (if exists)
```

---

## Appendix B: Files to Keep

```
installer/scripts/install.sh
├── install_python_package()        (lines 337-392)
├── autobuild CLI routing           (lines 845-879)
└── Help text updates               (lines 800-815)
```
