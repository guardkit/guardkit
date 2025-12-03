---
id: TASK-SHA-001
title: Implement installer conflict detection and backup mechanism
status: backlog
created: 2025-11-28T20:30:00Z
updated: 2025-11-28T20:30:00Z
priority: critical
tags: [shared-agents, installer, conflict-detection, phase-0, prerequisite]
complexity: 5
estimated_effort: 4h
phase: "Phase 0: Prerequisites"
depends_on: []
blocks: [TASK-SHA-P2-002, TASK-SHA-P3-002]
parent_task: TASK-ARCH-DC05
task_type: implementation
---

# Task: Implement Conflict Detection and Backup

## Context

**Critical Finding from Architectural Review**: Installer may overwrite local agent customizations, causing data loss and user frustration.

**Risk**: High severity - User data loss, broken workflows, trust damage
**Mitigation**: Add conflict detection and backup mechanism to installer

## Description

Implement conflict detection in the installer to prevent overwriting local agent customizations. Create backup mechanism to protect user data during installation.

## Acceptance Criteria

- [ ] Function created: `check_conflicts()` in `installer/scripts/install.sh`
- [ ] Function created: `backup_existing_agents()` in `installer/scripts/install.sh`
- [ ] Function created: `rollback_from_backup()` in `installer/scripts/install.sh`
- [ ] Conflicts detected before installation
- [ ] User prompted with clear options (Backup/Keep/Abort)
- [ ] Backup created with timestamp
- [ ] Backup restoration tested and verified
- [ ] No data loss in any test scenario
- [ ] Integration tested with TASK-SHA-P4-004

## Implementation Approach

### 1. Add Conflict Detection Function

Add to `installer/scripts/install.sh`:

```bash
check_conflicts() {
    local target_dir="$PROJECT_ROOT/.claude/agents"
    local universal_dir="$PROJECT_ROOT/.claude/agents/universal"
    local temp_extract="/tmp/shared-agents-temp-$$"

    # Extract shared-agents to temp location
    mkdir -p "$temp_extract"
    if ! tar -xz -C "$temp_extract" < /tmp/shared-agents.tar.gz 2>/dev/null; then
        echo "ERROR: Failed to extract shared-agents for conflict check"
        rm -rf "$temp_extract"
        return 1
    fi

    # Check for conflicts with local agents
    if [ -d "$target_dir" ]; then
        local conflicts=$(comm -12 \
            <(ls "$target_dir/" 2>/dev/null | grep '\.md$' | sort) \
            <(ls "$temp_extract/agents/" 2>/dev/null | grep '\.md$' | sort))

        if [ -n "$conflicts" ]; then
            echo ""
            echo "======================================================================="
            echo "⚠️  WARNING: Shared Agents Installation Conflict"
            echo "======================================================================="
            echo ""
            echo "The following local agents will be affected:"
            echo "$conflicts" | sed 's/^/  - /'
            echo ""
            echo "These agents exist in both your local .claude/agents/ directory"
            echo "and the shared-agents repository. The shared-agents versions will"
            echo "be installed to .claude/agents/universal/, but your local versions"
            echo "will take precedence in agent discovery."
            echo ""
            echo "Options:"
            echo "  [B] Backup local agents and continue (RECOMMENDED)"
            echo "      Creates .claude/agents.backup.<timestamp>.tar.gz"
            echo ""
            echo "  [K] Keep local agents and continue"
            echo "      Shared agents will be installed but not used (local takes precedence)"
            echo ""
            echo "  [A] Abort installation"
            echo "      No changes will be made"
            echo ""
            read -p "Your choice? [B/K/A] " -n 1 -r
            echo ""
            echo "======================================================================="

            case $REPLY in
                [Bb])
                    backup_existing_agents || {
                        echo "ERROR: Backup failed. Aborting installation."
                        rm -rf "$temp_extract"
                        exit 1
                    }
                    ;;
                [Kk])
                    echo ""
                    echo "ℹ️  Keeping local agents. Shared agents will be installed to universal/."
                    echo "   Your local agents will take precedence in agent discovery."
                    echo ""
                    ;;
                [Aa])
                    echo ""
                    echo "Installation aborted by user."
                    rm -rf "$temp_extract"
                    exit 0
                    ;;
                *)
                    echo ""
                    echo "Invalid choice. Aborting for safety."
                    rm -rf "$temp_extract"
                    exit 1
                    ;;
            esac
        fi
    fi

    # Cleanup temp extraction
    rm -rf "$temp_extract"
    return 0
}
```

