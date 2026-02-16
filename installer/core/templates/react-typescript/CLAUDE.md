# React TypeScript Template - Feature-Based Architecture

## Project Context

This template provides a production-ready foundation for React applications using TypeScript, Vite, and feature-based architecture. Based on Bulletproof React (28.5k+ stars), it emphasizes scalability, type safety, and developer experience.

## Core Principles

1. **Feature-Based Organization**: Code organized by domain features, not technical layers
2. **Type Safety First**: Leverage TypeScript for compile-time guarantees
3. **Server State Management**: TanStack Query for efficient data fetching and caching
4. **Component Composition**: Build UIs from small, reusable components
5. **Testing at Every Level**: Unit, integration, and E2E tests co-located with code

## Architecture Overview

### Feature-Based Structure

Features are organized as independent modules containing all related code:

```
features/{feature-name}/
├── api/              # Data fetching and mutations
├── components/       # Feature-specific UI
├── hooks/            # Custom hooks (optional)
├── types/            # Feature types (optional)
└── __tests__/        # Tests
```

**See**: `.claude/rules/patterns/feature-based.md` for complete patterns and examples.

### Layers

1. **Features Layer** (`src/features/`): Domain-specific business logic and UI
2. **Components Layer** (`src/components/`): Shared, reusable UI components
3. **App Layer** (`src/app/`): Application routes and global layout
4. **Lib Layer** (`src/lib/`): Shared utilities and infrastructure

### Data Flow

```
User Interaction → Component → Custom Hook (useQuery/useMutation) → API Function → API Client → Backend
```

## Technology Stack

### Core
- **React 18.3**: UI library with concurrent features
- **TypeScript 5.4+**: Static typing and enhanced IDE support
- **Vite 5.2**: Fast build tool and dev server

### State Management
- **TanStack Query 5.32**: Server state management and caching
- **Zustand 4.5**: Client state management (when needed)

### Routing
- **React Router 7.0**: Declarative routing with data loaders

### Styling
- **Tailwind CSS 3.4**: Utility-first CSS framework
- **Radix UI**: Headless, accessible UI components
- **class-variance-authority**: Variant-based component styling
- **tailwind-merge**: Intelligent Tailwind class merging

### Forms & Validation
- **React Hook Form 7.51**: Performant form state management
- **Zod 3.23**: TypeScript-first schema validation

### Testing
- **Vitest 2.1**: Fast unit testing with Vite
- **Testing Library**: User-centric testing utilities
- **Playwright 1.43**: Reliable E2E testing
- **MSW 2.2**: API mocking for tests and development

### Developer Experience
- **ESLint**: Code linting and style enforcement
- **Prettier**: Opinionated code formatting
- **Husky**: Git hooks for quality checks

## Project Structure

```
src/
├── app/                    # Application setup and routing
│   ├── index.tsx          # App entry point
│   ├── provider.tsx       # Global providers
│   ├── router.tsx         # Route definitions
│   └── routes/            # Route components
├── features/              # Feature modules
│   ├── auth/             # Authentication feature
│   ├── discussions/      # Discussions feature
│   └── ...
├── components/           # Shared components
│   ├── ui/              # Design system components
│   └── layouts/         # Layout components
├── lib/                 # Shared libraries
│   ├── api-client.ts   # Axios instance
│   └── react-query.ts  # Query client config
├── utils/              # Utility functions
├── types/             # Global type definitions
├── config/           # Configuration
└── testing/         # Testing utilities
```

## Development Workflow

### Starting Development
```bash
npm install       # Install dependencies
npm run dev      # Start dev server
npm test         # Run tests in watch mode
npm run test-e2e # Run E2E tests
```

### Code Quality Checks
```bash
npm run lint           # Lint code
npm run check-types    # Type check
npx prettier --write . # Format code
```

### Building for Production
```bash
npm run build   # Build
npm run preview # Preview build
```

## Common Tasks

### Adding a New Feature
1. Create feature directory: `mkdir -p src/features/{feature-name}/{api,components,__tests__}`
2. Implement API layer with TanStack Query
3. Create components using shared UI components
4. Add tests
5. Add route in `app/router.tsx`

**See**: `.claude/rules/patterns/feature-based.md` for detailed guide

### Adding API Endpoints
1. Create API file in `features/{feature}/api/{action}-{entity}.ts`
2. Define query options factory pattern
3. Create custom hook wrapping useQuery/useMutation
4. Add MSW handler in `testing/mocks/handlers/`

**See**: `.claude/rules/patterns/query-patterns.md` for patterns

