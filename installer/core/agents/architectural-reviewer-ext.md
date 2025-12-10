# architectural-reviewer - Extended Reference

This file contains detailed documentation for the `architectural-reviewer` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/architectural-reviewer-ext.md
```


## Documentation Level Awareness (TASK-035)

You receive `documentation_level` parameter via `<AGENT_CONTEXT>` block:

```markdown
<AGENT_CONTEXT>
documentation_level: minimal|standard|comprehensive
complexity_score: 1-10
task_id: TASK-XXX
stack: python|react|maui|etc
phase: 2.5B
</AGENT_CONTEXT>
```

### Behavior by Documentation Level

**Key Principle**: Architectural review **ALWAYS RUNS** in all modes (quality gate preserved). Only the **output format** changes.

**Minimal Mode** (simple tasks, 1-3 complexity):
- Perform full SOLID/DRY/YAGNI evaluation (same rigor)
- Return **scores and findings as structured data**
- Skip standalone architecture guide (665 lines)
- Output: Score object + brief issue list for embedding in summary
- Example: `{"overall_score": 85, "solid": 42/50, "dry": 23/25, "yagni": 20/25, "issues": [...], "recommendations": [...]}`

**Standard Mode** (medium tasks, 4-10 complexity, DEFAULT):
- Perform full SOLID/DRY/YAGNI evaluation (same rigor)
- Return **scores, findings, and brief architecture summary**
- Skip standalone architecture guide
- Embed findings in implementation summary
- Output: Score object + 200-line architecture summary section

**Comprehensive Mode** (explicit request or force triggers):
- Perform full SOLID/DRY/YAGNI evaluation (same rigor)
- Generate **standalone architecture guide** (665 lines)
- Create file: `docs/architecture/{task_id}-architecture-guide.md`
- Complete documentation with examples and recommendations
- Output: Full architectural review document + score object

### Output Format Examples

**Minimal Mode Output** (for embedding):
```json
{
  "overall_score": 85,
  "status": "approved_with_recommendations",
  "solid_compliance": {
    "total": 42,
    "max": 50,
    "breakdown": {
      "srp": 8, "ocp": 9, "lsp": 10, "isp": 7, "dip": 8
    }
  },
  "dry_compliance": {"score": 23, "max": 25},
  "yagni_compliance": {"score": 20, "max": 25},
  "critical_issues": [],
  "recommendations": [
    "Split AuthenticationService into AuthService and TokenManager (SRP)",
    "Use dependency injection for UserRepository (DIP)"
  ],
  "estimated_fix_time": "15 minutes"
}
```

**Standard Mode Output** (embedded section):
```markdown

## Architectural Review (Phase 2.5B)

**Overall Score**: 85/100 (Approved with Recommendations)

**SOLID Compliance** (42/50):
- Single Responsibility: 8/10 ✅ (Minor: AuthService has multiple concerns)
- Open/Closed: 9/10 ✅
- Liskov Substitution: 10/10 ✅
- Interface Segregation: 7/10 ⚠️ (Recommendation: Split IUserService)
- Dependency Inversion: 8/10 ✅

**DRY Compliance** (23/25):
- Score: 23/25 ⚠️
- Issue: Validation logic duplicated in 2 places
- Recommendation: Extract to shared EmailValidator class

**YAGNI Compliance** (20/25):
- Score: 20/25 ⚠️
- Issue: Plugin system not required for MVP
- Recommendation: Simplify to direct implementation

**Critical Issues**: None

**Recommendations**:
1. Interface Segregation: Split IUserService into IUserReader and IUserWriter
2. DRY: Extract email validation to EmailValidator class
3. YAGNI: Remove plugin architecture, add when needed

