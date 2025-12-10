# TASK-BRIDGE-006: Fix /template-create Command File Structure

**Status**: completed
**Priority**: critical
**Estimated Duration**: 2 hours
**Actual Duration**: 40 minutes
**Completed**: 2025-11-12T00:00:00Z
**Completed Location**: tasks/completed/TASK-BRIDGE-006/
**Tags**: #bridge #bugfix #command-structure #template-create

---

## Description

Fix the `/template-create` command file structure so Claude Code properly executes the Python code block instead of creating wrapper scripts. Currently, Claude Code is ignoring the Python code in `template-create.md` and manually running the orchestrator with wrapper scripts.

**Part of**: Python↔Claude Agent Invocation Bridge (Critical Feature)
**Depends on**: TASK-BRIDGE-005 (COMPLETED)
**Blocks**: Template creation functionality

---

## Context

### Current Behavior (BROKEN)

When user runs `/template-create --validate`, Claude Code:
1. ❌ Does NOT execute Python code block from `template-create.md`
2. ❌ Creates wrapper script in `/tmp/template_create_runner.py`
3. ❌ Manually discovers PYTHONPATH
4. ❌ Manually runs orchestrator with subprocess
5. ❌ Asks user for approval before executing

### Expected Behavior (WORKING)

When user runs `/template-create --validate`, Claude Code should:
1. ✅ Directly execute Python code block from `template-create.md`
2. ✅ Use PYTHONPATH discovery code in the command file
3. ✅ Run orchestrator using the checkpoint-resume loop
4. ✅ Execute immediately without user approval

### Root Causes Identified

1. **Command file structure may not match Claude Code's expectations**
   - Python code block might not be in the right format
   - Markers or delimiters might be incorrect

2. **Multiple Python code blocks confusing Claude Code**
   - Line 288: Data structure example (NOT executable)
   - Line 983: Main execution code (SHOULD be executable)

3. **Import path issues in orchestrator files**
   - `manifest_generator.py` has incorrect imports
   - Other files may have similar issues
   - Multiple PYTHONPATH locations needed (taskwright + installer/core)

4. **Missing __main__ entry point in orchestrator module**
   - `template_create_orchestrator.py` is a module, not a script
   - No `if __name__ == "__main__"` block
   - Unclear how Python executes it as `-m module`

---

## Acceptance Criteria

### Primary Criteria

- [x] Claude Code executes Python code block directly from command file
- [x] No wrapper scripts created in /tmp
- [x] PYTHONPATH discovery works from Python code in command file
- [x] Orchestrator runs using checkpoint-resume loop
- [x] User does NOT get approval prompts for execution
- [x] Command works from any directory

### Import Path Fixes

- [x] All import errors in orchestrator files fixed
- [x] PYTHONPATH includes both locations:
  - [x] `/path/to/taskwright` (for `installer.core.*` imports)
  - [x] `/path/to/taskwright/installer/core` (for `lib.*` imports)
- [x] Imports use consistent patterns across all files

### Testing Criteria

- [x] `/template-create --validate` runs without errors
- [x] Python code block executes immediately
- [x] Orchestrator loads all modules successfully
- [x] Q&A session starts (if not --skip-qa)
- [x] Agent invocation works (exit code 42 handled)

---

## Investigation Required

### 1. Claude Code Command File Format

**Questions to answer:**
- What is the exact format Claude Code expects for command files?
- How should Python code blocks be delimited?
- Should there be only ONE Python code block?
- Where in the file should the executable code block be?
- Are there any special markers or frontmatter needed?

**Actions:**
- [ ] Read Claude Code documentation on command file format
- [ ] Examine working command files (e.g., `debug.md`, `task-work.md`)
- [ ] Compare structure with `template-create.md`
- [ ] Identify differences

### 2. Import Path Architecture

**Questions to answer:**
- Why do some files use `from lib.codebase_analyzer.models` imports?
- Why do other files use `from installer.core.lib.*` imports?
- What PYTHONPATH configuration makes both work?
- Should all imports be standardized?

**Actions:**
- [ ] Audit all import statements in `installer/core/` directory
- [ ] Map import patterns to file locations
- [ ] Determine correct PYTHONPATH configuration
- [ ] Document import conventions

### 3. Module Execution Model

**Questions to answer:**
- How does `python3 -m installer.core.commands.lib.template_create_orchestrator` work?
- What makes a module executable with `-m` flag?
- Should there be a `__main__.py` file?
- How are arguments passed to the module?

**Actions:**
- [ ] Read `template_create_orchestrator.py` to find entry point
- [ ] Check if module has proper structure for `-m` execution
- [ ] Test module execution from command line
- [ ] Document execution flow

---

## Implementation Plan

### Phase 1: Investigation & Documentation (30 min)

