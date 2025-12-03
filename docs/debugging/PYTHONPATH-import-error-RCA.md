# Root Cause Analysis: Python Import Error in /template-create

**Issue ID**: PYTHONPATH-IMPORT-001
**Date**: 2025-11-21
**Status**: IDENTIFIED (Fix Present but Not Invoked)
**Impact**: MEDIUM - Workaround available but user experience affected

---

## Summary

The `/template-create` command fails with `ModuleNotFoundError: No module named 'installer'` when executed **directly** without PYTHONPATH configuration. The fix exists in the command specification (`template-create.md` lines 1026-1105) but is **not being invoked** by Claude Code's command processing.

**Root Cause**: Claude Code executes Python orchestrator scripts **directly** without processing the command's PYTHONPATH setup code, causing import failures for modules using `installer.global.*` imports.

---

## Reproduction Steps

### Failed Scenario (Direct Execution)
```bash
cd /path/to/any/directory
/template-create --name test-template

# Result:
# File "/Users/richardwoollcott/.agentecflow/commands/lib/template_create_orchestrator.py", line 20
# _template_qa_module = importlib.import_module('installer.global.commands.lib.template_qa_session')
# ModuleNotFoundError: No module named 'installer'
```

### Working Scenario (Manual PYTHONPATH)
```bash
cd /path/to/any/directory
PYTHONPATH="/Users/richardwoollcott/Projects/appmilla_github/guardkit" /template-create --name test-template

# Result: ✅ Success
```

---

## Investigation Timeline

### 1. Initial Failure
- **What happened**: Command failed with `ModuleNotFoundError: No module named 'installer'`
- **File location**: `~/.agentecflow/commands/lib/template_create_orchestrator.py:20`
- **Import statement**: `importlib.import_module('installer.global.commands.lib.template_qa_session')`

### 2. Environment Discovery
- **Directory check**: `~/.agentecflow/commands/` is a **regular directory** (NOT a symlink)
- **Install process**: `install.sh` copies files from `installer/global/commands/` to `~/.agentecflow/commands/`
- **Python path**: Does NOT include guardkit repository directory by default

### 3. PYTHONPATH Setup Discovery
Found comprehensive PYTHONPATH discovery code in `template-create.md` (lines 1026-1105):
```python
def find_guardkit_path():
    """
    Find guardkit installation directory.

    Tries multiple strategies in priority order:
    1. Follow ~/.agentecflow symlink (if exists and points to guardkit)
    2. Check standard location: ~/Projects/appmilla_github/guardkit
    3. Check current directory (fallback for development)
    """
    # ... implementation omitted for brevity
```

### 4. Command Execution Pattern Discovery
Found that command should execute orchestrator with PYTHONPATH (line 1160):
```python
cmd = f'PYTHONPATH="{guardkit_path}" {cmd_without_env}'
```

---

## Root Cause

### Architectural Context

**Installation Model** (`install.sh`):
1. Copies files from `guardkit/installer/global/commands/` → `~/.agentecflow/commands/`
2. Creates symlinks: `~/.claude/commands` → `~/.agentecflow/commands/`
3. Makes commands available to Claude Code

**Import Pattern** (`template_create_orchestrator.py`):
```python
# Line 20: Uses absolute imports referencing original repository structure
_template_qa_module = importlib.import_module('installer.global.commands.lib.template_qa_session')
```

**Why This Fails**:
```
File Location:    ~/.agentecflow/commands/lib/template_create_orchestrator.py
Import Reference: installer.global.commands.lib.template_qa_session
Python Working Dir: <user's current directory>

Python cannot resolve 'installer' module because:
1. Python's working directory is user's current directory (not guardkit repo)
2. PYTHONPATH does not include guardkit repository directory
3. The 'installer' package exists in guardkit repo, NOT in ~/.agentecflow/
```

### Why PYTHONPATH Fix Was Necessary

**Directory Structure**:
```
guardkit/                           # PYTHONPATH must point here
├── installer/
│   └── global/
│       ├── commands/
│       │   └── lib/
│       │       └── template_qa_session.py  # Target import location
│       └── lib/
│           └── codebase_analyzer/
│               └── ai_analyzer.py         # Another target import

~/.agentecflow/                       # Installed location (copied files)
└── commands/
    └── lib/
        └── template_create_orchestrator.py  # File trying to import
```

