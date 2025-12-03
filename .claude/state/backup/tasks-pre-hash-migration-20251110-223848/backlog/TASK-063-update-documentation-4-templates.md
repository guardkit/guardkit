# TASK-063: Update Documentation for 4-Template Strategy

**Created**: 2025-01-08
**Priority**: High
**Type**: Documentation
**Parent**: Template Strategy Overhaul
**Status**: Backlog
**Complexity**: 5/10 (Medium)
**Estimated Effort**: 3-4 days
**Dependencies**: TASK-060 (Removals), TASK-061 (Base documentation), TASK-062 (Monorepo template)

---

## Problem Statement

Update all documentation to reflect the 4-template strategy (adding React + FastAPI Monorepo as 4th template) after initial documentation was created for 3-template approach in TASK-061.

**Goal**: Comprehensive documentation update adding React + FastAPI Monorepo template to all guides and references.

---

## Context

**Related Documents**:
- [Template Strategy Decision](../../docs/research/template-strategy-decision.md) - Updated with 4th template
- TASK-061: Base documentation updates (3 templates)
- TASK-062: React + FastAPI Monorepo template
- TASK-060: Template removals

**Change from TASK-061**:
- **Was**: 3 templates (react-typescript, fastapi-python, nextjs-fullstack)
- **Now**: 4 templates (+ react-fastapi-monorepo)

**New Template**:
- **Name**: react-fastapi-monorepo
- **Focus**: Python full-stack with type safety
- **Use Case**: ML/data teams, existing Python infrastructure

---

## Objectives

### Primary Objective
Update all documentation to include 4th template (React + FastAPI Monorepo) while maintaining consistency with TASK-061 messaging.

### Success Criteria
- [x] CLAUDE.md updated to include 4th template
- [x] README.md updated with 4-template approach
- [x] All guides updated with monorepo examples
- [x] Template selection guide updated
- [x] Installation documentation updated
- [x] Consistent messaging (4 templates, not 3)
- [x] Template Philosophy guide updated
- [x] No contradictions between documents

---

## Implementation Scope

### 1. Update CLAUDE.md

**File**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit/CLAUDE.md`

**Changes**:

```markdown
## Installation & Setup (UPDATE)

```bash
# Available Templates
guardkit init [react-typescript|fastapi-python|nextjs-fullstack|react-fastapi-monorepo|default]

# View template details
guardkit init react-typescript --info
```

**Template Documentation**:
- [react-typescript](installer/global/templates/react-typescript/README.md) - Frontend (Bulletproof React)
- [fastapi-python](installer/global/templates/fastapi-python/README.md) - Backend API (FastAPI Best Practices)
- [nextjs-fullstack](installer/global/templates/nextjs-fullstack/README.md) - JavaScript Full-Stack
- [react-fastapi-monorepo](installer/global/templates/react-fastapi-monorepo/README.md) - Python Full-Stack Monorepo

## Template Selection Guide (NEW SECTION)

| Template | Best For | Stack |
|----------|----------|-------|
| **react-typescript** | Frontend with external API | React + TypeScript |
| **fastapi-python** | Backend API for multiple clients | FastAPI + Python |
| **nextjs-fullstack** | JavaScript full-stack web apps | Next.js + TypeScript |
| **react-fastapi-monorepo** | Python full-stack (ML, data) | React + FastAPI + Turborepo |

### When to Use Each Template

**react-typescript**: Use when you have (or plan to have) a separate backend API. Best for:
- Frontend developers
- Teams with existing backend services
- Mobile + web sharing same API

**fastapi-python**: Use when building backend-only API. Best for:
- Backend developers
- Microservices architecture
- Multiple frontends (web, mobile, desktop)

**nextjs-fullstack**: Use when building complete web application with JavaScript/TypeScript. Best for:
- JavaScript/TypeScript teams
- Rapid full-stack development
- SEO-critical applications
- Teams wanting single deployment

**react-fastapi-monorepo**: Use when building full-stack with Python backend. Best for:
- Python-first teams (ML, data science)
- Type-safe Python ↔ TypeScript integration
- Teams with existing Python infrastructure
- Separate frontend/backend scaling needs

## Available Templates (UPDATE)

```bash
guardkit init [react-typescript|fastapi-python|nextjs-fullstack|react-fastapi-monorepo]
```

**All templates validated at 9+/10 quality score.**
```

### 2. Update README.md

**File**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit/README.md`

**Changes**:

```markdown
## Templates (UPDATE SECTION)

### Reference Implementation Templates

GuardKit ships with **4 high-quality reference templates** created from production-proven codebases:

| Template | Source | Stars | Focus | Score |
|----------|--------|-------|-------|-------|
| **react-typescript** | [Bulletproof React](https://github.com/alan2207/bulletproof-react) | 28.5k | Frontend | 9.3/10 |
| **fastapi-python** | [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices) | 12k+ | Backend API | 9.2/10 |
| **nextjs-fullstack** | Next.js App Router + Patterns | Official | JS Full-Stack | 9.4/10 |
| **react-fastapi-monorepo** | [Full Stack FastAPI](https://github.com/tiangolo/full-stack-fastapi-template) + Turborepo | Official | Python Full-Stack | 9.1/10 |

All templates validated at 9+/10 using comprehensive quality audit.

### Quick Start with Templates

```bash
# Frontend only
guardkit init react-typescript

# Backend API only
guardkit init fastapi-python

# JavaScript full-stack
guardkit init nextjs-fullstack

# Python full-stack (monorepo)
guardkit init react-fastapi-monorepo

# Create your own template (production)
cd your-production-codebase
/template-create
guardkit init your-custom-template
```

### Why Only 4 Templates?

**Templates are learning resources, not production code.**

Each template serves a distinct use case:
1. **react-typescript**: Frontend development patterns
2. **fastapi-python**: Backend API patterns
3. **nextjs-fullstack**: JavaScript full-stack patterns
4. **react-fastapi-monorepo**: Python full-stack patterns

Your production codebase is better than any generic template. Use `/template-create` to generate templates from code you've proven works.
```

### 3. Update Template Philosophy Guide

**File**: `docs/guides/template-philosophy.md`

**Add new section**:

```markdown
## The 4 Reference Templates

| Template | Purpose | When to Use |
|----------|---------|-------------|
| **react-typescript** | Learn frontend best practices | Frontend with external API |
| **fastapi-python** | Learn backend API patterns | Backend serving multiple frontends |
| **nextjs-fullstack** | Learn JavaScript full-stack | JavaScript teams, rapid development |
| **react-fastapi-monorepo** | Learn Python full-stack | Python teams, ML/data applications |

## Template Comparison

### Full-Stack Options: Next.js vs React + FastAPI Monorepo

Both are full-stack templates, but serve different use cases:

**nextjs-fullstack**:
- ✅ JavaScript/TypeScript end-to-end
- ✅ Simpler deployment (one service)
- ✅ Faster development (one language)
- ✅ Better for pure web applications
- ❌ Can't leverage Python libraries (ML, data science)
- ❌ Node.js backend only

**react-fastapi-monorepo**:
- ✅ Python backend (ML, data science, existing infra)
- ✅ Type safety (OpenAPI → TypeScript)
- ✅ Separate scaling (frontend CDN, backend servers)
- ✅ Leverage Python ecosystem
- ✅ Monorepo organization (Turborepo)
- ⚠️ More complex deployment (two services)
- ⚠️ Two languages to maintain

**Decision Guide**:
- Pure web app, JavaScript team → **nextjs-fullstack**
- ML/data/Python infrastructure → **react-fastapi-monorepo**
```

### 4. Update Quick Start Guide

**Add monorepo quick start**:

```markdown
## Quick Start - React + FastAPI Monorepo

### 5-Minute Setup

```bash
# 1. Install GuardKit
./installer/scripts/install.sh

# 2. Initialize monorepo template
guardkit init react-fastapi-monorepo

# 3. Start with Docker Compose
cd react-fastapi-monorepo-app
docker-compose up

# 4. Explore
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Type Safety Demo

```bash
# Generate TypeScript types from Python backend
pnpm generate-types

# Check generated types
cat packages/shared-types/src/schemas.ts

# Frontend now has full type safety calling backend!
```
```

### 5. Update Installation Documentation

**Update template list everywhere**:

```bash
# Search and update all occurrences
grep -r "3 templates" docs/ CLAUDE.md README.md
# Replace with "4 templates"

grep -r "react-typescript|fastapi-python|nextjs-fullstack" docs/
# Add |react-fastapi-monorepo
```

### 6. Update Template Migration Guide

**File**: `docs/guides/template-migration.md`

**Add migration path for users who might want to migrate to monorepo**:

```markdown
## Migrating to React + FastAPI Monorepo

### From Separate react-typescript + fastapi-python

If you're currently using separate templates and want to combine into monorepo:

```bash
# 1. Create new monorepo
mkdir my-monorepo
cd my-monorepo
guardkit init react-fastapi-monorepo

# 2. Copy your existing code
cp -r ../my-frontend/* apps/frontend/
cp -r ../my-backend/* apps/backend/

# 3. Setup type generation
pnpm generate-types

# 4. Update imports to use shared types
# ... (detailed migration steps)
```
```

---

## Files to Update (Checklist)

### Core Documentation
- [ ] `/CLAUDE.md` - Add 4th template, template selection guide
- [ ] `/README.md` - Update to 4 templates, add monorepo
- [ ] `/.claude/CLAUDE.md` - Mirror of CLAUDE.md

### Guides
- [ ] `docs/guides/template-philosophy.md` - Add 4th template section
- [ ] `docs/guides/creating-local-templates.md` - Update examples
- [ ] `docs/guides/template-quality-validation.md` - Reference monorepo template
- [ ] `docs/guides/guardkit-workflow.md` - Update template examples
- [ ] `docs/guides/quick-reference.md` - Update template list (3→4)
- [ ] `docs/guides/GETTING-STARTED.md` - Add monorepo quick start
- [ ] `docs/guides/template-migration.md` - Add monorepo migration path

### Workflows
- [ ] `docs/workflows/*.md` - Update any template references

### Research
- [ ] `docs/research/template-strategy-decision.md` - Already updated ✅

### Installation
- [ ] `installer/scripts/install.sh` - Update comments (3→4 templates)

---

## Acceptance Criteria

### Functional Requirements
- [ ] All documentation references 4 templates (not 3)
- [ ] react-fastapi-monorepo included in all template lists
- [ ] Template selection guide explains when to use each
- [ ] Quick start examples include monorepo
- [ ] Migration paths documented
- [ ] No broken references

### Quality Requirements
- [ ] Messaging consistent with TASK-061 (reference implementations)
- [ ] Clear differentiation between templates
- [ ] Examples use correct template names
- [ ] `/template-create` still positioned as production path

### Documentation Requirements
- [ ] Monorepo use cases explained
- [ ] Type safety benefits documented
- [ ] Docker Compose workflow shown
- [ ] Comparison with Next.js clarified

---

## Testing Requirements

### Documentation Validation
```bash
# 1. Check for "3 templates" references
grep -r "3 templates" docs/ CLAUDE.md README.md
# Expected: None (should be "4 templates")

# 2. Verify all 4 templates referenced
grep -r "react-fastapi-monorepo" docs/ CLAUDE.md README.md
# Expected: Multiple references

# 3. Check template lists
grep -A 5 "guardkit init" docs/ CLAUDE.md README.md
# Expected: All lists include react-fastapi-monorepo

# 4. Verify template selection guide exists
cat docs/guides/template-philosophy.md | grep -A 10 "Template Comparison"
# Expected: Comparison between Next.js and monorepo
```

---

## Incremental Updates from TASK-061

Since TASK-061 already did base documentation for 3 templates, this task is **incremental updates** only:

**TASK-061 Created**:
- ✅ Template Philosophy guide
- ✅ Updated CLAUDE.md (for 3 templates)
- ✅ Updated README.md (for 3 templates)
- ✅ Updated all guides

**TASK-063 Adds**:
- 🔄 Add 4th template to CLAUDE.md
- 🔄 Add 4th template to README.md
- 🔄 Add template selection guide (4 templates)
- 🔄 Add monorepo quick start
- 🔄 Add Next.js vs Monorepo comparison
- 🔄 Update all "3 templates" → "4 templates"

**Effort**: Should be faster than TASK-061 since it's incremental additions.

---

## Success Metrics

**Quantitative**:
- All documentation updated: 100%
- Zero references to "3 templates" only
- All template lists include 4 templates
- Template selection guide created: ✅

**Qualitative**:
- Clear when to use each template
- Monorepo benefits explained
- No confusion between Next.js and monorepo
- Type safety value proposition clear

---

## Related Tasks

- **TASK-061**: Base documentation (3 templates) - builds on this
- **TASK-062**: Monorepo template creation - prerequisite
- **TASK-060**: Template removal - prerequisite
- **TASK-056**: Audit findings - informs documentation

---

**Document Status**: Ready for Implementation (after TASK-061, TASK-062)
**Created**: 2025-01-08
**Parent Epic**: Template Strategy Overhaul
**Note**: Incremental update to TASK-061, not full rewrite
