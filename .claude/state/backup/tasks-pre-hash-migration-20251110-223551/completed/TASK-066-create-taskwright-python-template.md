# TASK-066: Create GuardKit Python Template

**Created**: 2025-01-10
**Completed**: 2025-01-10
**Priority**: High
**Type**: Feature
**Parent**: Template Strategy Overhaul
**Status**: completed
**Complexity**: 6/10 (Medium - template creation, documentation, integration)
**Estimated Effort**: 3-4 hours
**Actual Effort**: ~2 hours
**Dependencies**: TASK-065 (Installer Cleanup)

---

## Problem Statement

GuardKit itself (16,254 LOC, 70 Python files, 129 test files) represents a high-quality Python CLI tool with proven architectural patterns, but there's no template based on it. Creating a `guardkit-python` template would provide developers with a reference implementation for:

- **Orchestrator pattern** with dependency injection
- **Pydantic models** for type-safe data structures
- **Agent-based system** with markdown command definitions
- **CLI tool architecture** using Python
- **Comprehensive testing** with pytest (80% coverage threshold)
- **Template generation system** (dogfooding)

**Current State**: 5 templates exist, but none specifically for Python CLI tools with orchestrator patterns.

**Desired State**: A 6th template (`guardkit-python`) that demonstrates production-grade Python CLI architecture based on GuardKit's own codebase.

---

## Context

**Template Philosophy** (from CLAUDE.md):
- Templates are **learning resources** demonstrating best practices
- High-quality reference implementations (8+/10 quality score)
- Users create custom templates from their own codebases via `/template-create`

**Why GuardKit as a Template?**
1. **Real Production Tool**: 16K LOC used in production, not a toy example
2. **Proven Patterns**: Orchestrator + DI + Pydantic models + agent system
3. **Unique Features**: Markdown commands, template generation, quality gates
4. **Dogfooding Validation**: System used to build itself
5. **Minimal Dependencies**: Only 5 core libraries (Pydantic, Jinja2, PyYAML, pathspec, frontmatter)

**Comparison to python-blueprint**:
- GuardKit: 16,254 LOC, real-world complexity, unique patterns
- python-blueprint: Simple examples (factorial calculator), educational only

**Related Tasks**:
- TASK-060/061: Template strategy (4 → 5 templates)
- TASK-062: React + FastAPI Monorepo (9.2/10)
- TASK-065: Installer cleanup (17 → 5 templates)

---

## Objectives

### Primary Objective
Create a high-quality Python CLI template based on the GuardKit codebase using `/template-create`, achieving 8+/10 quality score.

### Success Criteria
- [ ] Template created at `installer/global/templates/guardkit-python/`
- [ ] Template validated with `/template-validate` (8+/10 quality score)
- [ ] Manifest.json includes all required placeholders (ProjectName, project-name, etc.)
- [ ] CLAUDE.md provides clear Python CLI guidance
- [ ] Template files demonstrate orchestrator pattern, DI, Pydantic models
- [ ] README.md explains template usage and patterns
- [ ] Stack agents created for Python CLI development
- [ ] Installer updated to include 6th template
- [ ] Template passes all validation checks (Level 2 validation)
- [ ] Documentation updated to reflect 6 templates

---

## Implementation Scope

### Step 1: Backup .claude Directory

**Rationale**: `/template-create` will analyze the current project structure, including `.claude/`. We need to backup `.claude/` so it doesn't get included in the template itself (templates should create their own `.claude/` directories during initialization).

Use **Bash tool**:

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit

# Backup .claude directory
mv .claude .claude.backup

