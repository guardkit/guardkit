---
id: TASK-IMP-TMPL-FIX
title: "Fix: template-create Command Orchestrator Bypass"
status: in_review
created: 2025-12-02T22:30:00Z
updated: 2025-12-02T23:00:00Z
priority: critical
task_type: implementation
tags: [template-create, regression-fix, pre-release-blocker]
related_tasks: [TASK-REV-TMPL-CMD, TASK-IMP-REVERT-V097]
review_source: TASK-REV-TMPL-CMD
commit: 773f534
---

# Implementation Task: Fix template-create Command Orchestrator Bypass

## Overview

This task implements the fix recommended by review task TASK-REV-TMPL-CMD. The `/template-create` command was bypassing its Python orchestrator because the command specification file contained ~530 lines of embedded Python pseudocode that Claude interpreted as implementation instructions.

**Status**: FIX COMMITTED (773f534), READY FOR VERIFICATION

## Root Cause (from TASK-REV-TMPL-CMD)

The file `installer/global/commands/template-create.md` had ambiguous structure:

```
Lines 1-1118:    Documentation (OK)
Lines 1119-1147: "## Execution" section header
Lines 1149-1645: ~530 lines Python pseudocode (PROBLEM)
Lines 1649-1656: "## Command Execution" section (actual command)
```

Claude would read the Python pseudocode and interpret it as "what to do" rather than recognizing it should run the Python orchestrator script.

## Fix Applied

### Change Summary

| Aspect | Before | After |
|--------|--------|-------|
| File lines | 1655 | 1126 |
| Execution sections | 2 (`## Execution` + `## Command Execution`) | 1 (`## Command Execution`) |
| Python pseudocode | 530 lines embedded | Removed |
| Command location | Line 1649 | Line 1119 |

### Exact Changes

**File**: `installer/global/commands/template-create.md`

**Deleted**: Lines 1119-1648 (530 lines)

This removed:
- `## Execution` section header (line 1119)
- `### Step 1: Parse Arguments` (lines 1123-1147)
- `### Step 2: Checkpoint-Resume Loop` (line 1149)
- Exit Code Reference table (lines 1155-1167)
- Agent Invocation Flow diagram (lines 1169-1183)
- Error Handling Strategy (lines 1185-1201)
- Python pseudocode block (lines 1203-1645):
  - PYTHONPATH discovery function
  - Exit message constants
  - Command building logic
  - Checkpoint-resume loop implementation
  - Agent request/response handling
  - Cleanup functions
  - `invoke_agent_subagent()` function

**Retained**: `## Command Execution` section (now at line 1119)

```markdown
## Command Execution

```bash
# Execute via symlinked Python script
python3 ~/.agentecflow/bin/template-create-orchestrator "$@"
```

**Note**: This command uses the orchestrator pattern with the entry point in `lib/template_create_orchestrator.py`. The symlink is created as `template-create-orchestrator` (underscores converted to hyphens for consistency).
```

### File Structure After Fix

```
installer/global/commands/template-create.md (1126 lines)
├── Lines 1-50:      Usage and command syntax
├── Lines 52-200:    Complete Workflow (8 phases)
├── Lines 201-400:   Output Structure and Command Options
├── Lines 401-600:   Understanding Boundary Sections
├── Lines 601-800:   Error Messages and Exit Codes
├── Lines 801-1000:  Agent Enhancement Integration
├── Lines 1001-1117: See Also, Related Docs, Implementation Tasks
├── Line 1118:       Horizontal rule separator
└── Lines 1119-1126: ## Command Execution (simple bash command)
```

## Verification Steps

### Step 1: Confirm File Structure

```bash
# Verify line count
wc -l installer/global/commands/template-create.md
# Expected: 1126

# Verify single Command Execution section
grep -n "## Execution\|## Command Execution" installer/global/commands/template-create.md
# Expected: 1119:## Command Execution

# Verify no Python function definitions in file
grep -c "^def \|^class " installer/global/commands/template-create.md
# Expected: 0
```

### Step 2: Test Command Invocation

```bash
# Dry run test (should invoke orchestrator, not manual file creation)
/template-create --dry-run --path /path/to/test/codebase

# Expected output pattern:
# GuardKit path: /Users/.../guardkit
# PYTHONPATH: /Users/.../guardkit
# Iteration 1: Running orchestrator...
# [orchestrator output]
```

