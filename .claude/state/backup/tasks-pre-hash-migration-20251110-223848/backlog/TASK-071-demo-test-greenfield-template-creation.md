# TASK-071: Demo/Test - Greenfield Template Creation Workflow

**Created**: 2025-01-10
**Priority**: Medium
**Type**: Testing & Demo
**Parent**: Template Strategy Validation
**Status**: backlog
**Complexity**: Medium (6/10)
**Estimated Effort**: 5-7 hours
**Dependencies**: None

---

## Problem Statement

GuardKit supports two template creation workflows:
1. **Existing Codebase** → Template (TASK-070)
2. **Greenfield** → Build → Template → Reuse

The second workflow hasn't been demonstrated: starting from scratch, building a quality project, then extracting it as a template for future use.

**Current State**: No documented examples of the greenfield → template workflow, which is valuable for:
- Learning new stacks (build, learn, templatize)
- Experimenting with patterns (prototype, validate, templatize)
- Creating specialized templates (build for specific need, generalize)

**Desired State**: Complete demo showing:
1. Planning and building a greenfield project
2. Using GuardKit's workflow to ensure quality
3. Extracting the project as a template
4. Using that template to start new projects

---

## Context

**Greenfield Use Cases**:
1. **Learning Path**: Learn Next.js → Build demo app → Extract template → Use for client projects
2. **Experimentation**: Try new pattern → Validate in real project → Templatize if successful
3. **Specialized Needs**: Need microservice template → Build reference implementation → Extract for team
4. **Stack Migration**: Build migration example → Validate approach → Templatize for other services

**Value Proposition**:
- Build once, reuse many times
- Quality-test patterns before templatizing
- Create templates tailored to your exact needs
- Evolve templates as you learn

**Demo Scenario** (Recommended):
Build a **GraphQL API with Node.js + TypeScript** as a greenfield project, then extract it as a template.

**Why GraphQL API?**
- Not covered by existing templates
- Real-world need
- Clear patterns to demonstrate
- Testable and validatable
- Medium complexity (~6/10)

---

## Objectives

### Primary Objective
Demonstrate the complete greenfield → template workflow by building a production-quality GraphQL API from scratch, extracting it as a template, and reusing it for new projects.

### Success Criteria
- [ ] Greenfield project planned with clear objectives
- [ ] Project built using GuardKit workflow (/task-create, /task-work)
- [ ] Project passes all quality gates (tests, coverage, architecture)
- [ ] Template extracted with `/template-create` (≥8.0/10 quality)
- [ ] Template validated and enhanced
- [ ] Template used to initialize 2+ new projects
- [ ] Complete blog post created (greenfield → template story)
- [ ] Video outline created showing full workflow
- [ ] Screenshots captured of entire journey
- [ ] Lessons learned documented

---

## Implementation Scope

### Phase 1: Plan Greenfield Project

**Project Definition**:
```markdown
# Project: GraphQL API Starter

## Overview
A production-ready GraphQL API built with Node.js, TypeScript, and Apollo Server.

## Features
- GraphQL schema with queries, mutations, subscriptions
- Type-safe resolvers with TypeScript
- DataLoader for batching and caching
- Authentication and authorization
- Error handling and validation
- Comprehensive testing (unit + integration)
- Docker configuration
- CI/CD setup

## Tech Stack
- Node.js + TypeScript
- Apollo Server
- GraphQL
- TypeORM or Prisma (database)
- PostgreSQL
- Jest (testing)
- Docker

## Quality Targets
- Test coverage: ≥80%
- Type safety: 100%
- Documentation: Complete
- Architecture score: ≥70/100
```

**Create Project**:
```bash
# Create project directory
mkdir ~/projects/graphql-api-starter
cd ~/projects/graphql-api-starter

# Initialize Node.js project
npm init -y

# Initialize TypeScript
npm install -D typescript @types/node ts-node
npx tsc --init

# Initialize git
git init
git add .
git commit -m "Initial commit: GraphQL API Starter"
```

### Phase 2: Build Using GuardKit Workflow

