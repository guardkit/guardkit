# Template Q&A - Interactive Template Customization

Run interactive Q&A session to customize template generation settings.
Saves configuration to `.template-create-config.json` for use by `/template-create`.

**Status**: IMPLEMENTED (TASK-9038)

## Purpose

Provide **optional** customization workflow for power users who need control over template generation.
Separates Q&A from `/template-create` to keep default workflow simple.

**90/10 Use Case Split**:
- **90% of users**: Just run `/template-create` with smart defaults
- **10% of users**: Run `/template-qa` first for full customization

## Usage

```bash
# New configuration
/template-qa

# Edit existing configuration
/template-qa --resume

# Save to specific location
/template-qa --path /path/to/project
```

## Workflow

```
Step 1: Run /template-qa
├─ Interactive Q&A session (10 sections)
├─ Validate answers
└─ Save to .template-create-config.json

Step 2: Run /template-create
├─ Auto-detect config file
├─ Use saved settings
└─ Generate template package
```

## Q&A Sections

The Q&A session covers 10 sections:

### Section 1: Template Identity (Required)
```
Template name: my-template
Template purpose: [quick_start|team_standards|prototype|production]
Description: Optional description
Version: 1.0.0 (default)
Author: Optional author name
```

### Section 2: Technology Stack (Required)
```
Primary language: [csharp|typescript|python|java|go|rust|...]
Framework: (context-dependent based on language)
  C#: [maui|blazor|aspnet-core|wpf|...]
  TypeScript: [react-nextjs|react-vite|angular|vue|...]
  Python: [fastapi|django|flask|...]
Framework version: [latest|lts|specific]
```

### Section 3: Architecture Pattern (Required)
```
Architecture pattern: [mvvm|clean|hexagonal|layered|mvc|...]
Domain modeling: [rich|anemic|functional]
```

### Section 4: Project Structure (Required)
```
Layer organization: [single|multi|feature-based]
Standard folders: [src, tests, docs, ...]
```

### Section 5: Testing Strategy (Required)
```
Unit testing framework: [auto|xunit|nunit|vitest|pytest|...]
Testing scope: [unit, integration, e2e]
Test pattern: [aaa|bdd|tdd]
```

### Section 6: Error Handling (Required)
```
Error handling: [result|exceptions|functional]
Validation approach: [fluent|data-annotations|manual]
```

### Section 7: Dependency Management (Required)
```
Dependency injection: [builtin|autofac|ninject|none]
Configuration approach: [code|files|both]
```

### Section 8: UI/Navigation (Conditional - UI frameworks only)
```
UI architecture: [mvvm|mvc|component-based]
Navigation pattern: [shell|stack|tab|drawer]
```

### Section 9: Additional Patterns (Conditional - Backend/UI frameworks)
```
Needs data access: [yes|no]
Data access: [ef-core|dapper|repository|...]
API pattern: [rest|graphql|grpc]
State management: [redux|context|signal|...]
```

### Section 10: Documentation Input (Optional)
```
Has documentation: [yes|no]
Documentation input method: [paths|text|urls]
Documentation paths: [file paths]
Documentation text: [pasted text]
Documentation URLs: [URLs]
Documentation usage: [reference|analysis|examples]
```

## Command Options

### Required Options
None - all options have defaults

### Optional Options

```bash
--path PATH              Where to save config file
                         Default: current directory

--resume                 Resume from existing config file
                         Loads .template-create-config.json and allows editing
                         Default: false (new config)

--verbose                Show detailed output
                         Default: false
```

## Output Structure

Creates `.template-create-config.json` in project root:

```json
{
  "version": "1.0",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "config": {
    "template_name": "my-template",
    "template_purpose": "quick_start",
    "primary_language": "csharp",
    "framework": "maui",
    "framework_version": "latest",
    "architecture_pattern": "mvvm",
    "domain_modeling": "rich",
    "layer_organization": "single",
    "standard_folders": ["src", "tests"],
    "unit_testing_framework": "xunit",
    "testing_scope": ["unit", "integration"],
    "test_pattern": "aaa",
    "error_handling": "result",
    "validation_approach": "fluent",
    "dependency_injection": "builtin",
    "configuration_approach": "both",
    "ui_architecture": "mvvm",
    "navigation_pattern": "shell",
    "needs_data_access": true,
    "data_access": "ef-core",
    "has_documentation": false
  }
}
```

## Integration with /template-create

The config file is automatically detected by `/template-create`:

```bash
# After running /template-qa
/template-create
→ Detects .template-create-config.json
→ Uses saved settings
→ Skips Q&A
→ Generates template package

# Explicit config flag (optional)
/template-create --config
→ Same behavior as above
```

