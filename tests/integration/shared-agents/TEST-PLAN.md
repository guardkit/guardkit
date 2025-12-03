# Shared Agents Integration - Test Plan

**Based on**: TASK-ARCH-DC05 Architectural Review
**Status**: Comprehensive Testing Strategy
**Test Coverage**: 8 scenarios with automated and manual test procedures
**Related Implementation**: TASK-SHA-002 (Define Integration Test Cases)

---

## Overview

This test plan provides comprehensive testing procedures for the shared-agents architecture migration. All scenarios include:
- Prerequisites (setup requirements)
- Steps (execution procedures)
- Expected results (pass criteria)
- Verification commands (automated checks)
- Rollback procedures (cleanup steps)

---

## Test Environment Setup

### Prerequisites

**Required**:
- [ ] Fresh Ubuntu/macOS environment (or Docker container)
- [ ] Git installed
- [ ] Internet connection (for most scenarios)
- [ ] GitHub access (for downloading releases)

**Optional**:
- [ ] Network proxy/firewall for offline testing
- [ ] Multiple test users for concurrent testing

### Test Data

**Repositories**:
```bash
# Clone test repositories
git clone https://github.com/guardkit/shared-agents.git
git clone https://github.com/guardkit/guardkit.git
git clone https://github.com/requirekit/require-kit.git
```

**Test Project**:
```bash
# Create fresh test project
mkdir test-project
cd test-project
git init
```

---

## Test Scenario 1: GuardKit Standalone Installation

**Objective**: Verify GuardKit can install shared-agents independently without RequireKit.

### Prerequisites

- [ ] Fresh project directory
- [ ] No existing `.claude/` directory
- [ ] Internet connection
- [ ] GuardKit cloned

### Test Steps

1. **Initialize test project**:
   ```bash
   cd test-project
   ls -la .claude  # Should not exist
   ```

2. **Run GuardKit installer**:
   ```bash
   cd ../guardkit
   ./installer/scripts/install.sh
   ```

3. **Verify shared-agents installation**:
   ```bash
   ls -la .claude/agents/universal/
   ```

4. **Check version installed**:
   ```bash
   cat installer/shared-agents-version.txt
   # Compare with files in .claude/agents/universal/
   ```

5. **Test agent discovery**:
   ```bash
   # Create sample task
   mkdir -p tasks/backlog
   cat > tasks/backlog/TASK-TEST-001.md <<EOF
   ---
   id: TASK-TEST-001
   title: Test task
   status: backlog
   ---
   # Test Task
   Test description
   EOF

   # Run task-work (should discover universal agents)
   /task-work TASK-TEST-001
   ```

### Expected Results

- [ ] `.claude/agents/universal/` directory exists
- [ ] Shared agents present (count matches manifest.json)
- [ ] Agent files have correct version metadata
- [ ] No error messages during installation
- [ ] Agent discovery finds universal agents
- [ ] `/task-work` command executes without errors

### Verification Commands

```bash
# Check directory structure
test -d .claude/agents/universal && echo "✅ Universal agents directory exists" || echo "❌ Directory missing"

# Count agents
EXPECTED_COUNT=$(curl -sL https://github.com/guardkit/shared-agents/releases/latest/download/manifest.json | jq '.agents | length')
ACTUAL_COUNT=$(ls -1 .claude/agents/universal/*.md | wc -l)
[ "$ACTUAL_COUNT" -eq "$EXPECTED_COUNT" ] && echo "✅ Agent count matches ($ACTUAL_COUNT)" || echo "❌ Agent count mismatch (expected: $EXPECTED_COUNT, actual: $ACTUAL_COUNT)"

# Verify checksum
cd .claude/agents/universal
tar -czf /tmp/test-agents.tar.gz .
INSTALLED_CHECKSUM=$(sha256sum /tmp/test-agents.tar.gz | cut -d' ' -f1)
EXPECTED_CHECKSUM=$(curl -sL https://github.com/guardkit/shared-agents/releases/latest/download/shared-agents.tar.gz.sha256 | cut -d' ' -f1)
# Note: This is approximate - exact match requires same tar options
echo "Installed checksum: $INSTALLED_CHECKSUM"
echo "Expected checksum: $EXPECTED_CHECKSUM"
```