**Task 1: Setup Project Structure**
```bash
# Use /task-create to create first task
/task-create "Setup TypeScript + Node.js project structure with linting and testing"

# Expected output: TASK-001
```

```bash
# Work on task
/task-work TASK-001

# Expected: Creates folder structure, configs, package.json, etc.
```

**Task 2: Implement GraphQL Schema**
```bash
/task-create "Define GraphQL schema with User and Post types, queries and mutations"
/task-work TASK-002
```

**Task 3: Implement Resolvers**
```bash
/task-create "Implement type-safe resolvers for User and Post with DataLoader"
/task-work TASK-003
```

**Task 4: Add Authentication**
```bash
/task-create "Add JWT authentication and authorization middleware"
/task-work TASK-004
```

**Task 5: Add Database Integration**
```bash
/task-create "Integrate Prisma ORM with PostgreSQL database"
/task-work TASK-005
```

**Task 6: Add Testing**
```bash
/task-create "Add comprehensive tests (unit + integration) for resolvers and auth"
/task-work TASK-006
```

**Task 7: Add Docker Configuration**
```bash
/task-create "Add Docker and docker-compose configuration for development and production"
/task-work TASK-007
```

**Track Progress**:
```bash
# Check task status
/task-status

# Expected: All tasks completed, all tests passing
```

**Document Build Process**:
Create `build-log.md`:
```markdown
# GraphQL API Starter - Build Log

## Day 1: Project Setup (TASK-001)
- Initialized TypeScript configuration
- Setup ESLint + Prettier
- Configured Jest for testing
- Created folder structure
- **Outcome**: Clean foundation ready for development

## Day 2: GraphQL Schema (TASK-002)
- Defined User and Post types
- Created queries (users, user, posts, post)
- Created mutations (createUser, updateUser, createPost)
- **Outcome**: Complete schema with 80% coverage

## Day 3: Resolvers (TASK-003)
- Implemented type-safe resolvers
- Added DataLoader for N+1 prevention
- Tested all resolver paths
- **Outcome**: 85% test coverage, performant queries

## Day 4: Authentication (TASK-004)
- JWT token generation and validation
- Authorization middleware
- Protected resolver fields
- **Outcome**: Secure API with 90% auth coverage

## Day 5: Database (TASK-005)
- Prisma schema defined
- Migrations created
- Database seeding
- **Outcome**: Full ORM integration, 100% type safety

## Day 6: Testing (TASK-006)
- Unit tests for all resolvers
- Integration tests for API
- Auth flow testing
- **Outcome**: 88% overall coverage

## Day 7: Docker (TASK-007)
- Development docker-compose
- Production Dockerfile
- Environment configuration
- **Outcome**: Containerized application

## Final Metrics
- Total LOC: ~4,500
- Test Coverage: 88%
- Tasks Completed: 7
- Architecture Score: 78/100 (from TASK-006 review)
- Build Success: ✅
```

### Phase 3: Validate Project Quality

**Run Quality Checks**:
```bash
# Verify tests pass
npm test -- --coverage
# Expected: All tests pass, ≥80% coverage

# Verify build succeeds
npm run build
# Expected: TypeScript compiles without errors

# Verify linting passes
npm run lint
# Expected: No errors

# Run type checking
npx tsc --noEmit
# Expected: No type errors

# Start server
npm run dev
# Expected: Server starts, GraphQL playground accessible
```

**Quality Metrics**:
```markdown
# Quality Validation Results

## Test Coverage
- Line Coverage: 88% ✅ (target: ≥80%)
- Branch Coverage: 82% ✅ (target: ≥75%)
- Function Coverage: 91% ✅
- Statement Coverage: 89% ✅

## Type Safety
- TypeScript Errors: 0 ✅
- Type Coverage: 100% ✅

## Architecture
- SOLID Compliance: 78/100 ✅ (target: ≥60)
- Pattern Consistency: High ✅
- Code Organization: Clear ✅

## Documentation
- README: Complete ✅
- API Docs: GraphQL schema self-documenting ✅
- Setup Guide: Clear ✅

## Production Readiness
- Error Handling: Comprehensive ✅
- Logging: Structured ✅
- Security: JWT + validation ✅
- Docker: Configured ✅

**Overall: Production-Ready ✅**
```

