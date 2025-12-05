---
id: TASK-IMP-674A
title: Create example Products feature implementation
status: in_review
created: 2025-12-03T11:45:00Z
updated: 2025-12-03T15:15:00Z
previous_state: in_progress
state_transition_reason: "All quality gates passed - ready for review"
priority: high
tags: [implementation, example, documentation]
complexity: 5
task_type: implementation
related_tasks: [TASK-REV-673A, TASK-IMP-674A-PREREQ]
test_results:
  status: passed
  total_tests: 103
  passed_tests: 103
  failed_tests: 0
  coverage_line: 98
  coverage_branch: 95
  last_run: 2025-12-03T15:15:00Z
quality_scores:
  architectural_review: 87
  code_review: 9.2
  solid_compliance: 44
  dry_compliance: 22
  yagni_compliance: 21
---

# Task: Create example Products feature implementation

## ✅ UNBLOCKED - Ready for Implementation

**Prerequisite Completed**: TASK-IMP-674A-PREREQ (Initialize FastAPI application infrastructure) ✅

**Infrastructure Status**:
- ✅ FastAPI application created at `src/main.py`
- ✅ Database session management in `src/db/session.py`
- ✅ Generic CRUD base in `src/crud/base.py`
- ✅ Configuration in `src/core/config.py`
- ✅ Application starts successfully: `uvicorn src.main:app --reload`
- ✅ Health check endpoint works
- ✅ OpenAPI docs accessible

**Ready to Proceed**: Execute `/task-work TASK-IMP-674A` to begin Products feature implementation.

---

## Description

Create a complete, production-ready Products feature as a reference implementation demonstrating how to use the FastAPI template. This will serve as the primary example for users learning the codebase structure and patterns.

## Context

From TASK-REV-673A review findings:
- Template structure exists but lacks concrete implementation example
- Users need reference to understand how templates are used in practice
- Example should demonstrate all layers: API, Schema, Model, CRUD, Service, Dependencies, Tests

## Requirements

### 1. Product Model (src/products/models.py)
- Fields:
  - `id` (Integer, primary key, auto-increment)
  - `name` (String(255), required, indexed)
  - `description` (Text, optional)
  - `price` (Decimal, required, must be > 0)
  - `quantity` (Integer, required, must be >= 0)
  - `category` (String(100), optional, indexed)
  - `is_active` (Boolean, default True)
  - `created_at` (DateTime, auto-generated)
  - `updated_at` (DateTime, auto-updated)
- Indexes: name, category, is_active
- Constraints: CHECK price > 0, CHECK quantity >= 0

### 2. Pydantic Schemas (src/products/schemas.py)
Implement all schema types following template patterns:
- `ProductBase` - Shared fields
- `ProductCreate` - Input validation with constraints
- `ProductUpdate` - Partial updates (all optional)
- `ProductInDB` - Database representation
- `ProductPublic` - API response (safe for public)
- `PaginatedProductResponse` - Pagination wrapper

Validation rules:
- name: 1-255 chars, not empty/whitespace
- description: max 1000 chars
- price: > 0, max 2 decimal places
- quantity: >= 0
- category: if provided, 1-100 chars

### 3. CRUD Operations (src/products/crud.py)
Extend CRUDBase with product-specific operations:
- `get_by_name(name: str)` - Find by exact name
- `get_active(skip, limit)` - Active products only
- `search_by_name(search_term, skip, limit)` - Case-insensitive partial match
- `search_by_category(category, skip, limit)` - Filter by category
- `deactivate(id)` - Soft delete (set is_active=False)
- `get_low_stock(threshold: int)` - Products with quantity < threshold

