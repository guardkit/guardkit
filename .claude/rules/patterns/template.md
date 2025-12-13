---
paths: installer/core/templates/**/*
---

# Template Development Patterns

Patterns for creating and maintaining GuardKit templates.

## Template Structure

```
installer/core/templates/{template-name}/
├── .claude/
│   ├── CLAUDE.md            # Core documentation (5-8KB)
│   ├── settings.json        # Template settings
│   ├── agents/              # Template-specific agents
│   │   ├── {specialist}.md  # Full agent with boundaries
│   │   └── {specialist}-ext.md  # Extended content (optional)
│   └── rules/               # Conditional loading rules
│       ├── code-style.md    # paths: src/**/*.{ext}
│       ├── testing.md       # paths: tests/**/*
│       └── patterns/        # Pattern-specific rules
├── manifest.json            # Template metadata
└── README.md                # Template documentation
```

## Rules Frontmatter

Every rule file must have paths frontmatter:

```yaml
---
paths: src/**/*.py, lib/**/*.py
---

# Rule Title

Rule content here...
```

### Path Pattern Examples

```yaml
# Single pattern
paths: src/**/*.py

# Multiple patterns
paths: src/**/*.ts, lib/**/*.tsx

# Specific files
paths: "**/models.py", "**/schemas.py"

# All Python files
paths: "**/*.py"
```

## Progressive Disclosure

Split content between core and extended files:

### Core File ({name}.md)
- Quick Start examples (5-10)
- Boundaries (ALWAYS/NEVER/ASK)
- Capabilities summary
- Phase integration
- Loading instructions

### Extended File ({name}-ext.md)
- Detailed code examples (30+)
- Best practices with full explanations
- Anti-patterns with code samples
- Technology-specific guidance
- Troubleshooting scenarios

## Template manifest.json

```json
{
  "schema_version": "1.0.0",
  "name": "python-library",
  "display_name": "Python Library Template",
  "description": "Template for Python library/CLI development",
  "version": "1.0.0",
  "language": "python",
  "language_version": ">=3.9",
  "frameworks": [
    {"name": "pytest", "version": ">=7.0", "purpose": "testing"},
    {"name": "pydantic", "version": ">=2.0", "purpose": "data"}
  ],
  "architecture": "Library",
  "patterns": ["Module", "Factory", "Registry"],
  "category": "library",
  "complexity": 4,
  "tags": ["python", "library", "cli", "pytest"]
}
```

## Template settings.json

```json
{
  "project": {
    "name": "{{ProjectName}}",
    "template": "python-library"
  },
  "quality_gates": {
    "coverage_threshold": 85,
    "branch_coverage_threshold": 75
  }
}
```

## Placeholder Syntax

Use double-brace placeholders:

```
{{ProjectName}}      # Project name
{{project_name}}     # Snake case variant
{{feature_name}}     # Feature-specific
{{author}}           # Author name
```

## Agent Development for Templates

Template agents should include:

1. **Stack-specific frontmatter**
   ```yaml
   stack: [python, library]
   phase: implementation
   capabilities:
     - Python module development
     - pytest fixtures
   ```

2. **Boundary sections**
   - ALWAYS: 5-7 mandatory behaviors
   - NEVER: 5-7 prohibited actions
   - ASK: 3-5 scenarios requiring human input

3. **Quick Start examples** from template source

## Validation Levels

### Level 1: Automatic (always on)
- CRUD completeness checks
- Layer symmetry validation
- Auto-fix common issues

### Level 2: Extended (--validate)
- Placeholder consistency
- Pattern fidelity
- Documentation completeness

### Level 3: Comprehensive (/template-validate)
- 16-section audit
- AI-assisted analysis
- Production readiness assessment
