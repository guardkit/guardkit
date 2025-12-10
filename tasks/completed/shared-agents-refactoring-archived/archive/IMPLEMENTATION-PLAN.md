# Shared Agents Refactoring - Implementation Plan

**Based on**: TASK-ARCH-DC05 Architectural Review
**Status**: Approved with Modifications
**Estimated Duration**: 7 days (includes 2-day buffer)
**Review Score**: 82/100 (Good - Approve with Modifications)

---

## Executive Summary

This implementation plan provides a detailed task breakdown for migrating universal agents from duplicated copies in GuardKit and RequireKit to a single shared-agents repository. The plan includes all critical modifications identified in the architectural review.

**Critical Prerequisites** (Must complete before Phase 1):
1. Verify actual agent duplication
2. Implement conflict detection
3. Define integration test cases
4. Document rollback procedures
5. Add checksum validation

---

## Phase 0: Prerequisites (Day 0 - Before Migration)

**Duration**: 1 day
**Dependencies**: None
**Goal**: Address critical gaps identified in architectural review

### TASK-SHA-000: Verify Agent Duplication

**Description**: Identify which agents are actually duplicated between GuardKit and RequireKit (proposal assumption may be incorrect).

**Acceptance Criteria**:
- [ ] Script created: `scripts/verify-agent-duplication.sh`
- [ ] Script compares GuardKit and RequireKit agents
- [ ] Output: List of truly duplicated agents (name, similarity %, active status)
- [ ] Documentation updated with verified duplication list

**Estimated Effort**: 2 hours

**Test Requirements**:
- Script runs without errors
- Identifies all duplicated agents
- Similarity calculation accurate (>80% match = duplicate)

**Implementation Approach**:
```bash
#!/bin/bash
# scripts/verify-agent-duplication.sh

# Compare agents between repos
GUARDKIT_AGENTS="installer/core/agents"
REQUIREKIT_AGENTS="../require-kit/.claude/agents"

# For each agent in GuardKit
for agent in $GUARDKIT_AGENTS/*.md; do
    basename=$(basename "$agent")
    requirekit_agent="$REQUIREKIT_AGENTS/$basename"

    if [ -f "$requirekit_agent" ]; then
        # Calculate similarity (simple line-based diff)
        total_lines=$(wc -l < "$agent")
        diff_lines=$(diff "$agent" "$requirekit_agent" | grep -c '^[<>]' || echo 0)
        similarity=$(( 100 - (diff_lines * 100 / total_lines) ))

        if [ $similarity -ge 80 ]; then
            echo "✅ $basename - ${similarity}% similar (DUPLICATE)"
        else
            echo "⚠️  $basename - ${similarity}% similar (DIVERGED)"
        fi
    fi
done
```

**Related Tasks**: None
**Priority**: Critical (blocks Phase 1)

---

### TASK-SHA-001: Implement Installer Conflict Detection

**Description**: Add conflict detection to prevent overwriting local agent customizations during shared-agents installation.

**Acceptance Criteria**:
- [ ] Function created: `check_conflicts()` in `install.sh`
- [ ] Function created: `backup_existing_agents()` in `install.sh`
- [ ] Conflicts detected before installation
- [ ] User prompted with options (continue, abort, backup)
- [ ] Backup created with timestamp
- [ ] No data loss during installation

**Estimated Effort**: 4 hours

**Test Requirements**:
- Test with local customized agents
- Test with no local agents
- Test with partial conflicts
- Verify backup creation
- Verify backup restoration

**Implementation Approach**:
```bash
check_conflicts() {
    local target_dir="$PROJECT_ROOT/.claude/agents/universal"
    local temp_extract="/tmp/shared-agents-temp"

    # Extract to temp location
    mkdir -p "$temp_extract"
    tar -xz -C "$temp_extract" < shared-agents.tar.gz

    # Check for conflicts with local agents
    if [ -d "$PROJECT_ROOT/.claude/agents" ]; then
        local conflicts=$(comm -12 \
            <(ls "$PROJECT_ROOT/.claude/agents/" | grep '\.md$' | sort) \
            <(ls "$temp_extract/agents/" | grep '\.md$' | sort))

        if [ -n "$conflicts" ]; then
            echo "⚠️  WARNING: Local agents will be overwritten:"
            echo "$conflicts" | sed 's/^/  - /'
            echo ""
            echo "Options:"
            echo "  [B]ackup and continue (recommended)"
            echo "  [A]bort installation"
            read -p "Choice? (B/A) " -n 1 -r
            echo

            case $REPLY in
                [Bb])
                    backup_existing_agents
                    return 0
                    ;;
                [Aa])
                    echo "Installation aborted by user."
                    exit 0
                    ;;
                *)
                    echo "Invalid choice. Aborting."
                    exit 1
                    ;;
            esac
        fi
    fi
}

backup_existing_agents() {
    local timestamp=$(date +%s)
    local backup_file=".claude/agents.backup.$timestamp.tar.gz"

    echo "📦 Creating backup: $backup_file"
    tar -czf "$backup_file" .claude/agents/
    echo "✅ Backup created successfully"
}
```

