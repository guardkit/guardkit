# BDD Mode Validation Bug

**Discovered**: 2025-11-29 during VM testing (Step 3.1 of FOCUSED test plan)
**Severity**: HIGH - BDD mode doesn't validate RequireKit before execution
**Status**: CONFIRMED

---

## Bug Description

When `/task-work TASK-XXX --mode=bdd` is executed **WITHOUT RequireKit installed**, the system should immediately error and stop execution.

**Expected behavior**:
```bash
/task-work TASK-001 --mode=bdd

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
    /task-work TASK-001 --mode=tdd      # Test-first development
    /task-work TASK-001 --mode=standard # Default workflow

[Execution STOPS here]
```

**Actual behavior**:
```bash
/task-work TASK-001 --mode=bdd

Creating task 001...
✅ Task created: TASK-001

Phase 1: Load Task Context
✅ Found: TASK-001.md (state: backlog)

⚠️ Note: BDD mode with Gherkin scenarios requires https://github.com/requirekit/require-kit.
This workflow will focus on BDD-style error testing patterns.

Transitioning task from backlog → in_progress...

Phase 2: Implementation Planning
...
[Execution CONTINUES incorrectly]
```

The system:
1. ✅ Detects RequireKit is not available
2. ❌ Shows a **warning** instead of an **error**
3. ❌ **Continues execution** instead of stopping
4. ❌ Proceeds with standard workflow instead of BDD workflow

---

## Root Cause Analysis

### Issue 1: --mode Flag Not Parsed in Step 0

**File**: [task-work.md](../../../installer/global/commands/task-work.md)

**Location**: Step 0 (Parse and Validate Flags) - lines 560-618

**Problem**: The `--mode` flag is **not extracted or validated** in Step 0:

```python
# Step 0: Parse and Validate Flags
# Extract flags from command
design_only = "--design-only" in user_input or "-d" in user_input
implement_only = "--implement-only" in user_input or "-i" in user_input
micro = "--micro" in user_input

# Parse documentation level flag (TASK-036)
docs_flag = None
if "--docs=minimal" in user_input:
    docs_flag = "minimal"
elif "--docs=standard" in user_input:
    docs_flag = "standard"
elif "--docs=comprehensive" in user_input:
    docs_flag = "comprehensive"

# ❌ MISSING: --mode flag parsing!
# Should have:
# mode = "standard"  # default
# if "--mode=tdd" in user_input:
#     mode = "tdd"
# elif "--mode=bdd" in user_input:
#     mode = "bdd"
```

**Impact**: The `mode` variable is never initialized, so later BDD validation checks cannot work.

### Issue 2: BDD Validation Happens Too Late

**File**: [task-work.md](../../../installer/global/commands/task-work.md)

**Location**: Step 1 (Load Task Context) - lines 836-908

**Problem**: BDD mode validation happens in **Step 1** (after task loading), not **Step 0** (flag validation):

```python
# Step 1: Load Task Context
# ...
# IF BDD MODE: Load Gherkin scenarios from RequireKit:
if mode == "bdd":  # ❌ 'mode' variable doesn't exist yet!
    # RequireKit already validated in TASK-BDD-003
    # ❌ This comment is wrong - validation never happens!

    if not task_context["bdd_scenarios"]:
        print("ERROR: BDD mode requires linked Gherkin scenarios...")
        sys.exit(1)
```

**The comment "RequireKit already validated in TASK-BDD-003" is incorrect** - no validation happens before this point.

### Issue 3: No RequireKit Installation Check

**File**: [task-work.md](../../../installer/global/commands/task-work.md)

**Expected**: Before loading BDD scenarios, should validate RequireKit is installed:

```python
if mode == "bdd":
    # ✅ Should validate RequireKit FIRST
    from installer.global.lib.feature_detection import supports_bdd

    if not supports_bdd():  # Checks ~/.agentecflow/require-kit.marker
        print("""
ERROR: BDD mode requires RequireKit installation

  Repository:
    https://github.com/requirekit/require-kit

  Installation:
    cd ~/Projects/require-kit
    ./installer/scripts/install.sh

  Verification:
    ls ~/.agentecflow/require-kit.marker

  Alternative modes:
    /task-work TASK-001 --mode=tdd
    /task-work TASK-001 --mode=standard
        """)
        sys.exit(1)

    # THEN load scenarios...
```