### Pass Criteria

- All expected results achieved ✅
- All verification commands succeed ✅
- No errors in installation logs ✅

### Rollback Procedure

```bash
rm -rf .claude/
git checkout .claude/  # If under version control
```

---

## Test Scenario 2: RequireKit Standalone Installation

**Objective**: Verify RequireKit can install shared-agents independently without GuardKit.

### Prerequisites

Same as Test Scenario 1

### Test Steps

1. **Initialize test project**:
   ```bash
   cd test-project
   ls -la .claude  # Should not exist
   ```

2. **Run RequireKit installer**:
   ```bash
   cd ../require-kit
   ./installer/scripts/install.sh
   ```

3. **Verify shared-agents installation**:
   ```bash
   ls -la .claude/agents/universal/
   ```

4. **Check version installed**:
   ```bash
   cat installer/shared-agents-version.txt
   ```

5. **Test agent discovery** (if RequireKit has similar command):
   ```bash
   # Execute RequireKit-specific command that uses agents
   # Example: /formalize-ears (if applicable)
   ```

### Expected Results

Same as Test Scenario 1 (adapted for RequireKit)

### Verification Commands

Same as Test Scenario 1

### Pass Criteria

Same as Test Scenario 1

### Rollback Procedure

Same as Test Scenario 1

---

## Test Scenario 3: Combined Installation (GuardKit First)

**Objective**: Verify both tools can coexist when GuardKit is installed first.

### Prerequisites

- [ ] Fresh project directory
- [ ] No existing `.claude/` directory
- [ ] Both GuardKit and RequireKit cloned

### Test Steps

1. **Install GuardKit first**:
   ```bash
   cd test-project
   ../guardkit/installer/scripts/install.sh
   ```

2. **Verify initial installation**:
   ```bash
   ls -la .claude/agents/universal/
   INITIAL_COUNT=$(ls -1 .claude/agents/universal/*.md | wc -l)
   echo "Initial agent count: $INITIAL_COUNT"
   ```

3. **Install RequireKit second**:
   ```bash
   ../require-kit/installer/scripts/install.sh
   ```

4. **Verify no duplication**:
   ```bash
   FINAL_COUNT=$(ls -1 .claude/agents/universal/*.md | wc -l)
   echo "Final agent count: $FINAL_COUNT"
   ```