**Related Tasks**: TASK-SHA-000
**Priority**: Critical (blocks Phase 2)

---

### TASK-SHA-002: Define Integration Test Cases

**Description**: Create comprehensive integration test specifications for all migration scenarios.

**Acceptance Criteria**:
- [ ] Document created: `tests/integration/shared-agents/TEST-PLAN.md`
- [ ] 6+ test scenarios defined (see architectural review Appendix C)
- [ ] Pass/fail criteria specified for each test
- [ ] Automated test scripts created where possible
- [ ] Manual test checklist created

**Estimated Effort**: 4 hours

**Test Requirements**:
- All scenarios executable
- Clear pass/fail criteria
- Rollback procedures tested

**Test Scenarios**:
1. GuardKit standalone installation
2. RequireKit standalone installation
3. Combined installation (GuardKit first)
4. Combined installation (RequireKit first)
5. Version pinning (different versions)
6. Offline fallback
7. Conflict detection with local agents
8. Rollback to pre-migration state

**Related Tasks**: None
**Priority**: Critical (blocks Phase 4)

---

### TASK-SHA-003: Document Rollback Procedures

**Description**: Create detailed rollback documentation for all failure scenarios.

**Acceptance Criteria**:
- [ ] Document created: `docs/guides/shared-agents-rollback.md`
- [ ] 4+ rollback scenarios documented (see architectural review)
- [ ] Step-by-step instructions for each scenario
- [ ] Rollback script created: `scripts/rollback-shared-agents.sh`
- [ ] Rollback procedures tested

**Estimated Effort**: 3 hours

**Test Requirements**:
- All scenarios executable
- Rollback script works
- No data loss after rollback

**Rollback Scenarios**:
1. Bad shared-agents release
2. Broken installer script
3. Corrupted version file
4. Complete rollback to pre-migration state

**Related Tasks**: None
**Priority**: Critical (blocks Phase 2)

---

### TASK-SHA-004: Add Checksum Validation

**Description**: Implement checksum validation for shared-agents downloads to prevent corrupted installations.

**Acceptance Criteria**:
- [ ] GitHub Actions workflow updated to generate checksums
- [ ] Installer updated to validate checksums
- [ ] Checksum mismatch blocks installation
- [ ] Clear error message on checksum failure
- [ ] Documentation updated

**Estimated Effort**: 2 hours

**Test Requirements**:
- Valid checksum passes
- Invalid checksum fails with error
- Missing checksum handled gracefully

**Implementation Approach**:
```yaml
# .github/workflows/release.yml (addition)
- name: Create release archive
  run: |
    tar -czvf shared-agents.tar.gz agents/ manifest.json
    sha256sum shared-agents.tar.gz > shared-agents.tar.gz.sha256

- name: Create Release
  uses: softprops/action-gh-release@v1
  with:
    files: |
      shared-agents.tar.gz
      shared-agents.tar.gz.sha256
```

```bash
# installer/scripts/install.sh (addition)
validate_checksum() {
    local archive="$1"
    local checksum_file="$2"

    if [ ! -f "$checksum_file" ]; then
        echo "⚠️  WARNING: Checksum file not found. Skipping validation."
        return 0
    fi

    echo "🔍 Validating checksum..."
    if sha256sum -c "$checksum_file" 2>/dev/null; then
        echo "✅ Checksum valid"
        return 0
    else
        echo "❌ ERROR: Checksum validation failed"
        echo "   Archive may be corrupted. Please try again."
        return 1
    fi
}
```

**Related Tasks**: None
**Priority**: High (should complete before Phase 1)

---

## Phase 1: Create Shared Agents Repository (Day 1)

