# Implementation Plan: Add FastAPI Endpoint with Dependency Injection and Error Handling

## Architecture Overview

This task implements a RESTful API endpoint using FastAPI's dependency injection pattern with proper error handling. The solution follows a service-oriented architecture with clear separation of concerns:

- **API Layer** (`api/endpoints/users.py`): HTTP request/response handling
- **Service Layer** (`api/services/user_service.py`): Business logic and data access
- **Model Layer** (`api/models/user.py`): Data validation and serialization
- **Test Layer** (`tests/test_users_endpoint.py`): Comprehensive test coverage

The design prioritizes testability through dependency injection, type safety through Pydantic models, and proper error handling with domain-specific exceptions.

## File Structure

### New Files to Create

| File Path | Purpose | Type |
|-----------|---------|------|
| `api/__init__.py` | Package initialization | Init |
| `api/endpoints/__init__.py` | Endpoints package initialization | Init |
| `api/endpoints/users.py` | User endpoint implementation | Production |
| `api/services/__init__.py` | Services package initialization | Init |
| `api/services/user_service.py` | User service with DI | Production |
| `api/models/__init__.py` | Models package initialization | Init |
| `api/models/user.py` | Pydantic User model | Production |
| `api/exceptions.py` | Custom exception classes | Production |
| `tests/__init__.py` | Tests package initialization | Init |
| `tests/test_users_endpoint.py` | Endpoint test suite | Test |

### Existing Files to Modify

| File Path | Changes Required |
|-----------|------------------|
| `requirements.txt` | Add FastAPI, Pydantic, pytest dependencies |
| `main.py` (if exists) or create new | FastAPI app initialization with router registration |

## Implementation Details

### 1. `api/models/user.py` (30 LOC)
**Purpose**: Pydantic models for data validation

**Key Implementation Points**:
- Define `User` model with fields: `id` (int), `name` (str), `email` (EmailStr), `is_active` (bool)
- Use Pydantic v2 syntax with `ConfigDict` for configuration
- Include example values in `model_config` for OpenAPI documentation
- Add `EmailStr` type for email validation

### 2. `api/exceptions.py` (20 LOC)
**Purpose**: Custom exception classes for domain errors

**Key Implementation Points**:
- Define `UserNotFoundError` exception class
- Include user_id in exception message
- Inherit from built-in `Exception`
- Add docstring explaining usage

### 3. `api/services/user_service.py` (50 LOC)
**Purpose**: Service layer with business logic

**Key Implementation Points**:
- Create `UserService` class with mock database (dict)
- Implement `get_user(user_id: int) -> User` method
- Raise `UserNotFoundError` if user not found
- Pre-populate with 2-3 mock users for testing
- Add type hints for all methods
- Include docstrings for class and methods

### 4. `api/endpoints/users.py` (45 LOC)
**Purpose**: FastAPI endpoint with dependency injection

**Key Implementation Points**:
- Create `APIRouter` instance
- Define `GET /users/{user_id}` endpoint
- Use `Depends(UserService)` for dependency injection
- Implement exception handler for `UserNotFoundError` → 404 response
- Add response_model to endpoint decorator
- Include OpenAPI documentation (summary, description, response descriptions)
- Add status codes for 200 (success), 404 (not found), 500 (server error)

### 5. `main.py` (35 LOC)
**Purpose**: FastAPI application initialization

**Key Implementation Points**:
- Create FastAPI app instance
- Register exception handlers globally
- Include users router with `/api/v1` prefix
- Add root endpoint for health check
- Configure CORS if needed (optional)
- Add startup/shutdown events (optional)

### 6. `tests/test_users_endpoint.py` (120 LOC)
**Purpose**: Comprehensive test coverage

**Key Test Cases**:
- **Test successful user retrieval** (GET /users/1 → 200)
- **Test user not found** (GET /users/999 → 404)
- **Test invalid user_id type** (GET /users/abc → 422 validation error)
- **Test service exception handling** (mock service exception → 500)
- **Test response schema validation** (verify Pydantic model structure)
- **Test dependency injection override** (use test fixtures)

**Testing Approach**:
- Use `TestClient` from `fastapi.testclient`
- Override `UserService` dependency with mock
- Use `pytest` fixtures for test setup
- Assert response status codes and JSON structure
- Test edge cases (negative IDs, very large IDs)

## Dependencies

Add to `requirements.txt`:

```
fastapi==0.104.1
pydantic==2.5.0
pydantic[email]==2.5.0
uvicorn==0.24.0
pytest==7.4.3
pytest-cov==4.1.0
httpx==0.25.1  # Required for TestClient
```

