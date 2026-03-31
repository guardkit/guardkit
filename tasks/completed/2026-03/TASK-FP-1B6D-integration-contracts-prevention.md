---
id: TASK-FP-1B6D
title: Add Integration Contracts to feature-plan to prevent cross-task format mismatches
status: obsolete
superseded_by: [TASK-IC-6F94, TASK-IC-DD44, TASK-IC-B4E6]
superseded_reason: Decomposed after review (TASK-REV-9705) — complexity too high for single session, internal dependency requires split
created: 2026-02-18T00:00:00Z
updated: 2026-02-18T00:00:00Z
priority: high
task_type: feature
parent_review: TASK-REV-0E07
complexity: 6
dependencies: []
related_tasks:
  - TASK-REV-0E07  # Review that identified the root cause
  - TASK-DB-003    # Task that was blocked by the format mismatch
tags: [feature-plan, integration-contracts, autobuild, docker-fixtures, coach-validator]
---

# Add Integration Contracts to feature-plan to Prevent Cross-Task Format Mismatches

## Description

The docker_fixtures bug (TASK-DB-003 UNRECOVERABLE_STALL) was caused by a specification decomposition error: the feature planner split a user request into producer and consumer tasks without specifying the format contract at their boundary. TASK-INFR-5922 produced `DATABASE_URL=postgresql://...` (generic format) while TASK-DB-003 consumed it via `create_async_engine()` which requires `postgresql+asyncpg://` (framework-specific format). The mismatch was not detectable at task level because no component had cross-task visibility of the format constraint.

The deep analysis in `docs/reviews/autobuild-fixes/docker-fixtures-deep-analysis.md` shows this is a whole class of bug (MongoDB + Motor, Redis + aioredis, RabbitMQ + aio-pika, MySQL + aiomysql are all susceptible to the same structural problem). The fix must be technology-agnostic.

This task implements the four systemic prevention measures identified in the analysis, in priority order.

## Changes Required

### Change 1: Add Integration Contracts section to `/feature-plan` prompt template (Priority: High — 30 min)

**File:** `installer/core/commands/feature-plan.md` (and/or the feature planner agent prompt)

Add a mandatory `## §4: Integration Contracts` section to the feature planner output template. This section is required whenever the planner generates tasks where one task's output is consumed by another task's input (environment variables, config files, connection artifacts).

**Template to add:**

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

The planner prompt must also instruct the AI: "Whenever the user prompt mentions both an infrastructure service AND a consuming framework (e.g. 'PostgreSQL with SQLAlchemy async', 'Redis with aioredis', 'MongoDB with Motor'), you MUST generate an Integration Contract specifying the exact URL/connection format required by the consuming framework."

**Note:** This is a prompt-only change. It prevents the entire class of bug at planning time.

### Change 2: Add `consumer_context` to infrastructure task metadata schema (Priority: Medium — 2-3 hrs)

**Files:** Feature planner agent, task schema definitions, autobuild coach validator

When the feature planner generates an infrastructure task, it must include a `consumer_context` block in the task YAML metadata:

```yaml
consumer_context:
  - task: TASK-DB-xxx
    consumes: DATABASE_URL
    framework: "SQLAlchemy async (create_async_engine)"
    driver: "asyncpg"
    format_note: "URL must include +asyncpg dialect suffix for async engine"
```

The Coach validator must be updated to:
1. Read `consumer_context` from the task's metadata (if present)
2. For each entry, validate that the produced artifact's format is compatible with the declared consumer framework
3. Report format mismatches explicitly (not just "artifact is present")

The Coach does NOT need to know framework internals — it only needs to verify that the produced artifact matches the declared `format_note` constraint from the integration contract.

### Change 3: Generate seam test stubs from integration contracts (Priority: Medium — 3-4 hrs)

**Files:** Feature planner agent, possibly a new `seam_test_generator.py` utility

