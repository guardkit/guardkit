# TASK-061: Update Template Documentation and Messaging

**Created**: 2025-01-08
**Priority**: High
**Type**: Documentation
**Parent**: Template Strategy Overhaul
**Status**: Backlog
**Complexity**: 5/10 (Medium)
**Estimated Effort**: 3-4 days
**Dependencies**: TASK-056 (Audit), TASK-057, TASK-058, TASK-059 (New templates), TASK-060 (Removals)

---

## Problem Statement

Update all documentation to reflect the new 3-template strategy, reframe templates as "reference implementations" rather than production code, and position `/template-create` as the primary production workflow.

**Goal**: Comprehensive documentation update implementing new template philosophy and messaging strategy.

---

## Context

**Related Documents**:
- [Template Strategy Decision](../../docs/research/template-strategy-decision.md)
- TASK-056: Audit findings
- TASK-057, TASK-058, TASK-059: New reference templates
- TASK-060: Template removals
- TASK-021: Template location strategy

**Old Messaging**:
- Templates as production code
- Many templates to choose from
- Templates as final solution

**New Messaging**:
- Templates as learning resources
- 3 reference implementations
- `/template-create` as primary production path
- Templates demonstrate how to build your own

---

## Objectives

### Primary Objective
Update all documentation to reflect new template strategy and messaging.

### Success Criteria
- [x] CLAUDE.md updated with new template philosophy
- [x] README.md updated with 3-template approach
- [x] All guides updated (references, examples, messaging)
- [x] New "Template Philosophy" guide created
- [x] Quick start updated
- [x] Template examples updated
- [x] Installation documentation updated
- [x] Consistent messaging across all documents

---

## Implementation Scope

### 1. Update CLAUDE.md

**File**: `/Users/richardwoollcott/Projects/appmilla_github/taskwright/CLAUDE.md`

**Changes**:

```markdown
## Template Philosophy (NEW SECTION)

Taskwright includes **3 reference implementation templates** for learning and evaluation:

1. **react-typescript** - Frontend best practices (from Bulletproof React)
2. **fastapi-python** - Backend API patterns (from FastAPI Best Practices)
3. **nextjs-fullstack** - Full-stack application (Next.js App Router)

### Why Only 3 Templates?

**Templates are learning resources, not production code.**

Each template demonstrates:
- ✅ How to structure templates for `/template-create`
- ✅ Stack-specific best practices
- ✅ Taskwright workflow integration
- ✅ Quality standards (all score 9+/10)

### For Production: Use `/template-create`

```bash
# Evaluate Taskwright (reference template)
taskwright init react-typescript

# Production workflow (recommended)
cd your-existing-project
/template-create
taskwright init your-custom-template
```

**Why?** Your production code is better than any generic template. Create templates from what you've proven works.

## Installation & Setup (UPDATE)

```bash
# Available Templates
taskwright init [react-typescript|fastapi-python|nextjs-fullstack|default]

# View template details
taskwright init react-typescript --info
```

**Template Documentation**:
- [react-typescript](installer/global/templates/react-typescript/README.md) - From Bulletproof React (28.5k stars)
- [fastapi-python](installer/global/templates/fastapi-python/README.md) - From FastAPI Best Practices (12k+ stars)
- [nextjs-fullstack](installer/global/templates/nextjs-fullstack/README.md) - Next.js App Router + production patterns

## Template Creation (EMPHASIZE MORE)

### Creating Templates from Your Codebase

**Recommended production workflow**:

```bash
cd your-production-codebase
/template-create

# Answers questions about:
# - Template name
# - Technology stack
# - Architecture patterns
# - Quality gates

# Template created and validated
# Ready to use
taskwright init your-custom-template
```

**See**: [Creating Local Templates](docs/guides/creating-local-templates.md)

## When to Use Taskwright (UPDATE)

### Use When:
- Individual tasks or small features (1-8 hours)
- Solo dev or small teams (1-3 developers)
- Need quality enforcement without ceremony
- Want AI assistance with human oversight
- Small-to-medium projects
- **Learning new stack** (use reference templates)
- **Creating team templates** (use `/template-create`)

### Use RequireKit When:
- Need formal requirements management (EARS notation, BDD scenarios)
- Need epic/feature hierarchy
- Need requirements traceability matrices
- Need PM tool integration (Jira, Linear, Azure DevOps, GitHub)
```

