---
id: TASK-SHA-003
title: Update TaskWright installer to use shared-agents
status: backlog
created: 2025-11-28T21:00:00Z
updated: 2025-11-28T21:00:00Z
priority: high
tags: [shared-agents, guardkit, installer, lean]
complexity: 3
estimated_effort: 2h
depends_on: [TASK-SHA-002]
blocks: [TASK-SHA-005]
parent_task: TASK-ARCH-DC05
task_type: implementation
---

# Task: Update TaskWright Installer

## Context

Update TaskWright's installer to download shared-agents from the new repository instead of using local copies.

## Acceptance Criteria

- [ ] Version pinning file created: `installer/shared-agents-version.txt`
- [ ] Installer function added to download shared-agents
- [ ] Agents installed to `.claude/agents/universal/`
- [ ] Duplicate agents removed from `installer/global/agents/`
- [ ] Installer tested successfully

## Implementation

### 1. Create Version Pinning File

```bash
# installer/shared-agents-version.txt
echo "v1.0.0" > installer/shared-agents-version.txt
git add installer/shared-agents-version.txt
```

### 2. Add Install Function

Add to `installer/scripts/install.sh`:

```bash
install_shared_agents() {
    echo ""
    echo "📦 Installing shared agents..."

    # Read version
    local version=$(cat "$SCRIPT_DIR/../shared-agents-version.txt" 2>/dev/null || echo "v1.0.0")
    local url="https://github.com/guardkit/shared-agents/releases/download/$version/shared-agents.tar.gz"
    local target_dir="$PROJECT_ROOT/.claude/agents/universal"

    # Create directory
    mkdir -p "$target_dir"

    # Download and extract
    if curl -sL "$url" | tar -xz -C "$target_dir" --strip-components=1 2>/dev/null; then
        echo "✅ Shared agents $version installed"
    else
        echo "❌ Failed to install shared agents"
        echo "   This may affect task execution"
        return 1
    fi
}

# Call during installation (add near end of install script)
install_shared_agents || echo "Warning: Shared agents installation failed"
```

### 3. Remove Duplicate Agents

```bash
# Remove agents that are now in shared-agents
# (Based on verified list from TASK-SHA-001)

# Example:
rm installer/global/agents/code-reviewer.md
rm installer/global/agents/test-orchestrator.md
# ... remove others from verified list

git add installer/global/agents/
git commit -m "refactor: Move universal agents to shared-agents repo"
```

### 4. Test Installation

```bash
# Create fresh test project
mkdir test-guardkit
cd test-guardkit

# Run installer
../installer/scripts/install.sh

# Verify
ls -la .claude/agents/universal/
# Should contain shared agents

# Test functionality
/task-create "Test task"
/task-work TASK-001
# Should work normally
```

## Test Requirements

- [ ] Version file readable
- [ ] Download succeeds
- [ ] Extraction works
- [ ] Agents accessible in `.claude/agents/universal/`
- [ ] Task commands work (agent discovery finds shared agents)
- [ ] No regression in functionality

## Estimated Effort

**2 hours**
- Code changes: 1 hour
- Testing: 30 minutes
- Cleanup: 30 minutes

## Success Criteria

- [ ] Installer downloads shared-agents successfully
- [ ] Shared agents installed to correct location
- [ ] Duplicate agents removed from repository
- [ ] All tests pass
- [ ] No regression in task commands

## Notes

**Keep it simple**: Basic curl + tar extraction is enough. We don't need:
- ❌ Retry logic (if download fails, user can re-run)
- ❌ Checksum validation (GitHub is reliable)
- ❌ Elaborate error handling (simple fail message is fine)
- ❌ Fallback mechanism (handle edge cases if they occur)

**Error handling**: If download fails, installer prints error but continues. User can investigate and re-run if needed.
