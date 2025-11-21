# PYTHONPATH Import Error - Visual Analysis

## File Location vs Import Path Mismatch

```
┌────────────────────────────────────────────────────────────────────┐
│                    INSTALLATION STRUCTURE                           │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  taskwright/                    ← PYTHONPATH must point HERE       │
│  ├── installer/                                                    │
│  │   └── global/                                                   │
│  │       ├── commands/                                            │
│  │       │   └── lib/                                             │
│  │       │       ├── template_create_orchestrator.py             │
│  │       │       └── template_qa_session.py                      │
│  │       └── lib/                                                 │
│  │           ├── codebase_analyzer/                              │
│  │           │   └── ai_analyzer.py                              │
│  │           ├── template_generator/                             │
│  │           │   └── template_generator.py                       │
│  │           └── agent_generator/                                │
│  │               └── agent_generator.py                          │
│  │                                                                 │
│  └── .git/                                                         │
│                                                                     │
│                  ⬇ install.sh copies files ⬇                      │
│                                                                     │
│  ~/.agentecflow/                ← Installed location              │
│  └── commands/                                                     │
│      └── lib/                                                      │
│          ├── template_create_orchestrator.py (COPIED)            │
│          └── template_qa_session.py          (COPIED)            │
│                                                                     │
│                  ⬇ symlink for Claude Code ⬇                      │
│                                                                     │
│  ~/.claude/                                                        │
│  └── commands/ → ~/.agentecflow/commands/    (SYMLINK)           │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

## Import Resolution Flow

```
┌────────────────────────────────────────────────────────────────────┐
│              WHAT HAPPENS WHEN ORCHESTRATOR RUNS                    │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. User executes: /template-create --name test                   │
│                                                                     │
│  2. Claude Code invokes:                                          │
│     python3 ~/.agentecflow/commands/lib/template_create_orchestrator.py
│                                                                     │
│  3. Python working directory: /user/current/directory             │
│     (wherever user ran the command from)                          │
│                                                                     │
│  4. Orchestrator line 20 executes:                                │
│     importlib.import_module('installer.global.commands.lib.template_qa_session')
│                              ^^^^^^^^^^^^^^^^                      │
│                              Needs to resolve this path            │
│                                                                     │
│  5. Python searches for 'installer' package in:                   │
│     - /user/current/directory/installer/        ❌ Not found     │
│     - /opt/homebrew/.../site-packages/installer/ ❌ Not found     │
│     - <PYTHONPATH directories>/installer/        ❓ Depends!     │
│                                                                     │
│  6. Without PYTHONPATH:                                           │
│     ModuleNotFoundError: No module named 'installer'              │
│                                                                     │
│  7. With PYTHONPATH="/path/to/taskwright":                        │
│     - Searches: /path/to/taskwright/installer/  ✅ Found!        │
│     - Imports: installer.global.commands.lib.template_qa_session  │
│     - Success! ✅                                                 │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

## Why Import Uses 'installer.global.*' Pattern