**Approval Decision**: ✅ APPROVED WITH RECOMMENDATIONS
**Estimated Fix Time**: 15 minutes
```

**Comprehensive Mode Output** (standalone file):
- Full architectural review document saved to `docs/architecture/{task_id}-architecture-guide.md`
- Includes detailed SOLID/DRY/YAGNI analysis with code examples
- Complete pattern recommendations with rationale
- Traceability to requirements and design decisions
- Future maintenance considerations
- Score object returned for embedding in summary

### Quality Gate Preservation

**CRITICAL**: The following quality checks run in ALL modes (minimal/standard/comprehensive):
- SOLID principle evaluation (all 5 principles scored 0-10)
- DRY compliance assessment (0-25 points)
- YAGNI compliance assessment (0-25 points)
- Overall architectural score (0-100)
- Approval thresholds (≥80 auto-approve, 60-79 approved with recommendations, <60 reject)
- Critical issue detection (blocks implementation if found)
- Design pattern appropriateness validation

**What NEVER Changes**:
- Quality gate execution (all modes: 100%)
- Scoring methodology (identical across modes)
- Approval criteria (same thresholds)
- Review rigor (comprehensive analysis always)

**What Changes**:
- Output format (JSON vs embedded markdown vs standalone document)
- Documentation verbosity (concise vs balanced vs exhaustive)
- Supporting artifacts (none vs embedded vs standalone files)

### Agent Collaboration

**Markdown Plan**: This agent reads the implementation plan at `.claude/task-plans/{TASK_ID}-implementation-plan.md` and embeds architectural review results.

**Plan Format**: YAML frontmatter + structured markdown (always generated, all modes)

**Context Passing**: Uses `<AGENT_CONTEXT>` blocks for documentation_level parameter passing

**Backward Compatible**: Gracefully handles agents without context parameter support (defaults to standard)


## Core Review Principles

### SOLID Principles

#### 1. Single Responsibility Principle (SRP)
**Each class/module should have ONE reason to change.**

```python

# ❌ VIOLATION - Multiple responsibilities
class UserService:
    def create_user(self, data): pass
    def send_welcome_email(self, user): pass  # Email responsibility
    def log_user_activity(self, user): pass   # Logging responsibility
    def validate_password(self, pwd): pass    # Validation responsibility

# ✅ CORRECT - Single responsibilities
class UserService:
    def create_user(self, data): pass

class EmailService:
    def send_welcome_email(self, user): pass

class ActivityLogger:
    def log_user_activity(self, user): pass

class PasswordValidator:
    def validate(self, pwd): pass
```

**Review Questions:**
- Does this class/module do ONE thing?
- Can I describe its purpose in a single sentence without using "and"?
- Would different types of changes affect this code?

#### 2. Open/Closed Principle (OCP)
**Open for extension, closed for modification.**

```python

# ❌ VIOLATION - Must modify for new types
class PaymentProcessor:
    def process(self, payment_type, amount):
        if payment_type == "credit_card":
            # Credit card logic
        elif payment_type == "paypal":
            # PayPal logic
        elif payment_type == "bitcoin":  # Requires modification!
            # Bitcoin logic

# ✅ CORRECT - Extend without modifying
from abc import ABC, abstractmethod

class PaymentMethod(ABC):
    @abstractmethod
    def process(self, amount): pass

class CreditCardPayment(PaymentMethod):
    def process(self, amount): pass

class PayPalPayment(PaymentMethod):
    def process(self, amount): pass

class PaymentProcessor:
    def process(self, payment_method: PaymentMethod, amount):
        return payment_method.process(amount)
```

**Review Questions:**
- Can I add new behavior without changing existing code?
- Are there if/elif chains that handle different types?
- Is polymorphism being used appropriately?

#### 3. Liskov Substitution Principle (LSP)
**Subtypes must be substitutable for their base types.**

```python

# ❌ VIOLATION - ReadOnlyRepository breaks contract
class Repository:
    def save(self, entity): pass
    def delete(self, id): pass

class ReadOnlyRepository(Repository):
    def save(self, entity):
        raise NotImplementedError("Cannot save!")  # Breaks LSP
    def delete(self, id):
        raise NotImplementedError("Cannot delete!")  # Breaks LSP

# ✅ CORRECT - Proper abstraction hierarchy
class ReadableRepository:
    def get(self, id): pass
    def find_all(self): pass

class WritableRepository(ReadableRepository):
    def save(self, entity): pass
    def delete(self, id): pass
```

**Review Questions:**
- Can I swap subclass for parent without breaking functionality?
- Does subclass strengthen preconditions or weaken postconditions?
- Are there NotImplementedError or pass implementations?

#### 4. Interface Segregation Principle (ISP)
**Clients shouldn't depend on interfaces they don't use.**

```python

# ❌ VIOLATION - Fat interface
class Worker:
    def work(self): pass
    def eat(self): pass
    def sleep(self): pass

class RobotWorker(Worker):
    def work(self): pass
    def eat(self): pass  # Robots don't eat!
    def sleep(self): pass  # Robots don't sleep!

# ✅ CORRECT - Segregated interfaces
class Workable:
    def work(self): pass

class Eatable:
    def eat(self): pass

class Sleepable:
    def sleep(self): pass

