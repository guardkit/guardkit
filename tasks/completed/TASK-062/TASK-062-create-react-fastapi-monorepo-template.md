# TASK-062: Create React + FastAPI Monorepo Reference Template

**Created**: 2025-01-08
**Completed**: 2025-01-09
**Priority**: High
**Type**: Feature
**Parent**: Template Strategy Overhaul
**Status**: COMPLETED
**Complexity**: 6/10 (Medium) → 7/10 (High - Phase 2.7 evaluated)
**Estimated Effort**: 3-5 days (9.5 hours)
**Actual Effort**: ~8 hours
**Dependencies**: TASK-043 (Extended Validation), TASK-044 (Template Validate), TASK-045 (AI-Assisted Validation), TASK-056 (Audit Complete), TASK-057 (React completed), TASK-058 (FastAPI completed), TASK-068 (Template Location Refactor)
**Quality Score**: 9.2/10 (Grade: A)
**Success Criteria**: 11/11 met (100%)

**Implementation Plan**:
  - File Path: docs/state/TASK-062/implementation_plan.json
  - Markdown: docs/state/TASK-062/implementation_plan.md
  - Generated: 2025-01-09T20:15:00Z
  - Version: 1
  - Approved: false

**Complexity Evaluation**:
  - Score: 7/10 (High)
  - Level: high
  - File Path: docs/state/TASK-062/complexity_score.json
  - Calculated: 2025-01-09T20:15:00Z
  - Review Mode: FULL_REQUIRED
  - Forced Review Triggers: []
  - Factors:
    - File Complexity: 3.0/3.0 (38 files)
    - Pattern Familiarity: 1.5/2.0 (Mixed familiar/new)
    - Risk Level: 1.5/3.0 (4 medium, 1 low risk)
    - Dependency Complexity: 1.0/2.0 (3 new dependencies)

---

## Problem Statement

Create a **production-ready monorepo template** combining React frontend and FastAPI backend with type safety, shared tooling, and Docker orchestration. This template serves Python-first teams who need modern frontend with Python backend capabilities (ML, data science, existing Python infrastructure).

**Goal**: Combine react-typescript and fastapi-python into high-quality monorepo template achieving 9+/10 validation score.

---

## Context

**Related Documents**:
- [Template Strategy Decision](../../docs/research/template-strategy-decision.md)
- TASK-057: react-typescript template (frontend component)
- TASK-058: fastapi-python template (backend component)

**Source Repositories**:

**Primary Source - FastAPI Official**:
- **URL**: https://fastapi.tiangolo.com/project-generation/
- **GitHub**: https://github.com/tiangolo/full-stack-fastapi-template
- **Features**: Production-proven FastAPI + React structure, Docker Compose, PostgreSQL, authentication
- **Used by**: Thousands of production applications

**Monorepo Tooling - Turborepo Example**:
- **URL**: https://github.com/sinanbekar/monorepo-turborepo-python
- **Features**: Official Turborepo starter with FastAPI + React, pnpm workspaces
- **Use**: Turborepo configuration and monorepo structure

**Type Safety Reference**:
- **Guide**: https://abhayramesh.com/blog/type-safe-fullstack
- **Features**: OpenAPI → TypeScript type generation, @hey-api/openapi-ts

**Why This Combination**:
- ✅ Official FastAPI template (production-proven patterns)
- ✅ Turborepo monorepo management (modern tooling)
- ✅ Type safety across stack (OpenAPI → TypeScript)
- ✅ Docker orchestration (local dev + production)
- ✅ Combines react-typescript + fastapi-python templates

---

## Objectives

### Primary Objective
Create React + FastAPI monorepo reference template that achieves 9+/10 quality score and demonstrates type-safe full-stack development.

### Success Criteria
- [x] Monorepo structure created with Turborepo
- [x] Frontend integrated from react-typescript template
- [x] Backend integrated from fastapi-python template
- [x] Type safety working (OpenAPI → TypeScript)
- [x] Docker Compose orchestration for local dev
- [x] Template created using `/template-create`
- [x] Template passes `/template-validate` with 9+/10 score
- [x] All 16 validation sections score 8+/10
- [x] Zero critical issues
- [x] README documents monorepo architecture
- [x] Template installed in `installer/core/templates/react-fastapi-monorepo/`

---

## Implementation Scope

