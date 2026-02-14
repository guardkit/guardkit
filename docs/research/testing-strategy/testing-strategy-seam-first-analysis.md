# Testing Strategy: Seam-First for Platform Tools, Feature-First for Client Apps

## The Problem We Keep Finding

Every major GuardKit failure in the last three months follows the same pattern:

| Failure | What Unit Tests Said | What Actually Happened |
|---------|---------------------|----------------------|
| `system_plan.py` stub | No tests existed (but task was "in_review") | `run_system_plan()` was `pass` — never called Graphiti |
| Acceptance criteria wiring | Coach tests passed with mocked criteria | `_execute_turn()` never passed criteria to `_invoke_coach_safely()` |
| `files_created` empty | Task-work tests passed | Delegation results writer never populated the field |
| `/system-overview` returns nothing | `get_system_overview()` unit tests pass | Works perfectly — but no data in Graphiti because write path was a stub |
| `add-context` false positives | Individual parser tests pass | CLI reported success but `add_episode` returned errors silently |

The pattern: **unit tests mock the exact seams where failures occur.** Each component works in isolation. The system fails at the joints.

This isn't a surprise when you look at GuardKit's architecture. It's a multi-layer CLI tool where every user action crosses 3-5 technology boundaries:

```
User types /system-plan
    → Claude Code reads .claude/commands/system-plan.md (slash command spec)
        → Claude Code invokes `guardkit system-plan` (CLI boundary)
            → Click CLI parses args, calls run_system_plan() (Python entry point)
                → run_system_plan() calls detect_mode() (internal module)
                → run_system_plan() calls SystemPlanGraphiti.upsert_*() (Graphiti client)
                    → Graphiti client calls FalkorDB (external service)
                → run_system_plan() calls ArchitectureWriter (file I/O)
```

That's **seven seams** for a single command. A unit test for `detect_mode()` tells you nothing about whether the slash command actually triggers the CLI, or whether the CLI actually calls `run_system_plan()`, or whether `run_system_plan()` actually calls `detect_mode()`.

## Three Testing Models: Which Fits Where?

### The Testing Pyramid (Traditional)

```
    /  E2E  \           Few, slow, expensive
   /________\
  / Integration \       Some, moderate speed
 /______________\
/   Unit Tests    \     Many, fast, cheap
/==================\
```

**Origin:** Mike Cohn, 2009. Designed for monolithic applications where most logic lives in functions and classes.

**Core assumption:** Most bugs are logic bugs catchable by testing individual units. Integration is secondary.

**Where it works:** Standard business applications, CRUD APIs, computational libraries — anywhere the complexity is in the algorithms, not the wiring.

### The Testing Trophy (Kent C. Dodds)

```
        🏆  E2E (few)
      ______
    /        \
   | Integration |      ← MOST effort here
   |  (many)     |
    \________/
      Static
```

**Origin:** Kent C. Dodds, 2018. Guillermo Rauch's insight: "Write tests. Not too many. Mostly integration."

**Core principle:** "The more your tests resemble the way your software is used, the more confidence they can give you." Integration tests give the best ROI because they test real interactions without the brittleness of full E2E.

**Where it works:** Frontend applications, API-backed services, anything where component interaction is more complex than component logic.

### The Testing Honeycomb (Spotify)

```
     Integrated
    /          \
   | Integration |      ← MAXIMUM effort here
   |  (dominant) |
    \          /
     Details
```

**Origin:** Spotify Engineering, 2018. Born from microservices pain.

**Core insight:** "The biggest complexity in a microservice is not within the service itself, but in how it interacts with others." Unit tests for a small service are almost trivial — the risk is entirely at the boundaries.

**Where it works:** Microservices, plugin architectures, multi-layer CLI tools, **anything where the system is composed of small pieces connected by protocols and contracts.**

## GuardKit Is a Honeycomb Problem

GuardKit isn't a monolith with complex algorithms. It's a **protocol-connected system of small components**:

- Slash command specs (markdown interpreted by Claude Code)
- CLI commands (Click framework, Python entry points)
- Planning modules (Python, each ~100-500 lines)
- Graphiti persistence layer (async Python, external service)
- Entity definitions (dataclasses, ~60-90 lines each)
- AutoBuild orchestrator (LangGraph, multi-phase)
- Quality gates (Coach agent, acceptance criteria checking)
- File I/O (markdown writers, task state management)

Each individual component is simple. The `detect_mode()` function is 30 lines. The `ComponentDef` dataclass is 80 lines. Even `graphiti_arch.py` at 358 lines is straightforward — it's just upsert methods.

**The complexity is entirely in the connections.** Does the CLI pass the right args to the Python function? Does the Python function actually call the Graphiti client? Does the Graphiti client format the data correctly for FalkorDB? Does the slash command trigger the CLI at all, or does Claude Code just follow the spec directly and skip the Python?

This is exactly Spotify's observation: when your units are small and focused, unit testing them is almost trivial but tells you very little about whether the system works.

### GuardKit's Seam Map

These are the technology boundaries where failures actually occur:

| Seam | Layer A | Layer B | Historical Failures |
|------|---------|---------|-------------------|
| **S1** | Slash command (.md) | CLI invocation | Claude Code sometimes follows spec directly, bypassing Python |
| **S2** | CLI (Click) | Python entry point | Args not passed, async wrapping issues |
| **S3** | Orchestrator function | Module calls | Stub functions (system_plan.py), missing calls |
| **S4** | Python code | Graphiti client | Connection failures, silent errors, false success |
| **S5** | Graphiti client | FalkorDB | Query format issues, index conflicts |
| **S6** | AutoBuild orchestrator | Coach agent | Wiring bugs (acceptance_criteria never passed) |
| **S7** | Task-work delegation | Results writer | files_created/files_modified empty |
| **S8** | Quality gates | State transitions | Tasks move to in_review with 0% criteria checked |

**Every major failure maps to one of these seams.** Unit tests don't cover them because they mock one side or the other.

### Recommended Testing Distribution for GuardKit

```
GuardKit Testing Honeycomb:

     E2E Smoke Tests (~10%)
    /                     \
   |   Seam/Integration    |
   |   Tests (~60%)        |    ← Primary investment
   |                       |
    \                     /
     Unit Tests (~30%)
```

**Seam tests (60% of effort):**

These test across exactly one boundary with real implementations on both sides:

- **CLI → Python:** Invoke `guardkit system-plan --context spec.md` as subprocess, verify Graphiti was called (or mock Graphiti at the network level, not the Python level)
- **Orchestrator → Modules:** Call `run_system_plan()` with a real `SystemPlanGraphiti` instance (backed by test FalkorDB or in-memory mock at the protocol level)
- **AutoBuild → Coach:** Run `_execute_turn()` with real `acceptance_criteria` parameter, verify Coach receives it
- **Quality Gate → State:** Create task file with unchecked criteria, attempt state transition, verify rejection

**Unit tests (30% of effort):**

Still valuable for dense logic:
- Spec parser regex patterns
- Risk score calculation in impact analysis
- Token budget estimation
- Entity type inference from fact patterns

**E2E smoke tests (10% of effort):**

Full chain validation — a few critical paths only:
- `/system-plan` with spec file → verify `/system-overview` returns data
- `/task-create` → `/task-work` → verify task file created with content
- AutoBuild single task → verify all phases execute

### Anti-Stub Seam Test Pattern

The specific test that would have caught the `system_plan.py` stub:

```python
# tests/seam/test_system_plan_seam.py

import subprocess
import json

class TestSystemPlanSeam:
    """Tests the seam between CLI and orchestrator.
    
    These tests verify that the CLI actually invokes
    the Python orchestrator and that the orchestrator
    actually calls Graphiti. They do NOT test Graphiti
    itself — that's a separate seam.
    """
    
    def test_cli_invokes_orchestrator_not_stub(self):
        """The CLI must invoke run_system_plan() which must
        call upsert methods — not just pass/return."""
        result = subprocess.run(
            ["guardkit", "system-plan", "TestProject",
             "--context", "tests/fixtures/minimal-spec.md",
             "--dry-run"],
            capture_output=True, text=True
        )
        # A stub would produce no output about entities
        assert "components" in result.stdout.lower() or \
               "entities" in result.stdout.lower(), \
            f"Orchestrator appears to be a stub. Output: {result.stdout}"
        assert result.returncode == 0
    
    def test_orchestrator_calls_graphiti_upsert(self):
        """Verify run_system_plan() actually calls upsert methods."""
        # Use a recording mock at the Graphiti protocol level
        # NOT a Python mock that replaces the function
        from unittest.mock import AsyncMock, patch
        from guardkit.planning.system_plan import run_system_plan
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti
        
        # Create real SystemPlanGraphiti with mock client
        mock_client = AsyncMock()
        mock_client.enabled = True
        sp = SystemPlanGraphiti(client=mock_client, project_id="test")
        
        # Call the real orchestrator
        import asyncio
        asyncio.run(run_system_plan(
            system_name="Test",
            context_file="tests/fixtures/minimal-spec.md",
            sp=sp
        ))
        
        # Verify it called upsert (a stub would call nothing)
        assert sp.upsert_component.call_count > 0, \
            "run_system_plan() never called upsert_component — likely a stub"
```

### Slash Command Seam Testing

The trickiest seam is S1 (slash command → CLI). Claude Code interprets the markdown spec and decides whether to call the CLI or handle it directly. This can't be unit tested — it requires observing what Claude Code actually does.

**Approach: Output-based verification**

```python
# tests/seam/test_slash_command_outputs.py

class TestSlashCommandOutputs:
    """Verify that slash commands produce expected side effects.
    
    We can't directly test Claude Code's interpretation of
    slash command specs, but we CAN verify that the expected
    outputs exist after a command runs.
    """
    
    def test_system_plan_produces_graphiti_entities(self):
        """After /system-plan runs, Graphiti must contain entities."""
        # Pre-condition: clear Graphiti test groups
        # Action: run the CLI command (simulating what the slash command should trigger)
        # Assert: Graphiti search returns entities
        pass
    
    def test_system_overview_reads_graphiti_data(self):
        """After entities exist, /system-overview must return them."""
        # Pre-condition: seed Graphiti with known entities
        # Action: run guardkit system-overview --format json
        # Assert: JSON output contains expected component count
        pass
```

## Client App Development: The Trophy Approach

For standard client applications (React frontends, .NET APIs, mobile apps), the picture is different. The complexity IS in the business logic, not in the wiring between framework layers.

### Why the Trophy Works for Client Apps

A typical React application:
- Components render based on props and state (testable logic)
- API calls follow standard patterns (fetch/axios)
- State management has complex business rules (Redux/Zustand)
- User flows cross multiple components (integration value)

The seams (React → browser DOM, fetch → API server) are well-understood, heavily tested by the frameworks themselves, and follow standard protocols. You don't need to verify that React actually renders your component — React works. You need to verify that your component does the right thing.

```
Client App Testing Trophy:

        🏆  E2E / Playwright (~10%)
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

### Feature/Integration Tests for Client Apps

These test user-meaningful scenarios across multiple components:

```python
# For a React app: test the feature, not the component
def test_user_can_complete_checkout():
    """Integration test: renders the checkout flow,
    fills in payment details, submits, verifies confirmation."""
    render(<CheckoutFlow />)
    # Uses MSW to mock API at the HTTP level (not function mocks)
    fill_in("Card number", "4242...")
    click("Pay now")
    expect(screen.get_by_text("Order confirmed")).to_be_visible()

# For a .NET API: test the endpoint, not the service
def test_create_order_returns_201():
    """Integration test: hits the real controller,
    uses in-memory database, verifies response."""
    client = app.create_test_client()
    response = client.post("/api/orders", json=order_data)
    assert response.status_code == 201
    assert response.json()["orderId"] is not None
