---
id: TASK-CRS-009
title: Refactor react-fastapi-monorepo Template to Rules Structure
status: in_review
task_type: implementation
created: 2025-12-11T12:15:00Z
updated: 2025-12-11T14:30:00Z
completed: 2025-12-11T14:30:00Z
priority: medium
tags: [template-refactor, react-fastapi-monorepo, rules-structure]
complexity: 5
parent_feature: claude-rules-structure
wave: 4
implementation_mode: task-work
conductor_workspace: claude-rules-wave4-4
estimated_hours: 5-7
actual_hours: 2
dependencies:
  - TASK-CRS-002
  - TASK-CRS-003
---

# Task: Refactor react-fastapi-monorepo Template to Rules Structure

## Description

Refactor the `react-fastapi-monorepo` template (currently 19.4KB) to use the modular `.claude/rules/` structure.

## Target Structure

```
installer/core/templates/react-fastapi-monorepo/
├── .claude/
│   ├── CLAUDE.md                     (~5KB core)
│   └── rules/
│       ├── monorepo/
│       │   ├── turborepo.md          # paths: turbo.json, **/package.json
│       │   ├── docker.md             # paths: **/Dockerfile, docker-compose*
│       │   └── workspaces.md         # paths: pnpm-workspace.yaml, package.json
│       ├── frontend/
│       │   ├── react.md              # paths: apps/frontend/**/*.tsx
│       │   ├── types.md              # paths: packages/shared-types/**
│       │   └── query.md              # paths: apps/frontend/**/*query*, **/*api*
│       ├── backend/
│       │   ├── fastapi.md            # paths: apps/backend/**/*.py
│       │   ├── database.md           # paths: apps/backend/**/models/**, **/crud/**
│       │   └── schemas.md            # paths: apps/backend/**/schemas/**
│       └── agents/
│           ├── monorepo.md           # paths: turbo.json, docker-compose*, pnpm-*
│           ├── type-safety.md        # paths: packages/shared-types/**, **/openapi*
│           └── docker.md             # paths: **/Dockerfile, docker-compose*
├── agents/
└── templates/
```

## Key Rules Files

### rules/monorepo/turborepo.md

```markdown
---
paths: turbo.json, **/package.json
---

# Turborepo Task Orchestration

## Pipeline Configuration

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

## Key Features
- Dependency resolution with `dependsOn`
- Output caching for faster builds
- Parallel execution of independent tasks
- Filtering with `--filter`
```

### rules/frontend/types.md

```markdown
---
paths: packages/shared-types/**, **/generated/**
---

# Type-Safe API Client

## Type Generation Workflow

1. Backend generates OpenAPI spec at `/openapi.json`
2. Run `pnpm generate-types`
3. Types generated to `packages/shared-types/src/generated/`
4. Frontend imports fully-typed client

## Usage

```typescript
import { api, User } from 'shared-types'

export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const response = await api.get<User[]>('/users')
      return response.data  // Fully typed!
    },
  })
}
```

## Regenerate After Backend Changes

```bash
pnpm generate-types
```
```

### rules/agents/type-safety.md

```markdown
---
paths: packages/shared-types/**, **/openapi*, **/generated/**
---

# Type Safety Specialist

## Purpose

OpenAPI → TypeScript type generation for full-stack type safety.

## Technologies

@hey-api/openapi-ts, TypeScript, TanStack Query

## Boundaries

### ALWAYS
- Regenerate types after backend schema changes
- Use generated types in frontend API calls
- Keep shared-types package up to date
- Verify OpenAPI spec is valid before generating
- Include generated/ in .gitignore or commit (project preference)

### NEVER
- Manually define types that exist in generated/
- Skip type generation in CI/CD pipeline
- Import backend types directly (use shared-types)
- Ignore type errors from generated code
- Modify generated files directly

### ASK
- Type generation configuration changes
- Custom type extensions strategy
- Breaking API change handling
- Monorepo type sharing strategy
```

## Acceptance Criteria

- [x] Core CLAUDE.md reduced to ~5KB (achieved: 5015 bytes)
- [x] Monorepo patterns well-documented (turborepo.md, docker.md, workspaces.md)
- [x] Type generation workflow clear (types.md with full workflow)
- [x] Docker orchestration rules included (docker.md in monorepo and agents)
- [x] Frontend/backend separation clear (separate frontend/ and backend/ rule directories)
- [x] Template still works with `guardkit init` (structure preserved)

## Notes

- This is Wave 4 (parallel with other templates)
- Use `/task-work` for full quality gates
- Important for type-safe full-stack development