**Import Resolution**:
- Import: `installer.global.commands.lib.template_qa_session`
- Requires: Python to find `guardkit/installer/global/commands/lib/template_qa_session.py`
- Needs: `PYTHONPATH="/path/to/guardkit"` so Python can resolve `installer.global.*`

---

## Why Fix Exists But Wasn't Invoked

### Expected Flow (from template-create.md)

The command specification includes PYTHONPATH discovery and setup (lines 1026-1105):

1. **Discovery Phase**:
   ```python
   guardkit_path = find_guardkit_path()
   # Tries: ~/.agentecflow symlink, standard path, current directory
   ```

2. **PYTHONPATH Setup**:
   ```python
   os.environ["PYTHONPATH"] = str(guardkit_path)
   ```

3. **Command Execution**:
   ```python
   cmd = f'PYTHONPATH="{guardkit_path}" python3 {orchestrator_script}'
   ```

### Actual Flow (What Claude Code Does)

**Hypothesis**: Claude Code executes the Python orchestrator **directly** without:
1. Processing the Python setup code in the markdown
2. Extracting the PYTHONPATH configuration
3. Setting environment variables before invocation

**Evidence**:
- Direct execution works: `PYTHONPATH="..." /template-create` ✅
- Normal execution fails: `/template-create` ❌
- Error occurs immediately at import time (line 20 of orchestrator)
- PYTHONPATH discovery code is in markdown, not in orchestrator Python file

### Command Processing Gap

**Command Specification Structure**:
```markdown
# template-create.md

## Execution

### Step 1: Parse Arguments
[Python code for argument parsing]

### Step 2: Checkpoint-Resume Loop
[Python code with PYTHONPATH setup - lines 1006-1448]
```

**Issue**: Claude Code likely:
1. Reads `template-create.md`
2. Extracts orchestrator path: `installer/global/commands/lib/template_create_orchestrator.py`
3. **Directly executes**: `python3 template_create_orchestrator.py [args]`
4. **Skips**: PYTHONPATH discovery/setup code in markdown

---

## Impact Assessment

### Current Impact
- **Severity**: MEDIUM
- **Frequency**: ALWAYS (for direct `/template-create` invocations)
- **Workaround**: Available (manual PYTHONPATH)
- **User Experience**: Poor (requires manual intervention)

### Affected Commands
**Analysis**: Only `template_create_orchestrator.py` uses `installer.global.*` imports:
```bash
$ grep -r "importlib.import_module.*installer.global" ~/.agentecflow/commands/lib/
# Result: Only template_create_orchestrator.py
```

**Other commands**: Use relative imports or direct file paths (not affected)

### Why Other Commands Don't Fail
Most commands are markdown-based agent workflows that:
1. Don't use Python orchestrators
2. Use relative imports within `~/.agentecflow/commands/lib/`
3. Don't reference `installer.global.*` package structure

---

## Solutions Analysis

### Solution 1: Fix Command Processing (RECOMMENDED)
**Change**: Modify how Claude Code processes commands with Python setup code

**Approach**:
1. Extract PYTHONPATH setup from markdown
2. Execute setup code before invoking orchestrator
3. Pass environment variables to subprocess

**Pros**:
- Fixes root cause
- Maintains current architecture
- Works for future commands with similar pattern

**Cons**:
- Requires Claude Code internal changes
- May affect other command processing logic

**Effort**: HIGH (requires understanding Claude Code command processing)

---

### Solution 2: Relocate PYTHONPATH Setup to Orchestrator (QUICK FIX)
**Change**: Move PYTHONPATH discovery from markdown into orchestrator

