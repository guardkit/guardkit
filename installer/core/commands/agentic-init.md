# /agentic-init Command

## Overview

The `/agentic-init` command initializes projects using templates discovered from both personal and repository locations, with personal templates taking precedence.

**Purpose**: Enable users to quickly initialize new projects using templates they've created with `/template-create` or `/template-init`, or built-in repository templates.

**Key Feature**: Personal templates (user-created) automatically override repository templates (built-in) with the same name.

## Usage

```bash
/agentic-init [template-name]
```

### Arguments

- `template-name` (optional): Name of template to use. If not provided, shows interactive selection UI.

### Examples

```bash
# Interactive selection from all available templates
/agentic-init

# Initialize with specific template
/agentic-init my-react-template

# Initialize with built-in template
/agentic-init react
```

## Workflow

The command executes 5 phases automatically:

### Phase 1: Template Discovery

Discovers templates from two locations with priority:

1. **Personal templates** (`~/.agentecflow/templates/`)
   - Created with `/template-create` or `/template-init`
   - User-specific customizations
   - **Takes precedence** over repository templates

2. **Repository templates** (`installer/core/templates/`)
   - Built-in templates (react, python, maui-appshell, etc.)
   - Distributed with the system
   - Used if no personal template with same name exists

**Priority Rule**: If a personal template has the same name as a repository template, the personal version is used and the repository version is ignored.

**Duration**: <1 second

### Phase 2: Template Selection

**Interactive Mode** (no template name provided):
- Lists all available templates grouped by source
- Shows personal templates first
- Displays template metadata (version, language, frameworks, architecture)
- Allows selection by number or name

**Direct Mode** (template name provided):
- Finds template by exact name match
- Uses personal version if both exist
- Shows error if template not found

**Duration**: Varies (user interaction)

### Phase 3: Template Information

Displays selected template details:
- Name and version
- Source (personal vs repository)
- Language and frameworks
- Architecture pattern
- Description

**Duration**: <1 second

### Phase 4: Project Structure

Copies template structure to project:
- `manifest.json` → `.claude/manifest.json`
- `settings.json` → `.claude/settings.json`
- `CLAUDE.md` → project root
- `templates/` → project root (if exists)

**Duration**: <1 second

### Phase 5: Agent Installation

Installs agents with conflict detection:
- Copies agents from template to `.claude/agents/`
- **Conflict Resolution** (if agent already exists):
  - Option A: Keep your version (recommended)
  - Option B: Use template version
  - Option C: Keep both (rename template version)

**Duration**: <5 seconds (with conflicts)

## Output Example

```
============================================================
  Agentic Init - Project Initialization
============================================================

============================================================
  Phase 1: Template Discovery
============================================================

📦 Discovering templates...
  ✓ Found 2 personal template(s)
  ✓ Found 5 repository template(s)

📊 Total: 7 available template(s)

============================================================
  Phase 2: Template Selection
============================================================

📋 Available Templates:
============================================================

👤 Personal Templates:

  [1] mycompany-react (v2.0.0)
      Company React + TypeScript template
      TypeScript + React, Vite, Tailwind
      Architecture: Component-based

  [2] team-backend (v1.5.0)
      Backend microservice template
      C# + ASP.NET Core 8.0
      Architecture: Clean Architecture

📦 Repository Templates (Built-in):

  [3] python (v1.0.0)
      Python + FastAPI template
      Python + FastAPI, pytest

  [4] maui-appshell (v1.0.0)
      .NET MAUI with AppShell navigation
      C# + .NET MAUI 8.0

  [5] maui-navigationpage (v1.0.0)
      .NET MAUI with NavigationPage
      C# + .NET MAUI 8.0

  [6] dotnet-fastendpoints (v1.0.0)
      .NET + FastEndpoints + REPR pattern
      C# + ASP.NET Core 8.0

  [7] react (v1.0.0)
      React + TypeScript + Vite template
      TypeScript + React, Vite

============================================================

Select template (number or name) [or 'q' to quit]: 1

============================================================
  Phase 3: Template Information
============================================================

📋 Template: mycompany-react
   Version: 2.0.0
   Source: personal (~/.agentecflow/templates/)
   Language: TypeScript
   Frameworks: React, Vite, Tailwind
   Architecture: Component-based

============================================================
  Phase 4: Project Structure
============================================================

📂 Copying template structure...
  ✓ Copied manifest.json
  ✓ Copied settings.json
  ✓ Copied CLAUDE.md

✅ Template structure copied successfully

============================================================
  Phase 5: Agent Installation
============================================================

🤖 Installing agents...
  ✓ Installed: architectural-reviewer.md
  ✓ Installed: code-reviewer.md

  ⚠️  Agent 'react-specialist' already exists
      Your version: .claude/agents/react-specialist.md
      Template version: template/agents/react-specialist.md
      [a] Keep your version (recommended)
      [b] Use template version
      [c] Keep both (rename template version)
      Choice [a/b/c]: a
      ✓ Keeping your version

  ✓ Installed: test-verifier.md

✅ Total agents: 18

============================================================
  Initialization Complete
============================================================

✅ Project initialized successfully!
   Template: mycompany-react
   Location: /Users/developer/my-new-project
```

## Features

### Dual-Source Discovery