### Adding Forms
1. Define Zod schema co-located with API mutation
2. Use `<Form>` component with schema
3. Handle validation errors in UI
4. Connect to mutation hook

**See**: `.claude/rules/patterns/form-patterns.md` for patterns

## Specialized Agents

This template includes specialized agents for common patterns:

### Guidance Rules
- **react-query**: TanStack Query patterns (`.claude/rules/guidance/react-query.md`)
- **feature-arch**: Feature organization (`.claude/rules/guidance/feature-arch.md`)
- **form-validation**: Forms and validation (`.claude/rules/guidance/form-validation.md`)
- **react-state**: Client state management (`.claude/rules/guidance/react-state.md`)

These agents are automatically discovered based on file paths and provide context-specific guidance.

## Rules Structure

This template uses GuardKit's modular rules system:

### Code Guidelines
- **code-style.md**: Naming conventions, imports, type safety
- **testing.md**: Testing strategy, coverage requirements

### Patterns
- **patterns/feature-based.md**: Feature organization and structure
- **patterns/query-patterns.md**: TanStack Query patterns
- **patterns/form-patterns.md**: Form validation with Zod

### Agent-Specific Rules
- **agents/react-query.md**: Query specialist guidance
- **agents/feature-arch.md**: Architecture specialist guidance
- **agents/form-validation.md**: Form specialist guidance
- **agents/react-state.md**: State specialist guidance

Rules are automatically loaded based on file paths using the `paths:` frontmatter field.

## Environment Variables

```bash
# .env
VITE_API_URL=http://localhost:3000/api
VITE_APP_URL=http://localhost:5173
```

Access via:
```typescript
import { env } from '@/config/env';
const apiUrl = env.API_URL;
```

## Troubleshooting

### TypeScript Errors
- Run `npm run check-types` to see all type errors
- Check `tsconfig.json` for correct path mappings
- Ensure all dependencies have type definitions

### Query Not Updating
- Check query key is correct and includes all parameters
- Verify cache invalidation is called after mutations
- Use React Query DevTools to inspect cache

### Form Not Submitting
- Ensure form `id` matches submit button `form` attribute
- Check Zod schema is correct
- Verify mutation is properly connected

### MSW Not Mocking
- Ensure MSW is initialized in `mock-server.ts`
- Check handler matches request URL exactly
- Verify `env.API_URL` is correct in handlers

## Additional Resources

- [Bulletproof React](https://github.com/alan2207/bulletproof-react) - Original inspiration
- [TanStack Query Docs](https://tanstack.com/query/latest) - Query patterns
- [React Hook Form Docs](https://react-hook-form.com/) - Form management
- [Zod Docs](https://zod.dev/) - Schema validation
- [Radix UI Docs](https://www.radix-ui.com/) - UI components
- [Tailwind CSS Docs](https://tailwindcss.com/) - Styling
- [Playwright Docs](https://playwright.dev/) - E2E testing

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

- **50% Feature/Integration Tests**: Test user-meaningful scenarios across components
- **30% Unit Tests**: Complex business logic only (calculations, validations, state machines)
- **10% E2E Tests**: Critical user journeys (login, core workflows)
- **10% Static Analysis**: TypeScript strict mode, ESLint

### Testing Principles

**✅ Test behavior, not implementation**
- Focus on what users see and do
- Avoid testing internal component state
- Test from the user's perspective

**✅ What to mock:**
- External APIs (at HTTP level via MSW)
- Third-party services (Stripe, Auth0, etc.)

**❌ What NOT to mock:**
- Internal functions and utilities
- React components
- State management (TanStack Query, Zustand)

**✅ When seam tests ARE needed:**
- Third-party integrations (Stripe checkout, external APIs)
- Microservice boundaries in distributed systems
- Platform tool development (NOT client apps)

### Testing Requirements Checklist

- [ ] Feature/integration tests for every user story
- [ ] Unit tests for complex business logic only (calculations, validators, parsers)
- [ ] Contract tests for third-party API integrations
- [ ] E2E tests for critical user journeys only (not every feature)
- [ ] TypeScript strict mode enabled
- [ ] ESLint with recommended rules

**See**: [ADR-SP-009](../../docs/architecture/decisions/ADR-SP-009-honeycomb-testing-model.md) for architectural justification.

## Notes

- This template prioritizes scalability and maintainability
- Feature-based architecture scales better than layer-based
- Type safety prevents bugs at compile-time
- Co-located tests improve discoverability
- MSW provides consistent mocking across dev and testing