**Actual**: No RequireKit validation exists anywhere in the spec.

---

## Test Case That Exposed Bug

**Test**: Step 3.1 - Test BDD Mode WITHOUT RequireKit (5 min)

**Setup**:
```bash
# Remove RequireKit marker temporarily
mv ~/.agentecflow/require-kit.marker ~/.agentecflow/require-kit.marker.backup

# Create test task
cd ~/Projects/test-api-service
/task-create "Test BDD error handling"
# Created: TASK-001
```

**Execution**:
```bash
/task-work TASK-001 --mode=bdd
```

**Expected**: Immediate error and stop

**Actual**: Warning shown, but execution continued through Phase 1, Phase 2, and Phase 2.5B

**Evidence**: User provided full task-work output showing:
- Task transitioned from backlog → in_progress
- Phase 2 implementation planning started
- python-api-specialist agent selected
- Warning message displayed but ignored

---

## Impact

### User Impact
- **Silent failure**: User specifies `--mode=bdd` but gets standard workflow instead
- **Wasted time**: User proceeds through entire workflow before realizing BDD didn't run
- **Confusion**: Warning message is easy to miss in verbose output

### System Impact
- BDD mode is **non-functional** without RequireKit validation
- Users cannot use BDD mode even when RequireKit is installed (mode flag never parsed)
- Documentation claims BDD mode works but it doesn't

---

## Fix Required

### Fix 1: Parse --mode Flag in Step 0

**File**: `installer/global/commands/task-work.md`
**Section**: Step 0: Parse and Validate Flags (lines 560-618)

**Add**:
```python
# Parse mode flag (standard|tdd|bdd)
mode = "standard"  # default
if "--mode=tdd" in user_input:
    mode = "tdd"
elif "--mode=bdd" in user_input:
    mode = "bdd"
elif "--mode=standard" in user_input:
    mode = "standard"
```

### Fix 2: Validate BDD Mode Requirements in Step 0

**Add after mode parsing**:
```python
# Validate BDD mode requirements
if mode == "bdd":
    from installer.global.lib.feature_detection import supports_bdd

    if not supports_bdd():
        print("""
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
    /task-work TASK-{task_id} --mode=tdd      # Test-first development
    /task-work TASK-{task_id} --mode=standard # Default workflow

  BDD mode is designed for agentic systems, not general features.
  See: docs/guides/bdd-workflow-for-agentic-systems.md
        """)
        sys.exit(1)
```

### Fix 3: Update Flag Validation

**File**: `installer/global/commands/task-work.md`
**Section**: Step 0 - VALIDATE flag mutual exclusivity

**Update to include mode**:
```python
flags = {
    "design_only": design_only,
    "implement_only": implement_only,
    "micro": micro,
    "docs_flag": docs_flag,
    "mode": mode  # Add mode to validation
}

try:
    validate_flags(flags)
except FlagConflictError as e:
    print(str(e))
    exit(1)
```

### Fix 4: Display Mode in Step 0

**Add after workflow mode display**:
```python
# Display active mode
if mode == "tdd":
    print("🧪 Development Mode: TDD (Test-Driven Development)")
    print("   Red → Green → Refactor cycle\n")
elif mode == "bdd":
    print("📝 Development Mode: BDD (Behavior-Driven Development)")
    print("   EARS → Gherkin → Implementation workflow\n")
    print("   RequireKit integration active\n")
else:
    print("⚙️  Development Mode: STANDARD")
    print("   Traditional implementation-first approach\n")
```

### Fix 5: Remove Incorrect Comment

**File**: `installer/global/commands/task-work.md`
**Line**: 840

**Remove**:
```python
# RequireKit already validated in TASK-BDD-003  # ❌ FALSE - remove this
```

**Replace with**:
```python
# RequireKit validated in Step 0 (--mode=bdd flag parsing)  # ✅ TRUE after fix
```