**Duration**: 1 day
**Dependencies**: Phase 0 complete
**Goal**: Create source of truth for universal agents

### TASK-SHA-P1-001: Create Repository Structure

**Description**: Initialize `guardkit/shared-agents` repository with directory structure.

**Acceptance Criteria**:
- [ ] Repository created on GitHub: `guardkit/shared-agents`
- [ ] Directory structure created:
  ```
  shared-agents/
  ├── agents/
  ├── .github/workflows/
  ├── README.md
  ├── CHANGELOG.md
  ├── LICENSE
  └── .gitignore
  ```
- [ ] README.md documents purpose and usage
- [ ] LICENSE file added (same as GuardKit/RequireKit)
- [ ] .gitignore configured

**Estimated Effort**: 1 hour

**Test Requirements**:
- Repository accessible
- All files present
- README clear and accurate

**Related Tasks**: None
**Priority**: High

---

### TASK-SHA-P1-002: Migrate Universal Agents

**Description**: Copy verified duplicated agents (from TASK-SHA-000) to shared-agents repository.

**Acceptance Criteria**:
- [ ] Agents copied from GuardKit to `shared-agents/agents/`
- [ ] Only truly duplicated agents migrated (verified list)
- [ ] Agent metadata preserved (frontmatter)
- [ ] File permissions preserved
- [ ] Git commit with clear message

**Estimated Effort**: 1 hour

**Test Requirements**:
- All agents present
- Frontmatter valid
- Files readable

**Migration Script**:
```bash
#!/bin/bash
# Migrate agents based on verified duplication list
VERIFIED_AGENTS=(
    # List from TASK-SHA-000 output
    "code-reviewer.md"
    "test-orchestrator.md"
    # Add others as verified
)

for agent in "${VERIFIED_AGENTS[@]}"; do
    cp "guardkit/installer/core/agents/$agent" "shared-agents/agents/"
    echo "✅ Migrated: $agent"
done
```

**Related Tasks**: TASK-SHA-000 (depends on verification)
**Priority**: High

---

### TASK-SHA-P1-003: Create Manifest File

**Description**: Create `manifest.json` with agent metadata (simplified per architectural review).

**Acceptance Criteria**:
- [ ] `manifest.json` created with schema version
- [ ] All migrated agents listed
- [ ] Schema documented in README.md
- [ ] JSON valid (lint passes)

**Estimated Effort**: 1 hour

**Test Requirements**:
- JSON parses successfully
- All agents listed
- Schema version present

**Implementation**:
```json
{
  "schema_version": "1.0",
  "version": "1.0.0",
  "agents": [
    "agents/code-reviewer.md",
    "agents/test-orchestrator.md"
  ]
}
```

**Related Tasks**: TASK-SHA-P1-002
**Priority**: High

---

### TASK-SHA-P1-004: Set Up GitHub Actions

**Description**: Create release workflow for automated tarball creation with checksums.

**Acceptance Criteria**:
- [ ] Workflow file created: `.github/workflows/release.yml`
- [ ] Workflow triggers on version tags (`v*`)
- [ ] Tarball created with agents and manifest
- [ ] Checksum generated (SHA256)
- [ ] Release notes auto-generated
- [ ] Workflow tested with v1.0.0-beta tag

**Estimated Effort**: 2 hours

**Test Requirements**:
- Workflow runs successfully
- Tarball downloadable
- Checksum file present
- Release notes generated

**Related Tasks**: TASK-SHA-004 (checksum validation)
**Priority**: High

---

### TASK-SHA-P1-005: Create v1.0.0 Release

**Description**: Tag and release initial version of shared-agents.

**Acceptance Criteria**:
- [ ] Git tag created: `v1.0.0`
- [ ] GitHub release created automatically
- [ ] Release includes:
  - [ ] `shared-agents.tar.gz`
  - [ ] `shared-agents.tar.gz.sha256`
  - [ ] Release notes
- [ ] Download links verified
- [ ] CHANGELOG.md updated

**Estimated Effort**: 1 hour

**Test Requirements**:
- Release downloadable
- Checksum validates
- Tarball extracts successfully

**Related Tasks**: TASK-SHA-P1-004
**Priority**: High

---

## Phase 2: Update GuardKit (Day 2-3)

**Duration**: 2 days
**Dependencies**: Phase 1 complete
**Goal**: Integrate shared-agents into GuardKit

