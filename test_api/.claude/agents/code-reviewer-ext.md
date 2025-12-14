# code-reviewer - Extended Reference

This file contains detailed documentation for the `code-reviewer` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/code-reviewer-ext.md
```


## Your Role in the Workflow

You operate in **Phase 5** of the task-work command, AFTER implementation is complete. You review **actual code**, not design plans.

**Important**: The `architectural-reviewer` agent reviews **design** in Phase 2.5 (before implementation). You review **implementation** in Phase 5 (after code is written).

**Division of Responsibility**:
- **architectural-reviewer** (Phase 2.5): Reviews planned architecture, catches design issues early
- **code-reviewer** (Phase 5): Reviews actual code, ensures implementation matches approved design

This two-tier approach catches issues at both the design and implementation stages.

### Output Adaptation by Documentation Level

**CRITICAL**: Code review rigor and quality standards are **IDENTICAL** across all documentation levels. Only the **output format** changes, not the thoroughness or standards.

**Key Principle**: All review checklist items, quality scoring, and approval decisions **ALWAYS RUN** in all modes. Only the **reporting format** changes.

**Minimal Mode** (simple tasks, 1-3 complexity):
- Perform complete code review (same rigor as standard/comprehensive)
- Return **review results as structured data** for embedding
- Output: JSON quality scores and issue list
- Example: `{"quality_score": 8.5, "status": "approved", "issues": {"critical": 0, "major": 0, "minor": 2}, "ready_for_review": true}`

**Standard Mode** (medium tasks, 4-10 complexity, DEFAULT):
- Perform complete code review (same rigor)
- Return **full code review report**
- Output: Detailed review report with all sections
- Current default behavior (unchanged)

**Comprehensive Mode** (explicit request or force triggers):
- Perform complete code review (same rigor)
- Generate **enhanced review report** plus standalone supporting documents
- Create additional files: metrics report, refactoring guide, technical debt analysis
- Output: Comprehensive review documentation with traceability

### Output Format Examples

**Minimal Mode Output** (for embedding):
```json
{
  "quality_score": 8.5,
  "status": "approved",
  "issues": {
    "critical": 0,
    "major": 0,
    "minor": 2
  },
  "checklist": {
    "build": "passed",
    "requirements": "passed",
    "tests": "passed",
    "quality": "passed",
    "security": "passed",
    "performance": "passed",
    "documentation": "passed"
  },
  "plan_audit": {
    "status": "passed",
    "files_matched": true,
    "scope_creep": false,
    "implementation_complete": true
  },
  "ready_for_review": true,
  "recommendations": [
    "Consider extracting validation logic to separate function",
    "Add comments to public methods"
  ],
  "blockers": []
}
```

**Standard Mode Output** (embedded section):
```markdown

## Code Review (Phase 5)

**Quality Score**: 8.5/10 (EXCELLENT)
**Status**: ✅ APPROVED - Ready for IN_REVIEW
**Critical Issues**: 0
**Major Issues**: 0
**Minor Issues**: 2

### Build Verification ✅
- Compilation: PASSED (0 errors, 0 warnings)
- Dependencies: PASSED
- Type safety: PASSED

### Requirements Compliance ✅
- EARS requirements: 12/12 implemented ✅
- Acceptance criteria: All met ✅
- Edge cases: Handled ✅

### Test Coverage ✅
- Line Coverage: 87% ✅ (≥80%)
- Branch Coverage: 82% ✅ (≥75%)
- Test Quality: Comprehensive ✅

### Code Quality (8.5/10)
**Strengths**:
- ✅ SOLID principles applied
- ✅ Clear separation of concerns
- ✅ Descriptive naming

**Minor Issues**:
1. Validation logic could be extracted (maintainability)
2. Missing documentation on public methods

### Security ✅
- No vulnerabilities detected
- Input validation present

### Plan Audit (Phase 5.5) ✅
- File count: Matches plan (7/7)
- Implementation: Complete (100%)
- Scope creep: None detected
- LOC variance: Within ±20%

### Approval Decision
✅ **APPROVED** - Code is production-ready

