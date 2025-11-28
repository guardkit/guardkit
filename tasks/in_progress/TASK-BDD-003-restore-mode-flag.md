---
id: TASK-BDD-003
title: Restore --mode=bdd flag with RequireKit detection
status: in_progress
created: 2025-11-28T15:27:39.493246+00:00
updated: 2025-11-28T15:27:39.493246+00:00
priority: high
tags: [bdd-restoration, implementation, wave2]
complexity: 4
task_type: implementation
estimated_effort: 1-2 hours
wave: 2
parallel: false
implementation_method: task-work
parent_epic: bdd-restoration
depends_on: [TASK-BDD-001]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Restore --mode=bdd flag with RequireKit detection

## Context

Restore the `--mode=bdd` flag to task-work command with proper RequireKit detection using marker file pattern. This task implements the flag parsing and validation logic.

**Parent Epic**: BDD Mode Restoration
**Wave**: 2 (Implementation - sequential after Wave 1)
**Implementation**: Use `/task-work` (full quality gates)
**Depends On**: TASK-BDD-001 (investigation findings)

## Description

Add BDD mode flag to task-work command with:
1. Marker file detection (`~/.agentecflow/require-kit.marker`)
2. Clear error messages if RequireKit not installed
3. Validation of `bdd_scenarios` field in task frontmatter
4. Updated command documentation

This task does NOT implement the workflow routing - just the flag and validation.

## Acceptance Criteria

### Implementation Changes

#### 1. Update task-work.md Command Syntax

**File**: `installer/global/commands/task-work.md`

**Location**: Line 98

**Change**:
```markdown
## Command Syntax

```bash
/task-work TASK-XXX [--mode=standard|tdd|bdd] [--design-only | --implement-only | --micro] [--docs=minimal|standard|comprehensive] [other-flags...]
```
```

#### 2. Add BDD Mode Documentation

**File**: `installer/global/commands/task-work.md`

**Location**: After TDD mode section (around line 2395)

**Add**:
```markdown
#### BDD Mode (Requires RequireKit)

```bash
/task-work TASK-XXX --mode=bdd
```

**Purpose**: Behavior-Driven Development workflow for formal agentic systems

**Prerequisites**:
- RequireKit installed (checks `~/.agentecflow/require-kit.marker`)
- Task has `bdd_scenarios: [BDD-001, BDD-002]` in frontmatter

**Use for**:
- ✅ Agentic orchestration systems (LangGraph, state machines)
- ✅ Safety-critical workflows (quality gates, approval checkpoints)
- ✅ Complex behavior requirements (multi-agent coordination)
- ✅ Formal specifications (compliance, audit, traceability)
- ❌ NOT for general CRUD features or simple implementations

**Workflow**:
1. **Phase 1**: Validates RequireKit installation via marker file
2. **Phase 1**: Loads Gherkin scenarios from task frontmatter
3. **Phase 2**: Includes scenarios in planning context
4. **Phase 3**: Routes to RequireKit's bdd-generator agent
5. **Phase 3**: Generates step definitions for detected framework
6. **Phase 3**: Implements code to pass scenarios
7. **Phase 4**: Runs BDD tests (pytest-bdd, SpecFlow, Cucumber.js, etc.)
8. **Phase 4.5**: Fix loop for failing BDD tests (max 3 attempts)
9. **Phase 5**: Standard code review

**Error Handling**:

If RequireKit not installed:
```bash
/task-work TASK-042 --mode=bdd

ERROR: BDD mode requires RequireKit installation

  RequireKit provides EARS → Gherkin → Implementation workflow for
  formal behavior specifications.

  Repository:
    https://github.com/requirekit/require-kit

  Installation:
    cd ~/Projects/require-kit
    ./installer/scripts/install.sh

  Verification:
    ls ~/.agentecflow/require-kit.marker  # Should exist

  Alternative modes:
    /task-work TASK-042 --mode=tdd      # Test-first development
    /task-work TASK-042 --mode=standard # Default workflow

  BDD mode is designed for agentic systems, not general features.
  See: docs/guides/bdd-workflow-for-agentic-systems.md
```

If bdd_scenarios not linked:
```bash
/task-work TASK-042 --mode=bdd

ERROR: BDD mode requires linked Gherkin scenarios

  Task frontmatter must include bdd_scenarios field:

    ---
    id: TASK-042
    title: Implement complexity routing
    bdd_scenarios: [BDD-ORCH-001, BDD-ORCH-002]  ← Add this
    ---

  Generate scenarios in RequireKit:
    cd ~/Projects/require-kit
    /formalize-ears REQ-XXX
    /generate-bdd REQ-XXX

  Or use alternative modes:
    /task-work TASK-042 --mode=tdd
    /task-work TASK-042 --mode=standard
