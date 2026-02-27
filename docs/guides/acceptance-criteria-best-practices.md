# Acceptance Criteria Best Practices for Local LLM Runs

Write acceptance criteria that local LLM backends (vLLM/Qwen3, Ollama, etc.) can implement correctly on the first pass. These models have lower first-pass comprehension than Anthropic models, so specificity is critical.

## Why This Matters

In the FEAT-947C database feature build on vLLM/Qwen3 (GB10), **50% of tasks required a second turn** vs 0% for the same feature on Anthropic/Claude. The primary cause: acceptance criteria that were clear enough for Claude but too ambiguous for Qwen3.

The Coach's adversarial loop catches these issues, but each extra turn costs ~10-50 minutes on local hardware. Writing better AC upfront saves significant wall-clock time.

## Core Principle: Always Prefer Explicit Over Implicit

Anthropic models infer intent from context. Local LLMs implement exactly what's written. If the AC doesn't say it, assume the local LLM won't do it.

## Rules

### 1. Include Expected Interface Signatures

Don't assume the model will infer the correct function signatures, return types, or parameter names.

**Vague:**
```markdown
- [ ] Health check endpoint returns database status
```

**Explicit:**
```markdown
- [ ] GET /health returns JSON: `{"status": "healthy", "database": "connected", "version": "<alembic-revision>"}`
- [ ] GET /health returns HTTP 200 when database is reachable
- [ ] GET /health returns HTTP 503 with `{"status": "unhealthy", "database": "disconnected", "error": "<message>"}` when database is unreachable
```

### 2. Specify Exact File Paths and Function Names

Don't leave file placement to the model's judgement. State exactly where code should live.

**Vague:**
```markdown
- [ ] Create a health check router
```

**Explicit:**
```markdown
- [ ] Create `src/health/router.py` with `router = APIRouter(prefix="/health", tags=["health"])`
- [ ] Register the router in `src/main.py` via `app.include_router(health_router)`
- [ ] Create `tests/health/test_router.py` with tests for healthy and unhealthy states
```

### 3. Break Large AC Into Smaller, Testable Items

A single criterion that covers multiple behaviours will partially fail. Split it so each item is independently verifiable.

**Vague:**
```markdown
- [ ] Database health check works correctly in all scenarios
```

**Explicit:**
```markdown
- [ ] When database is reachable: returns `status: healthy` with HTTP 200
- [ ] When database is unreachable: returns `status: unhealthy` with HTTP 503
- [ ] When database connection times out: returns within 5 seconds (not hung)
- [ ] Response includes current Alembic migration revision
- [ ] Health check does not require authentication
```

### 4. State the Negative Cases

Local LLMs focus on the happy path. Explicitly list what should happen when things go wrong.

**Vague:**
```markdown
- [ ] CRUD operations handle errors
```

**Explicit:**
```markdown
- [ ] `get_user(id)` raises `HTTPException(404)` when user not found
- [ ] `create_user(data)` raises `HTTPException(409)` when email already exists
- [ ] `update_user(id, data)` raises `HTTPException(404)` when user not found
- [ ] All database errors are caught and returned as `HTTPException(500)` with sanitised message
```

### 5. Specify Integration Points Explicitly

Don't assume the model knows how your project wires things together.

**Vague:**
```markdown
- [ ] Health check is integrated into the application
```

**Explicit:**
```markdown
- [ ] Health router registered in `src/main.py` after database initialisation
- [ ] Health check uses the same `AsyncSession` dependency as other routers (`get_db` from `src/database.py`)
- [ ] Health check calls `SELECT 1` to verify database connectivity (not just connection pool status)
```

### 6. Include Type and Validation Constraints

**Vague:**
```markdown
- [ ] User schema validates input
```

**Explicit:**
```markdown
- [ ] `UserCreate` schema: `email: EmailStr`, `name: str` (min 1 char, max 100 chars)
- [ ] `UserResponse` schema: `id: int`, `email: str`, `name: str`, `created_at: datetime`
- [ ] Schema models defined in `src/users/schemas.py` using Pydantic v2 `BaseModel`
```

## Case Study: TASK-DB-008 (Turn 1 Failure)

TASK-DB-008 ("Integrate database health check") illustrates the problem. On the vLLM/Qwen3 run:

- **Turn 1 result**: Tests passed (3 test files, all green), but only **2/9 acceptance criteria verified** (22%)
- **Root cause**: The model produced a working health endpoint that returned correct HTTP status codes, but didn't implement the specific response format, Alembic version reporting, timeout handling, or error scenarios described in the AC
- **Turn 2 result**: After Coach feedback listing the 7 unmet criteria, the model fixed all of them — **9/9 verified** (100%)

**Key insight**: Qwen3 follows specific instructions well (Turn 2 was fast and correct) but struggles with comprehensive first-pass implementation from high-level descriptions. The more specific the AC, the higher the first-pass success rate.

### Contrast with Anthropic

The same feature on Anthropic/Claude achieved **100% first-pass success** (5/5 tasks, 0 needing a second turn). Claude inferred the expected response formats, error handling, and integration patterns from the broader task context. Local LLMs need these spelled out.

## Checklist: Before Submitting Tasks for Local LLM Builds

- [ ] Every AC item is independently testable (Coach can verify each one)
- [ ] File paths are specified for all new files
- [ ] Function/class names are specified where they matter
- [ ] Return types and response formats are shown as code literals
- [ ] Error cases have their own AC items (not bundled into happy-path criteria)
- [ ] Integration points name the exact files and functions involved
- [ ] No AC item requires inferring information from project context alone

## When Vague AC Is Acceptable

For **Anthropic API runs**, concise high-level AC is fine — Claude fills in the gaps. Only invest in detailed AC when:

- Running on local LLM backends (vLLM, Ollama, llama.cpp)
- Tasks have high complexity (score >= 5)
- The feature involves multiple integration points
- Previous runs of similar tasks needed 2+ turns
