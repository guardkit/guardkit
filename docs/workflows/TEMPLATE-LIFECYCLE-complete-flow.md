# Template Lifecycle: Complete Flow
## From Creation to Usage

**Date**: 2025-11-01
**Status**: Design Validation
**Purpose**: Sanity check integration of new template creation with existing `agentic-init` (→ `guardkit`)

---

## Overview: Three Commands, One Ecosystem

```
┌─────────────────────────────────────────────────────────────┐
│                    TEMPLATE LIFECYCLE                        │
└─────────────────────────────────────────────────────────────┘

    CREATE TEMPLATES                      USE TEMPLATES
    ├─ Brownfield                         ├─ Initialize Project
    │  /template-create                   │  agentic-init (→ guardkit)
    │                                     │
    └─ Greenfield                         └─ Apply to new project
       /template-init


FLOW:

1. Create template (brownfield or greenfield)
   ↓
2. Template saved to installer/local/templates/
   ↓
3. Use template with agentic-init <name>
   ↓
4. New project initialized with template
```

---

## Command Relationship

### Creation Commands (New - EPIC-001)

**`/template-create "name"`** - Brownfield
- Analyzes existing codebase
- Extracts patterns, naming conventions
- Generates agents based on actual code
- Creates template

**`/template-init`** - Greenfield
- Interactive Q&A (9 sections)
- AI suggests intelligent defaults
- User refines choices
- Creates template

### Usage Command (Existing)

**`agentic-init <template-name>`** (→ `guardkit`)
- Discovers available templates (global + local)
- Applies template to new project
- Sets up agents
- Initializes structure

---

## Complete Lifecycle: Brownfield Example

### Step 1: Developer has existing MAUI project

```bash
my-maui-app/
├── src/
│   ├── Domain/
│   │   └── Products/
│   │       └── GetProducts.cs
│   ├── Presentation/
│   │   ├── Views/
│   │   │   └── ProductListPage.xaml
│   │   └── ViewModels/
│   │       └── ProductListViewModel.cs
│   └── ...
└── .claude/
    └── agents/
        └── mycompany-logging-specialist.md
```

**Developer's goal**: Capture this architecture for reuse

### Step 2: Create template from existing codebase

```bash
$ cd my-maui-app
$ /template-create "mycompany-maui"

# Q&A Session
❓ Path to existing codebase: [/Users/dev/my-maui-app]
❓ What should be included? [✓] Structure [✓] Patterns [✓] Config
❓ Quality focus: [b] Extract only good patterns
# ... 8 questions total

🔍 Analyzing codebase...
✓ Language: C# / .NET MAUI 8.0
✓ Architecture: MVVM + AppShell
✓ Patterns: ErrorOr<T>, Verb-based domain operations

📦 Scanning agent sources...
✓ Found 1 custom agent in .claude/agents/
✓ Found 15 global agents

🤖 Creating project-specific agents...
✓ Created: maui-appshell-navigator
✓ Created: errror-pattern-specialist

💾 Save agents for reuse?
  maui-appshell-navigator: [y/N] y
    ✓ Saved to .claude/agents/maui-appshell-navigator.md

✅ Template created: mycompany-maui
   Location: installer/local/templates/mycompany-maui/
```

### Step 3: Template structure created

```bash
installer/local/templates/mycompany-maui/
├── manifest.json
│   {
│     "name": "mycompany-maui",
│     "version": "1.0.0",
│     "language": "C#",
│     "frameworks": [".NET MAUI 8.0"],
│     "architecture": "MVVM + AppShell",
│     "patterns": ["ErrorOr", "CQRS", "Verb-based operations"]
│   }
│
├── settings.json
│   {
│     "naming_conventions": {
│       "domain_operations": "{Verb}{Entity}",
│       "views": "{Entity}Page",
│       "viewmodels": "{Entity}ViewModel"
│     },
│     "layers": {
│       "domain": "src/Domain",
│       "presentation": "src/Presentation"
│     }
│   }
│
├── CLAUDE.md
│   # MyCompany MAUI Architecture
│
│   ## Architecture Pattern: MVVM + AppShell
│   ...
│
├── templates/
│   ├── domain/
│   │   └── query-operation.cs.template
│   ├── presentation/
│   │   ├── view.xaml.template
│   │   └── viewmodel.cs.template
│   └── ...
│
└── agents/
    ├── architectural-reviewer.md (from global)
    ├── code-reviewer.md (from global)
    ├── maui-appshell-navigator.md (generated)
    ├── errror-pattern-specialist.md (generated)
    └── mycompany-logging-specialist.md (from .claude/agents/)
```

### Step 4: Developer B uses template for new project

