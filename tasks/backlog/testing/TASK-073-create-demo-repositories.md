# TASK-073: Create Demo Repositories and Example Projects

**Created**: 2025-01-10
**Priority**: Medium
**Type**: Documentation & Infrastructure
**Parent**: Template Strategy Validation
**Status**: backlog
**Complexity**: Medium (5/10)
**Estimated Effort**: 6-8 hours
**Dependencies**: TASK-069, TASK-070, TASK-071, TASK-072 (recommended)

---

## Problem Statement

Demo content created in TASK-069 through TASK-072 exists locally but needs to be:
1. **Organized** into shareable repositories
2. **Published** for public access
3. **Referenced** in documentation and marketing materials
4. **Maintained** with clear instructions for replication

**Current State**: Demo projects exist locally but aren't shareable or discoverable.

**Desired State**: Professional demo repositories on GitHub that:
- Showcase Taskwright's capabilities
- Serve as learning resources
- Provide copy-paste examples for documentation
- Act as marketing materials for blog posts and videos

---

## Context

**Demo Content Created** (from previous tasks):
- **TASK-069**: 5 initialized template projects (react-typescript, fastapi-python, etc.)
- **TASK-070**: Custom template extraction example (RealWorld → template)
- **TASK-071**: Greenfield project example (GraphQL API)
- **TASK-072**: End-to-end workflow example (Todo API)

**Repository Strategy**:

### Option 1: Monorepo Approach
**Single Repository**: `taskwright-examples`
```
taskwright-examples/
├── template-demos/           # From TASK-069
│   ├── react-typescript-demo/
│   ├── fastapi-python-demo/
│   └── ...
├── custom-template-demo/     # From TASK-070
├── greenfield-demo/          # From TASK-071
└── end-to-end-demo/          # From TASK-072
```

**Pros**: Single repo to maintain, easy to find
**Cons**: Large size, mixed contexts

### Option 2: Multiple Repositories
**Separate Repositories**:
- `taskwright-template-demos` (TASK-069)
- `taskwright-custom-template-example` (TASK-070)
- `taskwright-greenfield-example` (TASK-071)
- `taskwright-workflow-example` (TASK-072)

**Pros**: Focused repos, clear purpose
**Cons**: More to maintain, harder to discover

### Recommended: Hybrid Approach
**Main Repository**: `taskwright-examples` (monorepo)
**Specialized Repos**: For standout examples
- Main: All demos organized
- Specialized: `taskwright-realworld-template` (showcase quality)
- Specialized: `taskwright-graphql-starter` (usable template)

---

## Objectives

### Primary Objective
Create and publish professional demo repositories showcasing Taskwright's features, suitable for documentation, marketing, and learning.

### Success Criteria
- [ ] Main repository created (`taskwright-examples`)
- [ ] All demo projects organized and committed
- [ ] Each demo has comprehensive README
- [ ] Repository has overall README explaining all demos
- [ ] All demos tested and verified working
- [ ] Repository published to GitHub
- [ ] Specialized repos created for standout examples
- [ ] Documentation updated with repository links
- [ ] All repos tagged with relevant topics
- [ ] CI/CD setup to verify demos stay functional

---

## Implementation Scope

### Phase 1: Create Main Repository Structure

**Initialize Repository**:
```bash
# Create main demo repository
mkdir ~/projects/taskwright-examples
cd ~/projects/taskwright-examples

# Initialize git
git init

# Create structure
mkdir -p template-demos
mkdir -p custom-template-example
mkdir -p greenfield-example
mkdir -p workflow-example
mkdir -p docs
mkdir -p .github/workflows
```