When `/feature-plan` generates integration contracts, it must also generate seam test stubs in the consuming task's test scaffolding:

```python
# Auto-generated from Integration Contract: database_connection_url
# Producer: TASK-INFR-xxxx | Consumer: TASK-DB-xxxx

@pytest.mark.seam
@pytest.mark.integration_contract("database_connection_url")
def test_infrastructure_output_compatible_with_consumer():
    """
    Verify that the infrastructure task's output artifact
    is consumable by the downstream task's framework.
    """
    artifact = get_env_exports("postgresql")["DATABASE_URL"]
    assert validate_connection_url_for_consumer(artifact), (
        f"Infrastructure artifact '{artifact}' is not compatible "
        f"with the declared consumer framework"
    )
```

The stub is generated with a placeholder `validate_connection_url_for_consumer` that the Player fills in with framework-specific validation. The key is that the seam test exists and must pass — the implementer cannot forget it.

### Change 4: Refactor `docker_fixtures.py` to consumer-aware URL generation (Priority: Low — 2-3 hrs, after Changes 1-3 proven)

**File:** The `docker_fixtures.py` fixture module in the FastAPI/Python template

Replace hardcoded connection URL formats with a consumer-context-aware design:

```python
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

`docker_fixtures.py` must not hardcode knowledge of asyncpg, aiomysql, Motor, or any other framework. Format specifics live in the integration contracts, not in the fixtures module.

## Acceptance Criteria

- [ ] `/feature-plan` output includes a mandatory `## §4: Integration Contracts` section whenever tasks have cross-task data dependencies
- [ ] When a user prompt mentions a service + consuming framework (e.g. "PostgreSQL with SQLAlchemy async"), the feature planner generates a contract specifying the exact connection URL format required by the consumer
- [ ] Infrastructure tasks generated by feature planner include `consumer_context` metadata when they produce artifacts consumed by other tasks
- [ ] The Coach validator reads `consumer_context` and validates artifact format compatibility (not just artifact existence)
- [ ] Feature planner generates seam test stubs from integration contracts in the consuming task's test scaffolding
- [ ] `docker_fixtures.py` in the FastAPI template accepts consumer context for URL format overrides and does not hardcode framework-specific URL schemes
- [ ] The pattern works for at least: PostgreSQL+asyncpg, MySQL+aiomysql — validates technology-agnosticism

## Constraints

- Change 1 (feature-plan template) MUST be done first — it is the primary prevention point
- Changes 2-3 depend on Change 1 being in place (they reference the contracts generated by Change 1)
- Change 4 MUST NOT be done until Changes 2-3 are proven — it is defence-in-depth, not a primary fix
- Do NOT hardcode SQLAlchemy, asyncpg, or any other framework into the prevention system — all technology specifics must come from the integration contracts
- Do NOT change FEAT-DG-001 data flow diagram logic — the integration contracts complement it (format mismatches), they do not replace it (missing connections)

## Implementation Notes

- See `docs/reviews/autobuild-fixes/docker-fixtures-deep-analysis.md` for full analysis, parallel scenarios table, and validation walkthrough
- The immediate fix (change `postgresql://` → `postgresql+asyncpg://` in docker_fixtures.py) is already done as TASK-FIX-0C22
- FEAT-FP-002 already includes `integration_points` in §4 mapping — this task formalises what those points must contain (format constraints, not just "these tasks interact")
- The Coach's adversarial intensity system already does full validation at complexity ≥5 — adding `consumer_context` gives the existing system what it needs to catch format mismatches without architectural changes

## Related Documentation

- `docs/reviews/autobuild-fixes/docker-fixtures-deep-analysis.md` — Root cause analysis and full prevention proposal
- `installer/core/commands/feature-plan.md` — Feature planner command spec (primary file to modify)
- `installer/core/agents/` — Feature planner agent definitions
- `.claude/rules/autobuild.md` — Autobuild Coach validation rules