### 2. Update README.md

**File**: `/Users/richardwoollcott/Projects/appmilla_github/taskwright/README.md`

**Changes**:

```markdown
## Templates (NEW SECTION)

### Reference Implementation Templates

Taskwright ships with **3 high-quality reference templates** created from production-proven codebases:

| Template | Source | Stars | Focus | Score |
|----------|--------|-------|-------|-------|
| **react-typescript** | [Bulletproof React](https://github.com/alan2207/bulletproof-react) | 28.5k | Frontend | 9.3/10 |
| **fastapi-python** | [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices) | 12k+ | Backend API | 9.2/10 |
| **nextjs-fullstack** | Next.js App Router + Patterns | Official | Full-stack | 9.4/10 |

All templates validated at 9+/10 using comprehensive quality audit.

### Quick Start with Templates

```bash
# Try a reference template (evaluation)
taskwright init react-typescript

# Create your own template (production)
cd your-production-codebase
/template-create
taskwright init your-custom-template
```

### Why Only 3 Templates?

**Templates are learning resources, not production code.**

Your production codebase is better than any generic template. Use `/template-create` to generate templates from code you've proven works.

Reference templates demonstrate:
- How to structure templates
- Stack-specific best practices
- Quality standards to target
- Taskwright workflow patterns

### Create Your Own Templates

```bash
cd your-production-codebase
/template-create

# Template created with:
# ✅ Your patterns and conventions
# ✅ Your proven architecture
# ✅ Your team's best practices
# ✅ Quality validation
```

**See**: [Creating Local Templates](docs/guides/creating-local-templates.md)

## Installation (UPDATE)

```bash
chmod +x installer/scripts/install.sh
./installer/scripts/install.sh

# Initialize with reference template
taskwright init [react-typescript|fastapi-python|nextjs-fullstack]

# Or create custom template
cd your-project
/template-create
taskwright init your-custom-template
```

## Features (ADD)

### Template Creation from Real Code

Transform your production codebase into reusable templates:

```bash
cd your-production-codebase
/template-create

# AI analyzes your code:
# - Identifies patterns
# - Extracts placeholders
# - Generates manifest
# - Creates AI agents
# - Validates quality
```

**Unique to Taskwright**: Create templates from proven code, not generic examples.
```

### 3. Create Template Philosophy Guide

**File**: `docs/guides/template-philosophy.md`

```markdown
# Template Philosophy

## Overview

Taskwright's template strategy is simple: **Reference implementations for learning, `/template-create` for production.**

## The 3 Reference Templates

| Template | Purpose | When to Use |
|----------|---------|-------------|
| **react-typescript** | Learn frontend best practices | Evaluating Taskwright, learning React patterns |
| **fastapi-python** | Learn backend API patterns | Evaluating Taskwright, learning FastAPI |
| **nextjs-fullstack** | Learn full-stack development | Evaluating Taskwright, learning Next.js App Router |

## Why This Approach?

### 1. Your Code > Generic Templates

**Your production codebase**:
- ✅ Proven to work in production
- ✅ Matches your team's conventions
- ✅ Contains your specific patterns
- ✅ Reflects your architecture decisions

**Generic templates**:
- ⚠️ May not match your conventions
- ⚠️ Generic patterns (not your proven ones)
- ⚠️ Require customization anyway

### 2. Developers Are Opinionated

Every team develops unique:
- Code organization preferences
- Naming conventions
- Architecture patterns
- Technology choices
- Quality standards

**Rather than shipping 50 templates trying to cover every opinion, we provide 3 excellent examples and tools to create your own.**

### 3. Quality Over Quantity

**Old approach**: 9 templates, unknown quality, high maintenance

**New approach**: 3 templates, all 9+/10 quality, low maintenance

### 4. Learning Resource First

Reference templates teach:
- How to structure templates for `/template-create`
- What makes a template high quality
- Stack-specific best practices
- Taskwright workflow integration

## The Production Workflow

### Step 1: Evaluate with Reference Templates

```bash
# Try Taskwright quickly
taskwright init react-typescript