```

### When Client Apps Need Seam Tests

Client apps occasionally have GuardKit-style seam problems:

- **Third-party integrations:** Payment gateways, OAuth providers, email services — use contract tests
- **Microservice boundaries:** If the app calls other services, test the contracts
- **Build pipeline:** If the build process is complex (mono-repo, code generation), test the pipeline

But these are the exception, not the primary testing investment.

## Comparison Summary

| Dimension | GuardKit / Platform Tools | Client Applications |
|-----------|--------------------------|-------------------|
| **Primary model** | Honeycomb (Spotify) | Trophy (Kent C. Dodds) |
| **Where bugs hide** | Technology seams | Business logic |
| **Biggest risk** | Components not connected | Components doing wrong thing |
| **Primary test type** | Seam/integration (60%) | Feature/integration (50%) |
| **Unit test role** | Dense logic only (30%) | Algorithm + component (30%) |
| **E2E role** | Smoke tests for critical paths (10%) | User journey validation (10%) |
| **What to mock** | External services only (at protocol level) | APIs (at HTTP level via MSW/WireMock) |
| **What NOT to mock** | Internal module boundaries | Internal function calls |
| **Key anti-pattern** | Mocking the seam you're trying to test | Testing implementation details |
| **Framework** | pytest + subprocess + test containers | Jest/Vitest + Testing Library + Playwright |

## Recommended Actions for GuardKit

### Immediate: Add Seam Test Category

Create `tests/seam/` directory alongside existing `tests/unit/` and `tests/integration/`:

```
tests/
├── unit/           # Existing: pure logic, no I/O
├── integration/    # Existing: module combinations  
├── seam/           # NEW: cross-boundary verification
│   ├── test_cli_to_python.py       # S2: CLI → Python entry points
│   ├── test_orchestrator_wiring.py # S3: Orchestrators → module calls
│   ├── test_graphiti_persistence.py# S4: Python → Graphiti
│   ├── test_autobuild_coach.py     # S6: AutoBuild → Coach wiring
│   └── test_quality_gate_state.py  # S8: Gates → state transitions
└── e2e/            # Full chain smoke tests
    ├── test_system_plan_chain.py   # /system-plan → /system-overview
    └── test_task_lifecycle.py      # create → work → complete
```

### Quality Gate Update

Add seam test requirement to feature plan template:

```markdown
## Testing Requirements
- [ ] Unit tests for dense logic (>80% coverage of algorithmic functions)
- [ ] Seam tests for every technology boundary the feature crosses
- [ ] At least one seam test verifies the primary function is not a stub
- [ ] E2E smoke test if feature introduces new user-facing command
```

### Anti-Stub Gate (Already In Progress)

The TASK-FIX-STUB-B anti-stub rule catches the symptom. Seam tests catch the cause — a stub can't pass a test that invokes it and checks for real side effects.

## Recommended Guidance for Client App Templates

For the React, .NET, and other client app templates:

```markdown
## Testing Requirements  
- [ ] Feature/integration tests for every user story (test behaviour, not implementation)
- [ ] Unit tests for complex business logic (calculations, validations, state machines)
- [ ] Contract tests for third-party API integrations
- [ ] E2E tests for critical user journeys only (login, checkout, core workflow)
- [ ] Static analysis (TypeScript strict mode, ESLint, or equivalent)
```

The key difference: client app templates should NOT emphasise seam testing because framework seams (React rendering, .NET middleware, HTTP routing) are reliable and well-tested by the framework maintainers. The testing investment should go toward verifying that the application logic is correct, not that the framework wiring works.

## Key Takeaway

**Test where the risk is:**

- For platform/tooling projects (GuardKit, RequireKit, AutoBuild): the risk is at the seams → test the seams
- For client applications: the risk is in the business logic → test the features
- For both: integration tests give better ROI than unit tests → "write tests, not too many, mostly integration"

The traditional pyramid's assumption — that most bugs are logic bugs — holds for application code but catastrophically fails for platform tooling where the units are simple but the connections are fragile.
