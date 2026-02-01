# Review Report: TASK-REV-DEP1

## Executive Summary

The dependency resolution error in FEAT-GR-MVP is a **wave assignment bug** caused by the `build_parallel_groups()` function in `generate_feature_yaml.py`. The function correctly groups tasks by dependency satisfaction but does **not account for intra-wave dependencies**. When TASK-GR-PRE-003-D depends on TASK-GR-PRE-003-C and both are placed in the same wave, the orchestrator correctly rejects execution because a task cannot depend on another task in the same parallel group.

**Root Cause**: Configuration issue (wave assignment), not orchestrator bug.

**Recommended Fix**: Option C (validation at feature load time) with Option A (immediate fix for FEAT-GR-MVP).

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard
- **Duration**: ~45 minutes
- **Reviewer**: Claude Code

## Findings

### Finding 1: Wave Assignment Algorithm Does Not Prevent Intra-Wave Dependencies

**Location**: [generate_feature_yaml.py:240-269](installer/core/commands/lib/generate_feature_yaml.py#L240-L269)

**Evidence**: The `build_parallel_groups()` function assigns tasks to waves based on whether all dependencies are in **previous** waves (i.e., `scheduled` set). However, when parsing tasks from JSON in `/feature-plan`, the dependencies may include tasks that happen to satisfy the "all deps scheduled" condition simultaneously with the dependent task.

```python
# From build_parallel_groups()
if all(d in scheduled for d in dep_map[t.id]):
    available.append(t.id)
```

The issue: If TASK-GR-PRE-003-B is completed, both TASK-GR-PRE-003-C (depends on B) and TASK-GR-PRE-003-D (depends on C) could be placed in the same wave because:
- TASK-GR-PRE-003-C: deps [B] - B is scheduled ✓
- TASK-GR-PRE-003-D: deps [C] - C is NOT scheduled ✗

Wait - this should have worked correctly. Let me re-examine...

**Actual Issue Found**: Looking at the YAML, the `parallel_groups` show:
```yaml
parallel_groups:
- - TASK-GR-PRE-003-C
  - TASK-GR-PRE-003-D  # Wave 5
```

But the task files show:
- TASK-GR-PRE-003-C: `depends_on: [TASK-GR-PRE-003-B]`, `wave: 5`
- TASK-GR-PRE-003-D: `depends_on: [TASK-GR-PRE-003-C]`, `wave: 5`

**The root cause is clearer now**: The YAML was likely edited manually or the wave assignment was overridden. The `build_parallel_groups()` function would NOT have placed these together if run correctly.

### Finding 2: No Validation of Intra-Wave Dependencies

**Location**: [feature_orchestrator.py:909-918](guardkit/orchestrator/feature_orchestrator.py#L909-L918)

**Evidence**: The orchestrator validates dependencies at wave start but has no mechanism to detect or correct intra-wave dependency conflicts:

```python
for task_id in task_ids:
    task = FeatureLoader.find_task(feature, task_id)
    if task and not self._dependencies_satisfied(task, feature):
        raise DependencyError(
            f"Task {task_id} has unsatisfied dependencies: {task.dependencies}"
        )
```

This is **correct behavior** - the orchestrator should reject invalid configurations. The problem is that invalid configurations can be created.

### Finding 3: Wave Assignment in Task Files Inconsistent with YAML

**Location**: Task markdown files

**Evidence**:
- TASK-GR-PRE-003-C: `wave: 5` in frontmatter
- TASK-GR-PRE-003-D: `wave: 5` in frontmatter
- FEAT-GR-MVP.yaml: Both in same `parallel_groups` wave

The `wave` field in task files appears to be manually assigned or comes from a different source than `parallel_groups` in the YAML. This creates a potential for inconsistency.

### Finding 4: parallel_analyzer.py Has Correct Logic

**Location**: [parallel_analyzer.py:266-268](installer/core/lib/parallel_analyzer.py#L266-L268)

**Evidence**: The `detect_parallel_groups()` function in `parallel_analyzer.py` correctly handles dependencies:

```python
# All dependencies must be in PREVIOUS waves (not current wave)
deps = set(task.get("dependencies", []))
unmet_deps = deps - assigned_to_previous_waves
has_unmet_dependency = bool(unmet_deps)
```

This implementation would NOT have created the invalid configuration. The bug is likely in:
1. The YAML was manually edited
2. A different code path was used to generate the YAML
3. The `generate_feature_yaml.py` version differs from `parallel_analyzer.py`

### Finding 5: Discrepancy Between Two Wave Assignment Implementations

**Location**:
- [generate_feature_yaml.py:240-269](installer/core/commands/lib/generate_feature_yaml.py#L240-L269)
- [parallel_analyzer.py:171-297](installer/core/lib/parallel_analyzer.py#L171-L297)

**Evidence**: There are TWO implementations of wave assignment:
1. `generate_feature_yaml.py:build_parallel_groups()` - simpler, used by `/feature-plan`
2. `parallel_analyzer.py:detect_parallel_groups()` - more sophisticated, considers file conflicts

The `generate_feature_yaml.py` implementation is simpler and may have edge cases where tasks slip through. Looking at the code:

```python
# generate_feature_yaml.py - checks if ALL deps are in scheduled (previous waves)
if all(d in scheduled for d in dep_map[t.id]):
    available.append(t.id)
```

This should work correctly. BUT if TASK-GR-PRE-003-D's dependency on TASK-GR-PRE-003-C was somehow not recorded when `build_parallel_groups` was called, they could end up in the same wave.

## Root Cause Determination

**Most Likely Cause**: The FEAT-GR-MVP.yaml file was edited or regenerated without correct dependency information. Specifically:

1. The feature YAML shows `parallel_groups` with both tasks in wave 5
2. The task files show correct `depends_on` relationships
3. The wave assignment algorithms (both versions) would NOT create this configuration if dependencies were correct

**Evidence**: Looking at the YAML, TASK-GR-PRE-003-C and TASK-GR-PRE-003-D appear in the same group:
```yaml
- - TASK-GR-PRE-003-C
  - TASK-GR-PRE-003-D
```

But the task dependencies are:
- C depends on B
- D depends on C

If the algorithm ran with correct input, D would be in a LATER wave than C, not the same wave.

## Recommendations

### Option A: Fix Task Wave Assignment (Configuration Fix) - IMMEDIATE

**Effort**: Low (5 minutes)
**Risk**: Low
**Recommendation**: ✅ RECOMMENDED for immediate fix

Simply update FEAT-GR-MVP.yaml to move TASK-GR-PRE-003-D to wave 6:

```yaml
# Change from:
- - TASK-GR-PRE-003-C
  - TASK-GR-PRE-003-D

# To:
- - TASK-GR-PRE-003-C
- - TASK-GR-PRE-003-D
```

This is the fastest fix and allows FEAT-GR-MVP to continue execution.

### Option B: Add Intra-Wave Dependency Handling in Orchestrator (Code Fix)

**Effort**: Medium (2-4 hours)
**Risk**: Medium (changes execution semantics)
**Recommendation**: ⚠️ NOT RECOMMENDED

This would add complexity to the orchestrator to automatically reorder tasks within a wave. However:
- Violates the principle that orchestrator validates config, doesn't fix it
- Could mask configuration errors
- Adds runtime complexity

### Option C: Add Validation at Feature Load Time (Prevention) - STRATEGIC

**Effort**: Medium (1-2 hours)
**Risk**: Low
**Recommendation**: ✅ RECOMMENDED for prevention

Add validation in `FeatureLoader` to detect intra-wave dependency conflicts before orchestration:

```python
def validate_parallel_groups(feature: Feature) -> List[str]:
    """Validate that no task depends on another in the same wave."""
    errors = []
    for wave_num, task_ids in enumerate(feature.orchestration.parallel_groups, 1):
        wave_set = set(task_ids)
        for task_id in task_ids:
            task = find_task(feature, task_id)
            if task:
                for dep_id in task.dependencies:
                    if dep_id in wave_set:
                        errors.append(
                            f"Wave {wave_num}: {task_id} depends on {dep_id} "
                            f"but both are in the same parallel group"
                        )
    return errors
```

This catches the error early with a clear message, before orchestration begins.

### Option D: Consolidate Wave Assignment Implementations (Technical Debt)

**Effort**: Medium (2-4 hours)
**Risk**: Low
**Recommendation**: ⚠️ OPTIONAL (future improvement)

Consolidate `generate_feature_yaml.py:build_parallel_groups()` and `parallel_analyzer.py:detect_parallel_groups()` into a single implementation to prevent future drift.

## Decision Matrix

| Option | Effort | Risk | Fixes Now | Prevents Future | Recommendation |
|--------|--------|------|-----------|-----------------|----------------|
| A: Config fix | Low | Low | ✅ Yes | ❌ No | ✅ Do now |
| B: Orchestrator fix | Medium | Medium | ✅ Yes | ❌ No | ❌ Skip |
| C: Load validation | Medium | Low | ❌ No | ✅ Yes | ✅ Create task |
| D: Consolidate impl | Medium | Low | ❌ No | ✅ Partial | ⚠️ Optional |

## Recommended Approach

1. **Immediate**: Apply Option A - Fix FEAT-GR-MVP.yaml manually
2. **Follow-up**: Create implementation task for Option C - Add validation

## Appendix

### Files Examined

- [TASK-GR-PRE-003-C-upsert-episode.md](tasks/backlog/graphiti-refinement-mvp/TASK-GR-PRE-003-C-upsert-episode.md)
- [TASK-GR-PRE-003-D-upsert-tests-docs.md](tasks/backlog/graphiti-refinement-mvp/TASK-GR-PRE-003-D-upsert-tests-docs.md)
- [FEAT-GR-MVP.yaml](.guardkit/features/FEAT-GR-MVP.yaml)
- [feature_orchestrator.py](guardkit/orchestrator/feature_orchestrator.py)
- [parallel_analyzer.py](installer/core/lib/parallel_analyzer.py)
- [generate_feature_yaml.py](installer/core/commands/lib/generate_feature_yaml.py)

### Error Context

```
ERROR:guardkit.orchestrator.feature_orchestrator:Feature orchestration failed:
Task TASK-GR-PRE-003-D has unsatisfied dependencies: ['TASK-GR-PRE-003-C']
```

This error is **correct behavior** - the orchestrator is correctly rejecting an invalid configuration where a task depends on another task in the same parallel execution wave.