# Explore generated code
# See Taskwright in action
```

### Step 2: Create Your Template

```bash
# Once you're convinced, create from your code
cd your-production-codebase
/template-create

# Answer questions about your stack
# AI generates template automatically
```

### Step 3: Use Your Template

```bash
# Now use YOUR patterns, not ours
taskwright init your-custom-template

# Get YOUR best practices
# Follow YOUR conventions
```

## Comparison with Other Tools

| Tool | Approach | Taskwright Difference |
|------|----------|---------------------|
| create-react-app | 1 opinionated template | 3 reference examples + create your own |
| dotnet new | 50+ built-in templates | 3 references + `/template-create` from your code |
| Yeoman | Community generators | `/template-create` from production code |

**Unique value**: Create templates from your actual production code, not from generic examples.

## When to Use Which Template

### Use react-typescript When:
- ⏱️ Evaluating Taskwright (< 1 hour)
- 📚 Learning React + TypeScript best practices
- 🎓 Training new team members
- 🔍 Reference for building your own template

### Use fastapi-python When:
- ⏱️ Evaluating Taskwright for backend
- 📚 Learning FastAPI best practices
- 🎓 Training Python developers
- 🔍 Reference for API architecture

### Use nextjs-fullstack When:
- ⏱️ Evaluating Taskwright for full-stack
- 📚 Learning Next.js App Router
- 🎓 Training full-stack developers
- 🔍 Reference for modern Next.js

### Use `/template-create` When:
- 🚀 Production projects
- 🏢 Team/organization templates
- 🎯 Custom stack not covered by references
- ✅ You have proven production code

## FAQ

**Q: Why don't you ship templates for [my favorite stack]?**

A: Because YOUR production code is better than any template we could create. Use `/template-create` from your codebase.

**Q: Can I modify the reference templates?**

A: Yes, but we recommend using them as references and creating your own with `/template-create` instead.

**Q: What happened to the other templates?**

A: We reduced from 9 to 3 high-quality references. Old templates are archived. See [Template Migration Guide](template-migration.md).

**Q: How do I share templates with my team?**

A: Use `/template-create` in your repo, commit to git, team members run `install.sh`. See [Creating Local Templates](creating-local-templates.md).

## Related Documentation

- [Creating Local Templates](creating-local-templates.md) - Create templates from your code
- [Template Quality Validation](template-quality-validation.md) - Quality standards
- [Template Migration Guide](template-migration.md) - Migrating from old templates
- [Template Strategy Decision](../research/template-strategy-decision.md) - Full rationale
```

### 4. Update Quick Start Guide

**File**: `docs/guides/quick-start-guide.md` (if exists) or in README

**Add prominent workflow**:

```markdown
## Quick Start

### 5-Minute Evaluation

```bash
# 1. Install Taskwright
./installer/scripts/install.sh

# 2. Try a reference template
taskwright init react-typescript

# 3. Explore generated code
cd react-typescript-app
npm install
npm run dev
```

### Production Setup (Recommended)

```bash
# 1. Create template from your production code
cd your-production-codebase
/template-create

# 2. Use your template
taskwright init your-custom-template

# 3. Start working with YOUR patterns
```
```

### 5. Update All Guides with New References

**Files to update**:
- `docs/guides/*.md`
- `docs/workflows/*.md`
- Any file with template examples

**Changes**:
- Replace old template names with: `react-typescript`, `fastapi-python`, `nextjs-fullstack`
- Update examples
- Add note about `/template-create` workflow

### 6. Update Installer Documentation

**File**: `installer/scripts/install.sh` (comments) or installation guide

```bash
# Reference Templates (9+/10 Quality):
# - react-typescript: From Bulletproof React (frontend)
# - fastapi-python: From FastAPI Best Practices (backend)
# - nextjs-fullstack: Next.js App Router (full-stack)
#
# For production: Use /template-create from your codebase
```

