# Deep Analysis: docker_fixtures.py Specification Gap — Root Cause and Technology-Agnostic Prevention

**Date:** 2026-02-18  
**Context:** TASK-REV-0E07 / TASK-DB-003 UNRECOVERABLE_STALL  
**Previous Analysis:** Traced specification chain to TASK-INFR-5922  
**This Document:** Deepens the analysis to total confidence, validates technology-agnosticism, and proposes systemic fixes

---

## 1. Restating the Problem Precisely

The original prompt to `/feature-plan` was:

> "Add PostgreSQL database integration using SQLAlchemy async with connection pooling, health check integration, and a sample users table with CRUD endpoints"

This prompt contains two critical pieces of information in a single sentence: **PostgreSQL** (the service) and **SQLAlchemy async** (the consuming framework). The feature planner decomposed this into separate tasks — one for Docker infrastructure (TASK-INFR-5922) and one for the database layer (TASK-DB-003). In doing so, the **relationship between the infrastructure output and the consumer's expectations** was lost.

TASK-INFR-5922's specification included `DATABASE_URL=postgresql://postgres:test@localhost:5433/test`. TASK-DB-003's code calls `create_async_engine(settings.DATABASE_URL)`. The URL format is correct for PostgreSQL but incorrect for SQLAlchemy's async dialect resolution, which requires `postgresql+asyncpg://`.

---

## 2. Why the Previous Analysis Is Incomplete

The previous analysis correctly identified the bug and traced it to the specification. However, it proposed three fixes that are all **SQLAlchemy-specific**:

1. Stack-aware fixture URLs that check for `asyncpg` in dependencies
2. A seam test asserting `+asyncpg` in the URL
3. Acceptance criteria specifying `postgresql+asyncpg://` format

These fixes prevent *this exact bug* from recurring. But they don't prevent the *class of bug* from recurring with different technologies. Consider parallel scenarios:

| Service | Infrastructure Output | Consumer Expectation | Same Class of Bug |
|---------|----------------------|---------------------|-------------------|
| PostgreSQL | `postgresql://` | SQLAlchemy async needs `postgresql+asyncpg://` | ✅ The bug we hit |
| MongoDB | `mongodb://host:27017` | Motor (async) needs `mongodb://host:27017/?serverSelectionTimeoutMS=5000` | Timeout format |
| Redis | `redis://host:6379` | aioredis needs `redis://host:6379/0` with DB index | Missing DB index |
| RabbitMQ | `amqp://guest:guest@host:5672` | aio-pika needs `amqp://guest:guest@host:5672//` (double slash for vhost) | Missing vhost |
| MySQL | `mysql://user:pass@host:3306/db` | aiomysql needs `mysql+aiomysql://user:pass@host:3306/db` | Missing dialect suffix |
| Elasticsearch | `http://host:9200` | elasticsearch-async needs `http://host:9200` with auth headers | Missing auth params |

Every one of these is the same structural problem: **an infrastructure task produces a connection artifact in a generic format, while a downstream task consumes it in a framework-specific format**. Hardcoding knowledge of `asyncpg` solves one cell in this table. We need to solve the whole table.

---

## 3. The Real Root Cause: Missing Producer-Consumer Contracts at Task Boundaries

### 3.1 What Happened at Feature Planning Time

When the feature planner received the prompt, it correctly identified that this feature needs Docker infrastructure (PostgreSQL) and application code (SQLAlchemy async). It decomposed these into separate tasks with separate specifications.

The problem is that the feature planner treated the infrastructure task's output as **self-contained** rather than as **an input to a downstream consumer**. The task spec for TASK-INFR-5922 says "set DATABASE_URL" but doesn't say "set DATABASE_URL *in a format compatible with TASK-DB-003's async engine*."

This is not a bug in one task specification. It's a **missing contract between tasks**.

### 3.2 Why the Coach Didn't Catch It

The Coach for TASK-INFR-5922 tested:
- Container starts → ✅
- Environment variable is set → ✅  
- `DATABASE_URL.startswith("postgresql://")` → ✅
- Container stops cleanly → ✅