# Verify backup
ls -la | grep claude
# Should show: .claude.backup (not .claude)
```

### Step 2: Invoke /template-create Command

**IMPORTANT**: This step explicitly invokes the `/template-create` command to generate the template.

Use **SlashCommand tool**:

```bash
/template-create --validate --output-location=repo
```

**Expected Interactive Prompts** (answer these during execution):

1. **Template name?** → `guardkit-python`
2. **Template description?** → `Python CLI tool with orchestrator pattern, dependency injection, and agent-based system (based on GuardKit)`
3. **Technology stack?** → `python`
4. **Author?** → `GuardKit Contributors`
5. **Version?** → `1.0.0`

**What this does**:
- Analyzes current GuardKit codebase structure
- Identifies Python patterns (orchestrator, DI, Pydantic)
- Generates `manifest.json` with placeholders
- Creates template files in `installer/global/templates/guardkit-python/`
- Generates `CLAUDE.md` with Python CLI guidance
- Creates `README.md` with template usage
- Runs Level 2 validation (`--validate` flag)
- Generates `validation-report.md` with quality score

**Expected Output Location**:
```
installer/global/templates/guardkit-python/
├── manifest.json
├── settings.json
├── CLAUDE.md
├── README.md
├── validation-report.md
└── templates/
    ├── src/
    ├── tests/
    ├── requirements.txt
    └── pytest.ini
```

### Step 3: Restore .claude Directory

Use **Bash tool**:

```bash
# Restore .claude directory
mv .claude.backup .claude

# Verify restoration
ls -la | grep claude
# Should show: .claude (not .claude.backup)
```

### Step 4: Review Validation Report

Use **Read tool** to examine the generated validation report:

```bash
# Read validation report
cat installer/global/templates/guardkit-python/validation-report.md
```

**Check for**:
- Quality score ≥8.0/10 (target: 8+/10)
- CRUD completeness: ≥80%
- Layer symmetry: ≥80%
- Placeholder consistency: 100%
- Pattern fidelity: ≥80%

**If quality score <8.0/10**: Proceed to Step 5 (Comprehensive Audit) to identify and fix issues.

### Step 5: Run Comprehensive Audit (if needed)

If validation score <8.0/10, use **SlashCommand tool** to run Level 3 audit:

```bash
/template-validate installer/global/templates/guardkit-python
```

**Interactive Audit Sections**:
1. Manifest validation
2. Placeholder usage
3. CRUD completeness
4. Layer symmetry
5. Settings consistency
6. Documentation quality
7. Template structure
8. **AI Analysis**: Pattern recognition
9. File organization
10. Naming conventions
11. **AI Analysis**: Best practices
12. **AI Analysis**: Anti-patterns
13. **AI Analysis**: Security issues
14. Stack specificity
15. Quick start guide
16. Production readiness

**Expected Actions**:
- Review AI analysis sections (8, 11, 12, 13)
- Fix any issues identified in audit
- Re-run audit to verify fixes
- Target: 8+/10 quality score

### Step 6: Review and Enhance Manifest.json

Use **Read tool** and **Edit tool** to review and enhance the generated manifest:

```bash
# Read generated manifest
cat installer/global/templates/guardkit-python/manifest.json
```

**Required Placeholders** (verify these exist):
- `{{ProjectName}}` - PascalCase project name (e.g., "TaskManager")
- `{{project-name}}` - kebab-case project name (e.g., "task-manager")
- `{{project_name}}` - snake_case project name (e.g., "task_manager")
- `{{description}}` - Project description
- `{{author}}` - Project author
- `{{PythonPackageName}}` - Python package name (snake_case)
- `{{CliCommandName}}` - CLI command name (kebab-case)

**Example Enhancement** (if needed):

Use **Edit tool** to add missing placeholders or improve descriptions:

```json
{
  "name": "guardkit-python",
  "description": "Python CLI tool with orchestrator pattern, dependency injection, and agent-based system",
  "version": "1.0.0",
  "stack": "python",
  "category": "cli-tool",
  "placeholders": {
    "ProjectName": {
      "name": "{{ProjectName}}",
      "description": "Project name in PascalCase (e.g., TaskManager)",
      "required": true,
      "pattern": "^[A-Z][A-Za-z0-9]*$",
      "example": "TaskManager"
    },
    "project_name": {
      "name": "{{project_name}}",
      "description": "Project name in snake_case for Python modules (e.g., task_manager)",
      "required": true,
      "pattern": "^[a-z][a-z0-9_]*$",
      "example": "task_manager"
    },
    "cli-command-name": {
      "name": "{{cli-command-name}}",
      "description": "CLI command name in kebab-case (e.g., task-manager)",
      "required": true,
      "pattern": "^[a-z][a-z0-9-]*$",
      "example": "task-manager"
    }
  }
}
```

### Step 7: Review and Enhance CLAUDE.md

Use **Read tool** to review the generated CLAUDE.md:

```bash
cat installer/global/templates/guardkit-python/CLAUDE.md
```

**Expected Content**:
- Python CLI tool architecture overview
- Orchestrator pattern explanation
- Dependency injection guidance
- Pydantic models best practices
- Agent-based system documentation
- Testing strategy (pytest, 80% coverage)
- Command definitions (markdown-based)

**Enhancement** (if needed):

Use **Edit tool** to add GuardKit-specific guidance:

```markdown
# Python CLI Tool with Orchestrator Pattern

