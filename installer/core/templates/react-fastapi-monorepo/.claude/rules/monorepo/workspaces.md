---
paths: pnpm-workspace.yaml, package.json
---

# pnpm Workspaces

## Workspace Configuration

pnpm manages the monorepo structure and dependencies:

```yaml
# pnpm-workspace.yaml
packages:
  - 'apps/*'
  - 'packages/*'
```

## Root Package Configuration

```json
{
  "name": "react-fastapi-monorepo",
  "private": true,
  "workspaces": [
    "apps/*",
    "packages/*"
  ],
  "scripts": {
    "dev": "turbo run dev",
    "build": "turbo run build",
    "test": "turbo run test",
    "generate-types": "turbo run generate-types",
    "docker:up": "docker-compose up -d",
    "docker:down": "docker-compose down"
  },
  "devDependencies": {
    "turbo": "^2.0.0"
  }
}
```

## Workspace Structure

```
monorepo-root/
├── apps/
│   ├── frontend/          # React application
│   └── backend/           # FastAPI application
├── packages/
│   └── shared-types/      # Shared TypeScript types
├── package.json           # Root workspace config
├── pnpm-workspace.yaml    # Workspace packages
└── turbo.json            # Turborepo config
```

## Dependency Management

### Workspace Dependencies
```json
{
  "name": "@monorepo/frontend",
  "dependencies": {
    "shared-types": "workspace:*"
  }
}
```

### Installing Dependencies
```bash
# Install for all workspaces
pnpm install

# Install for specific workspace
pnpm --filter frontend add react-hook-form

# Install dev dependency at root
pnpm add -Dw prettier
```

## Workspace Scripts

### Run in All Workspaces
```bash
pnpm -r dev     # Run dev in all workspaces
pnpm -r build   # Build all workspaces
pnpm -r test    # Test all workspaces
```

### Run in Specific Workspace
```bash
pnpm --filter frontend dev
pnpm --filter backend test
pnpm --filter shared-types build
```

## Shared Dependencies

### Common Development Tools (Root)
```json
{
  "devDependencies": {
    "turbo": "^2.0.0",
    "typescript": "^5.4.0",
    "prettier": "^3.0.0",
    "eslint": "^8.0.0"
  }
}
```

### App-Specific Dependencies
```json
{
  "name": "@monorepo/frontend",
  "dependencies": {
    "react": "^18.3.0",
    "shared-types": "workspace:*"
  }
}
```

## Best Practices

### 1. Use Workspace Protocol
```json
{
  "dependencies": {
    "shared-types": "workspace:*"  // ✅ Always in sync
  }
}
```

### 2. Install at Correct Level
- **Root**: Shared dev tools (turbo, prettier, eslint)
- **Workspace**: App-specific dependencies (react, fastapi)

### 3. Use Filters
```bash
# Run command in specific workspace
pnpm --filter frontend dev

# Run in multiple workspaces
pnpm --filter frontend --filter backend test
```

### 4. Leverage Turborepo
```bash
# Use turbo for orchestration
pnpm dev      # → turbo run dev
pnpm build    # → turbo run build
```

## Package Naming

### Scoped Names
```json
{
  "name": "@monorepo/frontend",
  "name": "@monorepo/backend",
  "name": "shared-types"
}
```

## Troubleshooting

### Issue: shared-types not found
**Check**: Workspace dependency installed
```bash
pnpm install
```

### Issue: Wrong package version
**Check**: Using `workspace:*` protocol
```json
{
  "dependencies": {
    "shared-types": "workspace:*"
  }
}
```

### Issue: Dependency conflicts
**Solution**: Use pnpm overrides
```json
{
  "pnpm": {
    "overrides": {
      "react": "^18.3.0"
    }
  }
}
```

### Issue: Changes not reflecting
**Solution**: Rebuild workspace
```bash
pnpm --filter shared-types build
```
