---
paths: **/*.{ts,tsx}
---

# Code Style & Conventions

## Naming Conventions

### Components
- **Format**: PascalCase
- **Extension**: `.tsx`
- **Examples**: `UserList`, `UserForm`, `DashboardLayout`
- **Location**: `src/components/`

### Pages
- **Format**: `page.tsx` (fixed name)
- **Examples**: `app/users/page.tsx`, `app/(dashboard)/settings/page.tsx`

### Server Actions
- **Format**: camelCase
- **Extension**: `.ts`
- **Examples**: `createUser`, `deletePost`, `updateProfile`
- **Location**: `src/app/actions/`

### API Routes
- **Format**: `route.ts` (fixed name)
- **Examples**: `app/api/users/route.ts`, `app/api/posts/[id]/route.ts`

### Library Files
- **Format**: camelCase
- **Extension**: `.ts`
- **Examples**: `db.ts`, `auth.ts`, `utils.ts`
- **Location**: `src/lib/`

### Test Files
- **Unit Tests**: `ComponentName.test.tsx` (adjacent to source)
- **E2E Tests**: `feature.spec.ts` (in `e2e/` directory)

## TypeScript Standards

- **Strict Mode**: Enabled for maximum type safety
- **Type Annotations**: Required for function parameters and return types
- **No Any**: Avoid `any` type, use `unknown` if needed
- **Interface vs Type**: Use `type` for unions/intersections, `interface` for objects

## Code Quality

- **Linting**: ESLint with Next.js recommended rules
- **Formatting**: Consistent code style (2 spaces, single quotes)
- **Comments**: Use JSDoc for public APIs, inline comments for complex logic