### TASK-SHA-P2-001: Add Version Pinning File

**Description**: Create `installer/shared-agents-version.txt` to pin shared-agents version.

**Acceptance Criteria**:
- [ ] File created: `installer/shared-agents-version.txt`
- [ ] Content: `v1.0.0`
- [ ] Documentation added explaining version pinning
- [ ] Git committed

**Estimated Effort**: 30 minutes

**Test Requirements**:
- File readable
- Version format valid

**Related Tasks**: None
**Priority**: High

---

### TASK-SHA-P2-002: Update Installer Script

**Description**: Modify `install.sh` to download and install shared-agents.

**Acceptance Criteria**:
- [ ] Function created: `install_shared_agents()`
- [ ] Conflict detection implemented (TASK-SHA-001)
- [ ] Checksum validation implemented (TASK-SHA-004)
- [ ] Version mismatch warning implemented
- [ ] Offline fallback implemented (optional, see architectural review)
- [ ] Function called during installation
- [ ] Error handling comprehensive

**Estimated Effort**: 4 hours

**Test Requirements**:
- Downloads shared-agents successfully
- Validates checksum
- Detects conflicts
- Creates backup
- Handles network failures gracefully

**Related Tasks**: TASK-SHA-001, TASK-SHA-004
**Priority**: Critical

---

### TASK-SHA-P2-003: Create Fallback Agents Directory

**Description**: Bundle fallback agents for offline installation (if offline fallback kept).

**Acceptance Criteria**:
- [ ] Directory created: `installer/fallback/agents/universal/`
- [ ] Agents copied from shared-agents v1.0.0
- [ ] Fallback used when download fails
- [ ] Warning displayed when using fallback
- [ ] Documentation updated

**Estimated Effort**: 1 hour

**Test Requirements**:
- Fallback agents present
- Fallback used when offline
- Warning displayed

**Note**: Architectural review suggests reconsidering offline fallback (YAGNI). Decide before implementation.

**Related Tasks**: None
**Priority**: Medium (optional)

---

### TASK-SHA-P2-004: Remove Duplicate Agents

**Description**: Remove agents from `installer/core/agents/` that are now in shared-agents.

**Acceptance Criteria**:
- [ ] Duplicate agents removed (verified list from TASK-SHA-000)
- [ ] Only agents migrated to shared-agents are removed
- [ ] Git commit with clear message
- [ ] No broken references in codebase

**Estimated Effort**: 1 hour

**Test Requirements**:
- All duplicates removed
- No broken imports
- Agent discovery still works

**Related Tasks**: TASK-SHA-000 (verified duplication list)
**Priority**: High

---

### TASK-SHA-P2-005: Update Agent Discovery

**Description**: Modify agent discovery to recognize `universal/` subdirectory as separate precedence tier.

**Acceptance Criteria**:
- [ ] `lib/agent_discovery.py` updated with new precedence level
- [ ] Precedence order: local > user > universal > global > template
- [ ] Agent discovery tests updated
- [ ] Documentation updated: `docs/guides/agent-discovery-guide.md`

**Estimated Effort**: 3 hours

**Test Requirements**:
- Universal agents discovered correctly
- Precedence order respected
- No regression in existing discovery

**Implementation Approach**:
```python
# lib/agent_discovery.py
AGENT_SOURCES = [
    ('local', '.claude/agents'),
    ('user', '~/.agentecflow/agents'),
    ('universal', '.claude/agents/universal'),  # NEW
    ('global', 'installer/core/agents'),
    ('template', 'installer/core/templates/*/agents')
]
```

**Related Tasks**: None
**Priority**: High

---

### TASK-SHA-P2-006: Update Documentation

**Description**: Update all GuardKit documentation referencing agents.

**Acceptance Criteria**:
- [ ] CLAUDE.md updated with shared-agents architecture
- [ ] README.md updated
- [ ] Agent discovery guide updated
- [ ] Installation guide updated
- [ ] Migration guide created for existing users

**Estimated Effort**: 2 hours

**Test Requirements**:
- All links valid
- Documentation accurate
- No outdated references

**Related Tasks**: None
**Priority**: Medium

---

### TASK-SHA-P2-007: Test GuardKit Standalone

**Description**: Run integration tests for GuardKit standalone installation.