5. **Check agent checksums** (verify they're identical):
   ```bash
   sha256sum .claude/agents/universal/*.md
   ```

6. **Test both tools independently**:
   ```bash
   # GuardKit command
   /task-status

   # RequireKit command (if applicable)
   # /req-status
   ```

### Expected Results

- [ ] `.claude/agents/universal/` has correct number of agents (not duplicated)
- [ ] `$INITIAL_COUNT == $FINAL_COUNT` (no duplication)
- [ ] Both tools work independently
- [ ] Shared agents are identical (same checksums)
- [ ] No conflicts or overwrites

### Verification Commands

```bash
# Check for duplicates
find .claude/agents/ -name "*.md" | sort | uniq -d
# Should output nothing (no duplicates)

# Verify both tools installed correctly
test -f .claude/commands/task-create.md && echo "✅ GuardKit installed"
test -f .claude/commands/formalize-ears.md && echo "✅ RequireKit installed"

# Check shared agents integrity
AGENT_COUNT=$(ls -1 .claude/agents/universal/*.md | wc -l)
[ "$AGENT_COUNT" -eq "$INITIAL_COUNT" ] && echo "✅ No duplication" || echo "❌ Agents duplicated"
```

### Pass Criteria

- No agent duplication ✅
- Both tools function correctly ✅
- Shared agents identical ✅

### Rollback Procedure

```bash
rm -rf .claude/
```

---

## Test Scenario 4: Combined Installation (RequireKit First)

**Objective**: Verify both tools can coexist when RequireKit is installed first (reverse order of Scenario 3).

### Prerequisites

Same as Test Scenario 3

### Test Steps

Same as Test Scenario 3, but reverse installation order:

1. Install RequireKit first
2. Verify initial installation
3. Install GuardKit second
4. Verify no duplication
5. Test both tools

### Expected Results

Same as Test Scenario 3

### Verification Commands

Same as Test Scenario 3

### Pass Criteria

Same as Test Scenario 3

### Rollback Procedure

Same as Test Scenario 3

---

## Test Scenario 5: Version Pinning (Different Versions)

**Objective**: Verify different tools can pin different shared-agents versions without conflicts.

### Prerequisites

- [ ] Fresh project directory
- [ ] shared-agents has multiple releases (v1.0.0, v1.1.0, etc.)
- [ ] Both tools cloned

### Test Steps

1. **Modify GuardKit version pinning**:
   ```bash
   cd guardkit
   echo "v1.0.0" > installer/shared-agents-version.txt
   ```

2. **Modify RequireKit version pinning**:
   ```bash
   cd ../require-kit
   echo "v1.1.0" > installer/shared-agents-version.txt
   ```

3. **Install GuardKit**:
   ```bash
   cd ../test-project
   ../guardkit/installer/scripts/install.sh
   ```

4. **Verify GuardKit version**:
   ```bash
   # Check agent file metadata or version marker
   head -20 .claude/agents/universal/code-reviewer.md | grep -i version
   ```

5. **Install RequireKit**:
   ```bash
   ../require-kit/installer/scripts/install.sh
   ```

6. **Verify RequireKit version**:
   ```bash
   # Same check as step 4
   head -20 .claude/agents/universal/code-reviewer.md | grep -i version
   ```

7. **Check for version mismatch warnings**:
   ```bash
   # Should have been displayed during installation
   # Check installer logs
   ```

### Expected Results

- [ ] GuardKit gets v1.0.0 agents (initially)
- [ ] RequireKit installer detects version mismatch
- [ ] Warning displayed about different versions
- [ ] User prompted with options (update, keep, abort)
- [ ] Final state consistent (either v1.0.0 or v1.1.0, not mixed)

### Verification Commands

```bash
# Check which version is installed
VERSION_INSTALLED=$(grep -r "version:" .claude/agents/universal/*.md | head -1 | awk '{print $2}')
echo "Installed version: $VERSION_INSTALLED"

# Verify no mixed versions
VERSIONS=$(grep -r "version:" .claude/agents/universal/*.md | awk '{print $2}' | sort -u | wc -l)
[ "$VERSIONS" -eq 1 ] && echo "✅ Single version" || echo "❌ Mixed versions detected"
```

### Pass Criteria

- Version mismatch detected ✅
- Warning displayed ✅
- User prompted ✅
- Consistent final state ✅

### Rollback Procedure

```bash
rm -rf .claude/
cd guardkit && git checkout installer/shared-agents-version.txt
cd ../require-kit && git checkout installer/shared-agents-version.txt
```

---

## Test Scenario 6: Offline Fallback

**Objective**: Verify offline installation uses bundled fallback agents.

**Note**: Only applicable if offline fallback feature is implemented (see architectural review YAGNI analysis).

### Prerequisites

- [ ] Fresh project directory
- [ ] Network disabled or GitHub blocked
- [ ] Fallback agents bundled in installer

### Test Steps

1. **Disable network access**:
   ```bash
   # Option 1: Disable network interface
   sudo ifconfig en0 down  # macOS
   sudo ip link set eth0 down  # Linux

   # Option 2: Block GitHub in /etc/hosts
   echo "127.0.0.1 github.com" | sudo tee -a /etc/hosts
   ```

2. **Run installer**:
   ```bash
   cd test-project
   ../guardkit/installer/scripts/install.sh
   ```

3. **Verify fallback used**:
   ```bash
   # Check for fallback warning in output
   # Installation should succeed despite network failure
   ```

4. **Verify agents installed**:
   ```bash
   ls -la .claude/agents/universal/
   ```

5. **Re-enable network**:
   ```bash
   sudo ifconfig en0 up  # macOS
   sudo ip link set eth0 up  # Linux
   # OR
   sudo sed -i '/github.com/d' /etc/hosts
   ```

### Expected Results

- [ ] Download fails (expected)
- [ ] Fallback warning displayed
- [ ] Fallback agents installed
- [ ] Installation completes successfully
- [ ] Agents functional (may be older version)

### Verification Commands

```bash
# Check for fallback agents
test -d installer/fallback/agents/universal && echo "✅ Fallback agents present"

# Verify installation succeeded despite network failure
test -d .claude/agents/universal && echo "✅ Agents installed"

# Compare with bundled fallback
diff -r installer/fallback/agents/universal/ .claude/agents/universal/
# Should be identical if fallback was used
```

### Pass Criteria

- Fallback activated ✅
- Warning displayed ✅
- Installation succeeds ✅
- Agents functional ✅

### Rollback Procedure

```bash
rm -rf .claude/
# Network already re-enabled in step 5
```

---

## Test Scenario 7: Conflict Detection with Local Agents

**Objective**: Verify installer detects and handles conflicts with local customized agents.

### Prerequisites

- [ ] Fresh project directory
- [ ] GuardKit cloned with conflict detection implemented (TASK-SHA-001)

### Test Steps

1. **Create local customized agent**:
   ```bash
   mkdir -p .claude/agents
   cat > .claude/agents/code-reviewer.md <<'EOF'
   ---
   name: code-reviewer
   description: Custom local version
   ---
   # Custom Code Reviewer
   This is a local customization.
   EOF
   ```

2. **Run GuardKit installer**:
   ```bash
   ../guardkit/installer/scripts/install.sh
   ```

3. **Verify conflict detection**:
   ```bash
   # Should prompt user:
   # ⚠️  WARNING: Local agents will be overwritten:
   #   - code-reviewer.md
   #
   # Options:
   #   [B]ackup and continue (recommended)
   #   [A]bort installation
   # Choice? (B/A)
   ```

4. **Choose backup option**:
   ```bash
   # Press 'B' when prompted
   ```

5. **Verify backup created**:
   ```bash
   ls -la .claude/agents.backup.*.tar.gz
   ```

6. **Verify shared-agents installed**:
   ```bash
   cat .claude/agents/universal/code-reviewer.md | grep -i "Custom local version"
   # Should NOT contain custom content (overwritten)
   ```

7. **Restore from backup** (test rollback):
   ```bash
   tar -xzf .claude/agents.backup.*.tar.gz
   cat .claude/agents/code-reviewer.md | grep -i "Custom local version"
   # Should contain custom content (restored)
   ```

### Expected Results

- [ ] Conflict detected accurately
- [ ] User prompted with clear options
- [ ] Backup created successfully
- [ ] Backup contains original local agents
- [ ] Backup restoration works
- [ ] No data loss

### Verification Commands

```bash
# Check conflict detection ran
# (Should see warning in installation output)

# Verify backup exists
BACKUP_FILE=$(ls -t .claude/agents.backup.*.tar.gz | head -1)
test -f "$BACKUP_FILE" && echo "✅ Backup created: $BACKUP_FILE"

# Verify backup contents
tar -tzf "$BACKUP_FILE" | grep code-reviewer.md
# Should list the backed-up file

# Test restoration
mkdir /tmp/backup-test
tar -xzf "$BACKUP_FILE" -C /tmp/backup-test
grep "Custom local version" /tmp/backup-test/.claude/agents/code-reviewer.md && echo "✅ Backup contains customizations"
```

### Pass Criteria

- Conflict detected ✅
- User prompted ✅
- Backup created ✅
- Backup valid ✅
- Restoration works ✅

### Rollback Procedure

```bash
# Restore from backup
tar -xzf .claude/agents.backup.*.tar.gz

# Or clean slate
rm -rf .claude/
```

---

## Test Scenario 8: Rollback to Pre-Migration State

**Objective**: Verify all rollback scenarios work correctly.

### Prerequisites

- [ ] GuardKit with shared-agents installed
- [ ] Rollback script created (TASK-SHA-003)
- [ ] Backup available

### Test Steps

#### Scenario 8a: Bad Shared-Agents Release

1. **Install known good version** (e.g., v1.0.0):
   ```bash
   echo "v1.0.0" > installer/shared-agents-version.txt
   ./installer/scripts/install.sh
   ```

2. **Upgrade to bad version** (e.g., v1.1.0 with bugs):
   ```bash
   echo "v1.1.0" > installer/shared-agents-version.txt
   ./installer/scripts/install.sh
   ```

3. **Detect issues**:
   ```bash
   # Hypothetically, v1.1.0 has bugs
   /task-work TASK-001  # Fails due to agent bugs
   ```

4. **Rollback to v1.0.0**:
   ```bash
   echo "v1.0.0" > installer/shared-agents-version.txt
   ./installer/scripts/install.sh
   ```

5. **Verify rollback**:
   ```bash
   /task-work TASK-001  # Should work now
   ```

**Expected**: Version downgrade succeeds, functionality restored.

---

#### Scenario 8b: Broken Installer Script

1. **Break installer** (simulate):
   ```bash
   # Introduce syntax error
   echo "syntax error &&& invalid" >> installer/scripts/install.sh
   ```

2. **Attempt installation**:
   ```bash
   ./installer/scripts/install.sh
   # Should fail with error
   ```

3. **Rollback installer**:
   ```bash
   git checkout HEAD~1 installer/scripts/install.sh
   ```

4. **Re-run fixed installer**:
   ```bash
   ./installer/scripts/install.sh
   # Should succeed
   ```

**Expected**: Broken installer detected, Git rollback works.

---

#### Scenario 8c: Corrupted Version File

1. **Corrupt version file**:
   ```bash
   echo "invalid-version-format" > installer/shared-agents-version.txt
   ```

2. **Attempt installation**:
   ```bash
   ./installer/scripts/install.sh
   # Should fail or use fallback
   ```

3. **Manually restore version file**:
   ```bash
   echo "v1.0.0" > installer/shared-agents-version.txt
   ```

4. **Manual agent installation**:
   ```bash
   curl -sL https://github.com/guardkit/shared-agents/releases/download/v1.0.0/shared-agents.tar.gz | tar -xz -C .claude/agents/universal/
   ```

**Expected**: Manual recovery works, agents restored.

---

#### Scenario 8d: Complete Rollback to Pre-Migration

1. **Install shared-agents** (current state):
   ```bash
   ./installer/scripts/install.sh
   ```

2. **Use rollback script**:
   ```bash
   ./scripts/rollback-shared-agents.sh
   ```

3. **Verify pre-migration state restored**:
   ```bash
   # Check agents are back in original location
   ls -la installer/global/agents/
   # Should contain agents that were migrated

   # Check universal directory removed
   test ! -d .claude/agents/universal && echo "✅ Universal directory removed"
   ```

**Expected**: Complete rollback to pre-shared-agents state.

---

### Verification Commands

```bash
# Verify rollback script exists
test -x scripts/rollback-shared-agents.sh && echo "✅ Rollback script executable"

# Test rollback script (dry-run if supported)
./scripts/rollback-shared-agents.sh --dry-run
```

### Pass Criteria

- All rollback scenarios work ✅
- No data loss ✅
- Clear error messages ✅
- State fully restored ✅

### Rollback Procedure

N/A (this IS the rollback test)

---

## Automated Test Suite

### Pytest-Based Integration Tests

**Location**: `tests/integration/shared-agents/test_integration.py`

**Framework**: pytest + subprocess

**Example**:

```python
import pytest
import subprocess
import os
import tempfile
import shutil

class TestSharedAgents:
    @pytest.fixture
    def fresh_project(self):
        """Create fresh test project directory."""
        tmpdir = tempfile.mkdtemp(prefix="test-shared-agents-")
        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_guardkit_standalone(self, fresh_project):
        """Test Scenario 1: GuardKit standalone installation."""
        # Change to test project
        os.chdir(fresh_project)

        # Run installer
        result = subprocess.run(
            ["../guardkit/installer/scripts/install.sh"],
            capture_output=True,
            text=True
        )

        # Verify installation succeeded
        assert result.returncode == 0, f"Installer failed: {result.stderr}"

        # Verify universal agents directory exists
        assert os.path.isdir(".claude/agents/universal"), "Universal agents directory missing"

        # Count agents
        agents = os.listdir(".claude/agents/universal")
        assert len(agents) > 0, "No agents installed"

        # Verify agent files
        for agent in agents:
            assert agent.endswith(".md"), f"Invalid agent file: {agent}"

    def test_requirekit_standalone(self, fresh_project):
        """Test Scenario 2: RequireKit standalone installation."""
        # Similar to test_guardkit_standalone
        pass

    def test_combined_installation_guardkit_first(self, fresh_project):
        """Test Scenario 3: Combined installation (GuardKit first)."""
        os.chdir(fresh_project)

        # Install GuardKit
        result1 = subprocess.run(
            ["../guardkit/installer/scripts/install.sh"],
            capture_output=True,
            text=True
        )
        assert result1.returncode == 0

        # Count initial agents
        initial_count = len(os.listdir(".claude/agents/universal"))

        # Install RequireKit
        result2 = subprocess.run(
            ["../require-kit/installer/scripts/install.sh"],
            capture_output=True,
            text=True
        )
        assert result2.returncode == 0

        # Count final agents
        final_count = len(os.listdir(".claude/agents/universal"))

        # Verify no duplication
        assert initial_count == final_count, f"Agents duplicated: {initial_count} → {final_count}"

    def test_version_pinning(self, fresh_project):
        """Test Scenario 5: Version pinning."""
        # Implementation depends on multiple releases existing
        pass

    def test_conflict_detection(self, fresh_project):
        """Test Scenario 7: Conflict detection."""
        os.chdir(fresh_project)

        # Create local customized agent
        os.makedirs(".claude/agents", exist_ok=True)
        with open(".claude/agents/code-reviewer.md", "w") as f:
            f.write("# Custom local version\n")

        # Run installer with automated input (select backup)
        result = subprocess.run(
            ["../guardkit/installer/scripts/install.sh"],
            input="B\n",  # Choose backup option
            capture_output=True,
            text=True
        )

        # Verify conflict detected
        assert "WARNING" in result.stdout, "Conflict not detected"

        # Verify backup created
        backups = [f for f in os.listdir(".claude") if f.startswith("agents.backup.")]
        assert len(backups) > 0, "Backup not created"

    # Add more test methods for other scenarios...

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Run Tests**:
```bash
cd tests/integration/shared-agents
pytest test_integration.py -v
```

---

## CI/CD Integration

### GitHub Actions Workflow

**Location**: `.github/workflows/test-shared-agents.yml`

```yaml
name: Test Shared Agents Integration

on:
  push:
    branches: [main, develop]
    paths:
      - 'installer/scripts/install.sh'
      - 'installer/shared-agents-version.txt'
  pull_request:
    branches: [main]

jobs:
  test-integration:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        scenario:
          - guardkit-standalone
          - requirekit-standalone
          - combined-guardkit-first
          - combined-requirekit-first
          - conflict-detection

    steps:
      - name: Checkout GuardKit
        uses: actions/checkout@v4
        with:
          path: guardkit

      - name: Checkout RequireKit
        uses: actions/checkout@v4
        with:
          repository: requirekit/require-kit
          path: require-kit

      - name: Checkout Shared Agents
        uses: actions/checkout@v4
        with:
          repository: guardkit/shared-agents
          path: shared-agents

      - name: Set up test environment
        run: |
          mkdir test-project
          cd test-project
          git init

      - name: Run test scenario
        run: |
          cd tests/integration/shared-agents
          pytest test_integration.py::TestSharedAgents::test_${{ matrix.scenario }} -v

      - name: Upload test artifacts
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: test-logs-${{ matrix.scenario }}
          path: |
            test-project/.claude/
            test-project/*.log
```

---

## Manual Test Checklist

**Tester**: _______________
**Date**: _______________
**Environment**: _______________

### Pre-Test Setup

- [ ] Fresh Ubuntu 22.04 or macOS environment
- [ ] Git installed and configured
- [ ] GitHub access verified
- [ ] All repositories cloned

### Test Execution

- [ ] **Scenario 1**: GuardKit standalone - PASS / FAIL
  - Notes: _______________________________

- [ ] **Scenario 2**: RequireKit standalone - PASS / FAIL
  - Notes: _______________________________

- [ ] **Scenario 3**: Combined (GuardKit first) - PASS / FAIL
  - Notes: _______________________________

- [ ] **Scenario 4**: Combined (RequireKit first) - PASS / FAIL
  - Notes: _______________________________

- [ ] **Scenario 5**: Version pinning - PASS / FAIL
  - Notes: _______________________________

- [ ] **Scenario 6**: Offline fallback - PASS / FAIL (if applicable)
  - Notes: _______________________________

- [ ] **Scenario 7**: Conflict detection - PASS / FAIL
  - Notes: _______________________________

- [ ] **Scenario 8**: Rollback scenarios - PASS / FAIL
  - 8a: Bad release - PASS / FAIL
  - 8b: Broken installer - PASS / FAIL
  - 8c: Corrupted version file - PASS / FAIL
  - 8d: Complete rollback - PASS / FAIL
  - Notes: _______________________________

### Overall Assessment

- [ ] All critical scenarios passed
- [ ] No data loss in any scenario
- [ ] Error messages clear and actionable
- [ ] Documentation matches actual behavior
- [ ] Ready for production release

**Sign-off**: _______________  **Date**: _______________

---

## Test Coverage Matrix

| Scenario | Unit Tests | Integration Tests | Manual Tests | CI/CD |
|----------|-----------|------------------|--------------|-------|
| Scenario 1 | N/A | ✅ pytest | ✅ Checklist | ✅ GitHub Actions |
| Scenario 2 | N/A | ✅ pytest | ✅ Checklist | ✅ GitHub Actions |
| Scenario 3 | N/A | ✅ pytest | ✅ Checklist | ✅ GitHub Actions |
| Scenario 4 | N/A | ✅ pytest | ✅ Checklist | ✅ GitHub Actions |
| Scenario 5 | N/A | ✅ pytest | ✅ Checklist | ⚠️ Manual (multiple releases needed) |
| Scenario 6 | N/A | ⚠️ Manual (network control) | ✅ Checklist | ❌ Not in CI |
| Scenario 7 | N/A | ✅ pytest | ✅ Checklist | ✅ GitHub Actions |
| Scenario 8 | N/A | ⚠️ Manual (destructive) | ✅ Checklist | ⚠️ Subset in CI |

**Legend**:
- ✅ Implemented/Planned
- ⚠️ Partial coverage or manual intervention required
- ❌ Not applicable or not in scope

---

## Success Criteria Summary

### Phase 4 Test Gate

All tests must pass before proceeding to Phase 5 (Documentation & Release):

- [ ] **Automated tests**: 100% pass rate (pytest suite)
- [ ] **CI/CD tests**: GitHub Actions green across all matrix combinations
- [ ] **Manual tests**: All critical scenarios verified by QA
- [ ] **No blockers**: Zero critical or high-severity bugs
- [ ] **Performance**: Installation completes in <30 seconds (normal network)
- [ ] **Reliability**: <1% failure rate across 100+ test runs

### Acceptance Criteria

- [ ] All 8 test scenarios executed and passed
- [ ] Automated test suite created and green
- [ ] CI/CD integration verified
- [ ] Manual test checklist completed and signed off
- [ ] Zero data loss in any scenario
- [ ] Rollback procedures verified and documented
- [ ] Test artifacts archived for audit trail

---

**Test Plan Version**: 1.0
**Based on**: TASK-ARCH-DC05 Architectural Review
**Last Updated**: November 28, 2025
**Status**: Ready for Execution (after TASK-SHA-002 completion)
