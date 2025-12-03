---
id: TASK-SHA-003
title: Document comprehensive rollback procedures
status: backlog
created: 2025-11-28T20:30:00Z
updated: 2025-11-28T20:30:00Z
priority: critical
tags: [shared-agents, rollback, documentation, phase-0, prerequisite]
complexity: 4
estimated_effort: 3h
phase: "Phase 0: Prerequisites"
depends_on: []
blocks: [TASK-SHA-P4-005]
parent_task: TASK-ARCH-DC05
task_type: implementation
---

# Task: Document Rollback Procedures

## Context

**Critical Finding from Architectural Review**: Rollback procedures are incomplete in the original proposal. Only basic revert instructions provided, no detailed recovery scenarios.

**Risk**: High severity - Without clear rollback procedures, failed migrations could leave systems broken
**Mitigation**: Document 4+ rollback scenarios with step-by-step instructions

## Description

Create comprehensive rollback documentation covering all failure scenarios identified in the architectural review. Include both automated rollback scripts and manual recovery procedures.

## Acceptance Criteria

- [ ] Document created: `docs/guides/shared-agents-rollback.md`
- [ ] 4+ rollback scenarios documented with:
  - [ ] Scenario description
  - [ ] Detection criteria (how to know rollback is needed)
  - [ ] Step-by-step rollback instructions
  - [ ] Verification steps
  - [ ] Troubleshooting guidance
- [ ] Rollback script created: `scripts/rollback-shared-agents.sh`
- [ ] All rollback scenarios tested and verified
- [ ] Documentation linked from main README
- [ ] Team training on rollback procedures completed

## Implementation Approach

### 1. Create Rollback Guide Document

Create `docs/guides/shared-agents-rollback.md`:

```markdown
# Shared Agents Rollback Guide

**Purpose**: Recover from failed shared-agents migrations
**Audience**: Developers, DevOps, Support Engineers
**Last Updated**: 2025-11-28

---

## When to Rollback

Trigger rollback if:
- Shared-agents download corrupted or invalid
- Installation breaks existing workflows
- Agent discovery fails after installation
- User data loss detected
- CI/CD builds fail after migration
- Critical bugs in new shared-agents version

**Decision Matrix**:
| Symptom | Severity | Rollback? |
|---------|----------|-----------|
| Tests failing | High | Yes, immediately |
| Slow performance | Medium | No, investigate first |
| Missing agents | High | Yes, immediately |
| Version mismatch warning | Low | No, expected behavior |

---

## Scenario 1: Bad Shared-Agents Release

**Trigger**: New shared-agents version has bugs

### Detection
```bash
# Symptoms:
# - Tasks failing with agent errors
# - Agent discovery not working
# - Tests failing after update

# Check current version
cat .claude/agents/universal/.version
# Example output: v1.1.0 (buggy version)
```

### Rollback Steps

1. **Identify last known good version**:
   ```bash
   # Check git history for previous version
   git log --all --oneline -- installer/shared-agents-version.txt

   # Example output:
   # abc123 Update shared-agents to v1.1.0 (current, buggy)
   # def456 Update shared-agents to v1.0.0 (last good)
   ```

2. **Revert version pinning file**:
   ```bash
   # Update to last known good version
   echo "v1.0.0" > installer/shared-agents-version.txt

   # Verify
   cat installer/shared-agents-version.txt
   # Should output: v1.0.0
   ```

3. **Re-run installer**:
   ```bash
   ./installer/scripts/install.sh

   # Installer will:
   # - Download v1.0.0
   # - Overwrite v1.1.0 (buggy version)
   # - Install to .claude/agents/universal/
   ```

4. **Verify rollback**:
   ```bash
   # Check version
   cat .claude/agents/universal/.version
   # Should output: v1.0.0

   # Test functionality
   /task-work TASK-001  # Should work now

   # Run tests
   pytest tests/ -v  # Should pass
   ```

5. **Report issue**:
   ```bash
   # File bug report for v1.1.0
   # Include:
   # - Symptoms observed
   # - Error messages
   # - Steps to reproduce
   ```

### Recovery Time
- **RTO**: 15 minutes
- **RPO**: No data loss (version downgrade only)

---

## Scenario 2: Broken Installer Script

**Trigger**: Installer script has syntax errors or bugs

### Detection
```bash
# Symptoms:
# - Installer fails with syntax error
# - Installation incomplete
# - Missing directories or files

# Try installation
./installer/scripts/install.sh