**Acceptance Criteria**:
- [ ] Test scenario 1 passes (see TASK-SHA-002)
- [ ] Shared agents downloaded and installed
- [ ] Agent discovery works
- [ ] `/task-work` command functions correctly
- [ ] No errors in logs

**Estimated Effort**: 2 hours

**Test Requirements**:
- All test criteria met
- No regressions

**Related Tasks**: TASK-SHA-002 (test plan)
**Priority**: Critical

---

## Phase 3: Update RequireKit (Day 2-3, Parallel with Phase 2)

**Duration**: 2 days
**Dependencies**: Phase 1 complete
**Goal**: Integrate shared-agents into RequireKit

**Note**: Tasks identical to Phase 2, executed in RequireKit repository.

### TASK-SHA-P3-001: Add Version Pinning File (RequireKit)

**Description**: Create `installer/shared-agents-version.txt` in RequireKit.

**Acceptance Criteria**: Same as TASK-SHA-P2-001

**Estimated Effort**: 30 minutes

**Related Tasks**: TASK-SHA-P2-001 (reference implementation)
**Priority**: High

---

### TASK-SHA-P3-002: Update Installer Script (RequireKit)

**Description**: Modify RequireKit `install.sh` to download shared-agents.

**Acceptance Criteria**: Same as TASK-SHA-P2-002

**Estimated Effort**: 4 hours

**Related Tasks**: TASK-SHA-P2-002 (reference implementation)
**Priority**: Critical

---

### TASK-SHA-P3-003: Create Fallback Agents Directory (RequireKit)

**Description**: Bundle fallback agents in RequireKit (if offline fallback kept).

**Acceptance Criteria**: Same as TASK-SHA-P2-003

**Estimated Effort**: 1 hour

**Related Tasks**: TASK-SHA-P2-003 (reference implementation)
**Priority**: Medium (optional)

---

### TASK-SHA-P3-004: Remove Duplicate Agents (RequireKit)

**Description**: Remove duplicated agents from RequireKit `.claude/agents/`.

**Acceptance Criteria**: Same as TASK-SHA-P2-004

**Estimated Effort**: 1 hour

**Related Tasks**: TASK-SHA-P2-004 (reference implementation)
**Priority**: High

---

### TASK-SHA-P3-005: Update Agent Discovery (RequireKit)

**Description**: Modify RequireKit agent discovery (if applicable).

**Acceptance Criteria**: Same as TASK-SHA-P2-005

**Estimated Effort**: 3 hours

**Note**: RequireKit may have different agent discovery mechanism. Adapt as needed.

**Related Tasks**: TASK-SHA-P2-005 (reference implementation)
**Priority**: High

---

### TASK-SHA-P3-006: Update Documentation (RequireKit)

**Description**: Update RequireKit documentation.

**Acceptance Criteria**: Same as TASK-SHA-P2-006

**Estimated Effort**: 2 hours

**Related Tasks**: TASK-SHA-P2-006 (reference implementation)
**Priority**: Medium

---

### TASK-SHA-P3-007: Test RequireKit Standalone

**Description**: Run integration tests for RequireKit standalone installation.

**Acceptance Criteria**: Same as TASK-SHA-P2-007 (Test scenario 2)

**Estimated Effort**: 2 hours

**Related Tasks**: TASK-SHA-002 (test plan)
**Priority**: Critical

---

## Phase 4: Integration Testing (Day 4-5)

**Duration**: 2 days
**Dependencies**: Phase 2 AND Phase 3 complete
**Goal**: Verify all integration scenarios work correctly

### TASK-SHA-P4-001: Combined Installation Testing

**Description**: Test combined installation scenarios (both tools in same project).

**Acceptance Criteria**:
- [ ] Test scenario 3 passes (GuardKit first)
- [ ] Test scenario 4 passes (RequireKit first)
- [ ] Shared agents not duplicated
- [ ] Both tools function independently
- [ ] No version conflicts

**Estimated Effort**: 3 hours

**Test Requirements**:
- All test criteria met
- No data loss
- No conflicts

**Related Tasks**: TASK-SHA-002 (test plan)
**Priority**: Critical

---

### TASK-SHA-P4-002: Version Pinning Testing

**Description**: Test different version pinning scenarios.

**Acceptance Criteria**:
- [ ] Test scenario 5 passes (different versions)
- [ ] Version mismatch warnings displayed
- [ ] Correct versions installed
- [ ] No interference between versions

**Estimated Effort**: 2 hours

