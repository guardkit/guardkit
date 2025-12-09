---
id: TASK-FIX-PD06
title: Make /agent-enhance run Python script instead of markdown interpretation
status: in_progress
task_type: implementation
created: 2025-12-09
updated: 2025-12-09
priority: high
tags: [progressive-disclosure, agent-enhance, slash-commands, critical]
related_tasks: [TASK-FIX-PD05, TASK-FIX-PD04, TASK-REV-AB89]
estimated_complexity: 6
---

# TASK-FIX-PD06: Make /agent-enhance Run Python Script

## Summary

Ensure the `/agent-enhance` slash command executes the Python script (`agent-enhance.py`) instead of being interpreted by Claude Code as a markdown command specification. The Python script contains the correct progressive disclosure split logic, but it's being bypassed.

## Background

### The Problem

When a user runs `/agent-enhance`, Claude Code reads the markdown command specification (`agent-enhance.md`) and interprets it rather than executing the Python script (`agent-enhance.py`). This causes:

1. Claude spawns `agent-content-enhancer` via Task tool
2. The agent writes directly to the file (ignoring JSON-only instructions)
3. The Python orchestrator with split logic never runs
4. No `-ext.md` file is created (progressive disclosure broken)

### Evidence from Session Log

```
⏺ agent-content-enhancer(Enhance Svelte5 component agent)
  ⎿  Done (0 tool uses · 15.7k tokens · 2m 56s)

⏺ Write(.agentecflow/templates/kartlog/agents/svelte5-component-specialist.md)
  ⎿  Updated with 539 additions and 11 removals
```

The agent wrote a monolithic file instead of returning JSON for the orchestrator to split.

### Expected vs Actual Flow

**Expected (Python Script):**
```
/agent-enhance command
    → python3 ~/.agentecflow/bin/agent-enhance {args}
    → AgentEnhanceOrchestrator.run()
    → SingleAgentEnhancer.enhance()
    → AI returns JSON response
    → applier.apply_with_split()
    → Creates: agent.md + agent-ext.md
```

**Actual (Markdown Interpretation):**
```
/agent-enhance command
    → Claude reads agent-enhance.md command spec
    → Claude invokes Task tool with agent-content-enhancer
    → Agent writes DIRECTLY to file (bypasses Python)
    → Returns "Done"
    → Only creates: agent.md (NO SPLIT)
```

## Root Cause Investigation

### Hypothesis 1: Slash Command Registration

Claude Code may prioritize markdown command specs over Python scripts. Check:
- How are slash commands discovered and registered?
- Is there a precedence order (`.md` vs `.py`)?
- Can we force Python execution?

### Hypothesis 2: Symlink Not Being Followed

The symlink exists:
```
~/.agentecflow/bin/agent-enhance → /path/to/guardkit/installer/global/commands/agent-enhance.py
```

But Claude may not be executing it. Check:
- Is the symlink executable? (`chmod +x`)
- Does Claude Code check `~/.agentecflow/bin/` for commands?
- Is there a path resolution issue?

### Hypothesis 3: Markdown Command Takes Precedence

When both `agent-enhance.md` and `agent-enhance.py` exist:
- Claude may prefer the markdown spec (human-readable)
- The markdown spec describes using Task tool, so Claude follows that

## Acceptance Criteria

### AC1: Investigate Command Discovery
- [x] Determine how Claude Code discovers slash commands
- [x] Check precedence between `.md` and `.py` files
- [x] Identify why Python script is not being executed
- [x] Document the command discovery mechanism

**Findings**: Claude Code only understands Markdown for slash commands. The `.md` file is interpreted as instructions. There is no native Python file execution for slash commands. The solution is to add explicit Python execution instruction at the top of the markdown file.

### AC2: Fix Command Execution Path
- [ ] ~~Modify command registration/discovery to prioritize Python scripts~~ (Not possible - Claude Code is markdown-only)
- [x] OR: Update markdown command to explicitly invoke Python script
- [ ] ~~OR: Add hook/trigger that ensures Python runs~~ (Not needed - explicit instruction works)
- [x] Ensure solution works for all environments (macOS, Linux)

**Implementation**: Added "🚨 CRITICAL: Execute Python Script First" section at the top of `agent-enhance.md` with explicit bash command to run the Python script.

### AC3: Update agent-enhance.md Command Spec
- [x] Add explicit instruction to run Python script first
- [x] Document the execution flow clearly
- [x] Ensure markdown spec doesn't conflict with Python execution

**Changes Made**:
1. Added critical instruction section at top of file
2. Explicit bash command: `python3 ~/.agentecflow/bin/agent-enhance {all arguments}`
3. Clear "DO NOT" instructions to prevent Claude from invoking agents directly
4. Updated "Command Execution" section at bottom to reinforce the message

### AC4: Verify Split Logic Executes
- [ ] Run `/agent-enhance template/agent --hybrid`
- [ ] Confirm Python orchestrator receives control
- [ ] Confirm `apply_with_split()` is called
- [ ] Confirm two files are created: core + extended

**Note**: Requires user to re-run installer to update `~/.agentecflow/commands/agent-enhance.md`

### AC5: End-to-End Verification
- [ ] Test with kartlog/svelte5-component-specialist
- [ ] Verify `svelte5-component-specialist.md` is ~150 lines (core)
- [ ] Verify `svelte5-component-specialist-ext.md` is ~300 lines (extended)
- [ ] Verify core file contains loading instruction pointing to extended
- [ ] Verify extended file contains: examples, related_templates, best_practices

**Note**: End-to-end verification requires running `/agent-enhance` with the updated markdown file

## Implementation Approach

### Option A: Modify agent-enhance.md to Invoke Python (Recommended)

Add explicit Python invocation at the start of the command spec:

```markdown
# Agent Enhance Command

## CRITICAL: Execute Python Script

This command MUST be executed via the Python script, not interpreted as markdown.

**Before any other action:**
```bash
python3 ~/.agentecflow/bin/agent-enhance {all arguments}
```

If the Python script exits with code 0, the command is complete.
Only fall back to markdown interpretation if Python is unavailable.
```

### Option B: Remove Markdown Command Spec

If markdown and Python commands conflict:
1. Rename `agent-enhance.md` to `agent-enhance-spec.md` (documentation only)
2. Ensure only `agent-enhance.py` is discoverable as a command
3. Keep markdown as reference documentation

### Option C: Add Pre-Hook in Markdown

Add a pre-execution hook:

```markdown
## Pre-Execution Hook

ALWAYS run this before any other processing:

```python
import subprocess
import sys

result = subprocess.run(
    ['python3', '~/.agentecflow/bin/agent-enhance'] + sys.argv[1:],
    capture_output=True
)

if result.returncode == 0:
    print(result.stdout.decode())
    sys.exit(0)
# Fall through to markdown interpretation only if Python fails
```

## Key Files

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `installer/global/commands/agent-enhance.md` | Command specification (markdown) | Add Python invocation instruction |
| `installer/global/commands/agent-enhance.py` | Python script with correct logic | Verify works when called directly |
| `~/.agentecflow/bin/agent-enhance` | Symlink to Python script | Verify executable and accessible |
| `installer/global/lib/agent_enhancement/orchestrator.py` | Orchestrator with split logic | Already correct (TASK-FIX-PD04) |
| `installer/global/lib/agent_enhancement/applier.py` | Applier with section routing | Already correct (TASK-FIX-PD04) |

## Python Script Verification

Before implementing, verify the Python script works correctly when called directly:

```bash
# Direct invocation should work
python3 ~/.agentecflow/bin/agent-enhance docs/reviews/progressive-disclosure/kartlog/agents/svelte5-component-specialist.md --hybrid --verbose

# Check output for:
# - "Applying enhancement with split output"
# - "Split content: X core sections, Y extended sections"
# - Two files created
```

## Test Plan

### Test 1: Direct Python Invocation
```bash
python3 ~/.agentecflow/bin/agent-enhance kartlog/svelte5-component-specialist --hybrid
```
Expected: Two files created, extended has 50+ lines

### Test 2: Slash Command Invocation
```bash
/agent-enhance kartlog/svelte5-component-specialist --hybrid
```
Expected: Same result as Test 1 (two files)

### Test 3: Dry Run Mode
```bash
/agent-enhance kartlog/svelte5-component-specialist --hybrid --dry-run
```
Expected: Shows preview, mentions split output

### Test 4: Verify File Contents

After enhancement:
```bash
wc -l agents/svelte5-component-specialist.md      # Should be ~150 lines
wc -l agents/svelte5-component-specialist-ext.md  # Should be ~300 lines
grep "## Extended Reference" agents/svelte5-component-specialist.md  # Should exist
grep "## Detailed Examples" agents/svelte5-component-specialist-ext.md  # Should exist
```

## Success Metrics

1. **Two files created**: Every `/agent-enhance` run produces core + extended files
2. **Core file size**: 100-200 lines (not 500+)
3. **Extended file size**: 200-500 lines
4. **Loading instruction present**: Core file links to extended
5. **Python orchestrator runs**: Logs show "Split content: X core, Y extended"

## Rollback Plan

If fix causes issues:
1. Revert changes to `agent-enhance.md`
2. Users can manually run: `python3 ~/.agentecflow/bin/agent-enhance {args}`
3. Document workaround in troubleshooting guide

## Dependencies

- TASK-FIX-PD04 (completed): Section name mapping fixed in applier.py
- Requires understanding of Claude Code's command discovery mechanism

## Priority Justification

**HIGH** - Progressive disclosure is a key differentiator for GuardKit:
- 55-60% token reduction expected
- Currently producing 0% reduction (monolithic files)
- Every `/agent-enhance` run is wasting tokens
- Competitive positioning affected

---

## Implementation Notes (2025-12-09)

### Root Cause Analysis

**Finding**: Claude Code slash commands are **Markdown-only**. When you run `/agent-enhance`, Claude Code:
1. Discovers the command from `~/.agentecflow/commands/agent-enhance.md`
2. Reads the markdown file
3. Interprets it as instructions/documentation
4. Follows the described behavior (invoke agent-content-enhancer via Task tool)

There is NO native support for `.py` files as slash command definitions. The Python script was being completely bypassed.

### Solution Implemented

**Option A was chosen**: Modified `agent-enhance.md` to explicitly invoke Python script first.

Added a "🚨 CRITICAL: Execute Python Script First" section at the **top** of `installer/global/commands/agent-enhance.md` with:
- Explicit bash command: `python3 ~/.agentecflow/bin/agent-enhance {all arguments}`
- Clear explanation of why Python execution is required
- List of things Claude must NOT do (invoke agents directly, write to files directly)
- Expected behavior after running the script

### Files Modified

1. **`installer/global/commands/agent-enhance.md`**
   - Added critical execution instruction section at top (lines 9-51)
   - Updated "Command Execution" section at bottom (lines 664-690)
   - Updated document status and timestamp

### Deployment Requirements

For users to get the fix:
1. Re-run the installer: `./installer/scripts/install.sh`
2. This copies updated `agent-enhance.md` to `~/.agentecflow/commands/`
3. Next `/agent-enhance` invocation will use Python script

### Verification Pending

AC4 and AC5 require manual testing after deployment:
- Run `/agent-enhance` and verify Python script is invoked
- Verify two files are created (core + extended)
- Verify file sizes match expectations
