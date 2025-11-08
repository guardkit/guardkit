# TASK-059: Create Next.js Full-Stack Reference Template

**Created**: 2025-01-08
**Priority**: High
**Type**: Feature
**Parent**: Template Strategy Overhaul
**Status**: Backlog
**Complexity**: 8/10 (High)
**Estimated Effort**: 7-10 days
**Dependencies**: TASK-043 (Extended Validation), TASK-044 (Template Validate), TASK-045 (AI-Assisted Validation), TASK-056 (Audit Complete)

---

## Problem Statement

Create a **reference implementation template** for Next.js full-stack development combining modern App Router patterns with production best practices. This template must demonstrate full-stack React capabilities, achieve 9+/10 quality score, and serve as a learning resource.

**Goal**: Create high-quality Next.js full-stack template using Next.js App Router + production patterns, validate to 9+/10 standard.

---

## Context

**Related Documents**:
- [Template Strategy Decision](../../docs/research/template-strategy-decision.md)
- [Next.js 2025 Best Practices Research](../../docs/research/template-strategy-decision.md)
- TASK-044: Template validation command
- TASK-056: Template audit findings

**Source Pattern**:
- **Base**: Next.js App Router (official)
- **Enhancements**: Production patterns from 2025 best practices research
- **Stack**: Next.js 14+, TypeScript, Tailwind, Server Actions, Prisma/Drizzle, Auth.js

**Why Next.js Full-Stack**:
- ✅ 42.7% usage among full-stack developers (2025 data)
- ✅ React Server Components (RSC) - significant 2025 growth
- ✅ Hybrid rendering strategies (SSG, SSR, CSR, ISR)
- ✅ API routes + Server Actions
- ✅ Adopted by Netflix, TikTok, major enterprises
- ✅ Best SEO/performance for content-rich applications

---

## Objectives

### Primary Objective
Create Next.js full-stack reference template with App Router + production patterns that achieves 9+/10 quality score.

### Success Criteria
- [x] Next.js project created with App Router
- [x] Production patterns integrated (auth, database, testing, deployment)
- [x] Template created using `/template-create` command
- [x] Template passes `/template-validate` with 9+/10 score
- [x] All 16 validation sections score 8+/10
- [x] Zero critical issues
- [x] README documents full-stack architecture
- [x] Template installed in `installer/global/templates/nextjs-fullstack/`
- [x] Documentation updated to reference new template

---

## Implementation Scope

**IMPORTANT: Claude Code Tool Usage**
This task requires you to **execute commands using the SlashCommand tool**, not just describe them. You will create a production-ready Next.js project, then iteratively create, validate, refine, and re-validate the template until it achieves 9+/10 quality.

### Step 1: Create Production-Ready Next.js Project

Use **Bash tool** to create a Next.js project with production patterns:

```bash
# Create Next.js project with all modern features
cd /tmp
npx create-next-app@latest nextjs-reference \
  --typescript \
  --tailwind \
  --app \
  --src-dir \
  --import-alias "@/*"

cd nextjs-reference
```

### Step 2: Add Production Patterns

Use **Bash tool** and **Write tool** to add production-ready patterns:

**Authentication (Auth.js)**:
```bash
npm install next-auth@beta
```

Use **Write tool** to create:
- `app/api/auth/[...nextauth]/route.ts` - Auth configuration
- `lib/auth.ts` - Auth utilities
- `middleware.ts` - Route protection

**Database (Prisma)**:
```bash
npm install prisma @prisma/client
npx prisma init
```

Use **Write tool** to create:
- `prisma/schema.prisma` - Example schema with User model
- `lib/db.ts` - Database client singleton
- `app/actions/users.ts` - Server Actions for CRUD

**Testing Setup**:
```bash
npm install -D vitest @vitejs/plugin-react @testing-library/react @testing-library/jest-dom
npm install -D @playwright/test
npx playwright install
```

Use **Write tool** to create:
- `vitest.config.ts` - Vitest configuration
- `playwright.config.ts` - Playwright configuration
- Example test files for components, Server Actions, API routes

