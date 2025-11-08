# TASK-058: Create Python FastAPI Reference Template

**Created**: 2025-01-08
**Priority**: High
**Type**: Feature
**Parent**: Template Strategy Overhaul
**Status**: Backlog
**Complexity**: 7/10 (Medium-High)
**Estimated Effort**: 5-7 days
**Dependencies**: TASK-043 (Extended Validation), TASK-044 (Template Validate), TASK-045 (AI-Assisted Validation), TASK-056 (Audit Complete), TASK-068 (Template Location Refactor)

---

## Problem Statement

Create a **reference implementation template** for Python FastAPI backend development from a production-proven exemplar repository. This template must demonstrate best practices, achieve 9+/10 quality score, and serve as a learning resource for API developers.

**Goal**: Create high-quality Python FastAPI template from [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices) repository using `/template-create`, validate to 9+/10 standard.

---

## Context

**Related Documents**:
- [Template Strategy Decision](../../docs/research/template-strategy-decision.md)
- [FastAPI Best Practices Repository](https://github.com/zhanymkanov/fastapi-best-practices)
- TASK-044: Template validation command
- TASK-056: Template audit findings

**Source Repository**:
- **URL**: https://github.com/zhanymkanov/fastapi-best-practices
- **Stars**: 12k+
- **Description**: FastAPI best practices and conventions from production startup experience
- **Stack**: FastAPI, SQLAlchemy, Alembic, Pydantic, pytest

**Why This Repository**:
- ✅ Production decisions from years of startup experience
- ✅ Scalable project structure (Netflix Dispatch-inspired)
- ✅ Dependency injection patterns
- ✅ Database migration with Alembic
- ✅ Async best practices
- ✅ 12k+ stars (community validation)

---

## Objectives

### Primary Objective
Create Python FastAPI reference template from fastapi-best-practices repository that achieves 9+/10 quality score.

### Success Criteria
- [x] Source repository cloned and analyzed
- [x] Template created using `/template-create` command
- [x] Template passes `/template-validate` with 9+/10 score
- [x] All 16 validation sections score 8+/10
- [x] Zero critical issues
- [x] README documents template architecture and patterns
- [x] Template installed in `installer/global/templates/fastapi-python/`
- [x] Documentation updated to reference new template

---

## Implementation Scope

**IMPORTANT: Claude Code Tool Usage**
This task requires you to **execute commands using the SlashCommand tool**, not just describe them. You will iteratively create, validate, refine, and re-validate the template until it achieves 9+/10 quality.

### Step 1: Clone and Analyze Source Repository

Use the **Bash tool** to clone and explore the source repository:

```bash
# Clone source repository
cd /tmp
git clone https://github.com/zhanymkanov/fastapi-best-practices.git
cd fastapi-best-practices

# Explore structure
tree -L 3
```

Use **Read tool** to analyze key files:
- Project structure (Netflix Dispatch-inspired)
- API route patterns (`app/api/routes/*.py`)
- CRUD operations (`app/crud/*.py`)
- Database models (`app/models/*.py`)
- Pydantic schemas (`app/schemas/*.py`)
- Testing patterns (`tests/*.py`)
- Dependency injection (`app/api/dependencies.py`)

### Step 2: Create Template Using `/template-create` Command

**Execute using SlashCommand tool**:

```
Use SlashCommand tool to invoke: /template-create --validate --output-location=repo
```

**Note**: The `--output-location=repo` (or `-o repo`) flag writes the template directly to `installer/global/templates/` for team/public distribution. This flag is required for reference templates that will be included in the Taskwright repository. (TASK-068 changed the default behavior to write to `~/.agentecflow/templates/` for personal use.)

The command will:
1. Run interactive Q&A (answer as specified below)
2. Analyze the fastapi-best-practices codebase
3. Generate manifest.json, settings.json, CLAUDE.md, templates/, agents/
4. Write directly to `installer/global/templates/fastapi-python/` (repo location)
5. Run extended validation (TASK-043)
6. Generate validation-report.md

**Q&A Answers**:
- **Template name**: fastapi-python
- **Template type**: Backend API
- **Primary language**: Python
- **Frameworks**: FastAPI, SQLAlchemy, Pydantic
- **Architecture patterns**: Layered, Repository pattern, Dependency injection
- **Testing**: pytest, pytest-asyncio, httpx
- **Generate custom agents**: Yes

**Expected Output**: Template created at `installer/global/templates/fastapi-python/` with initial validation score of 7-8/10

### Step 3: Review Initial Validation Report

Use **Read tool** to review the validation report:

```
Read: installer/global/templates/fastapi-python/validation-report.md
```

Identify issues in these categories:
- Placeholder consistency (target: 9+/10)
- Pattern fidelity (target: 9+/10)
- Documentation completeness (target: 9+/10)
- Agent validation (target: 9+/10)
- Manifest accuracy (target: 9+/10)

### Step 4: Comprehensive Audit with AI Assistance

**Execute using SlashCommand tool**:

```
Use SlashCommand tool to invoke: /template-validate installer/global/templates/fastapi-python --sections 1-16
```

This runs the 16-section audit framework with AI assistance for sections 8, 11, 12, 13.

**Expected Output**:
- Section-by-section scores
- Detailed findings report
- AI-generated strengths/weaknesses
- Critical issues (if any)
- Specific recommendations for improvement

### Step 5: Iterative Improvement Loop

Based on validation findings, use **Edit tool** or **Write tool** to improve the template:

**Common Improvements**:

1. **Enhance CLAUDE.md** (Use Edit tool):
   - Add FastAPI code examples
   - Document dependency injection patterns
   - Explain async/await best practices
   - Show database operation patterns
   - Document all agents with examples

2. **Improve Templates** (Use Edit/Write tools):
   - Add missing CRUD operation templates (Create, Read, Update, Delete, List)
   - Fix placeholder inconsistencies
   - Ensure pattern fidelity matches source
   - Add comprehensive test templates
   - Add API versioning patterns

3. **Enhance Agents** (Use Edit/Write tools):
   - Complete agent prompts
   - Add concrete examples
   - Document capabilities clearly
   - Ensure agents reference CLAUDE.md correctly

4. **Complete Manifest** (Use Edit tool):
   - Fill all metadata fields
   - Document all placeholders with patterns
   - Verify technology stack accuracy
   - Add quality scores from analysis

### Step 6: Re-validate After Improvements

**Execute using SlashCommand tool**:

```
Use SlashCommand tool to invoke: /template-validate installer/global/templates/fastapi-python --sections 10,11,16
```

(Re-run specific sections to verify improvements)

**Repeat Steps 5-6 until**:
- Overall score ≥9.0/10
- All 16 sections ≥8.0/10
- Zero critical issues
- Recommendation: APPROVE

### Step 7: Verify Template Location

Use **Bash tool**:

```bash
# Verify structure (template already in repo location)
ls -la installer/global/templates/fastapi-python/
```

### Step 8: Final Validation

**Execute using SlashCommand tool**:

```
Use SlashCommand tool to invoke: /template-validate installer/global/templates/fastapi-python --sections 1-16
```

**Acceptance Criteria**:
- Overall Score: ≥9.0/10
- Grade: A or A+
- All sections: ≥8.0/10
- Critical issues: 0
- Recommendation: APPROVE

### Step 9: Installation and Integration Testing

Use **Bash tool** to test the template:

```bash
# Install template globally
./installer/scripts/install.sh

# Test template initialization in clean directory
cd /tmp/test-fastapi-app
taskwright init fastapi-python

# Verify generated project runs and tests pass
cd /tmp/test-fastapi-app
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest                           # Must pass
mypy app/                        # No type errors
ruff check app/                  # No linting errors
uvicorn app.main:app --reload &  # Must start successfully
sleep 5
curl http://localhost:8000/api/v1/health  # Must return 200
```

If any tests fail, return to Step 5 and fix issues in the template.

---

## Template Structure (Expected)

```
installer/global/templates/fastapi-python/
├── manifest.json                    # Template metadata
├── settings.json                    # Naming conventions, patterns
├── CLAUDE.md                        # AI guidance for FastAPI
├── README.md                        # Human-readable documentation
├── templates/                       # Code generation templates
│   ├── api/
│   │   ├── router.py.template
│   │   ├── dependencies.py.template
│   │   └── schemas.py.template
│   ├── crud/
│   │   ├── crud-base.py.template
│   │   └── crud-entity.py.template
│   ├── models/
│   │   ├── model-base.py.template
│   │   └── model-entity.py.template
│   ├── schemas/
│   │   ├── schema-base.py.template
│   │   └── schema-entity.py.template
│   ├── services/
│   │   └── service-entity.py.template
│   ├── database/
│   │   ├── session.py.template
│   │   └── base.py.template
│   └── testing/
│       ├── conftest.py.template
│       ├── test-api.py.template
│       └── test-crud.py.template
└── agents/                          # Stack-specific AI agents
    ├── fastapi-specialist.md
    ├── fastapi-testing-specialist.md
    └── fastapi-database-specialist.md
```

---

## Key Patterns to Capture

From fastapi-best-practices repository, capture these patterns:

### 1. Project Structure
```python
# Netflix Dispatch-inspired structure
app/
├── api/
│   ├── routes/          # API routes by feature
│   ├── dependencies.py  # Dependency injection
│   └── errors.py        # Error handlers
├── core/
│   ├── config.py        # Settings/configuration
│   ├── security.py      # Authentication/authorization
│   └── logging.py       # Logging configuration
├── crud/                # Database operations
├── db/
│   ├── base.py
│   ├── session.py
│   └── migrations/      # Alembic migrations
├── models/              # SQLAlchemy models
├── schemas/             # Pydantic schemas
└── services/            # Business logic
```

### 2. Dependency Injection Pattern
```python
# Reusable dependency
from fastapi import Depends
from sqlalchemy.orm import Session

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Using dependency
@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    return crud.user.get(db, id=user_id)
```

### 3. CRUD Pattern
```python
# Base CRUD operations
from typing import Generic, TypeVar, Type
from pydantic import BaseModel
from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: int) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100):
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: CreateSchemaType):
        obj_data = obj_in.dict()
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
```

### 4. Testing Strategy
```python
# Pytest fixtures and async tests
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    response = await client.post(
        "/api/v1/users/",
        json={"email": "test@example.com", "password": "password"}
    )
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
```

---

## Acceptance Criteria

### Functional Requirements
- [ ] Template created from fastapi-best-practices using `/template-create`
- [ ] Template validates at 9+/10 score
- [ ] All 16 validation sections score 8+/10
- [ ] Zero critical issues in validation report
- [ ] Template generates working FastAPI project
- [ ] Generated project runs successfully
- [ ] Generated project tests pass

### Quality Requirements
- [ ] CLAUDE.md documents FastAPI patterns
- [ ] README comprehensive and clear
- [ ] manifest.json complete and accurate
- [ ] settings.json defines naming conventions
- [ ] Agents created (fastapi-specialist, fastapi-testing-specialist, fastapi-database-specialist)
- [ ] Templates cover common patterns (CRUD, API routes, database, tests)

### Documentation Requirements
- [ ] Template architecture documented
- [ ] Dependency injection explained
- [ ] Database patterns illustrated
- [ ] Testing strategy shown
- [ ] Best practices highlighted

---

## Testing Requirements

### Template Validation Tests
```bash
# Comprehensive validation
/template-validate installer/global/templates/fastapi-python

# Expected results:
# Overall Score: ≥9.0/10
# Grade: A or A+
# All sections: ≥8.0/10
# Critical issues: 0
# Recommendation: APPROVE
```

### Generated Project Tests
```bash
# Initialize project from template
taskwright init fastapi-python --output /tmp/test-fastapi-app

# Setup environment
cd /tmp/test-fastapi-app
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest
# Expected: All tests pass

# Run server
uvicorn app.main:app --reload &
sleep 5

# Test API endpoints
curl http://localhost:8000/api/v1/health
# Expected: {"status": "healthy"}

# Type checking
mypy app/
# Expected: No type errors

# Linting
ruff check app/
# Expected: No linting errors
```

---

## Risk Mitigation

### Risk 1: fastapi-best-practices Structure Too Opinionated
**Mitigation**: Adapt during template creation, focus on core patterns, document alternatives

### Risk 2: Validation Score Below 9/10
**Mitigation**: Iterative improvement cycle, use `/template-validate` feedback, apply TASK-045 AI assistance

### Risk 3: Generated Project Dependencies Conflict
**Mitigation**: Test with fresh virtual environment, pin dependency versions, provide requirements.txt

---

## Success Metrics

**Quantitative**:
- Template validation score: ≥9.0/10
- All validation sections: ≥8.0/10
- Critical issues: 0
- Generated project test pass: 100%
- Generated project runs successfully: 100%

**Qualitative**:
- Template demonstrates FastAPI best practices
- Documentation is comprehensive and clear
- Patterns are production-ready
- Developers can learn from template
- Template serves as reference implementation

---

## Related Tasks

- **TASK-044**: Prerequisite - Template validation command
- **TASK-056**: Prerequisite - Template audit (informs improvements)
- **TASK-057**: Create React reference template (parallel effort)
- **TASK-059**: Create Next.js reference template (parallel effort)
- **TASK-060**: Remove low-quality templates (clears space)
- **TASK-061**: Update documentation (includes new template)

---

**Document Status**: Ready for Implementation
**Created**: 2025-01-08
**Parent Epic**: Template Strategy Overhaul