### Phase 4: Extract Template

**Prepare for Extraction**:
```bash
cd ~/projects/graphql-api-starter

# Clean build artifacts
rm -rf node_modules
rm -rf dist
rm -rf coverage
rm -rf .env

# Backup .claude directory
mv .claude .claude.backup

# Review structure
tree -L 3 -I 'node_modules|dist|coverage'
```

**Extract Template**:
```bash
# Use SlashCommand tool
/template-create --validate --output-location=repo
```

**Interactive Prompts**:
```
Template name? graphql-api-starter
Template description? Production-ready GraphQL API with Apollo Server, TypeScript, Prisma, and JWT auth
Technology stack? typescript
Author? [Your Name]
Version? 1.0.0
```

**Expected Output**:
```
installer/global/templates/graphql-api-starter/
├── manifest.json
├── settings.json
├── CLAUDE.md
├── README.md
├── validation-report.md
└── templates/
    ├── src/
    │   ├── schema/
    │   ├── resolvers/
    │   ├── middleware/
    │   └── utils/
    ├── tests/
    ├── package.json
    ├── tsconfig.json
    ├── docker-compose.yml
    └── Dockerfile
```

**Restore .claude**:
```bash
mv .claude.backup .claude
```

### Phase 5: Review and Enhance Template

**Review Validation Report**:
```bash
cat installer/global/templates/graphql-api-starter/validation-report.md
```

**Target**: Quality score ≥8.0/10

**Enhance Manifest** (if needed):
```json
{
  "name": "graphql-api-starter",
  "description": "Production-ready GraphQL API with Apollo Server, TypeScript, Prisma, and JWT auth",
  "version": "1.0.0",
  "stack": "typescript",
  "category": "backend-api",
  "placeholders": {
    "ProjectName": {
      "name": "{{ProjectName}}",
      "description": "Project name in PascalCase (e.g., UserAPI)",
      "required": true,
      "pattern": "^[A-Z][A-Za-z0-9]*$",
      "example": "UserAPI"
    },
    "project-name": {
      "name": "{{project-name}}",
      "description": "Project name in kebab-case (e.g., user-api)",
      "required": true,
      "pattern": "^[a-z][a-z0-9-]*$",
      "example": "user-api"
    },
    "description": {
      "name": "{{description}}",
      "description": "Project description",
      "required": true,
      "example": "A GraphQL API for user management"
    },
    "author": {
      "name": "{{author}}",
      "description": "Project author",
      "required": true,
      "example": "Your Name"
    },
    "DatabaseName": {
      "name": "{{DatabaseName}}",
      "description": "PostgreSQL database name",
      "required": true,
      "pattern": "^[a-z][a-z0-9_]*$",
      "example": "user_api_db"
    }
  }
}
```

**Enhance CLAUDE.md**:
```markdown
# GraphQL API with Apollo Server

## Architecture Overview

This template provides a production-ready GraphQL API built with:
- **Apollo Server**: Industry-standard GraphQL server
- **TypeScript**: Full type safety across schema and resolvers
- **Prisma**: Modern ORM with type-safe database access
- **JWT Authentication**: Secure user authentication
- **DataLoader**: N+1 query prevention and caching

## Key Patterns

### Schema-First Design
- Define GraphQL schema in `schema.graphql`
- Generate TypeScript types automatically
- Type-safe resolver implementations

### Resolver Pattern
```typescript
export const resolvers = {
  Query: {
    users: async (_, __, { dataSources, user }) => {
      // DataLoader prevents N+1 queries
      return dataSources.userAPI.getUsers();
    }
  }
}
```

### Authentication Middleware
```typescript
// JWT verification in context
const context = ({ req }) => {
  const token = req.headers.authorization;
  const user = verifyToken(token);
  return { user, dataSources };
};
```

## Development Workflow

1. Define schema in `src/schema/`
2. Implement resolvers in `src/resolvers/`
3. Add tests in `tests/`
4. Run `npm test` (quality gates enforce ≥80% coverage)
5. Use `/task-work` for new features

## Testing Strategy

- **Unit Tests**: Resolver logic in isolation
- **Integration Tests**: Full GraphQL queries
- **Auth Tests**: JWT flow and authorization
- **Coverage Target**: ≥80% line, ≥75% branch

## Deployment

```bash
# Development
docker-compose up

