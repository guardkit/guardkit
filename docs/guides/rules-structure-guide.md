# Claude Code Rules Structure Guide

## Overview

Claude Code supports a modular rules structure that enables path-specific loading of project instructions, reducing context window usage by 60-70%. Instead of loading a single large CLAUDE.md file for every task, the rules structure allows you to split your documentation into focused rule files that are only loaded when working with relevant files.

## What is the Rules Structure?

The rules structure is a hierarchical organization of project guidance that uses path patterns to determine which documentation to load. When you open a file or work on a task, Claude Code automatically identifies which rule files apply based on the file paths involved and loads only the relevant guidance.

### Key Benefits

- **Reduced Context Usage**: 60-70% reduction in context window usage
- **Faster Response Times**: Less context to process means quicker AI responses
- **Better Organization**: Logical grouping of related rules and patterns
- **Path-Specific Guidance**: Different rules for different parts of your codebase
- **Improved Maintainability**: Easier to update specific guidance without affecting others

## When to Use Rules Structure

### Use Rules Structure When:

- **Large Documentation**: CLAUDE.md exceeds 15KB
- **Multiple Agents**: Template has specialized agents for different tasks
- **Path-Specific Patterns**: Different coding patterns apply to different file types or directories
- **Context Optimization**: Working with large codebases where context window is at premium
- **Team Templates**: Sharing templates across teams with varied needs
- **Complex Stacks**: Full-stack projects with distinct frontend/backend patterns

### Use Single CLAUDE.md When:

- **Simple Projects**: Documentation is less than 10KB
- **Universal Rules**: All guidance applies to entire codebase
- **Getting Started**: Initial project setup before patterns emerge
- **Prototyping**: Exploratory phase where structure isn't clear yet
- **Small Teams**: 1-2 developers who prefer simplicity

## Quick Start

### 1. Generate Rules Structure

When creating a new template, use the `--use-rules-structure` flag:

```bash
/template-create --use-rules-structure
```

This automatically:
- Creates `.claude/rules/` directory structure
- Splits CLAUDE.md into core (~5KB) + rule files
- Adds path patterns to rule file frontmatter
- Organizes guidance into rules/guidance/

### 2. Directory Structure Overview

```
.claude/
├── CLAUDE.md                # Core documentation (~5KB)
│                            # - Project overview
│                            # - Tech stack summary
│                            # - Quick start commands
│                            # - Links to detailed rules
└── rules/
    ├── code-style.md        # paths: **/*.{ts,tsx,py,cs}
    │                        # Language-specific style rules
    ├── testing.md           # paths: **/*.test.*, **/tests/**
    │                        # Testing patterns and conventions
    ├── patterns/
    │   ├── api-patterns.md  # paths: **/api/**, **/endpoints/**
    │   ├── database.md      # paths: **/models/**, **/repositories/**
    │   └── frontend.md      # paths: **/components/**, **/pages/**
    └── guidance/
        ├── api-specialist.md      # paths: **/api/**/*.py
        ├── database-specialist.md # paths: **/models/**
        └── react-specialist.md    # paths: **/*.tsx, **/components/**
```

### 3. Path Patterns Reference

Path patterns use glob syntax to match files. Here are common patterns:

| Pattern | Matches | Use Case |
|---------|---------|----------|
| `**/*.ts` | All TypeScript files anywhere | TypeScript-specific rules |
| `**/*.{ts,tsx}` | All TypeScript and TSX files | React/TypeScript rules |
| `src/**/*` | All files under src/ directory | Source code patterns |
| `**/tests/**` | Any tests/ directory at any level | Testing guidance |
| `**/api/**/*.py` | Python files in any api/ directory | API endpoint rules |
| `{src,lib}/**/*.ts` | TypeScript in src/ OR lib/ | Multiple directory patterns |
| `**/*query*, **/*api*` | Files with query or api in name | Naming-based rules |
| `!**/node_modules/**` | Exclude node_modules (negation) | Exclude directories |

### 4. Creating Rule Files

Each rule file has two parts:

1. **Frontmatter** (YAML) - Defines which paths the rule applies to
2. **Content** (Markdown) - The actual guidance

Example rule file:

```markdown
---
paths: src/api/**/*.ts, **/router*.py
---

# API Development Rules

## Request Validation

- Validate all inputs using Zod or Pydantic
- Return 400 for validation errors
- Include field-specific error messages

## Error Responses

- Use consistent error format:
  ```json
  {
    "error": "message",
    "code": "ERROR_CODE",
    "details": {}
  }
  ```

## Documentation

- Document all endpoints with OpenAPI/Swagger
- Include request/response examples
- Document authentication requirements
```