```
┌────────────────────────────────────────────────────────────────────┐
│              IMPORT DESIGN RATIONALE                                │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PROBLEM: Orchestrator needs to import modules from multiple       │
│           locations in the repo:                                   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ From: installer/global/commands/lib/                         │ │
│  │   - template_qa_session.py                                   │ │
│  │                                                               │ │
│  │ From: installer/global/lib/codebase_analyzer/               │ │
│  │   - ai_analyzer.py                                           │ │
│  │   - serializer.py                                            │ │
│  │   - models.py                                                │ │
│  │                                                               │ │
│  │ From: installer/global/lib/template_generator/              │ │
│  │   - template_generator.py                                    │ │
│  │   - completeness_validator.py                                │ │
│  │   - extended_validator.py                                    │ │
│  │   - models.py                                                │ │
│  │                                                               │ │
│  │ From: installer/global/lib/agent_generator/                 │ │
│  │   - agent_generator.py                                       │ │
│  │   - markdown_formatter.py                                    │ │
│  │                                                               │ │
│  │ From: installer/global/lib/agent_bridge/                    │ │
│  │   - invoker.py                                               │ │
│  │   - state_manager.py                                         │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  SOLUTION: Use absolute imports from 'installer' root:            │
│            installer.global.lib.codebase_analyzer.ai_analyzer     │
│                                                                     │
│  REQUIRES: PYTHONPATH includes taskwright repo directory          │
│                                                                     │
│  ALTERNATIVE (Not Used): Relative imports                         │
│  ❌ Would require:                                                │
│     - Copying ALL modules to ~/.agentecflow/commands/lib/        │
│     - Flattening namespace (lose organization)                    │
│     - Breaking development workflow                               │
│     - 50+ module files to copy and maintain                       │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

## Command Execution Flow (Expected vs Actual)

```
┌────────────────────────────────────────────────────────────────────┐
│                    EXPECTED FLOW                                    │
│              (What template-create.md Specifies)                    │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. User: /template-create --name test                            │
│           ↓                                                         │
│  2. Claude Code reads: template-create.md                          │
│           ↓                                                         │
│  3. Claude executes markdown Python code:                          │
│     ┌────────────────────────────────────────────────────┐        │
│     │ # Lines 1026-1105 in template-create.md           │        │
│     │ taskwright_path = find_taskwright_path()           │        │
│     │ os.environ["PYTHONPATH"] = str(taskwright_path)    │        │
│     │                                                     │        │
│     │ cmd = f'PYTHONPATH="{taskwright_path}" python3 ...'│        │
│     │ result = await bash(cmd, timeout=600000)           │        │
│     └────────────────────────────────────────────────────┘        │
│           ↓                                                         │
│  4. Bash executes with PYTHONPATH set:                            │
│     PYTHONPATH="/path/to/taskwright" python3 orchestrator.py      │
│           ↓                                                         │
│  5. Orchestrator imports installer.global.* modules ✅            │
│           ↓                                                         │
│  6. Template creation completes ✅                                │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│                     ACTUAL FLOW                                     │
│              (What Claude Code Actually Does)                       │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. User: /template-create --name test                            │
│           ↓                                                         │
│  2. Claude Code reads: template-create.md                          │
│           ↓                                                         │
│  3. ❌ Claude Code SKIPS Python setup code in markdown            │
│           ↓                                                         │
│  4. Claude Code finds orchestrator path:                           │
│     ~/.agentecflow/commands/lib/template_create_orchestrator.py   │
│           ↓                                                         │
│  5. Claude Code directly executes (NO PYTHONPATH):                │
│     python3 orchestrator.py --name test                            │
│           ↓                                                         │
│  6. Orchestrator tries to import installer.global.* ❌            │
│           ↓                                                         │
│  7. ModuleNotFoundError: No module named 'installer' ❌           │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

## Solution: Self-Contained PYTHONPATH Setup

```
┌────────────────────────────────────────────────────────────────────┐
│              SOLUTION 2: ORCHESTRATOR SELF-SETUP                    │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Move PYTHONPATH discovery from markdown INTO orchestrator:        │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ # template_create_orchestrator.py                            │ │
│  │                                                               │ │
│  │ import sys                                                    │ │
│  │ from pathlib import Path                                     │ │
│  │                                                               │ │
│  │ def _setup_pythonpath():                                     │ │
│  │     """Find taskwright and add to sys.path"""               │ │
│  │                                                               │ │
│  │     # Try ~/.agentecflow symlink                            │ │
│  │     agentecflow = Path.home() / ".agentecflow"              │ │
│  │     if agentecflow.is_symlink():                            │ │
│  │         target = agentecflow.resolve().parent               │ │
│  │         if (target / "installer").exists():                 │ │
│  │             sys.path.insert(0, str(target))                 │ │
│  │             return                                           │ │
│  │                                                               │ │
│  │     # Try standard location                                  │ │
│  │     standard = Path.home() / "Projects" / "appmilla_github" / "taskwright"
│  │     if (standard / "installer").exists():                   │ │
│  │         sys.path.insert(0, str(standard))                   │ │
│  │         return                                               │ │
│  │                                                               │ │
│  │     raise ImportError("Cannot find taskwright")             │ │
│  │                                                               │ │
│  │ # Run BEFORE any installer.global imports                   │ │
│  │ _setup_pythonpath()                                         │ │
│  │                                                               │ │
│  │ # NOW safe to import                                         │ │
│  │ import importlib                                             │ │
│  │ _template_qa_module = importlib.import_module(              │ │
│  │     'installer.global.commands.lib.template_qa_session'     │ │
│  │ )                                                            │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  RESULT: Works regardless of how orchestrator is invoked:         │
│                                                                     │
│    ✅ python3 orchestrator.py                 (direct)            │
│    ✅ /template-create                        (via command)       │
│    ✅ PYTHONPATH=... python3 orchestrator.py  (manual override)   │
│    ✅ Works from any directory                                    │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

## Import Resolution After Fix

```
┌────────────────────────────────────────────────────────────────────┐
│           IMPORT RESOLUTION WITH SELF-SETUP                         │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Orchestrator starts:                                           │
│     python3 template_create_orchestrator.py                        │
│                                                                     │
│  2. First line runs: _setup_pythonpath()                           │
│     ↓                                                               │
│     Discovers: /Users/user/Projects/appmilla_github/taskwright    │
│     ↓                                                               │
│     Adds to sys.path: sys.path.insert(0, taskwright_path)          │
│                                                                     │
│  3. Now sys.path contains:                                         │
│     [                                                               │
│       '/Users/user/Projects/appmilla_github/taskwright',  ← NEW   │
│       '/opt/homebrew/.../python3.14',                              │
│       '/opt/homebrew/.../site-packages',                           │
│       ...                                                           │
│     ]                                                               │
│                                                                     │
│  4. Import statement executes:                                     │
│     importlib.import_module('installer.global.commands.lib.template_qa_session')
│     ↓                                                               │
│     Python searches sys.path[0]:                                   │
│     /Users/user/Projects/appmilla_github/taskwright/installer/    │
│     ↓                                                               │
│     Found! ✅                                                      │
│     /Users/.../taskwright/installer/global/commands/lib/template_qa_session.py
│                                                                     │
│  5. All subsequent installer.global.* imports work ✅             │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