**Test Requirements**:
- Different versions coexist
- Warnings displayed
- No errors

**Related Tasks**: TASK-SHA-002 (test plan)
**Priority**: High

---

### TASK-SHA-P4-003: Offline Fallback Testing

**Description**: Test offline installation scenarios (if offline fallback kept).

**Acceptance Criteria**:
- [ ] Test scenario 6 passes (offline fallback)
- [ ] Fallback agents installed
- [ ] Warning displayed
- [ ] Installation completes successfully

**Estimated Effort**: 1 hour

**Test Requirements**:
- Fallback works
- Warning clear
- No errors

**Related Tasks**: TASK-SHA-002 (test plan)
**Priority**: Medium (optional)

---

### TASK-SHA-P4-004: Conflict Detection Testing

**Description**: Test conflict detection with local customized agents.

**Acceptance Criteria**:
- [ ] Test scenario 7 passes (conflict detection)
- [ ] Conflicts detected accurately
- [ ] User prompted correctly
- [ ] Backup created successfully
- [ ] No data loss

**Estimated Effort**: 2 hours

**Test Requirements**:
- All conflicts detected
- Backup restoration works
- User experience smooth

**Related Tasks**: TASK-SHA-001 (conflict detection)
**Priority**: Critical

---

### TASK-SHA-P4-005: Rollback Testing

**Description**: Test all rollback scenarios.

**Acceptance Criteria**:
- [ ] Test scenario 8 passes (rollback)
- [ ] All rollback scenarios work
- [ ] Rollback script functions correctly
- [ ] No data loss after rollback

**Estimated Effort**: 2 hours

**Test Requirements**:
- All scenarios executable
- Rollback successful
- State restored

**Related Tasks**: TASK-SHA-003 (rollback procedures)
**Priority**: Critical

---

### TASK-SHA-P4-006: CI/CD Pipeline Testing

**Description**: Test installation in GitHub Actions and other CI environments.

**Acceptance Criteria**:
- [ ] GitHub Actions workflow runs successfully
- [ ] Shared agents downloaded in CI
- [ ] Caching works (if implemented)
- [ ] Build succeeds
- [ ] No network-related failures

**Estimated Effort**: 3 hours

**Test Requirements**:
- CI builds pass
- Performance acceptable
- Reliability high (>99%)

**Related Tasks**: None
**Priority**: High

---

### TASK-SHA-P4-007: Agent Discovery Testing

**Description**: Test agent discovery across all precedence levels.

**Acceptance Criteria**:
- [ ] Universal agents discovered correctly
- [ ] Precedence order respected
- [ ] Local customizations override universal agents
- [ ] Discovery feedback accurate
- [ ] No regression in existing discovery

**Estimated Effort**: 2 hours

**Test Requirements**:
- All precedence levels tested
- No broken discovery
- Performance acceptable

**Related Tasks**: TASK-SHA-P2-005, TASK-SHA-P3-005
**Priority**: High

---

## Phase 5: Documentation & Release (Day 6-7)

**Duration**: 2 days
**Dependencies**: Phase 4 complete
**Goal**: Document changes and release new versions

### TASK-SHA-P5-001: Update README Files

**Description**: Update README.md in all three repositories.

**Acceptance Criteria**:
- [ ] `shared-agents/README.md` updated
- [ ] `guardkit/README.md` updated
- [ ] `require-kit/README.md` updated
- [ ] All READMEs reference shared-agents architecture
- [ ] Installation instructions accurate
- [ ] Links valid

**Estimated Effort**: 2 hours

**Test Requirements**:
- All links work
- Instructions accurate
- No outdated content

**Related Tasks**: None
**Priority**: Medium

---

### TASK-SHA-P5-002: Create Migration Guide

**Description**: Create comprehensive migration guide for existing users.

**Acceptance Criteria**:
- [ ] Document created: `docs/guides/shared-agents-migration.md`
- [ ] Guide covers:
  - [ ] What changed
  - [ ] Why changed
  - [ ] How to update
  - [ ] How to preserve customizations
  - [ ] Troubleshooting
- [ ] Step-by-step instructions
- [ ] FAQ section
- [ ] Clear and concise

**Estimated Effort**: 3 hours

**Test Requirements**:
- Guide follows actual migration
- All steps accurate
- FAQ comprehensive

**Related Tasks**: None
**Priority**: High

---

