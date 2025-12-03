# Structuring Open-Source Demos That Win Over Skeptical CTOs

**Date**: 2025-05-30
**Purpose**: Best practices for organizing TaskWright demo repositories
**Target Audience**: Developers and CTOs who respond with "show me the code"

---

## Executive Summary

**Mono-repo wins for discoverability and maintenance**, based on how Vercel, Prisma, and tRPC structure their examples. The key differentiator for convincing technical audiences isn't the structure itself—it's demonstrating production patterns like error handling, testing, and CI/CD that distinguish professional work from "AI slop."

The most effective pattern combines a **dedicated examples mono-repo** (like Prisma's `prisma-examples`) with **branch-based before/after states** for showing your tool's impact.

---

## Repository Structure: Mono-Repo Wins

Analysis of major developer tool companies reveals a clear winner: **dedicated examples mono-repo** separate from your main tool repository.

### Why Mono-Repo

| Approach | Example | Pros | Cons |
|----------|---------|------|------|
| Mono-repo (dedicated) | Prisma `prisma-examples` | Single location, easy discovery, consistent quality | Large size |
| Examples in main repo | Vercel/Next.js | Ships with releases | Friction - must clone entire framework |
| Multiple repos | Supabase community | Focused repos | Fragmented, quality varies |

### Recommended Structure

```
guardkit-examples/
├── README.md                    # Index table with all examples
├── fastapi/
│   ├── basic-crud/
│   ├── with-authentication/
│   └── production-ready/
├── nextjs/
│   ├── basic-crud/
│   ├── with-authentication/
│   └── fullstack-app/
├── svelte/
│   └── kartlog-demo/           # Real-world brownfield demo
└── docs/
    ├── demo-prompts.md         # Prompts used for each example
    └── quality-metrics.md      # Test coverage, lint scores
```

**Naming convention**: Use `[framework]-[feature]` pattern (e.g., `fastapi-crud`, `nextjs-auth`). Makes examples immediately scannable.

---

## Branch Strategy: Before/After with Tagged Checkpoints

### Two-Branch Pattern

```
main        → Polished, production-ready solution
starter     → Realistic starting point (not empty)

Tags:
v0.0.0-starter    → Initial state snapshot
v0.1.0-generated  → After AI generation (raw output)
v1.0.0-production → After human refinement and testing
```

### Critical Insight

The `starter` branch shouldn't be a blank project. It should be a **realistic codebase with real complexity**—existing models, partial implementations, technical debt. This demonstrates the tool works on real code, not greenfield projects any tool can handle.

### For Each Feature Demo

```bash
# User can compare states
git diff starter..feature/weather

# Or pick up where we left off
git checkout starter
guardkit task-work TASK-001
```

---

## README Pattern for Maximum Impact

### Time-Optimized Structure

Developers should be able to understand and run your demo in under 5 minutes:

```markdown
# Example: Production-Ready FastAPI with TaskWright

> ⏱️ **Time to run**: ~3 minutes | **Difficulty**: Intermediate

## What This Demonstrates
[Your Tool] generating a complete authentication system with JWT tokens, 
password hashing, and refresh token rotation—production patterns, not toy demos.

## Quick Start
```bash
git clone https://github.com/yourorg/examples
cd examples/fastapi-auth
git checkout starter        # See the "before" state
guardkit task-work        # Run the tool
git diff main               # Compare with solution
```

## The Prompts Used
```
Add JWT authentication with refresh tokens. Include:
- Password hashing with bcrypt
- Token refresh endpoint
- Proper error responses (401, 403)
```

## What Was Generated vs. Modified
| Component | Generated | Human-Modified |
|-----------|-----------|----------------|
| Auth routes | ✅ | Minor type fixes |
| JWT utils | ✅ | Added logging |
| Tests | ✅ | Added edge cases |

## Quality Scorecard
- ✅ 94% test coverage
- ✅ Type hints throughout (mypy strict)
- ✅ Ruff linting passes
- ✅ OpenAPI docs auto-generated
```

### Key Elements

1. **Time estimate** - Respect developers' time
2. **Prompts used** - Transparency builds trust
3. **Generated vs Modified** - Honest about what AI did
4. **Quality metrics** - Quantitative proof, not testimonials

---

## Production Quality Signals

### What Skeptical CTOs Look For

These are patterns AI typically gets wrong:

| Quality Signal | Why It Matters | How to Demonstrate |
|----------------|----------------|-------------------|
| Error handling edge cases | AI produces happy-path code | Tests for invalid inputs, network failures |
| Consistent code style | AI output varies by prompt | Linting config with zero warnings |
| Meaningful test coverage | AI tests the obvious | Integration tests, not just unit tests |
| Security considerations | AI misses auth edge cases | Rate limiting, input validation |
| Observability | Often omitted by AI | Structured logging, health checks |
| "Why" documentation | AI writes "what" not "why" | Inline comments explaining decisions |

### Include in Every Demo

- [ ] CI/CD pipeline (GitHub Actions badge)
- [ ] Test coverage report
- [ ] Linting passing
- [ ] Type checking (mypy, TypeScript)
- [ ] Security scan results
- [ ] Performance metrics where relevant

---

## FastAPI Demo Structure

For Python/FastAPI demos targeting skeptical CTOs:

```
fastapi-production-example/
├── src/
│   ├── auth/
│   │   ├── router.py           # Endpoints
│   │   ├── schemas.py          # Pydantic models
│   │   ├── models.py           # SQLAlchemy
│   │   ├── service.py          # Business logic
│   │   ├── dependencies.py     # Auth dependencies
│   │   └── exceptions.py       # Custom exceptions
│   ├── config.py               # Pydantic BaseSettings
│   └── main.py
├── tests/
│   ├── conftest.py             # Fixtures with async client
│   └── auth/
├── alembic/                    # Database migrations
├── .github/workflows/ci.yml
├── Dockerfile
└── pyproject.toml              # Modern Python packaging
```

### Production Signals

- **Async test client** using `httpx` + `pytest-anyio`
- **Pydantic BaseSettings** with `@lru_cache`
- **Custom exception classes** per domain
- **Alembic migrations** with descriptive names
- **Ruff** for linting (modern replacement for black + isort)
- **Pre-commit hooks** configured

---

## Next.js Demo Structure

For Next.js in 2025, **App Router with TypeScript** is non-negotiable:

```
nextjs-production-example/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── api/
│   ├── components/
│   │   └── ui/
│   ├── lib/
│   └── types/
├── tests/
│   └── e2e/
├── .github/workflows/ci.yml
└── next.config.ts              # .ts not .js
```

### Required for Credibility

- Error boundaries
- Loading states
- Proper metadata/SEO
- Environment variable validation
- Playwright or Cypress E2E tests

---

## Stack Prioritization

### Recommended Launch Sequence

1. **FastAPI/Python first** - Primary AI coding tool audience
2. **Next.js fullstack** - Popular, demonstrates frontend + backend
3. **Svelte/real-world** - Shows flexibility beyond templates

### Why Python First

- Python developers are primary AI coding tool audience
- FastAPI's type hints make generated code quality visible
- Auto-generated OpenAPI docs are immediate visual proof
- CLI tools often target backend developers first

---

## What Makes Demos Compelling

### Do This

- **Real applications, not tutorials** - Prisma links to Cal.com, Dub.co
- **Live deployed demos** - tRPC provides working sites
- **Reproducible benchmarks** - Aider publishes tests anyone can run
- **Quantitative metrics** - Test coverage, lint scores, type coverage

### Avoid This

- Toy examples (todo apps, counters)
- Contrived features no one would build
- Missing tests or "tests coming soon"
- Broken builds or outdated dependencies
- Generic code that could come from any tool

---

## Quality Scorecard Template

Include in every demo README:

```markdown
## Quality Scorecard

| Metric | Score | Notes |
|--------|-------|-------|
| Test Coverage | 87% | `npm run test:coverage` |
| Type Coverage | 94% | mypy strict mode |
| Lint Warnings | 0 | Ruff + ESLint |
| Bundle Size | 145kb | Gzipped |
| Lighthouse | 96 | Performance score |
| Accessibility | AA | WCAG compliant |

### What TaskWright Generated vs Modified

| File | Generated | Human Modified | Notes |
|------|-----------|----------------|-------|
| `auth/router.py` | ✅ | 2 lines | Added logging |
| `auth/tests.py` | ✅ | 15 lines | Edge cases |
| `config.py` | ❌ | N/A | Already existed |
```

---

## CI/CD for Demo Verification

### GitHub Actions Example

```yaml
name: Verify Demo Projects

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # Weekly verification

jobs:
  verify-fastapi:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install and test
        working-directory: fastapi/production-example
        run: |
          pip install -r requirements.txt
          pytest tests/ -v --cov=src --cov-fail-under=80
          ruff check src/
          mypy src/
```

### Why Weekly Runs

Catches dependency rot before users find it. Nothing kills credibility faster than a demo that doesn't work.

---

## Summary: Checklist for Demo Success

### Repository

- [ ] Dedicated mono-repo for examples
- [ ] Clear folder structure by framework/feature
- [ ] README index table linking all examples
- [ ] CI/CD verifying all demos weekly

### Each Demo

- [ ] `starter` branch with realistic starting point
- [ ] `main` branch with production-ready solution
- [ ] Tagged versions for checkpoints
- [ ] README with <5 minute quick start
- [ ] Prompts/commands documented
- [ ] Generated vs modified table
- [ ] Quality scorecard with metrics

### Code Quality

- [ ] 80%+ test coverage
- [ ] Zero lint warnings
- [ ] Type checking passing
- [ ] CI/CD badge in README
- [ ] No TODOs or broken code

### For AI Tool Demos Specifically

- [ ] Document exact prompts used
- [ ] Show raw output vs refined code
- [ ] Include time taken
- [ ] Be honest about modifications needed

---

## References

- Prisma Examples: https://github.com/prisma/prisma-examples
- Vercel Next.js Examples: https://github.com/vercel/next.js/tree/canary/examples
- tRPC Examples: https://github.com/trpc/trpc/tree/main/examples
- Aider Benchmarks: https://aider.chat/docs/leaderboards/
- FastAPI Best Practices: https://github.com/zhanymkanov/fastapi-best-practices