---

## Acceptance Criteria

### Functional Requirements
- [ ] CLAUDE.md updated with new template philosophy
- [ ] README.md updated with 3-template approach
- [ ] Template Philosophy guide created
- [ ] Quick start updated
- [ ] All guides updated (no broken references)
- [ ] Installation documentation updated
- [ ] Consistent messaging across all documents

### Quality Requirements
- [ ] Messaging is clear and consistent
- [ ] Examples use new template names
- [ ] `/template-create` positioned as primary production path
- [ ] Reference templates positioned as learning resources
- [ ] No contradictions between documents

### Documentation Requirements
- [ ] Template philosophy explained clearly
- [ ] Migration path documented (TASK-060)
- [ ] Production workflow emphasized
- [ ] Reference template purposes clear

---

## Testing Requirements

### Documentation Validation
```bash
# 1. Check for old template references
grep -r "maui-navigationpage" docs/ CLAUDE.md README.md
# Expected: Only in migration guide

# 2. Verify new template references
grep -r "react-typescript" docs/ CLAUDE.md README.md
# Expected: Multiple references

# 3. Check for broken links
# (Manual review of all markdown files)

# 4. Verify messaging consistency
grep -r "reference implementation" docs/ CLAUDE.md README.md
grep -r "/template-create" docs/ CLAUDE.md README.md
# Expected: Consistent usage
```

### User Journey Testing
```bash
# 1. Follow quick start as new user
# Does it make sense?
# Are examples correct?

# 2. Follow production workflow
# Is /template-create workflow clear?
# Are instructions complete?

# 3. Check template information
taskwright init react-typescript --info
# Is information accurate and helpful?
```

---

## Files to Update (Checklist)

### Core Documentation
- [ ] `/CLAUDE.md` - Template philosophy section
- [ ] `/README.md` - Templates section, quick start
- [ ] `/.claude/CLAUDE.md` - Mirror of CLAUDE.md

### Guides
- [ ] `docs/guides/template-philosophy.md` - NEW
- [ ] `docs/guides/creating-local-templates.md` - Update examples
- [ ] `docs/guides/template-quality-validation.md` - Reference new templates
- [ ] `docs/guides/taskwright-workflow.md` - Update template examples
- [ ] `docs/guides/quick-reference.md` - Update template list
- [ ] `docs/guides/GETTING-STARTED.md` - Update quick start

### Workflows
- [ ] `docs/workflows/*.md` - Update any template references

### Testing
- [ ] `docs/testing/*.md` - Update template examples

### Research (Reference Only)
- [ ] `docs/research/template-strategy-decision.md` - Already complete
- [ ] Link from main docs to decision document

### Installation
- [ ] `installer/scripts/install.sh` - Update comments
- [ ] Any installation guides

---

## Messaging Consistency Checklist

Ensure these messages are consistent across ALL documentation:

✅ **Templates are reference implementations (learning resources)**
✅ **3 high-quality templates (9+/10 score)**
✅ **Production workflow: `/template-create` from your code**
✅ **Your code > generic templates**
✅ **Reference templates demonstrate how to build templates**
✅ **Each template from production-proven repository**

---

## Success Metrics

**Quantitative**:
- All documentation updated: 100%
- Zero broken template references
- Consistent messaging: 100% of documents
- Template Philosophy guide created: ✅

**Qualitative**:
- Clear differentiation: reference vs. production
- Obvious value proposition
- Easy to understand workflow
- New users understand approach quickly

---

## Related Tasks

- **TASK-056**: Audit findings inform documentation
- **TASK-057**: react-typescript template (document features)
- **TASK-058**: fastapi-python template (document features)
- **TASK-059**: nextjs-fullstack template (document features)
- **TASK-060**: Template removal (migration guide)
- **TASK-021**: Template location strategy (integrate decision)

---

**Document Status**: Ready for Implementation (after TASK-056, TASK-057, TASK-058, TASK-059, TASK-060)
**Created**: 2025-01-08
**Parent Epic**: Template Strategy Overhaul