## Use Cases

### Use Case 1: First-Time User (Default Workflow)
```bash
# Most users just run this - no /template-qa needed
/template-create
→ Smart defaults
→ Minimal prompts
→ Fast template generation
```

### Use Case 2: Power User (Customization Workflow)
```bash
# Power users who need control
/template-qa
→ Complete Q&A session
→ All customization options
→ Save config

/template-create
→ Use saved config
→ No prompts
→ Custom template generation
```

### Use Case 3: Iterative Refinement
```bash
# First iteration
/template-qa
/template-create

# Edit config and regenerate
/template-qa --resume
→ Edit existing values
→ Save updates

/template-create
→ Use updated config
```

### Use Case 4: Team Templates
```bash
# Create team-specific config
/template-qa
→ Configure team standards
→ Save .template-create-config.json

# Commit to version control
git add .template-create-config.json
git commit -m "Add team template config"

# Team members clone and use
git clone ...
/template-create
→ Auto-detect config
→ Generate consistent templates
```

## Examples

### Example 1: Basic Usage
```bash
$ /template-qa

============================================================
  /template-qa - Template Customization Q&A
============================================================

Mode: New configuration

Section 1: Template Identity
------------------------------------------------------------
Template name: my-maui-app
Template purpose:
  [1] Start new projects quickly
  [2] Enforce team standards
  [3] Prototype/experiment
  [4] Production-ready scaffold

Enter number (default: 1): 1

[... rest of Q&A ...]

============================================================
  ✅ Configuration Saved Successfully!
============================================================

📁 Config file: /path/to/project/.template-create-config.json
📝 Template: my-maui-app
🔤 Language: csharp
🛠️  Framework: maui

📝 Next Steps:
   /template-create --config
   # OR
   /template-create  # Will auto-detect and use config file
```

### Example 2: Resume Mode
```bash
$ /template-qa --resume

============================================================
  /template-qa - Template Customization Q&A
============================================================

Mode: Resume (editing existing configuration)

Resuming from Existing Config
------------------------------------------------------------

Existing Configuration:
  Template: my-maui-app
  Language: csharp
  Framework: maui
  Architecture: mvvm
  Last updated: 2024-01-15T10:30:00Z

  ✓ Config loaded successfully

You can now edit any values in the following Q&A session.

[... Q&A with pre-filled values ...]

  ✓ Config saved: .template-create-config.json

✅ Configuration updated successfully!
```

### Example 3: Custom Path
```bash
$ /template-qa --path ~/projects/my-app

[... Q&A session ...]

📁 Config file: ~/projects/my-app/.template-create-config.json
```

## Error Handling

### Common Errors

**Config File Not Found (Resume Mode)**:
```
❌ Config file not found: .template-create-config.json
   Run /template-qa without --resume to create new config
```

**Invalid Config File**:
```
❌ Invalid config file: Missing required field 'template_name'
   Fix config file or run /template-qa --resume to regenerate
```

**Save Permission Denied**:
```
❌ Failed to save config: Permission denied
   Check directory permissions or use --path to specify different location
```

**Q&A Session Interrupted**:
```
⚠️  Q&A session interrupted
   Session state may be saved - run /template-qa --resume to continue
```

## Validation

Config file is validated before saving:

**Required Fields**:
- template_name (3-50 chars)
- template_purpose
- primary_language
- framework
- framework_version
- architecture_pattern
- domain_modeling
- layer_organization
- standard_folders (non-empty list)
- unit_testing_framework
- testing_scope (non-empty list)
- test_pattern
- error_handling
- validation_approach
- dependency_injection
- configuration_approach

**Optional Fields**:
- description
- version
- author
- ui_architecture
- navigation_pattern
- needs_data_access
- data_access
- api_pattern
- state_management
- has_documentation
- documentation_*

**Type Validation**:
- String fields must be strings
- List fields must be lists of strings
- Boolean fields must be booleans
- Version must match semantic versioning format

## Testing

**Test Files**:
- `tests/unit/test_template_config_handler.py` - Config handler tests
- `tests/unit/test_template_qa_orchestrator.py` - Orchestrator tests
- `tests/integration/test_template_qa_workflow.py` - Full workflow tests

**Coverage Target**: >80%

**Key Test Scenarios**:
- New config creation
- Resume from existing config
- Config validation (valid and invalid)
- File I/O errors
- Q&A session integration
- Config file format

## Performance Considerations

**Typical Execution Time**:
- Q&A Session: 2-5 minutes (user-dependent)
- Config Validation: <1 second
- File I/O: <1 second
- Total: 2-5 minutes