**Create Main README**:
```markdown
# Taskwright Examples

> Comprehensive examples showcasing Taskwright's task workflow system with built-in quality gates.

## What is Taskwright?

Taskwright is a lightweight, pragmatic task workflow system with built-in quality gates that prevents broken code from reaching production.

**Core Features**:
- Quality Gates (architectural review + test enforcement)
- Simple Workflow (create → work → complete)
- AI Collaboration (AI implements, humans decide)
- Zero Ceremony (minimal process, maximum productivity)

## Examples in This Repository

### 1. Template Demos (`template-demos/`)
Demonstrations of all 5 core Taskwright templates.

| Template | Description | Demo Project | Quality |
|----------|-------------|--------------|---------|
| react-typescript | React + TypeScript frontend | Task Dashboard | 9+/10 |
| fastapi-python | FastAPI backend API | Task API | 9+/10 |
| nextjs-fullstack | Next.js full-stack app | Task Manager | 9+/10 |
| react-fastapi-monorepo | Full-stack monorepo | Task Workspace | 9.2/10 |
| default | Language-agnostic (Go) | Task CLI | 8+/10 |

**Learn More**: [Template Demos README](template-demos/README.md)

### 2. Custom Template Example (`custom-template-example/`)
Complete example of extracting a custom template from an existing codebase.

**Demonstrates**:
- Selecting a suitable source codebase (RealWorld React)
- Using `/template-create` to extract template
- Validating template quality (8.5/10)
- Using template to create new projects

**Learn More**: [Custom Template Example README](custom-template-example/README.md)

### 3. Greenfield Example (`greenfield-example/`)
Building a production-ready project from scratch and extracting it as a template.

**Project**: GraphQL API with Apollo Server, TypeScript, Prisma
**Journey**: Zero → Production-ready → Template → Reusable

**Demonstrates**:
- Using Taskwright workflow from day one
- Building with quality gates (80% coverage, 78/100 architecture)
- Extracting proven patterns as template
- Reusing for multiple projects

**Learn More**: [Greenfield Example README](greenfield-example/README.md)

### 4. Workflow Example (`workflow-example/`)
End-to-end demonstration of complete Taskwright workflow.

**Project**: Todo API with authentication
**Workflow**: Template init → Task creation → Quality gates → Completion

**Demonstrates**:
- All workflow phases (2 → 2.5 → 2.7 → 3 → 4 → 4.5 → 5 → 5.5)
- Architectural review in action
- Test enforcement loop
- Task refinement
- Complete task lifecycle

**Learn More**: [Workflow Example README](workflow-example/README.md)

## Quick Start

### Prerequisites
- Taskwright installed ([Installation Guide](https://github.com/yourusername/taskwright))
- Node.js 18+ / Python 3.11+ / Go 1.21+ (depending on example)

### Run an Example

```bash
# Clone this repository
git clone https://github.com/yourusername/taskwright-examples.git
cd taskwright-examples

# Choose an example
cd template-demos/react-typescript-demo

# Follow example's README
cat README.md
```

## Learning Path

**New to Taskwright?**
1. Start with **Workflow Example** → Understand complete process
2. Try **Template Demos** → See different tech stacks
3. Explore **Custom Template Example** → Learn template extraction
4. Build with **Greenfield Example** → Apply to your own projects

**Experienced User?**
- Explore examples for inspiration
- Reference patterns in your own projects
- Use as templates for demos or training

## Documentation

- [Main Documentation](https://github.com/yourusername/taskwright)
- [Template Philosophy](https://github.com/yourusername/taskwright/docs/guides/template-philosophy.md)
- [Workflow Guide](https://github.com/yourusername/taskwright/docs/guides/taskwright-workflow.md)

## Contributing

Found an issue or have an improvement?
- Open an issue: [Issues](https://github.com/yourusername/taskwright-examples/issues)
- Submit a PR: [Pull Requests](https://github.com/yourusername/taskwright-examples/pulls)

## License

MIT License - See [LICENSE](LICENSE) for details.

## Related Projects

- [Taskwright](https://github.com/yourusername/taskwright) - Main project
- [RequireKit](https://github.com/requirekit/require-kit) - Requirements management (pairs with Taskwright)

---

**Questions?** Open a [discussion](https://github.com/yourusername/taskwright-examples/discussions) or join our [community](link-to-community).
```

### Phase 2: Organize Template Demos

**Copy and Organize**:
```bash
cd ~/projects/taskwright-examples/template-demos

# Copy demos from TASK-069
cp -r ~/taskwright-demos/core-templates/* .

# Structure:
# template-demos/
# ├── react-typescript-demo/
# ├── fastapi-python-demo/
# ├── nextjs-fullstack-demo/
# ├── react-fastapi-monorepo-demo/
# └── default-demo/
```

