# Next.js Full-Stack Template

## Overview

Production-ready Next.js 15 template with App Router, React Server Components, Server Actions, and Prisma ORM.

**Template**: `nextjs-fullstack`
**Complexity**: 7/10
**Confidence**: 92/100

## Technology Stack

- **Next.js**: 15.1.2 (App Router)
- **React**: 18.2.0 (Server + Client Components)
- **TypeScript**: 5.x (strict mode)
- **Prisma**: 6.19.0
- **NextAuth**: 4.24.11
- **Tailwind CSS**: 4.x
- **Vitest**: 4.0.8 (unit/integration)
- **Playwright**: 1.56.1 (E2E)

## Architecture

### App Router with React Server Components

```
┌─────────────────────────────────────────┐
│  Presentation (Server/Client Components)│
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│  Application (Server Actions, API)      │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│  Data Access (Prisma ORM)               │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│  Database (SQLite/PostgreSQL)           │
└─────────────────────────────────────────┘
```

## Project Structure

```
src/
├── app/                      # App Router
│   ├── (dashboard)/users/   # Server Components
│   ├── actions/users.ts     # Server Actions
│   ├── api/users/route.ts   # API handlers
│   └── layout.tsx
├── components/               # Client Components
├── lib/                      # Utilities (db, auth)
└── test/                     # Tests
```

## Key Patterns

1. **React Server Components** - Server-side rendering with zero client JS
2. **Server Actions** - Type-safe mutations from client components
3. **API Route Handlers** - RESTful endpoints for external clients
4. **Database Singleton** - Single Prisma instance during development
5. **Progressive Enhancement** - Forms work without JavaScript

## Rules Structure

This template uses Claude Code's modular rules system. Rules are automatically loaded based on file paths:

```
.claude/
├── CLAUDE.md                    # This file (core guide)
└── rules/
    ├── code-style.md            # **/*.{ts,tsx}
    ├── testing.md               # **/*.test.*, **/e2e/**
    ├── server/
    │   ├── components.md        # **/app/**/*.tsx
    │   ├── actions.md           # **/actions/**/*.ts
    │   └── streaming.md         # **/loading.tsx, **/error.tsx
    ├── api/
    │   └── routes.md            # **/api/**/route.ts
    ├── database/
    │   └── prisma.md            # **/prisma/**, **/lib/db.ts
    ├── auth/
    │   └── nextauth.md          # **/auth/**, **/api/auth/**
    └── agents/
        ├── server-components.md # Server Component patterns
        ├── server-actions.md    # Server Action patterns
        ├── fullstack.md         # Full-stack patterns (always loaded)
        └── react-state.md       # React hooks and state
```

## Getting Started

```bash
# 1. Initialize
guardkit init nextjs-fullstack --output my-app
cd my-app

# 2. Install dependencies
npm install

# 3. Configure environment
echo 'DATABASE_URL="file:./dev.db"' > .env
echo 'NEXTAUTH_SECRET="your-secret"' >> .env
echo 'NEXTAUTH_URL="http://localhost:3000"' >> .env

# 4. Setup database
npx prisma generate
npx prisma migrate dev --name init

# 5. Run development server
npm run dev

# 6. Run tests
npm test              # Unit tests
npm run test:e2e      # E2E tests
```

## AI Agents

This template includes specialized agents:

1. **nextjs-server-components-specialist** - Server Components and data fetching
2. **nextjs-server-actions-specialist** - Server Actions and mutations
3. **nextjs-fullstack-specialist** - Complete full-stack workflows
4. **react-state-specialist** - React hooks and client state

## Testing Strategy: Trophy Model

This template follows **Kent C. Dodds' Trophy testing model** for client applications:

```
    🏆  E2E (~10%)
  ___________
/             \
| Feature/    |
| Integration |  ← Primary focus (~50%)
| Tests       |
\____________/
Unit Tests (~30%)
__________
Static (~10%)
```

### Testing Distribution

- **50% Feature/Integration Tests**: Test user scenarios across Server/Client Components
- **30% Unit Tests**: Complex business logic only (calculations, validators, utilities)
- **10% E2E Tests**: Critical user journeys (auth flow, core workflows)
- **10% Static Analysis**: TypeScript strict mode, ESLint

### Testing Principles

**✅ Test behavior, not implementation**
- Test Server Components with `render()` from Testing Library
- Test Server Actions with direct function calls
- Verify user-facing behavior and outcomes

**✅ What to mock:**
- External APIs (at HTTP level via MSW or fetch mocks)
- Third-party services (payment, email, analytics)
- Slow operations (file uploads, image processing)

**❌ What NOT to mock:**
- Prisma database calls (use test database)
- Server Actions (test directly)
- Next.js routing and rendering
- React Server Components flow

**✅ When seam tests ARE needed:**
- Third-party integrations (Stripe, SendGrid, external APIs)
- Microservice boundaries in distributed systems
- Platform tool development (NOT client apps)

### Testing Requirements Checklist

- [ ] Feature/integration tests for every user story (component → action → DB)
- [ ] Unit tests for complex business logic only (calculations, validators, parsers)
- [ ] Contract tests for third-party API integrations
- [ ] E2E tests for critical user journeys only (login, checkout, core workflows)
- [ ] TypeScript strict mode enabled
- [ ] ESLint with Next.js recommended rules

**See**: [ADR-SP-009](../../../docs/architecture/decisions/ADR-SP-009-honeycomb-testing-model.md) for architectural justification.

## Quality Standards

- **TypeScript**: Strict mode enabled
- **Test Coverage**: ≥80% lines, ≥75% branches
- **Performance**: FCP <1.5s, TTI <3.5s
- **Architecture**: SOLID 75/100, DRY 80/100, YAGNI 90/100

## Common Tasks

### Add New Entity
1. Update Prisma schema → Generate migration
2. Create Server Component (page.tsx) → Server Actions (actions/*.ts) → Client Components

### Deploy
**Vercel**: Push to Git, connect, configure env, deploy
**Docker**: Build with `node:18-alpine`, run `npm run build`

## Troubleshooting

- **Prisma errors**: Run `npx prisma generate`
- **TypeScript errors**: Run `npm run type-check`
- **Auth errors**: Verify `NEXTAUTH_SECRET` and `NEXTAUTH_URL`
- **Database errors**: Check `DATABASE_URL` in `.env`

## References

- [Next.js Docs](https://nextjs.org/docs)
- [React Server Components](https://react.dev/reference/rsc/server-components)
- [Prisma Docs](https://www.prisma.io/docs)
- [NextAuth Docs](https://next-auth.js.org)

---

**Version**: 1.0.0
**Updated**: 2025-12-11
**Quality**: Production Ready