## Converting Existing Templates

If you have an existing template with a large CLAUDE.md, follow these steps to convert to rules structure:

### Step 1: Identify Content Categories

Analyze your CLAUDE.md and identify distinct categories:

- **Code Style**: Language syntax, formatting, naming conventions
  → `rules/code-style.md`

- **Testing Patterns**: Test structure, naming, coverage requirements
  → `rules/testing.md`

- **Architecture Patterns**: Design patterns, file organization, layering
  → `rules/patterns/`

- **Agent Guidance**: Specialized agent instructions
  → `rules/guidance/`

### Step 2: Extract and Split Content

For each category:

1. **Create Rule File**
   ```bash
   mkdir -p .claude/rules/patterns
   touch .claude/rules/patterns/api-patterns.md
   ```

2. **Add Frontmatter with Path Patterns**
   ```markdown
   ---
   paths: **/api/**/*.py, **/endpoints/**
   ---
   ```

3. **Move Relevant Content**
   - Copy the relevant section from CLAUDE.md
   - Paste into the new rule file
   - Remove from CLAUDE.md

4. **Verify Path Patterns**
   - Test that paths match intended files
   - Use `/memory` command to see which rules load

### Step 3: Slim Down Core CLAUDE.md

Your core CLAUDE.md should contain only:

- **Project Overview**: Brief description of what the project does
- **Technology Stack**: High-level tech stack summary
- **Quick Start**: Essential commands to get started
- **Directory Structure**: Overview of project organization
- **Rule Links**: Pointers to detailed guidance in rules/

**Target Size**: ~5KB (about 100-150 lines)

Example slimmed-down CLAUDE.md:

```markdown
# MyProject - API Service

## Overview
RESTful API service for user management built with FastAPI and PostgreSQL.

## Tech Stack
- FastAPI 0.104+ (async Python API framework)
- PostgreSQL 15+ (database)
- SQLAlchemy 2.0+ (ORM)
- Pydantic v2 (validation)

## Quick Start
```bash
/task-create "Your task"
/task-work TASK-XXX
/task-complete TASK-XXX
```

## Directory Structure
```
src/
├── api/        # API endpoints (see rules/patterns/api-patterns.md)
├── models/     # Database models (see rules/patterns/database.md)
├── services/   # Business logic
└── tests/      # Tests (see rules/testing.md)
```

## Detailed Guidance
- Code style: `.claude/rules/code-style.md`
- API patterns: `.claude/rules/patterns/api-patterns.md`
- Testing: `.claude/rules/testing.md`
- Guidance: `.claude/rules/guidance/`
```

### Step 4: Organize Agents

Move agent files into rules/guidance/ and add path patterns:

```bash
mkdir -p .claude/rules/guidance
mv .claude/agents/api-specialist.md .claude/rules/guidance/
```

Edit agent frontmatter to add paths:

```yaml
---
name: api-specialist
stack: python
phase: implementation
paths: **/api/**/*.py, **/endpoints/**
---
```

## Best Practices

### Rule File Organization

**One Topic Per File**
- Keep each rule file focused on a single concern
- Split large files into multiple specific ones
- Easier to maintain and update

**Descriptive Filenames**
- Use clear, specific names: `api-patterns.md` not `patterns.md`
- Match filename to content purpose
- Use kebab-case for consistency

**Group Related Rules**
- Use subdirectories for related rules: `patterns/`, `agents/`
- Keep flat structure when possible (avoid deep nesting)
- Maximum 2-3 levels of nesting

### Path Pattern Tips

**Be Specific**
```markdown
# ✅ Good - Specific
paths: src/api/v1/**/*.py

# ❌ Too Broad - Matches too much
paths: **/*.py
```

**Test Patterns**
- Create test files in target locations
- Use `/memory` to verify which rules load
- Adjust patterns based on actual behavior

**Use Negation Sparingly**
```markdown
# ⚠️ Use only when necessary
paths: src/**/*.py, !src/tests/**
```

**Combine Related Patterns**
```markdown
# ✅ Multiple related patterns in one rule
paths: **/components/**/*.tsx, **/pages/**/*.tsx
```

### Agent Rules

**Include Boundary Sections**
- ALWAYS: Non-negotiable actions (5-7 rules)
- NEVER: Prohibited actions (5-7 rules)
- ASK: Human escalation scenarios (3-5 rules)

**Use Path Patterns**
```markdown
---
name: react-specialist
paths: **/*.tsx, **/components/**, **/hooks/**
---
```