**Server Components & Server Actions**:

Use **Write tool** to create examples of:
- Server Component pages (`app/(dashboard)/users/page.tsx`)
- Client Component with interactivity (`components/UserForm.tsx`)
- Server Actions (`app/actions/users.ts`)
- API Routes (`app/api/users/route.ts`)
- Error boundaries (`app/error.tsx`, `app/global-error.tsx`)
- Loading states (`app/(dashboard)/loading.tsx`)

**Verify the project builds and runs**:
```bash
npm run build  # Must succeed
npm run dev    # Must start
```

### Step 3: Create Template Using `/template-create` Command

**Execute using SlashCommand tool**:

```
Use SlashCommand tool to invoke: /template-create --validate
```

The command will:
1. Run interactive Q&A (answer as specified below)
2. Analyze the nextjs-reference codebase
3. Generate manifest.json, settings.json, CLAUDE.md, templates/, agents/
4. Run extended validation (TASK-043)
5. Generate validation-report.md

**Q&A Answers**:
- **Template name**: nextjs-fullstack
- **Template type**: Full-stack
- **Primary language**: TypeScript
- **Frameworks**: Next.js (App Router), React, Tailwind
- **Architecture patterns**: Server Components, Server Actions, API Routes
- **Database**: Prisma
- **Authentication**: Auth.js
- **Testing**: Vitest (unit/integration), Playwright (e2e)
- **Generate custom agents**: Yes

**Expected Output**: Template created at `./templates/nextjs-fullstack/` with initial validation score of 7-8/10

### Step 4: Review Initial Validation Report

Use **Read tool** to review the validation report:

```
Read: ./templates/nextjs-fullstack/validation-report.md
```

Identify issues in these categories:
- Placeholder consistency (target: 9+/10)
- Pattern fidelity (target: 9+/10)
- Documentation completeness (target: 9+/10)
- Agent validation (target: 9+/10)
- Manifest accuracy (target: 9+/10)

### Step 5: Comprehensive Audit with AI Assistance

**Execute using SlashCommand tool**:

```
Use SlashCommand tool to invoke: /template-validate ./templates/nextjs-fullstack --sections 1-16
```

This runs the 16-section audit framework with AI assistance for sections 8, 11, 12, 13.

**Expected Output**:
- Section-by-section scores
- Detailed findings report
- AI-generated strengths/weaknesses
- Critical issues (if any)
- Specific recommendations for improvement

### Step 6: Iterative Improvement Loop

Based on validation findings, use **Edit tool** or **Write tool** to improve the template:

**Common Improvements**:

1. **Enhance CLAUDE.md** (Use Edit tool):
   - Add Next.js App Router code examples
   - Document Server Components vs Client Components
   - Explain Server Actions patterns
   - Show hybrid rendering strategies (SSG, SSR, ISR)
   - Document authentication flow
   - Document all agents with examples

2. **Improve Templates** (Use Edit/Write tools):
   - Add Server Component page templates
   - Add Client Component templates
   - Add Server Action templates (Create, Read, Update, Delete, List)
   - Add API route templates
   - Add layout templates
   - Add loading/error templates
   - Fix placeholder inconsistencies

3. **Enhance Agents** (Use Edit/Write tools):
   - Create nextjs-fullstack-specialist agent
   - Create nextjs-server-components-specialist agent
   - Create nextjs-testing-specialist agent
   - Complete agent prompts with examples
   - Ensure agents reference CLAUDE.md correctly

4. **Complete Manifest** (Use Edit tool):
   - Fill all metadata fields
   - Document all placeholders with patterns
   - Verify technology stack accuracy
   - Add quality scores from analysis

### Step 7: Re-validate After Improvements

**Execute using SlashCommand tool**:

```
Use SlashCommand tool to invoke: /template-validate ./templates/nextjs-fullstack --sections 10,11,16
```

(Re-run specific sections to verify improvements)

**Repeat Steps 6-7 until**:
- Overall score ≥9.0/10
- All 16 sections ≥8.0/10
- Zero critical issues
- Recommendation: APPROVE