1. **Study Working Command Files**
   ```bash
   # Find simple working commands
   ls ~/.agentecflow/commands/*.md

   # Read debug command (known to work)
   cat ~/.agentecflow/commands/debug.md

   # Compare with template-create
   diff -u ~/.agentecflow/commands/debug.md ~/.agentecflow/commands/template-create.md | head -100
   ```

2. **Analyze Command File Structure**
   - Identify common patterns in working commands
   - Look for special markers or frontmatter
   - Check Python code block format
   - Note placement of executable code

3. **Document Findings**
   - Create comparison table
   - List differences from template-create.md
   - Identify required changes

### Phase 2: Fix Import Paths (30 min)

1. **Audit All Import Statements**
   ```bash
   # Find all Python files in orchestrator
   find ~/Projects/appmilla_github/taskwright/installer/core -name "*.py" -type f

   # Extract import statements
   grep -rn "^from " ~/Projects/appmilla_github/taskwright/installer/core/ | grep -v "__pycache__"

   # Group by import pattern
   grep -rn "^from lib\." ~/Projects/appmilla_github/taskwright/installer/core/
   grep -rn "^from installer\.global\.lib\." ~/Projects/appmilla_github/taskwright/installer/core/
   ```

2. **Fix Inconsistent Imports**
   - Choose standard pattern (likely `from lib.*` based on existing code)
   - Update all imports to use consistent pattern
   - Update PYTHONPATH to include `installer/core/`

3. **Test Import Resolution**
   ```bash
   # Test imports work with PYTHONPATH
   cd /tmp
   PYTHONPATH="/path/to/taskwright:/path/to/taskwright/installer/core" python3 -c "
   from lib.codebase_analyzer.models import CodebaseAnalysis
   from installer.core.commands.lib.template_create_orchestrator import *
   print('✅ All imports successful')
   "
   ```

### Phase 3: Fix Command File Structure (45 min)

1. **Restructure template-create.md**

   **Option A: Single Executable Python Block**
   ```markdown
   # Documentation sections
   ## Usage
   ## Features
   ## Execution Protocol

   ```python
   # ONLY executable Python code
   # NO documentation or examples
   import json
   from pathlib import Path
   # ... actual execution code
   ```

   **Option B: Separate Documentation from Code**
   ```markdown
   # Documentation
   ## Data Structures
   ```python
   # Example only (not executed)
   @dataclass
   class CodebaseAnalysis:
       ...
   ```

   ## Execution
   ```python
   # Executable code (Claude Code runs this)
   import json
   from pathlib import Path
   # ... execution code
   ```

   **Decision:** Choose Option A (single executable block) if that's what working commands use.

2. **Update PYTHONPATH Setup**
   ```python
   # Update find_taskwright_path() to return both paths
   def find_taskwright_path():
       # ... discovery logic ...
       return {
           "base": taskwright_path,
           "global": taskwright_path / "installer" / "global"
       }

   # Set both in PYTHONPATH
   paths = find_taskwright_path()
   os.environ["PYTHONPATH"] = f"{paths['base']}:{paths['global']}"

   # Or use in bash command
   cmd = f'PYTHONPATH="{paths["base"]}:{paths["global"]}" {cmd_without_env}'
   ```

3. **Remove Non-Executable Code Blocks**
   - Move data structure examples to documentation sections
   - Keep only executable code in Python block
   - Ensure Python block is at the very end

### Phase 4: Test Module Execution (15 min)

1. **Test Orchestrator Module**
   ```bash
   cd /tmp
   PYTHONPATH="/path/to/taskwright:/path/to/taskwright/installer/core" \
   python3 -m installer.core.commands.lib.template_create_orchestrator --help

   # Should show help output without errors
   ```

2. **Test From User Project**
   ```bash
   cd ~/Projects/DeCUK.Mobile.MyDrive
   PYTHONPATH="/path/to/taskwright:/path/to/taskwright/installer/core" \
   python3 -m installer.core.commands.lib.template_create_orchestrator --validate --path .

   # Should start Q&A or validation
   ```

3. **Test Command File Execution**
   ```bash
   cd ~/Projects/DeCUK.Mobile.MyDrive
   /template-create --validate

   # Should execute Python code from command file
   # Should NOT create wrapper scripts
   # Should NOT ask for user approval
   ```

---

## Technical Details

### Claude Code Command File Specification

**Format** (to be confirmed during investigation):
```markdown
# Command Title

Documentation sections explaining what the command does.

## Usage
Examples and options.

## Execution

```python
# Executable Python code
# This is what Claude Code runs when command is invoked
import sys
# ... actual code
```
```

**Key Requirements:**
- Single executable Python code block (at end?)
- No other Python code blocks (except in documentation)?
- Specific markers or frontmatter?
- Specific code block syntax?

### PYTHONPATH Configuration