### Step 3: Verify Orchestrator Behavior

When `/template-create` is invoked, you should see:

**EXPECTED (Correct)**:
```
⏺ Bash(PYTHONPATH="..." python3 .../template_create_orchestrator.py --path . --name test)
  ⎿  INFO:installer.global.lib.codebase_analyzer.ai_analyzer:Analyzing codebase...
     INFO:lib.codebase_analyzer.stratified_sampler:Starting stratified sampling...
     ... orchestrator output ...
     Exit code: 42 (agent invocation needed)

⏺ Read(.agent-request.json)
⏺ Task(architectural-reviewer agent...)
⏺ Write(.agent-response.json)
⏺ Bash(python3 ... --resume)
  ⎿  Template created with 90%+ confidence
```

**NOT EXPECTED (Bug still present)**:
```
⏺ Bash(ls -la ~/.agentecflow)
⏺ Read(package.json)
⏺ Read(src/App.svelte)
⏺ Write(~/.agentecflow/templates/test/manifest.json)
  ⎿  Template created with 68% confidence (heuristic fallback)
```

### Step 4: Verify Template Quality

After successful template creation:

| Metric | Expected | Bug Symptom |
|--------|----------|-------------|
| Confidence score | 90%+ | 68% (heuristic) |
| Agent count | 7-8 AI-generated | 2 manual |
| Orchestrator invoked | Yes | No |
| Exit code 42 handled | Yes | N/A |

## Scope Constraints

**IN SCOPE**:
- [x] Remove problematic pseudocode from template-create.md
- [x] Commit the change (773f534)
- [ ] Verify command works correctly (manual test required)
- [ ] Update task status to completed

**OUT OF SCOPE** (to avoid regressions):
- Do NOT modify the Python orchestrator (`template_create_orchestrator.py`)
- Do NOT modify the symlink installation (`install.sh`)
- Do NOT modify other command files
- Do NOT add new features or documentation
- Do NOT refactor the remaining documentation

## Pseudocode Preservation (Optional)

The removed pseudocode contained useful implementation reference. If needed for developer documentation, it can be preserved at:

```
docs/deep-dives/template-create-orchestration-internals.md
```

However, this is NOT required for the fix and should be done as a separate task to keep scope minimal.

## Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| Documentation loss | Low | Pseudocode was never executed, just confusing |
| Other commands affected | None | Only template-create.md modified |
| Rollback complexity | Very Low | Single `git revert` |
| New regressions | Very Low | Removing unused content, not changing behavior |

## Acceptance Criteria

1. [x] `template-create.md` has 1126 lines (not 1655)
2. [x] Single `## Command Execution` section at line 1119
3. [x] No Python pseudocode blocks in command file
4. [ ] `/template-create --dry-run` invokes Python orchestrator (manual test required)
5. [ ] Exit code 42 triggers agent invocation (manual test required)
6. [ ] Template confidence score is 90%+ (not 68%) (manual test required)
7. [x] Changes committed with appropriate message (773f534)

## Commit Message Template

```
fix(template-create): Remove pseudocode causing orchestrator bypass

The template-create.md command file contained ~530 lines of Python
pseudocode that Claude interpreted as implementation instructions,
causing it to bypass the Python orchestrator and manually create
templates with reduced quality (68% vs 90%+ confidence).

Root cause: Ambiguous file structure with "## Execution" section
containing pseudocode BEFORE "## Command Execution" section.

Fix: Removed pseudocode, leaving only the "## Command Execution"
section with the bash command to invoke the orchestrator.

Fixes: TASK-REV-TMPL-CMD
Related: TASK-IMP-REVERT-V097

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Next Steps

1. **Verify fix** - Run `/template-create --dry-run` on a test codebase
2. **Commit changes** - Use commit message template above
3. **Test on clean VM** - Verify fix works on fresh installation
4. **Close related tasks** - Mark TASK-REV-TMPL-CMD as completed
5. **Update release notes** - Note the fix in release documentation

---

**Implementation Status**: COMPLETE
**Verification Status**: PENDING MANUAL TEST
**Commit Status**: COMMITTED (773f534)
