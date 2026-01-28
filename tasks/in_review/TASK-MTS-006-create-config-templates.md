---
complexity: 4
conductor_workspace: mcp-ts-wave2-3
created: 2026-01-24 16:45:00+00:00
dependencies:
- TASK-MTS-001
feature_id: FEAT-MTS
id: TASK-MTS-006
implementation_mode: task-work
parallel_group: wave2
parent_review: TASK-REV-4371
priority: high
status: in_review
tags:
- template
- mcp
- typescript
- config
- docker
task_type: scaffolding
title: Create config templates (package.json, tsconfig, docker, claude-desktop)
updated: 2026-01-28 18:55:00+00:00
wave: 2
---

# Task: Create config templates

## Description

Create configuration file templates for MCP TypeScript projects including package.json, tsconfig.json, Claude Desktop config, Dockerfile, and docker-compose.yml.

## Reference

Use `.claude/reviews/TASK-REV-4371-review-report.md` Sections 8 for build/deployment patterns.
Use `docs/research/mcp-server-best-practices-2025.md` for configuration examples.

## Deliverables

### 1. config/package.json.template

```json
{
  "name": "{{ServerName}}",
  "version": "{{ServerVersion}}",
  "description": "{{Description}}",
  "type": "module",
  "main": "dist/index.js",
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "esbuild src/index.ts --bundle --platform=node --outfile=dist/index.js --external:@modelcontextprotocol/*",
    "start": "node dist/index.js",
    "test": "vitest",
    "test:coverage": "vitest --coverage",
    "test:protocol": "./tests/protocol/test-protocol.sh",
    "lint": "eslint src/",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0",
    "zod": "^3.25.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "esbuild": "^0.20.0",
    "eslint": "^9.0.0",
    "tsx": "^4.0.0",
    "typescript": "^5.4.0",
    "vitest": "^2.0.0",
    "@vitest/coverage-v8": "^2.0.0"
  },
  "engines": {
    "node": ">=20.0.0"
  }
}
```

### 2. config/tsconfig.json.template

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "tests"]
}
```

### 3. config/claude-desktop.json.template

```json
{
  "mcpServers": {
    "{{ServerName}}": {
      "command": "{{AbsoluteNodePath}}",
      "args": ["--import", "tsx", "{{AbsoluteProjectPath}}/src/index.ts"],
      "cwd": "{{AbsoluteProjectPath}}",
      "env": {
        "NODE_ENV": "development"
      }
    }
  }
}
```

**CRITICAL**: Document that paths MUST be absolute!

### 4. docker/Dockerfile.template

```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY tsconfig.json ./
COPY src/ ./src/
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Copy built artifacts
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package*.json ./

# Install production dependencies only
RUN npm ci --production

# Create non-root user
RUN adduser -D -u 1000 mcp
USER mcp

# Environment
ENV NODE_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=5s \
  CMD node -e "console.log('healthy')"

CMD ["node", "dist/index.js"]
```

### 5. docker/docker-compose.yml.template

```yaml
version: '3.8'

services:
  {{ServerName}}:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: {{ServerName}}
    stdin_open: true
    tty: true
    environment:
      - NODE_ENV=production
    restart: unless-stopped
```

## Acceptance Criteria

- [x] config/package.json.template created with all scripts and dependencies
- [x] config/tsconfig.json.template created with proper module settings
- [x] config/claude-desktop.json.template created with ABSOLUTE PATH warnings
- [x] docker/Dockerfile.template created with multi-stage build and non-root user
- [x] docker/docker-compose.yml.template created
- [x] All templates use proper placeholders
- [x] Documentation notes about absolute paths included

## Test Execution Log

### TDD Test Run - 2026-01-28 18:54

```
 ✓ tests/unit/mcp-typescript-config-templates.test.ts (54 tests) 8ms
   ✓ MCP TypeScript Config Templates - File Existence (5 tests)
   ✓ MCP TypeScript Config Templates - package.json.template (12 tests)
   ✓ MCP TypeScript Config Templates - tsconfig.json.template (9 tests)
   ✓ MCP TypeScript Config Templates - claude-desktop.json.template (9 tests)
   ✓ MCP TypeScript Config Templates - Dockerfile.template (11 tests)
   ✓ MCP TypeScript Config Templates - docker-compose.yml.template (7 tests)
   ✓ MCP TypeScript Config Templates - Placeholder Consistency (1 test)

 Test Files  1 passed (1)
      Tests  54 passed (54)
   Duration  138ms
```

## Implementation Summary

All 5 configuration templates created following MCP best practices:

1. **package.json.template**: ESM module with esbuild bundling, vitest testing, tsx development
2. **tsconfig.json.template**: ES2022 target, NodeNext modules, strict mode, path aliases
3. **claude-desktop.json.template**: MCP server config with absolute path placeholders
4. **Dockerfile.template**: Multi-stage build, non-root user, health checks
5. **docker-compose.yml.template**: stdio transport support, production environment

Files created in:
- `installer/core/templates/mcp-typescript/config/`
- `installer/core/templates/mcp-typescript/docker/`
