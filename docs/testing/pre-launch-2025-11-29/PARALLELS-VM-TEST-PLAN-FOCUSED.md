# TaskWright Pre-Launch Test Plan - FOCUSED (Recent Changes Only)

**Created**: 2025-11-29
**Platform**: macOS Parallels Virtual Machine (clean slate)
**Duration**: 1.5-2 hours (streamlined)
**Goal**: Validate ONLY recent changes before public launch

---

## What We're Testing (Recent Changes Only)

### Recent Changes to Validate ✅

1. **BDD Mode Restoration** (TASK-BDD-001 to BDD-005)
   - `--mode=bdd` flag with RequireKit detection
   - Error messages when RequireKit not installed
   - BDD workflow routing to bdd-generator
   - Integration with RequireKit's Gherkin scenarios

2. **Template Init Greenfield Q&A** (if recently changed)
   - Interactive questions during `taskwright init`
   - Configuration generation based on answers
   - Template customization workflow

3. **Subagent Discovery Enforcement** (if recently changed)
   - Stack detection and agent routing
   - Discovery precedence (local > user > universal > global > template)
   - Agent selection feedback

4. **Conductor Integration Changes**
   - State symlinks working across worktrees
   - Task completion in parallel worktrees
   - No file conflicts

### What We're NOT Testing ❌

1. **Hash-based Task IDs** - Stable, well-documented, working fine
2. **Quality Gates (Phase 2.5, 4.5)** - Existing functionality, not changed
3. **Basic task workflow** - Core functionality, stable
4. **Agent enhancement** - Not recently changed

---

## Test Environment Setup (5 min)

### VM Configuration

**Recommended**:
- **OS**: macOS Sonoma
- **RAM**: 8GB minimum
- **Disk**: 50GB
- **Network**: Shared network

**Pre-Test Snapshot**: "Pre-TaskWright-Install"

---

## Streamlined Test Plan (1.5-2 hours)

### Phase 1: Installation (20 min)

**Objective**: Clean install on fresh VM

```bash
# Install prerequisites
xcode-select --install
brew install python@3.11

# Install TaskWright
mkdir -p ~/Projects
cd ~/Projects
git clone https://github.com/taskwright-dev/taskwright.git
cd taskwright
chmod +x installer/scripts/install.sh
./installer/scripts/install.sh

# Verify
taskwright --version
which taskwright
ls ~/.agentecflow/

# Install RequireKit
cd ~/Projects
git clone https://github.com/requirekit/require-kit.git
cd require-kit
chmod +x installer/scripts/install.sh
./installer/scripts/install.sh

# Verify RequireKit installation
bash ~/Projects/taskwright/docs/testing/pre-launch-2025-11-29/check-requirekit.sh

# Or manually check marker file
ls ~/.agentecflow/require-kit.marker
```

**Test Checklist**:
- [ ] Both installations complete without errors
- [ ] Commands available globally
- [ ] RequireKit marker file created
- [ ] No installation warnings or failures

**Expected**: Clean installation with no issues

---

### Phase 2: Template Init Q&A Workflow (20 min)

**Objective**: Validate greenfield template initialization with Q&A

```bash
# Create new project
mkdir -p ~/Projects/test-api-service
cd ~/Projects/test-api-service
git init
git config user.name "Test User"
git config user.email "test@example.com"

# Initialize with template
taskwright init fastapi-python
```

**What to Validate**:

1. **Q&A Session Triggers**
   - System asks relevant configuration questions
   - Questions are clear and helpful
   - Default options suggested

2. **Configuration Generation**
   - Answers stored correctly
   - Template files customized based on answers
   - Project structure matches selections

3. **Expected Questions** (document what you see):
   - [ ] Project purpose/description?
   - [ ] Authentication method?
   - [ ] Database choice?
   - [ ] Testing framework?
   - [ ] Docker configuration?

