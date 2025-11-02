# Bidirectional Integration Testing Guide

This guide provides comprehensive testing strategies for validating the bidirectional optional integration between taskwright and require-kit.

## Overview

The bidirectional optional integration allows taskwright and require-kit to work independently with optional mutual enhancement. This testing guide ensures all three installation scenarios work correctly.

## Test Scenarios

### Scenario 1: taskwright Only (Standalone Mode)
**Goal**: Verify taskwright works without require-kit installed

**Expected Behavior**:
- Task management workflow functions
- Quality gates and testing work
- Commands gracefully handle missing require-kit features
- Users see helpful messages about installing require-kit

### Scenario 2: require-kit Only (Standalone Mode)
**Goal**: Verify require-kit works without taskwright installed

**Expected Behavior**:
- Requirements engineering functions
- Epic/Feature hierarchy management works
- BDD scenario generation works
- Users see helpful messages about installing taskwright

### Scenario 3: Both Installed (Full Agentecflow)
**Goal**: Verify full integration when both packages installed

**Expected Behavior**:
- All features from both packages available
- Feature detection recognizes both packages
- Commands use enhanced features automatically
- Complete requirements → tasks → implementation workflow

## Testing Approaches

### Option 1: Virtual Machine Testing (Recommended)

**Best for**: Clean environment, production-like testing

**Advantages**:
- Complete isolation from host system
- Can test fresh installations
- Easy to snapshot and restore
- Production-like environment

**Setup Requirements**:
- macOS VM or Windows VM (via Parallels)
- Git installed
- Python 3.7+ installed
- Claude Code (optional but recommended)

### Option 2: Isolated Testing on Host Machine

**Best for**: Quick iteration without VM overhead

**Advantages**:
- Faster than VM
- No virtualization overhead
- Good for development testing

**Disadvantages**:
- May have conflicts with existing installations
- Requires careful cleanup

### Option 3: Docker Container Testing

**Best for**: Repeatable, automated testing

**Advantages**:
- Consistent environment
- Easy to automate
- Can be part of CI/CD

**Disadvantages**:
- Claude Code integration harder to test
- Shell integration differences

## Installation Testing Procedure

### Phase 1: taskwright Only Installation

#### Step 1: Pre-Installation Checks

```bash
# Verify VM/environment is clean
ls -la ~/.agentecflow  # Should not exist
ls -la ~/.claude       # Should not exist or be empty

# Verify prerequisites
git --version          # Should be installed
python3 --version      # Should be 3.7+
pip3 --version         # Should be installed
```

#### Step 2: Clone and Install

```bash
# Clone repository
git clone https://github.com/yourusername/taskwright.git
cd taskwright

# Make installer executable
chmod +x installer/scripts/install.sh

# Run installer
./installer/scripts/install.sh
```

#### Step 3: Verify Installation

```bash
# Check agentecflow health
agentecflow doctor

# Expected output:
# ✓ Agentecflow home: /Users/[user]/.agentecflow
# ✓ Directory commands exists
# ✓ Directory agents exists
# ✓ [n] agents installed
# ✓ Commands symlinked correctly
# ✓ Agents symlinked correctly

# Verify marker file exists
cat ~/.agentecflow/taskwright.marker.json

# Expected output:
# {
#   "package": "taskwright",
#   "version": "2.0.0",
#   "provides": ["task_management", "quality_gates", ...],
#   "optional_integration": ["require-kit"],
#   "integration_model": "bidirectional_optional"
# }
```

#### Step 4: Verify Directory Structure

```bash
# Check key directories exist
ls ~/.agentecflow/commands
ls ~/.agentecflow/agents
ls ~/.agentecflow/commands/lib
ls ~/.agentecflow/templates

# Check symlinks
ls -la ~/.claude/commands  # Should point to ~/.agentecflow/commands
ls -la ~/.claude/agents    # Should point to ~/.agentecflow/agents
```

#### Step 5: Test Feature Detection

