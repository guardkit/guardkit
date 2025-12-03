# TASK-069: Demo/Test - Core Template Usage and Evaluation

**Created**: 2025-01-10
**Priority**: High
**Type**: Testing & Demo
**Parent**: Template Strategy Validation
**Status**: backlog
**Complexity**: Medium (5/10)
**Estimated Effort**: 4-6 hours
**Dependencies**: None

---

## Problem Statement

With 5 high-quality core templates now available, we need to:
1. **Test** that each template initializes correctly and provides a solid foundation
2. **Document** the experience for blog posts and YouTube videos
3. **Validate** that templates meet their stated quality scores (8-9+/10)
4. **Create** reusable demo content showing real-world usage

**Current State**: Templates exist but haven't been thoroughly tested from an end-user perspective or documented for demos.

**Desired State**: Each core template tested, validated, and documented with demo content ready for blog/video production.

---

## Context

**Core Templates to Test**:
1. **react-typescript** - Frontend best practices (9+/10)
2. **fastapi-python** - Backend API patterns (9+/10)
3. **nextjs-fullstack** - Full-stack application (9+/10)
4. **react-fastapi-monorepo** - Full-stack monorepo (9.2/10)
5. **default** - Language-agnostic foundation (8+/10)

**Demo Objectives**:
- Show how easy it is to start a new project with GuardKit templates
- Demonstrate the quality and structure of each template
- Highlight template-specific features and patterns
- Document common workflows for new users

**Testing Objectives**:
- Verify template initialization works correctly
- Validate project structure matches expectations
- Test that dependencies install cleanly
- Verify tests run successfully
- Confirm quality matches stated scores

---

## Objectives

### Primary Objective
Test and document all 5 core templates through initialization, validation, and real-world usage scenarios, producing demo content for blogs and videos.

### Success Criteria
- [ ] All 5 templates initialized successfully in test directories
- [ ] Each template's dependencies install without errors
- [ ] Each template's tests execute successfully
- [ ] Project structure validated for each template
- [ ] Demo script created for each template (blog-ready)
- [ ] Video outline created for each template
- [ ] Screenshots captured for documentation
- [ ] Common issues documented with solutions
- [ ] Quality scores verified (actual vs claimed)
- [ ] User experience notes documented

---

## Implementation Scope

### Phase 1: Setup Test Environment

**Create Test Workspace**:
```bash
# Create demo workspace
mkdir -p ~/guardkit-demos/core-templates
cd ~/guardkit-demos/core-templates

# Create subdirectories for each template
mkdir react-typescript-demo
mkdir fastapi-python-demo
mkdir nextjs-fullstack-demo
mkdir react-fastapi-monorepo-demo
mkdir default-demo
```

### Phase 2: Test react-typescript Template

**Initialize Template**:
```bash
cd ~/guardkit-demos/core-templates/react-typescript-demo
guardkit init react-typescript

# Expected prompts:
# ProjectName: TaskDashboard
# project-name: task-dashboard
# description: A beautiful task dashboard built with React and TypeScript
# author: Demo User
```

**Validate Installation**:
```bash
# Install dependencies
npm install

# Run development server
npm run dev
# Expected: Server starts on http://localhost:5173

# Run tests
npm test
# Expected: All tests pass

# Run build
npm run build
# Expected: Build succeeds

# Check coverage
npm test -- --coverage
# Expected: ≥80% coverage
```

**Document Experience**:
- Take screenshots of:
  - Terminal showing successful init
  - Project structure in VS Code
  - Running dev server
  - Test results
  - Built application
- Create notes on:
  - Time to first running app
  - Pain points or confusions
  - Highlights and strengths
  - Suggested improvements

### Phase 3: Test fastapi-python Template

**Initialize Template**:
```bash
cd ~/guardkit-demos/core-templates/fastapi-python-demo
guardkit init fastapi-python

# Expected prompts:
# ProjectName: TaskAPI
# project_name: task_api
# description: A RESTful API for task management built with FastAPI
# author: Demo User
```

**Validate Installation**:
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn src.task_api.main:app --reload
# Expected: Server starts on http://127.0.0.1:8000

# Test API endpoints
curl http://127.0.0.1:8000/docs
# Expected: Swagger UI accessible