**Keep Guidance Focused**
- Only include guidance relevant to the agent's scope
- Link to pattern files for detailed examples
- Avoid duplicating content from other rules

## Troubleshooting

### Rules Not Loading

**Problem**: Expected rule file isn't loading when working with a file.

**Solutions**:
1. **Check Frontmatter Syntax**
   ```markdown
   ---
   paths: src/**/*.ts
   ---
   ```
   - Must have opening and closing `---`
   - Use `paths:` (plural) not `path:`
   - Space after colon

2. **Verify File Extensions Match**
   ```markdown
   # Won't match .tsx files
   paths: **/*.ts

   # Will match both
   paths: **/*.{ts,tsx}
   ```

3. **Test with /memory Command**
   ```bash
   # Open a file and check loaded rules
   /memory
   ```

4. **Check File Location**
   - Rule files must be in `.claude/rules/` directory
   - Subdirectories are fine: `.claude/rules/patterns/api.md`

### Too Many Rules Loading

**Problem**: Context window filling up with too many rule files.

**Solutions**:
1. **Make Paths More Specific**
   ```markdown
   # Before: Too broad
   paths: **/*.ts

   # After: More specific
   paths: src/api/**/*.ts
   ```

2. **Split Overly Broad Patterns**
   - Instead of one rule for all TypeScript files
   - Create separate rules for API, models, services

3. **Use Subdirectories**
   ```
   rules/
   ├── frontend/
   │   ├── components.md  # paths: **/components/**
   │   └── hooks.md       # paths: **/hooks/**
   └── backend/
       ├── api.md         # paths: **/api/**
       └── database.md    # paths: **/models/**
   ```

### Pattern Not Matching Expected Files

**Problem**: Pattern should match files but doesn't.

**Solutions**:
1. **Test Pattern Syntax**
   - `**` matches any directory depth
   - `*` matches any characters except `/`
   - `{}` groups alternatives

2. **Check Directory Structure**
   ```markdown
   # If files are at: src/components/Button.tsx

   # ✅ Will match
   paths: **/components/**/*.tsx

   # ❌ Won't match (missing **)
   paths: src/components/*.tsx  # Only matches direct children
   ```

3. **Escape Special Characters**
   - If directory names contain special characters
   - Use quotes: `paths: "src/my-api/**/*.ts"`

### Rules Loading for Wrong Files

**Problem**: Rule loads when it shouldn't.

**Solutions**:
1. **Add Negation Patterns**
   ```markdown
   paths: src/**/*.ts, !src/tests/**
   ```

2. **Be More Specific with Extensions**
   ```markdown
   # Before: Matches .tsx too
   paths: **/*.ts*

   # After: Only .ts files
   paths: **/*.ts
   ```

3. **Check for Overlapping Patterns**
   - Review all rule files for pattern conflicts
   - Make patterns mutually exclusive when possible

## Examples

### Example 1: FastAPI Python Backend

```
.claude/
├── CLAUDE.md                      # ~4KB core
└── rules/
    ├── code-style.md              # paths: **/*.py
    ├── testing.md                 # paths: **/tests/**/*.py
    ├── patterns/
    │   ├── api-patterns.md        # paths: **/api/**/*.py
    │   ├── database.md            # paths: **/models/**/*.py
    │   └── services.md            # paths: **/services/**/*.py
    └── agents/
        ├── fastapi-specialist.md  # paths: **/api/**/*.py
        └── database-specialist.md # paths: **/models/**/*.py
```

**Results**:
- Core CLAUDE.md: 4KB (always loaded)
- Working on API endpoint: +3KB (api-patterns.md + fastapi-specialist.md)
- Working on model: +2KB (database.md + database-specialist.md)
- Working on tests: +1.5KB (testing.md)

**Total Context Savings**: 65% compared to single 20KB CLAUDE.md

### Example 2: React TypeScript Frontend

```
.claude/
├── CLAUDE.md                      # ~3.5KB core
└── rules/
    ├── code-style.md              # paths: **/*.{ts,tsx}
    ├── testing.md                 # paths: **/*.test.tsx, **/tests/**
    ├── patterns/
    │   ├── components.md          # paths: **/components/**/*.tsx
    │   ├── hooks.md               # paths: **/hooks/**/*.ts
    │   ├── state-management.md    # paths: **/store/**, **/*context*.tsx
    │   └── routing.md             # paths: **/pages/**, **/routes/**
    └── agents/
        ├── react-specialist.md    # paths: **/*.tsx
        ├── hooks-specialist.md    # paths: **/hooks/**/*.ts
        └── query-specialist.md    # paths: **/*query*.ts, **/*api*.ts
```