```bash
$ cd ~/projects
$ mkdir new-inventory-app
$ cd new-inventory-app

$ agentic-init mycompany-maui

# (Will become: guardkit mycompany-maui)

📦 Discovering templates...
  ✓ Found 5 global templates
  ✓ Found 1 local template

📋 Template: mycompany-maui
   Version: 1.0.0
   Language: C# / .NET MAUI 8.0
   Architecture: MVVM + AppShell

🤖 Setting up agents...
  ✓ Template agents: 5 specialized agents
  ✓ Global agents: 15 built-in agents
  ✓ Total: 20 agents configured

📁 Creating project structure...
  ✓ src/Domain/
  ✓ src/Presentation/Views/
  ✓ src/Presentation/ViewModels/

📄 Generating initial files...
  ✓ .claude/CLAUDE.md (architecture guide)
  ✓ .claude/agents/ (20 agents)
  ✓ .editorconfig (naming conventions)

✅ Project initialized: new-inventory-app
   Template: mycompany-maui
   Ready for development!

💡 Next steps:
   - Review .claude/CLAUDE.md for architecture guidance
   - Use agents for code generation:
     • /create domain operation GetInventoryItems
     • /create view InventoryListPage
```

### Step 5: Developer B starts working

```bash
$ cd new-inventory-app

# Project now has:
new-inventory-app/
├── src/
│   ├── Domain/
│   ├── Presentation/
│   │   ├── Views/
│   │   └── ViewModels/
│   └── ...
└── .claude/
    ├── CLAUDE.md              # Architecture guidance
    ├── agents/
    │   ├── architectural-reviewer.md
    │   ├── code-reviewer.md
    │   ├── maui-appshell-navigator.md
    │   ├── errror-pattern-specialist.md
    │   └── mycompany-logging-specialist.md
    └── commands/
        └── ... (inherited commands)

# Developer uses agents
$ # (In Claude Code)
> /create domain operation GetInventoryItems

# maui-appshell-navigator agent kicks in
# Creates: src/Domain/Inventory/GetInventoryItems.cs
# Following template pattern: {Verb}{Entity}
# Using ErrorOr<T> pattern (from template)
```

---

## Complete Lifecycle: Greenfield Example

### Step 1: Developer wants new template type

**Scenario**: Company wants standardized FastAPI template

### Step 2: Create template from scratch

```bash
$ /template-init

# Section 1: Basic Information
❓ Template name: mycompany-fastapi
❓ Description: Company standard FastAPI + SQLAlchemy template
❓ Version: 1.0.0

# Section 2: Technology Stack
❓ Primary technology: [Python]
❓ Framework: [FastAPI]
❓ Database: [PostgreSQL + SQLAlchemy]
❓ Testing framework: [pytest + pytest-asyncio]

# Section 3: Architecture & Patterns
❓ Architecture pattern: [Clean Architecture]
❓ API pattern: [RESTful]
❓ Error handling: [Result<T, Error>]

# Section 4-9: Layers, Testing, Quality, Company standards, etc.
# ... 40 questions total

🤖 Generating agents for this configuration...
  ✓ Created: fastapi-endpoint-specialist
  ✓ Created: sqlalchemy-repository-specialist
  ✓ Created: pytest-async-specialist

💾 Save agents for reuse?
  fastapi-endpoint-specialist: [y/N] y

✅ Template created: mycompany-fastapi
   Location: installer/local/templates/mycompany-fastapi/
```

### Step 3: Template structure created

```bash
installer/local/templates/mycompany-fastapi/
├── manifest.json
├── settings.json
├── CLAUDE.md
├── templates/
│   ├── api/
│   │   ├── get-endpoint.py.template
│   │   └── post-endpoint.py.template
│   ├── domain/
│   │   └── entity.py.template
│   └── repository/
│       └── repository.py.template
└── agents/
    ├── fastapi-endpoint-specialist.md
    ├── sqlalchemy-repository-specialist.md
    └── pytest-async-specialist.md
```

### Step 4: Team uses template

```bash
$ cd ~/projects/new-api-project
$ agentic-init mycompany-fastapi

📦 Discovering templates...
  ✓ Found mycompany-fastapi (local)

✅ Project initialized with mycompany-fastapi template
```

---

## Integration Points

### 1. Template Storage

**Two locations**:

```
installer/
├── global/
│   └── templates/          # Built-in templates (react, python, maui-appshell, etc.)
│       ├── react/
│       ├── python/
│       ├── maui-appshell/
│       └── ...
│
└── local/
    └── templates/          # User/team-created templates (NEW)
        ├── mycompany-maui/
        ├── mycompany-fastapi/
        └── team-microservice/
```

**Discovery priority**:
1. Local templates (user/team-created) - HIGHEST
2. Global templates (built-in)