# Production
docker build -t graphql-api .
docker run -p 4000:4000 graphql-api
```
```

### Phase 6: Test Template Initialization

**Test 1: Initialize First Project**:
```bash
mkdir -p ~/template-test-workspace/blog-api
cd ~/template-test-workspace/blog-api

guardkit init graphql-api-starter

# Prompts:
# ProjectName: BlogAPI
# project-name: blog-api
# description: A GraphQL API for blog management
# author: Test User
# DatabaseName: blog_api_db
```

**Verify Structure**:
```bash
tree -L 2
# Expected:
# .
# ├── src/
# │   ├── schema/
# │   ├── resolvers/
# │   ├── middleware/
# │   └── utils/
# ├── tests/
# ├── package.json (name: "blog-api")
# ├── tsconfig.json
# └── docker-compose.yml (database: blog_api_db)
```

**Test Installation and Execution**:
```bash
# Install dependencies
npm install

# Start database
docker-compose up -d postgres

# Run migrations
npx prisma migrate dev

# Run tests
npm test -- --coverage
# Expected: All tests pass, ≥80% coverage

# Start server
npm run dev
# Expected: Server on http://localhost:4000
# Visit http://localhost:4000/graphql (playground)
```

**Test 2: Initialize Second Project**:
```bash
cd ~/template-test-workspace/product-api
guardkit init graphql-api-starter

# Prompts:
# ProjectName: ProductAPI
# project-name: product-api
# description: A GraphQL API for product catalog
# author: Test User
# DatabaseName: product_api_db

# Verify independent setup
npm install
docker-compose up -d
npm test
npm run dev
```

### Phase 7: Document Greenfield Journey

**Create Blog Post** (`docs/demos/greenfield-to-template-blog.md`):
```markdown
# From Zero to Reusable: Building and Templatizing a GraphQL API

## Introduction
"I need a GraphQL API for my project." Sound familiar? Instead of copying code from old projects or starting from scratch every time, what if you could build once and reuse infinitely?

This is the story of building a production-ready GraphQL API from scratch and turning it into a reusable template with GuardKit.

## The Challenge
We needed a GraphQL API starter that:
- Uses modern patterns (Apollo Server, TypeScript, Prisma)
- Includes authentication and authorization
- Has comprehensive testing
- Is production-ready
- Can be reused for multiple projects

## The Journey

### Week 1: Building the Foundation
**Day 1-2: Project Setup** (TASK-001)
[Details of setting up TypeScript, linting, testing...]

**Day 3-4: GraphQL Schema and Resolvers** (TASK-002, TASK-003)
[Details of schema design and resolver implementation...]

**Day 5-6: Authentication and Database** (TASK-004, TASK-005)
[Details of JWT auth and Prisma integration...]

**Day 7: Testing and Docker** (TASK-006, TASK-007)
[Details of comprehensive testing and containerization...]

### Week 2: Quality Validation
We achieved:
- ✅ 88% test coverage
- ✅ 100% type safety
- ✅ 78/100 architecture score
- ✅ Docker-ready deployment

### Week 3: Template Extraction
Using GuardKit's `/template-create`:
```bash
/template-create --validate --output-location=repo
```

In 5 minutes, our week of work became a reusable template.

### Week 4: Reaping the Benefits
**Project 1: Blog API** - Initialized in 2 minutes, ready for development
**Project 2: Product API** - Initialized in 2 minutes, independent setup
**Project 3: User API** - You get the idea...

## Lessons Learned

1. **Build Quality First**: The template is only as good as the source project
2. **Use GuardKit Throughout**: Quality gates ensure template worthiness
3. **Think Generic During Development**: Avoid hardcoding project-specific logic
4. **Document Patterns**: Future you will thank present you
5. **Test the Template**: Initialize multiple projects to verify reusability

## The Results

**Time Investment**:
- Building original: 7 days (56 hours)
- Extracting template: 5 minutes
- Initializing new project: 2 minutes

**ROI**:
- First new project: Immediate return (saved 56 hours)
- Second new project: 2x return
- Third new project: 3x return
- [Pattern continues...]

## Conclusion
The greenfield → template workflow transforms one-time projects into perpetual value. Build once, reuse forever.

Ready to try it yourself? [Link to getting started guide]
```