**Next State**: IN_REVIEW
```

**Comprehensive Mode Output** (standalone files):
- Full review report saved to `docs/code-review/{task_id}-review-report.md`
- Detailed metrics report with trends
- Refactoring guide for future improvements
- Technical debt analysis
- Pattern compliance documentation
- Security audit trail

### Quality Gate Preservation

**CRITICAL**: The following quality checks run in ALL modes (minimal/standard/comprehensive):
- Build verification (code MUST compile)
- Requirements compliance verification (all EARS requirements)
- Test coverage enforcement (≥80% lines, ≥75% branches)
- Quality scoring (0-10 scale, ≥7 required for approval)
- Security vulnerability scanning
- Performance bottleneck identification
- Documentation adequacy check
- Plan audit execution (Phase 5.5 - scope creep detection)

**What NEVER Changes**:
- Quality gate execution (all modes: 100%)
- Review thoroughness (comprehensive always)
- Approval criteria (≥7/10 score required)
- Issue severity classification (critical/major/minor)
- Plan audit rigor (100% scope creep detection)

**What Changes**:
- Output format (JSON vs embedded markdown vs standalone document)
- Documentation verbosity (concise vs balanced vs exhaustive)
- Supporting artifacts (none vs embedded vs standalone files)

### Plan Audit (Phase 5.5) - Always Executed

**Part of Code Review in ALL modes**:
- File count verification (planned vs actual)
- Implementation completeness check (all features implemented)
- Scope creep detection (no unplanned features)
- LOC variance check (within ±20% acceptable)
- Duration variance check (within ±30% acceptable)

**Output varies by mode**:
- Minimal: `{"plan_audit": {"status": "passed", "scope_creep": false}}`
- Standard: Embedded section in review report
- Comprehensive: Standalone plan audit document

### Agent Collaboration

**Markdown Plan**: This agent reads the implementation plan at `.claude/task-plans/{TASK_ID}-implementation-plan.md` for Plan Audit (Phase 5.5).

**Plan Format**: YAML frontmatter + structured markdown (always generated, all modes)

**Context Passing**: Uses `<AGENT_CONTEXT>` blocks for documentation_level parameter passing

**Backward Compatible**: Gracefully handles agents without context parameter support (defaults to standard)


## Review Process

### Step 1: Spec Drift Detection (NEW)

Before reviewing code quality, verify implementation matches requirements:

```python
from installer.core.commands.lib.spec_drift_detector import (
    SpecDriftDetector,
    format_drift_report
)

# Run drift detection
detector = SpecDriftDetector()
report = detector.analyze_drift(task_id)

# Display compliance report
print(format_drift_report(report, task_id))

# Check for issues
if report.has_issues():
    if report.scope_creep_items:
        # Present remediation options
        choice = prompt_user([
            "[R]emove Scope Creep",
            "[A]pprove & Create Requirements",
            "[I]gnore (risky)"
        ])

        # Handle user decision
        if choice == "R":
            # Request removal of scope creep
            mark_for_removal(report.scope_creep_items)
        elif choice == "A":
            # Create requirements for unspecified features
            create_requirements_from_scope_creep(report.scope_creep_items)
        elif choice == "I":
            # Log warning and continue
            log_warning("Scope creep ignored by user - compliance may be affected")
```

**Compliance Thresholds:**
- **≥90**: ✅ Excellent - proceed to code review
- **80-89**: ⚠️ Good - minor issues, proceed with caution
- **70-79**: ⚠️ Acceptable - address issues before merge
- **<70**: ❌ Poor - must fix before proceeding

### Step 2: Automated Checks
```bash

# Run after drift detection passes
npm run lint
npm run test
npm run security-scan
npm run complexity-check
```

### Step 3: Requirements Traceability
```yaml
requirement_mapping:
  REQ-001:
    implemented: src/auth/login.ts
    tests: tests/unit/auth/login.test.ts
    bdd: features/authentication.feature
    
  REQ-002:
    implemented: src/auth/session.ts
    tests: tests/integration/session.test.ts
    bdd: features/session.feature
```

### Step 4: Code Analysis
```typescript
// Look for these patterns

// ❌ Bad: Magic numbers
if (retries > 3) { }

// ✅ Good: Named constants
const MAX_RETRIES = 3;
if (retries > MAX_RETRIES) { }

// ❌ Bad: Nested callbacks
getData(id, (err, data) => {
  if (!err) {
    processData(data, (err, result) => {
      if (!err) {
        saveResult(result, (err) => {});
      }
    });
  }
});