**Why**: User's templates override built-in (can customize/extend)

### 2. Template Format

**All templates (global or local) have same structure**:

```
template-name/
├── manifest.json       # Metadata, language, frameworks, patterns
├── settings.json       # Naming conventions, layer structure
├── CLAUDE.md          # Architecture documentation
├── templates/          # Code generation templates
│   └── *.template
└── agents/            # Template-specific agents
    └── *.md
```

**Compatibility**: Templates created by `/template-create` or `/template-init` are 100% compatible with `agentic-init`

### 3. Command Flow Integration

```
┌─────────────────────────────────────────────────────────────┐
│ TEMPLATE CREATION (One-time per template)                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Brownfield:                      Greenfield:               │
│  /template-create "name"          /template-init            │
│          ↓                               ↓                  │
│    [Analyze codebase]              [Q&A session]            │
│          ↓                               ↓                  │
│    [Generate agents]               [Generate agents]        │
│          ↓                               ↓                  │
│  [Create template]                 [Create template]        │
│          ↓                               ↓                  │
│   installer/local/templates/template-name/                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ TEMPLATE USAGE (Every new project)                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  agentic-init template-name  (→ guardkit template-name)   │
│          ↓                                                   │
│  [Discover templates]                                        │
│    - Check installer/local/templates/                       │
│    - Check installer/core/templates/                      │
│          ↓                                                   │
│  [Load template]                                             │
│    - Read manifest.json, settings.json, CLAUDE.md           │
│          ↓                                                   │
│  [Apply template]                                            │
│    - Create project structure                               │
│    - Copy agents to .claude/agents/                         │
│    - Generate initial files from templates                  │
│          ↓                                                   │
│  [Initialize project]                                        │
│    - Setup .claude/ directory                               │
│    - Install commands                                       │
│    - Ready for development                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4. Agent Integration

**During template creation**:
```
/template-create "myapp"
  ↓