This template demonstrates a production-grade Python CLI tool based on GuardKit's architecture.

## Architecture Overview

- **Orchestrator Pattern**: Central orchestrator coordinates agents and workflows
- **Dependency Injection**: Loose coupling via DI container
- **Pydantic Models**: Type-safe data structures with validation
- **Agent System**: Specialized agents for different tasks
- **Markdown Commands**: Commands defined in markdown for AI/human readability

## Key Patterns

### Orchestrator Pattern
```python
class Orchestrator:
    def __init__(self, config: Config, di_container: DIContainer):
        self.config = config
        self.container = di_container

    async def execute_workflow(self, workflow_name: str):
        # Coordinate agents and execute workflow
        pass
```

[... more examples ...]
```

### Step 8: Create Stack Agents

Use **Bash tool** to create stack agent directory:

```bash
mkdir -p installer/global/agents/stacks/guardkit-python
```

Use **Write tool** to create stack-specific agents:

**Agent 1: Python CLI Specialist**

```bash
# File: installer/global/agents/stacks/guardkit-python/python-cli-specialist.md
```

```markdown
---
name: python-cli-specialist
type: implementation
description: Python CLI tool development specialist for orchestrator pattern, Click/Typer, and command-line interfaces
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
---

# Python CLI Specialist

You are a Python CLI development specialist focused on building production-grade command-line tools with orchestrator patterns.

## Expertise

- **CLI Frameworks**: Click, Typer, argparse
- **Orchestrator Pattern**: Central coordination of workflows
- **Dependency Injection**: Service locator and DI containers
- **Configuration**: YAML, JSON, environment variables
- **Logging**: Structured logging with context

## Implementation Guidelines

1. Use Click or Typer for CLI interface (Typer preferred for type safety)
2. Implement orchestrator pattern for complex workflows
3. Use Pydantic for configuration and data validation
4. Implement proper error handling and user feedback
5. Add progress indicators for long-running operations
6. Support --verbose, --quiet, --help flags
7. Use dependency injection for testability

## Code Standards

- Type hints for all functions
- Docstrings (Google style)
- Error messages should be actionable
- Support both interactive and non-interactive modes
```

**Agent 2: Python Testing Specialist**

```bash
# File: installer/global/agents/stacks/guardkit-python/python-testing-specialist.md
```

```markdown
---
name: python-testing-specialist
type: testing
description: Python testing specialist for pytest, fixtures, mocking, and test coverage
tools:
  - Read
  - Write
  - Edit
  - Bash
---

# Python Testing Specialist

You are a Python testing specialist focused on comprehensive test coverage using pytest.

## Expertise

- **pytest**: Fixtures, parametrize, markers
- **Mocking**: unittest.mock, pytest-mock
- **Coverage**: pytest-cov, branch coverage
- **Test Organization**: Conftest, fixtures, helpers

## Testing Standards

1. Use pytest for all tests
2. Achieve ≥80% line coverage, ≥75% branch coverage
3. Use fixtures for setup/teardown
4. Mock external dependencies
5. Parametrize tests for multiple scenarios
6. Use markers (unit, integration, slow)
7. Test error cases and edge cases

## Test Structure