### 2. Add Backup Function

```bash
backup_existing_agents() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$PROJECT_ROOT/.claude/agents.backup.$timestamp.tar.gz"

    echo ""
    echo "📦 Creating backup of local agents..."

    # Create backup
    if tar -czf "$backup_file" -C "$PROJECT_ROOT" .claude/agents/ 2>/dev/null; then
        echo "✅ Backup created successfully: $backup_file"
        echo ""
        echo "   To restore your local agents later:"
        echo "   cd $PROJECT_ROOT"
        echo "   tar -xzf $backup_file"
        echo ""

        # Store backup path for potential rollback
        echo "$backup_file" > "$PROJECT_ROOT/.claude/.last-backup"

        return 0
    else
        echo "❌ ERROR: Backup failed"
        echo "   Cannot proceed without successful backup"
        return 1
    fi
}
```

### 3. Add Rollback Function

```bash
rollback_from_backup() {
    local backup_file="$1"

    # If no backup file specified, use last backup
    if [ -z "$backup_file" ]; then
        if [ -f "$PROJECT_ROOT/.claude/.last-backup" ]; then
            backup_file=$(cat "$PROJECT_ROOT/.claude/.last-backup")
        else
            backup_file=$(ls -t "$PROJECT_ROOT"/.claude/agents.backup.*.tar.gz 2>/dev/null | head -1)
        fi
    fi

    if [ -z "$backup_file" ] || [ ! -f "$backup_file" ]; then
        echo "❌ No backup found. Cannot rollback."
        echo "   Backup location should be: .claude/agents.backup.<timestamp>.tar.gz"
        return 1
    fi

    echo ""
    echo "📦 Restoring from backup: $(basename "$backup_file")"

    # Remove current agents (if universal directory exists)
    if [ -d "$PROJECT_ROOT/.claude/agents/universal" ]; then
        rm -rf "$PROJECT_ROOT/.claude/agents/universal"
    fi

    # Restore from backup
    if tar -xzf "$backup_file" -C "$PROJECT_ROOT" 2>/dev/null; then
        echo "✅ Local agents restored successfully"
        return 0
    else
        echo "❌ ERROR: Restoration failed"
        return 1
    fi
}
```

### 4. Integrate into Installer

Update `install_shared_agents()` function:

```bash
install_shared_agents() {
    local version_file="$SCRIPT_DIR/../shared-agents-version.txt"
    local version=$(cat "$version_file" 2>/dev/null || echo "v1.0.0")
    local target_dir="$PROJECT_ROOT/.claude/agents/universal"
    local download_url="https://github.com/guardkit/shared-agents/releases/download/$version/shared-agents.tar.gz"

    echo "📦 Installing shared agents $version..."

    # Create target directory
    mkdir -p "$target_dir"

    # Download to temp location
    local temp_archive="/tmp/shared-agents.tar.gz"
    if curl -sL "$download_url" -o "$temp_archive"; then
        echo "✅ Downloaded shared agents $version"

        # NEW: Check for conflicts before extraction
        check_conflicts

        # Extract to universal directory
        if tar -xz -C "$target_dir" --strip-components=1 < "$temp_archive"; then
            echo "✅ Installed shared agents to $target_dir"
            rm -f "$temp_archive"
        else
            echo "❌ ERROR: Failed to extract shared agents"
            rm -f "$temp_archive"
            exit 1
        fi
    else
        echo "⚠️  Failed to download shared agents"
        # Fallback logic here (if implemented)
    fi
}
```

