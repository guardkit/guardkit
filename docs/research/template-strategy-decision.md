# Template Strategy Decision - High-Quality Reference Implementation Approach

**Date**: 2025-01-08
**Discussion Context**: Built-in templates vs. template creation from existing code
**Decision**: Pivot to minimal, high-quality reference templates + exemplar approach

---

## Executive Summary

**Decision**: Keep built-in templates but reduce from 9 to 5 high-quality **reference implementations**. Reframe these as learning resources and demonstrations, with `/template-create` as the primary production path.

**Updated Decision (2025-01-08)**: Added 4th template (React + FastAPI Monorepo) based on additional research showing strong industry adoption and genuine use case differentiation.

**Final Update (2025-11-27)**: Removed guardkit-python template (TASK-G6D4) - GuardKit's `.claude/` is git-managed, so template initialization is not needed for GuardKit development. Final count: 5 reference templates.

**Rationale**: All major scaffolding tools (create-react-app, dotnet new, Vite) ship with default templates despite developers being highly opinionated. Built-in templates serve 6 critical functions beyond code generation.

**Impact**:
- Reduced maintenance burden (9 → 5 templates, 44% reduction)
- Higher quality through validation (8+/10 score required, 9+/10 for top-tier)
- Clearer value proposition (reference + customization)
- Better adoption path (quick start → customize)
- Serves both JavaScript and Python full-stack ecosystems

---

## The Original Question

**User Perspective**:
> "We have really powerful template creation from existing code, we have tasks to extend validation... This makes me question: do we even need the built-in templates?
>
> Individual developers and teams get so attached to their styles that every project becomes unique. Maybe we should just simplify and not bother with included templates? Developers are so opinionated they probably won't be happy with them anyway."

**Valid Observations**:
1. ✅ Developers ARE highly opinionated about code structure
2. ✅ Template creation from existing code is powerful (unique feature)
3. ✅ Customization is inevitable (evidenced by 1,245-line local template guide)

---

## Critical Analysis: Why Built-in Templates Are Essential

### Industry Evidence

**ALL major scaffolding tools ship templates**:
- **create-react-app**: Default template despite React devs being notoriously opinionated (20M+ downloads/month)
- **dotnet new**: 50+ built-in templates despite .NET teams having strong conventions
- **Vite**: Ships 6 templates (vanilla, vue, react, preact, lit, svelte) - fastest-growing build tool
- **Yeoman**: Ships core generators, community creates hundreds more

**Pattern**: Ship curated defaults + support customization = adoption success

### Six Critical Functions of Built-In Templates

Built-in templates serve purposes beyond code generation:

#### 1. **Cold Start Problem (True Greenfield)**

**Scenario**:
- First-time developers learning the stack
- Startups with no existing codebase
- Proof-of-concept projects where importing is overkill
- Evaluating GuardKit before committing

**Without templates**: "Install GuardKit, then... uh... go find some code somewhere?"

**Evidence**: The React template README is 186 lines teaching:
- Error boundaries, performance optimization (React.memo, useMemo/useCallback)
- Accessibility patterns (focus management, ARIA)
- Security patterns (XSS protection)
- SSE streaming, Test-driven development

This is **documentation as code** - removing it removes a learning resource.

#### 2. **System Validation & Testing**

**Question**: How do you test `/template-create` works correctly?

**Answer**: You need canonical reference templates.

**Evidence**: Tasks TASK-043, TASK-044, TASK-045 all assume reference templates exist to validate against.

#### 3. **Demonstration & Marketing**

**"Look what GuardKit can do"** requires working examples.

**Evidence**: Our documentation uses templates everywhere:
- `guardkit init react` appears in multiple guides
- Template selection guide compares maui-appshell vs maui-navigationpage
- Quick start shows `guardkit init [template-name]`

#### 4. **Best Practices Showcase**

**Templates demonstrate how to use GuardKit's features**.

**Evidence from React template**:
```markdown
### Component Template (`component.tsx.hbs`)
- TypeScript interfaces with JSDoc comments
- Accessibility-first implementation
- Proper prop handling and default values
- Memoization ready structure
```

This teaches users **how to write good templates**, which they'll use when creating their own via `/template-create`.

#### 5. **Adoption Friction Reduction**

Every additional step before "working code" increases abandonment.