[Scan existing agents]
  - .claude/agents/ (user's custom)
  - installer/core/agents/ (built-in)
  ↓
[Generate missing agents]
  ↓
[Save to template]
  installer/local/templates/myapp/agents/
    ├── custom-agent.md (from .claude/agents/)
    ├── global-agent.md (from installer/core/agents/)
    └── generated-agent.md (AI-created)
```

**During template usage**:
```
agentic-init myapp
  ↓
[Load template agents]
  Read installer/local/templates/myapp/agents/*.md
  ↓
[Install to project]
  Copy to .claude/agents/
  ↓
[Agents available for use]
```

**Key insight**: Template is self-contained (includes all agents)

---

## Scenarios & Edge Cases

### Scenario 1: User has custom agent, template has different version

```bash
# User's project
.claude/agents/
└── react-specialist.md (v2.0, custom)

# Template
installer/local/templates/team-react/agents/
└── react-specialist.md (v1.0, from template)

# During agentic-init:
❓ Agent 'react-specialist' exists in both locations.
   Your version: v2.0 (custom)
   Template version: v1.0

   Which to use?
   [a] Keep your custom version (recommended)
   [b] Use template version
   [c] Keep both (rename template version)

Choice: a

✓ Using your custom react-specialist (v2.0)
```

**Resolution**: User's custom always takes precedence (confirmed design decision)

### Scenario 2: Template created on Mac, used on Windows

**No issues**:
- Templates are markdown/JSON (cross-platform)
- Paths use forward slashes (works on both)
- No OS-specific dependencies

### Scenario 3: Team collaboration

```bash
# Developer A creates template
$ /template-create "team-backend"
$ git add installer/local/templates/team-backend/
$ git commit -m "Add team backend template"
$ git push

# Developer B uses template
$ git pull
$ cd new-project
$ agentic-init team-backend
  ✓ Using local template: team-backend (from team)
```

**Works seamlessly**: Templates in git, shared across team

### Scenario 4: Global template exists with same name

```bash
# Global template
installer/core/templates/react/

# User creates local template
$ /template-create "react"
  ⚠️  Warning: Global template 'react' already exists.
  Your local template will take precedence.
  Continue? [y/N] y

# Later: agentic-init react
📦 Discovering templates...
  ✓ Found 'react' (local) - will use this
  ℹ️  Also found 'react' (global) - skipped

✓ Using local template: react
```

**Resolution**: Local templates override global (user control)

---

## Command Renaming: agentic-init → guardkit

### Current (Before Rename)

```bash
agentic-init <template-name>
```

### After Rename

```bash
guardkit <template-name>
```

**OR** (more explicit):

```bash
guardkit init <template-name>
```

**Rationale**: Shorter, consistent with project name

### Backwards Compatibility

```bash
# Keep alias for backwards compatibility
alias agentic-init='guardkit'
```

---

## Summary: Does This Make Sense?

### ✅ Clean Separation of Concerns

1. **Template Creation** (One-time):
   - `/template-create` - Capture existing codebase
   - `/template-init` - Design from scratch

2. **Template Usage** (Every project):
   - `agentic-init` (→ `guardkit`) - Initialize new project

### ✅ Consistent Template Format

- Both creation methods produce identical structure
- Compatible with existing `agentic-init` command
- No changes needed to `agentic-init` for compatibility

### ✅ Agent Integration

- Templates are self-contained (include agents)
- User's custom agents take precedence
- Agents available immediately after init

### ✅ Team Collaboration

- Templates in git (sharable)
- Local templates override global
- Consistent across team

### ✅ Discovery & Priority

```
Priority:
1. installer/local/templates/ (user/team templates)
2. installer/core/templates/ (built-in templates)

Agent Priority (within project):
1. .claude/agents/ (user's custom)
2. Template agents (from template)
3. installer/core/agents/ (built-in)
```

---

## Potential Issues & Solutions

### Issue 1: Template name conflicts

**Problem**: User creates local template with same name as global

**Solution**:
- Warn user during creation
- Local takes precedence (user control)
- User can rename if desired

### Issue 2: Template version updates

**Problem**: User creates template v1.0, later wants v2.0

**Solution**:
- Re-run `/template-create` with same name
- Prompt: `[O] Overwrite, [M] Merge, [C] Cancel`
- Version in manifest.json tracks changes

### Issue 3: Agent version conflicts

**Problem**: User's custom agent conflicts with template agent

**Solution** (Already decided):
- User's custom always takes precedence
- Notify user during `agentic-init`
- User can choose to keep both (rename one)

### Issue 4: Template portability

**Problem**: Template created on one machine, used on another

**Solution**:
- Templates are JSON/markdown (portable)
- No absolute paths (use relative)
- Cross-platform compatible

---

## Changes Needed to Existing `agentic-init`

### Minimal Changes Required

**1. Template Discovery** (Minor update):
```python
def discover_templates():
    """Discover templates from local and global"""
    templates = []

    # Check local first (PRIORITY)
    local_path = Path("installer/local/templates")
    if local_path.exists():
        templates.extend(scan_directory(local_path, source="local"))

    # Check global
    global_path = Path("installer/core/templates")
    if global_path.exists():
        templates.extend(scan_directory(global_path, source="global"))

    return templates
```

**2. Agent Installation** (Already works):
```python
def install_agents(template_path: Path, project_path: Path):
    """Install agents from template to project"""
    agents_src = template_path / "agents"
    agents_dst = project_path / ".claude/agents"

    # Copy all agents
    for agent_file in agents_src.glob("*.md"):
        # Check if user already has this agent
        dst_file = agents_dst / agent_file.name
        if dst_file.exists():
            # User's custom exists - ask what to do
            choice = prompt_user(f"Agent {agent_file.stem} exists...")
            # Handle based on choice
        else:
            # Copy template agent
            shutil.copy(agent_file, dst_file)
```

**3. No other changes needed** ✅

---

## Validation Checklist

### Template Creation (Brownfield)
- [ ] `/template-create` analyzes existing codebase
- [ ] Agents generated from actual code
- [ ] Template saved to `installer/local/templates/`
- [ ] Compatible with `agentic-init`

### Template Creation (Greenfield)
- [ ] `/template-init` runs Q&A session
- [ ] AI generates intelligent defaults
- [ ] Template saved to `installer/local/templates/`
- [ ] Compatible with `agentic-init`

### Template Usage
- [ ] `agentic-init` discovers local templates
- [ ] Local templates take precedence over global
- [ ] Template agents installed to project
- [ ] User's custom agents take precedence

### Team Collaboration
- [ ] Templates sharable via git
- [ ] Templates work across platforms
- [ ] Consistent experience across team

### Edge Cases
- [ ] Template name conflicts handled
- [ ] Agent version conflicts handled
- [ ] Template portability verified

---

## Recommendation

**✅ Design is sound!**

The integration between template creation (`/template-create`, `/template-init`) and template usage (`agentic-init` → `guardkit`) is clean and logical:

1. **Clear separation**: Creation vs usage
2. **Compatible format**: Both creation methods produce same structure
3. **Minimal changes**: `agentic-init` needs minor update for local template discovery
4. **User control**: Custom agents, local templates take precedence
5. **Team-friendly**: Git-based sharing works seamlessly

**No major issues identified.** The flow makes sense end-to-end.

---

**Created**: 2025-11-01
**Status**: ✅ **VALIDATED** - Flow makes sense
**Changes Needed**: Minimal (template discovery in `agentic-init`)
**Ready**: Yes, proceed with implementation