**Results**:
- Core CLAUDE.md: 3.5KB (always loaded)
- Working on component: +4KB (components.md + react-specialist.md)
- Working on hook: +2.5KB (hooks.md + hooks-specialist.md)
- Working on query: +3KB (state-management.md + query-specialist.md)

**Total Context Savings**: 70% compared to single 25KB CLAUDE.md

### Example 3: Next.js Full-Stack

```
.claude/
├── CLAUDE.md                      # ~5KB core
└── rules/
    ├── code-style.md              # paths: **/*.{ts,tsx}
    ├── testing.md                 # paths: **/*.test.*, **/tests/**
    ├── patterns/
    │   ├── app-router.md          # paths: **/app/**/*.tsx
    │   ├── server-components.md   # paths: **/app/**/*page*.tsx
    │   ├── server-actions.md      # paths: **/actions/**/*.ts
    │   ├── api-routes.md          # paths: **/api/**/*.ts
    │   └── database.md            # paths: **/lib/db/**/*.ts
    └── agents/
        ├── nextjs-specialist.md   # paths: **/app/**/*.tsx
        ├── server-actions.md      # paths: **/actions/**/*.ts
        └── api-specialist.md      # paths: **/api/**/*.ts
```

**Results**:
- Core CLAUDE.md: 5KB (always loaded)
- Working on page: +5KB (app-router.md + server-components.md + nextjs-specialist.md)
- Working on API route: +3KB (api-routes.md + api-specialist.md)
- Working on server action: +2.5KB (server-actions.md + server-actions-specialist.md)

**Total Context Savings**: 60% compared to single 30KB CLAUDE.md

## Template Examples

See these templates for complete examples of rules structure:

- **[fastapi-python](../../installer/core/templates/fastapi-python/.claude/rules/)** - Python backend API patterns
- **[react-typescript](../../installer/core/templates/react-typescript/.claude/rules/)** - React frontend patterns
- **[nextjs-fullstack](../../installer/core/templates/nextjs-fullstack/.claude/rules/)** - Full-stack Next.js patterns

Each template demonstrates:
- Core CLAUDE.md structure (~5KB)
- Path pattern organization
- Agent guidance separation
- Pattern file hierarchy

## Advanced Topics

### Conditional Loading

Rules can be combined with task context for smart loading:

```markdown
---
paths: **/api/**/*.py
task_types: [implementation, review]
---
```

This rule loads only when:
- Working with API files AND
- Task type is implementation or review

### Rule Composition

Break complex guidance into composable pieces:

```
rules/
└── patterns/
    ├── api-base.md           # Core API patterns (all APIs)
    ├── api-rest.md           # REST-specific (extends base)
    └── api-graphql.md        # GraphQL-specific (extends base)
```

Each file can reference others:
```markdown
# api-rest.md
See [API Base Patterns](./api-base.md) for common guidance.

## REST-Specific Patterns
...
```

### Dynamic Path Patterns

Use glob brace expansion for complex patterns:

```markdown
# Match multiple frameworks
paths: {src,lib}/**/api/**/*.{py,ts,cs}

# Match by naming convention
paths: **/*{Controller,Service,Repository}.cs

# Exclude multiple patterns
paths: src/**/*.ts, !**/*.{test,spec}.ts, !**/node_modules/**
```

## Migration Checklist

Use this checklist when converting a template to rules structure:

- [ ] Backup original CLAUDE.md
- [ ] Create `.claude/rules/` directory structure
- [ ] Identify content categories (code-style, testing, patterns, agents)
- [ ] Create rule files with appropriate path patterns
- [ ] Move content from CLAUDE.md to rule files
- [ ] Slim down core CLAUDE.md to ~5KB
- [ ] Update agent files with path patterns
- [ ] Test with `/memory` command
- [ ] Verify rules load for expected files
- [ ] Check context window usage improvement
- [ ] Update template documentation

## Conclusion

The Claude Code rules structure is a powerful feature for optimizing context window usage and organizing project guidance. By splitting documentation into path-specific rule files, you can:

- Reduce context usage by 60-70%
- Improve AI response times
- Better organize project guidance
- Scale to larger, more complex projects

Start with a simple structure and evolve it as patterns emerge. The rules structure grows with your project, providing the right level of guidance exactly when and where you need it.

For questions or issues with the rules structure, see the [troubleshooting section](#troubleshooting) or check the [template examples](#template-examples).