**Test Checklist**:
- [ ] Q&A session appears (not silent installation)
- [ ] Questions relevant to FastAPI/Python
- [ ] Can provide answers interactively
- [ ] Generated files reflect answers
- [ ] `.claude/agents/` populated
- [ ] Project structure complete

**Screenshot**:
- Q&A session in progress
- Generated project structure
- Sample config file showing customization

**Notes**: Document the exact questions asked for documentation updates

---

### Phase 3: BDD Mode Integration (40 min)

**Objective**: Validate TASK-BDD-001 to BDD-005 changes

#### Step 3.1: Test BDD Mode WITHOUT RequireKit (5 min)

**Purpose**: Validate error handling

```bash
# Remove RequireKit marker temporarily
mv ~/.agentecflow/require-kit.marker ~/.agentecflow/require-kit.marker.backup

# Try BDD mode
cd ~/Projects/test-api-service
/task-create "Test BDD error handling"
/task-work TASK-XXXX --mode=bdd
```

**Expected Error Message**:
```
ERROR: BDD mode requires RequireKit installation

  Repository: https://github.com/requirekit/require-kit
  Installation:
    cd ~/Projects/require-kit
    ./installer/scripts/install.sh

  Alternative modes:
    /task-work TASK-XXX --mode=tdd
    /task-work TASK-XXX --mode=standard

BDD mode is designed for:
  • Agentic orchestration systems (LangGraph, state machines)
  • Safety-critical workflows (quality gates, checkpoints)
  • Formal behavior specifications (audit, compliance)

For general features, use standard or TDD modes.
```

**Test Checklist**:
- [ ] Error message displays (not crash)
- [ ] Error includes installation instructions
- [ ] Error suggests alternative modes
- [ ] Error explains when to use BDD
- [ ] Message is clear and actionable

**BUG DISCOVERED**: ⚠️ This test failed - BDD mode detected RequireKit was not available but **continued execution** instead of stopping. See [BUG-BDD-MODE-VALIDATION.md](./BUG-BDD-MODE-VALIDATION.md) for full analysis and fix.

**Root Cause**: `--mode` flag is not parsed in Step 0 of task-work.md, so BDD validation never happens.

**Screenshot**: Error message (or bug evidence if test fails again)

```bash
# Restore marker file
mv ~/.agentecflow/require-kit.marker.backup ~/.agentecflow/require-kit.marker
```

---

#### Step 3.2: Create EARS Requirement in RequireKit (10 min)

```bash
cd ~/Projects/require-kit

# Create epic
/req-create "User Authentication" type:epic
# Note the REQ ID

# Create requirement
/req-create "Login with JWT" parent:REQ-001 type:requirement
# Note the REQ ID

# Formalize with EARS
/formalize-ears REQ-002
```

**EARS Example**:
```
WHEN user submits login credentials,
WHERE account is active,
SYSTEM SHALL authenticate user,
AND system SHALL return JWT token valid for 24 hours.
```

**Test Checklist**:
- [ ] Epic created
- [ ] Requirement created
- [ ] EARS formalization works
- [ ] Requirement saved

**Screenshot**: EARS formalization session

---

#### Step 3.3: Generate Gherkin Scenarios (5 min)

```bash
# Generate BDD scenarios
/generate-bdd REQ-002
# Note the BDD ID
```

**Test Checklist**:
- [ ] Gherkin scenarios generated
- [ ] Multiple scenarios (happy path + edge cases)
- [ ] Feature file created
- [ ] Scenarios linked to requirement

**Screenshot**: Generated Gherkin scenarios

---

#### Step 3.4: Run BDD Mode WITH RequireKit (20 min)

```bash
cd ~/Projects/test-api-service

# Create task for login implementation
/task-create "Implement JWT login endpoint" task_type:implementation
```

**Edit task frontmatter**:
```markdown
---
id: TASK-XXXX
title: Implement JWT login endpoint
bdd_scenarios: [BDD-001]  # <-- ADD THIS LINE
status: backlog
created: 2025-11-29
---
```