class HumanWorker(Workable, Eatable, Sleepable):
    def work(self): pass
    def eat(self): pass
    def sleep(self): pass

class RobotWorker(Workable):
    def work(self): pass
```

**Review Questions:**
- Are there methods that some implementations leave empty?
- Can I split this interface into smaller, focused interfaces?
- Do all clients need all methods?

#### 5. Dependency Inversion Principle (DIP)
**Depend on abstractions, not concretions.**

```python

# ❌ VIOLATION - Depends on concrete implementation
class EmailService:
    def send(self, to, message): pass

class UserService:
    def __init__(self):
        self.email_service = EmailService()  # Tight coupling!

# ✅ CORRECT - Depends on abstraction
from abc import ABC, abstractmethod

class NotificationService(ABC):
    @abstractmethod
    def send(self, to, message): pass

class EmailService(NotificationService):
    def send(self, to, message): pass

class UserService:
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service  # Flexible!
```

**Review Questions:**
- Are concrete classes instantiated directly?
- Is dependency injection being used?
- Can I swap implementations without code changes?

### DRY Principle (Don't Repeat Yourself)

**Every piece of knowledge should have a single, unambiguous representation.**

```python

# ❌ VIOLATION - Repeated validation logic
class UserController:
    def create_user(self, data):
        if not data.get("email"):
            raise ValueError("Email required")
        if "@" not in data["email"]:
            raise ValueError("Invalid email")
        # Create user

    def update_user(self, id, data):
        if not data.get("email"):
            raise ValueError("Email required")
        if "@" not in data["email"]:
            raise ValueError("Invalid email")
        # Update user

# ✅ CORRECT - Shared validation logic
class EmailValidator:
    @staticmethod
    def validate(email: str):
        if not email:
            raise ValueError("Email required")
        if "@" not in email:
            raise ValueError("Invalid email")

class UserController:
    def create_user(self, data):
        EmailValidator.validate(data.get("email"))
        # Create user

    def update_user(self, id, data):
        EmailValidator.validate(data.get("email"))
        # Update user
```

**Review Questions:**
- Is the same logic implemented in multiple places?
- Are there copy-pasted code blocks with slight variations?
- Can I extract common behavior into a shared function/class?

### YAGNI Principle (You Aren't Gonna Need It)

**Don't build functionality until you actually need it.**

```python

# ❌ VIOLATION - Premature abstraction
class UserService:
    def create_user(self, data):
        # Complex plugin system for future extensibility
        for plugin in self.plugins:
            plugin.before_create(data)

        user = self._create(data)

        for plugin in self.plugins:
            plugin.after_create(user)

        return user

# ✅ CORRECT - Simple implementation
class UserService:
    def create_user(self, data):
        return self._create(data)  # Add complexity when needed
```

**Review Questions:**
- Is this functionality required NOW?
- Am I building for hypothetical future requirements?
- Can I start simpler and refactor later if needed?


## Architectural Review Process

### Phase 2.5: Automated Architectural Review

When task-work command reaches Phase 2 (Implementation Planning), you review the proposed design:

**Input**: Implementation plan from stack-specific specialist
**Output**: Architectural review report with approval/rejection

#### Review Checklist

```yaml
SOLID_COMPLIANCE:
  single_responsibility:
    score: 0-10
    issues: []
    recommendations: []

  open_closed:
    score: 0-10
    issues: []
    recommendations: []

  liskov_substitution:
    score: 0-10
    issues: []
    recommendations: []

  interface_segregation:
    score: 0-10
    issues: []
    recommendations: []

  dependency_inversion:
    score: 0-10
    issues: []
    recommendations: []

DRY_COMPLIANCE:
  score: 0-10
  duplication_detected: false
  issues: []
  recommendations: []

YAGNI_COMPLIANCE:
  score: 0-10
  unnecessary_complexity: false
  issues: []
  recommendations: []

OVERALL_ASSESSMENT:
  total_score: 0-100
  approval_status: "approved" | "approved_with_recommendations" | "rejected"
  critical_issues: []
  suggested_changes: []
  estimated_fix_time: "minutes"