**Industry pattern**:
- create-react-app: `npx create-react-app my-app` → working code
- dotnet new: `dotnet new react` → working code
- GuardKit without templates: "Install, then... figure out how to get code"

#### 6. **Stack-Specific Guidance**

Templates encode **years of stack-specific best practices**:

**MAUI templates include**:
- AppShell vs NavigationPage navigation patterns
- Platform-specific testing strategies
- ErrorOr functional error handling
- MVVM viewmodel patterns

Telling users "just template your own code" assumes they already know these patterns - but they're using GuardKit to LEARN them.

---

## Current State Analysis

### Existing Templates (9 total)

1. **default** - Language-agnostic
2. **react** - React + TypeScript + Next.js + Tailwind
3. **python** - FastAPI + pytest + LangGraph
4. **typescript-api** - NestJS + Result patterns
5. **maui-appshell** - .NET MAUI + AppShell + MVVM
6. **maui-navigationpage** - .NET MAUI + NavigationPage
7. **dotnet-fastendpoints** - .NET + FastEndpoints + REPR
8. **dotnet-aspnetcontroller** - .NET + Controllers + MVC
9. **dotnet-minimalapi** - .NET 8+ Minimal API

**Observation**: 5/9 are .NET variants. Questions:
- Specialization? (expertise)
- Market opportunity? (strategic)
- Scope creep? (feature bloat)

### Quality Status

**Unknown**: Templates have never been validated against comprehensive quality standards.

**Evidence**: TASK-043/044/045 created specifically to establish validation framework because quality is uncertain.

---

## Strategic Options Evaluated

### Option A: Reference Exemplar Set (5 templates) ⭐ RECOMMENDED (AS IMPLEMENTED)

**Templates**:
1. **Frontend**: React + TypeScript
2. **Backend**: Python FastAPI
3. **Full-stack (JS)**: Next.js
4. **Full-stack (Python)**: React + FastAPI Monorepo
5. **Language-agnostic**: Default template

**Rationale**:
- Covers 5 major paradigms and ecosystems
- Provides demonstration value
- Reduces maintenance burden 44% (9 → 5)
- Forces users to `/template-create` for customization (which is the real value)

**Framework Selection Evidence** (2025 adoption data):
- **Next.js**: 42.7% usage among full-stack developers, adopted by Netflix, strong SEO/performance
- **FastAPI**: Fastest-growing Python framework, production-proven by major companies
- **React + TypeScript**: Bulletproof React (28.5k stars) demonstrates production-ready patterns

### Option B: Technology-Agnostic Meta-Template (1 template)

**Templates**:
- **default** template only

**Rationale**:
- Demonstrates GuardKit concepts without technology lock-in
- Forces `/template-create` from day 1
- Minimal maintenance

**Cons**:
- No stack-specific guidance
- Limited demonstration value
- No best practices showcase

### Option C: Current Approach + Quality Bar (9 templates)

**Keep all 9 templates but**:
- Implement TASK-043/044/045 validation
- Set quality bar: All templates must score 8+/10
- Remove templates that don't meet bar

**Cons**:
- High maintenance burden
- Continued scope creep risk
- Resource intensive

---

## Decision: Option A with Quality Validation

### Final Template Set

**Five reference implementation templates**:

#### 1. Frontend: React + TypeScript

**Source Repository**: https://github.com/alan2207/bulletproof-react
- **Stars**: 28.5k
- **Features**: Production-ready architecture, scalable patterns
- **Stack**: React, TypeScript, React Query, Testing Library, Vitest, Playwright
- **Use Case**: Frontend-only applications with external API backend

**Validation Target**: 9+/10 (comprehensive audit)

#### 2. Backend: Python FastAPI

**Source Repository**: https://github.com/zhanymkanov/fastapi-best-practices
- **Stars**: 12k+
- **Features**: Production decisions from years of startup experience
- **Stack**: FastAPI, SQLAlchemy, Alembic, Pydantic, pytest
- **Use Case**: Backend API serving multiple frontends (web, mobile)

**Validation Target**: 9+/10 (comprehensive audit)

#### 3. Full-Stack: Next.js (JavaScript Ecosystem)

**Source Repository**: Next.js App Router example + production patterns
- **Features**: React Server Components, hybrid rendering, API routes
- **Stack**: Next.js 14+, TypeScript, Tailwind, Server Actions, Prisma
- **Use Case**: JavaScript/TypeScript full-stack web applications

