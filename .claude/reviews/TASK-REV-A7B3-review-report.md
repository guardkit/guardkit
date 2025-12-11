# Review Report: TASK-REV-A7B3

## Executive Summary

This review provides a comprehensive explanation of GuardKit's template system architecture, including how template files, agent files, and CLAUDE.md work together. The system uses **progressive disclosure** to optimize context window usage (55-60% token reduction) while maintaining comprehensive documentation. Metadata in `manifest.json` and `settings.json` provides structured configuration for template behavior and code generation.

---

## 1. Template System Architecture Overview

GuardKit templates are self-contained packages that provide stack-specific guidance, agents, and configuration for AI-assisted development. The system follows a **three-tier hierarchy**:

```
Template Directory
├── CLAUDE.md              # Primary AI guidance document
├── manifest.json          # Template metadata and discovery
├── settings.json          # Code style and generation settings
├── agents/                # Stack-specific AI specialists
│   ├── {agent}.md         # Core agent (always loaded)
│   └── {agent}-ext.md     # Extended reference (loaded on-demand)
├── docs/                  # Extended documentation
│   ├── patterns/          # Design patterns (on-demand)
│   └── reference/         # Reference material (on-demand)
└── templates/             # Code templates (optional)
```

### Available Templates

| Template | Purpose | Quality Score |
|----------|---------|---------------|
| `react-typescript` | React + TypeScript + TanStack Query | 9+/10 |
| `fastapi-python` | Python FastAPI backend | 9+/10 |
| `nextjs-fullstack` | Next.js App Router full-stack | 9+/10 |
| `react-fastapi-monorepo` | Full-stack monorepo | 9.2/10 |
| `default` | Language-agnostic foundation | 8+/10 |

---

## 2. CLAUDE.md - The Primary Guidance Document

### Purpose

CLAUDE.md is the **primary AI instruction file** that Claude Code reads to understand project context, architecture, and coding standards. It serves as the "source of truth" for how code should be written in a project.

### Structure

A typical CLAUDE.md contains these sections:

```markdown
# {Template Name} - {Architecture Type}

## Project Context
- High-level description of project purpose
- Target use cases and users

## Core Principles
- 5-7 foundational development principles
- E.g., "Type Safety First", "Feature-Based Organization"

## Architecture Overview
- Structural patterns (layered, feature-based, etc.)
- Data flow diagrams
- Layer responsibilities

## Technology Stack
- Core libraries with versions
- Purpose of each technology
- Integration notes

## Project Structure
- Directory layout with descriptions
- File organization patterns
- Naming conventions

## Patterns and Best Practices
- Code examples for common tasks
- Pattern implementations
- DO/DON'T guidance

## Quality Standards
- Code quality requirements
- Testing requirements
- Performance expectations

## Specialized Agents
- List of template-specific agents
- When to use each agent
```

### Example: React TypeScript CLAUDE.md

Key elements from the react-typescript template:

- **Core Principles**: Feature-Based Organization, Type Safety First, Server State Management, Component Composition, Testing at Every Level
- **Architecture**: Feature-based structure with `features/`, `components/`, `app/`, `lib/` layers
- **Technology Stack**: React 18.3, TypeScript 5.4+, TanStack Query 5.32, Vite 5.2, Tailwind CSS 3.4
- **Patterns**: Query Options Factory, Mutations with Cache Invalidation, Form Validation with Zod, Component Variants with CVA

---

## 3. Agent Files - Specialized AI Assistants

### Purpose

Agent files define **specialized AI assistants** that provide domain-specific expertise during task execution. They are automatically discovered based on metadata and invoked during appropriate workflow phases.

### Agent File Format

Agent files use YAML frontmatter for discovery metadata followed by markdown content:

```yaml
---
name: react-state-specialist
description: React hooks and state management implementation specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "Explanation for model selection"

# Discovery metadata
stack: [react, typescript]
phase: implementation
capabilities:
  - React hooks implementation
  - TanStack Query for server state
  - State management patterns
keywords: [react, hooks, state, tanstack-query]

collaborates_with:
  - react-testing-specialist
  - feature-architecture-specialist
---
```

### Frontmatter Fields

| Field | Purpose | Required |
|-------|---------|----------|
| `name` | Agent identifier | Yes |
| `description` | Brief description | Yes |
| `tools` | Available tools | Yes |
| `model` | Claude model (haiku/sonnet/opus) | Yes |
| `model_rationale` | Why this model was chosen | Recommended |
| `stack` | Technology stack(s) | For discovery |
| `phase` | Workflow phase (implementation/review/testing) | For discovery |
| `capabilities` | List of capabilities | For discovery |
| `keywords` | Search terms | For discovery |
| `collaborates_with` | Related agents | Optional |