**Create Template Demos README**:
```markdown
# Template Demos

Demonstrations of all Taskwright core templates with working examples.

## Overview

Each demo shows a fully initialized project ready to run and develop.

## Available Demos

### 1. React + TypeScript (`react-typescript-demo/`)

**Template**: `react-typescript`
**Project**: Task Dashboard
**Description**: Beautiful task dashboard built with React, TypeScript, and Tailwind CSS

**Tech Stack**:
- React 18 + TypeScript
- Vite (build tool)
- Tailwind CSS (styling)
- Vitest + React Testing Library (testing)
- Playwright (E2E testing)

**Quick Start**:
```bash
cd react-typescript-demo
npm install
npm run dev
# Visit http://localhost:5173
```

**Test**:
```bash
npm test              # Unit tests
npm run test:e2e      # E2E tests
npm run test:coverage # Coverage report
```

---

### 2. FastAPI + Python (`fastapi-python-demo/`)

**Template**: `fastapi-python`
**Project**: Task API
**Description**: RESTful API for task management built with FastAPI

**Tech Stack**:
- FastAPI + Python 3.11+
- SQLAlchemy (ORM)
- Alembic (migrations)
- Pydantic (validation)
- pytest (testing)

**Quick Start**:
```bash
cd fastapi-python-demo
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.task_api.main:app --reload
# Visit http://127.0.0.1:8000/docs
```

**Test**:
```bash
pytest tests/ -v --cov=src --cov-report=term
```

---

[Continue for all 5 templates...]

## Comparison Matrix

| Feature | react-typescript | fastapi-python | nextjs-fullstack | react-fastapi-monorepo | default |
|---------|------------------|----------------|------------------|------------------------|---------|
| Type | Frontend | Backend | Full-stack | Monorepo | Agnostic |
| Setup Time | 2 min | 3 min | 4 min | 5 min | 2 min |
| First Run | 30 sec | 1 min | 1 min | 2 min | 1 min |
| Test Coverage | 85% | 88% | 82% | 87% | Varies |
| Quality Score | 9+/10 | 9+/10 | 9+/10 | 9.2/10 | 8+/10 |
| Best For | SPAs | APIs | SSR Apps | Full-stack | Any language |

## Next Steps

After exploring these demos:
1. Choose a template for your project
2. Run `taskwright init [template-name]`
3. Start building with `/task-create` and `/task-work`

## Related Examples

- [Custom Template Example](../custom-template-example/) - Extract your own templates
- [Greenfield Example](../greenfield-example/) - Build from scratch
- [Workflow Example](../workflow-example/) - Complete workflow demo
```

**Create Individual READMEs**:
```bash
# For each demo, create detailed README with:
# - Project description
# - Prerequisites
# - Installation steps
# - Running instructions
# - Testing instructions
# - Project structure
# - Key features demonstrated
# - Next steps
```

### Phase 3: Organize Custom Template Example

**Copy and Enhance**:
```bash
cd ~/projects/taskwright-examples/custom-template-example

# Copy from TASK-070
cp -r ~/template-test-workspace/realworld-react-redux-template .

# Structure:
# custom-template-example/
# ├── source-codebase/          # Original RealWorld React
# ├── extracted-template/       # Generated template
# ├── example-project-1/        # blog-platform
# ├── example-project-2/        # forum-app
# ├── docs/
# │   ├── extraction-process.md
# │   ├── validation-report.md
# │   └── before-after-comparison.md
# └── README.md
```

**Create README**:
```markdown
# Custom Template Example

Complete example of extracting a custom template from an existing codebase using Taskwright's `/template-create` command.

## Overview

This example demonstrates:
1. Selecting a suitable source codebase (RealWorld React + Redux)
2. Preparing the codebase for extraction
3. Using `/template-create --validate` to extract template
4. Reviewing and enhancing the template
5. Using the template to create multiple projects

## What's Included

### Source Codebase (`source-codebase/`)
The original RealWorld React + Redux implementation:
- **Size**: ~8,500 LOC
- **Quality**: Production-ready
- **Patterns**: Redux, React Router, JWT auth
- **Tests**: 70+ tests

### Extracted Template (`extracted-template/`)
Generated template with quality score 8.5/10:
- Placeholder system for customization
- Pattern documentation in CLAUDE.md
- Validation report showing quality metrics
- Ready to use with `taskwright init`

### Example Projects
Two projects initialized from the template:

**blog-platform** (`example-project-1/`):
- News/blogging platform
- Customized for blog-specific features
- Independent from source

**forum-app** (`example-project-2/`):
- Community forum application
- Customized for forum features
- Independent from source and project 1

## Quick Start

### 1. Review Source Codebase
```bash
cd source-codebase
npm install
npm test
npm run dev
```

### 2. See Extracted Template
```bash
cd ../extracted-template
cat validation-report.md  # Quality: 8.5/10
cat CLAUDE.md             # Pattern documentation
cat manifest.json         # Placeholder definitions
```

### 3. Try Template
```bash
# Install template (if not already in Taskwright)
cp -r extracted-template ~/.agentecflow/templates/realworld-react-redux