All tests passed because the Coach validated the **producer's contract with itself** (did I produce a PostgreSQL URL?) rather than the **producer's contract with its consumer** (did I produce a URL that the downstream async engine can use?).

The Coach had no visibility into what TASK-DB-003 would need, because task-level coaches operate within task boundaries.

### 3.3 Why This Is a Feature Planner Responsibility

The feature planner is the *only* component that has visibility across all tasks in a feature. It sees both "Docker fixtures produce DATABASE_URL" and "SQLAlchemy async consumes DATABASE_URL." The planner is therefore the only component that can specify the format contract at the boundary.

This is directly analogous to the FEAT-DG-001 "disconnection rule" — write paths without corresponding read paths. But it's a subtler variant: **the paths are connected, but the data format at the boundary doesn't match**. Think of it as a "type mismatch" at an integration seam, not a missing connection.

---

## 4. Technology-Agnostic Framing

The generalised problem is:

> When a feature planner decomposes a user request into multiple tasks, any task that **produces an artifact consumed by another task** must have its output format constrained by the consumer's requirements, not just the producer's capabilities.

This gives us three technology-agnostic principles:

### Principle 1: Interface Contracts Must Be Feature-Level, Not Task-Level

The contract between "infrastructure produces a connection string" and "application code consumes a connection string" belongs in the **feature specification**, not in either task's specification. The feature planner must generate an explicit section like:

```
## Integration Contracts

### Contract: database_connection_url
- Producer: TASK-INFR-xxxx (Docker fixtures)
- Consumer: TASK-DB-xxxx (Database layer)  
- Format: Must be consumable by the declared async database driver
- Validation: Consumer's framework must accept the URL without modification
```

### Principle 2: Acceptance Criteria Must Include Consumer Compatibility

When a task produces an artifact consumed by another task, the acceptance criteria must include:

> "The output artifact is compatible with the consuming task's declared technology stack"

Not just "the artifact is valid in isolation." This is the difference between unit testing and integration testing applied to specifications.

### Principle 3: The Coach Must Validate Across Task Boundaries for Infrastructure Tasks

Infrastructure tasks are inherently cross-cutting — they exist to serve other tasks. The Coach for an infrastructure task should receive context about downstream consumers and validate format compatibility, not just lifecycle correctness.

---

## 5. Concrete Prevention Measures (Technology-Agnostic)

### 5.1 Feature Planner Enhancement: Mandatory Integration Contract Section

**What changes:** The `/feature-plan` command prompt template gets a new mandatory output section.

**When it triggers:** Whenever the planner generates tasks where one task's output is consumed by another task's input. Specifically, whenever:
- A task produces environment variables, configuration files, or connection artifacts
- Another task in the same feature declares a dependency on those artifacts

**Template addition:**

```markdown
## §4: Integration Contracts

For each cross-task data dependency, specify:

### Contract: {artifact_name}
- **Producer task:** TASK-xxx
- **Consumer task(s):** TASK-xxx, TASK-xxx
- **Artifact type:** environment variable / config file / API endpoint / etc.
- **Format constraint:** {What format must the artifact be in for the consumer to use it without modification?}
- **Validation method:** {How should the Coach verify this contract is met?}

⚠️ If any task produces an artifact consumed by another task and no integration
contract is specified, add one. Unspecified cross-task contracts are the #1 source
of integration-boundary bugs.
```

This is the data flow diagram from FEAT-DG-001, but for *data format* rather than just data *existence*. The two complement each other.

### 5.2 Coach Validation Enhancement: Consumer-Aware Infrastructure Testing

**What changes:** The Coach's validation instructions for infrastructure tasks include consumer context.

**How it works:** When the feature planner generates an infrastructure task, it includes a `consumer_context` block in the task metadata:

```yaml
# In task YAML metadata
consumer_context:
  - task: TASK-DB-003
    consumes: DATABASE_URL
    framework: "SQLAlchemy async (create_async_engine)"
    driver: "asyncpg"
    format_note: "URL must include +asyncpg dialect suffix for async engine"
```

The Coach then validates:
1. The artifact exists (current behaviour)
2. The artifact format is compatible with each declared consumer (new behaviour)