### Agent Content Structure

After frontmatter, agents follow this structure:

```markdown
## Quick Start
- 2-3 practical code examples showing core patterns
- Copy-paste ready implementations

## Boundaries

### ALWAYS (5-7 rules)
- ✅ Non-negotiable actions with rationale
- E.g., "✅ Use hooks for state management (modern React patterns)"

### NEVER (5-7 rules)
- ❌ Prohibited actions with rationale
- E.g., "❌ Never use class components (deprecated pattern)"

### ASK (3-5 scenarios)
- ⚠️ Situations requiring human decision
- E.g., "⚠️ Global state needed: Ask if Zustand vs Context"

## Capabilities
- Detailed list of agent expertise areas
- Organized by category

## When I'm Engaged
- Trigger conditions for this agent

## I Hand Off To
- Related agents for follow-up work

## Extended Reference
- Loading instruction for extended file
```

### Agent Discovery

Agents are discovered automatically during Phase 3 (Implementation) based on:

1. **Stack matching**: Task file extensions, keywords, project structure
2. **Phase matching**: Current workflow phase
3. **Capability matching**: Task requirements vs agent capabilities

Discovery precedence: local (.claude/agents) > user (~/.agentecflow/agents) > global (installer/core/agents) > template

---

## 4. Progressive Disclosure Pattern

### Concept

Progressive disclosure **splits content into core and extended files** to optimize context window usage. Core content is always loaded; extended content is loaded on-demand via explicit instructions.

### Why It Matters

- **55-60% token reduction** in typical tasks
- **Faster responses** from reduced context
- **Same comprehensive content** available when needed
- **Better first impressions** for new users

### File Splitting Pattern

**Before (monolithic):**
```
agent.md (16KB, ~4,000 tokens)
├── All content in one file
└── Loaded entirely every time
```

**After (progressive disclosure):**
```
agent.md (6KB, ~1,500 tokens)        # Core - always loaded
├── YAML frontmatter (discovery)
├── Quick Start examples (5-10)
├── Boundaries (ALWAYS/NEVER/ASK)
├── Capabilities summary
├── Phase integration
└── Loading instruction for extended

agent-ext.md (10KB, ~2,500 tokens)   # Extended - loaded on-demand
├── Detailed code examples (30+)
├── Best practices with explanations
├── Anti-patterns with code samples
├── Technology-specific guidance
└── Troubleshooting scenarios
```

### Loading Instructions

Core files include explicit loading instructions:

```markdown
## Extended Reference

For detailed examples, best practices, and troubleshooting:

```bash
cat agents/{agent-name}-ext.md
```

The extended file includes:
- Additional Quick Start examples
- Detailed code examples with explanations
- Best practices with rationale
- Anti-patterns to avoid
```

### Token Savings by Scenario

| Scenario | Without PD | With PD | Savings |
|----------|-----------|---------|---------|
| Simple task | ~45K tokens | ~20K tokens | 56% |
| Standard task | ~45K tokens | ~30K tokens | 33% |
| Complex task | ~45K tokens | ~35K tokens | 22% |
| Debugging | ~45K tokens | ~25K tokens | 44% |

---

## 5. manifest.json - Template Metadata

### Purpose

The manifest file provides **structured metadata** for template discovery, validation, and configuration. It defines what the template is, what it contains, and how it should be used.

### Complete Field Reference

```json
{
  "schema_version": "1.0.0",

  // Identity
  "name": "react-typescript",
  "display_name": "React TypeScript",
  "description": "Production-ready React template...",
  "version": "1.0.0",
  "author": "GuardKit",

  // Language/Framework
  "language": "TypeScript",
  "language_version": "5.4+",

  // Framework definitions
  "frameworks": [
    {
      "name": "React",
      "version": "18.3",
      "purpose": "ui"              // ui, build, state-management, routing, styling, testing, etc.
    }
  ],

  // Architecture
  "architecture": "Feature-Based",
  "patterns": [
    "Feature folders",
    "Query Options pattern",
    "Custom hooks"
  ],
  "layers": ["features", "components", "app"],

  // Placeholders for code generation
  "placeholders": {
    "ProjectName": {
      "name": "{{ProjectName}}",
      "description": "Name of the project",
      "required": true,
      "pattern": "^[A-Za-z][A-Za-z0-9-]*$",
      "example": "my-app",
      "default": null               // Optional default value
    }
  },

  // Discovery and categorization
  "tags": ["typescript", "react", "vite"],
  "category": "frontend",           // frontend, backend, fullstack, mobile, infrastructure
  "complexity": 7,                  // 1-10 scale

  // Quality scores (optional)
  "quality_scores": {
    "solid_compliance": 90,
    "dry_compliance": 85,
    "yagni_compliance": 88,
    "test_coverage": 85,
    "documentation": 90
  },

  // Metadata
  "created_at": "2025-11-09T00:00:00Z",
  "updated_at": "2025-11-09T00:00:00Z",
  "source_project": "https://github.com/...",
  "confidence_score": 92,           // Template extraction confidence
  "production_ready": true,
  "learning_resource": true,
  "reference_implementation": true
}
```