### Step 8: Move Template to Installer Location

Use **Bash tool**:

```bash
# Move to final location
mv ./templates/nextjs-fullstack installer/global/templates/

# Verify structure
ls -la installer/global/templates/nextjs-fullstack/
```

### Step 9: Final Validation at Installer Location

**Execute using SlashCommand tool**:

```
Use SlashCommand tool to invoke: /template-validate installer/global/templates/nextjs-fullstack --sections 1-16
```

**Acceptance Criteria**:
- Overall Score: ≥9.0/10
- Grade: A or A+
- All sections: ≥8.0/10
- Critical issues: 0
- Recommendation: APPROVE

### Step 10: Installation and Integration Testing

Use **Bash tool** to test the template:

```bash
# Install template globally
./installer/scripts/install.sh

# Test template initialization in clean directory
cd /tmp/test-nextjs-app
taskwright init nextjs-fullstack

# Verify generated project builds and tests pass
cd /tmp/test-nextjs-app
npm install
npm run build       # Must succeed
npm test            # Must pass
npm run test:e2e    # Must pass
npm run type-check  # No TypeScript errors
npm run lint        # No linting errors
npm run dev         # Must start successfully
```

If any tests fail, return to Step 6 and fix issues in the template.

---

## Template Structure (Expected)

```
installer/global/templates/nextjs-fullstack/
├── manifest.json                    # Template metadata
├── settings.json                    # Naming conventions, patterns
├── CLAUDE.md                        # AI guidance for Next.js
├── README.md                        # Human-readable documentation
├── templates/                       # Code generation templates
│   ├── app/
│   │   ├── page-server.tsx.template         # Server Component page
│   │   ├── page-client.tsx.template         # Client Component page
│   │   ├── layout.tsx.template              # Layout
│   │   ├── loading.tsx.template             # Loading state
│   │   ├── error.tsx.template               # Error boundary
│   │   └── not-found.tsx.template           # 404 page
│   ├── components/
│   │   ├── server-component.tsx.template
│   │   ├── client-component.tsx.template
│   │   └── component-test.test.tsx.template
│   ├── actions/
│   │   ├── server-action.ts.template
│   │   └── action-test.test.ts.template
│   ├── api/
│   │   ├── route-get.ts.template
│   │   ├── route-post.ts.template
│   │   └── route-test.test.ts.template
│   ├── lib/
│   │   ├── db-client.ts.template
│   │   ├── auth-config.ts.template
│   │   └── utils.ts.template
│   ├── prisma/
│   │   └── schema.prisma.template
│   └── testing/
│       ├── unit-test.test.tsx.template
│       ├── integration-test.test.tsx.template
│       └── e2e-test.spec.ts.template
└── agents/                          # Stack-specific AI agents
    ├── nextjs-fullstack-specialist.md
    ├── nextjs-server-components-specialist.md
    └── nextjs-testing-specialist.md
```

---

## Key Patterns to Capture

### 1. Server Component (Default)
```typescript
// app/dashboard/page.tsx
import { db } from '@/lib/db'

export default async function DashboardPage() {
  const users = await db.user.findMany()

  return (
    <div>
      <h1>Dashboard</h1>
      <UserList users={users} />
    </div>
  )
}
```

### 2. Client Component (Interactivity)
```typescript
// components/counter.tsx
'use client'

import { useState } from 'react'

export function Counter() {
  const [count, setCount] = useState(0)

  return (
    <button onClick={() => setCount(count + 1)}>
      Count: {count}
    </button>
  )
}
```

### 3. Server Action
```typescript
// app/actions/user.ts
'use server'

import { db } from '@/lib/db'
import { revalidatePath } from 'next/cache'

export async function createUser(formData: FormData) {
  const name = formData.get('name') as string

  await db.user.create({
    data: { name }
  })

  revalidatePath('/users')

  return { success: true }
}
```

### 4. API Route (App Router)
```typescript
// app/api/users/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'

export async function GET(request: NextRequest) {
  const users = await db.user.findMany()
  return NextResponse.json({ users })
}

export async function POST(request: NextRequest) {
  const body = await request.json()
  const user = await db.user.create({ data: body })
  return NextResponse.json({ user }, { status: 201 })
}
```

