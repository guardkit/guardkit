# Taskwright Templates Overview

**Last Updated**: 2025-01-10
**Template Count**: 6

---

## Summary

Taskwright includes **6 high-quality reference templates** for different use cases, all validated to 8+/10 quality standards.

---

## Template Categories

### Production Stack Templates (3 templates)

Templates based on popular open-source projects and best practices:

#### 1. react-typescript (9+/10)
- **Source**: [Bulletproof React](https://github.com/alan2207/bulletproof-react) (28.5K stars)
- **Use Case**: React SPAs, frontends
- **Patterns**: Feature-based architecture, component composition
- **Tech Stack**: React 18, TypeScript, Vite, Tailwind CSS, Vitest, Playwright
- **Best For**: Single-page applications, modern frontend development

#### 2. fastapi-python (9+/10)
- **Source**: [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices) (12K+ stars)
- **Use Case**: REST APIs, backends
- **Patterns**: Layered architecture, dependency injection
- **Tech Stack**: FastAPI, Python 3.11+, SQLAlchemy, Alembic, pytest
- **Best For**: RESTful APIs, microservices, backend services

#### 3. nextjs-fullstack (9+/10)
- **Source**: Next.js best practices
- **Use Case**: Full-stack web applications
- **Patterns**: App Router, server components, API routes
- **Tech Stack**: Next.js 14+, React Server Components, TypeScript
- **Best For**: Server-side rendered apps, full-stack applications

---

### Specialized Templates (2 templates)

#### 4. react-fastapi-monorepo (9.2/10)
- **Source**: Monorepo best practices
- **Use Case**: Full-stack monorepos
- **Patterns**: Type-safe contracts, shared code, concurrent development
- **Tech Stack**: React + FastAPI, shared types, workspace configuration
- **Best For**: Full-stack projects with frontend + backend in single repository
- **Added**: TASK-062

#### 5. taskwright-python (8+/10) - Internal Development
- **Source**: Taskwright's own codebase (16K LOC)
- **Use Case**: CLI tools with orchestration, understanding Taskwright
- **Patterns**: Orchestrator pattern, dependency injection, agent system
- **Tech Stack**: Python 3.11+, Click/Typer, Pydantic, pytest
- **Best For**: CLI tools with complex workflows, learning Taskwright's architecture
- **Added**: TASK-066

**⚠️ Special Note on taskwright-python**:
- **Dogfooding**: Created from the tool that creates templates
- **Internal Development**: Shows patterns used to build Taskwright itself
- **Educational**: Learn orchestrator + DI + agent systems
- **NOT for**: General Python APIs (use fastapi-python instead)

---

### Universal Templates (1 template)

#### 6. default (8+/10)
- **Source**: Language-agnostic patterns
- **Use Case**: Any language (Go, Rust, Ruby, Elixir, PHP, etc.)
- **Patterns**: Universal project structure, adaptable workflows
- **Tech Stack**: Language-agnostic
- **Best For**: Languages not covered by stack-specific templates
- **Restored**: TASK-060A (quality improvements)

---

## Selection Guide

### Quick Decision Table

| Your Need | Recommended Template |
|-----------|---------------------|
| React SPA / Frontend | **react-typescript** |
| REST API / Backend | **fastapi-python** |
| Full-stack web app | **nextjs-fullstack** |
| Full-stack monorepo | **react-fastapi-monorepo** |
| CLI tool with orchestration | **taskwright-python** |
| Understand Taskwright's code | **taskwright-python** |
| Go / Rust / Ruby / PHP | **default** |
| Any other language | **default** |

### Detailed Selection Criteria

#### Choose react-typescript if:
- ✅ Building a single-page application
- ✅ Modern React with TypeScript
- ✅ Need component library structure
- ✅ Want feature-based architecture
- ❌ Need server-side rendering (use nextjs-fullstack)
- ❌ Need backend API (use fastapi-python or nextjs-fullstack)

#### Choose fastapi-python if:
- ✅ Building REST APIs
- ✅ Python backend services
- ✅ Need layered architecture
- ✅ Want OpenAPI/Swagger docs
- ❌ Need frontend (use nextjs-fullstack or monorepo)
- ❌ Building CLI tools (use taskwright-python)

#### Choose nextjs-fullstack if:
- ✅ Full-stack application
- ✅ Server-side rendering required
- ✅ React + API routes in one project
- ✅ Need SEO optimization
- ❌ Pure SPA (use react-typescript)
- ❌ Separate frontend/backend repos (use monorepo or separate templates)

#### Choose react-fastapi-monorepo if:
- ✅ Full-stack with separate frontend/backend
- ✅ Type-safe contracts between FE/BE
- ✅ Concurrent frontend + backend development
- ✅ Shared code across services
- ❌ Simple full-stack app (use nextjs-fullstack)
- ❌ Separate repositories (use individual templates)

#### Choose taskwright-python if:
- ✅ Building CLI tool with orchestration
- ✅ Want to understand Taskwright's architecture
- ✅ Need orchestrator + DI + agent patterns
- ✅ Learning internal development patterns
- ❌ Building web APIs (use fastapi-python)
- ❌ Building web apps (use react-typescript or nextjs-fullstack)
- ❌ General Python projects (use default)

#### Choose default if:
- ✅ Using Go, Rust, Ruby, Elixir, PHP
- ✅ Stack not covered by other templates
- ✅ Quick evaluation before custom template
- ✅ Language-agnostic foundation
- ❌ Using React/TypeScript (use react-typescript)
- ❌ Using Python for APIs (use fastapi-python)

---

## Template Quality

All templates meet or exceed **8.0/10 quality threshold**.

### Quality Metrics

| Template | Score | CRUD | Symmetry | Coverage | Docs |
|----------|-------|------|----------|----------|------|
| react-typescript | 9.3/10 | 95% | 90% | 85% | Excellent |
| fastapi-python | 9.2/10 | 92% | 88% | 88% | Excellent |
| nextjs-fullstack | 9.4/10 | 93% | 90% | 82% | Excellent |
| react-fastapi-monorepo | 9.2/10 | 90% | 87% | 87% | Excellent |
| taskwright-python | 8.0+/10 | 85% | 82% | 80%+ | Good |
| default | 8.0+/10 | 80% | 80% | Varies | Good |

### Quality Criteria

Quality scores reflect:
- **CRUD Completeness**: Complete create/read/update/delete operations
- **Layer Symmetry**: Consistent patterns across layers (API, domain, data)
- **Test Coverage**: Minimum 80% line coverage, 75% branch coverage
- **Pattern Consistency**: Adherence to stack-specific best practices
- **Documentation Quality**: Complete README, inline docs, setup guides
- **Production Readiness**: Real-world patterns, error handling, security

---

## Template Evolution

### History

| Version | Templates | Changes |
|---------|-----------|---------|
| Original | 9 | Initial templates, unknown quality |
| TASK-060 | 4 | Quality focus: removed 5 low-quality templates |
| TASK-060A | 5 | Reinstated `default` with quality improvements |
| TASK-062 | 5 | Added `react-fastapi-monorepo` (9.2/10) |
| TASK-066 | 6 | Added `taskwright-python` (8+/10, internal dev) |
| **Current** | **6** | **Stable, high-quality set** |

### Philosophy Evolution

**Old Approach** (9 templates):
- ❌ Many low-quality templates
- ❌ High maintenance burden
- ❌ Inconsistent quality
- ❌ Trying to cover every stack

**Current Approach** (6 templates):
- ✅ All high-quality (8+/10)
- ✅ Low maintenance
- ✅ Consistent quality
- ✅ Focus on learning + `/template-create` for production

---

## Getting Started

### Quick Start

```bash
# 1. Install Taskwright
chmod +x installer/scripts/install.sh
./installer/scripts/install.sh

# 2. Choose a template
taskwright init [template-name]

# Examples:
taskwright init react-typescript
taskwright init fastapi-python
taskwright init nextjs-fullstack
taskwright init react-fastapi-monorepo
taskwright init taskwright-python
taskwright init default
```

### Template Information

```bash
# View template details
taskwright init [template-name] --info

# Example:
taskwright init react-typescript --info
```

### After Initialization

1. **Install dependencies**: `npm install` or `pip install -r requirements.txt`
2. **Run tests**: `npm test` or `pytest tests/`
3. **Start development**: `npm run dev` or `uvicorn src.main:app --reload`
4. **Create tasks**: `/task-create "Your feature"`
5. **Implement with quality gates**: `/task-work TASK-001`

---

## Template Documentation

Each template includes:
- 📄 **README.md**: Setup, usage, project structure
- 📄 **CLAUDE.md**: AI guidance for development
- 📄 **manifest.json**: Template metadata and placeholders
- 📄 **settings.json**: Template configuration
- 📄 **validation-report.md**: Quality metrics and findings

### Deep Dive Documentation

- [react-typescript README](../../installer/global/templates/react-typescript/README.md)
- [fastapi-python README](../../installer/global/templates/fastapi-python/README.md)
- [nextjs-fullstack README](../../installer/global/templates/nextjs-fullstack/README.md)
- [react-fastapi-monorepo README](../../installer/global/templates/react-fastapi-monorepo/README.md)
- [taskwright-python README](../../installer/global/templates/taskwright-python/README.md)
- [default README](../../installer/global/templates/default/README.md)

---

## For Production: Create Your Own Template

### Recommended Workflow

1. **Evaluate** with reference templates (understand Taskwright)
2. **Build** your production project (proven patterns)
3. **Extract** template with `/template-create` (from your code)
4. **Validate** with 3-level validation system (quality assurance)
5. **Reuse** for all future projects (consistency + speed)

### Why Custom Templates?

**Your production code is better than any generic template**:
- ✅ Proven in production
- ✅ Matches your team's conventions
- ✅ Contains your specific patterns
- ✅ Reflects your architecture decisions

### Creating Custom Templates

```bash
# In your production codebase
cd your-proven-project
/template-create --validate

# Answer questions about your stack
# Template generated automatically

# Initialize new project
cd ../new-project
taskwright init your-custom-template
```

**See**: [Template Philosophy Guide](../guides/template-philosophy.md) for complete rationale.

---

## Frequently Asked Questions

### Why only 6 templates?

We focus on **quality over quantity**. These 6 templates demonstrate best practices for the most popular stacks. For production, use `/template-create` from your own proven code.

### What if my stack isn't covered?

Use the `default` template for initial structure, then use `/template-create` from your project once you've proven the patterns.

### Can I modify the reference templates?

Yes, but we recommend using them as references and creating your own with `/template-create` instead. Your production code is better than our generic templates.

### What happened to the other templates?

We reduced from 9 to 6 high-quality templates, removing 5 low-quality templates and adding 2 specialized ones. All templates now meet 8+/10 quality threshold. See [Template Migration Guide](../guides/template-migration.md).

### What makes taskwright-python special?

It's a **dogfooding example** - created from Taskwright's own codebase. Use it to understand how Taskwright itself is built or to create similar CLI tools with orchestration. It's for **internal development learning**, not general Python APIs.

### How do I share templates with my team?

Create templates using `/template-create` in your repository, commit to git, and team members run `install.sh`. See [Creating Local Templates](../guides/creating-local-templates.md).

---

## Related Documentation

- [Template Philosophy Guide](../guides/template-philosophy.md) - Complete rationale
- [Creating Local Templates](../guides/creating-local-templates.md) - Team templates
- [Template Validation Guide](../guides/template-validation-guide.md) - Quality standards
- [Template Migration Guide](../guides/template-migration.md) - Migrating from old templates

---

## Summary

**6 high-quality templates**:
- **3 production stacks** (React, FastAPI, Next.js) at 9+/10
- **2 specialized** (Monorepo, Internal Dev) at 8-9+/10
- **1 universal** (Language-agnostic) at 8+/10

**Philosophy**: Reference templates for learning, `/template-create` for production.

**Your Next Step**: Choose a template above or create your own from proven code.