**IMPORTANT: Claude Code Tool Usage**
This task requires you to **execute commands using the SlashCommand tool**, not just describe them. This monorepo template combines TASK-057 (React) + TASK-058 (FastAPI) with additional type safety and Docker orchestration. You will iteratively create, validate, refine, and re-validate the template until it achieves 9+/10 quality.

### Step 1: Clone and Study Source Repositories

Use **Bash tool** to clone reference repositories:

```bash
# Clone official FastAPI template
cd /tmp
git clone https://github.com/tiangolo/full-stack-fastapi-template.git

# Clone Turborepo example
git clone https://github.com/sinanbekar/monorepo-turborepo-python.git
```

Use **Read tool** to study:
- FastAPI template structure (`full-stack-fastapi-template/backend/`, `full-stack-fastapi-template/frontend/`)
- Turborepo configuration (`monorepo-turborepo-python/turbo.json`)
- Docker Compose setup (`full-stack-fastapi-template/docker-compose.yml`)
- Type generation patterns (research from type-safety guide)

### Step 2: Create Monorepo Structure with Turborepo

Use **Bash tool**:

```bash
cd /tmp
mkdir react-fastapi-monorepo && cd react-fastapi-monorepo

# Initialize Turborepo
pnpm dlx create-turbo@latest .
# Select: basic example

# Create app directories
mkdir -p apps/frontend apps/backend packages/shared-types
```

### Step 3: Integrate Frontend from react-typescript Template

Use **Bash tool** and **Read tool**:

```bash
# Copy patterns from completed react-typescript template (TASK-057)
# Located at: installer/core/templates/react-typescript/
```

Use **Write tool** to create:
- Frontend app in `apps/frontend/` following react-typescript patterns
- Vite configuration
- TypeScript configuration
- API client that uses shared types

### Step 4: Integrate Backend from fastapi-python Template

Use **Bash tool** and **Read tool**:

```bash
# Copy patterns from completed fastapi-python template (TASK-058)
# Located at: installer/core/templates/fastapi-python/
```

Use **Write tool** to create:
- Backend app in `apps/backend/` following fastapi-python patterns
- FastAPI application with OpenAPI generation
- CRUD operations with Pydantic schemas
- Database setup with SQLAlchemy

### Step 5: Add Type Safety Layer (OpenAPI → TypeScript)

Use **Bash tool** and **Write tool**:

```bash
# Setup shared types package
cd packages/shared-types
pnpm init
pnpm add -D @hey-api/openapi-ts
```

Use **Write tool** to create:
- `packages/shared-types/package.json` with type generation script
- Type generation workflow documentation

**Type generation flow**:
1. Backend generates OpenAPI spec (`/openapi.json` endpoint)
2. Shared-types package runs `@hey-api/openapi-ts` to generate TypeScript
3. Frontend imports generated types for type-safe API calls

### Step 6: Add Docker Compose and Turborepo Configuration

Use **Write tool** to create:

**docker-compose.yml** (root):
- PostgreSQL service
- Backend service (FastAPI)
- Frontend service (Vite)
- Volume configuration

**turbo.json** (root):
- Build pipeline with dependencies
- Dev, test, lint tasks
- Type generation task

**Root package.json**:
- Monorepo scripts (dev, build, test, docker:up, generate-types)
- Turborepo configuration

### Step 7: Verify Monorepo Functionality

Use **Bash tool** to verify:

```bash
# Test Turborepo tasks
pnpm build      # Should build all apps
pnpm dev        # Should start all services
pnpm generate-types  # Should generate TypeScript types

# Test Docker Compose
docker-compose up   # Should start all services
```

### Step 8: Create Template Using `/template-create` Command

**Execute using SlashCommand tool**:

IT IS MANDATORY TO INVOKE THIS COMMAND - DO NOT GET ALL CREATIVE AND DECIDE TO DO THIS MANUALLY AS WE WANT TO EVALUATE THE COMMAND AS PART OF THIS PROCESS.

```
Use SlashCommand tool to invoke: /template-create --skip-qa --validate --output-location=repo
```

**Note**: The `--output-location=repo` (or `-o repo`) flag writes the template directly to `installer/core/templates/` for team/public distribution. This flag is required for reference templates that will be included in the Taskwright repository. (TASK-068 changed the default behavior to write to `~/.agentecflow/templates/` for personal use.)

The '--skip-qa' flag will skip the interactive Q&A which caused issues on a previous task

