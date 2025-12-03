# ROOT CAUSE ANALYSIS: File Path Mismatch in Agent Enhancement

**Status**: CRITICAL ARCHITECTURAL ISSUE
**Impact**: 20+ failed attempts over 10+ days
**Date**: 2025-11-20

---

## Summary

The "pragmatic fix" (build locally, copy at end) failed because **it doesn't address the root cause**: Python orchestrator and Claude Code run in **different working directories**, making **relative paths fundamentally incompatible** with the current architecture.

---

## Evidence Gathering

### 1. Command Output (test19)

```
⏺ Write(.agent-response.json)  # RELATIVE PATH - NOT ABSOLUTE!
  ⎿  Wrote 14 lines to .agent-response.json
```

**Analysis**: Despite the orchestrator writing an **absolute path** to the request file (`response_file_path: /Users/.../DeCUK.Mobile.MyDrive/.agent-response.json`), Claude Code wrote using a **relative path** (`.agent-response.json`).

### 2. Debug Log (test19)

```
[2025-11-20 10:27:29.813] CWD: /Users/.../DeCUK.Mobile.MyDrive
[2025-11-20 10:27:29.813] Response file path: /Users/.../DeCUK.Mobile.MyDrive/.agent-response.json
[2025-11-20 10:27:29.813] Response file exists: False
[2025-11-20 10:39:54.153] INVOKER: Returning cached response (67801 chars)
```

**Analysis**:
- Orchestrator **created** the path: `/Users/.../DeCUK.Mobile.MyDrive/.agent-response.json`
- Orchestrator **checked** for response at that path: **File not found**
- Orchestrator **returned cached response** from memory (meaning it ran twice)

### 3. Current Working Directory

From investigating the code:
- **Python Orchestrator CWD**: Set via `Path.cwd()` in line 971 of `template_create_orchestrator.py`
- **Claude Code CWD**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit` (the repo root)
- **Evidence**: Running `pwd` in this session confirms it

---

## Root Cause Identification

### THE FUNDAMENTAL ISSUE

```
┌─────────────────────────────────────────────────┐
│ Python Orchestrator                              │
│ CWD: /Users/.../DeCUK.Mobile.MyDrive            │
│                                                  │
│ Writes request to:                               │
│   cwd / ".agent-request.json"                    │
│   = /Users/.../DeCUK.Mobile.MyDrive/             │
│     .agent-request.json                          │
│                                                  │
│ Expects response at:                             │
│   cwd / ".agent-response.json"                   │
│   = /Users/.../DeCUK.Mobile.MyDrive/             │
│     .agent-response.json                         │
└─────────────────────────────────────────────────┘
                      ⬇️
              ❌ CWD MISMATCH ❌
                      ⬇️