**Rationale**:
- `fastapi`: Core framework
- `pydantic`: Data validation and settings management
- `pydantic[email]`: EmailStr type support
- `uvicorn`: ASGI server for running FastAPI
- `pytest`: Testing framework
- `pytest-cov`: Coverage reporting
- `httpx`: Required by FastAPI's TestClient

## Testing Strategy

### Coverage Goals
- **Line Coverage**: ≥80% (target: 90%+)
- **Branch Coverage**: ≥75% (target: 85%+)

### Test Coverage Breakdown

| Component | Test Cases | Coverage Target |
|-----------|-----------|-----------------|
| `users.py` endpoint | 5 test cases | 95% |
| `user_service.py` | Tested via endpoint | 100% |
| `user.py` models | Tested via endpoint | 100% |
| Exception handling | 3 test cases | 100% |

### Test Execution
```bash
# Run tests with coverage
pytest tests/test_users_endpoint.py -v --cov=api --cov-report=term --cov-report=json

# Expected output: 100% test pass rate, ≥80% coverage
```

## Estimated Lines of Code

### Production Code

| File | Estimated LOC | Complexity |
|------|---------------|------------|
| `api/models/user.py` | 30 | Low |
| `api/exceptions.py` | 20 | Low |
| `api/services/user_service.py` | 50 | Low |
| `api/endpoints/users.py` | 45 | Medium |
| `main.py` | 35 | Low |
| `__init__.py` files (5 files) | 10 | Minimal |
| **Total Production** | **190** | **Low-Medium** |

### Test Code

| File | Estimated LOC | Complexity |
|------|---------------|------------|
| `tests/test_users_endpoint.py` | 120 | Medium |
| `tests/__init__.py` | 2 | Minimal |
| **Total Test** | **122** | **Medium** |

### Grand Total
- **Production LOC**: 190
- **Test LOC**: 122
- **Total LOC**: 312
- **Test/Production Ratio**: 0.64 (64% test coverage by LOC)

## Risk Assessment

### Low Risks
1. **Simple CRUD operation**: Straightforward GET endpoint with no complex business logic
2. **Well-documented patterns**: FastAPI dependency injection is well-established
3. **Type safety**: Pydantic provides runtime validation

### Potential Issues

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|---------|------------|
| Pydantic v1 vs v2 syntax differences | Low | Low | Use Pydantic v2 syntax consistently |
| Dependency injection override in tests | Low | Low | Follow FastAPI testing documentation |
| Mock database state management | Low | Low | Use pytest fixtures for clean state |
| Missing email validator package | Medium | Low | Explicitly install `pydantic[email]` |

### Complexity Factors
- **File Complexity**: 3/10 (9 files total, all simple structure)
- **Pattern Familiarity**: 1/10 (standard FastAPI patterns)
- **Risk Level**: 0/10 (no database, no external services, no security concerns)
- **Dependencies**: 1/10 (FastAPI + Pydantic + pytest)

**Overall Complexity**: 3/10 (Simple) ✅

## Implementation Order

1. **Phase 1 - Models & Exceptions** (30 min)
   - Create package structure (`__init__.py` files)
   - Implement `User` model
   - Implement `UserNotFoundError` exception

2. **Phase 2 - Service Layer** (45 min)
   - Implement `UserService` with mock data
   - Add type hints and docstrings

3. **Phase 3 - API Layer** (60 min)
   - Implement users endpoint
   - Add exception handlers
   - Create main.py with app initialization

4. **Phase 4 - Testing** (90 min)
   - Write comprehensive test suite
   - Verify coverage meets ≥80% threshold
   - Test all edge cases

5. **Phase 5 - Validation** (15 min)
   - Run pytest with coverage
   - Verify all tests pass
   - Check code quality (type hints, docstrings)

**Total Estimated Time**: ~4 hours

## Success Criteria Checklist

- [ ] All files created in correct directory structure
- [ ] Endpoint accessible at `GET /users/{user_id}`
- [ ] Dependency injection working correctly
- [ ] 404 returned for non-existent users
- [ ] 422 returned for invalid input
- [ ] Pydantic models validate data correctly
- [ ] All tests passing (100%)
- [ ] Code coverage ≥80%
- [ ] Type hints on all functions
- [ ] Docstrings on classes and complex methods
- [ ] No compilation errors
- [ ] FastAPI OpenAPI docs generated correctly

---

**Plan Status**: Ready for Phase 2.5 (Architectural Review)