```bash
# Test feature detection library
cd ~/.agentecflow/commands/lib
python3 << 'EOF'
from feature_detection import (
    supports_requirements,
    supports_epics,
    supports_features,
    supports_bdd,
    get_available_features,
    get_installed_packages
)

print("Installed packages:", get_installed_packages())
# Expected: ['taskwright']

print("Supports requirements:", supports_requirements())
# Expected: False

print("Supports epics:", supports_epics())
# Expected: False

print("\nAvailable features:")
features = get_available_features()
for feature, available in features.items():
    status = "✓" if available else "✗"
    print(f"  {status} {feature}")

# Expected:
# ✓ task_management
# ✓ quality_gates
# ✓ architectural_review
# ✓ test_enforcement
# ✗ requirements_engineering
# ✗ bdd_generation
# ✗ epic_management
# ✗ feature_management
EOF
```

#### Step 6: Test Commands in Claude Code

Open Claude Code and test the following:

**Test 1: Basic Task Creation**
```
/task-create "Test task without requirements"
```
**Expected**: Task created successfully

**Test 2: Task Creation with Epic (Should Warn)**
```
/task-create "Test task with epic" epic:EPIC-001
```
**Expected**: Warning message:
```
⚠️  Warning: Epic linking requires require-kit to be installed
   Install: cd require-kit && ./installer/scripts/install.sh
```

**Test 3: Task Creation with Requirements (Should Warn)**
```
/task-create "Test task with requirements" requirements:[REQ-001]
```
**Expected**: Warning message about require-kit

**Test 4: Task Work (Should Use task-manager Agent)**
```
/task-work TASK-001
```
**Expected**: Uses `task-manager` agent for Phase 1 analysis (not `requirements-analyst`)

#### Step 7: Test Spec Drift Detector

```bash
# Create a test task with implementation
cd /tmp/test-project
/task-create "Test implementation"
# ... implement something ...

# Run task-work to trigger spec drift detection (Phase 5)
/task-work TASK-001
```

**Expected in Phase 5 output**:
```
📋 REQUIREMENTS COVERAGE
ℹ️  Requirements traceability unavailable
   Install require-kit for EARS requirements tracking
   cd require-kit && ./installer/scripts/install.sh
```

### Phase 2: Add require-kit (Full Integration)

#### Step 1: Install require-kit

```bash
# Clone require-kit
cd ..
git clone https://github.com/yourusername/require-kit.git
cd require-kit

# Run installer
./installer/scripts/install.sh
```

#### Step 2: Verify Both Markers Exist

```bash
# Check both marker files
ls -la ~/.agentecflow/*.marker.json

# Expected:
# taskwright.marker.json
# require-kit.marker.json

cat ~/.agentecflow/taskwright.marker.json
cat ~/.agentecflow/require-kit.marker.json
```

#### Step 3: Verify Feature Detection (Updated)

```bash
cd ~/.agentecflow/commands/lib
python3 << 'EOF'
from feature_detection import (
    supports_requirements,
    get_installed_packages,
    get_available_features
)

print("Installed packages:", get_installed_packages())
# Expected: ['taskwright', 'require-kit']

print("Supports requirements:", supports_requirements())
# Expected: True

print("\nAvailable features:")
features = get_available_features()
for feature, available in features.items():
    status = "✓" if available else "✗"
    print(f"  {status} {feature}")

# Expected: ALL features should be ✓
EOF
```

#### Step 4: Test Full Integration in Claude Code

**Test 1: Task Creation with Epic (Should Work)**
```
/task-create "Test with epic" epic:EPIC-001
```
**Expected**: Task created with epic link (no warning)

**Test 2: Task Creation with Requirements (Should Work)**
```
/task-create "Test with requirements" requirements:[REQ-001,REQ-002]
```
**Expected**: Task created with requirements linked

**Test 3: Task Work (Should Use requirements-analyst)**
```
/task-work TASK-001
```
**Expected**: Uses `requirements-analyst` agent for Phase 1 analysis

**Test 4: Spec Drift Shows Requirements**
```
/task-work TASK-001
```
**Expected in Phase 5**:
```
📋 REQUIREMENTS COVERAGE
✅ REQ-001: [requirement text]
   └─ src/implementation.ts
```

## Testing Checklist

### Pre-Installation Checklist

- [ ] VM is clean (no existing ~/.agentecflow)
- [ ] VM is clean (no existing ~/.claude or empty)
- [ ] Git installed and working
- [ ] Python 3.7+ installed
- [ ] pip3 installed and working
- [ ] Claude Code installed (optional)
- [ ] Shell is bash or zsh

### Installation Execution Checklist