┌─────────────────────────────────────────────────┐
│ Claude Code (Agent Invocation)                   │
│ CWD: /Users/.../guardkit                      │
│                                                  │
│ Reads request from:                              │
│   .agent-request.json (relative path)            │
│   = /Users/.../guardkit/.agent-request.json   │
│                                                  │
│ Writes response to:                              │
│   Write(.agent-response.json) (relative)         │
│   = /Users/.../guardkit/.agent-response.json  │
└─────────────────────────────────────────────────┘
```

**Result**:
- Request written to `/Users/.../DeCUK.Mobile.MyDrive/.agent-request.json`
- Response written to `/Users/.../guardkit/.agent-response.json`
- Orchestrator checks `/Users/.../DeCUK.Mobile.MyDrive/.agent-response.json` → **NOT FOUND**

---

## Why the "Pragmatic Fix" Didn't Work

### What We Changed

1. Modified `_get_output_path()` to always return `codebase/.template-build/{name}/`
2. Assumed both Python and Claude Code would work in the codebase directory
3. Expected file path mismatches to disappear

### Why It Failed

**The change didn't affect Claude Code's working directory!**

```python
# template_create_orchestrator.py, line 971
cwd = Path.cwd()  # ← Returns Python's CWD, not Claude Code's CWD
enhancement_invoker = AgentBridgeInvoker(
    request_file=cwd / ".agent-request.json",
    response_file=cwd / ".agent-response.json",
    ...
)
```

**Problem**: `Path.cwd()` returns **Python's** current working directory, which is set by whoever invokes the Python script (likely the codebase directory). But **Claude Code** runs in the **GuardKit repo directory** (`/Users/.../guardkit`), and we have no control over that.

**The pragmatic fix only changed WHERE templates are built**, not WHERE the processes run.

---

## Architectural Issues Uncovered

### Issue 1: Assumption of Shared CWD

The checkpoint-resume pattern assumes both processes share the same working directory:

```python
# invoker.py, line 189
self.request_file.write_text(...)  # Writes to Python's CWD
# ... exit(42) ...
# Claude Code reads from ITS CWD (NOT the same!)
```

### Issue 2: Claude Code Uses Relative Paths

The command output shows:
```
Write(.agent-response.json)  # ← RELATIVE PATH
```

This means Claude Code's `Write` tool is being called with a **relative path**, which resolves based on Claude Code's CWD, not Python's.

### Issue 3: No Variable Visibility

From the command prompt in `agent_enhancer.py`:

```python
# Line 1829
return f"""You are enhancing AI agent documentation files...

**CRITICAL FIRST STEP:**
Read the file `.agent-enhancement-data.json` to get:
...

The file is in the current working directory: `.agent-enhancement-data.json`
```

**Problem**: This instruction tells Claude Code to read from "current working directory", but:
1. Claude Code's CWD is NOT Python's CWD
2. The file is written to Python's CWD
3. Text instructions in prompts don't change where files are written

---

## Why Previous Attempts Failed (Timeline)

| Attempt | What We Tried | Why It Failed |
|---------|---------------|---------------|
| 1-5 | Text instructions in prompts | Claude Code doesn't parse variable names from prompts |
| 6-10 | Variable name changes (`codebase_dir` → `output_path`) | Variable names are invisible to Claude Code |
| 11-15 | Comments in code | Comments don't affect execution |
| 16-19 | "Build locally, copy at end" | Changed template location, not process CWDs |
| 20+ | Data file approach | Still assumes shared CWD |

**Common Thread**: All attempts assumed we could control where Claude Code writes files. **We cannot.**

---

## The Actual Problem

**Claude Code's working directory is IMMUTABLE from Python's perspective.**

When we invoke a Claude Code command:
```bash
/template-create /path/to/codebase
```

The command handler:
1. Runs Python script (CWD = codebase directory)
2. Python writes files to its CWD
3. Python exits with code 42
4. Claude Code resumes (CWD = guardkit repo)
5. Claude Code looks for files in ITS CWD
6. **MISMATCH**

---

## Solutions That WILL Work

### Solution 1: System Temp Directory with UUID ✅ RECOMMENDED

**Strategy**: Use a globally accessible location that both processes can reach.

```python
import tempfile
import uuid

class AgentBridgeInvoker:
    def __init__(self, ...):
        session_id = str(uuid.uuid4())
        temp_dir = Path(tempfile.gettempdir())

        self.request_file = temp_dir / f".agent-request-{session_id}.json"
        self.response_file = temp_dir / f".agent-response-{session_id}.json"
```

**Why it works**:
- `/tmp/` is accessible from ANY working directory
- UUID prevents collisions
- Both Python and Claude Code can read/write there
- Standard practice for IPC

**Advantages**:
- ✅ No CWD dependency
- ✅ Works across all platforms (macOS, Linux, Windows)
- ✅ Automatic cleanup (OS purges /tmp/)
- ✅ No code changes to Claude Code needed

**Implementation**:
```python
# invoker.py
import tempfile
import uuid

def __init__(self, ...):
    session_id = str(uuid.uuid4())
    base_dir = Path(tempfile.gettempdir()) / "guardkit"
    base_dir.mkdir(exist_ok=True)

    self.request_file = base_dir / f"agent-request-{session_id}.json"
    self.response_file = base_dir / f"agent-response-{session_id}.json"
```

---

### Solution 2: Orchestrator Searches Multiple Locations ⚠️ FALLBACK

**Strategy**: Have Python check multiple likely locations for the response file.

```python
def load_response(self) -> str:
    """Try multiple locations for response file."""
    search_paths = [
        self.response_file,  # Expected location (Python CWD)
        Path.cwd() / ".agent-response.json",  # Current CWD
        Path(__file__).parent / ".agent-response.json",  # Script directory
        Path.home() / ".guardkit" / ".agent-response.json",  # User directory
    ]

    for path in search_paths:
        if path.exists():
            logger.info(f"Found response at: {path}")
            response_data = json.loads(path.read_text())
            # ... parse and return ...
            path.unlink()  # Cleanup
            return response.response

    raise FileNotFoundError("Response not found in any expected location")
```

**Why it works**:
- Tolerates CWD mismatch
- Finds file wherever Claude Code wrote it

**Disadvantages**:
- ❌ Doesn't fix root cause
- ❌ Fragile (depends on knowing all possible locations)
- ❌ Cleanup complexity (multiple files might exist)

---

### Solution 3: Have Orchestrator Write Both Files 🚫 NOT RECOMMENDED

**Strategy**: Don't have Claude Code write the response file. Instead:
1. Claude Code invokes agent directly (no checkpoint-resume)
2. Claude Code returns response inline
3. Orchestrator writes both request and response

**Why we shouldn't do this**:
- ❌ Breaks checkpoint-resume pattern (no state persistence)
- ❌ Requires changes to command handler
- ❌ Loses ability to resume after crashes
- ❌ Defeats the purpose of exit code 42 architecture

---

### Solution 4: Change Command Architecture 🚫 NOT RECOMMENDED

**Strategy**: Move agent invocation inside Python, use Claude Code as a library.

**Why we shouldn't do this**:
- ❌ Requires complete redesign
- ❌ Loses Claude Code's state management
- ❌ Breaks existing workflow

---

## Recommended Solution

**USE SOLUTION 1: System Temp Directory with UUID**

### Implementation Plan

1. **Modify `AgentBridgeInvoker.__init__()` (invoker.py)**:
   ```python
   import tempfile
   import uuid

   def __init__(self, phase: int = 6, phase_name: str = "agent_generation"):
       session_id = str(uuid.uuid4())[:8]  # Short UUID for readability
       temp_dir = Path(tempfile.gettempdir()) / "guardkit"
       temp_dir.mkdir(parents=True, exist_ok=True)

       self.request_file = temp_dir / f"agent-request-{session_id}.json"
       self.response_file = temp_dir / f"agent-response-{session_id}.json"
       self.phase = phase
       self.phase_name = phase_name
       self._cached_response: Optional[str] = None
   ```

2. **Remove CWD dependency from orchestrator** (template_create_orchestrator.py, line 972):
   ```python
   # BEFORE (line 971-976):
   cwd = Path.cwd()
   enhancement_invoker = AgentBridgeInvoker(
       request_file=cwd / ".agent-request.json",
       response_file=cwd / ".agent-response.json",
       ...
   )

   # AFTER:
   enhancement_invoker = AgentBridgeInvoker(
       phase=WorkflowPhase.PHASE_7_5,
       phase_name="agent_enhancement"
   )
   ```

3. **Add cleanup in orchestrator** (after successful completion):
   ```python
   # After response is loaded
   self.request_file.unlink(missing_ok=True)
   self.response_file.unlink(missing_ok=True)
   ```

4. **Test**:
   ```bash
   /template-create /path/to/codebase
   # Check /tmp/guardkit/ for request/response files
   # Verify enhancement works
   ```

---

## Expected Outcome

**After implementing Solution 1**:

```
┌─────────────────────────────────────────────────┐
│ Python Orchestrator                              │
│ CWD: /Users/.../DeCUK.Mobile.MyDrive            │
│                                                  │
│ Writes request to:                               │
│   /tmp/guardkit/agent-request-abc123.json      │
│                                                  │
│ Expects response at:                             │
│   /tmp/guardkit/agent-response-abc123.json     │
└─────────────────────────────────────────────────┘
                      ⬇️
              ✅ SHARED LOCATION ✅
                      ⬇️
┌─────────────────────────────────────────────────┐
│ Claude Code (Agent Invocation)                   │
│ CWD: /Users/.../guardkit                      │
│                                                  │
│ Reads request from:                              │
│   /tmp/guardkit/agent-request-abc123.json      │
│   (absolute path, CWD doesn't matter)            │
│                                                  │
│ Writes response to:                              │
│   /tmp/guardkit/agent-response-abc123.json     │
│   (absolute path, CWD doesn't matter)            │
└─────────────────────────────────────────────────┘
```

**Result**: ✅ Files found, enhancement works, 20+ days of debugging resolved

---

## Lessons Learned

1. **Text instructions to AI don't control file I/O**: Variable names, comments, and prompt instructions are invisible to the execution environment.

2. **CWD is process-specific**: Each process has its own CWD, which can't be changed from outside.

3. **Use absolute paths for IPC**: Relative paths are inherently fragile across process boundaries.

4. **System temp directory is the standard solution**: `/tmp/` exists for exactly this use case.

5. **Checkpoint-resume requires shared state location**: If two processes need to communicate, they need a mutually accessible location.

---

## Next Steps

1. ✅ Implement Solution 1 (temp directory with UUID)
2. ✅ Remove CWD dependency from orchestrator
3. ✅ Test with real codebase
4. ✅ Verify cleanup works
5. ✅ Document new architecture in code comments

---

## Files to Modify

| File | Lines | Change |
|------|-------|--------|
| `installer/global/lib/agent_bridge/invoker.py` | 112-131 | Add temp directory logic to `__init__()` |
| `installer/global/commands/lib/template_create_orchestrator.py` | 971-976 | Remove manual path construction |
| `installer/global/lib/agent_bridge/invoker.py` | 233-235 | Add cleanup logic |

---

## Success Metrics

After implementation:
- ✅ Response file found on first try (no searching)
- ✅ Works regardless of CWD
- ✅ No file path mismatch errors
- ✅ Agent enhancement completes successfully
- ✅ Test19 scenario passes

---

**CONCLUSION**: The "pragmatic fix" failed because it addressed the **symptom** (template build location) rather than the **root cause** (CWD mismatch between Python and Claude Code). The definitive solution is to use a **shared temp directory** that is accessible from any working directory, eliminating CWD dependency entirely.