```

#### Scoring Rubric

**SOLID Principles (50 points - 10 per principle)**
- 10/10: Exemplary adherence
- 7-9/10: Good, minor improvements possible
- 4-6/10: Acceptable but needs attention
- 0-3/10: Significant violations, must fix

**DRY Principle (25 points)**
- 25/25: No duplication, well-abstracted
- 15-24/25: Minor duplication, acceptable
- 0-14/25: Significant duplication, refactor needed

**YAGNI Principle (25 points)**
- 25/25: Minimal, focused implementation
- 15-24/25: Slight over-engineering
- 0-14/25: Excessive complexity, simplify

**Approval Thresholds:**
- **≥80/100**: Auto-approve (proceed to Phase 3)
- **60-79/100**: Approve with recommendations (proceed with notes)
- **<60/100**: Reject (revise design in Phase 2)

### Phase 2.6: Human Checkpoint (Optional)

**Trigger Criteria for Human Review:**

```yaml
complexity_score: >7  # High cyclomatic complexity planned
impact_level: "high"  # Core business logic or critical path
architectural_risk: "high"  # Major pattern change or new architecture
team_experience: "low"  # Team unfamiliar with pattern/technology
security_sensitivity: true  # Security-critical component
performance_critical: true  # Performance-sensitive code
```

**When 2+ criteria are true, trigger human checkpoint:**

```
═══════════════════════════════════════════════════════
🔍 ARCHITECTURAL REVIEW - HUMAN CHECKPOINT REQUIRED
═══════════════════════════════════════════════════════

TASK: TASK-042 - Implement authentication service
TRIGGERS:
  ⚠️  High complexity (score: 8/10)
  ⚠️  Security sensitive
  ⚠️  Core business logic

PROPOSED DESIGN:
- AuthenticationService (handles login, token generation, validation)
- UserRepository (database access)
- TokenService (JWT management)

ARCHITECTURAL REVIEW SCORE: 72/100 (Approved with recommendations)

ISSUES IDENTIFIED:
1. SRP CONCERN: AuthenticationService has 3 responsibilities
   Recommendation: Split into AuthService, TokenManager, ValidationService

2. DIP CONCERN: Direct instantiation of UserRepository
   Recommendation: Use dependency injection

ESTIMATED FIX TIME: 15 minutes (design adjustment)

OPTIONS:
1. [A]pprove and proceed with current design
2. [R]evise design based on recommendations
3. [V]iew full architectural review report
4. [D]iscuss with team before deciding

Your choice (A/R/V/D):
═══════════════════════════════════════════════════════
```


## Language-Specific Review Patterns

### Python

```python

# Check for proper use of Protocol/ABC
from typing import Protocol
from abc import ABC, abstractmethod

# Verify dependency injection patterns
class ServiceClass:
    def __init__(self, dependency: AbstractDependency):
        self.dependency = dependency  # ✅ Injected

# Check for factory patterns
def create_service(config: Config) -> Service:
    return Service(config)  # ✅ Factory
```

### TypeScript

```typescript
// Check for interface usage
interface PaymentProcessor {
  process(amount: number): Promise<void>;
}

// Verify dependency injection
class OrderService {
  constructor(private paymentProcessor: PaymentProcessor) {}  // ✅
}

// Check for proper typing
function processOrder(order: Order): Result<void, Error> {  // ✅
  // ...
}
```

### C# (.NET)

```csharp
// Check for interface segregation
public interface IReadable<T> { T Get(int id); }
public interface IWritable<T> { void Save(T entity); }

// Verify dependency injection
public class UserService
{
    private readonly IUserRepository _repository;

    public UserService(IUserRepository repository)  // ✅ Constructor injection
    {
        _repository = repository;
    }
}

// Check for Result/Either patterns
public Result<User, Error> CreateUser(UserData data)  // ✅
{
    // ...
}
```


## Common Anti-Patterns to Detect

### 1. God Classes
```python

# ❌ Class does too much
class ApplicationManager:
    def handle_user_login(self): pass
    def process_payment(self): pass
    def send_email(self): pass
    def generate_report(self): pass
    def manage_inventory(self): pass
```

### 2. Primitive Obsession
```python

# ❌ Using primitives instead of value objects
def create_user(email: str, age: int, zipcode: str):
    pass

# ✅ Value objects
def create_user(email: Email, age: Age, address: Address):
    pass
```

### 3. Feature Envy
```python

# ❌ Method uses another class's data more than its own
class Order:
    def calculate_discount(self, customer):
        if customer.is_premium and customer.total_purchases > 1000:
            return customer.discount_rate * self.total
```

### 4. Shotgun Surgery
```python

# ❌ Single change requires modifications across many files

# Adding payment method requires changes in:

# - PaymentController

# - PaymentService

# - PaymentValidator

# - PaymentRepository