# Run tests
pytest tests/ -v --cov=src --cov-report=term
# Expected: All tests pass, ≥80% coverage
```

**Document Experience**:
- Screenshots of:
  - Virtual environment setup
  - Swagger/OpenAPI documentation
  - Test results with coverage
  - Running API server
- Notes on Python best practices demonstrated

### Phase 4: Test nextjs-fullstack Template

**Initialize Template**:
```bash
cd ~/guardkit-demos/core-templates/nextjs-fullstack-demo
guardkit init nextjs-fullstack

# Expected prompts:
# ProjectName: TaskManager
# project-name: task-manager
# description: A full-stack task management app built with Next.js
# author: Demo User
```

**Validate Installation**:
```bash
# Install dependencies
npm install

# Setup database (if template includes)
npm run db:migrate

# Run development server
npm run dev
# Expected: Server starts on http://localhost:3000

# Run tests
npm test
# Expected: All tests pass

# Test API routes
curl http://localhost:3000/api/health
# Expected: 200 OK response
```

**Document Experience**:
- Screenshots of:
  - Next.js App Router structure
  - Server components vs client components
  - API routes
  - Database integration
- Notes on full-stack patterns

### Phase 5: Test react-fastapi-monorepo Template

**Initialize Template**:
```bash
cd ~/guardkit-demos/core-templates/react-fastapi-monorepo-demo
guardkit init react-fastapi-monorepo

# Expected prompts:
# ProjectName: TaskWorkspace
# project-name: task-workspace
# description: A full-stack monorepo with React frontend and FastAPI backend
# author: Demo User
```

**Validate Installation**:
```bash
# Frontend setup
cd frontend
npm install
npm run dev &
# Expected: Frontend on http://localhost:5173

# Backend setup
cd ../backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload &
# Expected: Backend on http://127.0.0.1:8000

# Run tests (frontend)
cd ../frontend
npm test

# Run tests (backend)
cd ../backend
pytest tests/ -v --cov=src
```

**Document Experience**:
- Screenshots of:
  - Monorepo structure
  - Frontend-backend communication
  - Concurrent development
  - Shared types/contracts
- Notes on monorepo benefits

### Phase 6: Test default Template

**Initialize Template (Go Example)**:
```bash
cd ~/guardkit-demos/core-templates/default-demo
guardkit init default

# Expected prompts:
# ProjectName: TaskCLI
# project-name: task-cli
# description: A command-line task management tool
# author: Demo User
# language: go
```

**Validate Installation**:
```bash
# Initialize Go module
go mod init github.com/demouser/task-cli

# Build project
go build -o task-cli ./cmd/task-cli

# Run tests
go test ./... -v -cover
# Expected: Tests pass, coverage reported

# Run application
./task-cli --help
# Expected: Help text displayed
```

**Document Experience**:
- Screenshots of:
  - Language-agnostic structure
  - Go module setup
  - Test execution
  - Built binary
- Notes on flexibility for different languages

### Phase 7: Create Demo Content

**For Each Template, Create**:

1. **Blog Post Outline** (`{template}-blog-outline.md`):
   ```markdown
   # Getting Started with {Template Name}

   ## Introduction
   - What is GuardKit?
   - Why use templates?
   - What this template provides

   ## Prerequisites
   - System requirements
   - Tools needed

   ## Step-by-Step Guide
   1. Install GuardKit
   2. Initialize template
   3. Explore project structure
   4. Run development server
   5. Run tests
   6. Make first changes

   ## Key Features
   - Pattern 1
   - Pattern 2
   - Pattern 3

   ## Next Steps
   - Creating tasks with /task-create
   - Using /task-work
   - Customizing the template

   ## Conclusion
   - Summary
   - Call to action
   ```

2. **Video Script** (`{template}-video-script.md`):
   ```markdown
   # {Template Name} - Video Script

   ## Opening (0:00-0:30)
   - Hook: "Want to build a production-ready {type} in under 5 minutes?"
   - Introduce GuardKit
   - What we'll cover

   ## Demo (0:30-4:00)
   - Show installation
   - Initialize template
   - Walk through structure
   - Run dev server
   - Show key features
   - Run tests

   ## Explanation (4:00-6:00)
   - Explain patterns used
   - Highlight quality features
   - Show where to learn more

   ## Closing (6:00-7:00)
   - Recap
   - Next steps
   - Call to action
   ```

3. **Screenshots** (`screenshots/{template}/`):
   - 01-installation.png
   - 02-initialization.png
   - 03-project-structure.png
   - 04-running-app.png
   - 05-test-results.png
   - 06-built-output.png

4. **Comparison Matrix** (`template-comparison.md`):
   ```markdown
   | Feature | react-typescript | fastapi-python | nextjs-fullstack | react-fastapi-monorepo | default |
   |---------|------------------|----------------|------------------|------------------------|---------|
   | Type | Frontend | Backend | Full-stack | Monorepo | Agnostic |
   | Quality | 9+/10 | 9+/10 | 9+/10 | 9.2/10 | 8+/10 |
   | Setup Time | 2 min | 3 min | 4 min | 5 min | 2 min |
   | Test Coverage | 85% | 88% | 82% | 87% | - |
   | Best For | SPAs | APIs | SSR Apps | Full-stack | Any language |
   ```

### Phase 8: Document Issues and Solutions

**Create Issues Log** (`template-testing-issues.md`):
```markdown
# Template Testing Issues and Solutions