```python
# tests/conftest.py - shared fixtures
# tests/unit/ - unit tests
# tests/integration/ - integration tests
# pytest.ini - pytest configuration
```
```

**Agent 3: Python Architecture Specialist**

```bash
# File: installer/global/agents/stacks/guardkit-python/python-architecture-specialist.md
```

```markdown
---
name: python-architecture-specialist
type: design
description: Python architecture specialist for orchestrator pattern, DI, and modular design
tools:
  - Read
  - Analyze
  - Design
---

# Python Architecture Specialist

You are a Python architecture specialist focused on orchestrator patterns and dependency injection.

## Expertise

- **Orchestrator Pattern**: Coordinating complex workflows
- **Dependency Injection**: Service locator, DI containers
- **Modular Design**: Plugin systems, extensibility
- **Design Patterns**: Factory, Strategy, Observer

## Architectural Principles

1. Single Responsibility Principle
2. Dependency Inversion (depend on abstractions)
3. Open/Closed Principle (open for extension)
4. Loose coupling via DI
5. Clear separation of concerns

## Orchestrator Pattern

```python
# Core orchestrator coordinates agents
# Agents are specialized for specific tasks
# DI container manages dependencies
# Configuration drives behavior
```
```

### Step 9: Update Installer Scripts

Use **Edit tool** to update `installer/scripts/install.sh`:

**Update template count** (around line 1106-1125):

```bash
# Old:
Available Templates:
  • default - Language-agnostic foundation
  • fastapi-python - FastAPI backend patterns (9+/10)
  • nextjs-fullstack - Next.js full-stack (9+/10)
  • react-fastapi-monorepo - React + FastAPI monorepo (9.2/10)
  • react-typescript - React frontend patterns (9+/10)

# New:
Available Templates:
  • default - Language-agnostic foundation
  • fastapi-python - FastAPI backend patterns (9+/10)
  • nextjs-fullstack - Next.js full-stack (9+/10)
  • react-fastapi-monorepo - React + FastAPI monorepo (9.2/10)
  • react-typescript - React frontend patterns (9+/10)
  • guardkit-python - Python CLI with orchestrator pattern (8+/10)
```

**Update template count** (around line 448):

```bash
# Old:
  📋 Templates:       5

# New:
  📋 Templates:       6
```

Use **Edit tool** to update `installer/scripts/init-project.sh`:

**Add guardkit-python to template list** (around line 68-87):

```bash
# Add new case:
guardkit-python)
    echo "  📋 Template:    guardkit-python"
    echo "  📝 Type:        Python CLI tool"
    echo "  🎯 Use Case:    CLI tools with orchestrator pattern"
    echo "  ⭐ Quality:     8+/10"
    ;;
```

### Step 10: Update Documentation

Use **Edit tool** to update `CLAUDE.md`:

**Update template count** (search for "5 templates" or "four templates"):

```markdown
# Old:
GuardKit includes **5 high-quality templates**

# New:
GuardKit includes **6 high-quality templates**
```

**Add guardkit-python to template list**:

```markdown
### Stack-Specific Reference Templates (9+/10 Quality)
1. **react-typescript** - Frontend best practices
2. **fastapi-python** - Backend API patterns
3. **nextjs-fullstack** - Full-stack application

### Language-Agnostic Template (8+/10 Quality)
4. **default** - For Go, Rust, Ruby, Elixir, PHP

### Specialized Templates (8-9+/10 Quality)
5. **react-fastapi-monorepo** - Full-stack monorepo (9.2/10)
6. **guardkit-python** - Python CLI with orchestrator pattern (8+/10)
```

Use **Edit tool** to update `README.md`:

**Update template count and list**:

```markdown
# Templates

GuardKit provides **6 high-quality reference templates**:

1. **react-typescript** - React frontend (9+/10)
2. **fastapi-python** - Python backend (9+/10)
3. **nextjs-fullstack** - Next.js full-stack (9+/10)
4. **react-fastapi-monorepo** - Monorepo (9.2/10)
5. **guardkit-python** - Python CLI tool (8+/10)
6. **default** - Language-agnostic (8+/10)
```

### Step 11: Test Template Installation

Use **Bash tool** to test the new template:

```bash
# Create test directory
mkdir -p /tmp/test-guardkit-python-template
cd /tmp/test-guardkit-python-template