### TASK-SHA-P5-003: Update CHANGELOG

**Description**: Update CHANGELOG.md in all repositories.

**Acceptance Criteria**:
- [ ] `shared-agents/CHANGELOG.md` updated
- [ ] `guardkit/CHANGELOG.md` updated
- [ ] `require-kit/CHANGELOG.md` updated
- [ ] Changes categorized (Added, Changed, Deprecated, Removed, Fixed)
- [ ] Version numbers correct
- [ ] Release dates accurate

**Estimated Effort**: 1 hour

**Test Requirements**:
- All changes documented
- Format consistent
- Dates correct

**Related Tasks**: None
**Priority**: Medium

---

### TASK-SHA-P5-004: Create Release Announcements

**Description**: Prepare release announcements for GitHub releases.

**Acceptance Criteria**:
- [ ] GuardKit release notes drafted
- [ ] RequireKit release notes drafted
- [ ] Release notes include:
  - [ ] Summary of changes
  - [ ] Migration guide link
  - [ ] Breaking changes (if any)
  - [ ] Known issues
- [ ] Tone professional and clear

**Estimated Effort**: 2 hours

**Test Requirements**:
- All information accurate
- Links valid
- Tone appropriate

**Related Tasks**: TASK-SHA-P5-002 (migration guide)
**Priority**: Medium

---

### TASK-SHA-P5-005: Tag and Release GuardKit

**Description**: Create new GuardKit release with shared-agents integration.

**Acceptance Criteria**:
- [ ] Version incremented appropriately (semantic versioning)
- [ ] Git tag created: `v2.x.0` (or appropriate version)
- [ ] GitHub release created
- [ ] Release notes published
- [ ] Download links verified
- [ ] CHANGELOG.md updated

**Estimated Effort**: 1 hour

**Test Requirements**:
- Release downloadable
- Installation works
- No broken links

**Related Tasks**: TASK-SHA-P5-004 (release notes)
**Priority**: High

---

### TASK-SHA-P5-006: Tag and Release RequireKit

**Description**: Create new RequireKit release with shared-agents integration.

**Acceptance Criteria**: Same as TASK-SHA-P5-005

**Estimated Effort**: 1 hour

**Related Tasks**: TASK-SHA-P5-004 (release notes)
**Priority**: High

---

### TASK-SHA-P5-007: Announce to Users

**Description**: Announce releases via appropriate channels.

**Acceptance Criteria**:
- [ ] GitHub Discussions post (if applicable)
- [ ] Twitter/social media announcement (if applicable)
- [ ] Stakeholders notified
- [ ] Migration guide linked

**Estimated Effort**: 1 hour

**Test Requirements**:
- All channels covered
- Links valid
- Messaging clear

**Related Tasks**: None
**Priority**: Low

---

## Summary of Tasks

### Phase 0: Prerequisites (1 day)
- TASK-SHA-000: Verify agent duplication (2h)
- TASK-SHA-001: Implement conflict detection (4h)
- TASK-SHA-002: Define integration test cases (4h)
- TASK-SHA-003: Document rollback procedures (3h)
- TASK-SHA-004: Add checksum validation (2h)

**Total: ~15 hours (2 days with buffer)**

### Phase 1: Create Shared Agents Repository (1 day)
- TASK-SHA-P1-001: Create repository structure (1h)
- TASK-SHA-P1-002: Migrate universal agents (1h)
- TASK-SHA-P1-003: Create manifest file (1h)
- TASK-SHA-P1-004: Set up GitHub Actions (2h)
- TASK-SHA-P1-005: Create v1.0.0 release (1h)

**Total: 6 hours (1 day)**

### Phase 2: Update GuardKit (2 days)
- TASK-SHA-P2-001: Add version pinning file (0.5h)
- TASK-SHA-P2-002: Update installer script (4h)
- TASK-SHA-P2-003: Create fallback agents directory (1h, optional)
- TASK-SHA-P2-004: Remove duplicate agents (1h)
- TASK-SHA-P2-005: Update agent discovery (3h)
- TASK-SHA-P2-006: Update documentation (2h)
- TASK-SHA-P2-007: Test GuardKit standalone (2h)

**Total: 13.5 hours (2 days)**

### Phase 3: Update RequireKit (2 days, parallel with Phase 2)
- TASK-SHA-P3-001 through TASK-SHA-P3-007 (same as Phase 2)