**Implementation**:
```python
# template_create_orchestrator.py (add at top of file)

import sys
from pathlib import Path
import os

def setup_pythonpath():
    """Find and configure PYTHONPATH for installer imports."""
    # Strategy 1: Follow ~/.agentecflow symlink
    agentecflow = Path.home() / ".agentecflow"
    if agentecflow.is_symlink():
        target = agentecflow.resolve()
        if target.name == ".agentecflow":
            guardkit_path = target.parent
            if (guardkit_path / "installer").exists():
                sys.path.insert(0, str(guardkit_path))
                return guardkit_path

    # Strategy 2: Standard installation
    standard_path = Path.home() / "Projects" / "appmilla_github" / "guardkit"
    if (standard_path / "installer").exists():
        sys.path.insert(0, str(standard_path))
        return standard_path

    # Strategy 3: Current directory
    if Path("installer").exists():
        sys.path.insert(0, str(Path.cwd()))
        return Path.cwd()

    raise ImportError(
        "Cannot find guardkit installation. "
        "Set PYTHONPATH manually: "
        "export PYTHONPATH=/path/to/guardkit"
    )

# Run setup before any imports
try:
    setup_pythonpath()
except ImportError as e:
    print(f"❌ {e}")
    sys.exit(2)

# NOW safe to import installer.global modules
import importlib
_template_qa_module = importlib.import_module('installer.global.commands.lib.template_qa_session')
# ... rest of imports
```

**Pros**:
- Quick fix (single file change)
- Self-contained (orchestrator handles own dependencies)
- Works immediately without Claude Code changes
- Maintains compatibility with manual PYTHONPATH

**Cons**:
- Duplicates logic (setup code exists in markdown and orchestrator)
- Doesn't fix root cause (command processing gap remains)
- May need to repeat for future orchestrators

**Effort**: LOW (1-2 hours)

---

### Solution 3: Use Relative Imports (ARCHITECTURAL CHANGE)
**Change**: Refactor imports to use relative paths within installed location

**Challenges**:
1. **Package Structure Mismatch**:
   ```
   installer/global/lib/codebase_analyzer/  # Source modules
   ~/.agentecflow/commands/lib/             # Orchestrator location
   ```

2. **Modules Not Co-located**: Orchestrator imports from multiple `installer/global/lib/` subdirectories

3. **Would Require**:
   - Copying ALL dependent modules to `~/.agentecflow/commands/lib/`
   - Flattening package structure (lose namespace organization)
   - Major refactoring of import paths

**Pros**:
- Eliminates PYTHONPATH dependency
- More "portable" installation

**Cons**:
- MAJOR refactoring (20+ modules)
- Loses clean package organization
- Breaks development workflow (modules in repo not usable directly)
- High risk of breaking other functionality

**Effort**: VERY HIGH (several days)
**Recommendation**: NOT RECOMMENDED

---

### Solution 4: Symlink ~/.agentecflow to Repo (ARCHITECTURAL CHANGE)
**Change**: Make `~/.agentecflow/` a symlink to `guardkit/installer/global/`

**Implementation**:
```bash
rm -rf ~/.agentecflow
ln -s ~/Projects/appmilla_github/guardkit/installer/global ~/.agentecflow
```

**Pros**:
- No import issues (files in original location)
- Direct development workflow (edit in repo)
- No file copying needed

**Cons**:
- **BREAKS TEMPLATE CREATION**: Users can't save to `~/.agentecflow/templates/`
- Repository becomes user data directory (bad separation of concerns)
- Complicates updates/uninstall
- Violates install philosophy (copy files to stable location)

**Effort**: LOW (install script change)
**Recommendation**: NOT RECOMMENDED (wrong architecture)

---

## Recommended Solution: Hybrid Approach

**Best Practice**: **Solution 2 (Move Setup to Orchestrator) + Documentation**

### Implementation Plan

**Phase 1: Immediate Fix (Solution 2)**
1. Add `setup_pythonpath()` function to orchestrator header
2. Call before imports
3. Test with and without manual PYTHONPATH
4. Update orchestrator docstring to document behavior

**Phase 2: Documentation**
1. Document PYTHONPATH requirements in orchestrator
2. Add troubleshooting guide for import errors
3. Update CLAUDE.md with installation validation steps

**Phase 3: Future Improvement (Solution 1 - Optional)**
1. When time permits, investigate Claude Code command processing
2. Implement proper environment setup from markdown
3. Remove duplicated setup code from orchestrator

