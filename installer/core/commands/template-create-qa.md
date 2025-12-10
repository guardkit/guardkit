# Template Create Q&A - Interactive Greenfield Template Creation

Interactive Q&A session for creating project templates from scratch (greenfield).

**Status**: IMPLEMENTED (TASK-001B)

## Purpose

Guide users through technology selection and architecture decisions when creating a new project template without an existing codebase. Gathers structured input for AI-powered template generation.

## Usage

```bash
# Interactive Q&A mode (default)
/template-create-qa

# Skip Q&A and use defaults
/template-create-qa --skip

# Resume from saved session
/template-create-qa --resume

# Specify custom session file
/template-create-qa --session-file /path/to/session.json
```

## Question Sections

The Q&A session covers 10 sections with approximately 42 questions total:

### Section 1: Template Identity
- Template name (with validation)
- Template purpose (quick start, team standards, prototype, production)

### Section 2: Technology Stack
- Primary language (C#, TypeScript, Python, Java, Swift, Go, Rust)
- Framework (context-dependent based on language)
- Framework version (latest, LTS, specific)

### Section 3: Architecture Pattern
- Primary architecture (MVVM, Clean, Hexagonal, Layered, Vertical Slice, Simple)
- Domain modeling approach (rich, anemic, functional, data-centric)

### Section 4: Project Structure
- Layer organization (single, by-layer, by-feature, hybrid)
- Standard folders (src, tests, docs, scripts, .github, docker)

### Section 5: Testing Strategy
- Unit testing framework (auto-select or specify)
- Testing scope (unit, integration, e2e, performance, security)
- Test pattern preference (AAA, BDD, no preference)

### Section 6: Error Handling
- Error handling strategy (Result type, exceptions, error codes, mixed, minimal)
- Input validation (FluentValidation, annotations, manual, minimal)

### Section 7: Dependency Management
- Dependency injection (built-in, third-party, manual, none)
- Configuration approach (JSON, env vars, both, service, minimal)

### Section 8: UI/Navigation (conditional)
*Only asked if UI framework selected*
- UI architecture pattern (MVVM, MVC, component-based, code-behind)
- Navigation approach (framework-recommended, custom, minimal)

### Section 9: Additional Patterns (conditional)
*Asked if backend or UI framework selected*
- Data access pattern (repository, direct, CQRS, event sourcing)
- API pattern (REST, REPR, Minimal APIs, GraphQL, gRPC)
- State management (framework-recommended, minimal, specify)

### Section 10: Documentation Input
- Has documentation to guide template creation?
- Input method (file paths, paste text, URLs, none)
- Documentation usage (strict, guidance, naming, reasoning)

## Features

### Input Validation
- Template name validation (3-50 chars, alphanumeric + hyphens/underscores)
- Choice validation (ensures valid selections)
- Multi-choice validation (comma-separated numbers)
- File path validation (with existence checks)
- URL validation (basic format check)
- Version string validation (semantic versioning)

### Session Persistence
```bash
# Session is automatically saved on Ctrl+C
# Resume with:
/template-create-qa --resume

# Session file location (default)
.template-init-session.json

# Custom session file
/template-create-qa --session-file /path/to/custom-session.json
```

### Conditional Logic
Questions adapt based on previous answers:
- Framework choices depend on selected language
- UI section only shown for UI frameworks
- Backend patterns only shown for backend frameworks
- Documentation questions only shown if user has documentation

### Summary Display
Before proceeding, shows complete summary of all answers organized by section.

## Output Structure

Returns a `GreenfieldAnswers` dataclass with all collected responses:

```python
@dataclass
class GreenfieldAnswers:
    # Section 1: Template Identity
    template_name: str
    template_purpose: str

    # Section 2: Technology Stack
    primary_language: str
    framework: str
    framework_version: str

    # Section 3: Architecture
    architecture_pattern: str
    domain_modeling: str

    # Section 4: Project Structure
    layer_organization: str
    standard_folders: List[str]

    # Section 5: Testing
    unit_testing_framework: str
    testing_scope: List[str]
    test_pattern: str

    # Section 6: Error Handling
    error_handling: str
    validation_approach: str

    # Section 7: Dependency Management
    dependency_injection: str
    configuration_approach: str

    # Section 8: UI/Navigation (optional)
    ui_architecture: Optional[str]
    navigation_pattern: Optional[str]

    # Section 9: Additional Patterns
    needs_data_access: Optional[bool]
    data_access: Optional[str]
    api_pattern: Optional[str]
    state_management: Optional[str]

    # Section 10: Documentation Input
    has_documentation: Optional[bool]
    documentation_input_method: Optional[str]
    documentation_paths: Optional[List[Path]]
    documentation_text: Optional[str]
    documentation_urls: Optional[List[str]]
    documentation_usage: Optional[str]
```

## Integration with Template Generation

This Q&A session is the first phase of the `/template-init` command flow:

```bash
# Complete flow (TASK-011)
/template-init

# Phase 1: Q&A Session (this command - TASK-001B)
# → Collects user preferences and technology decisions

# Phase 2: AI Template Generation (TASK-011)
# → Uses GreenfieldAnswers to generate intelligent defaults

# Phase 3: Agent Setup (TASK-011)
# → Configures specialized agents based on stack
```

## Implementation Details

### Python Modules

**Core Files**:
- `installer/core/commands/lib/template_qa_session.py` - Main session manager
- `installer/core/commands/lib/template_qa_questions.py` - Question definitions
- `installer/core/commands/lib/template_qa_validator.py` - Input validators
- `installer/core/commands/lib/template_qa_display.py` - Display helpers
- `installer/core/commands/lib/template_qa_persistence.py` - Save/load session

**Uses Python stdlib only** (no external dependencies):
- `input()` for user prompts
- `pathlib` for path handling
- `json` for persistence
- `dataclasses` for data structures
- `sys` for CLI interaction

### Error Handling

```python
try:
    session = TemplateQASession()
    answers = session.run()
except KeyboardInterrupt:
    # Automatically saves session
    # User can resume later
except PersistenceError as e:
    # Handle save/load failures
except ValidationError as e:
    # Handle input validation failures
```

## Examples

### Basic Usage
```bash
$ /template-create-qa

============================================================
  /template-init - Greenfield Template Creation
============================================================

This Q&A will guide you through creating a new project template.
Press Ctrl+C at any time to save and exit.

------------------------------------------------------------
  Section 1: Template Identity
------------------------------------------------------------

What should this template be called?
  (Example: dotnet-maui-mvvm-template)

Enter value (default: my-template): dotnet-maui-app

What is the primary purpose of this template?
  [1] Start new projects quickly [DEFAULT]
  [2] Enforce team standards
  [3] Prototype/experiment
  [4] Production-ready scaffold

Enter number (default: Start new projects quickly): 1

...
```

### Skip Q&A Mode
```bash
$ /template-create-qa --skip

# Uses all default values
# Useful for testing or when defaults are acceptable
```

### Resume Session
```bash
$ /template-create-qa

Found existing session saved at 2024-01-15T14:30:00Z
Progress: 5 sections completed

Confirm (Y/n): y

Session loaded successfully

------------------------------------------------------------
  Section 6: Error Handling
------------------------------------------------------------
...
```

## Differences from Brownfield Q&A (TASK-001)

| Aspect | Brownfield (TASK-001) | Greenfield (TASK-001B) |
|--------|----------------------|------------------------|
| **Codebase** | Analyzes existing code | No existing code |
| **Questions** | 8 questions | ~42 questions (10 sections) |
| **Focus** | Detect patterns, understand structure | Select technologies, define architecture |
| **Context** | Codebase analysis informs answers | User knowledge drives answers |
| **Output** | BrownfieldAnalysis | GreenfieldAnswers |
| **Command** | `/template-create` | `/template-init` |

## Testing

**Test Files**:
- `tests/test_template_qa_session.py` - Session flow tests
- `tests/test_template_qa_validator.py` - Validation tests

**Coverage Target**: >85%

**Key Test Scenarios**:
- Complete Q&A flow with all sections
- Conditional section logic (UI, backend)
- Session save/resume functionality
- Input validation for all question types
- Error handling and recovery
- Default value handling
- Multi-choice parsing

## Command Line Options

```bash
--skip                 Use default values for all questions (no interaction)
--resume               Resume from last saved session
--session-file PATH    Use custom session file path
--help                 Show help message
```

## Exit Codes

- `0` - Q&A completed successfully
- `1` - Q&A cancelled by user (during confirmation)
- `130` - Q&A interrupted with Ctrl+C (session saved)
- `2` - Error during Q&A (validation, persistence, etc.)

## Related Commands

- `/template-init` - Complete greenfield template creation (includes this Q&A)
- `/template-create` - Brownfield template creation (analyzes existing codebase)
- `/task-create` - Create development task

## Dependencies

**Required**:
- Python 3.8+
- Python stdlib modules only

**Optional**:
- None (fully standalone)

## Future Enhancements

Planned for future tasks:
- Interactive plan editing before template generation
- Template preview/dry-run mode
- Custom question profiles (save frequently-used answers)
- Integration with external documentation sources
- Team-wide default configurations

## See Also

- [TASK-001B: Interactive Q&A Session for /template-init (Greenfield)](../../tasks/backlog/TASK-001B-greenfield-qa-session.md)
- [TASK-011: Template Init Command Orchestrator](../../tasks/backlog/TASK-011-template-init-orchestrator.md)
- [Template Creation Workflow](../../docs/workflows/template-creation-workflow.md)