## Comparison of Solutions

```
┌────────────────────────────────────────────────────────────────────┐
│                  SOLUTION COMPARISON MATRIX                         │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┬──────────┬──────┬──────────┬──────────────┐ │
│  │ Solution         │ Effort   │ Risk │ UX       │ Recommend    │ │
│  ├──────────────────┼──────────┼──────┼──────────┼──────────────┤ │
│  │ 1. Fix Claude    │ VERY HIGH│ MED  │ Perfect  │ Long-term    │ │
│  │    Code command  │ (weeks)  │      │          │ only         │ │
│  │    processing    │          │      │          │              │ │
│  ├──────────────────┼──────────┼──────┼──────────┼──────────────┤ │
│  │ 2. Self-setup    │ LOW      │ LOW  │ Good     │ ✅ YES       │ │
│  │    in orchestrator│ (1-2hrs)│      │          │ IMPLEMENT    │ │
│  │                  │          │      │          │ THIS         │ │
│  ├──────────────────┼──────────┼──────┼──────────┼──────────────┤ │
│  │ 3. Relative      │ VERY HIGH│ HIGH │ Poor     │ ❌ NO        │ │
│  │    imports       │ (days)   │      │          │              │ │
│  ├──────────────────┼──────────┼──────┼──────────┼──────────────┤ │
│  │ 4. Symlink to    │ LOW      │ HIGH │ Poor     │ ❌ NO        │ │
│  │    repo          │ (1hr)    │      │          │              │ │
│  └──────────────────┴──────────┴──────┴──────────┴──────────────┘ │
│                                                                     │
│  WINNER: Solution 2 (Self-setup in orchestrator)                  │
│                                                                     │
│  Reasons:                                                           │
│  ✅ Minimal code change (30 lines)                                │
│  ✅ Self-contained (no external dependencies)                     │
│  ✅ User-friendly (auto-discovery)                                │
│  ✅ Low risk (single file, well-tested pattern)                   │
│  ✅ Quick implementation (1-2 hours)                               │
│  ✅ Doesn't prevent future improvements                           │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

## Testing Strategy

```
┌────────────────────────────────────────────────────────────────────┐
│                     TESTING MATRIX                                  │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Test Scenarios to Verify:                                         │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ 1. Direct execution (no PYTHONPATH)                          │ │
│  │    cd /tmp                                                    │ │
│  │    /template-create --name test --dry-run                    │ │
│  │    Expected: ✅ Success                                      │ │
│  ├──────────────────────────────────────────────────────────────┤ │
│  │ 2. With manual PYTHONPATH (compatibility)                    │ │
│  │    PYTHONPATH="/path/to/taskwright" /template-create ...     │ │
│  │    Expected: ✅ Success (respects manual override)           │ │
│  ├──────────────────────────────────────────────────────────────┤ │
│  │ 3. From different directories                                 │ │
│  │    cd / && /template-create ...                              │ │
│  │    cd ~/Documents && /template-create ...                    │ │
│  │    cd ~/Projects && /template-create ...                     │ │
│  │    Expected: ✅ Success in all                               │ │
│  ├──────────────────────────────────────────────────────────────┤ │
│  │ 4. Error handling (taskwright not found)                      │ │
│  │    mv taskwright taskwright.bak                              │ │
│  │    /template-create ...                                       │ │
│  │    Expected: Clear error message with troubleshooting        │ │
│  ├──────────────────────────────────────────────────────────────┤ │
│  │ 5. Full workflow                                              │ │
│  │    /template-create --name full-test                         │ │
│  │    Expected: Complete template creation ✅                   │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

## Summary

**Problem**: Import fails because Python can't find 'installer' package

**Why**: Claude Code skips PYTHONPATH setup from command markdown

**Fix**: Add self-contained PYTHONPATH discovery to orchestrator

**Impact**: 30 lines of code, 1-2 hours work, fixes 100% of failures

**Testing**: 5 test scenarios to verify all edge cases

**Result**: `/template-create` works automatically from any directory ✅