**Validation Target**: 9+/10 (comprehensive audit)

#### 4. Full-Stack: React + FastAPI Monorepo (Python Ecosystem) **[NEW - Added 2025-01-08]**

**Source Repositories**:
- **Primary**: https://github.com/tiangolo/full-stack-fastapi-template (Official FastAPI)
- **Monorepo Tooling**: https://github.com/sinanbekar/monorepo-turborepo-python (Turborepo)
- **Type Safety**: https://abhayramesh.com/blog/type-safe-fullstack (OpenAPI → TypeScript)

**Features**:
- Type-safe full-stack (OpenAPI → TypeScript auto-generation)
- Turborepo monorepo management
- Docker Compose orchestration
- Production-proven patterns from official FastAPI template

**Stack**: React, TypeScript, FastAPI, PostgreSQL, Turborepo, Docker Compose

**Use Case**: Python-first teams (ML, data science, existing Python infrastructure)

**Validation Target**: 9+/10 (comprehensive audit)

**Why Added**:
- ✅ Research confirmed strong 2024-2025 industry adoption
- ✅ Genuinely different from Next.js (Python vs. Node.js backend)
- ✅ Type safety is compelling killer feature
- ✅ Low incremental effort (combines TASK-057 + TASK-058)
- ✅ Serves Python full-stack market segment

### Reframed Messaging

```markdown
# Built-in Templates: Learning Resources, Not Production Code

GuardKit includes five reference implementation templates for three purposes:

1. **Learning**: See how to structure templates for `/template-create`
2. **Evaluation**: Try GuardKit in <5 minutes
3. **Foundation**: Starting point for customization

**For production**: Use `/template-create` from your existing codebase.

## Template Selection Guide

| Template | When to Use |
|----------|-------------|
| **react-typescript** | Frontend with external API backend |
| **fastapi-python** | Backend API for multiple frontends |
| **nextjs-fullstack** | JavaScript/TypeScript full-stack web app |
| **react-fastapi-monorepo** | Python full-stack (ML, data, Python teams) |
| **default** | Language-agnostic (Go, Rust, Ruby, Elixir, PHP, etc.) |
```

---

## Implementation Plan

### Phase 1: Validate Current Templates (TASK-056)

**Goal**: Run TASK-044 comprehensive audit on all 9 existing templates

**Actions**:
1. Implement `/template-validate` command (TASK-044)
2. Run 16-section audit on each template
3. Document scores and findings
4. Identify templates that pass 8+/10 threshold

**Duration**: 3-5 days (once TASK-044 complete)

### Phase 2: Create New Reference Templates (TASK-057, TASK-058, TASK-059, TASK-062, TASK-DEFAULT)

**TASK-057: Create React + TypeScript Reference Template**
- Source: bulletproof-react repository
- Use `/template-create` to generate from source
- Validate with `/template-validate`
- Achieve 9+/10 score
- Duration: 5-7 days

**TASK-058: Create FastAPI Reference Template**
- Source: fastapi-best-practices repository
- Use `/template-create` to generate from source
- Validate with `/template-validate`
- Achieve 9+/10 score
- Duration: 5-7 days

**TASK-059: Create Next.js Reference Template**
- Source: Next.js app-router production example
- Use `/template-create` to generate from source
- Validate with `/template-validate`
- Achieve 9+/10 score
- Duration: 7-10 days

**TASK-062: Create React + FastAPI Monorepo Reference Template [NEW]**
- Source: Official Full Stack FastAPI Template + Turborepo structure
- Combine TASK-057 + TASK-058 with monorepo tooling
- Add type safety (OpenAPI → TypeScript generation)
- Docker Compose orchestration
- Validate with `/template-validate`
- Achieve 9+/10 score
- Duration: 3-5 days
- **Depends on**: TASK-057 and TASK-058 completion

**TASK-DEFAULT: Maintain Default Template**
- Source: GuardKit's generic patterns
- Validate language-agnostic approach
- Achieve 8+/10 score
- Duration: 1-2 days

### Phase 3: Remove Low-Quality Templates (TASK-060)

**Goal**: Remove templates that don't pass quality bar