## Test Requirements

### Unit Tests

Create `tests/unit/test-conflict-detection.sh`:

```bash
#!/bin/bash
# Test conflict detection function

setup_test() {
    TEST_DIR=$(mktemp -d)
    mkdir -p "$TEST_DIR/.claude/agents"
    export PROJECT_ROOT="$TEST_DIR"
}

teardown_test() {
    rm -rf "$TEST_DIR"
}

test_no_conflicts() {
    setup_test
    # No local agents
    check_conflicts
    assert_exit_code 0
    teardown_test
}

test_with_conflicts() {
    setup_test
    # Create conflicting local agent
    echo "# Local agent" > "$TEST_DIR/.claude/agents/code-reviewer.md"
    # Should detect conflict and prompt user
    # (automated testing needs mock input)
    teardown_test
}

test_backup_creation() {
    setup_test
    mkdir -p "$TEST_DIR/.claude/agents"
    echo "# Test agent" > "$TEST_DIR/.claude/agents/test.md"

    backup_existing_agents

    # Verify backup exists
    BACKUP=$(ls -t "$TEST_DIR"/.claude/agents.backup.*.tar.gz | head -1)
    assert_file_exists "$BACKUP"

    # Verify backup contents
    tar -tzf "$BACKUP" | grep "test.md"
    assert_exit_code 0

    teardown_test
}

test_rollback() {
    setup_test
    mkdir -p "$TEST_DIR/.claude/agents"
    echo "# Original content" > "$TEST_DIR/.claude/agents/test.md"

    # Create backup
    backup_existing_agents
    BACKUP=$(ls -t "$TEST_DIR"/.claude/agents.backup.*.tar.gz | head -1)

    # Modify file
    echo "# Modified content" > "$TEST_DIR/.claude/agents/test.md"

    # Rollback
    rollback_from_backup "$BACKUP"

    # Verify original content restored
    grep "Original content" "$TEST_DIR/.claude/agents/test.md"
    assert_exit_code 0

    teardown_test
}

# Run all tests
test_no_conflicts
test_with_conflicts
test_backup_creation
test_rollback
```

### Integration Tests

- [ ] Test with TASK-SHA-P4-004 (Conflict Detection Testing)
- [ ] Test all user choices (B/K/A)
- [ ] Test backup creation
- [ ] Test rollback procedure
- [ ] Test with multiple conflicting agents
- [ ] Test with no conflicts

## Dependencies

**Prerequisite Tasks**: None (Phase 0)

**Blocks**:
- TASK-SHA-P2-002 (Update TaskWright Installer)
- TASK-SHA-P3-002 (Update RequireKit Installer)
- TASK-SHA-P4-004 (Conflict Detection Testing)

**External Dependencies**:
- `tar` command (standard on Unix systems)
- `comm` command (standard on Unix systems)
- Bash 4.0+ (for array operations)

## Success Criteria

- [ ] Conflict detection implemented and tested
- [ ] Backup mechanism tested and verified
- [ ] Zero data loss in 100+ test runs
- [ ] User prompts clear and actionable
- [ ] Rollback procedure verified
- [ ] Integration tests pass
- [ ] Code review approved

## Estimated Effort

**Total**: 4 hours
- Implementation: 2 hours
- Testing: 1.5 hours
- Documentation: 30 minutes

## Related Documents

- Architectural Review: `.claude/reviews/TASK-ARCH-DC05-shared-agents-architectural-review.md` (Risk R2)
- Risk Mitigation Plan: `.claude/reviews/TASK-ARCH-DC05-risk-mitigation-plan.md` (Risk R2)
- Test Plan: `tests/integration/shared-agents/TEST-PLAN.md` (Scenario 7)