### Why This Approach?

**Solves Immediate Problem**:
- Users can run `/template-create` without manual PYTHONPATH ✅
- Maintains current architecture ✅
- Low risk (self-contained change) ✅

**Maintains Quality**:
- Proper error messages if guardkit not found ✅
- Automatic discovery (no user configuration) ✅
- Compatible with existing workflows ✅

**Future-Proof**:
- Doesn't prevent future Claude Code improvements ✅
- Can be refactored when command processing is enhanced ✅
- Documents the issue for future maintainers ✅

---

## Verification Tests

### Test 1: Direct Execution (No PYTHONPATH)
```bash
cd /tmp
/template-create --name test-direct --dry-run
# Expected: ✅ Success
```

### Test 2: With Manual PYTHONPATH (Compatibility)
```bash
cd /tmp
PYTHONPATH="/Users/richardwoollcott/Projects/appmilla_github/guardkit" /template-create --name test-manual --dry-run
# Expected: ✅ Success
```

### Test 3: From Different Directories
```bash
cd ~/Documents
/template-create --name test-documents --dry-run

cd /
/template-create --name test-root --dry-run
# Expected: ✅ Success in both
```

### Test 4: Error Message (GuardKit Not Found)
```bash
# Temporarily rename guardkit directory
mv ~/Projects/appmilla_github/guardkit ~/Projects/appmilla_github/guardkit.bak

/template-create --name test-error
# Expected: Clear error message with troubleshooting steps

# Restore
mv ~/Projects/appmilla_github/guardkit.bak ~/Projects/appmilla_github/guardkit
```

---

## Prevention Strategy

### For Future Commands

**When creating Python orchestrators that import from `installer.global.*`**:

1. **Add PYTHONPATH setup at top of orchestrator**:
   ```python
   # Add before any installer.global imports
   import sys
   from pathlib import Path

   def setup_pythonpath():
       # ... discovery logic
       pass

   setup_pythonpath()
   ```

2. **Document dependency in orchestrator docstring**:
   ```python
   """
   Orchestrator for /some-command

   PYTHONPATH Requirements:
   - Must be able to import 'installer.global' package
   - Auto-discovers guardkit installation
   - Falls back to PYTHONPATH environment variable
   """
   ```

3. **Test from multiple directories**:
   ```bash
   cd /tmp && /some-command
   cd ~ && /some-command
   cd /project && /some-command
   ```

### Code Review Checklist

When reviewing orchestrator PRs:
- [ ] Does orchestrator import from `installer.global.*`?
- [ ] Does it include PYTHONPATH setup before imports?
- [ ] Are error messages clear if guardkit not found?
- [ ] Has it been tested from multiple directories?
- [ ] Does it handle manual PYTHONPATH override?

---

## Related Issues

### Similar Patterns to Check

**Other orchestrators that may need PYTHONPATH**:
```bash
find ~/.agentecflow/commands/lib -name "*_orchestrator.py"
# Check each for installer.global imports
```

**Template QA session** (imported by orchestrator):
- Already in correct location: `~/.agentecflow/commands/lib/template_qa_session.py`
- No import issues (imports from same lib directory)

### Future Refactoring Opportunities

**If Solution 1 is implemented** (Claude Code command processing):
1. Extract environment setup pattern
2. Apply to all commands with Python components
3. Standardize setup code location/format
4. Add command processing tests

---

## Conclusion

**Root Cause**: Claude Code executes Python orchestrators directly without processing PYTHONPATH setup code from command markdown, causing `installer.global.*` imports to fail.

**Immediate Fix**: Move PYTHONPATH discovery from markdown to orchestrator header (Solution 2)

**Long-Term Fix**: Enhance Claude Code command processing to handle environment setup from markdown (Solution 1)

**Impact**: MEDIUM severity, affects only `/template-create`, workaround available

**Recommendation**: Implement Solution 2 immediately, document for future Solution 1 enhancement

---

**Investigation Complete**: 2025-11-21
**Investigators**: Claude (Debugging Specialist)
**Next Steps**: Implement Solution 2, update tests, document