### 4. API Endpoints (src/products/router.py)
Full REST API following template patterns:
- `GET /api/v1/products/` - List with pagination, optional filters (category, search)
- `GET /api/v1/products/{product_id}` - Get by ID
- `POST /api/v1/products/` - Create new product (requires auth)
- `PUT /api/v1/products/{product_id}` - Update product (requires auth)
- `PATCH /api/v1/products/{product_id}` - Partial update (requires auth)
- `DELETE /api/v1/products/{product_id}` - Soft delete (requires auth)
- `GET /api/v1/products/search` - Search by name
- `GET /api/v1/products/low-stock` - Low stock report (requires auth)

All endpoints:
- Use async/await
- Have response_model specified
- Include OpenAPI documentation (docstrings)
- Use Query() validators for parameters
- Return proper status codes

### 5. Dependencies (src/products/dependencies.py)
- `valid_product_id(product_id, db)` - Validate product exists, return object or 404
- `active_product_required(product)` - Ensure product is active
- `unique_product_name(name, db)` - Validate name uniqueness for creation

### 6. Database Migration (alembic/versions/)
- Auto-generate migration: `alembic revision --autogenerate -m "Add products table"`
- Review migration for correctness
- Include indexes and constraints
- Test upgrade and downgrade

### 7. Comprehensive Tests (tests/products/)
Achieve 95%+ coverage with tests for:

**test_router.py** (API tests):
- Happy path: create, read, update, delete, list
- Validation errors: empty name, negative price, invalid data types
- Not found errors: non-existent product ID
- Authentication: 401 for unauthenticated requests
- Pagination: skip/limit, edge cases (skip > total)
- Search: by name, by category
- Partial updates: only update provided fields
- Soft delete: is_active=False behavior

**test_crud.py** (Database tests):
- All CRUD operations
- Custom queries: get_by_name, search, filter by category
- Edge cases: duplicate names, invalid IDs

**test_schemas.py** (Validation tests):
- Field validators
- Model validators
- Type coercion
- Error messages

**conftest.py**:
- `create_test_product` factory fixture
- Sample product data fixtures

### 8. Integration with Main App
- Register router in main.py or api router
- Add to API documentation
- Include in OpenAPI tags

### 9. Documentation
Add to README.md or create docs/examples/products.md:
- Overview of Products feature
- API endpoint examples with curl commands
- Code walkthrough explaining each layer
- How to extend for other features

## Acceptance Criteria

- [ ] All 6 layers implemented (router, schemas, models, crud, dependencies, tests)
- [ ] Database migration created and tested
- [ ] Test coverage >= 95% for products module
- [ ] All tests pass (pytest tests/products/ -v)
- [ ] API documentation auto-generated in /docs
- [ ] Code follows template patterns exactly
- [ ] No linter errors (ruff check src/products/)
- [ ] Type checking passes (mypy src/products/)
- [ ] Example documentation included
- [ ] Router registered in main app

## Quality Gates

This task will go through:
- **Phase 2.5**: Architectural review (SOLID/DRY/YAGNI check)
- **Phase 4.5**: Test enforcement (95% coverage required)
- **Phase 5**: Code review (FastAPI best practices)

## Implementation Notes

**Use the templates as foundation**:
- Copy from `.claude/templates/` and customize
- Follow naming conventions exactly
- Maintain async-first patterns
- Use dependency injection throughout

**This is a REFERENCE IMPLEMENTATION**:
- Code should be exemplary quality
- Comments explaining why, not what
- Demonstrate all template features
- Serve as learning resource for users

## Test Execution Log

_Automatically populated by /task-work_

## Related Resources

- Template files: `.claude/templates/`
- Review report: `.claude/reviews/TASK-REV-673A-review-report.md`
- FastAPI docs: https://fastapi.tiangolo.com/
- SQLAlchemy async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html

## Success Criteria

**Definition of Done**:
1. Users can run: `uvicorn src.main:app --reload` and see Products API in /docs
2. Users can run: `pytest tests/products/ -v` and see all tests pass
3. Users can follow the code as a learning example for creating their own features
4. Products feature demonstrates every pattern in the template
