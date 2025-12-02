# Review Report: TASK-REV-TMPL-CMD

## Executive Summary

The `/template-create` command bypasses the Python orchestrator because the command specification file (`template-create.md`) contains ~500 lines of **embedded Python pseudocode** between the documentation and the actual execution command. Claude interprets this pseudocode as implementation guidance rather than understanding it should invoke the Python script.

**Root Cause**: Ambiguous command file structure with "## Execution" section containing Python pseudocode that competes with "## Command Execution" section.

**Recommended Fix**: Restructure the command file to follow the pattern used by working commands like `/agent-enhance`.

## Review Details

| Aspect | Value |
|--------|-------|
| **Mode** | Decision Analysis |
| **Depth** | Comprehensive |
| **Duration** | ~45 minutes |
| **Reviewer** | Architectural analysis |

## Findings

### Finding 1: No Changes Between v0.97 and Current

**Evidence**:
- `git diff 6c651a3..HEAD -- installer/global/commands/template-create.md` returns empty
- Both versions have identical 1655 lines
- The bypass behavior has always been a latent risk

**Implication**: The issue is not a recent regression but a structural problem that may have been masked by other factors (model version, context window, etc.).

### Finding 2: Ambiguous Section Headers

**Evidence** (lines 1119-1656):
```markdown
## Execution                    # Line 1119 - Implies "here's how to execute"
### Step 1: Parse Arguments     # Line 1123
### Step 2: Checkpoint-Resume   # Line 1149
[...500 lines of Python pseudocode...]

## Command Execution            # Line 1649 - The ACTUAL instruction
```bash
python3 ~/.agentecflow/bin/template-create-orchestrator "$@"
```

**Problem**: Two section headers both imply "how to execute" - Claude may stop at the first one and interpret the Python pseudocode as implementation instructions.

### Finding 3: Working Commands Have Different Structure

**agent-enhance.md (works consistently)**:
```
Lines 1-555: Documentation, usage, workflow
Lines 557-562: ## Command Execution with bash command
No embedded Python pseudocode
```

**template-validate.md (works consistently)**:
```
Lines 1-250: Documentation
Lines 252-259: ## Command Execution with bash command
No embedded Python pseudocode
```

**template-create.md (problematic)**:
```
Lines 1-1118: Documentation
Lines 1119-1147: ## Execution with Step 1/Step 2 headers
Lines 1149-1645: Python pseudocode block (~500 lines)
Lines 1649-1656: ## Command Execution with bash command
```

### Finding 4: Symlink Infrastructure is Correct

**Evidence**:
```bash
$ ls -la ~/.agentecflow/bin/template-create-orchestrator
lrwxr-xr-x template-create-orchestrator -> .../template_create_orchestrator.py
```

The installation and symlinks are correct - the issue is purely in how Claude interprets the command file.

### Finding 5: The Python Pseudocode is Comprehensive But Misplaced

The embedded Python pseudocode (lines 1203-1645) includes:
- Configuration constants
- Error handling logic
- Agent invocation patterns
- File I/O operations
- Checkpoint-resume flow

This is valuable implementation documentation but should NOT be in the command file where Claude interprets it as "what to do".

## Root Cause Analysis

```
                    ┌─────────────────────────────────────┐
                    │     /template-create invoked        │
                    └────────────────┬────────────────────┘
                                     │
                                     ▼
                    ┌─────────────────────────────────────┐
                    │   Claude reads template-create.md   │
                    └────────────────┬────────────────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │                         │                         │
           ▼                         ▼                         ▼
    ┌──────────────┐      ┌──────────────────┐     ┌──────────────────┐
    │ Documentation│      │  ## Execution    │     │ ## Command       │
    │ (Lines 1-1118)      │  (Line 1119)     │     │ Execution (1649) │
    └──────────────┘      └────────┬─────────┘     └──────────────────┘
                                   │
                                   ▼
                          ┌──────────────────┐
                          │  Python pseudo-  │
                          │  code (500 lines)│
                          └────────┬─────────┘
                                   │
                        CLAUDE INTERPRETS THIS
                        AS "IMPLEMENTATION STEPS"
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │   Claude manually creates templates │
                    │   instead of running orchestrator   │
                    └─────────────────────────────────────┘