The command will:
1. Run interactive Q&A (answer as specified below)
2. Analyze the react-fastapi-monorepo codebase
3. Generate manifest.json, settings.json, CLAUDE.md, templates/, agents/
4. Write directly to `installer/core/templates/react-fastapi-monorepo/` (repo location)
5. Run extended validation (TASK-043)
6. Generate validation-report.md

**Q&A Answers**:
- **Template name**: react-fastapi-monorepo
- **Template type**: Full-stack Monorepo
- **Primary languages**: TypeScript, Python
- **Frameworks**: React, FastAPI, Turborepo
- **Architecture patterns**: Monorepo, Type-safe API, Microservices
- **Database**: PostgreSQL (via Docker)
- **Testing**: Vitest (frontend), pytest (backend)
- **Container**: Docker Compose
- **Generate custom agents**: Yes

**Expected Output**: Template created at `installer/core/templates/react-fastapi-monorepo/` with initial validation score of 7-8/10

### Step 9: Review Initial Validation Report

Use **Read tool** to review the validation report:

```
Read: installer/core/templates/react-fastapi-monorepo/validation-report.md
```

Identify issues in these categories:
- Placeholder consistency (target: 9+/10)
- Pattern fidelity (target: 9+/10)
- Documentation completeness (target: 9+/10)
- Agent validation (target: 9+/10)
- Manifest accuracy (target: 9+/10)

### Step 10: Comprehensive Audit with AI Assistance

**Execute using SlashCommand tool**:

```
Use SlashCommand tool to invoke: /template-validate installer/core/templates/react-fastapi-monorepo --sections 1-16
```

This runs the 16-section audit framework with AI assistance for sections 8, 11, 12, 13.

**Expected Output**:
- Section-by-section scores
- Detailed findings report
- AI-generated strengths/weaknesses
- Critical issues (if any)
- Specific recommendations for improvement

### Step 11: Iterative Improvement Loop

Based on validation findings, use **Edit tool** or **Write tool** to improve the template:

**Common Improvements**:

1. **Enhance CLAUDE.md** (Use Edit tool):
   - Add monorepo architecture diagram
   - Document type generation workflow (OpenAPI → TypeScript)
   - Explain Docker Compose orchestration
   - Show Turborepo task dependencies
   - Document all agents with examples

2. **Improve Templates** (Use Edit/Write tools):
   - Frontend CRUD templates using typed API client
   - Backend API route templates
   - Shared type definition templates
   - Docker service templates
   - Turborepo task configuration templates
   - Fix placeholder inconsistencies

3. **Enhance Agents** (Use Edit/Write tools):
   - Create react-fastapi-monorepo-specialist agent
   - Create monorepo-type-safety-specialist agent
   - Create docker-orchestration-specialist agent
   - Complete agent prompts with examples
   - Ensure agents reference CLAUDE.md correctly

4. **Complete Manifest** (Use Edit tool):
   - Fill all metadata fields
   - Document monorepo-specific placeholders
   - Verify multi-language stack accuracy (TypeScript + Python)
   - Add quality scores from analysis

### Step 12: Re-validate After Improvements

**Execute using SlashCommand tool**:

```
Use SlashCommand tool to invoke: /template-validate installer/core/templates/react-fastapi-monorepo --sections 10,11,16
```

(Re-run specific sections to verify improvements)

**Repeat Steps 11-12 until**:
- Overall score ≥9.0/10
- All 16 sections ≥8.0/10
- Zero critical issues
- Recommendation: APPROVE

### Step 13: Verify Template Location

Use **Bash tool**:

```bash
# Verify structure (template already in repo location)
ls -la installer/core/templates/react-fastapi-monorepo/
```

### Step 14: Final Validation

**Execute using SlashCommand tool**:

```
Use SlashCommand tool to invoke: /template-validate installer/core/templates/react-fastapi-monorepo --sections 1-16
```

**Acceptance Criteria**:
- Overall Score: ≥9.0/10
- Grade: A or A+
- All sections: ≥8.0/10
- Critical issues: 0
- Recommendation: APPROVE

### Step 15: Installation and Integration Testing

Use **Bash tool** to test the template:

```bash
# Install template globally
./installer/scripts/install.sh

# Test template initialization in clean directory
cd /tmp/test-monorepo
taskwright init react-fastapi-monorepo

# Verify monorepo setup
cd test-monorepo

# Test with Docker Compose
docker-compose up
# → Frontend on http://localhost:3000
# → Backend on http://localhost:8000
# → PostgreSQL on localhost:5432

# Test type generation
pnpm generate-types
# → Check packages/shared-types/src for generated types

# Test builds
pnpm build

# Test development mode
pnpm dev
```

---

## Template Structure (Expected)

```
installer/core/templates/react-fastapi-monorepo/
├── manifest.json                    # Template metadata
├── settings.json                    # Naming conventions
├── CLAUDE.md                        # AI guidance for monorepo
├── README.md                        # Human-readable docs
├── templates/                       # Code generation templates
│   ├── apps/
│   │   ├── frontend/
│   │   │   ├── component.tsx.template
│   │   │   ├── api-hook.ts.template
│   │   │   └── test.test.tsx.template
│   │   └── backend/
│   │       ├── router.py.template
│   │       ├── schema.py.template
│   │       ├── crud.py.template
│   │       └── test.py.template
│   ├── packages/
│   │   └── shared-types/
│   │       └── client.ts.template
│   └── docker/
│       ├── docker-compose.yml.template
│       ├── frontend.Dockerfile.template
│       └── backend.Dockerfile.template
└── agents/                          # Stack-specific AI agents
    ├── react-fastapi-monorepo-specialist.md
    ├── monorepo-typescript-specialist.md
    └── docker-orchestration-specialist.md
```

---

## Key Patterns to Capture

### 1. Monorepo Structure
```
react-fastapi-monorepo/
├── apps/
│   ├── frontend/       # React + TypeScript + Vite
│   └── backend/        # FastAPI + SQLAlchemy
├── packages/
│   └── shared-types/   # Generated TypeScript types
├── docker-compose.yml  # Local development
├── turbo.json         # Turborepo config
└── package.json       # Root scripts
```

### 2. Type-Safe API Client
```typescript
// packages/shared-types/src/client.ts (auto-generated)
import { ApiClient } from '@hey-api/openapi-ts'

export const api = new ApiClient({
  baseUrl: import.meta.env.VITE_API_URL
})

// Auto-generated typed methods
export const { getUsers, createUser, updateUser } = api

// apps/frontend/src/hooks/useUsers.ts
import { useQuery } from '@tanstack/react-query'
import { getUsers } from '@repo/shared-types'

export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => getUsers() // Fully typed!
  })
}
```

### 3. Shared Pydantic → TypeScript
```python
# apps/backend/app/schemas/user.py
from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    name: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    created_at: datetime
```

**Generates TypeScript**:
```typescript
// packages/shared-types/src/schemas.ts (auto-generated)
export interface UserCreate {
  email: string
  name: string
}

export interface UserResponse {
  id: number
  email: string
  name: string
  created_at: string
}
```

### 4. Docker Compose Development
```bash
# Start everything with one command
docker-compose up

# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# PostgreSQL: localhost:5432
# Auto-reload enabled for both services
```

### 5. Turborepo Task Orchestration
```bash
# Run all dev servers in parallel
pnpm dev

# Build all apps
pnpm build

# Run all tests
pnpm test

# Generate types before building
turbo run build --filter=frontend
# → Automatically runs generate-types first (dependency)
```

---

## Acceptance Criteria

### Functional Requirements
- [ ] Monorepo created with Turborepo
- [ ] Frontend integrated from react-typescript
- [ ] Backend integrated from fastapi-python
- [ ] Type generation working (OpenAPI → TypeScript)
- [ ] Docker Compose orchestration functional
- [ ] Template created using `/template-create`
- [ ] Template validates at 9+/10 score
- [ ] All 16 validation sections score 8+/10
- [ ] Zero critical issues
- [ ] Generated monorepo builds successfully
- [ ] Generated monorepo runs in Docker

### Quality Requirements
- [ ] CLAUDE.md documents monorepo patterns
- [ ] README comprehensive and clear
- [ ] manifest.json complete and accurate
- [ ] settings.json defines naming conventions
- [ ] Agents created (monorepo specialists)
- [ ] Templates cover frontend + backend + shared

### Documentation Requirements
- [ ] Monorepo architecture documented
- [ ] Type generation workflow explained
- [ ] Docker Compose usage shown
- [ ] Turborepo task orchestration documented
- [ ] Development workflow clear

---

## Testing Requirements