- **Personal templates**: User-created, immediate use
- **Repository templates**: Built-in, system-wide
- **Automatic priority**: Personal overrides repository

### Interactive Selection

- Grouped display (personal vs repository)
- Rich metadata (version, language, frameworks, architecture)
- Selection by number or name
- Quit option ('q')

### Agent Conflict Detection

When installing agents, conflicts are detected and user can choose:
- **Keep existing**: Preserves user's custom agent (recommended)
- **Use template**: Replaces with template version
- **Keep both**: Saves template version with `-template` suffix

### Graceful Error Handling

- Missing directories: Silently skipped (personal templates may not exist)
- Invalid manifests: Skipped with warning
- Template not found: Clear error with available options
- No templates: Helpful message with creation commands

### Backward Compatibility

- Works with all existing repository templates
- No changes required to existing templates
- Seamless migration from template-only to dual-source

## Template Structure Requirements

Templates must have this structure:

```
template-name/
├── manifest.json          # Required: Template metadata
├── settings.json          # Optional: Default project settings
├── CLAUDE.md              # Optional: Template-specific AI instructions
├── agents/                # Optional: Agent definitions
│   ├── agent1.md
│   └── agent2.md
└── templates/             # Optional: Code templates
    └── ...
```

### manifest.json (Required)

```json
{
  "name": "template-name",
  "version": "1.0.0",
  "description": "Template description",
  "language": "TypeScript",
  "frameworks": ["React", "Vite"],
  "architecture": "Component-based"
}
```

**Required fields**: `name`

**Optional fields**: `version`, `description`, `language`, `frameworks`, `architecture`

## Integration with Template Creation

Works seamlessly with template creation commands:

```bash
# Create personal template from existing codebase
/template-create my-template

# Create personal template from scratch
/template-init

# Use personal template
/agentic-init my-template
```

**Default Location**: Personal templates are saved to `~/.agentecflow/templates/` by default, making them immediately available to `/agentic-init`.

**Repository Templates**: Use `--output-location=repo` with `/template-create` to create templates in `installer/core/templates/` for distribution.

## Testing

### Unit Tests

Located in `tests/test_agentic_init_discovery.py`:
- Template discovery from personal and repository sources
- Personal template priority over repository
- Missing directory handling
- Manifest parsing (minimal and complete)
- Invalid manifest handling
- Template finding by name

**Coverage**: 15 tests, all passing

### Integration Tests

Located in `tests/integration/test_agentic_init_integration.py`:
- Agent installation with and without conflicts
- Agent conflict resolution
- Project structure copying
- Full initialization workflow
- Error handling

**Coverage**: 11 tests, all passing

### Manual Testing

```bash
# Test discovery
python3 -c "from commands.lib.agentic_init import discover_templates; print(discover_templates())"

# Test full command
python3 -m commands.lib.agentic_init.command my-template

# Run tests
pytest tests/test_agentic_init_discovery.py -v
pytest tests/integration/test_agentic_init_integration.py -v
```

## Dependencies

### Internal

- **Template Discovery**: `commands.lib.agentic_init.template_discovery`
- **Template Selection**: `commands.lib.agentic_init.template_selection`
- **Agent Installer**: `commands.lib.agentic_init.agent_installer`

### External

- Python 3.8+ (stdlib only, no external dependencies)

## Troubleshooting

### No Templates Found

**Symptom**: "No templates found" message

**Solutions**:
1. Create personal template: `/template-create my-template`
2. Create from scratch: `/template-init`
3. Check repository templates exist: `ls installer/core/templates/`
4. Verify personal templates directory: `ls ~/.agentecflow/templates/`

### Template Not Found

**Symptom**: "Template 'name' not found"

**Solutions**:
1. List available templates: `/agentic-init` (interactive mode)
2. Check spelling of template name
3. Verify template has valid `manifest.json`

### Agent Conflicts

**Symptom**: Agent conflict prompt during installation

**Recommended**: Choose option [a] to keep your custom version

**Alternative**: Choose [c] to keep both versions for comparison

### Invalid Manifest

**Symptom**: Template skipped with warning

**Solutions**:
1. Verify `manifest.json` is valid JSON
2. Ensure `name` field exists
3. Check file permissions

## Related Commands

- `/template-create <name>` - Create template from existing codebase
- `/template-init` - Create template from scratch via Q&A
- `/task-create` - Create new development task

## API Usage

```python
from commands.lib.agentic_init import agentic_init
from pathlib import Path

# Initialize with specific template
success = agentic_init(
    template_name="my-react-template",
    project_path=Path("/path/to/project")
)

# Initialize with interactive selection
success = agentic_init(
    project_path=Path("/path/to/project")
)
```

## Future Enhancements

- Template versioning and updates
- Template marketplace integration
- Template validation before initialization
- Automatic dependency installation
- Project configuration customization during init

## See Also

- [Template Discovery Implementation](../commands/lib/agentic_init/template_discovery.py)
- [TASK-017 Specification](../../tasks/in_progress/TASK-017-update-agentic-init-discovery.md)
- [Template Creation Workflow](../../docs/guides/template-creation-workflow.md)

---

**Status**: ✅ IMPLEMENTED (TASK-017)
**Version**: 1.0.0
**Last Updated**: 2025-01-08
**Test Coverage**: 26 tests (15 unit + 11 integration), 100% passing
