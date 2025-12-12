---
paths: ["**/*.{ts,tsx}"]
---

# Code Style Guidelines

## Naming Conventions

### Files
- **Components**: `kebab-case.tsx` (export: `PascalCase`)
  - Example: `discussions-list.tsx` → `export const DiscussionsList`
- **Hooks**: `use-hook-name.ts` or `useHookName.ts`
  - Example: `use-discussions.ts` → `export const useDiscussions`
- **API Files**: `{action}-{entity}.ts`
  - Example: `get-discussions.ts`, `create-discussion.ts`
- **Types**: `types.ts` or co-located with usage
- **Tests**: `{filename}.test.tsx` in `__tests__/` subdirectory

### Code
- **Components**: `PascalCase`
- **Hooks**: `camelCase` with `use` prefix
- **Functions**: `camelCase`
- **Constants**: `SCREAMING_SNAKE_CASE` or `camelCase`
- **Types/Interfaces**: `PascalCase`

### Features
- **Feature folders**: Singular, lowercase, kebab-case
  - Example: `discussion/`, `comment/`, `user/`
- **API endpoints**: Match feature name (singular or plural based on operation)
  - Example: `/discussions` (list), `/discussions/:id` (single)

## Path Aliases

Use path aliases for clean imports:

```typescript
// tsconfig.json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}

// Import usage
import { Button } from '@/components/ui/button';
import { useDiscussions } from '@/features/discussions/api/get-discussions';
import { formatDate } from '@/utils/format';
```

## Import Organization

Organize imports in the following order:
1. Built-in modules
2. External dependencies
3. Internal modules (using `@/` alias)

```typescript
// ✅ Good
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { formatDate } from '@/utils/format';

// ❌ Bad - mixed order
import { Button } from '@/components/ui/button';
import { useState } from 'react';
import { formatDate } from '@/utils/format';
import { useQuery } from '@tanstack/react-query';
```

## Type Safety

### Avoid `any`
- Never use `any` types
- Use `unknown` when type is truly unknown
- Use proper type guards to narrow `unknown` types

```typescript
// ✅ Good
function processData(data: unknown) {
  if (typeof data === 'string') {
    return data.toUpperCase();
  }
  throw new Error('Invalid data type');
}

// ❌ Bad
function processData(data: any) {
  return data.toUpperCase();
}
```

### Infer Types from Schemas
Use `z.infer` to derive TypeScript types from Zod schemas:

```typescript
// ✅ Good
export const createDiscussionInputSchema = z.object({
  title: z.string().min(1, 'Required'),
  body: z.string().min(1, 'Required'),
});

export type CreateDiscussionInput = z.infer<typeof createDiscussionInputSchema>;

// ❌ Bad - duplicate type definitions
export type CreateDiscussionInput = {
  title: string;
  body: string;
};
```

## Quality Standards

### Code Quality
- **Type Safety**: No `any` types (use `unknown` when necessary)
- **Linting**: Pass all ESLint rules (including TypeScript rules)
- **Formatting**: Prettier-formatted code
- **Naming**: Consistent naming conventions
- **Imports**: Organized imports (built-in → external → internal)
