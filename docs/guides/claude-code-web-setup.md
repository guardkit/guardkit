# Using Taskwright with Claude Code Web

## Overview

Taskwright is fully compatible with **Claude Code Web** (claude.ai/code), providing a complete AI-assisted development workflow with quality gates directly in your browser. This guide covers installation, persistence, and best practices for using Taskwright across multiple repositories.

## Table of Contents

- [How It Works](#how-it-works)
- [Installation](#installation)
- [Persistence Across Sessions](#persistence-across-sessions)
- [Multi-Repository Usage](#multi-repository-usage)
- [Working Directory Requirements](#working-directory-requirements)
- [Integration with RequireKit](#integration-with-requirekit)
- [Available Commands](#available-commands)
- [Troubleshooting](#troubleshooting)
- [Quick Reference](#quick-reference)

---

## How It Works

### Architecture

Taskwright uses Claude Code's **slash command system** and **agent framework**:

```
/root/.agentecflow/          # Global installation (persistent storage)
├── commands/                # Command definitions (.md files)
│   ├── task-create.md      → /task-create
│   ├── task-work.md        → /task-work
│   ├── task-complete.md    → /task-complete
│   └── ...
├── agents/                  # AI agent definitions (.md files)
│   ├── task-manager.md
│   ├── code-reviewer.md
│   ├── test-verifier.md
│   └── ...
└── templates/               # Stack templates (react, python, .NET, etc.)

/root/.claude/               # Claude Code configuration
├── commands -> /root/.agentecflow/commands  # Symlink
└── agents -> /root/.agentecflow/agents      # Symlink
```

### Command Discovery Process

1. **On startup**, Claude Code scans `~/.claude/commands/` for `.md` files
2. **Each .md file** becomes a slash command (filename determines command name)
3. **Commands are registered** and available for autocomplete
4. **Agents are loaded** from `~/.claude/agents/` for specialized tasks

### Why This Works in Web

- **Persistent file system**: `/root/` and `/home/user/` persist across sessions
- **No installation required**: Slash commands are markdown files, not executables
- **Browser-based**: All operations use Claude Code's built-in tools (Bash, Read, Write, Edit)
- **Full functionality**: Access to all Taskwright features without limitations

---

## Installation

### One-Time Setup

Run the installation script from the Taskwright repository:

```bash
# 1. Navigate to taskwright repository
cd /home/user/taskwright

# 2. Run installer (creates global installation)
./installer/scripts/install.sh
```

### What Gets Installed

**Global Components** (`~/.agentecflow/`):
- **Commands**: 9 slash commands (task-create, task-work, etc.)
- **Agents**: 55 AI agents (14 global + 41 stack-specific)
- **Templates**: 6 high-quality templates (react-typescript, fastapi-python, nextjs-fullstack, react-fastapi-monorepo, taskwright-python, default)
- **Libraries**: Python modules for complexity evaluation, plan rendering
- **Documentation**: Methodology instructions and references

**Claude Code Integration** (`~/.claude/`):
- **Symlinks** to commands and agents directories
- Enables automatic command discovery
- Compatible with Conductor.build for parallel development

**Shell Integration** (`~/.bashrc`):
- PATH configuration for CLI commands (`taskwright`, `taskwright-init`)
- Environment variables (`AGENTECFLOW_HOME`)

### Installation Output

```
✅ Installation Complete!

Installed Components:
- 9 slash commands available
- 55 AI agents (14 global + 41 stack-specific)
- 4 high-quality project templates
- Python dependencies (Jinja2, python-frontmatter)

Commands Available:
- /task-create
- /task-work
- /task-complete
- /task-status
- /task-refine
- /debug
- /figma-to-react
- /zeplin-to-maui
- /mcp-zeplin

Installation size: ~4.0 MB
```

### Verification

Verify installation success:

```bash
# Check installation directory
ls -la ~/.agentecflow/
# Should show: agents, bin, commands, templates, etc.

# Check Claude Code symlinks
ls -la ~/.claude/
# Should show: commands -> /root/.agentecflow/commands
#              agents -> /root/.agentecflow/agents

# List available commands
ls -1 ~/.claude/commands/*.md
# Should show all 9 command files

# List available agents
ls -1 ~/.claude/agents/*.md | head -10
# Should show agent definitions
```

---

## Persistence Across Sessions

### How Persistence Works

**File System Persistence:**
- Claude Code Web provides persistent storage in `/root/` and `/home/user/`
- Installation creates files that **survive session restarts**
- No re-installation needed for future sessions

**Automatic Command Loading:**
```
Session Start → Claude Code scans ~/.claude/commands/
             → Registers slash commands
             → Loads agent definitions
             → Commands immediately available
```

### What Persists

✅ **Persists Across Sessions:**
- All installed commands and agents
- Project files and code
- Task states and history
- Implementation plans
- Configuration settings

❌ **Does NOT Persist:**
- Running processes (background tasks)
- Environment variables (set via `export` in shell)
- Temporary files in `/tmp/`

### Testing Persistence

**In Current Session:**
```bash
# Verify installation
ls ~/.claude/commands/task-work.md
# Output: /root/.claude/commands/task-work.md
```

**In Future Sessions:**
```bash
# Commands automatically available
/task-status
# Should work immediately without re-installation
```

### Re-installation

**Not Required!** Installation is one-time only.

**When to Re-install:**
- Upgrading to a new Taskwright version
- Fixing corrupted installation
- Adding new templates or agents

---

## Multi-Repository Usage

### Global Availability

Commands are available in **all repositories**:

```bash
# Taskwright repository
cd /home/user/taskwright
/task-status    # ✅ Works

# RequireKit repository
cd /home/user/requirekit
/task-status    # ✅ Works

# Any other project
cd /home/user/my-project
/task-status    # ✅ Works
```

### Command Scope

| Command | Available Globally? | Notes |
|---------|-------------------|-------|
| `/task-create` | ✅ Yes | Creates tasks in current directory's `tasks/` folder |
| `/task-status` | ✅ Yes | Shows tasks from current directory |
| `/task-work` | ✅ Yes | **Must run from project root** (see below) |
| `/task-complete` | ✅ Yes | Works on tasks in current directory |
| `/task-refine` | ✅ Yes | Works on tasks in current directory |
| `/debug` | ✅ Yes | Troubleshooting for current context |

### Repository-Specific Usage

**Taskwright Development:**
```bash
cd /home/user/taskwright
/task-status                  # View taskwright tasks
/task-work TASK-002          # Implement taskwright feature
/task-complete TASK-002      # Complete taskwright task
```

**RequireKit Development:**
```bash
cd /home/user/requirekit
/task-status                  # View requirekit tasks
/task-work REQ-TASK-001      # Implement requirekit feature
/task-complete REQ-TASK-001  # Complete requirekit task
```

**Other Projects:**
```bash
cd /home/user/my-web-app
taskwright init react-typescript  # Initialize with React template
/task-create "Add user auth"  # Create task in this project
/task-work TASK-001          # Implement in this project
```

---

## Working Directory Requirements

### Critical: Run from Project Root

**The `/task-work` command MUST be run from your project's root directory** where source code should be created.

### Why This Matters

`/task-work` uses the **current working directory** to:

1. **Detect technology stack**
   - Looks for `.csproj` → .NET project
   - Looks for `package.json` → Node.js/TypeScript project
   - Looks for `requirements.txt` → Python project

2. **Create source files**
   - Implements code in correct directories
   - Follows project structure conventions

3. **Run tests and builds**
   - Executes stack-specific test commands
   - Validates compilation and coverage

4. **Generate artifacts**
   - Creates implementation plans in `.claude/task-plans/`
   - Updates task states in `tasks/` folders

### Correct Usage Examples

✅ **Correct - Working on Taskwright Tasks:**
```bash
# 1. Navigate to taskwright project
cd /home/user/taskwright
pwd  # Verify: /home/user/taskwright

# 2. Confirm you see project files
ls   # Should show: installer/, tasks/, README.md, etc.

# 3. Work on task
/task-work TASK-001
# Creates files in /home/user/taskwright/
# Detects: Python/Shell project
```

✅ **Correct - Working on RequireKit Tasks:**
```bash
# 1. Navigate to requirekit project
cd /home/user/requirekit
pwd  # Verify: /home/user/requirekit

# 2. Confirm you see project files
ls   # Should show: requirements.txt, src/, tests/, etc.

# 3. Work on task
/task-work TASK-042
# Creates files in /home/user/requirekit/
# Detects: Python project with pytest
```

### Incorrect Usage Examples

❌ **Wrong - Files Go to Wrong Location:**
```bash
# In taskwright directory, working on requirekit task
cd /home/user/taskwright
/task-work REQ-TASK-001
# Problem: Creates files in taskwright/ instead of requirekit/
# Problem: Detects wrong tech stack
```

❌ **Wrong - Wrong Tech Stack Detected:**
```bash
# In wrong directory
cd /home/user/
/task-work TASK-001
# Problem: Can't detect technology stack
# Problem: Doesn't know where to create files
```

### Directory Validation

**Before running `/task-work`, verify location:**

```bash
# Check current directory
pwd

# List project files (should see your project's main files)
ls -la

# For .NET projects, should see:
ls *.csproj 2>/dev/null

# For Node.js projects, should see:
ls package.json 2>/dev/null

# For Python projects, should see:
ls requirements.txt 2>/dev/null || ls setup.py 2>/dev/null
```

### Quick Validation Script

```bash
# Verify you're in a project root
if [ -f "*.csproj" ] || [ -f "package.json" ] || [ -f "requirements.txt" ]; then
    echo "✅ In project root - safe to run /task-work"
else
    echo "❌ Not in project root - navigate to project first!"
fi
```

---

## Integration with RequireKit

### Automatic Detection

Taskwright automatically detects if RequireKit is installed and enhances workflow:

**Taskwright Only:**
- Task workflow with quality gates
- Implementation planning
- Architectural review
- Test enforcement

**Taskwright + RequireKit:**
- All the above PLUS:
- Loads EARS requirements automatically
- Includes Gherkin scenarios for BDD
- Epic/feature context and hierarchy
- Requirements-based acceptance criteria

### No Configuration Required

Detection is automatic - just install both packages:

```bash
# Install Taskwright (already done)
cd /home/user/taskwright
./installer/scripts/install.sh

# Install RequireKit (optional)
cd /home/user/requirekit
./installer/scripts/install.sh

# Both commands now available everywhere
# Integration happens automatically
```

### Usage Pattern

**Create requirement in RequireKit:**
```bash
cd /home/user/requirekit
/req-create "User authentication system"
# Creates: REQ-001
```

**Create linked task in your project:**
```bash
cd /home/user/my-web-app
/task-create "Implement user auth" requirements:[REQ-001]
# Creates: TASK-001 linked to REQ-001
```

**Work on task (from project directory):**
```bash
cd /home/user/my-web-app
/task-work TASK-001
# Automatically loads REQ-001 context
# Implements in /home/user/my-web-app/
```

### Benefits of Integration

| Feature | Taskwright Only | Taskwright + RequireKit |
|---------|----------------|------------------------|
| Task workflow | ✅ | ✅ |
| Quality gates | ✅ | ✅ |
| EARS requirements | ❌ | ✅ |
| Gherkin scenarios | ❌ | ✅ |
| Epic/feature hierarchy | ❌ | ✅ |
| Requirements traceability | ❌ | ✅ |
| BDD workflow | ❌ | ✅ |

---

## Available Commands

### Task Management Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/task-create` | Create a new task | `/task-create "Add login feature"` |
| `/task-work` | Execute task workflow (Phases 2-5.5) | `/task-work TASK-001` |
| `/task-complete` | Mark task as complete and archive | `/task-complete TASK-001` |
| `/task-status` | View task status and summary | `/task-status TASK-001` |
| `/task-refine` | Lightweight improvements without re-work | `/task-refine TASK-001` |
| `/task-review` | Analysis and decision workflows | `/task-review TASK-001 --mode=architectural --depth=standard` |

### Design Integration Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/figma-to-react` | Convert Figma designs to React components | `/figma-to-react <file-key>` |
| `/zeplin-to-maui` | Convert Zeplin designs to .NET MAUI | `/zeplin-to-maui <project-id> <screen-id>` |
| `/mcp-zeplin` | Zeplin MCP integration utilities | `/mcp-zeplin` |

### Utility Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/debug` | Troubleshoot issues and check configuration | `/debug` |

### Task Work Options

```bash
# Standard mode (default)
/task-work TASK-001

# TDD mode (test-driven development)
/task-work TASK-001 --mode=tdd

# Design-first workflow (complex tasks)
/task-work TASK-001 --design-only
# [Review and approve plan]
/task-work TASK-001 --implement-only
```

### Command Flags

| Flag | Description | Use Case |
|------|-------------|----------|
| `--mode=standard` | Implementation + tests together (default) | Straightforward features |
| `--mode=tdd` | Test-Driven Development (Red → Green → Refactor) | Complex business logic |
| `--design-only` | Planning phase only (Phases 2-2.8) | Complex tasks requiring review |
| `--implement-only` | Implementation phase only (Phases 3-5) | After design approval |

---

## Troubleshooting

### Commands Not Found

**Problem:** Slash commands don't appear in autocomplete

**Solutions:**
```bash
# 1. Verify installation
ls ~/.claude/commands/
# Should show: task-create.md, task-work.md, etc.

# 2. Check symlinks
readlink ~/.claude/commands
# Should show: /root/.agentecflow/commands

# 3. Re-create symlinks if broken
mkdir -p ~/.claude
ln -sf /root/.agentecflow/commands ~/.claude/commands
ln -sf /root/.agentecflow/agents ~/.claude/agents

# 4. Verify Claude Code can read files
cat ~/.claude/commands/task-work.md | head -20
# Should show command definition
```

### Wrong Directory Errors

**Problem:** `/task-work` creates files in wrong location

**Solution:**
```bash
# Always verify location before running /task-work
pwd
ls -la

# Navigate to correct project root
cd /home/user/your-project

# Verify you see project files
ls package.json  # or *.csproj, requirements.txt, etc.

# Now run task-work
/task-work TASK-001
```

### Tech Stack Misdetected

**Problem:** Taskwright detects wrong technology stack

**Cause:** Running from wrong directory

**Solution:**
```bash
# Ensure you're in project root with correct markers
cd /home/user/your-project

# For .NET projects, verify:
ls *.csproj

# For Node.js projects, verify:
ls package.json

# For Python projects, verify:
ls requirements.txt
```

### Tasks Not Found

**Problem:** `/task-status` shows no tasks

**Possible Causes:**
1. No `tasks/` directory in current location
2. Tasks in different repository
3. Running from wrong directory

**Solution:**
```bash
# Check if tasks/ directory exists
ls -la tasks/

# Verify task files exist
ls -la tasks/backlog/
ls -la tasks/in_progress/

# Navigate to correct repository
cd /home/user/taskwright  # or requirekit, or your project
/task-status
```

### Installation Issues

**Problem:** Installation script fails

**Solution:**
```bash
# 1. Check prerequisites
python3 --version  # Should be 3.7+
node --version     # Optional but recommended

# 2. Check permissions
ls -la installer/scripts/install.sh
# Should be executable (-rwxr-xr-x)

# 3. Re-run with explicit bash
bash installer/scripts/install.sh

# 4. Check installation log
tail -50 ~/.agentecflow/installation.log  # If exists
```

### Commands Work But No Output

**Problem:** Commands execute but produce no visible results

**Possible Causes:**
1. Command is running but needs time to complete
2. Error occurred but wasn't displayed
3. Output is being written elsewhere

**Solution:**
```bash
# 1. Check command output explicitly
/task-status 2>&1

# 2. Verify task files
ls -la tasks/backlog/

# 3. Check for error logs
ls -la ~/.agentecflow/logs/  # If exists

# 4. Run debug command
/debug
```

---

## Quick Reference

### Installation Checklist

- [ ] Navigate to taskwright repository
- [ ] Run `./installer/scripts/install.sh`
- [ ] Verify symlinks: `ls -la ~/.claude/`
- [ ] Test command: `/task-status`
- [ ] Verify 9 commands available
- [ ] Verify 55 agents installed

### Pre-Flight Checklist (Before /task-work)

- [ ] Navigate to project root: `cd /home/user/your-project`
- [ ] Verify location: `pwd`
- [ ] Check project files exist: `ls`
- [ ] Confirm task exists: `ls tasks/backlog/TASK-XXX*`
- [ ] Run command: `/task-work TASK-XXX`

### Common Workflows

**Simple Task:**
```bash
cd /home/user/your-project
/task-create "Feature name"
/task-work TASK-001
/task-complete TASK-001
```

**Complex Task with Design Review:**
```bash
cd /home/user/your-project
/task-create "Complex refactoring" priority:high
/task-work TASK-002 --design-only
# [Review plan in .claude/task-plans/]
/task-work TASK-002 --implement-only
/task-complete TASK-002
```

**TDD Workflow:**
```bash
cd /home/user/your-project
/task-create "Calculate tax rates"
/task-work TASK-003 --mode=tdd
/task-complete TASK-003
```

### Directory Structure Reference

```
/root/.agentecflow/              # Global installation
├── agents/                      # 55 AI agents
├── commands/                    # 9 slash commands
├── templates/                   # 6 high-quality templates
└── bin/                        # CLI commands (taskwright, tw)

/root/.claude/                   # Claude Code config
├── commands -> ../agentecflow/commands
└── agents -> ../agentecflow/agents

/home/user/taskwright/           # Taskwright repository
├── tasks/
│   ├── backlog/
│   ├── in_progress/
│   └── completed/
├── .claude/
│   └── task-plans/
└── installer/

/home/user/requirekit/           # RequireKit repository (optional)
├── requirements/
├── tasks/
└── .claude/

/home/user/your-project/         # Your project
├── tasks/                       # Created by taskwright init
├── .claude/                     # Created by taskwright init
├── src/                        # Your source code
└── tests/                      # Your tests
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Global Installation** | Commands available in all repositories |
| **Working Directory** | Must be project root for /task-work |
| **Persistence** | Installation survives session restarts |
| **Auto-Detection** | RequireKit integration automatic |
| **Symlinks** | Claude Code reads from ~/.claude/ |
| **Stack Templates** | 4 high-quality reference templates + custom via /template-create |

### Command Hierarchy

```
All Commands Available Globally
    ↓
Task Commands Need Project Context
    ↓
/task-work Needs Project Root Directory
    ↓
Creates Files in Current Directory
    ↓
Detects Tech Stack from Current Directory
```

### Getting Help

**Documentation:**
- [Taskwright Workflow](taskwright-workflow.md) - Complete workflow guide
- [Quick Reference](quick-reference.md) - Command cheat sheet
- [Creating Local Templates](creating-local-templates.md) - Custom templates
- [MAUI Template Selection](maui-template-selection.md) - .NET MAUI guidance

**Commands:**
```bash
/debug                    # Troubleshooting and diagnostics
/task-status             # View all tasks
/task-status TASK-001    # View specific task
```

**Verification:**
```bash
# Check installation
ls ~/.agentecflow/
ls ~/.claude/commands/

# Test commands
/task-status

# Verify agents
ls ~/.claude/agents/
```

---

## Summary

**Taskwright works seamlessly with Claude Code Web:**

✅ **One-time installation** - Persists across all sessions
✅ **Global commands** - Available in all repositories
✅ **Multi-repository support** - Use with taskwright, requirekit, and your projects
✅ **Full functionality** - No limitations compared to desktop
✅ **Automatic integration** - RequireKit detection when both installed
✅ **Quality gates** - 80% coverage, 100% test pass, architectural review

**Remember:**
- Install once, use everywhere
- Always run `/task-work` from project root directory
- Commands persist across Claude Code Web sessions
- No re-installation needed

**Ready to start:**
```bash
cd /home/user/your-project
/task-create "Your feature"
/task-work TASK-001
/task-complete TASK-001
```

Happy building! 🚀