**taskwright Installation:**
- [ ] Repository clones successfully
- [ ] Installer runs without errors
- [ ] All prerequisites detected (Python, pip, git)
- [ ] All directories created in ~/.agentecflow/
- [ ] Marker file created: taskwright.marker.json
- [ ] Marker file has valid JSON format
- [ ] Marker file contains correct metadata
- [ ] Symlinks created: ~/.claude/commands → ~/.agentecflow/commands
- [ ] Symlinks created: ~/.claude/agents → ~/.agentecflow/agents
- [ ] Shell integration configured (PATH updated)
- [ ] Installation summary shows correct counts

**require-kit Installation (Full Integration Test):**
- [ ] Repository clones successfully
- [ ] Installer runs without errors
- [ ] Marker file created: require-kit.marker.json
- [ ] Both marker files exist in ~/.agentecflow/
- [ ] Installation detects existing taskwright
- [ ] Shows "Full Agentecflow integration available" message

### Post-Installation Verification Checklist

- [ ] `agentecflow doctor` runs without errors
- [ ] `agentecflow doctor` shows all green checks
- [ ] `agentecflow version` shows correct version
- [ ] Commands available: agentecflow, agentec-init, af, ai
- [ ] feature_detection.py imports successfully
- [ ] supports_requirements() returns expected value
- [ ] get_installed_packages() returns correct list
- [ ] get_available_features() returns correct features

### Functional Testing Checklist (Scenario 1: taskwright Only)

**Task Creation:**
- [ ] `/task-create "Basic task"` works
- [ ] Task file created in tasks/backlog/
- [ ] Task has valid frontmatter
- [ ] `/task-create` with epic: shows warning
- [ ] `/task-create` with requirements: shows warning
- [ ] Warning message mentions require-kit installation

**Task Work:**
- [ ] `/task-work TASK-001` runs
- [ ] Uses task-manager agent (not requirements-analyst)
- [ ] Phase 1 completes without errors
- [ ] Does not attempt to load requirements files
- [ ] Quality gates work correctly
- [ ] Tests execute successfully

**Spec Drift Detection:**
- [ ] Phase 5 runs without errors
- [ ] Shows "Requirements traceability unavailable" message
- [ ] Provides helpful install message for require-kit
- [ ] Does not crash when requirements/ directory missing
- [ ] Scope creep detection still works

**Help Text:**
- [ ] `/task-create --help` shows core options
- [ ] Help text separates Core vs Integration options
- [ ] Integration options show "require-kit required" note

### Functional Testing Checklist (Scenario 3: Both Installed)

**Task Creation:**
- [ ] `/task-create "Task" epic:EPIC-001` works
- [ ] Epic link saved in frontmatter
- [ ] `/task-create` with requirements: works
- [ ] Requirements linked correctly
- [ ] No warnings shown for epic/requirements

**Task Work:**
- [ ] Uses requirements-analyst agent
- [ ] Phase 1 loads requirements successfully
- [ ] Requirements displayed in context summary
- [ ] Epic/Feature shown in context
- [ ] Full integration features available

**Spec Drift Detection:**
- [ ] Phase 5 loads requirements files
- [ ] Shows requirements coverage
- [ ] Traces requirements to implementation
- [ ] Scope creep detection works
- [ ] Compliance scoring works

**Epic/Feature Commands:**
- [ ] `/epic-create` available
- [ ] `/feature-create` available
- [ ] `/epic-status` works
- [ ] Task hierarchy works

### Edge Cases to Test

- [ ] Install taskwright, remove marker file, verify graceful degradation
- [ ] Install both, remove require-kit marker, verify fallback to standalone
- [ ] Install with existing ~/.claude/ directory
- [ ] Install with existing ~/.agentecflow/ directory
- [ ] Reinstall taskwright over existing installation
- [ ] Shell integration with zsh
- [ ] Shell integration with bash
- [ ] Commands work from subdirectories
- [ ] Commands work from project root

### Performance Testing

- [ ] Installation completes in < 2 minutes
- [ ] feature_detection calls are fast (< 100ms)
- [ ] Marker file reads don't slow down commands
- [ ] No performance regression vs monolithic version

### Cross-Platform Testing (Optional)

**macOS Testing:**
- [ ] All Scenario 1 tests pass
- [ ] All Scenario 3 tests pass
- [ ] Shell integration works (zsh default on macOS)
- [ ] Symlinks work correctly