# Example error output:
# line 42: syntax error: unexpected token 'fi'
```

### Rollback Steps

1. **Identify last working installer**:
   ```bash
   # Check git history
   git log --oneline -- installer/scripts/install.sh

   # Example:
   # abc123 Add shared-agents support (current, broken)
   # def456 Update installer logging (last working)
   ```

2. **Revert installer script**:
   ```bash
   # Checkout last working version
   git checkout def456 -- installer/scripts/install.sh

   # Or revert specific commit
   git revert abc123
   ```

3. **Re-run fixed installer**:
   ```bash
   ./installer/scripts/install.sh

   # Should complete successfully
   ```

4. **Verify installation**:
   ```bash
   # Check directory structure
   ls -la .claude/agents/universal/

   # Check agents present
   test -f .claude/agents/universal/code-reviewer.md && echo "OK"
   ```

5. **Fix and test broken installer**:
   ```bash
   # Create fix in new branch
   git checkout -b fix/installer-syntax-error

   # Apply fix
   # ... edit installer/scripts/install.sh

   # Test fix
   ./installer/scripts/install.sh

   # Commit and PR
   git add installer/scripts/install.sh
   git commit -m "fix: Installer syntax error"
   ```

### Recovery Time
- **RTO**: 30 minutes
- **RPO**: No data loss (script fix only)

---

## Scenario 3: Corrupted Version File

**Trigger**: Version file has invalid content

### Detection
```bash
# Check version file
cat installer/shared-agents-version.txt