**Create Video Script** (`docs/demos/greenfield-to-template-video.md`):
```markdown
# Greenfield to Template - Video Script (15 minutes)

## Act 1: The Problem (0:00-1:00)
- **Opening Hook**: "How many times have you rebuilt the same project from scratch?"
- **Problem Setup**: Every new project = hours of setup, configuration, boilerplate
- **Traditional Solutions**: Copy-paste old code (messy), start from scratch (slow), use generic templates (not your patterns)
- **Better Way**: Build your perfect project once, extract it as a template, reuse forever

## Act 2: The Build (1:00-6:00)
- **Project Introduction**: We're building a GraphQL API starter
- **Tech Stack**: Apollo Server + TypeScript + Prisma + JWT
- **GuardKit Workflow Demo**:
  - Show `/task-create` for first task
  - Show `/task-work` executing with quality gates
  - Fast-forward through 7 tasks (montage style)
  - Highlight key moments: tests passing, architecture review, final build

## Act 3: Quality Validation (6:00-8:00)
- **Show Test Results**: 88% coverage, all green
- **Show Type Safety**: No TypeScript errors
- **Show Architecture Score**: 78/100 from automated review
- **Show Running App**: GraphQL playground in action
- **The Punchline**: "This took us a week. Now watch this..."

## Act 4: Template Extraction (8:00-10:00)
- **The Magic Moment**: Run `/template-create --validate`
- **Show Interactive Prompts**: Name, description, stack
- **Show Validation Report**: Quality score 8.5/10
- **Show Generated Template**: Files, structure, placeholders
- **The Reveal**: "One week of work → 5 minutes to template"

## Act 5: Reusability Demo (10:00-13:00)
- **First New Project**: Initialize blog-api (2 minutes start to finish)
  - Show initialization
  - Show placeholder substitution
  - npm install, tests pass, server running
- **Second New Project**: Initialize product-api (fast-forward, same result)
- **The Impact**: "Each new project: 2 minutes instead of 56 hours"

## Act 6: Lessons and Call to Action (13:00-15:00)
- **Key Lessons**:
  1. Build quality first
  2. Use GuardKit throughout
  3. Think generic during development
  4. Test the template
- **ROI Calculation**: Show the math (56 hours saved per project)
- **Call to Action**: "What will you templatize?"
- **Resources**: Links to docs, GitHub, community
- **Closing**: "Thanks for watching. Now go build once and reuse forever."
```

### Phase 8: Create Comparative Analysis

