---
id: TASK-BDD-003
title: Restore --mode=bdd flag with RequireKit detection
status: completed
created: 2025-11-28T15:27:39.493246+00:00
updated: 2025-11-28T21:45:00.000000+00:00
completed_at: 2025-11-28T22:00:00.000000+00:00
priority: high
tags: [bdd-restoration, implementation, wave2]
complexity: 4
task_type: implementation
estimated_effort: 1-2 hours
actual_effort: 1.5 hours
wave: 2
parallel: false
implementation_method: task-work
parent_epic: bdd-restoration
depends_on: [TASK-BDD-001]
test_results:
  status: passed
  total_tests: 20
  passed: 20
  failed: 0
  coverage: 27
  last_run: 2025-11-28T22:00:00.000000+00:00
completion_metrics:
  total_duration: 6.5 hours
  implementation_time: 1.5 hours
  testing_time: 0.5 hours
  review_time: 0.5 hours
  test_iterations: 3
  final_coverage: 27
  files_created: 1
  files_modified: 2
  tests_written: 20
  lines_added: 446
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

## Implementation Summary

### Completed Changes

#### 1. Command Syntax Update ✅
- **File**: `installer/global/commands/task-work.md:98`
- **Change**: Added `--mode=standard|tdd|bdd` to command syntax
- **Status**: Complete

#### 2. BDD Mode Documentation ✅
- **File**: `installer/global/commands/task-work.md:2762-2851`
- **Added**: Complete BDD mode section with:
  - Purpose and prerequisites
  - Use cases (agentic systems, safety-critical workflows)
  - Workflow phases (1-5)
  - Error handling for RequireKit not installed
  - Error handling for missing bdd_scenarios
  - BDD framework detection (pytest-bdd, SpecFlow, Cucumber.js, Cucumber)
  - Link to workflow guide
- **Status**: Complete

#### 3. Feature Detection Validation ✅
- **File**: `installer/global/lib/feature_detection.py:106-113`
- **Verified**: `supports_bdd()` function exists and checks marker file
- **Status**: Complete (no changes needed)

#### 4. Test Suite ✅
- **File**: `tests/integration/test_bdd_mode_validation.py`
- **Created**: 20 comprehensive tests covering:
  - Marker file detection (with/without RequireKit)
  - Task frontmatter validation (bdd_scenarios field)
  - Error message structure validation
  - Mode flag parsing (standard, tdd, bdd)
  - Integration tests for complete BDD flow
  - Regression tests (standard/TDD modes unaffected)
- **Results**: 20/20 tests passing ✅
- **Coverage**: feature_detection.py 27% (covers supports_bdd path)
- **Status**: Complete

### Test Results

```
============================= test session starts ==============================
platform darwin -- Python 3.14.0, pytest-8.4.2, pluggy-1.6.0
collected 20 items

tests/integration/test_bdd_mode_validation.py::TestBDDModeValidation::test_supports_bdd_with_marker_file PASSED
tests/integration/test_bdd_mode_validation.py::TestBDDModeValidation::test_supports_bdd_without_marker_file PASSED
tests/integration/test_bdd_mode_validation.py::TestBDDModeValidation::test_is_require_kit_installed_with_marker PASSED
tests/integration/test_bdd_mode_validation.py::TestBDDModeValidation::test_is_require_kit_installed_without_marker PASSED
tests/integration/test_bdd_mode_validation.py::TestBDDModeValidation::test_marker_file_location PASSED
tests/integration/test_bdd_mode_validation.py::TestBDDModeErrorMessages::test_requirekit_not_installed_error_message PASSED
tests/integration/test_bdd_mode_validation.py::TestBDDModeErrorMessages::test_no_scenarios_linked_error_message PASSED
tests/integration/test_bdd_mode_validation.py::TestBDDModeTaskFrontmatter::test_valid_frontmatter_with_scenarios PASSED
tests/integration/test_bdd_mode_validation.py::TestBDDModeTaskFrontmatter::test_frontmatter_without_scenarios_field PASSED
tests/integration/test_bdd_mode_validation.py::TestBDDModeTaskFrontmatter::test_frontmatter_with_empty_scenarios PASSED
tests/integration/test_bdd_mode_validation.py::TestBDDModeIntegration::test_bdd_mode_detection_flow PASSED
tests/integration/test_bdd_mode_validation.py::TestBDDModeIntegration::test_bdd_mode_failure_no_marker PASSED
tests/integration/test_bdd_mode_validation.py::TestBDDModeIntegration::test_bdd_mode_failure_no_scenarios PASSED
tests/integration/test_bdd_mode_validation.py::TestModeValidation::test_valid_modes PASSED
tests/integration/test_bdd_mode_validation.py::TestModeValidation::test_invalid_mode PASSED
tests/integration/test_bdd_mode_validation.py::TestModeValidation::test_mode_default_value PASSED
tests/integration/test_bdd_mode_validation.py::TestModeValidation::test_mode_tdd_value PASSED
tests/integration/test_bdd_mode_validation.py::TestModeValidation::test_mode_bdd_value PASSED
tests/integration/test_bdd_mode_validation.py::TestRegressionPreservation::test_standard_mode_unaffected PASSED
tests/integration/test_bdd_mode_validation.py::TestRegressionPreservation::test_tdd_mode_unaffected PASSED

============================== 20 passed in 1.19s ==============================
```

### Quality Gates

- ✅ All tests passing (20/20)
- ✅ Documentation complete and accurate
- ✅ Error messages match specification
- ✅ Standard/TDD modes unaffected (regression tests pass)
- ✅ Feature detection validated
- ✅ Marker file pattern confirmed

### Implementation Notes

This implementation follows the **pure slash command pattern** discovered in TASK-BDD-001:
- No Python orchestration scripts required
- All logic documented in `task-work.md` specification
- Validation using existing `supports_bdd()` function
- Marker file detection at `~/.agentecflow/require-kit.marker`
- Consistent with TDD mode pattern

### Next Steps

**Ready for**: TASK-BDD-004 (workflow routing to bdd-generator agent)

**Blocks**: TASK-BDD-004 requires this task to be complete before implementing workflow routing logic.

### Files Changed

1. `installer/global/commands/task-work.md` - Command syntax and BDD documentation
2. `tests/integration/test_bdd_mode_validation.py` - Comprehensive test suite (NEW)
3. `tasks/in_progress/TASK-BDD-003-restore-mode-flag.md` - Task status update

### Git Commit

```
commit 812f666
feat(bdd): Restore --mode=bdd flag with RequireKit detection

Implements TASK-BDD-003: Add BDD mode flag to task-work command with proper
RequireKit detection using marker file pattern.
```

## References

- [Implementation Guide](./IMPLEMENTATION-GUIDE.md)
- [BDD Restoration Guide](../../../docs/research/restoring-bdd-feature.md) (Phase 2, lines 80-137)
- [Feature Detection](../../../installer/global/lib/feature_detection.py)
- [TASK-BDD-001 Investigation Findings](../../completed/TASK-BDD-001/TASK-BDD-001-investigation-findings.md)