# Initialize new project
mkdir my-app
cd my-app
taskwright init realworld-react-redux
```

### 4. Compare Example Projects
```bash
# See how same template creates different apps
diff example-project-1/package.json example-project-2/package.json
# Notice: Same structure, different names/descriptions
```

## Process Documentation

### Extraction Process
See [docs/extraction-process.md](docs/extraction-process.md) for step-by-step guide.

### Validation Report
See [docs/validation-report.md](docs/validation-report.md) for quality analysis.

### Before/After Comparison
See [docs/before-after-comparison.md](docs/before-after-comparison.md) for transformation details.

## Key Lessons

1. **Start with Quality**: Template quality = Source quality
2. **Clean Thoroughly**: Remove artifacts, secrets, project-specific code
3. **Validate Rigorously**: Use `--validate` flag for quality assurance
4. **Test Reusability**: Initialize 2+ projects to verify
5. **Document Patterns**: CLAUDE.md helps users understand template

## Metrics

**Time Investment**:
- Source selection: 1 hour
- Preparation: 30 minutes
- Extraction: 5 minutes
- Enhancement: 1 hour
- Testing: 30 minutes
- **Total**: ~3 hours

**Value Delivered**:
- Reusable template for infinite projects
- Quality validated: 8.5/10
- Time saved per project: ~40 hours

**ROI**: Break-even at 1st new project, exponential after

## Next Steps

- Try extracting a template from your own codebase
- Read [Template Extraction Best Practices](../../docs/template-extraction-best-practices.md)
- Join [Taskwright community](link) to share your templates
```

### Phase 4: Organize Greenfield Example

**Copy and Document**:
```bash
cd ~/projects/taskwright-examples/greenfield-example

# Copy from TASK-071
cp -r ~/projects/graphql-api-starter .

# Structure:
# greenfield-example/
# ├── graphql-api-starter/       # Original project
# ├── extracted-template/        # Template created from project
# ├── example-usage-1/           # blog-api (from template)
# ├── example-usage-2/           # product-api (from template)
# ├── docs/
# │   ├── build-log.md          # Day-by-day development
# │   ├── task-history/          # All task files
# │   ├── quality-metrics.md
# │   └── greenfield-to-template-guide.md
# └── README.md
```

**Create README** (similar structure focusing on greenfield journey)

### Phase 5: Organize Workflow Example

**Copy and Document**:
```bash
cd ~/projects/taskwright-examples/workflow-example

# Copy from TASK-072
cp -r ~/taskwright-demos/end-to-end-workflow/todo-api .

# Structure:
# workflow-example/
# ├── todo-api/                  # Complete Todo API
# ├── tasks/                     # All 5 task files
# ├── docs/
# │   ├── workflow-phases.md    # Explanation of each phase
# │   ├── quality-gates.md      # Quality gate details
# │   ├── task-execution-logs/  # Detailed logs per task
# │   └── state-transitions.md  # Task state diagram
# └── README.md
```

### Phase 6: Add CI/CD for Demo Verification

**Create GitHub Actions**:
```yaml
# .github/workflows/verify-demos.yml
name: Verify Demo Projects

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    # Run weekly to catch dependency issues
    - cron: '0 0 * * 0'

jobs:
  verify-react-typescript:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      - name: Install and test
        working-directory: template-demos/react-typescript-demo
        run: |
          npm install
          npm test
          npm run build

  verify-fastapi-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install and test
        working-directory: template-demos/fastapi-python-demo
        run: |
          python -m venv venv
          source venv/bin/activate
          pip install -r requirements.txt
          pytest tests/ -v --cov=src

  # Add jobs for all demos...

  verify-workflow-example:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install and test
        working-directory: workflow-example/todo-api
        run: |
          python -m venv venv
          source venv/bin/activate
          pip install -r requirements.txt
          pytest tests/ -v --cov=src
```

### Phase 7: Publish to GitHub

**Commit and Push**:
```bash
cd ~/projects/taskwright-examples

# Add all files
git add .

# Create commit
git commit -m "Initial commit: Taskwright examples repository

Includes:
- Template demos (5 core templates)
- Custom template extraction example
- Greenfield project example
- End-to-end workflow example

All demos tested and verified working.
Quality scores: 8-9.2/10 across all examples."

# Create GitHub repository (via gh CLI or web)
gh repo create taskwright-examples --public --source=. --remote=origin

# Push
git push -u origin main

# Create first release
git tag -a v1.0.0 -m "Release 1.0.0: Initial examples"
git push origin v1.0.0
```

**Add Topics**:
```bash
# Via GitHub web interface or CLI
gh repo edit --add-topic taskwright
gh repo edit --add-topic examples
gh repo edit --add-topic templates
gh repo edit --add-topic quality-gates
gh repo edit --add-topic ai-assisted-development
gh repo edit --add-topic typescript
gh repo edit --add-topic python
gh repo edit --add-topic fastapi
gh repo edit --add-topic react
gh repo edit --add-topic nextjs
```