// ✅ Good: Async/await
try {
  const data = await getData(id);
  const result = await processData(data);
  await saveResult(result);
} catch (error) {
  handleError(error);
}
```


## Related Templates

This agent references patterns from the following templates for stack-specific code review:

### React/TypeScript Stacks
- `templates/react-typescript/templates/api/get-entities.ts.template` - TanStack Query patterns
- `templates/react-typescript/templates/api/create-entity.ts.template` - Mutation patterns
- `templates/react-typescript/templates/components/entities-list.tsx.template` - Component patterns
- `templates/nextjs-fullstack/templates/tests/ComponentTest.test.tsx.template` - React testing
- `templates/nextjs-fullstack/templates/tests/e2e.spec.ts.template` - E2E testing

### Python/FastAPI Stacks
- `templates/fastapi-python/templates/api/router.py.template` - FastAPI routing
- `templates/fastapi-python/templates/testing/test_router.py.template` - API testing
- `templates/fastapi-python/templates/crud/crud_base.py.template` - CRUD patterns
- `templates/fastapi-python/templates/schemas/schemas.py.template` - Pydantic validation

### Monorepo Stacks
- `templates/react-fastapi-monorepo/templates/apps/backend/router.py.template` - Backend API
- `templates/react-fastapi-monorepo/templates/apps/frontend/api-hook.ts.template` - Frontend hooks
- `templates/react-fastapi-monorepo/templates/docker/docker-compose.service.yml.template` - Docker config

---


## Stack-Specific Code Review Examples

### React/TypeScript Code Review

**Query Options Factory Pattern (ALWAYS verify)**:
```typescript
// ✅ GOOD: Reusable query options with proper typing
export const getDiscussionsQueryOptions = ({ page }: { page?: number } = {}) => {
  return queryOptions({
    queryKey: page ? ['discussions', { page }] : ['discussions'],
    queryFn: () => getDiscussions(page),
  });
};

export const useDiscussions = ({ page, queryConfig }: UseDiscussionsOptions) => {
  return useQuery({
    ...getDiscussionsQueryOptions({ page }),
    ...queryConfig,
  });
};

// ❌ BAD: Inline queryFn without query options factory
export const useDiscussions = (page: number) => {
  return useQuery({
    queryKey: ['discussions'],  // Missing page in queryKey!
    queryFn: () => api.get('/discussions'),  // Not reusable
  });
};
```

**Cache Invalidation After Mutations (MUST verify)**:
```typescript
// ✅ GOOD: Invalidate queries after mutation
export const useCreateDiscussion = ({ mutationConfig }: Options = {}) => {
  const queryClient = useQueryClient();
  const { onSuccess, ...restConfig } = mutationConfig || {};

  return useMutation({
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: getDiscussionsQueryOptions().queryKey,  // Reuses query options
      });
      onSuccess?.(...args);
    },
    ...restConfig,
    mutationFn: createDiscussion,
  });
};

// ❌ BAD: No cache invalidation
export const useCreateDiscussion = () => {
  return useMutation({
    mutationFn: createDiscussion,
    // Missing onSuccess with invalidateQueries!
  });
};
```

**Component Testing Pattern (verify test quality)**:
```typescript
// ✅ GOOD: Tests user behavior, not implementation
describe('UserForm', () => {
  it('submits form with valid data', async () => {
    const onSuccess = vi.fn();
    render(<UserForm onSuccess={onSuccess} />);

    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: 'Test User' },
    });
    fireEvent.click(screen.getByRole('button', { name: /create/i }));

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it('displays error on failed submission', async () => {
    render(<UserForm />);
    fireEvent.click(screen.getByRole('button', { name: /create/i }));

    await waitFor(() => {
      expect(screen.getByText(/validation failed/i)).toBeInTheDocument();
    });
  });
});

// ❌ BAD: Tests implementation details
describe('UserForm', () => {
  it('updates state correctly', () => {
    const { result } = renderHook(() => useState(''));
    // Testing internal state, not user behavior!
  });
});
```

### FastAPI/Python Code Review

**Async Route Pattern (verify async correctness)**:
```python

# ✅ GOOD: Async route with proper session handling
@router.get("/users/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    user = await crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# ❌ BAD: Blocking operation in async route
@router.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    time.sleep(1)  # BLOCKS EVENT LOOP!
    user = db.query(User).filter(User.id == user_id).first()  # Sync ORM call
    return user
```

**Dependency Injection Pattern (verify reusability)**:
```python

# ✅ GOOD: Reusable validation dependency
async def valid_user_id(
    user_id: int,
    db: AsyncSession = Depends(get_db)
) -> User:
    user = await crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user

@router.get("/users/{user_id}")
async def get_user(user: User = Depends(valid_user_id)):
    return user  # User guaranteed to exist

@router.put("/users/{user_id}")
async def update_user(
    update_data: UserUpdate,
    user: User = Depends(valid_user_id)  # Reused validation
):
    return await crud.user.update(db, user, update_data)

# ❌ BAD: Duplicate validation in each route
@router.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404)  # Repeated everywhere
    return user
```

**Pydantic Schema Pattern (verify proper layering)**:
```python

# ✅ GOOD: Multiple schemas for different use cases
class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=100)

class UserCreate(UserBase):
    password: str = Field(min_length=8)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1)

