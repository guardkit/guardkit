# Review Report: TASK-REV-1BE3

## Executive Summary

FEAT-CEE8 failed with `UNRECOVERABLE_STALL` because the `/feature-plan` LLM invocation of `generate-feature-yaml` omitted the `--feature-slug` argument, causing all task `file_path` values in the YAML to be set to `"."` instead of proper paths like `tasks/backlog/api-documentation/TASK-DOC-001-create-openapi-config-module.md`. This prevented `_copy_tasks_to_worktree()` from copying task files to the worktree, and `TaskStateBridge` could not find them, producing the same error on every turn until stall detection terminated the run.

**Root cause**: Spec-level bug in `feature-plan.md` — the example `generate-feature-yaml` invocation at line 1723 does not include `--feature-slug`, so the LLM following the spec omitted it.

**Secondary cause**: `FeatureLoader.validate_feature()` does not catch `file_path: .` because `Path(".").exists()` returns `True` (it resolves to the current directory).

**Tertiary cause**: `_copy_tasks_to_worktree()` logs a warning but does not raise an exception when file_path parsing fails, so execution continues into an unrecoverable state.

## Evidence

### Failure Log (api_docs_1.md)

| Line | Event | Significance |
|------|-------|--------------|
| 15 | `Loading feature from .../FEAT-CEE8.yaml` | Feature YAML loaded successfully |
| 17 | `Tasks: 5` | All 5 tasks present in YAML |
| 19 | `Feature validation passed` | **Validation missed the bad file_path** |
| 23 | `WARNING: Cannot copy tasks: 'tasks' directory not found in path: .` | **Root cause visible here** |
| 52 | `Ensuring task TASK-DOC-001 is in design_approved state` | State bridge attempts to find task file |
| 53 | `Task TASK-DOC-001 not found in any state directory` | **Fatal error** — task file not in worktree |
| 246 | `Unrecoverable stall detected` | Same error 3 turns in a row → stall exit |

### FEAT-CEE8 YAML (the broken feature)

```yaml
tasks:
- id: TASK-DOC-001
  name: Create OpenAPI configuration module
  file_path: .     # <-- BUG: should be tasks/backlog/api-documentation/TASK-DOC-001-create-openapi-config-module.md
  complexity: 4
```

All 5 tasks have `file_path: .`.

### FEAT-DD34 YAML (successful run, same repo, same day)

```yaml
tasks:
- id: TASK-FHA-001
  name: Create project scaffolding
  file_path: tasks/backlog/fastapi-health-app/TASK-FHA-001-create-project-scaffolding.md  # <-- CORRECT
  complexity: 2
```

### Task Files DO Exist

```
tasks/backlog/api-documentation/
├── IMPLEMENTATION-GUIDE.md
├── README.md
├── TASK-DOC-001-create-openapi-config-module.md   # EXISTS
├── TASK-DOC-002-configure-main-app-metadata.md    # EXISTS
├── TASK-DOC-003-implement-api-versioning-headers.md
├── TASK-DOC-004-add-response-examples.md
└── TASK-DOC-005-add-documentation-tests.md
```

The task markdown files were created correctly by the `/feature-plan` [I]mplement step. The YAML generation step that followed got the wrong `file_path` values.

## Root Cause Chain

```
1. /feature-plan spec (feature-plan.md:1723-1729)
   Example invocation does NOT include --feature-slug:

   python3 ~/.agentecflow/bin/generate-feature-yaml \
       --name "{feature_name}" \
       --task "TASK-001:First task name:5:" \
       --base-path "."

   Missing: --feature-slug "api-documentation"

2. generate_feature_yaml.py (parse_task_string, line 205-207)
   When feature_slug is empty, file_path defaults to "":

   file_path = ""
   if feature_slug:        # <-- False when empty
       file_path = build_task_file_path(...)

3. YAML serialization
   file_path: "" written to YAML. But actual YAML shows "." —
   likely the LLM set base-path "." and it ended up as file_path,
   or the LLM manually wrote file_path values.

4. FeatureLoader.validate_feature() (feature_loader.py:646)
   task_file = repo_root / Path(".")  # resolves to repo_root
   repo_root.exists() == True          # VALIDATION PASSES (false positive)

5. _copy_tasks_to_worktree() (feature_orchestrator.py:656-674)
   Path(".").parts == (".",)
   "tasks" not in (".",)  → ValueError → WARNING logged
   Returns without copying any files

6. TaskStateBridge._get_current_state() (state_bridge.py:287-316)
   Searches worktree_path/tasks/{backlog,in_progress,...}
   No task files found → raises TaskNotFoundError

7. All 3 turns fail identically → UNRECOVERABLE_STALL
```

## Responsibility Map (AC-002)

| Component | Responsibility | Status |
|-----------|---------------|--------|
| `/feature-plan` spec (feature-plan.md) | Specifies correct args for generate-feature-yaml | **BUG**: Missing `--feature-slug` in example |
| `generate_feature_yaml.py` | Generates YAML with correct `file_path` values | **WORKS** when `--feature-slug` provided |
| `FeatureLoader.validate_feature()` | Validates task `file_path` values are real files | **BUG**: `Path(".")` passes existence check |
| `_copy_tasks_to_worktree()` | Copies task files from repo to worktree | **BUG**: Logs warning but doesn't raise on failure |
| `TaskStateBridge` | Finds task files in worktree | **WORKS**: Correctly reports missing files |

## "Cannot copy tasks" Warning Trace (AC-003)

**Source**: `feature_orchestrator.py:610-735` (`_copy_tasks_to_worktree`)

**Call chain**:
1. `_load_feature()` at line 462 → loads YAML
2. `_create_new_worktree()` at line 564 → creates git worktree
3. `_copy_tasks_to_worktree()` at line 598 → called after worktree creation