## react-typescript
### Issue 1: [Description]
- **Severity**: Low/Medium/High
- **Solution**: [How to fix]
- **Prevention**: [How to avoid]

## fastapi-python
### Issue 1: [Description]
...

## Common Issues
### Issue 1: [Description across templates]
...
```

### Phase 9: Create Demo Repository

**Setup Demo Repo**:
```bash
# Create GitHub repo: guardkit-template-demos
mkdir ~/guardkit-template-demos
cd ~/guardkit-template-demos

# Copy all demo projects
cp -r ~/guardkit-demos/core-templates/* .

# Add README
cat > README.md << 'EOF'
# GuardKit Template Demos

Example projects demonstrating GuardKit's core templates.

## Templates Demonstrated

1. **react-typescript-demo** - React + TypeScript frontend
2. **fastapi-python-demo** - FastAPI backend
3. **nextjs-fullstack-demo** - Next.js full-stack
4. **react-fastapi-monorepo-demo** - Full-stack monorepo
5. **default-demo** - Language-agnostic (Go example)

## Usage

Each directory contains a fully initialized project ready to run.

See individual README files for specific instructions.
EOF

# Initialize git
git init
git add .
git commit -m "Add GuardKit template demos"
```

---

## Acceptance Criteria

### Testing Requirements
- [ ] All 5 templates initialize without errors
- [ ] Dependencies install successfully for each template
- [ ] Development servers start successfully
- [ ] All tests pass for each template
- [ ] Builds complete successfully (where applicable)
- [ ] Coverage meets or exceeds stated thresholds
- [ ] Project structures match documentation

### Documentation Requirements
- [ ] Blog post outline created for each template
- [ ] Video script created for each template
- [ ] 6+ screenshots captured per template (30+ total)
- [ ] Template comparison matrix completed
- [ ] Issues and solutions documented
- [ ] User experience notes captured

### Demo Content Requirements
- [ ] Demo repository created and committed
- [ ] All demo projects functional and ready to run
- [ ] README files provide clear instructions
- [ ] Common workflows documented
- [ ] Best practices highlighted

### Quality Verification
- [ ] Actual quality matches claimed scores (±0.5)
- [ ] No critical issues discovered
- [ ] Performance meets expectations
- [ ] User experience is smooth and intuitive

---

## Deliverables

1. **Test Results** (`docs/testing/core-template-test-results.md`)
2. **Demo Scripts** (5 blog outlines + 5 video scripts)
3. **Screenshots** (30+ images organized by template)
4. **Template Comparison Matrix** (`docs/templates/template-comparison.md`)
5. **Issues Log** (`docs/testing/template-testing-issues.md`)
6. **Demo Repository** (GitHub: guardkit-template-demos)
7. **User Experience Report** (`docs/testing/template-ux-report.md`)

---

## Success Metrics

**Quantitative**:
- 5 templates tested: 100%
- Test pass rate: 100%
- Templates meeting quality claims: 100%
- Demo content created: 10 pieces (5 blogs + 5 videos)
- Screenshots captured: 30+

**Qualitative**:
- Clear understanding of each template's strengths
- Identification of any rough edges
- Confidence in recommending templates to users
- Ready-to-use demo content for marketing
- Improved documentation from real usage

---

## Related Tasks

- **TASK-070**: Demo/Test - Create Custom Template from Existing Codebase
- **TASK-071**: Demo/Test - Greenfield Project with Template Creation
- **TASK-072**: Demo/Test - End-to-End GuardKit Workflow
- **TASK-060-062**: Template creation tasks
- **TASK-065**: Clean installer

---

**Document Status**: Ready for Implementation
**Created**: 2025-01-10
**Depends On**: None (templates already exist)