### Template Validation Tests
```bash
# Comprehensive validation
/template-validate installer/core/templates/react-fastapi-monorepo

# Expected results:
# Overall Score: ≥9.0/10
# Grade: A or A+
# All sections: ≥8.0/10
# Critical issues: 0
# Recommendation: APPROVE
```

### Generated Monorepo Tests
```bash
# Initialize monorepo from template
taskwright init react-fastapi-monorepo --output /tmp/test-monorepo

# Test Docker Compose
cd /tmp/test-monorepo
docker-compose up -d
# Expected: All services start successfully

# Test frontend
curl http://localhost:3000
# Expected: React app loads

# Test backend
curl http://localhost:8000/docs
# Expected: FastAPI OpenAPI docs

# Test type generation
pnpm generate-types
# Expected: TypeScript types generated in packages/shared-types

# Test builds
pnpm build
# Expected: All apps build successfully

# Test development mode
pnpm dev &
# Expected: Both apps start in dev mode

# Test type safety
cd apps/frontend
pnpm type-check
# Expected: No TypeScript errors (using generated types)

# Cleanup
docker-compose down
```

---

## Risk Mitigation

### Risk 1: Monorepo Complexity Too High
**Mitigation**: Clear documentation, step-by-step setup guide, working examples

### Risk 2: Type Generation Fails
**Mitigation**: Test with multiple OpenAPI specs, fallback to manual types, clear error messages

### Risk 3: Docker Compose Issues
**Mitigation**: Test on multiple platforms (Mac, Linux, Windows), provide troubleshooting guide

### Risk 4: Validation Score Below 9/10
**Mitigation**: Iterative improvement, leverage TASK-057 and TASK-058 quality, comprehensive testing

---

## Success Metrics

**Quantitative**:
- Template validation score: ≥9.0/10
- All validation sections: ≥8.0/10
- Critical issues: 0
- Docker Compose success: 100%
- Type generation success: 100%
- Build success: 100%

**Qualitative**:
- Monorepo demonstrates best practices
- Type safety is clear and functional
- Documentation is comprehensive
- Developers understand monorepo benefits
- Template serves as reference for Python full-stack

---

## Related Tasks

- **TASK-057**: Prerequisite - react-typescript template (frontend component)
- **TASK-058**: Prerequisite - fastapi-python template (backend component)
- **TASK-044**: Template validation command
- **TASK-056**: Template audit (quality standards)
- **TASK-059**: Next.js template (parallel full-stack approach)
- **TASK-060**: Remove low-quality templates
- **TASK-061**: Update documentation
- **TASK-063**: Update documentation for 4-template strategy (NEW)

---

## Example Validation Report (Target)

```markdown
# Template Validation Report

**Template**: react-fastapi-monorepo
**Generated**: 2025-01-XX
**Overall Score**: 9.1/10 (A)

## Executive Summary

**Recommendation**: APPROVE for production

Excellent React + FastAPI monorepo demonstrating:
- Type-safe full-stack development (OpenAPI → TypeScript)
- Production-ready monorepo structure (Turborepo)
- Docker orchestration for local dev and deployment
- Modern Python + React patterns

## Quality Scores

| Category | Score | Status |
|----------|-------|--------|
| CRUD Completeness | 9.0/10 | ✅ |
| Layer Symmetry | 9.0/10 | ✅ |
| Documentation | 9.5/10 | ✅ |
| Testing | 9.0/10 | ✅ |
| Type Safety | 9.5/10 | ✅ |
| **Overall** | **9.1/10** | **✅ APPROVE** |

## Strengths (Top 5)

1. **Excellent Type Safety**: OpenAPI → TypeScript auto-generation
2. **Production-Ready Monorepo**: Turborepo with proper task orchestration
3. **Comprehensive Docker Setup**: Local dev + production deployment
4. **Clear Architecture**: Separate concerns (frontend/backend/shared)
5. **Thorough Documentation**: CLAUDE.md + README with examples

## Production Readiness

**Status**: APPROVED

**Threshold**: ≥8/10 for production deployment ✅

---

**Report Generated**: 2025-01-XX
**Validation Duration**: 60 minutes
**Template Location**: installer/core/templates/react-fastapi-monorepo/
```

---

**Document Status**: Ready for Implementation
**Created**: 2025-01-08
**Parent Epic**: Template Strategy Overhaul
**Depends On**: TASK-057 (React), TASK-058 (FastAPI) must be completed first