**Warning at line 672-674**:
```python
except ValueError:
    logger.warning(
        f"Cannot copy tasks: 'tasks' directory not found in path: {task_file_path}"
    )
    return
```

This is triggered when `Path(first_task.file_path).parts` doesn't contain `"tasks"`. For `file_path: .`, `Path(".").parts = (".",)`, which has no `"tasks"` element, triggering the `ValueError` from `parts.index("tasks")`.

**Impact of the warning-only approach**: Execution continues to the Player-Coach loop where every turn fails with the same `TaskNotFoundError`. The warning is never escalated to an error that would halt execution early.

## Fix Recommendations (AC-004)

### FIX-1: Update feature-plan.md spec (PRIMARY FIX)

**File**: `installer/core/commands/feature-plan.md:1723-1729`

Add `--feature-slug` to the example invocation:

```bash
python3 ~/.agentecflow/bin/generate-feature-yaml \
    --name "{feature_name}" \
    --description "{review_findings_summary}" \
    --feature-slug "{feature_slug}" \
    --task "TASK-001:First task name:5:" \
    --base-path "."
```

Also update the second example at line 1740-1748 and the walkthrough at line 1875.

### FIX-2: Validate file_path is a proper task file path (DEFENSIVE)

**File**: `guardkit/orchestrator/feature_loader.py:644-648`

Add validation that `file_path` points to a `.md` file, not a directory:

```python
for task in feature.tasks:
    task_file = repo_root / task.file_path
    if task_file.is_dir():
        errors.append(f"Task file_path is a directory, not a file: {task.id} at {task.file_path}")
    elif not task_file.exists():
        errors.append(f"Task file not found: {task.id} at {task.file_path}")
```

### FIX-3: Raise on copy failure instead of warning (DEFENSIVE)

**File**: `guardkit/orchestrator/feature_orchestrator.py:670-675`

Change from warning to raising `FeatureValidationError`:

```python
except ValueError:
    raise FeatureValidationError(
        f"Invalid task file_path '{task_file_path}' in task {first_task.id}. "
        f"Expected format: tasks/backlog/<feature-slug>/TASK-XXX.md. "
        f"This usually means --feature-slug was not passed to generate-feature-yaml."
    )
```

### FIX-4: Default file_path to proper path when feature_slug is empty

**File**: `installer/core/commands/lib/generate_feature_yaml.py:204-207`

When `feature_slug` is empty, require it or raise an error:

```python
if not feature_slug:
    print("Error: --feature-slug is required for file_path generation", file=sys.stderr)
    sys.exit(1)
file_path = build_task_file_path(task_id, feature_slug, task_base_path, task_name=name)
```

### Fix Priority

| Fix | Type | Effort | Impact |
|-----|------|--------|--------|
| FIX-1 | Spec bug fix | Low (3 lines in markdown) | **Critical** — prevents recurrence |
| FIX-2 | Defensive validation | Low (3 lines) | High — catches bad YAML early |
| FIX-3 | Fail-fast | Low (5 lines) | High — prevents wasted turns |
| FIX-4 | Input validation | Low (3 lines) | Medium — catches at generation time |

## Impact Assessment (AC-005)

### Affected Scenarios

**Directly affected**: Any `/feature-plan` invocation where the LLM follows the spec example literally and omits `--feature-slug`. This is **non-deterministic** — it depends on whether the LLM includes it independently or follows the example.

**Evidence of non-determinism**: FEAT-DD34 (same repo, same day) succeeded because the LLM DID include `--feature-slug fastapi-health-app`. FEAT-CEE8 failed because it didn't.

### NOT Affected

- **Direct `guardkit autobuild task` (single-task mode)**: Does not use feature YAML or `_copy_tasks_to_worktree()`
- **Features with committed task files**: If task files are already committed to git, the worktree checkout includes them. The copy step is only needed for uncommitted files
- **Existing successful features**: FEAT-6EDD, FEAT-DD34 etc. all had correct `file_path` values

### Risk Level

**Medium-High**: The bug is in a spec file (LLM instruction), so it's probabilistic rather than deterministic. Some feature-plan runs will succeed (LLM includes `--feature-slug` on its own) while others will fail. The lack of defensive validation means failures waste turns before being detected.

## Comparison: FEAT-DD34 (Success) vs FEAT-CEE8 (Failure)

| Aspect | FEAT-DD34 | FEAT-CEE8 |
|--------|-----------|-----------|
| Repo | fastapi-examples | fastapi-examples |
| Date | 2026-02-10 | 2026-02-10 |
| Tasks | 5 | 5 |
| `file_path` | `tasks/backlog/fastapi-health-app/TASK-FHA-001-...md` | `.` |
| `--feature-slug` | Provided | **Not provided** |
| Task files exist | Yes | Yes (at `tasks/backlog/api-documentation/`) |
| Copy to worktree | Success | **Failed** (warning logged) |
| Validation | Passed | Passed (false positive) |
| Result | 5/5 approved | 0/5, UNRECOVERABLE_STALL |

## Appendix: Inconsistency in feature-plan.md

Line 1719 says:
> Note: Task file paths are derived automatically from --feature-slug.

But the examples at lines 1723-1729 and 1740-1748 do NOT include `--feature-slug` in the invocation. This contradiction is the direct cause of the bug — the LLM reads the example code block and replicates it without `--feature-slug`.

Additionally, line 1878 shows a different task format (`ID:NAME:FILE_PATH:COMPLEXITY:DEPS`) that contradicts the documented format at line 1732 (`ID:NAME:COMPLEXITY:DEPS`). This further confuses the LLM about how file_path should be provided.
