# Template System Architecture

This guide provides a comprehensive explanation of how GuardKit's template system works, including template files, agent files, CLAUDE.md, progressive disclosure, and the metadata in manifest.json and settings.json.

## Overview

GuardKit templates are self-contained packages that provide stack-specific guidance, agents, and configuration for AI-assisted development. The system uses **progressive disclosure** to optimize context window usage (55-60% token reduction) while maintaining comprehensive documentation.

### Template Directory Structure

```
template-name/
├── CLAUDE.md              # Primary AI guidance document
├── manifest.json          # Template metadata and discovery
├── settings.json          # Code style and generation settings
├── README.md              # Human-readable documentation
├── agents/                # Stack-specific AI specialists
│   ├── {agent}.md         # Core agent (always loaded)
│   └── {agent}-ext.md     # Extended reference (on-demand)
├── docs/                  # Extended documentation
│   ├── patterns/          # Design patterns (on-demand)
│   └── reference/         # Reference material (on-demand)
└── templates/             # Code templates (optional)
```

### Three-File Configuration System

| File | Purpose | Analogy |
|------|---------|---------|
| **manifest.json** | What the template is and contains | Identity card |
| **settings.json** | How code should be generated | Rulebook |
| **CLAUDE.md** | Why patterns are used | Philosophy guide |

---

## CLAUDE.md - The Primary Guidance Document

### Purpose

CLAUDE.md is the **primary AI instruction file** that Claude Code reads to understand project context, architecture, and coding standards. It serves as the "source of truth" for how code should be written in a project.

### Standard Structure

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

## Naming Conventions
- File naming rules
- Code naming rules
- Examples

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

## Extended Reference
- Loading instructions for on-demand content
```

### Example: Core Principles Section

From the react-typescript template:

```markdown
## Core Principles

1. **Feature-Based Organization**: Code organized by domain features, not technical layers
2. **Type Safety First**: Leverage TypeScript for compile-time guarantees
3. **Server State Management**: TanStack Query for efficient data fetching and caching
4. **Component Composition**: Build UIs from small, reusable components
5. **Testing at Every Level**: Unit, integration, and E2E tests co-located with code
```

### Example: Architecture Overview

```markdown
## Architecture Overview

### Feature-Based Structure

Features are organized as independent modules containing all related code:

```
features/
  └── {feature-name}/
      ├── api/              # Data fetching and mutations
      ├── components/       # Feature-specific UI
      ├── hooks/            # Custom hooks (optional)
      ├── types/            # Feature types (optional)
      └── __tests__/        # Tests
```

**Benefits:**
- Loose coupling between features
- Easy to locate and modify feature code
- Clear boundaries and responsibilities
- Scalable as application grows
```

---

## Agent Files - Specialized AI Assistants

### Purpose

Agent files define **specialized AI assistants** that provide domain-specific expertise during task execution. They are automatically discovered based on metadata and invoked during appropriate workflow phases.

### File Format

Agent files use YAML frontmatter for discovery metadata followed by markdown content:

```yaml
---
name: react-state-specialist
description: React hooks and state management implementation specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "React component implementation follows established patterns. Haiku provides fast, cost-effective implementation at 90% quality."

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

### Frontmatter Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Agent identifier (kebab-case) |
| `description` | string | Yes | Brief description of agent role |
| `tools` | array | Yes | Available Claude Code tools |
| `model` | string | Yes | Claude model: `haiku`, `sonnet`, or `opus` |
| `model_rationale` | string | Recommended | Explanation for model choice |
| `stack` | array | For discovery | Technology stack(s): `[react, typescript]` |
| `phase` | string | For discovery | Workflow phase: `implementation`, `review`, `testing`, `orchestration`, `debugging` |
| `capabilities` | array | For discovery | List of specific skills |
| `keywords` | array | For discovery | Search terms for matching |
| `collaborates_with` | array | Optional | Related agents for hand-offs |

### Content Structure

After frontmatter, agents follow this structure:

```markdown
## Quick Start

### Example 1: [Pattern Name]

```typescript
// 2-3 practical, copy-paste ready examples
```

## Boundaries

### ALWAYS (5-7 rules)
- ✅ Non-negotiable action (rationale)
- ✅ Use hooks for state management (modern React patterns)

### NEVER (5-7 rules)
- ❌ Prohibited action (rationale)
- ❌ Never use class components (deprecated pattern)

### ASK (3-5 scenarios)
- ⚠️ Situation requiring human decision
- ⚠️ Global state needed: Ask if Zustand vs Context appropriate

## Capabilities

### 1. Category Name
- Capability 1
- Capability 2

## When I'm Engaged
- Trigger conditions for this agent

## I Hand Off To
- **agent-name**: For specific follow-up work

## Extended Reference

For detailed examples and troubleshooting:
```bash
cat agents/{agent-name}-ext.md
```
```