**Technology-agnostic pattern:** The Coach doesn't need to know SQLAlchemy internals. It needs to know that "the consumer expects format X" and then verify the produced artifact matches format X. The format expectation comes from the feature planner's integration contract, not from hardcoded framework knowledge.

### 5.3 Seam Test Generation from Integration Contracts

**What changes:** When `/feature-plan` generates integration contracts, it also generates seam test stubs.

**Template:**

```python
# Auto-generated from Integration Contract: database_connection_url
# Producer: TASK-INFR-xxxx | Consumer: TASK-DB-xxxx

@pytest.mark.seam
@pytest.mark.integration_contract("database_connection_url")
def test_infrastructure_output_compatible_with_consumer():
    """
    Verify that the infrastructure task's output artifact
    is consumable by the downstream task's framework.
    
    Contract: DATABASE_URL produced by docker_fixtures must be
    accepted by the consumer's connection factory without modification.
    """
    # Producer side: get the artifact
    artifact = get_env_exports("postgresql")["DATABASE_URL"]
    
    # Consumer side: verify the framework accepts it
    # (This test is generated as a stub — the implementer fills in
    #  the framework-specific validation)
    assert validate_connection_url_for_consumer(artifact), (
        f"Infrastructure artifact '{artifact}' is not compatible "
        f"with the declared consumer framework"
    )
```

The key insight: the seam test is **generated from the integration contract**, not written manually. When the contract says "Producer TASK-INFR → Consumer TASK-DB, artifact DATABASE_URL", the test skeleton is automatic. The implementer fills in the consumer-side validation.

### 5.4 docker_fixtures.py Architectural Fix: Consumer-Declared Format

**What changes:** `docker_fixtures.py` stops hardcoding connection URL formats. Instead, it accepts a format specification from the consumer context.

**Technology-agnostic pattern:**

```python
# Instead of hardcoded URLs per service...
DOCKER_FIXTURES = {
    "postgresql": {
        "image": "postgres:16",
        "env_export": {
            # Base URL — overridden by consumer context
            "DATABASE_URL": "postgresql://{user}:{password}@{host}:{port}/{database}"
        },
        "defaults": {
            "user": "postgres", "password": "test",
            "host": "localhost", "port": 5433, "database": "test"
        }
    }
}

# Consumer context overrides the URL scheme
CONSUMER_URL_SCHEMES = {
    # pattern: (framework_marker, url_scheme_override)
    # These come from integration contracts, not hardcoded knowledge
}

def get_env_exports(
    service: str,
    consumer_context: Optional[Dict] = None
) -> Dict[str, str]:
    """
    Get environment exports for a Docker fixture service.
    
    If consumer_context is provided, adapt the URL format to match
    what the consumer expects. This is the integration contract
    enforcement point.
    """
    fixture = DOCKER_FIXTURES[service]
    exports = {}
    
    for key, template in fixture["env_export"].items():
        url = template.format(**fixture["defaults"])
        
        if consumer_context and key in consumer_context:
            url = consumer_context[key].adapt_url(url)
        
        exports[key] = url
    
    return exports
```

This design means `docker_fixtures.py` doesn't need to know about asyncpg, aiomysql, Motor, or any other framework. It produces a base URL and the consumer context tells it how to adapt. New frameworks require a new consumer context entry, not a code change to the fixtures module.

---

## 6. Relationship to Existing Work

### FEAT-DG-001 (Mandatory Diagram Output)

FEAT-DG-001's data flow diagrams catch **missing connections** (writes without reads). This analysis catches **format mismatches at existing connections**. These are complementary:

| FEAT-DG-001 | This Analysis |
|-------------|---------------|
| "Is there a read path?" | "Does the read path accept the write format?" |
| Detects: disconnected paths | Detects: type mismatches at boundaries |
| Visual: red boxes for missing reads | Visual: could add format annotations to arrows |

The integration contract section proposed here could be the third diagram type in FEAT-DG-001 — an "interface type diagram" showing the expected format at each boundary.

### FEAT-FP-002 (Two-Phase Feature Plan)

FEAT-FP-002 already includes `integration_points` in the §4 mapping table and `coach_validation_commands` per task. The integration contract section proposed here formalises what `integration_points` should contain: not just "these tasks interact" but "this is the format contract at their boundary."