**Document Value** (`docs/demos/greenfield-template-value-analysis.md`):
```markdown
# Greenfield → Template: Value Analysis

## Scenario Comparison

### Scenario 1: Traditional Approach (No Template)
**Project 1**: 56 hours (build from scratch)
**Project 2**: 48 hours (copy-paste + adapt from Project 1)
**Project 3**: 45 hours (copy-paste + adapt from Project 2)
**Total for 3 projects**: 149 hours

### Scenario 2: Greenfield → Template Approach
**Project 1 (Build)**: 56 hours
**Template Extraction**: 0.1 hours (5 minutes)
**Project 2 (Init from template)**: 0.033 hours (2 minutes)
**Project 3 (Init from template)**: 0.033 hours (2 minutes)
**Total for 3 projects**: 56.17 hours

**Savings**: 92.83 hours (62% reduction)

## Quality Comparison

| Aspect | Traditional | Greenfield → Template |
|--------|-------------|----------------------|
| Consistency | Low (copy-paste errors) | High (same template) |
| Quality | Degrades over time | Maintains quality |
| Test Coverage | Varies (70-90%) | Consistent (88%) |
| Documentation | Incomplete | Complete |
| Type Safety | Partial | 100% |
| Architecture | Inconsistent | Validated (78/100) |

## Long-Term Value

### After 10 Projects
**Traditional**: ~450 hours
**Greenfield → Template**: ~56.3 hours
**Savings**: ~393.7 hours (87% reduction)

### After 20 Projects
**Traditional**: ~880 hours
**Greenfield → Template**: ~56.6 hours
**Savings**: ~823.4 hours (94% reduction)

### Pattern
The more you reuse, the higher the ROI.

## Intangible Benefits

1. **Confidence**: Every project starts production-ready
2. **Learning**: Patterns crystallize as templates
3. **Team Alignment**: Everyone uses same foundation
4. **Evolution**: Update template → all future projects benefit
5. **Onboarding**: New team members start with proven patterns

## When to Use Greenfield → Template

✅ **Use When**:
- You're learning a new stack (build → learn → templatize)
- You're experimenting with patterns (prototype → validate → templatize)
- You need specialized templates (build reference → generalize)
- You're building multiple similar projects

❌ **Don't Use When**:
- Project is one-off (no reuse planned)
- Project is too unique (patterns won't generalize)
- Time-to-market is critical (use existing template instead)
```

---

## Acceptance Criteria

### Greenfield Build
- [ ] Project planned with clear objectives
- [ ] All tasks created with `/task-create`
- [ ] All tasks completed with `/task-work`
- [ ] All tests pass (≥80% coverage)
- [ ] Architecture score ≥70/100
- [ ] Production-ready application running

### Template Extraction
- [ ] Template extracted with `/template-create --validate`
- [ ] Quality score ≥8.0/10
- [ ] Manifest includes all necessary placeholders
- [ ] CLAUDE.md documents patterns
- [ ] README explains template usage

### Template Validation
- [ ] First project initializes successfully
- [ ] Second project initializes independently
- [ ] All placeholder substitutions work
- [ ] Dependencies install cleanly
- [ ] Tests pass for initialized projects
- [ ] Applications run successfully

### Documentation
- [ ] Build log documents journey
- [ ] Blog post created (greenfield story)
- [ ] Video script created (15 minutes)
- [ ] Value analysis completed
- [ ] Screenshots captured (20+)
- [ ] Lessons learned documented

---

## Deliverables

1. **Greenfield Project** (GraphQL API Starter) - Production-ready
2. **Build Log** (`build-log.md`) - Day-by-day journey
3. **Quality Metrics** (`quality-validation.md`) - All metrics documented
4. **Extracted Template** (`installer/global/templates/graphql-api-starter/`)
5. **Validation Report** (≥8.0/10 quality)
6. **Blog Post** (`greenfield-to-template-blog.md`)
7. **Video Script** (`greenfield-to-template-video.md`) - 15 minutes
8. **Value Analysis** (`greenfield-template-value-analysis.md`)
9. **Test Projects** (2 initialized projects)
10. **Screenshots** (20+ images)

---

## Success Metrics

**Quantitative**:
- Project test coverage: ≥80%
- Template quality score: ≥8.0/10
- Template initialization success: 100%
- Time to initialize: <5 minutes
- Documentation completeness: 100%

**Qualitative**:
- Clear demonstration of greenfield → template value
- Compelling narrative for blog/video
- Actionable lessons learned
- Confidence in recommending workflow
- Production-ready artifacts

---

## Related Tasks

- **TASK-069**: Demo/Test - Core Template Usage
- **TASK-070**: Demo/Test - Custom Template from Existing Codebase
- **TASK-072**: Demo/Test - End-to-End GuardKit Workflow

---

**Document Status**: Ready for Implementation
**Created**: 2025-01-10
**Depends On**: None