### Agent Discovery

Agents are discovered automatically during Phase 3 (Implementation) based on:

1. **Stack matching**: Task file extensions, keywords, project structure
2. **Phase matching**: Current workflow phase
3. **Capability matching**: Task requirements vs agent capabilities

**Discovery precedence**: local > user > global > template

```
.claude/agents/           # Local (project-specific)
~/.agentecflow/agents/    # User (personal customizations)
installer/core/agents/    # Global (core agents)
template/agents/          # Template (stack-specific)
```

---

## Progressive Disclosure

### Concept

Progressive disclosure **splits content into core and extended files** to optimize context window usage. Core content is always loaded; extended content is loaded on-demand via explicit instructions.

### Benefits

| Benefit | Impact |
|---------|--------|
| Token reduction | 55-60% in typical tasks |
| Faster responses | Less context to process |
| Same content available | Just loaded when needed |
| Better first impressions | Lower costs during evaluation |

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
├── YAML frontmatter
├── Quick Start (5-10 examples)
├── Boundaries (ALWAYS/NEVER/ASK)
├── Capabilities summary
└── Loading instruction

agent-ext.md (10KB, ~2,500 tokens)   # Extended - on-demand
├── Detailed code examples (30+)
├── Best practices with explanations
├── Anti-patterns with code samples
├── Technology-specific guidance
└── Troubleshooting scenarios
```

### What Goes Where

| Core File (Always Loaded) | Extended File (On-Demand) |
|---------------------------|---------------------------|
| YAML frontmatter | Detailed code examples |
| Role description | Best practices with full rationale |
| Quick Start examples (5-10) | Anti-patterns with code samples |
| Boundaries (ALWAYS/NEVER/ASK) | Technology-specific guidance |
| Capabilities summary | Troubleshooting scenarios |
| Loading instructions | Edge case handling |

### Loading Instructions

Core files include explicit loading instructions:

```markdown
## Extended Reference

For detailed examples, best practices, and troubleshooting:

```bash
cat agents/react-state-specialist-ext.md
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

## manifest.json - Template Metadata

### Purpose

The manifest file provides **structured metadata** for template discovery, validation, and configuration. It defines what the template is, what it contains, and how it should be used.

### Complete Schema

```json
{
  "schema_version": "1.0.0",

  // === Identity ===
  "name": "react-typescript",
  "display_name": "React TypeScript",
  "description": "Production-ready React template with TypeScript...",
  "version": "1.0.0",
  "author": "GuardKit",

  // === Language/Framework ===
  "language": "TypeScript",
  "language_version": "5.4+",

  "frameworks": [
    {
      "name": "React",
      "version": "18.3",
      "purpose": "ui"
    },
    {
      "name": "TanStack Query",
      "version": "5.32",
      "purpose": "state-management"
    }
  ],

  // === Architecture ===
  "architecture": "Feature-Based",
  "patterns": [
    "Feature folders",
    "Query Options pattern",
    "Custom hooks"
  ],
  "layers": ["features", "components", "app"],

  // === Code Generation ===
  "placeholders": {
    "ProjectName": {
      "name": "{{ProjectName}}",
      "description": "Name of the project",
      "required": true,
      "pattern": "^[A-Za-z][A-Za-z0-9-]*$",
      "example": "my-app",
      "default": null
    },
    "FeatureName": {
      "name": "{{FeatureName}}",
      "description": "Name of the feature (kebab-case)",
      "required": true,
      "pattern": "^[a-z][a-z0-9-]*$",
      "example": "user-profile"
    }
  },

  // === Discovery ===
  "tags": ["typescript", "react", "vite", "tanstack-query"],
  "category": "frontend",
  "complexity": 7,

  // === Quality (Optional) ===
  "quality_scores": {
    "solid_compliance": 90,
    "dry_compliance": 85,
    "yagni_compliance": 88,
    "test_coverage": 85,
    "documentation": 90
  },

  // === Metadata ===
  "created_at": "2025-11-09T00:00:00Z",
  "updated_at": "2025-11-09T00:00:00Z",
  "source_project": "https://github.com/alan2207/bulletproof-react",
  "confidence_score": 92,
  "production_ready": true,
  "learning_resource": true
}
```

### Field Reference

#### Identity Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | Yes | Manifest schema version |
| `name` | string | Yes | Template identifier (kebab-case) |
| `display_name` | string | Yes | Human-readable name |
| `description` | string | Yes | Brief description |
| `version` | string | Yes | Template version (semver) |
| `author` | string | Yes | Template author |

#### Technology Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `language` | string | Yes | Primary language |
| `language_version` | string | Yes | Minimum version |
| `frameworks` | array | Yes | Framework definitions |
| `frameworks[].name` | string | Yes | Framework name |
| `frameworks[].version` | string | Yes | Framework version |
| `frameworks[].purpose` | string | Yes | Role: `ui`, `build`, `testing`, `state-management`, etc. |

#### Architecture Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `architecture` | string | Yes | Architecture pattern name |
| `patterns` | array | Yes | Design patterns used |
| `layers` | array | Yes | Architectural layers in order |

#### Placeholder Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `placeholders` | object | Yes | Placeholder definitions |
| `placeholders.{name}.name` | string | Yes | Placeholder syntax: `{{Name}}` |
| `placeholders.{name}.description` | string | Yes | User-facing description |
| `placeholders.{name}.required` | boolean | Yes | Is this required? |
| `placeholders.{name}.pattern` | string | Yes | Validation regex |
| `placeholders.{name}.example` | string | Yes | Example value |
| `placeholders.{name}.default` | string | No | Default value |

#### Discovery Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tags` | array | Yes | Searchable tags |
| `category` | string | Yes | Category: `frontend`, `backend`, `fullstack`, `mobile` |
| `complexity` | number | Yes | Difficulty rating (1-10) |