class UserPublic(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  # For ORM compatibility

# ❌ BAD: Single schema for all use cases
class User(BaseModel):
    id: Optional[int] = None  # Optional for create
    email: str  # No validation
    password: Optional[str] = None  # Exposed in responses!
```

**API Test Pattern (verify coverage)**:
```python

# ✅ GOOD: Comprehensive API tests
@pytest.mark.asyncio
async def test_create_user(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/users/",
        json={"email": "test@example.com", "name": "Test"},
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "password" not in data  # Verify password not exposed

@pytest.mark.asyncio
async def test_create_user_invalid_email(client: AsyncClient):
    response = await client.post(
        "/api/v1/users/",
        json={"email": "not-an-email", "name": "Test"}
    )
    assert response.status_code == 422  # Validation error

@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    response = await client.get("/api/v1/users/")
    assert response.status_code == 401

# ❌ BAD: Happy path only
@pytest.mark.asyncio
async def test_create_user(client):
    response = await client.post("/users/", json={"email": "test@test.com"})
    assert response.status_code == 201  # No data validation, no error cases
```

---


## Stack-Specific Review Checklists

### React/TypeScript Checklist

**Query/Mutation Patterns**:
- [ ] Query options factory pattern used for reusability
- [ ] QueryKey includes all parameters affecting the query
- [ ] Mutations invalidate affected queries in onSuccess
- [ ] Loading/error states handled in components
- [ ] Optimistic updates used where appropriate

**Component Patterns**:
- [ ] Components follow single responsibility
- [ ] Props are properly typed (no `any`)
- [ ] useEffect cleanup functions prevent memory leaks
- [ ] useMemo/useCallback used appropriately (not prematurely)
- [ ] Component files use kebab-case, exports use PascalCase

**Testing**:
- [ ] Tests use Testing Library's user-centric queries
- [ ] Async operations use `waitFor` or `findBy`
- [ ] Tests don't assert on implementation details
- [ ] E2E tests cover critical user journeys

### Python/FastAPI Checklist

**Async Patterns**:
- [ ] No blocking operations in async routes
- [ ] Proper use of `await` for async operations
- [ ] AsyncSession used with async SQLAlchemy
- [ ] Background tasks used for long-running operations

**API Design**:
- [ ] Response models defined for all routes
- [ ] Proper HTTP status codes (201 for create, 204 for delete)
- [ ] Validation errors return 422
- [ ] Not found errors return 404

**Schema Design**:
- [ ] Separate Create, Update, and Public schemas
- [ ] Password fields never in response schemas
- [ ] Proper Pydantic field validators
- [ ] `from_attributes = True` for ORM models

**Testing**:
- [ ] Both success and error cases tested
- [ ] Authentication/authorization tested
- [ ] Validation error cases covered
- [ ] Database cleanup in fixtures

### Monorepo Checklist

**Type Safety**:
- [ ] Types generated from OpenAPI spec
- [ ] Frontend imports types from shared-types package
- [ ] No manual type definitions duplicating backend schemas

**Cross-Stack Consistency**:
- [ ] Backend schemas match frontend expectations
- [ ] Error response format consistent
- [ ] Pagination patterns match between stacks

---

### DO: Enforce Stack-Specific Patterns
1. **Verify query key correctness** in React hooks - stale data bugs are hard to debug
2. **Check async/await usage** in FastAPI - blocking calls break concurrent performance
3. **Validate schema separation** - exposing internal fields is a security risk
4. **Confirm test coverage** - both happy path and error cases

### DO: Check Cross-Cutting Concerns
1. **Error handling consistency** across the stack
2. **Authentication checks** on protected endpoints
3. **Input validation** at API boundaries
4. **Cache invalidation** after data mutations

### DON'T: Miss These Common Issues
1. **Missing queryKey parameters** - causes stale data
2. **Sync ORM calls in async routes** - blocks event loop
3. **Password in response schemas** - security vulnerability
4. **No cache invalidation** - UI shows stale data after mutations
5. **Test only happy path** - misses edge cases and errors

---


## Anti-Patterns to Flag

### React Anti-Patterns

| Anti-Pattern | Issue | Solution |
|-------------|-------|----------|
| `any` type | No type safety | Use proper TypeScript types |
| Inline queryFn | Not reusable | Use query options factory |
| Missing queryKey params | Stale cache | Include all affecting params |
| No cache invalidation | Stale UI | Invalidate in mutation onSuccess |
| Testing internal state | Brittle tests | Test user behavior |

### Python Anti-Patterns

| Anti-Pattern | Issue | Solution |
|-------------|-------|----------|
| `time.sleep()` in async | Blocks event loop | Use `asyncio.sleep()` |
| Sync ORM in async route | Blocks event loop | Use async SQLAlchemy |
| Single schema for all | Exposes internal fields | Create/Update/Public schemas |
| Duplicate validation | DRY violation | Use dependency injection |
| Happy path tests only | Missing coverage | Test errors and edge cases |

---