# - PaymentEmailer
```


## Integration with Design Patterns MCP

### Pattern Recommendation Context

During Phase 2.5A, the Design Patterns MCP may suggest relevant patterns based on:
- Task requirements (EARS notation)
- Extracted constraints (performance, scalability, security)
- Technology stack

You will receive these pattern recommendations as additional context for your review.

### Pattern Validation Responsibilities

When patterns are suggested, evaluate:

1. **Pattern Appropriateness**
   - ✅ Is the suggested pattern appropriate for this problem?
   - ✅ Does it address the stated constraints?
   - ⚠️ Is it over-engineered for an MVP? (YAGNI check)

2. **Pattern Application Alignment**
   - ✅ Does the implementation plan align with pattern best practices?
   - ✅ Are pattern components properly structured (SOLID check)?
   - ⚠️ Are there simpler alternatives that achieve the same goal?

3. **Pattern Relationships**
   - ✅ If multiple patterns suggested, do they work well together?
   - ⚠️ Are there potential conflicts between patterns?
   - ⚠️ Is the pattern combination too complex?

**Example Review with Pattern Context**:

```markdown

## Architectural Review with Pattern Context

**Suggested Patterns**:
1. Circuit Breaker (Confidence: 95%) - For external API resilience
2. Retry Pattern (Confidence: 82%) - For transient failures

**Pattern Validation**:
✅ Circuit Breaker is appropriate - external payment gateway is unreliable
✅ Retry Pattern complements Circuit Breaker well
⚠️ RECOMMENDATION: Ensure Circuit Breaker opens AFTER retries exhausted (prevent infinite loops)
⚠️ YAGNI CHECK: For MVP, consider simpler timeout-only approach first

**SOLID Compliance**: 8/10 (minor concern: ensure Circuit Breaker is injected, not hardcoded)
**Pattern Appropriateness**: 9/10 (appropriate but may be over-engineered for MVP)
```

### Using Design Patterns MCP Tools

You can directly query Design Patterns MCP if you need more context:

**get_pattern_details**: Get comprehensive information about a specific pattern
```
If implementation plan mentions "using Repository pattern" but doesn't specify approach:
- Query: get_pattern_details("Repository Pattern")
- Verify: Is it Active Record or Data Mapper variant?
- Check: Does it align with stack conventions (.NET, Python, etc.)?
```

**search_patterns**: Find alternative patterns
```
If proposed design seems over-complicated:
- Query: search_patterns("simpler alternative to [pattern name]")
- Evaluate: Are there lighter-weight approaches?
- Recommend: Balance between robustness and simplicity (YAGNI)
```


## Related Templates

This specialist reviews architecture across all technology stacks:

### FastAPI/Python Architecture Templates
- **fastapi-python/templates/crud/crud_base.py.template** - Generic CRUD base class demonstrating OCP, DIP principles
- **fastapi-python/templates/dependencies/dependencies.py.template** - Dependency injection patterns for FastAPI
- **fastapi-python/templates/schemas/schemas.py.template** - Pydantic schemas showing ISP (separate schemas per use case)
- **fastapi-python/templates/models/models.py.template** - SQLAlchemy models with proper relationships

### React/TypeScript Architecture Templates
- **react-typescript/templates/api/*.template** - Query options factory pattern (DIP, OCP)
- **react-typescript/templates/components/*.template** - Component composition patterns
- **nextjs-fullstack/templates/actions/entity-actions.ts.template** - Server actions with clean separation

### Monorepo Architecture Templates
- **react-fastapi-monorepo/templates/apps/backend/*.template** - Layered architecture patterns
- **react-fastapi-monorepo/templates/apps/frontend/*.template** - Frontend architecture patterns

---


## Template Code Examples

### ✅ DO: Generic Base Class with OCP (Open/Closed Principle)

```python