```

## Recommendations

### Option A: Restructure Command File (Recommended)

**Effort**: Low (1-2 hours)
**Risk**: Low
**Impact**: High

Move the Python pseudocode to a separate documentation file and restructure the command file:

```markdown
# template-create.md (restructured)

[Lines 1-1118: Keep documentation as-is]

---

## Command Execution

**IMPORTANT**: This command MUST be executed via the Python orchestrator.

```bash
python3 ~/.agentecflow/bin/template-create-orchestrator "$@"
```

The orchestrator handles:
- AI-native codebase analysis
- Checkpoint-resume for agent invocations
- Quality validation and error handling

For implementation details, see [Template Create Orchestrator Reference](../docs/reference/template-create-orchestrator.md)

---
```

Move lines 1119-1645 to `docs/reference/template-create-orchestrator.md`.

### Option B: Add CRITICAL Section at Top of Execution

**Effort**: Very Low (15 minutes)
**Risk**: Medium (may not be sufficient)
**Impact**: Medium

Add explicit instruction at the start:

```markdown
## Execution

### CRITICAL: ORCHESTRATOR REQUIRED

**YOU MUST RUN THE PYTHON ORCHESTRATOR. DO NOT MANUALLY IMPLEMENT THESE STEPS.**

Execute immediately:
```bash
python3 ~/.agentecflow/bin/template-create-orchestrator "$@"
```

The pseudocode below is REFERENCE DOCUMENTATION ONLY.

---

### Reference: Orchestrator Implementation Details

[...existing pseudocode...]
```

### Option C: Remove Pseudocode Entirely

**Effort**: Very Low (10 minutes)
**Risk**: Low
**Impact**: High

Delete lines 1119-1645 and keep only the Command Execution section:

```markdown
## Command Execution

```bash
python3 ~/.agentecflow/bin/template-create-orchestrator "$@"
```
```

**Trade-off**: Loses implementation documentation that may be useful for debugging.

## Decision Matrix

| Option | Effort | Risk | Solves Root Cause | Preserves Docs |
|--------|--------|------|-------------------|----------------|
| A: Restructure | Low | Low | ✓ | ✓ |
| B: Add CRITICAL | Very Low | Medium | Partial | ✓ |
| C: Remove | Very Low | Low | ✓ | ✗ |

## Recommended Action

**Implement Option A** with the following steps:

1. Create `docs/reference/template-create-orchestrator.md`
2. Move lines 1119-1645 from `template-create.md` to the new file
3. Replace with simple "## Command Execution" section
4. Test on clean environment
5. Verify confidence score returns to 90%+

## Verification Criteria

After implementing the fix:

- [ ] `/template-create --name test` invokes `python3 ~/.agentecflow/bin/template-create-orchestrator`
- [ ] Console shows "Iteration 1: Running orchestrator..."
- [ ] Exit code 42 triggers agent invocation (not manual file creation)
- [ ] Confidence score is 90%+ (not 68% heuristic fallback)
- [ ] Template includes 7-8 AI-generated agents (not 2 manual agents)

## Appendix: Command File Comparison

| File | Lines | Has Pseudocode | Works Consistently |
|------|-------|----------------|-------------------|
| template-create.md | 1655 | Yes (~500 lines) | No |
| agent-enhance.md | 570 | No | Yes |
| template-validate.md | 270 | No | Yes |
| task-review.md | 781 | No | Yes |
| task-work.md | 3600 | No (structured phases) | Yes |

## Related Tasks

- **TASK-IMP-REVERT-V097**: Baseline reference
- **TASK-REV-TMPL-REGRESS**: Parent review task

---

**Review Status**: COMPLETE
**Generated**: 2025-12-02
**Next Action**: Decision checkpoint (Accept/Revise/Implement/Cancel)
