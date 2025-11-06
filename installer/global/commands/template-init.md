# /template-init Command

## Overview

The `/template-init` command orchestrates greenfield template creation from user's technology choices without requiring an existing codebase.

**Purpose**: Enable users to create custom templates for new projects based on their preferred technology stack and architecture patterns.

**Key Difference from /template-create**:
- **Brownfield** (`/template-create`): Analyzes existing codebase → extracts patterns → generates template
- **Greenfield** (`/template-init`): Q&A session → AI generates intelligent defaults → creates template

## Usage

```bash
/template-init
```

## Workflow

The command executes 4 phases automatically:

### Phase 1: Q&A Session
Interactive questionnaire covering:
- Template identity (name, purpose)
- Technology stack (language, framework, version)
- Architecture patterns (MVVM, Clean, Layered, etc.)
- Project structure and organization
- Testing approach and frameworks
- Error handling patterns
- Dependency management
- UI/Navigation (if applicable)
- Additional patterns (data access, API, state)
- Documentation input (optional)

**Duration**: 5-10 minutes

**Features**:
- Resume on interruption (saves progress to `.template-init-session.json`)
- Validation of all inputs
- Context-aware questions (skips irrelevant sections)

### Phase 2: AI Template Generation
AI analyzes Q&A answers and generates:
- `manifest.json` - Template metadata
- `settings.json` - Default project settings
- `CLAUDE.md` - Template-specific instructions for AI
- Project structure definition
- Code templates (optional starter files)
- Inferred analysis for agent generation

**Duration**: 10-30 seconds

### Phase 3: Agent Setup
Automatically configures agent system:
- Scans for existing agents (global, template, custom)
- Generates technology-specific agents
- Creates agent recommendation (4-7 agents typical)
- Saves agent definitions to template

**Duration**: 5-15 seconds

### Phase 4: Save Template
Saves complete template structure:
```
installer/local/templates/{template-name}/
├── manifest.json
├── settings.json
├── CLAUDE.md
├── agents/
│   ├── architectural-reviewer.md
│   ├── task-manager.md
│   ├── test-verifier.md
│   ├── code-reviewer.md
│   └── ... (generated agents)
└── templates/ (optional)
    └── ... (code templates)
```

## Output Example

```
============================================================
  /template-init - Greenfield Template Creation
============================================================

============================================================
  Phase 1: Q&A Session
============================================================

📋 Starting Q&A session...

[Q&A interaction...]

✅ Q&A session completed successfully

============================================================
  Phase 2: AI Template Generation
============================================================

🤖 Generating template structure...
  ✓ Manifest generated
  ✓ Settings generated
  ✓ CLAUDE.md generated
  ✓ Project structure defined
  ✓ Code templates created

============================================================
  Phase 3: Agent System
============================================================

🤖 Setting up agent system...
  ✓ Agent system configured
  ✓ 7 agents ready

============================================================
  Phase 4: Save Template
============================================================

💾 Saving template...
  ✓ Saved: manifest.json
  ✓ Saved: settings.json
  ✓ Saved: CLAUDE.md
  ✓ Saved: 7 agents

✅ Template saved to: installer/local/templates/mycompany-dotnet-template

============================================================
  Template Creation Complete
============================================================

✅ Template created: mycompany-dotnet-template
   Location: installer/local/templates/mycompany-dotnet-template/
   Agents: 7 total

💡 Next steps:
   1. Review template at: installer/local/templates/mycompany-dotnet-template/
   2. Customize agents if needed
   3. Use template with: /agentic-init mycompany-dotnet-template
```

## Features

### Session Resume
If interrupted (Ctrl+C), the Q&A session saves progress to `.template-init-session.json`. On next run, you'll be prompted to resume.

### Input Validation
All inputs are validated:
- Template names: alphanumeric + hyphens
- Technology choices: verified against known options
- Architecture patterns: validated against supported patterns

### Error Handling
Graceful error handling with clear messages:
- Q&A cancellation: Returns to prompt
- Generation failures: Shows error details
- Save failures: Reports specific issues

### Fallback Behavior
If dependencies not available (rare):
- Q&A session falls back to minimal questions
- Agent setup uses global agents only
- Template generation uses basic defaults

## Dependencies

### Internal
- **TASK-001B**: Q&A session infrastructure
- **TASK-009**: Agent orchestration (future)
- **TASK-005**: Settings generator
- **TASK-006**: AI analysis
- **TASK-007**: Claude MD generation
- **TASK-008**: Template generation

### External
None (uses Python stdlib only)

## Testing

### Unit Tests
Located in `tests/test_template_init/`:
- `test_command.py` - Command orchestration
- `test_ai_generator.py` - Template generation
- `test_models.py` - Data models
- `test_errors.py` - Error handling

### Integration Tests
Located in `tests/integration/`:
- `test_template_init_flow.py` - End-to-end workflow
- `test_template_init_resume.py` - Session resume
- `test_template_init_validation.py` - Input validation

### Manual Testing
```bash
# Run command directly
python -m installer.global.commands.lib.template_init.command

# Or via CLI (when integrated)
/template-init
```

## Configuration

### Custom Template Directory
```python
from pathlib import Path
from installer.global.commands.lib.template_init import template_init

# Save to custom location
template_init(template_dir=Path("/custom/path/templates"))
```

### Enable External Agents (Future)
```python
from installer.global.commands.lib.template_init import TemplateInitCommand

command = TemplateInitCommand(enable_external_agents=True)
command.execute()
```

## Troubleshooting

### Q&A Session Fails
- Check `.template-init-session.json` exists
- Verify Python 3.8+ installed
- Ensure terminal supports interactive input

### Template Generation Fails
- Review Q&A answers (saved in session file)
- Check disk space available
- Verify write permissions to `installer/local/templates/`

### Agent Setup Fails
- Ensure global agents exist in `installer/global/agents/`
- Check agent markdown files are valid
- Verify agent orchestration dependencies

### Save Fails
- Check destination directory writable
- Verify no existing template with same name
- Ensure sufficient disk space

## Related Commands

- `/template-create` - Create template from existing codebase (brownfield)
- `/agentic-init <template>` - Initialize project using template
- `/task-create` - Create new task for development

## Future Enhancements

### Phase 2 (Not in TASK-011)
- Full AI-powered template generation
- Advanced code template creation
- Project structure inference
- Pattern-based file generation

### Phase 3 (Future)
- External agent discovery (MCP integration)
- Community agent marketplace
- Agent customization UI
- Agent testing and validation

## Notes

- **Current Implementation**: TASK-011 provides orchestration only
- **AI Generation**: Uses stub implementation (full AI in future task)
- **Agent Orchestration**: Uses fallback until TASK-009 complete
- **Session Persistence**: Fully implemented and tested

## See Also

- [Template Creation Workflow](../../docs/guides/template-creation-workflow.md)
- [TASK-011 Specification](../../tasks/in_progress/TASK-011-template-init-command.md)
- [TASK-001B Q&A Session](./template-create-qa.md)
- [TASK-009 Agent Orchestration](../../tasks/backlog/TASK-009-agent-orchestration.md)

---

**Status**: ✅ IMPLEMENTED (TASK-011)
**Version**: 1.0.0
**Last Updated**: 2025-11-06
