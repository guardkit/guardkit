# TASK-OPEN-SOURCE-DOCUMENTATION: Documentation for Open Source Release

**Task ID**: TASK-OPEN-SOURCE-DOCUMENTATION
**Title**: Create User Guide and Architecture Documentation
**Status**: BACKLOG
**Priority**: MEDIUM
**Complexity**: 3/10 (Simple)
**Estimated Hours**: 2-3
**Phase**: 8 of 8 (Template-Create Redesign)

---

## Problem Statement

### Current Issue

Documentation for template-create is scattered and incomplete. For a successful open source release, we need:
- Beginner-friendly user guide
- Architecture documentation for contributors
- Troubleshooting guide
- No references to "legacy" command

---

## Solution Design

### Documentation Structure

```
docs/
├── guides/
│   └── template-creation-guide.md       # User guide (beginner-friendly)
├── architecture/
│   └── template-create-architecture.md  # Architecture for contributors
└── troubleshooting/
    └── template-create-troubleshooting.md
```

### Updates Required

| File | Action | Description |
|------|--------|-------------|
| `docs/guides/template-creation-guide.md` | CREATE | User guide |
| `docs/architecture/template-create-architecture.md` | CREATE | Architecture |
| `docs/troubleshooting/template-create-troubleshooting.md` | CREATE | Troubleshooting |
| `CLAUDE.md` | UPDATE | Add template-create section |
| `README.md` | UPDATE | Add template-create feature |

---

## Implementation Details

### 1. User Guide

```markdown
<!-- docs/guides/template-creation-guide.md -->

# Template Creation Guide

Create reusable templates from your existing codebases. This guide walks you through creating, customizing, and using templates with Taskwright.

## Quick Start

Create your first template in 5 minutes:

```bash
# Navigate to your project
cd ~/Projects/my-awesome-project

# Create a template
/template-create --name my-template

# Use the template in a new project
cd ~/Projects/new-project
taskwright init my-template
```

## How It Works

Template creation uses AI-powered analysis to:

1. **Analyze your codebase** - Detects language, framework, patterns
2. **Create specialized agents** - 7-9 agents tailored to your patterns
3. **Generate templates** - Reusable file templates with placeholders
4. **Document conventions** - CLAUDE.md with project-specific guidance

## Creating Templates

### From Existing Project (Brownfield)

```bash
cd ~/Projects/my-existing-app
/template-create --name my-app-template
```

What gets analyzed:
- Technology stack (language, framework, build tools)
- Architecture patterns (MVVM, Clean Architecture, etc.)
- Code patterns (Repository, ErrorOr, CQRS, etc.)
- Naming conventions
- Test setup

### Template Locations

- **Personal templates** (default): `~/.agentecflow/templates/`
- **Repository templates**: `installer/global/templates/` (use `--output-location repo`)

### Options

```bash
# Basic usage
/template-create --name <name>

# Save to repository for team sharing
/template-create --name <name> --output-location repo

# Validate without creating
/template-create --validate

# Skip Q&A (use defaults)
/template-create --name <name> --skip-qa
```

## Template Contents

A template includes:

```
my-template/
├── manifest.json          # Template metadata
├── settings.json          # Naming conventions, patterns
├── CLAUDE.md              # AI instructions
├── templates/             # File templates with placeholders
│   ├── components/
│   ├── services/
│   └── tests/
└── agents/                # Specialized AI agents
    ├── mvvm-specialist.md
    ├── repository-specialist.md
    └── testing-specialist.md
```

## Quality Indicators

Good templates show:

| Metric | Target | What It Means |
|--------|--------|---------------|
| Confidence | 90%+ | Accurate technology detection |
| Agents | 7-9 | Comprehensive pattern coverage |
| Agent Size | 150-250 lines | Detailed, actionable agents |

## Using Templates

### Initialize New Project

```bash
mkdir my-new-project && cd my-new-project
taskwright init my-template
```

### View Template Info

```bash
taskwright init my-template --info
```

## Customizing Templates

### Edit Settings

```bash
# Open settings for editing
vim ~/.agentecflow/templates/my-template/settings.json
```

Common customizations:
- Naming conventions
- File locations
- Pattern preferences

### Enhance Agents

Agents are markdown files that you can edit:

```bash
vim ~/.agentecflow/templates/my-template/agents/mvvm-specialist.md
```

Add:
- More code examples
- Project-specific patterns
- Team conventions

## Best Practices

### DO

- Create templates from mature, well-structured projects
- Review and customize generated agents
- Test template on new project before sharing
- Update templates when patterns evolve

### DON'T

- Create templates from incomplete projects
- Share templates with hardcoded secrets
- Use templates without understanding them
- Expect 100% coverage (customize as needed)

## Troubleshooting

### Low Confidence Score

If confidence is below 90%:
1. Check for build artifacts (obj/, bin/, node_modules/)
2. Ensure .gitignore is comprehensive
3. Verify main files are at root level
4. Try with `--validate` to see what's detected

### Few Agents Created

If fewer than 7 agents:
1. Check if project has diverse patterns
2. Simple projects may need fewer agents
3. Add agents manually if needed

### Template Creation Fails

Common issues:
- Missing .gitignore (artifacts included)
- No source files (empty project)
- Permission issues (check output path)

## Examples

### React TypeScript Project

```bash
cd ~/Projects/my-react-app
/template-create --name react-ts-template
```

Expected: TypeScript, React, Jest, 8-9 agents

### Python FastAPI Project

```bash
cd ~/Projects/my-api
/template-create --name fastapi-template
```

Expected: Python, FastAPI, pytest, 7-8 agents

### .NET MAUI Project

```bash
cd ~/Projects/my-maui-app
/template-create --name maui-template
```

Expected: C#, .NET MAUI, xUnit, 8-9 agents

## Next Steps

- [Template Philosophy](template-philosophy.md) - Why this approach
- [Creating Local Templates](creating-local-templates.md) - Team templates
- [Template Validation](template-validation-guide.md) - Quality assurance

---

*Templates are learning resources. Create from proven patterns.*
```