```bash
# Run with BDD mode
/task-work TASK-XXXX --mode=bdd
```

**What to Validate**:

1. **Phase 1: Context Loading**
   ```
   Detected: BDD mode
   Validating RequireKit installation...
   ✅ RequireKit marker found

   Loading BDD scenarios: [BDD-001]
   ✅ Loaded X scenarios from RequireKit

   Stack detection: Python (FastAPI)
   BDD framework: pytest-bdd
   ```

2. **Phase 2: Planning**
   ```
   Planning implementation to satisfy scenarios:
     - Scenario 1: Successful login
     - Scenario 2: Invalid credentials
     - Scenario 3: Inactive account

   Implementation approach documented
   ```

3. **Phase 3: Implementation**
   ```
   Routing to bdd-generator agent (RequireKit)...
   ✅ Agent discovered: bdd-generator
      Source: RequireKit

   Generating step definitions...
   ✅ Created: tests/bdd/steps/test_login_steps.py
   ✅ Created: tests/bdd/features/login.feature

   Implementing to pass scenarios...
   ```

4. **Phase 4: BDD Test Execution**
   ```
   Running BDD tests...
   pytest tests/bdd/features/login.feature

   Feature: Login
     Scenario: Successful login ✅ PASSED
     Scenario: Invalid credentials ✅ PASSED
     Scenario: Inactive account ✅ PASSED

   X scenarios (X passed)
   Y steps (Y passed)
   ```

**Test Checklist**:
- [ ] RequireKit detection works
- [ ] Scenarios load from RequireKit
- [ ] bdd-generator agent invoked (not local agent)
- [ ] Step definitions generated (pytest-bdd format)
- [ ] Feature file created
- [ ] Implementation passes scenarios
- [ ] BDD tests execute in Phase 4
- [ ] All scenarios pass

**Screenshots**:
- RequireKit detection message
- Agent routing to bdd-generator
- Step definition generation
- BDD test execution output

---

### Phase 4: Subagent Discovery Validation (15 min)

**Objective**: Validate agent discovery works correctly

```bash
cd ~/Projects/test-api-service

# Create a simple Python API task
/task-create "Add health check endpoint"

# Work on it and watch agent selection
/task-work TASK-XXXX --mode=standard
```

**What to Validate**:

**Phase 3: Implementation** should show:
```
Selecting implementation agent...

Agent Discovery Results:
✅ python-api-specialist selected
   Source: global
   Stack: python
   Phase: implementation
   Capabilities: fastapi, async-patterns, pydantic

Invoking python-api-specialist...
```

**Test Checklist**:
- [ ] Stack detected correctly (Python/FastAPI)
- [ ] Appropriate agent selected (python-api-specialist)
- [ ] Agent source shown (global/user/local)
- [ ] Discovery feedback clear
- [ ] Agent actually invoked (not generic task-manager)

**Screenshot**: Agent discovery output

**Note**: If you've made recent changes to agent discovery metadata or precedence, test those. Otherwise, this is a quick validation.

---

### Phase 5: Conductor Integration (15 min)

**Objective**: Validate state management across worktrees

**Note**: This assumes you have Conductor installed. Skip if not.

```bash
cd ~/Projects/taskwright  # Main repo

# Create two test tasks
/task-create "Test conductor task 1"
/task-create "Test conductor task 2"

# Create worktrees
conductor create-workspace test-wt1 TASK-XXXX
conductor create-workspace test-wt2 TASK-YYYY

# In worktree 1
cd ../test-wt1
/task-work TASK-XXXX
/task-complete TASK-XXXX

# In worktree 2
cd ../test-wt2
/task-work TASK-YYYY
/task-complete TASK-YYYY

# Back to main
cd ~/Projects/taskwright
ls tasks/completed/

# Should see both tasks
# Verify no conflicts
git status
```