---

## Verification After Fix

### Test 1: BDD Mode WITHOUT RequireKit (Should Error)

```bash
# Remove RequireKit marker
mv ~/.agentecflow/require-kit.marker ~/.agentecflow/require-kit.marker.backup

# Try BDD mode
cd ~/Projects/test-api-service
/task-create "Test BDD error handling"
/task-work TASK-001 --mode=bdd

# Expected output:
# ERROR: BDD mode requires RequireKit installation
# [Installation instructions]
# [Exit without creating task or starting workflow]
```

**Success criteria**: Command exits immediately with error, no task state changes.

### Test 2: BDD Mode WITH RequireKit (Should Work)

```bash
# Restore RequireKit marker
mv ~/.agentecflow/require-kit.marker.backup ~/.agentecflow/require-kit.marker

# Verify RequireKit installed
ls ~/.agentecflow/require-kit.marker

# Try BDD mode
cd ~/Projects/test-api-service
/task-create "Implement BDD workflow" bdd_scenarios:[BDD-001]
/task-work TASK-002 --mode=bdd

# Expected output:
# 📝 Development Mode: BDD (Behavior-Driven Development)
#    EARS → Gherkin → Implementation workflow
#    RequireKit integration active
#
# ✅ Loaded 1 BDD scenarios from RequireKit:
#    • BDD-001
#    Framework: pytest-bdd
# [Workflow proceeds with BDD implementation]
```

**Success criteria**: BDD mode activates, loads scenarios, invokes bdd-generator agent.

### Test 3: TDD Mode (Should Work Without RequireKit)

```bash
# Remove RequireKit marker (TDD doesn't need it)
mv ~/.agentecflow/require-kit.marker ~/.agentecflow/require-kit.marker.backup

# Try TDD mode
cd ~/Projects/test-api-service
/task-create "Test TDD workflow"
/task-work TASK-003 --mode=tdd

# Expected output:
# 🧪 Development Mode: TDD (Test-Driven Development)
#    Red → Green → Refactor cycle
# [Workflow proceeds with TDD implementation]
```

**Success criteria**: TDD mode works without RequireKit (doesn't validate it).

### Test 4: Standard Mode (Default)

```bash
# Remove RequireKit marker (standard mode doesn't need it)
mv ~/.agentecflow/require-kit.marker ~/.agentecflow/require-kit.marker.backup

# Try standard mode (no --mode flag)
cd ~/Projects/test-api-service
/task-create "Test standard workflow"
/task-work TASK-004

# Expected output:
# ⚙️  Development Mode: STANDARD
#    Traditional implementation-first approach
# [Workflow proceeds with standard implementation]
```

**Success criteria**: Standard mode works without RequireKit (doesn't validate it).

---

## Related Files

- **Spec**: [task-work.md](../../../installer/global/commands/task-work.md)
- **Feature Detection**: [feature_detection.py](../../../installer/global/lib/feature_detection.py)
- **Test Plan**: [PARALLELS-VM-TEST-PLAN-FOCUSED.md](./PARALLELS-VM-TEST-PLAN-FOCUSED.md) (Step 3.1)
- **BDD Workflow Guide**: [bdd-workflow-for-agentic-systems.md](../../guides/bdd-workflow-for-agentic-systems.md)

---

## Priority

**HIGH** - This bug blocks BDD mode functionality entirely:
1. BDD mode cannot work (mode flag never parsed)
2. No validation prevents user confusion (silent failure)
3. Documented feature is non-functional
4. Public launch next week requires working BDD mode

**Recommendation**: Fix before public launch. BDD mode is a differentiating feature for agentic systems.

---

## Status

- [x] Bug confirmed via VM testing
- [x] Root cause identified (3 issues: no mode parsing, no RequireKit validation, validation too late)
- [ ] Fix implemented
- [ ] Fix verified (tests 1-4 above)
- [ ] Regression testing completed
- [ ] Documentation updated

---

**Next Steps**: Create task to implement Fix 1-5 above, then re-run Step 3.1 verification.
