# File Path Mismatch: Visual Diagnosis

**Date**: 2025-11-20
**Issue**: Agent enhancement fails due to CWD mismatch between Python and Claude Code
**Duration**: 20+ attempts over 10+ days
**Status**: **ROOT CAUSE IDENTIFIED** ✅

---

## The Problem in One Diagram

```
┌─────────────────────────────────────────────────────────┐
│ WHAT WE THOUGHT WAS HAPPENING                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Python Orchestrator          Claude Code               │
│  ─────────────────            ───────────                │
│                                                          │
│  CWD: /codebase/              CWD: /codebase/           │
│       ↓                            ↓                     │
│  Write: .agent-request.json   Read: .agent-request.json │
│         ✅ MATCH ✅                                      │
│  Read:  .agent-response.json  Write: .agent-response.json│
│                                                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ WHAT IS ACTUALLY HAPPENING                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Python Orchestrator          Claude Code               │
│  ─────────────────            ───────────                │
│                                                          │
│  CWD: /DeCUK.Mobile.MyDrive/  CWD: /taskwright/         │
│       ↓                            ↓                     │
│  Write: /DeCUK.Mobile.MyDrive/ Read: /taskwright/       │
│         .agent-request.json        .agent-request.json  │
│         ❌ DIFFERENT LOCATIONS ❌                        │
│  Read:  /DeCUK.Mobile.MyDrive/ Write: /taskwright/      │
│         .agent-response.json       .agent-response.json │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Evidence

### 1. Command Output Shows Relative Path

```
⏺ Write(.agent-response.json)  # ← RELATIVE, NOT ABSOLUTE!
  ⎿  Wrote 14 lines to .agent-response.json
```

**Analysis**: Claude Code received `.agent-response.json` (relative path), which resolves based on **Claude Code's CWD**, not Python's.

---

### 2. Debug Log Shows File Not Found

```
[2025-11-20 10:27:29.813] CWD: /Users/.../DeCUK.Mobile.MyDrive
[2025-11-20 10:27:29.813] Response file path: /Users/.../DeCUK.Mobile.MyDrive/.agent-response.json
[2025-11-20 10:27:29.813] Response file exists: False  # ← NOT FOUND
[2025-11-20 10:39:54.153] INVOKER: Returning cached response
```

**Analysis**:
- Python looked in `/Users/.../DeCUK.Mobile.MyDrive/`
- File doesn't exist there
- Python used cached response from previous run (workaround)

---

### 3. Working Directory Verification

```bash
# Python Orchestrator CWD
$ cd /path/to/codebase && python3 /path/to/taskwright/...
# CWD = /path/to/codebase

# Claude Code CWD
$ pwd
/Users/richardwoollcott/Projects/appmilla_github/taskwright
# CWD = taskwright repo
```

**Analysis**: Two different processes, two different CWDs.

---

## Timeline of Failed Attempts

| Days | Attempts | What We Tried | Why It Failed |
|------|----------|---------------|---------------|
| 1-3 | 1-5 | Text instructions in prompts | Claude Code doesn't parse variable names |
| 4-6 | 6-10 | Variable naming (`codebase_dir`) | Variables invisible to Claude Code |
| 7-9 | 11-15 | Code comments | Comments don't affect execution |
| 10+ | 16-20 | "Build local, copy at end" | Changed **where templates are built**, not **where processes run** |

**Common failure mode**: Assumed we could control Claude Code's file I/O behavior through:
- Text instructions ❌
- Variable names ❌
- Comments ❌
- Output path changes ❌

**Root cause**: Claude Code's CWD is **immutable** from Python's perspective.

---

## Why "Pragmatic Fix" Failed

### What We Changed

```python
# BEFORE
def _get_output_path(self) -> Path:
    if self.config.output_location == 'local':
        return Path.home() / '.agentecflow' / 'templates' / self.template_name
    else:
        return Path(__file__).parent.parent / 'templates' / self.template_name

# AFTER
def _get_output_path(self) -> Path:
    # Always build in codebase directory first
    return self.config.codebase_path / '.template-build' / self.template_name
```

### What We Expected

- Both Python and Claude Code work in codebase directory
- File paths match
- Enhancement works

### What Actually Happened

- Changed **where templates are written**
- Did NOT change **where Python runs** (still codebase directory)
- Did NOT change **where Claude Code runs** (still taskwright repo)
- **CWD mismatch persists**

---

## The Definitive Solution

### Use System Temp Directory (Shared Location)

```python
import tempfile
import uuid