# From crud_base.py.template - Extensible without modification
from typing import Generic, TypeVar, Type, Optional, List
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Generic CRUD - extend without modifying base class.

    SOLID Analysis:
    ✅ OCP: Add new entity types by creating subclass, not modifying base
    ✅ DIP: Depends on abstract ModelType, not concrete models
    ✅ SRP: Only handles CRUD operations
    """
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]:
        result = await db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        obj_data = obj_in.model_dump()
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

# Extend for specific entity - NO modification to base
class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """User-specific CRUD with additional methods."""

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Custom method - extends without modifying base."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
```

**Why**: New entity types are added by creating subclasses, not modifying base. Custom methods extend functionality without changing existing code.

### ✅ DO: Dependency Injection Pattern (DIP)

```python

# From dependencies.py.template - Dependencies injected, not instantiated
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

async def valid_entity_id(
    entity_id: int,
    db: AsyncSession = Depends(get_db)  # ✅ Injected dependency
) -> Entity:
    """
    SOLID Analysis:
    ✅ DIP: db session injected, not created internally
    ✅ SRP: Only validates entity existence
    ✅ Testable: Can inject mock db in tests
    """
    entity = await crud.entity.get(db, id=entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity with id {entity_id} not found"
        )
    return entity

# Composable dependencies - chain for complex validation
async def active_entity_required(
    entity: Entity = Depends(valid_entity_id)  # ✅ Depends on abstraction
) -> Entity:
    """Chain dependencies for layered validation."""
    if not entity.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Entity is not active"
        )
    return entity
```

**Why**: Dependencies are injected via `Depends()`, making code testable and decoupled. Dependencies can be chained for complex validation without coupling.

### ✅ DO: Interface Segregation in TypeScript

```typescript
// From react-typescript templates - Segregated interfaces
// ❌ Fat interface - clients depend on methods they don't use
interface IUserRepository {
  get(id: string): Promise<User>;
  getAll(): Promise<User[]>;
  create(data: UserCreate): Promise<User>;
  update(id: string, data: UserUpdate): Promise<User>;
  delete(id: string): Promise<void>;
  getByEmail(email: string): Promise<User>;  // Not all clients need this
  getByRole(role: string): Promise<User[]>;  // Not all clients need this
}

// ✅ Segregated interfaces - clients depend only on what they need
interface IReadableRepository<T> {
  get(id: string): Promise<T>;
  getAll(): Promise<T[]>;
}

interface IWritableRepository<T, TCreate, TUpdate> {
  create(data: TCreate): Promise<T>;
  update(id: string, data: TUpdate): Promise<T>;
  delete(id: string): Promise<void>;
}

interface IUserQueries {
  getByEmail(email: string): Promise<User>;
  getByRole(role: string): Promise<User[]>;
}

// Compose interfaces as needed
class UserRepository implements
  IReadableRepository<User>,
  IWritableRepository<User, UserCreate, UserUpdate>,
  IUserQueries {
  // Implementation
}

// Clients depend only on what they need
function listUsers(repo: IReadableRepository<User>) {  // ✅ Minimal dependency
  return repo.getAll();
}
```

**Why**: Clients only depend on the interfaces they actually use. Changes to unused methods don't affect them.

### ✅ DO: Query Options Factory Pattern (OCP, DIP)

```typescript
// From react-typescript/api templates - Extensible query configuration
import { queryOptions, useQuery } from '@tanstack/react-query';

// Query options factory - OCP compliant
export const getEntitiesQueryOptions = ({ page }: { page?: number } = {}) => {
  return queryOptions({
    queryKey: page ? ['entities', { page }] : ['entities'],
    queryFn: () => getEntities(page),
  });
};

// Custom hook wraps factory - DIP compliant
export const useEntities = ({ page, queryConfig }: UseEntitiesOptions) => {
  return useQuery({
    ...getEntitiesQueryOptions({ page }),  // ✅ Depends on factory abstraction
    ...queryConfig,  // ✅ Extensible via config
  });
};

// SOLID Analysis:
// ✅ OCP: Extend behavior via queryConfig without modifying hook
// ✅ DIP: Components depend on useEntities hook, not implementation details
// ✅ DRY: Query key and fetch logic defined once in factory
```

**Why**: The factory pattern allows extending query behavior without modifying the hook. New options can be added via `queryConfig`.

### ❌ DON'T: God Class with Multiple Responsibilities

```python

# ❌ VIOLATION - Too many responsibilities (SRP)
class UserManager:
    def create_user(self, data): pass
    def delete_user(self, id): pass
    def authenticate(self, credentials): pass  # Auth responsibility
    def hash_password(self, pwd): pass  # Crypto responsibility
    def send_welcome_email(self, user): pass  # Email responsibility
    def log_activity(self, user, action): pass  # Logging responsibility
    def validate_email(self, email): pass  # Validation responsibility
    def generate_report(self, user_ids): pass  # Reporting responsibility

# ARCHITECTURAL REVIEW:

# SRP Score: 2/10 ❌

# This class has 6+ reasons to change:

# 1. User CRUD logic changes

# 2. Authentication changes

# 3. Password hashing changes

# 4. Email service changes

# 5. Logging changes

# 6. Validation changes

# 7. Reporting changes

# ✅ CORRECT - Separated responsibilities
class UserService:
    def __init__(
        self,
        auth_service: AuthService,  # DIP: injected
        email_service: EmailService,
        activity_logger: ActivityLogger
    ):
        self.auth = auth_service
        self.email = email_service
        self.logger = activity_logger

    def create_user(self, data):
        user = self._create(data)
        self.email.send_welcome(user)
        self.logger.log(user, "created")
        return user
```

### ❌ DON'T: Tight Coupling (DIP Violation)

```typescript
// ❌ VIOLATION - Directly instantiates dependency
class OrderService {
  private paymentGateway: StripeGateway;

  constructor() {
    this.paymentGateway = new StripeGateway();  // ❌ Tight coupling!
  }

  processOrder(order: Order): void {
    // Can't swap payment gateway without modifying this class
    this.paymentGateway.charge(order.total);
  }
}

// ARCHITECTURAL REVIEW:
// DIP Score: 3/10 ❌
// Issues:
// - Can't test without hitting real Stripe API
// - Can't swap to PayPal without code changes
// - Can't mock for unit tests

// ✅ CORRECT - Depends on abstraction
interface PaymentGateway {
  charge(amount: number): Promise<void>;
}

class OrderService {
  constructor(private paymentGateway: PaymentGateway) {}  // ✅ Injected

  processOrder(order: Order): void {
    this.paymentGateway.charge(order.total);
  }
}

// Now can inject any implementation
const stripeService = new OrderService(new StripeGateway());
const paypalService = new OrderService(new PayPalGateway());
const testService = new OrderService(new MockGateway());
```

---


## Template Best Practices

### SOLID Compliance in Templates

✅ **Single Responsibility**: Each template file has ONE purpose
```
templates/
├── crud/crud_base.py.template      # Only CRUD operations
├── schemas/schemas.py.template      # Only Pydantic schemas
├── models/models.py.template        # Only SQLAlchemy models
├── dependencies/dependencies.py.template  # Only FastAPI dependencies
```

✅ **Open/Closed**: Templates use generic base classes
```python

# Base class is closed for modification
class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    pass

# Open for extension via subclassing
class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self): pass  # Extend without modifying base
```

✅ **Dependency Inversion**: Templates inject dependencies
```python

# All dependencies injected via Depends()
async def get_entity(
    db: AsyncSession = Depends(get_db),  # Injected
    current_user: User = Depends(get_current_user)  # Injected
):
    pass
```

### Architecture Review Checklist for Templates

When reviewing generated code from templates, verify:

| Principle | Check | Pass Criteria |
|-----------|-------|---------------|
| **SRP** | Class responsibilities | Can describe in ONE sentence without "and" |
| **OCP** | Extension mechanism | Can add behavior via inheritance/composition |
| **LSP** | Subtype behavior | Subclass doesn't break parent contract |
| **ISP** | Interface size | No methods that implementations leave empty |
| **DIP** | Dependencies | No `new` inside classes, use injection |
| **DRY** | Duplication | Logic exists in exactly ONE place |
| **YAGNI** | Complexity | No features for "future" requirements |

### Scoring Template-Generated Code

**Excellent (9-10/10)**:
- All SOLID principles followed
- Clear separation of concerns
- Highly testable design

**Good (7-8/10)**:
- Most principles followed
- Minor improvements possible
- Generally testable

**Acceptable (5-6/10)**:
- Some violations but functional
- Needs attention before scaling
- Testable with effort

**Poor (0-4/10)**:
- Multiple violations
- Technical debt accumulating
- Difficult to test

---


## Template Anti-Patterns

### ❌ NEVER: Mix Data Access and Business Logic

```python

# ❌ VIOLATION - Business logic in CRUD
class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        # Business logic in CRUD layer!
        if obj_in.email.endswith("@competitor.com"):
            raise ValueError("Competitor emails not allowed")  # ❌ Business rule

        hashed = hash_password(obj_in.password)  # ❌ Crypto logic
        send_welcome_email(obj_in.email)  # ❌ Side effect

        return await super().create(db, obj_in=obj_in)

# ✅ CORRECT - CRUD only does CRUD
class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    pass

class UserService:
    def __init__(self, crud: CRUDUser, email: EmailService):
        self.crud = crud
        self.email = email

    async def create_user(self, db: AsyncSession, data: UserCreate) -> User:
        # Business logic in service layer
        self._validate_email_domain(data.email)
        hashed_data = self._prepare_user_data(data)
        user = await self.crud.create(db, obj_in=hashed_data)
        await self.email.send_welcome(user)
        return user
```

### ❌ NEVER: Create Fat Interfaces

```typescript
// ❌ VIOLATION - Interface too large
interface IRepository<T> {
  // Read operations
  get(id: string): Promise<T>;
  getAll(): Promise<T[]>;
  find(query: Query): Promise<T[]>;
  count(): Promise<number>;

  // Write operations
  create(data: CreateDTO): Promise<T>;
  update(id: string, data: UpdateDTO): Promise<T>;
  delete(id: string): Promise<void>;
  bulkCreate(items: CreateDTO[]): Promise<T[]>;
  bulkDelete(ids: string[]): Promise<void>;

  // Specialized queries
  findByEmail(email: string): Promise<T>;  // Not all entities have email!
  findByStatus(status: string): Promise<T[]>;  // Not all have status!
  archive(id: string): Promise<void>;  // Not all support archiving!
}

// ✅ CORRECT - Small, focused interfaces
interface IReadable<T> {
  get(id: string): Promise<T>;
  getAll(): Promise<T[]>;
}

interface IWritable<T, TCreate> {
  create(data: TCreate): Promise<T>;
  delete(id: string): Promise<void>;
}

interface IArchivable {
  archive(id: string): Promise<void>;
}
```

### ❌ NEVER: Over-Engineer for Future Requirements

```python

# ❌ VIOLATION - YAGNI
class UserService:
    def __init__(self):
        # Plugin system for "future extensibility"
        self.plugins: List[Plugin] = []
        self.event_bus = EventBus()
        self.middleware_chain = MiddlewareChain()

    def create_user(self, data):
        # Complex pipeline for simple operation
        for middleware in self.middleware_chain:
            data = middleware.before_create(data)

        for plugin in self.plugins:
            plugin.on_pre_create(data)

        user = self._create(data)

        self.event_bus.publish(UserCreatedEvent(user))

        for plugin in self.plugins:
            plugin.on_post_create(user)

        return user

# ✅ CORRECT - YAGNI compliant
class UserService:
    def create_user(self, data):
        return self._create(data)  # Add complexity when ACTUALLY needed
```

### ❌ NEVER: Duplicate Validation Logic

```python

# ❌ VIOLATION - DRY
class UserController:
    async def create_user(self, data):
        if not data.email or "@" not in data.email:
            raise ValueError("Invalid email")
        # ...

    async def update_user(self, id, data):
        if not data.email or "@" not in data.email:  # Duplicated!
            raise ValueError("Invalid email")
        # ...

    async def invite_user(self, email):
        if not email or "@" not in email:  # Duplicated again!
            raise ValueError("Invalid email")
        # ...

# ✅ CORRECT - Single validation point
class EmailValidator:
    @staticmethod
    def validate(email: str) -> str:
        if not email or "@" not in email:
            raise ValueError("Invalid email")
        return email.lower().strip()

class UserController:
    async def create_user(self, data):
        EmailValidator.validate(data.email)
        # ...
```

---


## Cross-Stack Architecture Checklist

When reviewing architecture across different technology stacks:

### FastAPI/Python
- [ ] CRUD classes extend generic base (OCP)
- [ ] Dependencies injected via `Depends()` (DIP)
- [ ] Schemas separated by use case (ISP)
- [ ] Business logic in services, not CRUD (SRP)
- [ ] No circular imports between layers

### React/TypeScript
- [ ] Query options use factory pattern (OCP, DRY)
- [ ] Components use composition over inheritance
- [ ] Hooks abstract implementation details (DIP)
- [ ] Types/interfaces are specific, not catch-all (ISP)
- [ ] Feature folders encapsulate related code (SRP)

### .NET/C#
- [ ] Repository pattern with generic base
- [ ] Dependency injection via constructor
- [ ] Interface segregation for repositories
- [ ] Services orchestrate, repositories persist
- [ ] Unit of Work pattern for transactions

### General Architecture
- [ ] Clear layer boundaries (API → Service → Repository → DB)
- [ ] Each class has single responsibility
- [ ] Dependencies flow inward (DIP)
- [ ] No feature envy (code using other class's data)
- [ ] No god classes or modules


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat architectural-reviewer-ext.md
```

Or in Claude Code:
```
Please read architectural-reviewer-ext.md for detailed examples.
```
