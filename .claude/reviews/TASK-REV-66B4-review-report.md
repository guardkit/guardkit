# Review Report: TASK-REV-66B4

## Executive Summary

The `/feature-build` CLI command fails due to **schema mismatches** between what `/feature-plan` generates and what `FeatureLoader` expects. Four distinct errors were identified across schema structure, field requirements, and edge case handling. The recommended fix is to update `/feature-plan` output to match the existing CLI schema expectations.

## Review Details

| Field | Value |
|-------|-------|
| Mode | Code Quality Review |
| Depth | Standard |
| Duration | ~45 minutes |
| Reviewer | Claude Opus 4.5 |
| Task | TASK-REV-66B4 |
| Date | 2026-01-06 |

## Findings

### Finding 1: Missing `file_path` Field in Task Entries (Critical)

**Location**: [feature_loader.py:374](guardkit/orchestrator/feature_loader.py#L374)

**Severity**: Critical - Blocks execution

**Description**: `FeatureLoader._parse_task()` requires `file_path` as a mandatory field but `/feature-plan` generates a separate `task_files` section instead.

**Evidence**:
```python
# feature_loader.py:374
file_path=Path(task_data["file_path"]),  # KeyError if missing
```

**Impact**: Feature build fails immediately with `KeyError: 'file_path'`

---

### Finding 2: `execution_groups` vs `parallel_groups` Schema Mismatch (Critical)

**Location**: [feature_loader.py:324](guardkit/orchestrator/feature_loader.py#L324)

**Severity**: Critical - Blocks validation

**Description**: Two incompatible schema designs exist in the codebase:

| Component | Schema Used | Structure |
|-----------|-------------|-----------|
| FeatureLoader | `parallel_groups` | List of lists `[[TASK-001], [TASK-002, TASK-003]]` |
| feature-plan.md | `execution_groups` | Verbose objects with `wave`, `name`, `strategy`, `tasks` |

**Impact**: Feature validation fails with "Tasks not in orchestration" error

---

### Finding 3: Missing `status` Field Defaults (Minor)

**Location**: [feature_loader.py:377](guardkit/orchestrator/feature_loader.py#L377)

**Severity**: Low - Has fallback default

**Description**: While `_parse_task()` has a default for `status`, the feature YAML wasn't consistently including this field.

**Code**:
```python
status=task_data.get("status", "pending"),  # Default exists
```

---

### Finding 4: Fresh Repository Worktree Creation Fails (Medium)

**Location**: Worktree manager (referenced in error trace)

**Severity**: Medium - Edge case

**Description**: `git worktree add ... main` fails when repository has no commits because `main` branch doesn't exist yet.

**Impact**: New projects can't use `/feature-build` until first commit

---

## Code Quality Metrics

| Metric | Score | Assessment |
|--------|-------|------------|
| Schema Consistency | 3/10 | Two incompatible schemas |
| Error Messages | 6/10 | Thrown but could be clearer |
| Documentation Alignment | 4/10 | feature-plan.md ≠ feature_loader.py |
| Defensive Programming | 5/10 | Missing optional field handling |
| Overall Quality | 4.5/10 | Schema mismatch is blocking issue |

---

## Recommendations

### Recommendation 1: Update `/feature-plan` to Match CLI Schema (Recommended)

**Effort**: 2-3 hours | **Risk**: Low | **Priority**: P0

Update `feature-plan.md` and `generate-feature-yaml` script to produce the schema that `FeatureLoader` expects:

1. Embed `file_path` and `status` directly in each task entry
2. Use `parallel_groups` (list of lists) instead of `execution_groups`
3. Remove redundant `task_files` section

**Files to modify**:
- `installer/core/commands/feature-plan.md` - Schema documentation
- `~/.agentecflow/bin/generate-feature-yaml` - YAML generation script

**Expected schema output**:
```yaml
tasks:
  - id: TASK-001
    name: "Task Name"
    file_path: "tasks/backlog/.../TASK-001.md"
    status: pending
    complexity: 5
    dependencies: []
    implementation_mode: task-work

orchestration:
  parallel_groups:
    - - TASK-001
    - - TASK-002
      - TASK-003
```

---

### Recommendation 2: Add Repository State Check

**Effort**: 30 minutes | **Risk**: Low | **Priority**: P1

Add check for empty repositories before worktree creation:

```python
# In worktree manager
if not self._branch_exists(base_branch):
    if self._is_empty_repo():
        raise WorktreeError(
            f"Cannot create worktree: repository has no commits. "
            f"Create an initial commit first: git commit --allow-empty -m 'Initial commit'"
        )
```

---

### Recommendation 3: Improve Error Messages

**Effort**: 1 hour | **Risk**: Low | **Priority**: P2

Add schema hints to error messages:

```python
except KeyError as e:
    raise FeatureParseError(
        f"Missing required field: {e}\n"
        f"Expected schema: https://guardkit.dev/schemas/feature-yaml\n"
        f"Run: guardkit validate-feature {feature_id}"
    )
```

---

## Decision Matrix

| Option | Effort | Risk | Compatibility | Recommendation |
|--------|--------|------|---------------|----------------|
| Update feature-plan (Option 1) | 2-3h | Low | Breaking for existing | **Recommended** |
| Make FeatureLoader flexible (Option 2) | 4-6h | Medium | Backward compatible | Alternative |
| Hybrid with migration (Option 3) | 3-4h | Low | Migration path | If many existing files |

---

## Implementation Tasks (if [I]mplement chosen)

1. **TASK-FP-001**: Update `feature-plan.md` schema documentation
2. **TASK-FP-002**: Update `generate-feature-yaml` script output format
3. **TASK-FP-003**: Add repository state check to worktree manager
4. **TASK-FP-004**: Improve FeatureLoader error messages with schema hints
5. **TASK-FP-005**: Add unit tests for schema parsing edge cases

---

## Appendix

### Schema Comparison

**Current `/feature-plan` output (incorrect)**:
```yaml
tasks:
  - id: TASK-001
    name: "Task Name"
    wave: 1
    dependencies: []

task_files:
  - path: "tasks/backlog/.../TASK-001.md"

execution_groups:
  - wave: 1
    name: "Foundation"
    strategy: sequential
    tasks: [TASK-001]
```

**Expected `FeatureLoader` input (correct)**:
```yaml
tasks:
  - id: TASK-001
    name: "Task Name"
    file_path: "tasks/backlog/.../TASK-001.md"
    status: pending
    complexity: 5
    dependencies: []
    implementation_mode: task-work

orchestration:
  parallel_groups:
    - - TASK-001
```

### Source Files Reviewed

- [docs/reviews/feature-build/feature-build-output.md](docs/reviews/feature-build/feature-build-output.md) - Error log
- [guardkit/orchestrator/feature_loader.py](guardkit/orchestrator/feature_loader.py) - CLI parser
- [installer/core/commands/feature-plan.md](installer/core/commands/feature-plan.md) - Command spec

---

*Report generated by Claude Code review workflow*