### Key Fields Explained

| Field | Purpose |
|-------|---------|
| `frameworks` | Lists all frameworks with versions and purposes |
| `architecture` | High-level architecture pattern name |
| `patterns` | Design patterns used in the template |
| `layers` | Architectural layers in order |
| `placeholders` | Variables for code generation with validation patterns |
| `complexity` | Difficulty rating (1-10) for user guidance |
| `confidence_score` | How confidently the template was extracted from source |

---

## 6. settings.json - Code Style and Generation Settings

### Purpose

The settings file provides **detailed configuration** for code generation, naming conventions, file organization, and stack-specific behavior. It's the "how" to the manifest's "what".

### Complete Field Reference

```json
{
  "schema_version": "1.0.0",

  // Naming conventions per artifact type
  "naming_conventions": {
    "component": {
      "pattern": "{{ComponentName}}",
      "case_style": "kebab-case-file-pascal-case-export",
      "suffix": ".tsx",
      "examples": ["discussions-list.tsx (export: DiscussionsList)"]
    },
    "hook": {
      "pattern": "use{{HookName}}",
      "case_style": "camelCase",
      "prefix": "use",
      "suffix": ".ts",
      "examples": ["useDiscussions", "useCreateDiscussion"]
    },
    "test": {
      "pattern": "{{filename}}.test",
      "case_style": "kebab-case",
      "suffix": ".tsx",
      "directory": "__tests__"
    }
    // Additional types: api, type, schema, mock-handler, etc.
  },

  // File organization
  "file_organization": {
    "by_layer": false,
    "by_feature": true,
    "test_location": "adjacent",    // adjacent, separate, co-located
    "max_files_per_directory": 20
  },

  // Layer mappings
  "layer_mappings": {
    "features": {
      "directory": "src/features",
      "namespace_pattern": "@/features/{{FeatureName}}",
      "subdirectories": ["api", "components", "__tests__"],
      "file_patterns": ["*.ts", "*.tsx"],
      "description": "Feature modules with co-located code"
    }
  },

  // Code style
  "code_style": {
    "indentation": "spaces",
    "indent_size": 2,
    "line_length": 80,
    "trailing_commas": true,
    "semicolons": true,
    "quotes": "single",
    "arrow_functions": true,
    "jsx_quotes": "double"
  },

  // Import aliases
  "import_aliases": {
    "@/": "src/",
    "@/components": "src/components",
    "@/features": "src/features"
  },

  // Generation options
  "generation_options": {
    "include_tests": true,
    "include_mocks": true,
    "include_types": true,
    "include_schemas": true,
    "generate_query_options": true,
    "generate_custom_hooks": true
  }
}
```

### Stack-Specific Settings (FastAPI Example)

```json
{
  "naming_conventions": {
    "module": {
      "pattern": "{{name}}",
      "case_style": "snake_case",
      "suffix": ".py"
    },
    "class": {
      "pattern": "{{Name}}",
      "case_style": "PascalCase"
    },
    "router": {
      "pattern": "router.py",
      "description": "Router files always named 'router.py'"
    },
    "schema": {
      "pattern": "{{Name}}{{Type}}",
      "examples": ["UserCreate", "UserUpdate", "UserInDB"]
    }
  },

  "database": {
    "orm": "SQLAlchemy",
    "migration_tool": "Alembic",
    "async_driver": "asyncpg",
    "naming_convention": {
      "ix": "ix_%(column_0_label)s",
      "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
    }
  },

  "api_conventions": {
    "versioning": "url_path",
    "version_prefix": "/api/{{version}}",
    "pagination": "limit_offset",
    "error_handling": "HTTPException"
  }
}
```

### Default Template Settings (Documentation Levels)

The default template includes documentation level configuration:

```json
{
  "documentation": {
    "enabled": true,
    "default_level": "auto",
    "complexity_thresholds": {
      "minimal_max": 3,
      "standard_max": 10
    },
    "force_comprehensive": {
      "keywords": ["security", "authentication", "breaking change"],
      "triggers": ["security_changes", "compliance_required"]
    },
    "output_format": {
      "minimal": { "summary": "required", "architecture_guide": "skip" },
      "standard": { "summary": "required", "architecture_guide": "embedded" },
      "comprehensive": { "summary": "required", "architecture_guide": "standalone" }
    },
    "agent_behavior": {
      "architectural_reviewer": {
        "minimal": "json_scores",
        "standard": "embedded_summary",
        "comprehensive": "standalone_guide"
      }
    }
  },

  "quality_gates": {
    "compilation": { "enabled": true, "threshold": 100, "blocking": true },
    "tests": { "enabled": true, "pass_rate": 100, "auto_fix_attempts": 3 },
    "coverage": { "enabled": true, "line_coverage": 80, "blocking": false }
  },

  "workflow": {
    "phases": {
      "2": { "name": "Implementation Planning", "enabled": true },
      "2.5": { "name": "Architectural Review", "enabled": true },
      "4.5": { "name": "Test Enforcement", "enabled": true }
    }
  }
}
```

---

## 7. How Components Work Together

### Template Initialization Flow

```
1. User runs: guardkit init react-typescript

2. System reads manifest.json:
   - Validates template compatibility
   - Extracts placeholder definitions
   - Identifies required frameworks

3. System copies template structure:
   - CLAUDE.md → .claude/CLAUDE.md (or project root)
   - agents/ → .claude/agents/
   - settings.json → .claude/settings.json

4. System prompts for placeholder values:
   - {{ProjectName}}: "my-app"
   - {{FeatureName}}: "users"

5. Template is ready for use
```

### Task Execution Flow

```
1. User runs: /task-work TASK-XXX

2. Phase 2: Planning
   - System loads CLAUDE.md (core principles, architecture)
   - Creates implementation plan in markdown

3. Phase 2.5: Architectural Review
   - Loads architectural-reviewer agent
   - Scores against SOLID/DRY/YAGNI

4. Phase 3: Implementation
   - Agent discovery based on task context:
     a. Detects file types (*.tsx → react)
     b. Matches keywords ("query" → react-query-specialist)
     c. Loads core agent file
   - If generating code, loads extended file:
     cat agents/react-query-specialist-ext.md
   - Uses settings.json for:
     - Naming conventions
     - File organization
     - Code style
   - Uses manifest.json for:
     - Placeholder patterns
     - Framework versions

5. Phase 4-5: Testing and Review
   - Continues with appropriate agents
```

### Agent Discovery Example

```python
# Task context analysis
task_files = ["src/features/users/api/get-users.ts"]
task_keywords = ["useQuery", "cache invalidation", "prefetch"]

# Discovery process
for agent in available_agents:
    if "react" in agent.stack and "typescript" in agent.stack:
        if "implementation" == agent.phase:
            if any(kw in agent.keywords for kw in task_keywords):
                # Match: react-query-specialist
                load_agent(agent)
```

---

## 8. Key Takeaways

### For Template Users

1. **CLAUDE.md is your guide** - Read it to understand project patterns
2. **Agents are automatic** - They're discovered based on task context
3. **Extended content is on-demand** - Load it when you need detailed examples
4. **Settings control style** - Check settings.json for naming and organization rules

### For Template Authors

1. **Manifest defines identity** - What the template is and contains
2. **Settings define behavior** - How code should be generated
3. **CLAUDE.md defines guidance** - Why patterns are used
4. **Progressive disclosure saves tokens** - Split large files into core + extended

### Architecture Principles

| Principle | Implementation |
|-----------|----------------|
| **Separation of Concerns** | Manifest (what) vs Settings (how) vs CLAUDE.md (why) |
| **Progressive Disclosure** | Core files (essential) vs Extended files (reference) |
| **Convention over Configuration** | Sensible defaults with override capability |
| **Discovery over Registration** | Agents found by metadata, not explicit registration |

---

## Review Results Summary

| Metric | Score |
|--------|-------|
| Documentation Completeness | 95/100 |
| Architecture Clarity | 90/100 |
| Pattern Consistency | 92/100 |
| Progressive Disclosure Implementation | 85/100 |

### Findings

1. **Strong foundation**: Well-designed separation between manifest, settings, and CLAUDE.md
2. **Effective progressive disclosure**: Clear core/extended split reduces token usage by 55-60%
3. **Comprehensive metadata**: Both manifest and settings provide thorough configuration options
4. **Agent discovery works well**: Stack, phase, and capability matching is effective

### Recommendations

1. Consider adding a visual diagram to CLAUDE.md showing the template system architecture
2. Document the relationship between manifest.placeholders and code generation more explicitly
3. Add validation tooling to verify manifest/settings consistency

---

**Review completed**: 2025-12-10
**Reviewer**: architectural-reviewer
**Mode**: architectural
**Depth**: standard
