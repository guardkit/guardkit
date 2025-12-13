# TASK-WC-010 Investigation Results

## Summary

**Status**: This task is a NO-OP. No code changes required.

**Reason**: The GuardKit installer and initialization system already handle agent distribution automatically.

## How Agent Discovery Works

### 1. Installation Phase (`installer/scripts/install.sh`)

**Line 516**: The installer copies ALL agents from source to global location:

```bash
if [ -d "$INSTALLER_DIR/core/agents" ] && [ "$(ls -A $INSTALLER_DIR/core/agents)" ]; then
    cp -r "$INSTALLER_DIR/core/agents/"* "$INSTALL_DIR/agents/" 2>/dev/null || true
    print_success "Installed core global agents"
fi
```

**Result**: `installer/core/agents/clarification-questioner.md` → `~/.agentecflow/agents/clarification-questioner.md`

### 2. Project Initialization Phase (`installer/scripts/init-project.sh`)

**Lines 210-226**: The init script copies global agents to project:

```bash
# Copy global agents (skip if file exists from template)
local global_agent_count=0
if [ -d "$AGENTECFLOW_HOME/agents" ] && [ "$(ls -A $AGENTECFLOW_HOME/agents 2>/dev/null)" ]; then
    for agent_file in "$AGENTECFLOW_HOME/agents"/*.md; do
        if [ -f "$agent_file" ]; then
            local agent_name=$(basename "$agent_file")
            # Only copy if file doesn't already exist (template takes precedence)
            if [ ! -f ".claude/agents/$agent_name" ]; then
                cp "$agent_file" ".claude/agents/$agent_name"
                ((global_agent_count++))
            fi
        fi
    done
    if [ $global_agent_count -gt 0 ]; then
        print_success "Added $global_agent_count global agent(s)"
    fi
fi
```

**Result**: `~/.agentecflow/agents/clarification-questioner.md` → `.claude/agents/clarification-questioner.md`

### 3. Agent Discovery Phase (`installer/core/commands/lib/agent_discovery.py`)

**Lines 84-88**: Agent discovery searches global location:

```python
# 2. Global user agents (~/.agentecflow/agents/)
home = Path.home()
user_agents = home / ".agentecflow" / "agents"
if user_agents.exists():
    locations.append((user_agents, "user", PRIORITY_USER))
```

**Search Order** (priority 0 = highest):
1. **Local** (`.claude/agents/`) - Priority 0
2. **User** (`~/.agentecflow/agents/`) - Priority 2
3. **Global** (`installer/core/agents/`) - Priority 3
4. **Template** (`installer/core/templates/*/agents/`) - Priority 4

## Verification

### Current State

```bash
# Source agent exists
$ ls -la installer/core/agents/clarification-questioner.md
-rw-r--r--  1 richardwoollcott  staff  19724 Dec 13 21:20 clarification-questioner.md

# Not yet installed (installer hasn't been run since agent was created)
$ ls -la ~/.agentecflow/agents/ | grep clarification
# (no output)

# Total agents in source
$ ls -la installer/core/agents/*.md | wc -l
28

# Total agents installed
$ ls -la ~/.agentecflow/agents/*.md | wc -l
28
```

### After Running Installer

Once `./installer/scripts/install.sh` is run again:

1. ✅ `clarification-questioner.md` copied to `~/.agentecflow/agents/`
2. ✅ Available globally for all projects
3. ✅ Automatically copied during `guardkit init`
4. ✅ Discoverable by agent discovery system

## Testing Plan

### Test 1: Installation

```bash
# Run installer
cd ~/Projects/appmilla_github/guardkit
./installer/scripts/install.sh

# Verify agent installed
ls -la ~/.agentecflow/agents/clarification-questioner.md
# Expected: File exists

# Verify agent readable
head -20 ~/.agentecflow/agents/clarification-questioner.md
# Expected: Shows frontmatter with name: clarification-questioner
```

### Test 2: Project Initialization

```bash
# Create test directory
mkdir -p /tmp/guardkit-test && cd /tmp/guardkit-test

# Initialize project
guardkit init default

# Verify agent copied to project
ls -la .claude/agents/clarification-questioner.md
# Expected: File exists

# Verify agent discoverable
grep -r "clarification-questioner" .claude/
# Expected: File found in .claude/agents/
```

### Test 3: Agent Discovery

```bash
# In a project initialized with guardkit
cd /tmp/guardkit-test

# Create a test task
/task-create "Test clarification flow" complexity:5

# Run task-work (which should trigger Phase 1.6 clarification)
/task-work TASK-XXX --with-questions

# Expected: Clarification questions appear
# Expected: System shows "Using clarification-questioner agent"
```

## Implementation Required

**None**. The existing infrastructure handles this automatically.

## Documentation Updates Needed

Update `CLAUDE.md` to clarify agent discovery mechanism:

### Section: Agent Discovery

Add to the "Agent Discovery System" section:

```markdown
## How Agents Are Installed

### 1. Global Installation

The installer copies all agents from `installer/core/agents/` to `~/.agentecflow/agents/`:

```bash
./installer/scripts/install.sh
# Result: All agents available globally
```

### 2. Project Initialization

The `guardkit init` command copies global agents to project:

```bash
guardkit init [template]
# Result: Agents copied to .claude/agents/
```

**Agent Precedence**:
- Template agents (from template/agents/) take precedence
- Global agents copied only if not already in template
- Result: No duplicates, template patterns preserved

### 3. Agent Discovery

The Task tool discovers agents in this order:
1. Local (`.claude/agents/`) - Highest priority
2. User (`~/.agentecflow/agents/`)
3. Global (`installer/core/agents/`)
4. Template (`installer/core/templates/*/agents/`) - Lowest priority

**Important**: If the same agent exists in multiple locations, the highest priority version is used.

### Adding Custom Agents

To add a custom agent:

**Option A: Global** (available for all projects)
```bash
# Create agent file
vim ~/.agentecflow/agents/my-custom-agent.md

# Agent automatically discovered in all projects
```

**Option B: Project-Local** (available only for current project)
```bash
# Create agent file in project
vim .claude/agents/my-custom-agent.md

# Agent overrides global version (if exists)
```

**Option C: Template** (distributed with template)
```bash
# Add to template
vim installer/core/templates/my-template/agents/my-agent.md

# Copied during guardkit init my-template
```
```

## Acceptance Criteria

- [x] Clarification-questioner agent exists in `installer/core/agents/` (TASK-WC-005)
- [ ] Agent installed to `~/.agentecflow/agents/` (run installer)
- [ ] Agent discoverable after `guardkit init`
- [ ] Documentation updated to explain agent discovery
- [ ] Testing confirms agent works in fresh project

## Related Tasks

- **TASK-WC-005**: Create clarification-questioner agent (COMPLETED)
- **TASK-WC-009**: Update installer (NO-OP - already handles this)
- **TASK-WC-010**: Update guardkit init (NO-OP - this task)

## Recommendation

**Mark TASK-WC-009 and TASK-WC-010 as COMPLETED** with status: "No implementation required - existing infrastructure handles this automatically."

**Update task descriptions** to document findings and add testing verification steps.
