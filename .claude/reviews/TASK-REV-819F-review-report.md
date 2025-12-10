# Review Report: TASK-REV-819F

## Executive Summary

The `/template-create` command fails with `ModuleNotFoundError: No module named 'lib'` when executed via the symlinked orchestrator script. This is a **direct consequence** of the incomplete `global→core` rename (TASK-RENAME-GLOBAL).

**Root Cause**: The `lib` symlink at repository root (`/guardkit/lib`) still points to `installer/global/lib` which no longer exists after the rename to `installer/core/lib`.

**Severity**: **HIGH** - Blocks the `/template-create` command for all users

**Workaround Available**: Yes - Users can set `PYTHONPATH` to include `installer/core` before running the command.

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard
- **Duration**: ~15 minutes
- **Files Analyzed**: 6

## Root Cause Analysis

### Primary Issue: Broken `lib` Symlink

The repository contains a symlink at root level:

```
/guardkit/lib -> installer/global/lib
```

This symlink was created before the `global→core` rename but was **not updated** during TASK-RENAME-GLOBAL.

**Evidence**:
```bash
$ git cat-file -p $(git rev-parse HEAD:lib)
installer/global/lib
```

The target `installer/global/lib` no longer exists (directory renamed to `installer/core/lib`).

### Secondary Issue: Path Resolution in Orchestrator

The orchestrator script (`template_create_orchestrator.py`) has correct path resolution logic:

```python
def _add_repo_to_path():
    script_path = Path(__file__).resolve()
    # Navigate: lib/ -> commands/ -> core/ -> installer/ -> guardkit/ (5 levels up)
    repo_root = script_path.parent.parent.parent.parent.parent
    sys.path.insert(0, str(repo_root))
```

This correctly resolves to `/guardkit` and adds it to `sys.path`. However, when Python tries to import `lib.codebase_analyzer`, it:
1. Looks for `lib/` in sys.path entries
2. Finds `/guardkit/lib` (a symlink)
3. Follows symlink to `installer/global/lib` (non-existent)
4. Fails with `ModuleNotFoundError`

### Why the Workaround Works

Setting `PYTHONPATH=installer/core:$PYTHONPATH` works because:
1. Python searches `installer/core` first
2. Finds `installer/core/lib/` directly
3. Imports succeed without following the broken symlink

## Affected Components

| Component | Impact |
|-----------|--------|
| `template_create_orchestrator.py` | 20+ `importlib.import_module('lib.*')` calls fail |
| `/template-create` command | Completely broken |
| `lib` symlink | Points to non-existent directory |

### Other Scripts

Only `template_create_orchestrator.py` uses the `importlib.import_module('lib.*')` pattern. Other scripts in `installer/core/commands/lib/` use relative imports or don't depend on the `lib` symlink.

## Fix Options

### Option A: Fix the `lib` Symlink (Recommended)

**Effort**: Low (~5 minutes)
**Risk**: Low
**Completeness**: Full

Update the symlink to point to the new location:

```bash
cd /guardkit
rm lib
ln -s installer/core/lib lib
git add lib
git commit -m "Fix lib symlink: global→core"
```

**Pros**:
- Minimal code changes
- Fixes the issue at the source
- Completes the TASK-RENAME-GLOBAL rename
- All existing path resolution logic continues to work

**Cons**:
- None significant

### Option B: Update Path Resolution in Orchestrator

**Effort**: Medium (~30 minutes)
**Risk**: Medium
**Completeness**: Partial (only fixes orchestrator)

Modify the path resolution to add `installer/core` to sys.path instead of repo root:

```python
def _add_repo_to_path():
    script_path = Path(__file__).resolve()
    # Navigate to installer/core instead of repo root
    core_path = script_path.parent.parent.parent  # installer/core
    sys.path.insert(0, str(core_path))
```

**Pros**:
- Works even if symlink doesn't exist

**Cons**:
- Only fixes orchestrator, not other potential users of `lib`
- Requires testing all 20+ imports
- Doesn't fix the underlying broken symlink

### Option C: Remove importlib Usage (Deferred)

