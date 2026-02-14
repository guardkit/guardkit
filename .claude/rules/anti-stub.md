---
paths: guardkit/**/*.py, src/**/*.py, src/**/*.ts, src/**/*.cs
---

# Anti-Stub Quality Rule

> Stubs that pass quality gates are worse than failing code — they silently ship nothing.

## Stub Definition

A **stub** is a function or method whose body consists solely of one or more of:

1. **`pass`** (possibly preceded by a docstring or logger call)
2. **`raise NotImplementedError(...)`**
3. **Only comments**: `# TODO`, `# FIXME`, `# STUB`, `# placeholder`
4. **Hardcoded defaults with no logic**: `return None`, `return {}`, `return []`, `return ""`, `return 0`, `return False`
5. **Logging-only**: `logger.info(...)` + `pass` or bare `return`
6. **Ellipsis**: `...` as the entire body

A function that contains conditional logic, calls to domain-specific dependencies, data transformations, or meaningful error handling is **not** a stub, even if parts of it are incomplete.

## Enforcement by Task Type

### FEATURE and REFACTOR Tasks: Stubs are REJECTED

For tasks with type FEATURE or REFACTOR, **primary deliverable functions MUST NOT be stubs**.

The Coach MUST reject (return feedback, not approve) if any primary deliverable function:
- Has a body consisting entirely of stub patterns listed above
- Contains only logging + `pass`/`return`
- Defers all logic to a `# TODO` comment

### SCAFFOLDING and INFRASTRUCTURE Tasks: Stubs are PERMITTED

SCAFFOLDING and INFRASTRUCTURE tasks MAY create stubs **only when** the task's acceptance criteria explicitly state that stubs are acceptable (e.g., "create interface with placeholder implementation").

### DOCUMENTATION and TESTING Tasks: Not Applicable

Documentation and testing tasks do not produce primary deliverable functions, so this rule does not apply.

### INTEGRATION Tasks: Stubs are REJECTED for Wiring Logic

Integration tasks must contain working wiring logic (connecting components, calling real APIs). Stub wiring defeats the purpose.

## Primary Deliverable Function

A **primary deliverable function** is any function or method that:

1. Is **named or implied** by the task's acceptance criteria (e.g., if AC says "implement `run_system_plan()`", then `run_system_plan()` is primary)
2. Is the **main entry point** of a module created by the task
3. Is **called by the task's test suite** to exercise core behavior
4. Provides the **core logic** that the task was created to deliver

Functions that are legitimately thin wrappers (CLI entry points calling orchestrators, adapter methods delegating to a library) are NOT stubs — they have a clear purpose even if short.

## Concrete Examples

### Stub (REJECTED for FEATURE/REFACTOR)

```python
# Example 1: pass-only stub
async def run_system_plan(description: str, mode: str) -> None:
    """Main orchestration logic for system-plan command."""
    logger.info(f"run_system_plan called with {description}")
    pass

# Example 2: NotImplementedError stub
def process_payment(order_id: str, amount: float) -> PaymentResult:
    """Process a payment for the given order."""
    raise NotImplementedError("Payment processing not yet implemented")

# Example 3: hardcoded default stub
def get_user_preferences(user_id: str) -> dict:
    """Retrieve user preferences from the database."""
    return {}

# Example 4: TODO-only stub
def validate_input(data: dict) -> ValidationResult:
    # TODO: implement validation logic
    # FIXME: add schema checks
    return ValidationResult(valid=True, errors=[])
```

### Non-Stub (ACCEPTED)

```python
# Example 1: Real implementation with logic
async def run_system_plan(description: str, mode: str) -> None:
    """Main orchestration logic for system-plan command."""
    detected_mode = detect_mode(description) if mode is None else mode
    questions = generate_questions(detected_mode, description)
    answers = await collect_answers(questions)
    plan = build_plan(detected_mode, answers)
    await write_plan_files(plan)

# Example 2: Thin wrapper (NOT a stub — legitimate delegation)
@click.command()
@click.argument("description")
def system_plan(description: str) -> None:
    """CLI entry point for system-plan."""
    asyncio.run(run_system_plan(description, mode=None))

# Example 3: Minimal but real logic
def is_valid_email(email: str) -> bool:
    """Validate email format."""
    return bool(re.match(r'^[^@]+@[^@]+\.[^@]+$', email))

# Example 4: Partial implementation (acceptable if remaining work is non-primary)
def process_order(order: Order) -> OrderResult:
    """Process an order through the pipeline."""
    validated = validate_order(order)
    if not validated.is_valid:
        return OrderResult(success=False, errors=validated.errors)
    charge_result = charge_payment(order.payment_info)
    # TODO: add notification step (non-primary, enhancement)
    return OrderResult(success=True, order_id=order.id)
```

## Coach Verification Checklist

When reviewing a FEATURE or REFACTOR task, the Coach MUST:

1. **Identify** primary deliverable functions from the acceptance criteria
2. **Read** the function body (using Read tool, not just file names)
3. **Check** if the body matches any stub pattern defined above
4. **Reject** with specific feedback if stubs are found:
   - Name the stub function and its file location
   - Quote the stub body
   - State which acceptance criterion it violates
   - Provide guidance on what "real implementation" means for that function

## Feedback Template

When rejecting a stub, the Coach should provide feedback like:

```
STUB DETECTED: `run_system_plan()` in guardkit/planning/system_plan.py

The function body is:
    logger.info(...)
    pass

This is a stub (logging + pass pattern). For task type FEATURE, primary
deliverable functions must contain meaningful implementation logic.

AC-001 requires: "System plan orchestration coordinates mode detection,
question flow, and file writes."

The function must contain actual orchestration logic — calling
detect_mode(), generating questions, collecting answers, and writing
plan files.
```