### 5. Hybrid Rendering
```typescript
// app/blog/[slug]/page.tsx

// Static Site Generation (SSG)
export async function generateStaticParams() {
  const posts = await db.post.findMany()
  return posts.map((post) => ({
    slug: post.slug,
  }))
}

// Server Side Rendering (SSR) with dynamic data
export default async function BlogPost({ params }: { params: { slug: string } }) {
  const post = await db.post.findUnique({
    where: { slug: params.slug }
  })

  return <article>{post.content}</article>
}

// Incremental Static Regeneration (ISR)
export const revalidate = 3600 // Revalidate every hour
```

---

## Acceptance Criteria

### Functional Requirements
- [ ] Next.js App Router project created with production patterns
- [ ] Template created using `/template-create`
- [ ] Template validates at 9+/10 score
- [ ] All 16 validation sections score 8+/10
- [ ] Zero critical issues
- [ ] Template generates working Next.js full-stack project
- [ ] Generated project builds successfully
- [ ] Generated project tests pass (unit, integration, e2e)

### Quality Requirements
- [ ] CLAUDE.md documents Next.js App Router patterns
- [ ] README comprehensive with architecture diagrams
- [ ] manifest.json complete and accurate
- [ ] settings.json defines naming conventions
- [ ] Agents created (nextjs-fullstack-specialist, etc.)
- [ ] Templates cover Server Components, Client Components, Server Actions, API Routes

### Documentation Requirements
- [ ] Server Components vs Client Components explained
- [ ] Server Actions patterns documented
- [ ] Hybrid rendering strategies shown
- [ ] Authentication flow illustrated
- [ ] Database patterns documented
- [ ] Testing strategy explained

---

## Testing Requirements

### Template Validation Tests
```bash
# Comprehensive validation
/template-validate installer/global/templates/nextjs-fullstack

# Expected results:
# Overall Score: ≥9.0/10
# Grade: A or A+
# All sections: ≥8.0/10
# Critical issues: 0
# Recommendation: APPROVE
```

### Generated Project Tests
```bash
# Initialize project from template
taskwright init nextjs-fullstack --output /tmp/test-nextjs-app

# Setup
cd /tmp/test-nextjs-app
npm install

# Build
npm run build
# Expected: Successful production build

# Run tests
npm test
# Expected: All unit/integration tests pass

# Run E2E tests
npm run test:e2e
# Expected: All E2E tests pass

# Type checking
npm run type-check
# Expected: No TypeScript errors

# Linting
npm run lint
# Expected: No linting errors

# Run dev server
npm run dev
# Expected: Server starts on http://localhost:3000
```

---

## Risk Mitigation

### Risk 1: Next.js App Router Complexity
**Mitigation**: Focus on core patterns first, comprehensive documentation, clear Server vs Client examples

### Risk 2: Validation Score Below 9/10
**Mitigation**: Iterative improvement, use `/template-validate` feedback, extensive testing

### Risk 3: Generated Project Build Failures
**Mitigation**: Test generation early and often, ensure dependency versions compatible

---

## Success Metrics

**Quantitative**:
- Template validation score: ≥9.0/10
- All validation sections: ≥8.0/10
- Critical issues: 0
- Generated project build success: 100%
- Generated project test pass: 100%

**Qualitative**:
- Template demonstrates Next.js 2025 best practices
- Server Components vs Client Components clear
- Documentation comprehensive
- Full-stack patterns production-ready
- Developers can learn modern Next.js

---

## Related Tasks

- **TASK-044**: Prerequisite - Template validation command
- **TASK-056**: Prerequisite - Template audit
- **TASK-057**: Create React reference template (can share React patterns)
- **TASK-058**: Create FastAPI reference template (parallel effort)
- **TASK-060**: Remove low-quality templates
- **TASK-061**: Update documentation

---

**Document Status**: Ready for Implementation
**Created**: 2025-01-08
**Parent Epic**: Template Strategy Overhaul