# Initialize with new template
guardkit-init guardkit-python

# Expected prompts:
# ProjectName (PascalCase): TaskManager
# project_name (snake_case): task_manager
# cli-command-name (kebab-case): task-manager
# description: A task management CLI tool
# author: Your Name

# Verify initialization
ls -la
# Should show:
# - src/task_manager/
# - tests/
# - requirements.txt
# - pytest.ini
# - .claude/
```

**Verify structure**:

```bash
# Check directory structure
tree -L 3

# Expected:
# .
# ├── src/
# │   └── task_manager/
# │       ├── __init__.py
# │       ├── orchestrator.py
# │       └── di_container.py
# ├── tests/
# │   ├── conftest.py
# │   └── unit/
# ├── requirements.txt
# ├── pytest.ini
# └── .claude/
```

**Test Python installation**:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v --cov=src --cov-report=term
# Expected: All tests pass, ≥80% coverage
```

### Step 12: Commit Changes

Use **Bash tool**:

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit

git add installer/global/templates/guardkit-python/
git add installer/global/agents/stacks/guardkit-python/
git add installer/scripts/install.sh
git add installer/scripts/init-project.sh
git add CLAUDE.md
git add README.md

git status
# Verify:
# - New template directory added
# - New stack agent directory added
# - Installer scripts modified
# - Documentation updated
```

---

## Acceptance Criteria

### Functional Requirements
- [ ] Template created at `installer/global/templates/guardkit-python/`
- [ ] Validation report shows quality score ≥8.0/10
- [ ] Manifest.json includes all required Python CLI placeholders
- [ ] CLAUDE.md provides Python CLI architecture guidance
- [ ] README.md explains template usage and patterns
- [ ] 3 stack agents created (CLI, Testing, Architecture specialists)
- [ ] Template initializes correctly with `guardkit-init guardkit-python`
- [ ] Generated project has valid Python structure (src/, tests/, requirements.txt)
- [ ] Installer shows "Templates: 6" and lists all 6 templates
- [ ] Documentation updated to reflect 6 templates

### Quality Requirements
- [ ] Template demonstrates orchestrator pattern
- [ ] Template includes dependency injection examples
- [ ] Template uses Pydantic for data validation
- [ ] Template includes pytest configuration (≥80% coverage)
- [ ] Template includes agent-based system examples
- [ ] Template includes markdown command definitions
- [ ] All placeholder substitutions work correctly
- [ ] No broken references or imports
- [ ] Comprehensive documentation

---

## Testing Requirements

### Template Validation Tests
```bash
# Test 1: Level 2 validation (built-in)
/template-create --validate --output-location=repo
# Expected: Quality score ≥8.0/10

# Test 2: Level 3 comprehensive audit
/template-validate installer/global/templates/guardkit-python
# Expected: Score ≥8.0/10, no critical issues
```

### Template Initialization Tests
```bash
# Test 3: Initialize template
cd /tmp/test-guardkit-python
guardkit-init guardkit-python
# Expected: Initializes successfully with all prompts

# Test 4: Verify structure
ls -la src/
ls -la tests/
cat requirements.txt
cat pytest.ini
# Expected: All files present and correct

# Test 5: Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Expected: Installs successfully

# Test 6: Run tests
pytest tests/ -v --cov=src
# Expected: Tests run and pass (even if minimal)
```

### Installer Tests
```bash
# Test 7: Verify installer output
./installer/scripts/install.sh | grep -A 10 "Available Templates"
# Expected: Shows 6 templates including guardkit-python