**Effort**: High (1-2 hours)
**Risk**: Medium
**Completeness**: Full (but more invasive)

As noted in TASK-RENAME-GLOBAL, removing `importlib` workarounds was intentionally deferred. This would involve converting all imports to standard Python imports:

```python
# Instead of
_codebase_analyzer_module = importlib.import_module('lib.codebase_analyzer.ai_analyzer')
CodebaseAnalyzer = _codebase_analyzer_module.CodebaseAnalyzer

# Use
from lib.codebase_analyzer.ai_analyzer import CodebaseAnalyzer
```

**Pros**:
- Cleaner code
- Better IDE support
- Easier debugging

**Cons**:
- Requires fixing the symlink anyway
- Higher risk of introducing bugs
- Should be a separate task (TASK-CLEANUP-IMPORTLIB already exists)

## Recommendation

**Implement Option A** (Fix the `lib` symlink).

This is the simplest, lowest-risk solution that directly addresses the root cause. The symlink should have been updated during TASK-RENAME-GLOBAL but was missed.

### Additional Recommendation

Update TASK-RENAME-GLOBAL completion criteria to include:
- [x] `lib` symlink updated from `installer/global/lib` to `installer/core/lib`

## Decision Matrix

| Option | Effort | Risk | Completeness | Time | Recommendation |
|--------|--------|------|--------------|------|----------------|
| A: Fix symlink | Low | Low | Full | 5 min | **Recommended** |
| B: Update orchestrator | Medium | Medium | Partial | 30 min | Not recommended |
| C: Remove importlib | High | Medium | Full | 2 hrs | Defer to TASK-CLEANUP-IMPORTLIB |

## Implementation Plan (Option A)

### Step 1: Fix the Symlink
```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit
rm lib
ln -s installer/core/lib lib
```

### Step 2: Verify Fix
```bash
python3 -c "from lib.codebase_analyzer.ai_analyzer import CodebaseAnalyzer; print('OK')"
```

### Step 3: Test Command
```bash
python3 ~/.agentecflow/bin/template-create-orchestrator --help
```

### Step 4: Commit
```bash
git add lib
git commit -m "fix(symlink): Update lib symlink from global to core

TASK-REV-819F: Fix broken lib symlink after global→core rename.

The symlink was pointing to installer/global/lib which no longer
exists after TASK-RENAME-GLOBAL. Updated to installer/core/lib."
```

## Related Tasks

| Task | Status | Relationship |
|------|--------|--------------|
| TASK-RENAME-GLOBAL | IN_REVIEW | Parent (symlink fix was missed) |
| TASK-REV-144B | Completed | Related (fixed install.sh paths) |
| TASK-CLEANUP-IMPORTLIB | Backlog | Follow-up (remove importlib workarounds) |

## Appendix: Affected Imports

All 20+ `importlib.import_module('lib.*')` calls in `template_create_orchestrator.py`:

```python
importlib.import_module('lib.codebase_analyzer.ai_analyzer')
importlib.import_module('lib.template_creation.manifest_generator')
importlib.import_module('lib.settings_generator.generator')
importlib.import_module('lib.template_generator.claude_md_generator')
importlib.import_module('lib.template_generator.template_generator')
importlib.import_module('lib.agent_generator.agent_generator')
importlib.import_module('lib.agent_bridge.invoker')
importlib.import_module('lib.agent_bridge.state_manager')
importlib.import_module('lib.utils.file_io')
importlib.import_module('lib.orchestrator_error_messages')
importlib.import_module('lib.template_generator.completeness_validator')
importlib.import_module('lib.template_generator.models')
importlib.import_module('lib.template_generator.extended_validator')
importlib.import_module('lib.template_generator.report_generator')
importlib.import_module('lib.template_creation.constants')
importlib.import_module('lib.agent_scanner')
importlib.import_module('lib.agent_generator.agent_generator')
importlib.import_module('lib.agent_generator.markdown_formatter')
importlib.import_module('lib.codebase_analyzer.serializer')
importlib.import_module('lib.codebase_analyzer.models')
```

All will fail until the `lib` symlink is fixed.