### Phase 8: Create Specialized Repositories

**Option 1: Taskwright RealWorld Template**:
```bash
# Extract custom template example into standalone repo
cd ~/projects
git clone https://github.com/yourusername/taskwright-examples.git temp
cd temp/custom-template-example/extracted-template

# Create new repo
mkdir ~/projects/taskwright-realworld-template
cp -r . ~/projects/taskwright-realworld-template
cd ~/projects/taskwright-realworld-template

# Polish and publish
git init
# Add comprehensive README, documentation
git add .
git commit -m "Taskwright template based on RealWorld React + Redux"
gh repo create taskwright-realworld-template --public --source=.
git push -u origin main
```

**Option 2: Taskwright GraphQL Starter**:
```bash
# Similar process for greenfield GraphQL template
# Make it a standalone, production-ready template repo
```

### Phase 9: Update Main Project Documentation

**Update Taskwright README.md**:
```markdown
## Examples

Want to see Taskwright in action? Check out our comprehensive examples:

**[taskwright-examples](https://github.com/yourusername/taskwright-examples)** - Main examples repository:
- ✅ All 5 core templates demonstrated
- ✅ Custom template extraction walkthrough
- ✅ Greenfield project example
- ✅ End-to-end workflow demonstration

**Specialized Templates**:
- [taskwright-realworld-template](https://github.com/yourusername/taskwright-realworld-template) - RealWorld React + Redux template
- [taskwright-graphql-starter](https://github.com/yourusername/taskwright-graphql-starter) - GraphQL API starter template
```

**Update CLAUDE.md**:
```markdown
## Examples and Demos

For comprehensive examples, see:
- **Main Repository**: [taskwright-examples](https://github.com/yourusername/taskwright-examples)
- **Template Demos**: See all 5 core templates in action
- **Custom Template Example**: Learn template extraction from existing code
- **Greenfield Example**: Build from scratch with quality gates
- **Workflow Example**: Complete task lifecycle demonstration
```

---

## Acceptance Criteria

### Repository Structure
- [ ] Main repository created and organized
- [ ] All 4 example categories included
- [ ] Comprehensive main README
- [ ] Individual READMEs for each example
- [ ] Documentation directory with guides

### Demo Quality
- [ ] All demos tested and working
- [ ] Dependencies install cleanly
- [ ] Tests pass for all demos
- [ ] Applications run successfully
- [ ] No hardcoded values or secrets

### Documentation
- [ ] Main README explains all examples
- [ ] Quick start guides for each demo
- [ ] Comparison matrices created
- [ ] Process documentation complete
- [ ] Learning path suggested

### CI/CD
- [ ] GitHub Actions workflows created
- [ ] All demos verified by CI
- [ ] Weekly scheduled checks configured
- [ ] Badge added to README showing status

### Publication
- [ ] Repository published to GitHub
- [ ] Topics added for discoverability
- [ ] First release tagged (v1.0.0)
- [ ] License file added
- [ ] Contributing guide added

### Integration
- [ ] Main Taskwright repo updated with links
- [ ] CLAUDE.md updated with examples
- [ ] Specialized repos created (2+)
- [ ] Cross-references added

---

## Deliverables

1. **Main Repository** (`taskwright-examples`) - Published on GitHub
2. **Template Demos** (5 working demos)
3. **Custom Template Example** (Complete walkthrough)
4. **Greenfield Example** (Build → Template journey)
5. **Workflow Example** (End-to-end demo)
6. **Comprehensive Documentation** (READMEs, guides, diagrams)
7. **CI/CD Pipeline** (Automated verification)
8. **Specialized Repositories** (2+ standalone templates)
9. **Updated Main Docs** (Links and references)

---

## Success Metrics

**Quantitative**:
- Repositories created: 3+ (main + 2 specialized)
- Demos working: 100% (all functional)
- CI/CD passing: 100% (all green)
- Documentation completeness: 100%
- Links updated: 100%

**Qualitative**:
- Professional presentation
- Easy to navigate and understand
- Clear learning path
- Discoverable on GitHub
- Valuable for marketing and education

---

## Related Tasks

- **TASK-069**: Demo/Test - Core Template Usage (source)
- **TASK-070**: Demo/Test - Custom Template from Existing Codebase (source)
- **TASK-071**: Demo/Test - Greenfield Template Creation (source)
- **TASK-072**: Demo/Test - End-to-End Workflow (source)

---

**Document Status**: Ready for Implementation
**Created**: 2025-01-10
**Depends On**: TASK-069, TASK-070, TASK-071, TASK-072 (for demo content)
