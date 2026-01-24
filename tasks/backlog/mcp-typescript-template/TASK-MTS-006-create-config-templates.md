---
id: TASK-MTS-006
title: Create config templates (package.json, tsconfig, docker, claude-desktop)
status: backlog
task_type: scaffolding
created: 2026-01-24T16:45:00Z
updated: 2026-01-24T16:45:00Z
priority: high
tags: [template, mcp, typescript, config, docker]
complexity: 4
parent_review: TASK-REV-4371
feature_id: FEAT-MTS
wave: 2
parallel_group: wave2
implementation_mode: task-work
conductor_workspace: mcp-ts-wave2-3
dependencies:
  - TASK-MTS-001  # manifest.json for placeholders
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

- [ ] config/package.json.template created with all scripts and dependencies
- [ ] config/tsconfig.json.template created with proper module settings
- [ ] config/claude-desktop.json.template created with ABSOLUTE PATH warnings
- [ ] docker/Dockerfile.template created with multi-stage build and non-root user
- [ ] docker/docker-compose.yml.template created
- [ ] All templates use proper placeholders
- [ ] Documentation notes about absolute paths included

## Test Execution Log

[Automatically populated by /task-work]