**Actions**:
1. Remove templates scoring <8/10
2. Update documentation to remove references
3. Add migration guide for users of removed templates
4. Archive removed templates in separate branch

### Phase 4: Update Documentation & Messaging (TASK-061)

**Goal**: Reframe templates as "reference implementations"

**Actions**:
1. Update CLAUDE.md with new messaging
2. Update README.md with template strategy
3. Create "Template Philosophy" guide
4. Update all template references in documentation
5. Add community template gallery concept

### Phase 5: Template Location Strategy (TASK-021)

**Goal**: Resolve template creation location workflow

**Recommendation** (based on TASK-021 analysis): **Solution D - Smart Detection**

**Logic**:
```bash
if [[ inside guardkit repo ]]; then
    OUTPUT_DIR="installer/core/templates/"
    echo "📦 Template for distribution (in repo)"
elif [[ --to-repo flag ]]; then
    OUTPUT_DIR="installer/core/templates/"
    echo "📦 Template for distribution"
else
    OUTPUT_DIR="$HOME/.agentecflow/templates/"
    echo "👤 Template for personal use (in global)"
fi
```

**Benefits**:
- Personal templates: Immediate use (written to `~/.agentecflow/templates/`)
- Team/distribution templates: Version control (written to repo with `--to-repo` flag)
- Smart defaults based on context
- Clear feedback on where template was created

---

## Success Metrics

### Quantitative

- ✅ Template count reduced from 9 to 3 (67% reduction)
- ✅ All templates score 9+/10 on comprehensive audit
- ✅ Maintenance time reduced by 60%+
- ✅ Validation coverage: 100% (all templates validated)

### Qualitative

- ✅ Clear value proposition (reference + customization)
- ✅ Better onboarding experience
- ✅ Templates demonstrate best practices
- ✅ `/template-create` positioned as primary production path
- ✅ Community template gallery foundation established

---

## Risk Mitigation

### Risk 1: Users Depend on Removed Templates

**Mitigation**:
- Archive removed templates in separate branch
- Provide migration guide using `/template-create` on original source repos
- Document removal in changelog with 6-month deprecation notice

### Risk 2: New Templates Don't Pass Quality Bar

**Mitigation**:
- Use proven, production-tested source repositories
- Iterate with `/template-validate` until 9+/10 achieved
- AI-assisted validation (TASK-045) for comprehensive review

### Risk 3: Maintenance Burden Still Too High

**Mitigation**:
- Community template gallery for long-tail use cases
- Annual quality audit process
- Clear template lifecycle: create → validate → maintain → deprecate

---

## Community Template Gallery (Future)

**Concept**: Rather than shipping 50 templates, create community ecosystem.

**Structure**:
- GitHub repo: `guardkit-community-templates`
- User-contributed templates
- Rating/review system
- 3-5 "official" reference templates maintained by core team
- Community maintains everything else

**Precedent**: Yeoman ships a few core generators, community creates hundreds.

---

## Comparison: Before vs. After

| Aspect | Before (Current) | After (Recommended) |
|--------|-----------------|---------------------|
| **Template Count** | 9 templates | 3 reference templates |
| **Quality Validation** | None | 9+/10 required |
| **Maintenance Burden** | High (9 templates) | Low (3 templates, 67% reduction) |
| **Focus** | Production code | Learning resources |
| **Customization Path** | Unclear | `/template-create` primary |
| **Stack Coverage** | .NET-heavy (5/9) | Balanced (frontend/backend/full-stack) |
| **Adoption Path** | `init` → customize | `init` (demo) → `/template-create` (production) |
| **Quality Confidence** | Unknown | Validated (9+/10) |
| **Community** | None | Template gallery (future) |

---

## Exemplar Repository Selection Criteria

Templates will be created from these **production-proven** repositories:

### 1. React + TypeScript: Bulletproof React

**Repository**: https://github.com/alan2207/bulletproof-react
**Stars**: 28.5k
**Why Selected**:
- ✅ Production-ready architecture patterns
- ✅ Scalable folder structure
- ✅ Comprehensive testing setup (Vitest, Playwright, Testing Library)
- ✅ TypeScript best practices
- ✅ Real-world problem solutions

**Command**:
```bash
cd /tmp
git clone https://github.com/alan2207/bulletproof-react.git
cd bulletproof-react
/template-create
```

