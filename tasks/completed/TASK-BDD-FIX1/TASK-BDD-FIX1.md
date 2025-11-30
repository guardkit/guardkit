---
id: TASK-BDD-FIX1
title: Fix BDD mode validation (--mode flag parsing)
status: completed
created: 2025-11-29T14:00:00Z
updated: 2025-11-30T10:57:28.841727Z
priority: high
tags: [bug, bdd-mode, validation, pre-launch]
complexity: 6
test_results:
  status: verified
  coverage: documentation_change
  last_run: 2025-11-30T10:48:41.457776Z
previous_state: backlog
state_transition_reason: "Automatic transition for task-work execution"
completed: 2025-11-30T10:57:28.841727Z
completed_location: tasks/completed/TASK-BDD-FIX1/
---

# Task: Fix BDD mode validation (--mode flag parsing)

## Description

Fix the BDD mode validation bug discovered during VM testing (Step 3.1 of FOCUSED test plan).

**Issue**: When `/task-work TASK-XXX --mode=bdd` is executed WITHOUT RequireKit installed, the system should immediately error and stop execution. Instead:
- ✅ Detects RequireKit is not available
- ❌ Shows a **warning** instead of an **error**
- ❌ **Continues execution** instead of stopping
- ❌ Proceeds with standard workflow instead of BDD workflow

**Root Cause**: Three related issues:
1. `--mode` flag is NOT parsed in Step 0 of task-work.md
2. No RequireKit validation happens when BDD mode is requested
3. BDD validation happens too late (Step 1, after task loading)

**Severity**: HIGH - Blocks BDD mode functionality entirely

**Reference**: [BUG-BDD-MODE-VALIDATION.md](../../docs/testing/pre-launch-2025-11-29/BUG-BDD-MODE-VALIDATION.md)

## Acceptance Criteria

- [ ] `--mode` flag is parsed in Step 0 (Parse and Validate Flags)
- [ ] When `--mode=bdd`, RequireKit installation is validated immediately
- [ ] If RequireKit not installed, clear error displayed with installation instructions
- [ ] Execution stops immediately (no task state changes)
- [ ] Error message suggests alternative modes (`--mode=tdd`, `--mode=standard`)
- [ ] Active mode is displayed in Step 0 output (TDD/BDD/STANDARD)
- [ ] All 4 verification tests pass (see bug doc)

## Implementation Notes

**Files to Modify**:
1. [task-work.md](../../installer/global/commands/task-work.md:560-618) - Add mode flag parsing and validation

**Changes Required** (see bug doc for full details):

1. **Parse `--mode` flag in Step 0**
2. **Validate RequireKit when `mode == "bdd"`**
3. **Display clear error** with installation instructions if not found
4. **Update flag validation** to include mode
5. **Display active mode** in Step 0 output
6. **Remove incorrect comment** at line 840

See [BUG-BDD-MODE-VALIDATION.md](../../docs/testing/pre-launch-2025-11-29/BUG-BDD-MODE-VALIDATION.md) for complete implementation details including code examples.

## Test Requirements

### Test 1: BDD Mode WITHOUT RequireKit (Should Error)
```bash
mv ~/.agentecflow/require-kit.marker.json ~/.agentecflow/require-kit.marker.json.backup
/task-create "Test"
/task-work TASK-XXX --mode=bdd
# Expected: ERROR, execution stops, no task state changes
```

### Test 2: BDD Mode WITH RequireKit (Should Work)
```bash
mv ~/.agentecflow/require-kit.marker.json.backup ~/.agentecflow/require-kit.marker.json
/task-create "Test" bdd_scenarios:[BDD-001]
/task-work TASK-XXX --mode=bdd
# Expected: BDD workflow activates, loads scenarios
```

### Test 3: TDD Mode (Should Work Without RequireKit)
```bash
/task-work TASK-XXX --mode=tdd
# Expected: TDD workflow proceeds
```

### Test 4: Standard Mode (Default)
```bash
/task-work TASK-XXX
# Expected: Standard workflow proceeds
```

## Test Execution Log

[Automatically populated by /task-work]