class AgentBridgeInvoker:
    def __init__(self, phase: int, phase_name: str):
        session_id = str(uuid.uuid4())[:8]
        temp_dir = Path(tempfile.gettempdir()) / "taskwright"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # These paths work from ANY working directory
        self.request_file = temp_dir / f"agent-request-{session_id}.json"
        self.response_file = temp_dir / f"agent-response-{session_id}.json"
```

### Why This Works

```
┌─────────────────────────────────────────────────────────┐
│ SOLUTION: SHARED TEMP DIRECTORY                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Python Orchestrator          Claude Code               │
│  ─────────────────            ───────────                │
│                                                          │
│  CWD: /DeCUK.Mobile.MyDrive/  CWD: /taskwright/         │
│       ↓                            ↓                     │
│  Write: /tmp/taskwright/      Read: /tmp/taskwright/    │
│         agent-request-abc.json     agent-request-abc.json│
│         ✅ SAME ABSOLUTE PATH ✅                         │
│  Read:  /tmp/taskwright/      Write: /tmp/taskwright/   │
│         agent-response-abc.json    agent-response-abc.json│
│                                                          │
│  CWD doesn't matter - both use absolute paths!          │
└─────────────────────────────────────────────────────────┘
```

**Key insight**: `/tmp/` is accessible from **any** working directory. CWD is irrelevant when using absolute paths.

---

## Benefits of Solution

| Benefit | Explanation |
|---------|-------------|
| ✅ **CWD Independent** | Works regardless of where processes run |
| ✅ **Standard Practice** | System temp is designed for IPC |
| ✅ **Cross-Platform** | Works on macOS, Linux, Windows |
| ✅ **Auto Cleanup** | OS purges /tmp/ periodically |
| ✅ **No Collisions** | UUID ensures unique filenames |
| ✅ **Minimal Changes** | Only 3 lines of code |

---

## Implementation

### Files to Change

**1. `installer/global/lib/agent_bridge/invoker.py`** (lines 112-131)

```python
# BEFORE
def __init__(
    self,
    request_file: Path = Path(".agent-request.json"),
    response_file: Path = Path(".agent-response.json"),
    ...
):
    self.request_file = request_file
    self.response_file = response_file

# AFTER
import tempfile
import uuid

def __init__(
    self,
    phase: int = 6,
    phase_name: str = "agent_generation"
):
    session_id = str(uuid.uuid4())[:8]
    temp_dir = Path(tempfile.gettempdir()) / "taskwright"
    temp_dir.mkdir(parents=True, exist_ok=True)

    self.request_file = temp_dir / f"agent-request-{session_id}.json"
    self.response_file = temp_dir / f"agent-response-{session_id}.json"
    self.phase = phase
    self.phase_name = phase_name
    self._cached_response = None
```

**2. `installer/global/commands/lib/template_create_orchestrator.py`** (lines 971-976)

```python
# BEFORE
cwd = Path.cwd()
enhancement_invoker = AgentBridgeInvoker(
    request_file=cwd / ".agent-request.json",
    response_file=cwd / ".agent-response.json",
    phase=WorkflowPhase.PHASE_7_5,
    phase_name="agent_enhancement"
)

# AFTER
enhancement_invoker = AgentBridgeInvoker(
    phase=WorkflowPhase.PHASE_7_5,
    phase_name="agent_enhancement"
)
```

---

## Verification

After implementing:

```bash
# Run template creation
/template-create /path/to/codebase

# Check temp directory
ls -la /tmp/taskwright/
# Should see:
# agent-request-abc123.json
# agent-response-abc123.json

# Verify enhancement worked
cat /path/to/output/agents/some-agent.md | wc -l
# Should show 150-250 lines (enhanced)
```

---

## Key Takeaways

1. **CWD is process-specific** - Can't be controlled from outside
2. **Relative paths are fragile** - Break across process boundaries
3. **Use absolute paths for IPC** - Eliminates CWD dependency
4. **System temp is the standard** - Designed for this exact scenario
5. **Text instructions don't control I/O** - Only code does

---

**Next Step**: Implement the temp directory solution and test with real codebase.

---

**Full Analysis**: See `TASK-FIX-AGENT-ENHANCEMENT-PROMPT-QUALITY.md` for complete root cause analysis and all attempted solutions.
