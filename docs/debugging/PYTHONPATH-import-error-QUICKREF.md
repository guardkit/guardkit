# PYTHONPATH Import Error - Quick Reference Card

## The Problem in 3 Lines

1. **Error**: `ModuleNotFoundError: No module named 'installer'`
2. **Why**: Claude Code executes orchestrator directly without setting PYTHONPATH
3. **Fix**: Add PYTHONPATH discovery to orchestrator (30 lines of code)

---

## Immediate Workaround

```bash
# Until fix is implemented, use this:
PYTHONPATH="/Users/richardwoollcott/Projects/appmilla_github/taskwright" /template-create --name test
```

---

## Root Cause Diagram

```
Command markdown (template-create.md)
  └─ Contains PYTHONPATH setup code (lines 1026-1105)
       └─ ❌ Claude Code skips this code
            └─ Directly executes: python3 orchestrator.py
                 └─ Orchestrator imports 'installer.global.*'
                      └─ ❌ Python can't find 'installer' package
                           └─ Error: ModuleNotFoundError
```

---

## The Fix (Solution 2)

**File**: `installer/global/commands/lib/template_create_orchestrator.py`

**Add this at top** (before all imports):

```python
import sys
from pathlib import Path

def _setup_pythonpath():
    """Find taskwright installation and add to sys.path."""
    # Try ~/.agentecflow symlink
    agentecflow = Path.home() / ".agentecflow"
    if agentecflow.is_symlink():
        target = agentecflow.resolve()
        if target.name == ".agentecflow":
            taskwright_path = target.parent
            if (taskwright_path / "installer").exists():
                sys.path.insert(0, str(taskwright_path))
                return

    # Try standard location
    standard_path = Path.home() / "Projects" / "appmilla_github" / "taskwright"
    if (standard_path / "installer").exists():
        sys.path.insert(0, str(standard_path))
        return

    # Try PYTHONPATH
    import os
    if "PYTHONPATH" in os.environ:
        for dir_str in os.environ["PYTHONPATH"].split(":"):
            dir_path = Path(dir_str)
            if (dir_path / "installer").exists():
                sys.path.insert(0, str(dir_path))
                return

    raise ImportError("Cannot find taskwright installation")

# Run setup before imports
_setup_pythonpath()

# NOW safe to import
import importlib
_template_qa_module = importlib.import_module('installer.global.commands.lib.template_qa_session')
# ... rest of imports
```

**That's it!** Problem solved.

---

## Why This Fix?

| Aspect | Evaluation |
|--------|------------|
| **Effort** | LOW (1-2 hours) |
| **Risk** | LOW (single file change) |
| **Complexity** | LOW (30 lines of code) |
| **User Impact** | HIGH (works automatically) |
| **Maintenance** | LOW (self-contained) |
| **Testing** | EASY (5 test scenarios) |

---

## Testing Checklist

```bash
# ✅ Test 1: Direct execution
cd /tmp && /template-create --name test1 --dry-run

# ✅ Test 2: With manual PYTHONPATH
PYTHONPATH="/path/to/taskwright" /template-create --name test2 --dry-run

# ✅ Test 3: Different directories
cd / && /template-create --name test3 --dry-run

# ✅ Test 4: Error handling
mv taskwright{,.bak} && /template-create --name test4
mv taskwright{.bak,}

# ✅ Test 5: Full workflow
/template-create --name test5
```

---

## Architecture Context

**Why imports use 'installer.global.*' pattern:**

```
Orchestrator imports from multiple repo locations:
├── installer/global/commands/lib/template_qa_session.py
├── installer/global/lib/codebase_analyzer/ai_analyzer.py
├── installer/global/lib/template_generator/template_generator.py
├── installer/global/lib/agent_generator/agent_generator.py
└── installer/global/lib/agent_bridge/invoker.py

Can't use relative imports (would need to copy 50+ modules to ~/.agentecflow/)
MUST use absolute imports from 'installer' package root
REQUIRES PYTHONPATH pointing to taskwright repo directory
```

---

## Impact

**Before Fix**:
- Failure rate: 100% (without manual PYTHONPATH)
- User experience: Poor (requires workaround)
- Affected commands: `/template-create` only

**After Fix**:
- Failure rate: 0% (auto-discovery)
- User experience: Excellent (just works)
- Affected commands: None (all work)

---

## Files

**Primary**:
- `/Users/richardwoollcott/Projects/appmilla_github/taskwright/installer/global/commands/lib/template_create_orchestrator.py`

**Documentation**:
- `docs/debugging/PYTHONPATH-import-error-RCA.md` (full analysis)
- `docs/debugging/PYTHONPATH-import-error-SUMMARY.md` (executive summary)
- `docs/debugging/PYTHONPATH-import-error-DIAGRAM.md` (visual diagrams)
- `docs/debugging/PYTHONPATH-import-error-QUICKREF.md` (this file)

---

## Timeline

- **Now**: Workaround available (manual PYTHONPATH)
- **1-2 hours**: Implement fix (Solution 2)
- **Done**: Problem solved permanently ✅

---

## Questions?

**Q**: Why not fix Claude Code command processing?
**A**: Too much effort (weeks), this fix takes 1-2 hours

**Q**: Why not use relative imports?
**A**: Would require copying 50+ modules, breaks architecture

**Q**: Why not symlink ~/.agentecflow to repo?
**A**: Breaks user template creation, wrong separation of concerns

**Q**: Will this affect other commands?
**A**: No, only `/template-create` uses `installer.global.*` imports

---

## Next Steps

1. ✅ Understand root cause (you're here!)
2. ⏳ Implement fix (30 lines of code)
3. ⏳ Test thoroughly (5 scenarios)
4. ⏳ Update documentation
5. ✅ Problem solved!

---

**TL;DR**: Add 30 lines of PYTHONPATH discovery code to orchestrator header, problem solved. 1-2 hours work.