**Total: 13.5 hours (2 days, parallel)**

### Phase 4: Integration Testing (2 days)
- TASK-SHA-P4-001: Combined installation testing (3h)
- TASK-SHA-P4-002: Version pinning testing (2h)
- TASK-SHA-P4-003: Offline fallback testing (1h, optional)
- TASK-SHA-P4-004: Conflict detection testing (2h)
- TASK-SHA-P4-005: Rollback testing (2h)
- TASK-SHA-P4-006: CI/CD pipeline testing (3h)
- TASK-SHA-P4-007: Agent discovery testing (2h)

**Total: 15 hours (2 days)**

### Phase 5: Documentation & Release (2 days)
- TASK-SHA-P5-001: Update README files (2h)
- TASK-SHA-P5-002: Create migration guide (3h)
- TASK-SHA-P5-003: Update CHANGELOG (1h)
- TASK-SHA-P5-004: Create release announcements (2h)
- TASK-SHA-P5-005: Tag and release GuardKit (1h)
- TASK-SHA-P5-006: Tag and release RequireKit (1h)
- TASK-SHA-P5-007: Announce to users (1h)

**Total: 11 hours (2 days with buffer)**

---

## Timeline Summary

| Phase | Duration | Dependencies | Can Parallelize |
|-------|----------|--------------|-----------------|
| Phase 0 | 2 days | None | No |
| Phase 1 | 1 day | Phase 0 | No |
| Phase 2 | 2 days | Phase 1 | Yes (with Phase 3) |
| Phase 3 | 2 days | Phase 1 | Yes (with Phase 2) |
| Phase 4 | 2 days | Phase 2 + Phase 3 | Partially |
| Phase 5 | 2 days | Phase 4 | Partially |

**Total Calendar Days**: 7 days (with parallel execution and buffer)
**Total Person-Hours**: ~74 hours (~9.25 person-days)

---

## Risk Mitigation Tracking

All critical risks identified in architectural review have mitigation tasks:

| Risk | Mitigation Task(s) | Status |
|------|-------------------|--------|
| Agent classification error | TASK-SHA-000 | Pending |
| Breaking changes to users | TASK-SHA-001, TASK-SHA-P4-004 | Pending |
| CI/CD failures | TASK-SHA-P4-006 | Pending |
| Version conflicts | TASK-SHA-P4-002 | Pending |
| Agent discovery confusion | TASK-SHA-P2-005, TASK-SHA-P4-007 | Pending |
| Installer bugs | TASK-SHA-P4-001 through P4-007 | Pending |
| Rollback failures | TASK-SHA-003, TASK-SHA-P4-005 | Pending |

---

## Success Criteria

### Phase 0 Success Criteria
- [ ] Verified agent duplication list created
- [ ] Conflict detection implemented and tested
- [ ] Integration test plan documented
- [ ] Rollback procedures documented and tested
- [ ] Checksum validation implemented

### Phase 1 Success Criteria
- [ ] `shared-agents` repository created
- [ ] All verified agents migrated
- [ ] v1.0.0 release published
- [ ] Release downloadable and validates

### Phase 2 Success Criteria
- [ ] GuardKit installer updated
- [ ] Shared agents downloaded on installation
- [ ] Agent discovery works with universal tier
- [ ] Standalone installation succeeds
- [ ] No regressions

### Phase 3 Success Criteria
- [ ] RequireKit installer updated
- [ ] Shared agents downloaded on installation
- [ ] Standalone installation succeeds
- [ ] No regressions

### Phase 4 Success Criteria
- [ ] All 7 integration test scenarios pass
- [ ] CI/CD pipelines work
- [ ] Rollback procedures verified
- [ ] No data loss in any scenario

### Phase 5 Success Criteria
- [ ] All documentation updated
- [ ] Migration guide published
- [ ] New releases tagged
- [ ] Users notified
- [ ] Zero critical issues reported

---

## Next Steps

1. **Review this implementation plan** with team
2. **Create individual task files** in `tasks/backlog/shared-agents-refactoring/`
3. **Assign tasks** to team members
4. **Begin Phase 0** (prerequisites)
5. **Track progress** using `/task-status` and `/task-work` commands

---

**Implementation Plan Version**: 1.0
**Based on**: TASK-ARCH-DC05 Architectural Review (Score: 82/100)
**Last Updated**: November 28, 2025
**Status**: Ready for Execution