**Linux Testing (Optional):**
- [ ] All Scenario 1 tests pass
- [ ] All Scenario 3 tests pass
- [ ] Shell integration works (bash default)
- [ ] Path handling works correctly

**Windows Testing (Optional):**
- [ ] Installation works with Git Bash
- [ ] Marker files created correctly
- [ ] Path separators handled correctly
- [ ] Symlinks work (or appropriate fallback)

## Troubleshooting Common Issues

### Issue: Marker file not created

**Symptoms**: feature_detection returns False for everything

**Solution**:
```bash
# Check if installer reached create_marker_file step
grep "Creating marker file" installer_output.log

# Manually create marker file if needed
cat > ~/.agentecflow/taskwright.marker.json << 'EOF'
{
  "package": "taskwright",
  "version": "2.0.0",
  "installed": "2025-10-28T00:00:00Z",
  "provides": ["task_management", "quality_gates"],
  "optional_integration": ["require-kit"],
  "integration_model": "bidirectional_optional"
}
EOF
```

### Issue: Commands not found in Claude Code

**Symptoms**: /task-create shows "command not found"

**Solution**:
```bash
# Verify symlinks exist
ls -la ~/.claude/commands
ls -la ~/.claude/agents

# Recreate symlinks if needed
ln -sf ~/.agentecflow/commands ~/.claude/commands
ln -sf ~/.agentecflow/agents ~/.claude/agents

# Restart Claude Code
```

### Issue: feature_detection.py import fails

**Symptoms**: Python import error

**Solution**:
```bash
# Check file exists
ls -la ~/.agentecflow/commands/lib/feature_detection.py

# Check Python can find it
cd ~/.agentecflow/commands/lib
python3 -c "import feature_detection; print('OK')"

# If fails, check Python path
python3 -c "import sys; print(sys.path)"
```

### Issue: Wrong agent selected in task-work

**Symptoms**: Uses requirements-analyst when should use task-manager

**Solution**:
```bash
# Check marker file
cat ~/.agentecflow/taskwright.marker.json

# Test feature detection directly
python3 << 'EOF'
from feature_detection import supports_requirements
print("Supports requirements:", supports_requirements())
# Should be False if taskwright only
EOF
```

## Test Report Template

```markdown
# Bidirectional Integration Test Report

**Date**: [Date]
**Tester**: [Name]
**Environment**: [macOS VM / Windows VM / Docker / Host]
**Branch/Commit**: [Git commit hash]

## Test Summary

- Scenario 1 (taskwright only): ✅/❌
- Scenario 3 (both installed): ✅/❌
- Installation: ✅/❌
- Feature Detection: ✅/❌
- Command Behavior: ✅/❌

## Detailed Results

### Pre-Installation
- VM clean: ✅/❌
- Prerequisites: ✅/❌

### Installation (taskwright)
- Clone: ✅/❌
- Install script: ✅/❌
- Marker file: ✅/❌
- Symlinks: ✅/❌

### Feature Detection
- supports_requirements(): ✅/❌ (Expected: False)
- get_installed_packages(): ✅/❌ (Expected: ['taskwright'])

### Command Testing
- /task-create basic: ✅/❌
- /task-create with epic (warning): ✅/❌
- /task-work (task-manager): ✅/❌
- Spec drift (graceful message): ✅/❌

### Installation (require-kit)
- Install script: ✅/❌
- Both markers exist: ✅/❌

### Full Integration Testing
- /task-create with epic (works): ✅/❌
- /task-work (requirements-analyst): ✅/❌
- Full features available: ✅/❌

## Issues Found

[List any issues encountered]

## Recommendations

[Any recommendations for improvements]
```

## Next Steps After Testing

1. **If tests pass**:
   - Update documentation with any clarifications
   - Create release notes
   - Push to origin/main
   - Tag release version

2. **If tests fail**:
   - Document failure scenarios
   - Create bug report with reproduction steps
   - Fix issues in new branch
   - Retest after fixes

3. **Continuous Integration**:
   - Consider adding automated tests
   - Docker-based test suite
   - CI/CD pipeline integration

## References

- [Bidirectional Integration Architecture](../architecture/bidirectional-integration.md)
- [Installation Guide](../../installer/SETUP_GUIDE.md)
- [TASK-012 Implementation Summary](../../tasks/backlog/TASK-012-shared-installation-strategy.md)
