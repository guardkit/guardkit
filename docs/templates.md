# Templates

Stack-specific reference templates and customization guide.

## Available Templates

Taskwright includes **5 high-quality templates** for learning and evaluation:

### Stack-Specific Reference Templates (9+/10 Quality)

| Template | Stack | Quality | Description |
|----------|-------|---------|-------------|
| **react-typescript** | Frontend | 9+/10 | From Bulletproof React (28.5k stars) |
| **fastapi-python** | Backend API | 9+/10 | From FastAPI Best Practices (12k+ stars) |
| **nextjs-fullstack** | Full-stack | 9+/10 | Next.js App Router + production patterns |

### Specialized Templates (8-9+/10 Quality)

| Template | Stack | Quality | Description |
|----------|-------|---------|-------------|
| **react-fastapi-monorepo** | Full-stack | 9.2/10 | React + FastAPI monorepo |

### Language-Agnostic Template (8+/10 Quality)

| Template | Languages | Quality | Description |
|----------|-----------|---------|-------------|
| **default** | Go, Rust, Ruby, Elixir, PHP, etc. | 8+/10 | Language-agnostic foundation |

## Template Philosophy

**Templates are learning resources, not production code.**

Each template demonstrates:

- ✅ How to structure templates for `/template-create`
- ✅ Stack-specific best practices (or language-agnostic patterns)
- ✅ Taskwright workflow integration
- ✅ Boundary sections (ALWAYS/NEVER/ASK) for clear agent behavior
- ✅ High quality standards (all score 8+/10)

### Why This Approach?

**For Evaluation:**

```bash
# Try a reference template
taskwright init react-typescript
```

**For Production:**

```bash
# Create template from YOUR proven code
cd your-existing-project
/template-create  # Creates agents + enhancement tasks
taskwright init your-custom-template
```

**Your production code is better than any generic template.** Create templates from what you've proven works.

## Guides

### 📖 [Template Philosophy](guides/template-philosophy.md)

Why these 5 templates? Understanding the learning resource approach.

### 🔧 [Creating Local Templates](guides/creating-local-templates.md)

Team-specific templates from your own codebase (34KB comprehensive guide).

### 📋 [Template Selection Guide](guides/maui-template-selection.md)

Choosing the right template for your project (originally for MAUI, applies broadly).

### 🔄 [Template Migration](guides/template-migration.md)

Migrating from old templates to current structure.

### ✅ [Template Validation](guides/template-validation-guide.md)

3-level validation system for template quality assurance.

## Template Initialization

### Basic Usage

```bash
# Initialize with template
taskwright init react-typescript

# View template details
taskwright init react-typescript --info
```

### Template Locations

- **Personal templates**: `~/.agentecflow/templates/` (default, immediate use)
- **Repository templates**: `installer/global/templates/` (team/public distribution)

## Creating Custom Templates

### Quick Start

```bash
cd your-existing-project

# Create template with agent enhancement tasks (default)
/template-create

# Or without enhancement tasks (e.g., CI/CD)
/template-create --no-create-agent-tasks
```

**Default Behavior**: Creates agent enhancement tasks by default, providing immediate guidance on next steps.

### Template Quality

Templates generated via `/template-create` automatically include:

1. **Discovery Metadata**: Stack, phase, capabilities, keywords
2. **Boundary Sections**: ALWAYS/NEVER/ASK rules (9/10 quality, GitHub best practices)
3. **Agent Enhancement Tasks**: 12-15 tasks for incremental quality improvement

### Validation Levels

**Level 1: Automatic** (Always On)

- Runs during `/template-create`
- CRUD completeness checks
- Layer symmetry validation
- Auto-fix common issues

**Level 2: Extended** (Optional)

```bash
/template-create --validate
```

- All Level 1 checks
- Placeholder consistency
- Pattern fidelity spot-checks
- Documentation completeness
- Detailed quality report

**Level 3: Comprehensive Audit** (On-demand)

```bash
/template-validate ~/.agentecflow/templates/my-template
```

- Interactive 16-section audit
- Section selection
- Session save/resume
- Inline issue fixes
- AI-assisted analysis

## Template Documentation

Each reference template includes comprehensive README:

- **[react-typescript](https://github.com/taskwright-dev/taskwright/tree/main/installer/global/templates/react-typescript)**: Frontend best practices from Bulletproof React
- **[fastapi-python](https://github.com/taskwright-dev/taskwright/tree/main/installer/global/templates/fastapi-python)**: Backend API patterns from FastAPI Best Practices
- **[nextjs-fullstack](https://github.com/taskwright-dev/taskwright/tree/main/installer/global/templates/nextjs-fullstack)**: Full-stack with Next.js App Router
- **[react-fastapi-monorepo](https://github.com/taskwright-dev/taskwright/tree/main/installer/global/templates/react-fastapi-monorepo)**: Monorepo structure (9.2/10)
- **[default](https://github.com/taskwright-dev/taskwright/tree/main/installer/global/templates/default)**: Language-agnostic foundation

---

## Next Steps

- **Evaluate**: Try `taskwright init react-typescript` or `fastapi-python`
- **Customize**: Read [Creating Local Templates](guides/creating-local-templates.md)
- **Validate**: Learn [Template Validation](guides/template-validation-guide.md)
- **Understand**: Review [Template Philosophy](guides/template-philosophy.md)