### Adversarial Intensity (Adversarial_Intensity_and_Workflow_Review.md)

For complexity ≥5, the Coach already does full validation including integration review. The gap is that the Coach doesn't currently receive cross-task format contracts. Adding `consumer_context` to the Coach's context window enables the existing intensity-based system to catch format mismatches at the appropriate complexity level.

---

## 7. Validation: Would This Have Caught the Bug?

Walking through the original scenario with these fixes in place:

1. **Feature planner** receives: "Add PostgreSQL database integration using SQLAlchemy async..."

2. **Feature planner** generates tasks including TASK-INFR (Docker fixtures) and TASK-DB (database layer)

3. **New: Integration Contract section** captures:
   - Producer: TASK-INFR, artifact: DATABASE_URL
   - Consumer: TASK-DB, framework: SQLAlchemy async with asyncpg
   - Format constraint: URL must include `+asyncpg` dialect for async engine

4. **TASK-INFR specification** includes `consumer_context` referencing the integration contract

5. **Player** implements docker_fixtures with consumer-aware URL generation

6. **Coach** receives consumer context and validates: "Does DATABASE_URL work with SQLAlchemy async?" — catches the format mismatch even if the Player got it wrong

7. **Seam test** auto-generated from the integration contract verifies the URL is accepted by `create_async_engine()`

The bug would be caught at **three independent points**: the specification (step 3), the Coach validation (step 6), and the seam test (step 7). Defence in depth.

### Would it work for the parallel scenarios?

| Scenario | Integration Contract Catches? | Coach Catches? | Seam Test Catches? |
|----------|------------------------------|----------------|-------------------|
| MongoDB + Motor timeout format | ✅ Contract specifies timeout params | ✅ Consumer context includes timeout | ✅ Motor.connect() validates |
| Redis + aioredis DB index | ✅ Contract specifies DB index format | ✅ Consumer context includes DB selection | ✅ aioredis.connect() validates |
| RabbitMQ + aio-pika vhost | ✅ Contract specifies vhost in URL | ✅ Consumer context includes vhost | ✅ aio-pika.connect() validates |
| MySQL + aiomysql dialect | ✅ Contract specifies +aiomysql | ✅ Consumer context includes dialect | ✅ create_async_engine() validates |

All scenarios are caught without any technology-specific hardcoding in the prevention system. The technology specifics live in the integration contracts, which are generated per-feature by the feature planner.

---

## 8. Implementation Priority

| # | Change | Effort | Impact | Priority |
|---|--------|--------|--------|----------|
| 1 | Immediate fix: change `postgresql://` to `postgresql+asyncpg://` in docker_fixtures.py | 5 min | Unblocks TASK-DB-003 | **Now** |
| 2 | Add Integration Contract section to `/feature-plan` prompt template | 30 min | Prevents entire class at planning time | **This week** |
| 3 | Add `consumer_context` to infrastructure task metadata schema | 2-3 hrs | Enables Coach cross-task validation | **Next sprint** |
| 4 | Generate seam test stubs from integration contracts | 3-4 hrs | Automates boundary testing | **Next sprint** |
| 5 | Refactor docker_fixtures.py to consumer-aware URL generation | 2-3 hrs | Systemic fix for fixtures module | **After #2-4 proven** |

The most important change is #2 — it's prompt-only, costs 30 minutes, and prevents the entire class of bug at the cheapest possible point (planning time). Everything else is defence in depth.

---

## 9. Summary

The docker_fixtures bug is not a coding error. It's a specification decomposition error where the feature planner split a user request into producer and consumer tasks without specifying the format contract at their boundary.

The technology-agnostic lesson: **whenever a feature planner decomposes work into tasks with cross-task data dependencies, it must explicitly specify the format contract at each boundary**. Without this, infrastructure tasks will produce artifacts in generic formats that may be incompatible with framework-specific consumers.

The fix is a mandatory "Integration Contracts" section in `/feature-plan` output, complementing FEAT-DG-001's data flow diagrams (which catch missing connections) with format specifications (which catch type mismatches at existing connections). Together, they cover both classes of integration boundary bug.