# Test 8: Verify template count
./installer/scripts/install.sh | grep "Templates:"
# Expected: Shows "📋 Templates:       6"
```

---

## Files to Create/Modify

### Template Files (CREATE)
- `installer/global/templates/guardkit-python/manifest.json`
- `installer/global/templates/guardkit-python/settings.json`
- `installer/global/templates/guardkit-python/CLAUDE.md`
- `installer/global/templates/guardkit-python/README.md`
- `installer/global/templates/guardkit-python/validation-report.md`
- `installer/global/templates/guardkit-python/templates/src/{{project_name}}/__init__.py`
- `installer/global/templates/guardkit-python/templates/src/{{project_name}}/orchestrator.py`
- `installer/global/templates/guardkit-python/templates/src/{{project_name}}/di_container.py`
- `installer/global/templates/guardkit-python/templates/tests/conftest.py`
- `installer/global/templates/guardkit-python/templates/requirements.txt`
- `installer/global/templates/guardkit-python/templates/pytest.ini`

### Stack Agents (CREATE)
- `installer/global/agents/stacks/guardkit-python/python-cli-specialist.md`
- `installer/global/agents/stacks/guardkit-python/python-testing-specialist.md`
- `installer/global/agents/stacks/guardkit-python/python-architecture-specialist.md`

### Installer Scripts (MODIFY)
- `installer/scripts/install.sh` - Add template to list, update count to 6
- `installer/scripts/init-project.sh` - Add guardkit-python case

### Documentation (MODIFY)
- `CLAUDE.md` - Update template count and list
- `README.md` - Update template count and list

---

## Expected Template Output Structure

After running `/template-create --validate --output-location=repo`:

```
installer/global/templates/guardkit-python/
├── manifest.json                 # Template metadata + placeholders
├── settings.json                 # Template configuration
├── CLAUDE.md                     # AI guidance for Python CLI
├── README.md                     # Template usage documentation
├── validation-report.md          # Quality score + findings
└── templates/
    ├── src/
    │   └── {{project_name}}/
    │       ├── __init__.py
    │       ├── orchestrator.py   # Orchestrator pattern example
    │       ├── di_container.py   # DI container implementation
    │       ├── agents/
    │       │   └── __init__.py
    │       ├── commands/
    │       │   └── __init__.py
    │       └── models.py         # Pydantic models
    ├── tests/
    │   ├── conftest.py           # pytest fixtures
    │   ├── unit/
    │   │   └── test_orchestrator.py
    │   └── integration/
    │       └── __init__.py
    ├── requirements.txt          # Python dependencies
    ├── pytest.ini                # pytest configuration
    ├── setup.py                  # Package setup
    └── README.md                 # Project README template
```

---

## Risk Mitigation

### Risk 1: Quality Score <8.0/10
**Mitigation**: Run Level 3 comprehensive audit (`/template-validate`) to identify specific issues, then fix them iteratively.

### Risk 2: .claude Directory Included in Template
**Mitigation**: Backup and remove .claude before running `/template-create`, restore after completion.

### Risk 3: Placeholder Inconsistencies
**Mitigation**: Review manifest.json and all template files to ensure consistent placeholder usage ({{ProjectName}}, {{project_name}}, etc.).

### Risk 4: Missing Stack Agents
**Mitigation**: Create 3 stack-specific agents (CLI, Testing, Architecture) with clear expertise definitions.

### Risk 5: Template Doesn't Reflect GuardKit Patterns
**Mitigation**: Manually enhance CLAUDE.md and template files to explicitly document orchestrator pattern, DI, and agent system.

---

## Success Metrics

**Quantitative**:
- Quality score: ≥8.0/10 (target: 8.5/10)
- Template count: 6 (up from 5)
- Stack agent count: 3 new agents
- Placeholder count: ≥7 placeholders
- Validation checks: 100% passed

**Qualitative**:
- Clear demonstration of orchestrator pattern
- Comprehensive Python CLI guidance
- Production-grade code examples
- Excellent documentation
- Easy to initialize and customize

---

## Related Tasks

- **TASK-060**: Remove Low-Quality Templates
- **TASK-061**: Update Documentation for 4-Template Strategy
- **TASK-062**: Create React + FastAPI Monorepo Template (9.2/10)
- **TASK-065**: Clean Installer - Remove Deprecated Templates
- **TASK-067** (future): Update Documentation for 6-Template Strategy

---

**Document Status**: Ready for Implementation
**Created**: 2025-01-10
**Parent Epic**: Template Strategy Overhaul
**Depends On**: TASK-065 (Installer Cleanup completed)