---

## settings.json - Code Generation Settings

### Purpose

The settings file provides **detailed configuration** for code generation, naming conventions, file organization, and stack-specific behavior.

### Complete Schema

```json
{
  "schema_version": "1.0.0",

  // === Naming Conventions ===
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
    "api": {
      "pattern": "{{action}}-{{entity}}",
      "case_style": "kebab-case",
      "suffix": ".ts",
      "examples": ["get-discussions.ts", "create-discussion.ts"]
    },
    "test": {
      "pattern": "{{filename}}.test",
      "case_style": "kebab-case",
      "suffix": ".tsx",
      "directory": "__tests__"
    }
  },

  // === File Organization ===
  "file_organization": {
    "by_layer": false,
    "by_feature": true,
    "test_location": "adjacent",
    "max_files_per_directory": 20
  },

  // === Layer Mappings ===
  "layer_mappings": {
    "features": {
      "directory": "src/features",
      "namespace_pattern": "@/features/{{FeatureName}}",
      "subdirectories": ["api", "components", "__tests__"],
      "file_patterns": ["*.ts", "*.tsx"],
      "description": "Feature modules with co-located code"
    },
    "components": {
      "directory": "src/components",
      "namespace_pattern": "@/components/{{ComponentType}}",
      "subdirectories": ["ui", "layouts"],
      "file_patterns": ["*.tsx"]
    }
  },

  // === Code Style ===
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

  // === Import Aliases ===
  "import_aliases": {
    "@/": "src/",
    "@/components": "src/components",
    "@/features": "src/features",
    "@/lib": "src/lib"
  },

  // === Generation Options ===
  "generation_options": {
    "include_tests": true,
    "include_mocks": true,
    "include_types": true,
    "include_schemas": true
  }
}
```

### Field Reference

#### Naming Convention Fields

| Field | Type | Description |
|-------|------|-------------|
| `pattern` | string | Naming pattern with placeholders |
| `case_style` | string | Case convention: `camelCase`, `PascalCase`, `kebab-case`, `snake_case` |
| `prefix` | string | Optional prefix (e.g., `use` for hooks) |
| `suffix` | string | File extension |
| `directory` | string | Target directory (e.g., `__tests__`) |
| `examples` | array | Example filenames |

#### File Organization Fields

| Field | Type | Description |
|-------|------|-------------|
| `by_layer` | boolean | Organize by technical layer |
| `by_feature` | boolean | Organize by feature/domain |
| `test_location` | string | `adjacent`, `separate`, or `co-located` |
| `max_files_per_directory` | number | Maximum files before splitting |

#### Layer Mapping Fields

| Field | Type | Description |
|-------|------|-------------|
| `directory` | string | Base directory path |
| `namespace_pattern` | string | Import alias pattern |
| `subdirectories` | array | Standard subdirectories |
| `file_patterns` | array | Allowed file extensions |
| `description` | string | Human-readable description |

### Stack-Specific Examples