**Two locations needed:**
1. **Base**: `/path/to/taskwright`
   - For imports like: `from installer.core.lib.* import *`

2. **Global**: `/path/to/taskwright/installer/core`
   - For imports like: `from lib.codebase_analyzer.models import *`

**Setting in bash command:**
```bash
PYTHONPATH="/path/to/taskwright:/path/to/taskwright/installer/core" python3 -m ...
```

### Import Pattern Standards

**Current patterns found:**
- `from lib.codebase_analyzer.models import X` (most files)
- `from installer.core.lib.codebase_analyzer.models import X` (some files)
- `from .models import X` (relative imports)

**Standard pattern** (to be decided):
- Use `from lib.*` throughout
- Requires PYTHONPATH to include `installer/core/`

---

## Testing Strategy

### Test Case 1: Command File Execution
```bash
cd ~/Projects/DeCUK.Mobile.MyDrive
/template-create --validate

# Expected:
# ✅ Python code from command file executes immediately
# ✅ No wrapper scripts created
# ✅ No user approval prompts
# ✅ PYTHONPATH discovery runs
# ✅ Orchestrator starts without import errors
```

### Test Case 2: Import Resolution
```bash
cd /tmp
PYTHONPATH="<discovered_paths>" python3 -m installer.core.commands.lib.template_create_orchestrator --help

# Expected:
# ✅ Module loads successfully
# ✅ No import errors
# ✅ Help output displayed
```

### Test Case 3: Agent Invocation
```bash
cd ~/Projects/test-project
/template-create --validate --skip-qa

# Expected:
# ✅ Codebase analyzed
# ✅ Exit code 42 (agent invocation needed)
# ✅ .agent-request.json created
# ✅ Command waits for agent response
```

### Test Case 4: Complete Flow
```bash
cd ~/Projects/DeCUK.Mobile.MyDrive
/template-create --validate

# Expected:
# ✅ Q&A session runs
# ✅ Codebase analyzed
# ✅ Agents invoked (multiple iterations)
# ✅ Template created successfully
# ✅ Validation report generated
```

---

## Definition of Done

- [ ] Claude Code executes Python code from command file (verified)
- [ ] No wrapper scripts created in /tmp (verified)
- [ ] All import errors fixed (all modules load successfully)
- [ ] PYTHONPATH includes both required locations
- [ ] Orchestrator runs without errors from any directory
- [ ] `/template-create --validate` completes successfully
- [ ] Agent invocation works (exit code 42 handled)
- [ ] Documentation updated with correct command file format
- [ ] Import conventions documented
- [ ] All changes committed to git

---

## Related Tasks

- TASK-BRIDGE-001: Agent Bridge Infrastructure (COMPLETED)
- TASK-BRIDGE-002: Orchestrator Integration (COMPLETED)
- TASK-BRIDGE-003: Command Integration (COMPLETED)
- TASK-BRIDGE-004: End-to-End Testing (PENDING)
- TASK-BRIDGE-005: Fix PYTHONPATH (COMPLETED)
- TASK-BRIDGE-006: Fix Command Structure (THIS TASK)

---

## References

- [TASK-BRIDGE-005 Completion Summary](../completed/TASK-BRIDGE-005/completion-summary.md)
- [Bridge Implementation Summary](../../docs/proposals/BRIDGE-IMPLEMENTATION-SUMMARY.md)
- [Technical Specification](../../docs/proposals/python-claude-bridge-technical-spec.md)
- User Bug Report: "Claude Code creating wrapper scripts instead of executing command file"

---

## Impact Assessment

**Current State (BROKEN)**:
```
User runs: /template-create --validate
Result: ❌ Wrapper script created, manual execution, approval prompts
```

**After Fix (WORKING)**:
```
User runs: /template-create --validate
Result: ✅ Direct execution, no wrappers, automatic PYTHONPATH, immediate start
```

**Benefits of Fix**:
- ✅ Proper Claude Code command integration
- ✅ No user friction (approval prompts)
- ✅ Faster execution (no script creation overhead)
- ✅ Cleaner implementation (no /tmp pollution)
- ✅ More reliable (fewer failure points)

---

## Risk Assessment

**Technical Risk**: MEDIUM
- May require restructuring entire command file
- Import path changes could break other modules
- Need to understand Claude Code's internal expectations

**Testing Risk**: LOW
- Easy to test: run command and check behavior
- Clear success criteria
- Can test each phase independently

**Deployment Risk**: LOW
- Changes only affect command file and imports
- Backward compatible (worst case: fallback to current behavior)
- No breaking changes to API or data structures

---

## Time Breakdown

- Investigation & documentation: 30 minutes
- Fix import paths: 30 minutes
- Restructure command file: 45 minutes
- Testing: 15 minutes
- **Total**: ~2 hours