**Test Checklist**:
- [ ] Both tasks completed successfully
- [ ] Tasks appear in main repo's `tasks/completed/`
- [ ] State synced via symlinks
- [ ] No file conflicts
- [ ] Git history clean

**Screenshot**: Both completed tasks in main repo

---

## What Success Looks Like

### Critical (Must Pass)

- [ ] **BDD mode with RequireKit**: Full workflow works
- [ ] **BDD mode without RequireKit**: Clear error with instructions
- [ ] **Template init Q&A**: Questions appear and customize project
- [ ] **Installation**: Clean install on fresh VM

### High Priority (Should Pass)

- [ ] **Subagent discovery**: Correct agents selected
- [ ] **BDD scenarios**: Load from RequireKit correctly
- [ ] **Step definitions**: Generated in correct format (pytest-bdd)
- [ ] **Conductor state**: Synced across worktrees

### Medium Priority (Nice to Have)

- [ ] **Error messages**: All clear and actionable
- [ ] **Documentation accuracy**: Instructions match reality

---

## Quick Issue Categorization

**Critical** (Blocks launch):
- BDD mode doesn't work at all
- Installation fails
- RequireKit detection broken

**High** (Should fix before launch):
- Error messages unclear
- Template Q&A missing or broken
- Agent discovery routing wrong

**Medium** (Can fix post-launch):
- Documentation inaccuracies
- Edge case handling

**Low** (Future enhancement):
- UX improvements
- Additional features

---

## Time Estimate

| Phase | Estimated | Notes |
|-------|-----------|-------|
| Installation | 20 min | Both TaskWright + RequireKit |
| Template Init | 20 min | Q&A workflow |
| BDD Integration | 40 min | Full workflow + error testing |
| Subagent Discovery | 15 min | Quick validation |
| Conductor | 15 min | If available, skip if not |
| **Total** | **1.5-2 hours** | Focused on recent changes |

---

## After Testing

### If All Pass ✅

1. **Document results** in simplified template
2. **Proceed to shared agents Phase 0**
3. **Use validated workflow for demos**

### If Issues Found ⚠️

1. **Categorize** by severity
2. **Create fix tasks** for critical/high
3. **Fix critical issues**
4. **Re-test affected areas only**

---

## Simplified Results Template

```markdown
# TaskWright Focused Test Results

**Date**: _____________
**Duration**: _____________

## BDD Mode Integration
- [ ] PASS - BDD mode works with RequireKit
- [ ] PASS - Error message without RequireKit
- [ ] PASS - Scenarios load correctly
- [ ] PASS - Step definitions generated
- [ ] PASS - BDD tests execute

**Issues**:

## Template Init Q&A
- [ ] PASS - Q&A session appears
- [ ] PASS - Questions relevant
- [ ] PASS - Configuration generated
- [ ] PASS - Project structure correct

**Issues**:

## Subagent Discovery
- [ ] PASS - Stack detected
- [ ] PASS - Correct agent selected
- [ ] PASS - Discovery feedback clear

**Issues**:

## Conductor Integration
- [ ] PASS - State synced across worktrees
- [ ] PASS - No file conflicts

**Issues**:

## Overall
- [ ] READY FOR LAUNCH
- [ ] READY WITH FIXES
- [ ] NOT READY

**Critical Issues**: ___
**Fix Tasks Created**: ___

**Next Steps**:
1.
2.
3.
```

---

## Notes

- **Removed**: Hash ID testing (stable, documented)
- **Removed**: Quality gates testing (not recently changed)
- **Removed**: General task workflow (core functionality, stable)
- **Removed**: KartLog demo (optional, can do separately)

**Focus**: Only test what changed recently (BDD, template init Q&A, subagent discovery if changed, conductor if changed)

**Time Saved**: ~1-1.5 hours compared to full test plan

---

**You're ready to validate recent changes efficiently! 🚀**