# Invalid formats:
# - Empty file
# - Invalid version: "invalid-version-format"
# - Non-existent version: "v99.99.99"
```

### Rollback Steps

1. **Restore valid version file**:
   ```bash
   # From git
   git checkout HEAD -- installer/shared-agents-version.txt

   # Or manually
   echo "v1.0.0" > installer/shared-agents-version.txt
   ```

2. **Manual agent installation** (if installer failed):
   ```bash
   # Download shared-agents manually
   VERSION="v1.0.0"
   curl -sL "https://github.com/guardkit/shared-agents/releases/download/$VERSION/shared-agents.tar.gz" -o /tmp/shared-agents.tar.gz

   # Verify download
   test -f /tmp/shared-agents.tar.gz && echo "Downloaded"

   # Extract to universal directory
   mkdir -p .claude/agents/universal
   tar -xz -C .claude/agents/universal --strip-components=1 < /tmp/shared-agents.tar.gz

   # Cleanup
   rm /tmp/shared-agents.tar.gz
   ```

3. **Verify installation**:
   ```bash
   # Check agents present
   ls .claude/agents/universal/*.md

   # Verify version marker
   echo "$VERSION" > .claude/agents/universal/.version
   ```

### Recovery Time
- **RTO**: 10 minutes
- **RPO**: No data loss (manual recovery)

---

## Scenario 4: Complete Rollback to Pre-Migration State

**Trigger**: Need to completely undo shared-agents migration

### Detection
- Migration caused unforeseen issues
- Need to return to pre-shared-agents architecture
- Emergency rollback required

### Rollback Steps

1. **Use automated rollback script**:
   ```bash
   ./scripts/rollback-shared-agents.sh

   # Script will:
   # - Detect latest backup
   # - Prompt for confirmation
   # - Remove universal/ directory
   # - Restore from backup
   ```

2. **Manual rollback** (if script unavailable):
   ```bash
   # Find latest backup
   BACKUP=$(ls -t .claude/agents.backup.*.tar.gz 2>/dev/null | head -1)

   if [ -n "$BACKUP" ]; then
       echo "Restoring from: $BACKUP"

       # Remove shared-agents
       rm -rf .claude/agents/universal/

       # Restore backup
       tar -xzf "$BACKUP"

       echo "Rollback complete"
   else
       echo "ERROR: No backup found"
       echo "Manual recovery required"
   fi
   ```

3. **Restore original agents** (if no backup):
   ```bash
   # Remove shared-agents directory
   rm -rf .claude/agents/universal/

   # Restore agents from git (if in version control)
   git checkout HEAD -- .claude/agents/

   # Or copy from installer/global/agents/
   # (for agents that were removed during migration)
   ```

4. **Verify pre-migration state**:
   ```bash
   # Check agents are in original location
   ls .claude/agents/*.md
   # Should list agents (not in universal/ subdirectory)

   # Check universal directory removed
   test ! -d .claude/agents/universal && echo "✅ Rollback complete"

   # Test functionality
   /task-work TASK-001
   ```

### Recovery Time
- **RTO**: 5 minutes (with backup), 30 minutes (without backup)
- **RPO**: Last backup (typically created during installation)

---

## Emergency Rollback Script

The automated rollback script handles most scenarios.

**Location**: `scripts/rollback-shared-agents.sh`

**Usage**:
```bash
# With confirmation prompt
./scripts/rollback-shared-agents.sh

# Force rollback (no prompt)
./scripts/rollback-shared-agents.sh --force

# Dry-run (show what would be done)
./scripts/rollback-shared-agents.sh --dry-run
```

**What it does**:
1. Detects latest backup
2. Prompts for confirmation (unless --force)
3. Removes .claude/agents/universal/
4. Restores from backup
5. Verifies restoration

---

## Troubleshooting

### Backup Not Found

**Problem**: Rollback script can't find backup

**Solution**:
```bash
# Search for backups manually
find . -name "agents.backup.*.tar.gz"

# If found in different location, specify path
./scripts/rollback-shared-agents.sh /path/to/backup.tar.gz

# If no backup exists, restore from git
git checkout HEAD -- .claude/agents/
```

### Partial Rollback

**Problem**: Rollback incomplete, agents still broken

**Solution**:
```bash
# Nuclear option: complete reinstall
rm -rf .claude/agents/

# Restore from git
git checkout HEAD -- .claude/agents/

# Or re-run installer from scratch
./installer/scripts/install.sh
```

### Rollback Successful but Tasks Still Failing

**Problem**: Rollback completed but functionality broken

**Solution**:
```bash
# Clear agent cache (if applicable)
rm -rf .claude/.cache/

# Restart Claude Code
# (exit and restart your IDE)

# Verify agent discovery
/agent-list  # Should show agents

# If still failing, check git status
git status .claude/agents/
# Look for uncommitted changes
```

---

## Prevention

### Before Migration
- [ ] Create backup: `./scripts/rollback-shared-agents.sh --backup-only`
- [ ] Test in staging environment first
- [ ] Review rollback procedures
- [ ] Ensure git commit of current state

### During Migration
- [ ] Monitor installation output
- [ ] Verify each step completes successfully
- [ ] Test immediately after installation
- [ ] Keep backup for 30 days

### After Migration
- [ ] Run smoke tests
- [ ] Monitor for issues for 24 hours
- [ ] Document any issues encountered
- [ ] Share learnings with team

---

## Support

**Issues**: https://github.com/guardkit/shared-agents/issues
**Slack**: #shared-agents-support
**Docs**: https://github.com/guardkit/shared-agents/blob/main/README.md

---

**Last Updated**: 2025-11-28
**Version**: 1.0
```

### 2. Create Rollback Script

Create `scripts/rollback-shared-agents.sh`:

```bash
#!/bin/bash
# rollback-shared-agents.sh
# Rollback shared-agents installation to pre-migration state

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Parse arguments
DRY_RUN=false
FORCE=false
BACKUP_PATH=""

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            ;;
        --force)
            FORCE=true
            ;;
        --backup-only)
            # Just create backup and exit
            cd "$PROJECT_ROOT"
            timestamp=$(date +%Y%m%d_%H%M%S)
            backup_file=".claude/agents.backup.$timestamp.tar.gz"
            tar -czf "$backup_file" .claude/agents/
            echo "✅ Backup created: $backup_file"
            exit 0
            ;;
        *)
            # Assume it's a backup file path
            if [ -f "$arg" ]; then
                BACKUP_PATH="$arg"
            fi
            ;;
    esac
done

cd "$PROJECT_ROOT"

echo "======================================================================="
echo "Shared Agents Rollback"
echo "======================================================================="
echo ""

# Find backup
if [ -z "$BACKUP_PATH" ]; then
    if [ -f ".claude/.last-backup" ]; then
        BACKUP_PATH=$(cat ".claude/.last-backup")
    else
        BACKUP_PATH=$(ls -t .claude/agents.backup.*.tar.gz 2>/dev/null | head -1)
    fi
fi

if [ -z "$BACKUP_PATH" ] || [ ! -f "$BACKUP_PATH" ]; then
    echo -e "${RED}❌ No backup found${NC}"
    echo ""
    echo "Expected backup location: .claude/agents.backup.<timestamp>.tar.gz"
    echo ""
    echo "Options:"
    echo "  1. Restore from git: git checkout HEAD -- .claude/agents/"
    echo "  2. Manual restore: Copy agents from another source"
    echo ""
    exit 1
fi

echo "📦 Found backup: $(basename "$BACKUP_PATH")"
echo ""

# Dry run mode
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}[DRY RUN MODE - No changes will be made]${NC}"
    echo ""
    echo "Would perform the following actions:"
    echo "  1. Remove: .claude/agents/universal/"
    echo "  2. Restore from: $BACKUP_PATH"
    echo "  3. Verify: .claude/agents/ restored"
    echo ""
    exit 0
fi

# Confirmation prompt
if [ "$FORCE" = false ]; then
    echo "⚠️  WARNING: This will:"
    echo "  - Remove shared-agents from .claude/agents/universal/"
    echo "  - Restore agents from backup: $(basename "$BACKUP_PATH")"
    echo ""
    read -p "Continue? [y/N] " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Rollback cancelled"
        exit 0
    fi
    echo ""
fi

# Perform rollback
echo "🔄 Rolling back..."

# Remove universal directory
if [ -d ".claude/agents/universal" ]; then
    echo "  - Removing .claude/agents/universal/"
    rm -rf .claude/agents/universal/
fi

# Restore from backup
echo "  - Restoring from backup..."
if tar -xzf "$BACKUP_PATH" 2>/dev/null; then
    echo -e "${GREEN}✅ Agents restored successfully${NC}"
else
    echo -e "${RED}❌ ERROR: Restoration failed${NC}"
    exit 1
fi

# Verify
echo ""
echo "🔍 Verifying rollback..."

if [ -d ".claude/agents" ] && [ ! -d ".claude/agents/universal" ]; then
    echo -e "${GREEN}✅ Rollback complete${NC}"
    echo ""
    echo "Agents restored to: .claude/agents/"
    echo "Backup preserved at: $BACKUP_PATH"
    echo ""
    echo "Next steps:"
    echo "  1. Test functionality: /task-status"
    echo "  2. Verify agents: ls .claude/agents/*.md"
    echo ""
else
    echo -e "${YELLOW}⚠️  Rollback completed with warnings${NC}"
    echo "Please verify manually: ls .claude/agents/"
    echo ""
fi

echo "======================================================================="
```

Make script executable:
```bash
chmod +x scripts/rollback-shared-agents.sh
```

### 3. Test Rollback Procedures

Create `tests/unit/test-rollback.sh`:

```bash
#!/bin/bash
# Test rollback procedures

test_scenario_1_bad_release() {
    echo "Testing Scenario 1: Bad Release Rollback"

    # Setup: Install v1.1.0 (simulate bad release)
    echo "v1.1.0" > installer/shared-agents-version.txt
    ./installer/scripts/install.sh

    # Rollback to v1.0.0
    echo "v1.0.0" > installer/shared-agents-version.txt
    ./installer/scripts/install.sh

    # Verify
    version=$(cat .claude/agents/universal/.version)
    [ "$version" = "v1.0.0" ] && echo "✅ PASS" || echo "❌ FAIL"
}

test_scenario_4_complete_rollback() {
    echo "Testing Scenario 4: Complete Rollback"

    # Setup: Create backup
    tar -czf .claude/agents.backup.test.tar.gz .claude/agents/

    # Simulate migration
    mkdir -p .claude/agents/universal

    # Rollback
    ./scripts/rollback-shared-agents.sh --force

    # Verify
    [ ! -d ".claude/agents/universal" ] && echo "✅ PASS" || echo "❌ FAIL"

    # Cleanup
    rm .claude/agents.backup.test.tar.gz
}

# Run tests
test_scenario_1_bad_release
test_scenario_4_complete_rollback
```

## Test Requirements

### Rollback Testing Checklist

- [ ] **Scenario 1**: Bad release rollback tested
- [ ] **Scenario 2**: Broken installer recovery tested
- [ ] **Scenario 3**: Corrupted version file recovery tested
- [ ] **Scenario 4**: Complete rollback tested
- [ ] Rollback script tested (all flags: --dry-run, --force, --backup-only)
- [ ] Backup creation verified
- [ ] Backup restoration verified
- [ ] Verification steps work correctly

### Edge Cases

- [ ] No backup available (manual recovery documented)
- [ ] Multiple backups present (uses latest)
- [ ] Backup corrupted (error handling)
- [ ] Permissions issues (clear error messages)

## Dependencies

**Prerequisite Tasks**: None (Phase 0)

**Blocks**: TASK-SHA-P4-005 (Rollback Testing)

**External Dependencies**:
- `tar` command
- Git (for git-based recovery)
- Bash 4.0+

## Success Criteria

- [ ] Rollback guide created: `docs/guides/shared-agents-rollback.md`
- [ ] Rollback script created: `scripts/rollback-shared-agents.sh`
- [ ] All 4 scenarios documented with step-by-step instructions
- [ ] Rollback script tested (dry-run, force, backup-only modes)
- [ ] All rollback scenarios tested and verified
- [ ] Documentation linked from README
- [ ] Team training completed

## Estimated Effort

**Total**: 3 hours
- Documentation: 1.5 hours
- Script creation: 1 hour
- Testing: 30 minutes

## Notes

### Why This Matters (from Architectural Review)

Original proposal rollback procedure:
```
1. Revert shared-agents-version.txt to previous version
2. Re-run installer
```

**Problems**:
- What if installer is broken?
- What if version file is corrupted?
- What about complete rollback?
- No automated script

**This task addresses all gaps identified in the architectural review.**

## Related Documents

- Architectural Review: `.claude/reviews/TASK-ARCH-DC05-shared-agents-architectural-review.md` (Migration Strategy section)
- Risk Mitigation Plan: `.claude/reviews/TASK-ARCH-DC05-risk-mitigation-plan.md` (Risk R2)
- Test Plan: `tests/integration/shared-agents/TEST-PLAN.md` (Scenario 8)