```

**BDD Framework Detection**:
- Python project → pytest-bdd
- .NET project → SpecFlow
- TypeScript/JavaScript → Cucumber.js
- Ruby → Cucumber

**See**: [BDD Workflow Guide](../../docs/guides/bdd-workflow-for-agentic-systems.md)
```

#### 3. Implement Mode Validation Logic

**Based on TASK-BDD-001 findings**, add validation at appropriate location:

```python
# Pseudo-code - actual location determined by TASK-BDD-001
def validate_bdd_mode(task_frontmatter):
    """
    Validate BDD mode prerequisites.

    Checks:
    1. RequireKit installed (marker file exists)
    2. Task has bdd_scenarios field
    3. Scenarios are not empty

    Raises:
        SystemExit: With detailed error message if validation fails
    """
    from pathlib import Path

    # Check 1: RequireKit marker
    marker_file = Path.home() / ".agentecflow" / "require-kit.marker"
    if not marker_file.exists():
        print(ERROR_MESSAGE_REQUIREKIT_NOT_INSTALLED)  # From spec above
        sys.exit(1)

    # Check 2: bdd_scenarios field exists
    bdd_scenarios = task_frontmatter.get("bdd_scenarios", [])
    if not bdd_scenarios:
        print(ERROR_MESSAGE_NO_SCENARIOS_LINKED)  # From spec above
        sys.exit(1)

    # Check 3: scenarios not empty
    if not isinstance(bdd_scenarios, list) or len(bdd_scenarios) == 0:
        print(ERROR_MESSAGE_NO_SCENARIOS_LINKED)
        sys.exit(1)

    return bdd_scenarios  # Return for use in workflow
```

#### 4. Add Mode to Valid Options

**Location**: Determined by TASK-BDD-001

**Change**:
```python
VALID_MODES = ["standard", "tdd", "bdd"]

def parse_mode_flag(args):
    mode = args.get("--mode", "standard")

    if mode not in VALID_MODES:
        print(f"ERROR: Invalid mode '{mode}'")
        print(f"Valid modes: {', '.join(VALID_MODES)}")
        sys.exit(1)

    return mode
```

### Testing Requirements

- [ ] Test with `--mode=bdd` and RequireKit installed
  - Should validate successfully
  - Should proceed to Phase 1

- [ ] Test with `--mode=bdd` and RequireKit NOT installed
  - Should display error message
  - Should include repo link
  - Should suggest alternative modes
  - Should exit with code 1

- [ ] Test with `--mode=bdd` and no bdd_scenarios
  - Should display error message
  - Should show frontmatter example
  - Should suggest /generate-bdd
  - Should exit with code 1

- [ ] Test with `--mode=bdd` and empty bdd_scenarios
  - Should treat same as missing

- [ ] Test with invalid mode value
  - Should list valid modes
  - Should exit with code 1

- [ ] Test standard and tdd modes still work
  - Should not be affected by BDD changes

### Documentation Updates

- [ ] Command syntax updated (line 98)
- [ ] BDD mode section added (~line 2395)
- [ ] Error messages match implementation
- [ ] Links to workflow guide included
- [ ] Examples are accurate

## Implementation Notes

### Marker File Pattern

**Why marker file**:
- Simple, reliable detection
- No dependency on package managers
- Works across all platforms
- Already used by RequireKit installer

**Marker location**: `~/.agentecflow/require-kit.marker`

**Created by**: RequireKit's `installer/scripts/install.sh`

### Feature Detection Reuse

The existing `supports_bdd()` function should be called:

```python
from lib.feature_detection import supports_bdd

if mode == "bdd" and not supports_bdd():
    # Show error message
    sys.exit(1)
```

### Error Message Design

**Principles**:
1. **Clear problem statement** - "BDD mode requires RequireKit"
2. **Why it's needed** - "EARS → Gherkin workflow"
3. **How to fix** - Repo link + installation commands
4. **Alternatives** - Suggest TDD or standard
5. **Context** - When BDD is appropriate

## Success Criteria

- [ ] `--mode=bdd` flag recognized
- [ ] Marker file check works
- [ ] Error message displays if RequireKit missing
- [ ] Error message displays if scenarios missing
- [ ] Documentation complete and accurate
- [ ] All tests pass
- [ ] Standard/TDD modes unaffected

## Related Tasks

**Depends On**: TASK-BDD-001 (must complete first)
**Blocks**: TASK-BDD-004 (workflow routing needs this)
**Wave**: 2 (sequential implementation)

## References

- [Implementation Guide](./IMPLEMENTATION-GUIDE.md)
- [BDD Restoration Guide](../../../docs/research/restoring-bdd-feature.md) (Phase 2, lines 80-137)
- [Feature Detection](../../../installer/global/lib/feature_detection.py)
- TASK-BDD-001 findings (once available)
