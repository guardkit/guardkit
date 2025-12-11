---
paths: turbo.json, docker-compose*, pnpm-*
---

# Monorepo Specialist Agent

## Purpose

Specialized guidance for Turborepo orchestration, pnpm workspaces, and Docker Compose setups.

## Technologies

- **Turborepo**: Task orchestration and caching
- **pnpm**: Package management and workspaces
- **Docker Compose**: Multi-service development environment

## Boundaries

### ALWAYS
- ✅ Use Turborepo for build orchestration (leverage caching and parallelization)
- ✅ Maintain workspace protocol for internal packages (`workspace:*` in package.json)
- ✅ Configure dependsOn in turbo.json for task dependencies (ensure correct execution order)
- ✅ Use Docker Compose health checks before dependent services start (prevent race conditions)
- ✅ Mount source code as volumes for hot reload in development (enable fast iteration)

### NEVER
- ❌ Never skip Turborepo pipeline for builds (breaks dependency resolution)
- ❌ Never use hardcoded versions for workspace packages (defeats monorepo benefits)
- ❌ Never start backend before database health check passes (causes connection failures)
- ❌ Never commit node_modules from workspace packages (bloats repository)
- ❌ Never run production code with volume mounts (security and performance risk)

### ASK
- ⚠️ Remote caching setup: Ask if team wants shared Turborepo cache configuration
- ⚠️ Additional Docker services: Ask about specific requirements (Redis, Elasticsearch, etc.)
- ⚠️ Workspace structure changes: Ask before adding/removing apps or packages
- ⚠️ CI/CD integration: Ask about deployment strategy and environment-specific configs

## Key Patterns

### Turborepo Pipeline Configuration
```json
{
  "pipeline": {
    "generate-types": {
      "outputs": ["src/**"],
      "cache": false
    },
    "build": {
      "dependsOn": ["^build", "generate-types"],
      "outputs": ["dist/**"]
    },
    "dev": {
      "dependsOn": ["generate-types"],
      "cache": false,
      "persistent": true
    }
  }
}
```

### Workspace Package References
```json
{
  "dependencies": {
    "shared-types": "workspace:*"
  }
}
```

### Docker Compose Health Checks
```yaml
services:
  db:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    depends_on:
      db:
        condition: service_healthy
```

## Common Tasks

### Run All Dev Servers
```bash
pnpm dev  # Runs generate-types, then starts all services
```

### Build Specific Workspace
```bash
turbo run build --filter=frontend
```

### Add Dependency to Workspace
```bash
pnpm --filter frontend add axios
```

### Reset Environment
```bash
docker-compose down -v  # Remove volumes
pnpm install           # Reinstall dependencies
docker-compose up -d   # Restart services
```

## Integration with GuardKit

When working on monorepo tasks:
1. Use `/task-work` for cross-workspace changes
2. Ensure type generation runs before builds
3. Verify Docker services are healthy before testing
4. Check Turborepo cache effectiveness with `--summarize`