## Exit Codes

- `0` - Config saved successfully
- `1` - Q&A session cancelled or failed
- `2` - Config validation failed
- `3` - File I/O error
- `130` - Interrupted with Ctrl+C

## Related Commands

- `/template-create` - Create template from codebase (uses config if available)
- `/template-init` - Create greenfield template
- `taskwright init` - Apply template to new project

## Implementation Details

### Python Modules

**Core Orchestrator**:
- `installer/global/lib/template_qa_orchestrator.py` - Main orchestration logic

**Config Handler**:
- `installer/global/lib/template_config_handler.py` - Config file I/O and validation

**Dependencies** (reused from existing code):
- `installer/global/commands/lib/template_qa_session.py` - Q&A session
- `installer/global/commands/lib/template_qa_questions.py` - Question definitions
- `installer/global/commands/lib/template_qa_validator.py` - Answer validation
- `installer/global/commands/lib/template_qa_display.py` - UI display

### Architecture

Follows orchestrator pattern with dependency injection:
- **Orchestrator**: Coordinates workflow
- **Config Handler**: Handles file I/O and validation
- **Q&A Session**: Handles interactive prompts
- **Dependency Injection**: Testable components

## Design Decisions

**Why Separate Command?**
- Keeps `/template-create` simple for 90% of users
- Provides full control for power users (10%)
- Clear separation of concerns

**Why JSON Config File?**
- Human-readable and editable
- Git-friendly (team templates)
- Language-agnostic format
- Easy validation

**Why --resume Flag?**
- Iterative refinement workflow
- Edit without starting over
- Quick updates to existing config

## Future Enhancements

Planned for future iterations:
- Config templates/presets (e.g., "C# MAUI defaults")
- Config validation in CI/CD
- Config merging (team + personal)
- Config migration/upgrade tools

## See Also

- [TASK-9038: Create /template-qa Command](../../tasks/backlog/TASK-9038-create-template-qa-command.md)
- [Template Creation Workflow](../../docs/workflows/template-creation-workflow.md)
- [Template Customization Guide](../../docs/guides/template-customization.md)

---

## Execution

When user invokes `/template-qa [args]`, execute this workflow:

### Step 1: Parse Arguments

Extract arguments from user command:
- `--path PATH`: Where to save config file (default: current directory)
- `--resume`: Resume from existing config
- `--verbose`: Show detailed output

Build Python command:
```bash
python3 -m installer.global.lib.template_qa_orchestrator \
  [--path PATH] \
  [--resume] \
  [--verbose]
```

### Step 2: Execute Orchestrator

```python
import sys
from pathlib import Path

# Configuration
path = None  # Extracted from user args
resume = False  # Extracted from user args
verbose = False  # Extracted from user args

# Build command
cmd_parts = [
    "python3", "-m",
    "installer.global.lib.template_qa_orchestrator"
]

# Add user arguments
if path:
    cmd_parts.extend(["--path", path])
if resume:
    cmd_parts.append("--resume")
if verbose:
    cmd_parts.append("--verbose")

cmd = " ".join(cmd_parts)

# Run orchestrator
print("🚀 Starting template Q&A...\n")

result = await bash(cmd, timeout=600000)  # 10 minute timeout
exit_code = result.exit_code

# Handle exit codes
if exit_code == 0:
    print("\n✅ Configuration saved successfully!")
elif exit_code == 1:
    print("\n⚠️  Q&A session cancelled or failed")
elif exit_code == 2:
    print("\n❌ Config validation failed")
elif exit_code == 3:
    print("\n❌ File I/O error")
elif exit_code == 130:
    print("\n⚠️  Q&A interrupted (Ctrl+C)")
else:
    print(f"\n❌ Unexpected exit code {exit_code}")

sys.exit(exit_code)
```

### Exit Code Reference

| Code | Meaning | Description |
|------|---------|-------------|
| 0 | Success | Config saved successfully |
| 1 | Cancelled | Q&A session cancelled by user |
| 2 | Validation Failed | Config validation failed |
| 3 | I/O Error | File read/write failed |
| 130 | Interrupted | Ctrl+C pressed during Q&A |

### Error Handling Strategy

**File I/O Errors:**
- Missing config (resume): Show error, suggest creating new config
- Malformed JSON: Show error, suggest running without --resume
- Write failures: Show error with troubleshooting steps

**Validation Errors:**
- Missing fields: Show which fields are missing
- Invalid types: Show expected vs actual type
- Invalid values: Show validation requirements

**Session Errors:**
- User cancellation: Clean exit with message
- Interrupt: Save session state if possible
- Unexpected errors: Show error and cleanup