#### Python/FastAPI Settings

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
    "async_driver": "asyncpg"
  },
  "api_conventions": {
    "versioning": "url_path",
    "version_prefix": "/api/{{version}}",
    "pagination": "limit_offset"
  }
}
```

#### Default Template Settings (Documentation Levels)

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
      "keywords": ["security", "authentication", "breaking change"]
    },
    "output_format": {
      "minimal": { "architecture_guide": "skip" },
      "standard": { "architecture_guide": "embedded" },
      "comprehensive": { "architecture_guide": "standalone" }
    }
  },
  "quality_gates": {
    "compilation": { "enabled": true, "threshold": 100, "blocking": true },
    "tests": { "enabled": true, "pass_rate": 100, "auto_fix_attempts": 3 },
    "coverage": { "enabled": true, "line_coverage": 80, "blocking": false }
  }
}
```

---

## How Components Work Together

### Template Initialization Flow

```
1. User runs: guardkit init react-typescript

2. System reads manifest.json:
   ├── Validates template compatibility
   ├── Extracts placeholder definitions
   └── Identifies required frameworks

3. System copies template structure:
   ├── CLAUDE.md → project root or .claude/
   ├── agents/ → .claude/agents/
   └── settings.json → .claude/settings.json

4. System prompts for placeholder values:
   ├── {{ProjectName}}: "my-app"
   └── {{FeatureName}}: "users"

5. Template is ready for use
```

### Task Execution Flow

```
1. User runs: /task-work TASK-XXX

2. Phase 2: Planning
   ├── System loads CLAUDE.md
   └── Creates implementation plan

3. Phase 2.5: Architectural Review
   ├── Loads architectural-reviewer agent
   └── Scores against SOLID/DRY/YAGNI

4. Phase 3: Implementation
   ├── Agent discovery:
   │   ├── Detects file types (*.tsx → react)
   │   ├── Matches keywords ("query" → react-query-specialist)
   │   └── Loads core agent file
   ├── If generating code:
   │   └── Loads extended file on-demand
   ├── Uses settings.json for:
   │   ├── Naming conventions
   │   ├── File organization
   │   └── Code style
   └── Uses manifest.json for:
       ├── Placeholder patterns
       └── Framework versions

5. Phase 4-5: Testing and Review
   └── Continues with appropriate agents
```

### Agent Discovery Logic

```python
# Simplified discovery pseudocode
for agent in available_agents:
    stack_match = task.stack in agent.stack
    phase_match = current_phase == agent.phase
    keyword_match = any(kw in agent.keywords for kw in task.keywords)

    if stack_match and phase_match and keyword_match:
        load_agent(agent)
        break

# Fallback to task-manager if no specialist found
```

---

## Available Templates

| Template | Stack | Category | Complexity |
|----------|-------|----------|------------|
| `react-typescript` | React + TypeScript + TanStack Query | Frontend | 7/10 |
| `fastapi-python` | Python + FastAPI + SQLAlchemy | Backend | 7/10 |
| `nextjs-fullstack` | Next.js App Router | Full-stack | 8/10 |
| `react-fastapi-monorepo` | React + FastAPI + Docker | Full-stack | 9/10 |
| `default` | Language-agnostic | Foundation | 5/10 |

---

## Best Practices

### For Template Users

1. **Read CLAUDE.md first** - Understand project patterns before coding
2. **Trust agent discovery** - Agents are selected automatically based on context
3. **Load extended content when needed** - Use `cat agents/{name}-ext.md` for detailed examples
4. **Check settings.json** - Verify naming and organization rules

### For Template Authors

1. **Manifest defines identity** - What the template is and contains
2. **Settings define behavior** - How code should be generated
3. **CLAUDE.md defines guidance** - Why patterns are used
4. **Use progressive disclosure** - Split large files into core + extended
5. **Include boundaries** - ALWAYS/NEVER/ASK rules in every agent

### Architecture Principles

| Principle | Implementation |
|-----------|----------------|
| Separation of Concerns | Manifest (what) vs Settings (how) vs CLAUDE.md (why) |
| Progressive Disclosure | Core files (essential) vs Extended files (reference) |
| Convention over Configuration | Sensible defaults with override capability |
| Discovery over Registration | Agents found by metadata, not explicit registration |

---

## Related Documentation

- [Template Philosophy](template-philosophy.md) - Why these templates exist
- [Creating Local Templates](creating-local-templates.md) - Build custom templates
- [Template Validation Guide](template-validation-guide.md) - Quality assurance
- [Agent Discovery Guide](agent-discovery-guide.md) - How agents are matched to tasks
- [GuardKit Workflow](guardkit-workflow.md) - Complete task workflow

---

*Last updated: December 2025*
