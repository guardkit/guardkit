---
paths: turbo.json, **/package.json
---

# Turborepo Task Orchestration

## Pipeline Configuration

Turborepo manages monorepo tasks with dependency-aware execution:

```json
{
  "pipeline": {
    "generate-types": {
      "outputs": ["src/**"],
      "cache": false
    },
    "build": {
      "dependsOn": ["^build", "generate-types"],
      "outputs": ["dist/**", ".next/**", "build/**"]
    },
    "dev": {
      "dependsOn": ["generate-types"],
      "cache": false,
      "persistent": true
    },
    "test": {
      "dependsOn": ["build"],
      "outputs": ["coverage/**"]
    }
  }
}
```

## Key Features

### Dependency Resolution
- **`^build`**: Depends on build in upstream dependencies
- **`generate-types`**: Must run before dev/build
- **Automatic ordering**: Turborepo resolves execution order

### Output Caching
- **Cache outputs**: `dist/**`, `build/**`, `.next/**`
- **Skip on cache hit**: Faster rebuilds
- **Shared cache**: Remote caching for teams

### Parallel Execution
- **Independent tasks**: Run in parallel
- **CPU optimization**: Uses all available cores
- **Progress tracking**: Real-time status updates

### Filtering
```bash
# Run tasks for specific apps
turbo run build --filter=frontend
turbo run test --filter=backend

# Run tasks for all dependencies
turbo run build --filter=frontend...
```

## Common Commands

```bash
# Run all dev servers (frontend + backend)
pnpm dev

# Build everything
pnpm build

# Build specific app
turbo run build --filter=frontend

# Run tests across monorepo
pnpm test

# Clear Turborepo cache
turbo run build --force
```

## Pipeline Best Practices

### 1. Generate Types Before Dev/Build
```json
{
  "dev": {
    "dependsOn": ["generate-types"]
  },
  "build": {
    "dependsOn": ["^build", "generate-types"]
  }
}
```

### 2. Cache Expensive Operations
```json
{
  "build": {
    "outputs": ["dist/**"],
    "cache": true
  }
}
```

### 3. Disable Cache for Non-Deterministic Tasks
```json
{
  "generate-types": {
    "cache": false  // Fetches from live API
  },
  "dev": {
    "cache": false,
    "persistent": true
  }
}
```

## Troubleshooting

### Issue: Types not generated
**Solution**: Ensure `generate-types` runs before `dev`:
```json
{
  "dev": {
    "dependsOn": ["generate-types"]
  }
}
```

### Issue: Stale cache
**Solution**: Force rebuild:
```bash
turbo run build --force
```

### Issue: Slow builds
**Solution**: Check cache effectiveness:
```bash
turbo run build --summarize
```
