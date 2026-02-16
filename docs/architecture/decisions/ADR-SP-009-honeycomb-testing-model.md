# ADR-SP-009: Honeycomb Testing Model for Seam-First Testing

- **Date**: 2026-02
- **Status**: Accepted

## Context

GuardKit has experienced repeated failures at technology boundaries despite having passing unit tests. Historical failures include:

- **FP-002**: `system_plan.py` was a stub (`pass` statement) — no Graphiti calls ever executed
- **FP-003**: Acceptance criteria wiring bug — `_execute_turn()` never passed criteria to `_invoke_coach_safely()`
- **FP-006**: `files_created` field always empty — delegation results writer never populated it

The pattern: **unit tests mock the exact seams where failures occur.** Each component works in isolation. The system fails at the joints.

GuardKit is a protocol-connected system of small components (slash commands → CLI → Python → Graphiti → FalkorDB → file I/O). Individual components are simple (30-500 lines). The complexity is entirely in the connections — seven technology boundaries for a single user command.

This matches Spotify's Honeycomb model observation: "The biggest complexity in a microservice is not within the service itself, but in how it interacts with others." When your units are small and focused, unit testing them is almost trivial but tells you very little about whether the system works.

Client applications have a different profile — complexity lives in business logic (calculations, state machines, UI behavior), not framework wiring. React rendering, .NET middleware, and HTTP routing are reliable and well-tested by framework maintainers.

## Decision

### For GuardKit (Platform Tool)

Adopt the **Honeycomb testing model** with seam-first emphasis:

- **60% seam/integration tests**: Test across exactly one technology boundary with real implementations on both sides
- **30% unit tests**: Dense algorithmic logic only (parsers, risk scoring, token estimation)
- **10% E2E smoke tests**: Full chain validation for critical paths

**Testing distribution:**
```
     E2E Smoke Tests (~10%)
    /                     \
   |   Seam/Integration    |
   |   Tests (~60%)        |    ← Primary investment
   |                       |
    \                     /
     Unit Tests (~30%)
```

**Seam test requirements:**
- Test across one boundary with real implementations on both sides
- No mocking of internal module boundaries (mock external services at protocol level only)
- Every orchestrator function must have at least one seam test (anti-stub gate)
- Focus on the eight critical seams: slash command → CLI, CLI → Python, orchestrator → modules, Python → Graphiti, Graphiti → FalkorDB, AutoBuild → Coach, task delegation → results writer, quality gates → state transitions

**Example seam test pattern:**
```python
# tests/seam/test_system_plan_seam.py
def test_cli_invokes_orchestrator_not_stub(self):
    """Verify CLI actually invokes run_system_plan() which calls upsert methods."""
    result = subprocess.run(
        ["guardkit", "system-plan", "TestProject", "--context", "spec.md", "--dry-run"],
        capture_output=True, text=True
    )
    # A stub would produce no output about entities
    assert "components" in result.stdout.lower() or "entities" in result.stdout.lower()
```

### For Client App Templates

Use **Kent C. Dodds' Trophy model** (feature/integration-first):

- **50% feature/integration tests**: Test user-meaningful scenarios across multiple components
- **30% unit tests**: Complex business logic (calculations, validations, state machines)
- **10% E2E tests**: Critical user journeys only (login, checkout, core workflow)
- **10% static analysis**: TypeScript strict mode, ESLint, or equivalent

**Testing distribution:**
```
        🏆  E2E (~10%)
      ___________
    /             \
   | Feature/       |
   | Integration    |    ← Primary investment (~50%)
   | Tests          |
    \_____________/
     Unit Tests (~30%)
      ___________
     Static/Types (~10%)
```

**Key principle:** "The more your tests resemble the way your software is used, the more confidence they can give you." Framework seams are reliable — test the business logic, not the framework wiring.

## Consequences

### Positive

**For GuardKit:**
- Seam tests catch stub functions and wiring bugs that unit tests miss
- Anti-stub gate requirement prevents orchestrators from being deployed as stubs
- Test distribution aligns with where failures actually occur (technology boundaries)
- New `tests/seam/` directory provides clear organization for boundary tests

**For client app templates:**
- Feature tests provide confidence that user scenarios work end-to-end
- Less focus on implementation details, more on behavior
- Better ROI per test (one feature test validates multiple components)
- Trophy model is widely adopted and well-documented (Kent C. Dodds, Testing Library ecosystem)

### Negative

**For GuardKit:**
- Seam tests are slower than unit tests (subprocess invocation, real I/O)
- Requires test fixtures for each boundary (test FalkorDB instances, sample spec files)
- Developers must understand which seam they're testing and mock at the right level

**For client app templates:**
- Integration tests require more setup than unit tests (test databases, MSW for API mocking)
- E2E tests with Playwright/Cypress can be flaky if not written carefully
- May tempt developers to skip unit tests for complex calculations

### Implementation Changes

1. **New test directory structure:**
   ```
   tests/
   ├── unit/           # Pure logic, no I/O
   ├── seam/           # NEW: Cross-boundary verification
   ├── integration/    # Module combinations
   └── e2e/            # Full chain smoke tests
   ```

2. **Quality gate updates:**
   - Add seam test requirement to feature plan template
   - Require at least one seam test per orchestrator function (anti-stub gate)
   - Coverage thresholds remain: ≥80% line, ≥75% branch

3. **Template guidance updates:**
   - React TypeScript template: Trophy model with feature tests, MSW for API mocking
   - FastAPI Python template: Trophy model with TestClient for endpoint tests
   - Next.js Fullstack template: Trophy model with separate frontend/backend test strategies
   - React-FastAPI Monorepo template: Honeycomb for shared libraries, Trophy for apps

4. **Documentation updates:**
   - Testing strategy guide explaining when to use each model
   - Seam test examples for each GuardKit technology boundary
   - Feature test examples for each client app template

## References

- [Testing Strategy: Seam-First Analysis](../../research/testing-strategy/testing-strategy-seam-first-analysis.md)
- Honeycomb model: [Spotify Engineering Blog, 2018](https://engineering.atspotify.com/2018/01/testing-of-microservices/)
- Trophy model: [Kent C. Dodds, 2018](https://kentcdodds.com/blog/write-tests)
- Failure patterns: [GuardKit Failure Patterns](../failure-patterns.md)