### 2. Python FastAPI: FastAPI Best Practices

**Repository**: https://github.com/zhanymkanov/fastapi-best-practices
**Stars**: 12k+
**Why Selected**:
- ✅ Production decisions from years of startup experience
- ✅ Scalable project structure (Netflix Dispatch-inspired)
- ✅ Dependency injection patterns
- ✅ Database migration with Alembic
- ✅ Async best practices

**Command**:
```bash
cd /tmp
git clone https://github.com/zhanymkanov/fastapi-best-practices.git
cd fastapi-best-practices
/template-create
```

### 3. Next.js Full-Stack: Production App Router Pattern

**Repository**: Next.js official examples + production patterns
**Why Selected**:
- ✅ React Server Components (2025 standard)
- ✅ Hybrid rendering (SSG, SSR, CSR, ISR)
- ✅ API routes + server actions
- ✅ TypeScript + Tailwind
- ✅ Production deployment patterns

**Command**:
```bash
npx create-next-app@latest nextjs-reference --typescript --tailwind --app
cd nextjs-reference
# Add production patterns (auth, database, testing)
/template-create
```

---

## Documentation Updates Required

### CLAUDE.md
```markdown
## Template Philosophy

GuardKit includes **5 reference implementation templates** for learning and evaluation:

1. **react-typescript** - Frontend best practices
2. **fastapi-python** - Backend API patterns
3. **nextjs-fullstack** - Full-stack application (JavaScript)
4. **react-fastapi-monorepo** - Full-stack application (Python)
5. **default** - Language-agnostic foundation

These templates demonstrate:
- How to structure templates for `/template-create`
- Stack-specific best practices
- GuardKit workflow integration

**For production**: Use `/template-create` from your existing codebase.

### Quick Start

```bash
# Evaluate GuardKit (reference template)
guardkit init react-typescript

# Production workflow (recommended)
cd your-existing-project
/template-create
guardkit init your-custom-template
```
```

### README.md
```markdown
## Templates

GuardKit ships with 5 **reference implementation templates** created from production-proven codebases:

- **react-typescript**: From [Bulletproof React](https://github.com/alan2207/bulletproof-react) (28.5k stars)
- **fastapi-python**: From [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices) (12k+ stars)
- **nextjs-fullstack**: Next.js App Router with production patterns
- **react-fastapi-monorepo**: Full-stack Python with type-safe integration
- **default**: Language-agnostic foundation for Go, Rust, Ruby, Elixir, PHP, etc.

Each template scores 8+/10 on our comprehensive quality audit (with top 3 scoring 9+/10).

### Create Your Own Templates

```bash
cd your-production-codebase
/template-create
```

See [Creating Local Templates](docs/guides/creating-local-templates.md) for details.
```

---

## Conclusion

**Keep built-in templates, but pivot strategy**:

1. ✅ Reduce from 9 to 5 high-quality reference templates
2. ✅ Create from production-proven exemplar repositories
3. ✅ Validate all templates (8+/10 minimum, 9+/10 for top tier)
4. ✅ Reframe as "learning resources" not "production code"
5. ✅ Make `/template-create` the hero feature
6. ✅ Solve template location strategy (TASK-021)
7. ✅ Foundation for community template gallery

**Result**:
- Reduced maintenance (44% fewer templates, from 9 to 5)
- Higher quality (8-9.2/10 validated)
- Clearer value prop (reference + customization)
- Better adoption path (quick demo → production customization)
- Unique differentiation (`/template-create` from real codebases)
- Removed guardkit-python (TASK-G6D4) - not needed for GuardKit development

---

## Next Steps

1. **Immediate**: Create tasks TASK-056 through TASK-061
2. **Week 1**: Complete TASK-043/044 validation framework
3. **Week 2**: Audit existing templates (TASK-056)
4. **Week 3-4**: Create new reference templates (TASK-057, TASK-058, TASK-059)
5. **Week 5**: Remove low-quality templates (TASK-060)
6. **Week 6**: Update documentation (TASK-061)
7. **Week 7**: Resolve template location strategy (TASK-021)

**Total Timeline**: ~7 weeks for complete template strategy overhaul

---

**Decision Date**: 2025-01-08
**Decision Owner**: Richard Woollcott
**Status**: Approved - Ready for Implementation
**Implementation Start**: TASK-056
