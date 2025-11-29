# Structuring open-source demos that win over skeptical CTOs

**Mono-repo wins for discoverability and maintenance**, based on how Vercel, Prisma, and tRPC structure their examples. The key differentiator for convincing technical audiences isn't the structure itself—it's demonstrating production patterns like error handling, testing, and CI/CD that distinguish professional work from "AI slop." Your demos should be real-world implementations, not toy tutorials.

The most effective pattern emerging from successful developer tools combines a **dedicated examples mono-repo** (like Prisma's `prisma-examples`) with **branch-based before/after states** for showing your tool's impact. This lets skeptical developers clone a realistic codebase, see the "before" state, then examine exactly what your tool produced.

## Mono-repo with categorized examples beats separate repos

Analysis of four major developer tool companies reveals a clear winner: **dedicated examples mono-repo** separate from your main tool repository. Prisma's approach stands out as the gold standard—their `prisma-examples` repo contains ~40 examples organized by stack in clear tables, with automated dependency updates via GitHub Actions keeping everything current.

**Vercel's approach** (examples inside the main Next.js repo) works for them because examples ship with framework releases, but creates friction—contributors must clone the entire framework just to modify an example. **Supabase's hybrid** approach (main repo + 151 community repos) fragments discoverability and creates quality inconsistency.

The recommended structure follows Prisma's pattern:

```
examples/
├── README.md                    # Index table with all examples
├── fastapi/
│   ├── basic-crud/
│   ├── with-authentication/
│   └── production-ready/
├── nextjs/
│   ├── basic-crud/
│   ├── with-authentication/
│   └── fullstack-app/
└── deployment-platforms/
    ├── vercel/
    └── railway/
```

**Naming convention**: Use `[framework]-[feature]` pattern (e.g., `fastapi-crud`, `nextjs-auth`). Prisma and tRPC both follow this convention because it makes examples immediately scannable.

## Branch strategy: starter/solution with tagged checkpoints

The most effective before/after pattern combines **two persistent branches** with **semantic version tags**. This approach, derived from LinkedIn Learning and Kent C. Dodds workshop patterns, lets users either compare states or "pick up where you left off."

```
main        → Polished, production-ready solution
starter     → Realistic starting point (not empty, but needs your tool)

Tags:
v0.0.0-starter    → Initial state snapshot
v0.1.0-generated  → After AI generation (raw output)
v1.0.0-production → After human refinement and testing
```

**The critical insight**: Your `starter` branch shouldn't be a blank project. It should be a **realistic codebase with real complexity**—existing models, partial implementations, technical debt. This demonstrates your tool works on real code, not greenfield projects that any tool can handle.

For CLI tools specifically, include a `DEMO.md` file documenting:
- The exact prompts/commands used
- Model and settings (for AI tools)
- What was generated vs. manually modified
- Time taken for each step

## README patterns that convert skeptics

The most effective example READMEs follow a **time-optimized structure** designed to get developers running code in under 5 minutes. Based on analysis of highly-starred repos and GitHub's own documentation guidelines:

```markdown
# Example: Production-Ready FastAPI with [Your Tool]

> ⏱️ **Time to run**: ~3 minutes | **Difficulty**: Intermediate

![Demo GIF showing the tool in action]

## What This Demonstrates
This example shows [Your Tool] generating a complete authentication system 
with JWT tokens, password hashing, and refresh token rotation—patterns 
you'd find in production applications, not toy demos.

## Quick Start
```bash
git clone https://github.com/yourorg/examples
cd examples/fastapi-auth
git checkout starter        # See the "before" state
# ... run your tool ...
git diff main              # Compare with production solution
```

## The Prompts Used
```
Add JWT authentication with refresh tokens. Include:
- Password hashing with bcrypt
- Token refresh endpoint
- Proper error responses (401, 403)
- Rate limiting on auth endpoints
```

## What Was Generated vs. Modified
| Component | Generated | Human-Modified |
|-----------|-----------|----------------|
| Auth routes | ✅ | Minor type fixes |
| JWT utils | ✅ | Added logging |
| Tests | ✅ | Added edge cases |
| CI config | ❌ | Written manually |

## Code Quality Signals
- ✅ 94% test coverage
- ✅ Type hints throughout (mypy strict)
- ✅ Ruff linting passes
- ✅ OpenAPI docs auto-generated
```

**Key patterns for AI tool demos specifically**: Document prompts used, show what was generated versus manually modified, and include the CI/CD pipeline in the example itself. Aider's benchmark leaderboard demonstrates that **quantitative proof** (test coverage, linting scores, benchmark results) matters more to technical audiences than testimonials.

## FastAPI examples should demonstrate production patterns

For FastAPI demos targeting skeptical CTOs, the structure must signal production-readiness through architecture choices, not just working code. Based on the `fastapi-best-practices` repository (1.5+ years production experience):

```
fastapi-production-example/
├── src/
│   ├── auth/
│   │   ├── router.py           # Endpoints
│   │   ├── schemas.py          # Pydantic models
│   │   ├── models.py           # SQLAlchemy/SQLModel
│   │   ├── service.py          # Business logic
│   │   ├── dependencies.py     # Auth dependencies
│   │   └── exceptions.py       # Custom exceptions
│   ├── config.py               # Pydantic BaseSettings
│   ├── database.py
│   └── main.py
├── tests/
│   ├── conftest.py             # Fixtures with async client
│   └── auth/
│       └── test_auth.py
├── alembic/                    # Database migrations
├── .github/workflows/ci.yml    # CI/CD pipeline
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml              # Modern Python packaging
```

**Production signals that matter to CTOs**:
- **Async test client from day one** using `httpx` + `pytest-anyio` (not sync `TestClient`)
- **Pydantic BaseSettings** with `@lru_cache` for configuration
- **Custom exception classes** per domain (not generic `HTTPException` everywhere)
- **Alembic migrations** with descriptive names
- **Ruff** for linting (modern replacement for black + isort + flake8)
- **Pre-commit hooks** configured and documented

## Next.js examples need TypeScript and App Router

For Next.js demos in late 2025, **App Router with TypeScript** is non-negotiable for credibility. Server Components are the default; Page Router examples signal outdated patterns.

```
nextjs-production-example/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── api/
│   │       └── [...route]/route.ts
│   ├── components/
│   │   └── ui/
│   ├── lib/
│   │   ├── db.ts
│   │   └── auth.ts
│   └── types/
├── tests/
│   └── e2e/
├── .github/workflows/ci.yml
└── next.config.ts              # Note: .ts not .js
```

**Include these for production credibility**: Error boundaries, loading states, proper metadata/SEO, environment variable validation, and either Playwright or Cypress for E2E tests.

## Stack prioritization: FastAPI first, then Next.js

**Start with FastAPI/Python** for three reasons: (1) Python developers are the primary audience for AI coding tools, (2) FastAPI's type hints and auto-documentation make generated code quality immediately visible, and (3) CLI tools often target backend developers first.

Recommended launch sequence:

1. **FastAPI production example** with authentication, testing, CI/CD
2. **Next.js fullstack example** with tRPC or Server Actions
3. **CLI tool integration example** (showing your tool used with another popular CLI)

**Avoid mixing stacks in single examples**. Supabase's pattern of showing the same feature across multiple frameworks (`reset-flow/nextjs`, `reset-flow/react`, `reset-flow/vue`) in a `feature/framework` folder structure works well for demonstrating versatility without confusion.

## Signals that distinguish production code from AI slop

Skeptical CTOs look for **patterns that AI typically gets wrong**:

| Quality Signal | Why It Matters | How to Demonstrate |
|----------------|----------------|-------------------|
| Error handling edge cases | AI often produces happy-path code | Include tests for invalid inputs, network failures, race conditions |
| Consistent code style | AI output varies by prompt | Ruff/ESLint config with zero warnings |
| Meaningful test coverage | AI tests often test the obvious | Include integration tests, not just unit tests |
| Security considerations | AI misses auth edge cases | Rate limiting, input validation, proper secrets handling |
| Observability | Often omitted by AI | Structured logging, health checks, metrics endpoints |
| Documentation that explains "why" | AI writes "what" not "why" | Inline comments explaining architectural decisions |

**Aider's approach** of tracking "lazy comments" (where AI elides code with `// ...`) and malformed responses provides a model for transparency. Your demos should include a "quality scorecard" showing test coverage, type coverage, linting status, and any manual modifications required.

## Conclusion: Build real applications, not tutorials

The through-line from all successful developer tool examples is **authenticity**. Prisma links to real production apps (Cal.com, Dub.co, Umami). tRPC provides live deployed demos. Aider publishes reproducible benchmarks anyone can run.

For your examples repo, prioritize:

1. **Dedicated mono-repo** with Prisma-style table index in README
2. **Branch-based before/after** with `starter` and `main` branches
3. **FastAPI first** with production patterns (async tests, Pydantic settings, proper project structure)
4. **Document the AI process** transparently—prompts used, what was modified, what passed linting
5. **Include CI/CD in every example**—a passing GitHub Actions badge is worth more than testimonials

The examples that win over skeptical CTOs aren't the ones with the most features—they're the ones that look like code their own team would write.