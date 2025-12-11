# Next.js Full-Stack Template

Production-ready Next.js 15 template with App Router, React Server Components, Server Actions, Prisma ORM, and comprehensive testing.

## Features

- ✅ **Next.js 15** - App Router with React Server Components
- ✅ **TypeScript** - Strict mode for type safety
- ✅ **Prisma ORM** - Type-safe database with migrations
- ✅ **NextAuth** - Authentication (GitHub, credentials)
- ✅ **Server Actions** - Type-safe mutations
- ✅ **Tailwind CSS** - Utility-first styling
- ✅ **Vitest + Playwright** - Comprehensive testing
- ✅ **Progressive Enhancement** - Works without JavaScript

## Quick Start

```bash
# Initialize from template
guardkit init nextjs-fullstack

# Install dependencies
npm install

# Set up environment
echo 'DATABASE_URL="file:./dev.db"' > .env

# Initialize database
npx prisma generate
npx prisma migrate dev --name init

# Start development
npm run dev
```

## Technology Stack

| Category | Technology | Version |
|----------|-----------|---------|
| Framework | Next.js | 15.1.2 |
| UI Library | React | 18.2.0 |
| Language | TypeScript | 5.x |
| Database | Prisma | 6.19.0 |
| Auth | NextAuth | 4.24.11 |
| Styling | Tailwind CSS | 4.x |
| Testing | Vitest | 4.0.8 |
| E2E | Playwright | 1.56.1 |

## Project Structure

```
src/
├── app/                # Next.js App Router
│   ├── (dashboard)/    # Authenticated pages
│   ├── actions/        # Server Actions
│   ├── api/            # API routes
│   └── layout.tsx      # Root layout
├── components/         # React components
├── lib/                # Utilities
│   ├── db.ts          # Prisma client
│   └── auth.ts        # NextAuth config
├── types/              # TypeScript types
└── test/               # Test setup
prisma/
├── schema.prisma      # Database schema
└── migrations/        # DB migrations
e2e/                   # Playwright tests
```

## Key Patterns

### Server Component (Data Fetching)
```typescript
// app/users/page.tsx
export default async function UsersPage() {
  const users = await db.user.findMany()
  return <UserList users={users} />
}
```

### Client Component (Interactivity)
```typescript
// components/UserList.tsx
'use client'

export function UserList({ users }) {
  const [selected, setSelected] = useState(null)
  return <div onClick={() => setSelected(...)}>{...}</div>
}
```

### Server Action (Mutation)
```typescript
// app/actions/users.ts
'use server'

export async function createUser(formData: FormData) {
  const user = await db.user.create({...})
  revalidatePath('/users')
  return { success: true, data: user }
}
```

## Development Commands

```bash
npm run dev          # Start dev server
npm run build        # Build for production
npm start            # Start production server
npm test             # Run unit tests
npm run test:e2e     # Run E2E tests
npm run type-check   # TypeScript validation
npm run lint         # Run ESLint
```

## Database Management

```bash
# Generate Prisma client
npx prisma generate

# Create migration
npx prisma migrate dev --name <migration-name>

# Apply migrations
npx prisma migrate deploy

# Open Prisma Studio
npx prisma studio
```

## Environment Variables

Create a `.env` file with:

```env
DATABASE_URL="file:./dev.db"
NEXTAUTH_SECRET="your-secret-key"
NEXTAUTH_URL="http://localhost:3000"
GITHUB_ID="your-github-oauth-id"
GITHUB_SECRET="your-github-oauth-secret"
```

## Testing

### Unit Tests (Vitest)
```bash
npm test                # Run tests
npm run test:ui         # Run with UI
npm run test:coverage   # With coverage
```

### E2E Tests (Playwright)
```bash
npm run test:e2e        # Run E2E tests
npm run test:e2e:ui     # Run with UI
```

## Deployment

### Vercel (Recommended)
1. Push to Git (GitHub, GitLab, Bitbucket)
2. Import project in Vercel dashboard
3. Configure environment variables
4. Deploy automatically on every push

### Docker
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY . .
RUN npm install
RUN npx prisma generate
RUN npm run build
CMD ["npm", "start"]
```

### CI/CD Pipeline

This template includes a GitHub Actions workflow template (`workflows-ci.yml.template`) that runs:

1. **Linting** - ESLint code quality checks
2. **Type Checking** - TypeScript validation
3. **Unit Tests** - Vitest with coverage reporting
4. **E2E Tests** - Playwright browser tests
5. **Build** - Production build verification

To use: Copy `templates/workflows-ci.yml.template` to `.github/workflows/ci.yml` in your project.

The pipeline runs on every push and pull request to ensure code quality.

## Architecture

```
┌─────────────────┐
│   UI Layer      │  Server + Client Components
├─────────────────┤
│ Business Logic  │  Server Actions + API Routes
├─────────────────┤
│  Data Access    │  Prisma ORM
├─────────────────┤
│   Database      │  SQLite/PostgreSQL
└─────────────────┘
```

## Quality Scores

- **SOLID Compliance**: 75/100
- **DRY Compliance**: 80/100
- **YAGNI Compliance**: 90/100
- **Overall Confidence**: 92/100

## Custom AI Agents

This template includes 4 specialized agents:

1. **nextjs-fullstack-specialist** - Complete full-stack development
2. **nextjs-server-components-specialist** - Server Components patterns
3. **nextjs-server-actions-specialist** - Server Actions and mutations
4. **react-state-specialist** - React hooks and state management

## Rules Structure

This template uses Claude Code's modular rules structure for optimized context loading.

### Directory Layout

```
.claude/
├── CLAUDE.md                    # Core documentation (~5KB)
└── rules/
    ├── code-style.md            # Code style guidelines
    ├── testing.md               # Testing conventions
    ├── patterns/                # Pattern-specific rules
    │   └── {pattern}.md
    └── agents/                  # Agent guidance
        └── {agent}.md
```

### Path-Specific Rules

Rules files use `paths:` frontmatter for conditional loading:

| Rule File | Loads When Editing |
|-----------|-------------------|
| `rules/code-style.md` | Any `.tsx`, `.ts` file |
| `rules/testing.md` | Test files |
| `rules/server/components.md` | `**/app/**/*.tsx` |
| `rules/server/actions.md` | `**/actions/*.ts` |
| `rules/database/prisma.md` | `**/prisma/**` |
| `rules/agents/server-components.md` | App Router files |

### Benefits

- Rules only load when editing relevant files
- Reduced context window usage (60-70% reduction)
- Organized by concern (patterns, agents, etc.)

## Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [Prisma Documentation](https://www.prisma.io/docs)
- [NextAuth Documentation](https://next-auth.js.org)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)

## License

This template is part of the GuardKit project.

---

**Template Version**: 1.0.0
**Created**: 2025-11-09
**Complexity**: 7/10 (High)
**Status**: Production Ready