### 2. Architecture Documentation

```markdown
<!-- docs/architecture/template-create-architecture.md -->

# Template-Create Architecture

Technical architecture documentation for contributors.

## Overview

Template creation uses an AI-first architecture with checkpoint-resume for reliability.

## Core Components

### Orchestrator

`installer/global/commands/lib/template_create_orchestrator.py`

- Coordinates 10 phases
- Manages checkpoint-resume
- Handles agent invocation

### Agent Bridge

`installer/global/lib/agent_bridge/`

- Checkpoint state management
- Agent request/response handling
- Exit code 42 protocol

### AI Prompts

`docs/proposals/template-create/AI-PROMPTS-SPECIFICATION.md`

- Complete prompts for Phases 1, 4, 7.5
- Expected output schemas
- Confidence thresholds

## Phase Architecture

```
Phase 1: AI Codebase Analysis
   ↓ (checkpoint if needed)
Phase 2-4: Generation (no AI)
   ↓
Phase 5: AI Agent Creation
   ↓ (checkpoint if needed)
Phase 6: Write Files
   ↓
Phase 7.5: AI Agent Enhancement
   ↓ (checkpoint if needed)
Phase 8: Validation
```

## Checkpoint-Resume Pattern

```python
# Save checkpoint before agent invocation
state = TemplateCreateState(phase=1, ...)
checkpoint_manager.save_checkpoint(state, request)

# Exit with code 42
raise CheckpointRequested(agent="architectural-reviewer")

# On resume, check for response
if checkpoint_manager.has_agent_response():
    return complete_phase_from_response()
```

## Key Principles

### AI-First

- No hard-coded pattern matching
- AI analyzes, humans decide
- Prompts define behavior

### Agent Creation (Not Discovery)

- CREATE agents to fill gaps
- Respect existing agents
- User custom > template > global

### Graceful Degradation

- Low confidence → fallback to heuristics
- Agent failure → basic agent set
- Always produces usable output

## Data Schemas

See `AGENT-BRIDGE-SCHEMAS.md`:
- `.agent-request.json`
- `.agent-response.json`
- `.template-create-state.json`

## Testing Strategy

- Unit tests for each module
- Integration tests for checkpoint-resume
- E2E tests on 4 reference projects
- Mock invoker for testing without AI

## Contributing

1. Read this architecture doc
2. Review AI-PROMPTS-SPECIFICATION.md
3. Follow SOLID principles
4. Add tests for new features
5. Update docs with changes

---

*For detailed design, see TEMPLATE-CREATE-REDESIGN-PROPOSAL.md*
```

### 3. Troubleshooting Guide

```markdown
<!-- docs/troubleshooting/template-create-troubleshooting.md -->

# Template-Create Troubleshooting

Solutions for common issues during template creation.

## Common Issues

### Issue: Wrong Language Detected

**Symptom**: .NET project detected as Java

**Cause**: Build artifacts in obj/ folder

**Solution**:
1. Check .gitignore includes obj/, bin/
2. Run `/template-create --validate` first
3. If persists, file issue with debug output

### Issue: Low Confidence Score (<90%)

**Symptom**: Warning about heuristic fallback

**Cause**: AI analysis uncertain

**Solutions**:
- Ensure project has clear structure
- Add comprehensive .gitignore
- Check main framework files at root

### Issue: Few Agents Created (<7)

**Symptom**: Only 3-4 agents generated

**Cause**: Simple project or AI under-detection

**Solutions**:
- Verify project has diverse patterns
- Simple projects may not need many agents
- Manually add agents if needed

### Issue: Checkpoint Not Resuming

**Symptom**: Starts from beginning instead of resuming

**Cause**: Missing .agent-response.json

**Solutions**:
1. Ensure agent was invoked after checkpoint
2. Check response file exists
3. Delete .template-create-state.json to start fresh

### Issue: Template Creation Times Out

**Symptom**: Process hangs or times out

**Cause**: Large codebase or slow AI response

**Solutions**:
1. Wait for agent response (up to 3 min)
2. Check .agent-request.json was created
3. Invoke agent manually if needed

## Debug Mode

Run with debug output:

```bash
python -m installer.global.commands.template_create \
  --debug --name test-debug
```

Check debug logs for:
- File counts before/after filtering
- AI prompts sent
- Response parsing

## Getting Help

1. Check this guide
2. Run `/debug` command
3. File issue at https://github.com/taskwright/taskwright/issues

Include:
- Debug output
- .agent-request.json (if exists)
- Project type (language, framework)

---

*Most issues resolve with proper .gitignore and clear project structure.*
```

---

## Acceptance Criteria

### Functional

- [ ] User guide complete and beginner-friendly
- [ ] Architecture documented for contributors
- [ ] Troubleshooting guide comprehensive
- [ ] CLAUDE.md updated
- [ ] README updated

### Quality

- [ ] No references to "legacy" in user-facing docs
- [ ] Examples for all major stacks
- [ ] Clear, professional tone
- [ ] Links work

---

## Dependencies

### Depends On
- TASK-RENAME-LEGACY-BUILD-NEW (Phase 7) - needs working command

### Blocks
- Open source release

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| User guide | Complete | Covers all features |
| Architecture | Complete | Covers all components |
| Troubleshooting | 5+ issues | Common scenarios |
| Professional tone | Yes | Review |

---

**Created**: 2025-11-18
**Phase**: 8 of 8 (Template-Create Redesign)
**Related**: Open source release preparation
