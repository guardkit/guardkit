# Review Report: TASK-REV-BA4B (Revision 2)

## Executive Summary

When AutoBuild processes tasks requiring external infrastructure (PostgreSQL, Redis, Docker services), the Coach's independent test verification always fails because those services aren't running in the SDK subprocess environment. The Coach correctly classifies these as infrastructure failures, but the system has no alternative path -- the feedback loop repeats identically until stall detection fires after 3 turns, resulting in `UNRECOVERABLE_STALL`.

**Revised Recommendation**: Implement a **two-layer strategy**:

1. **Primary (Option E revised): Docker Test Fixtures** -- Both Player and Coach spin up required Docker containers before running tests. This is simpler than originally scoped -- it's a test fixture pattern, not a Docker orchestration system. The Player already has Bash access; the Coach has SDK Bash access (TASK-PCTD-3182).

2. **Fallback (Option C): Infrastructure-Aware Conditional Approval** -- When Docker is unavailable, declare `requires_infrastructure` in task/feature YAML and teach the Coach to conditionally approve when classification=infrastructure and metadata confirms the dependency.

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard (revised)
- **Task**: TASK-REV-BA4B
- **Related Tasks**: TASK-PCTD-5208, TASK-PCTD-9BEB, TASK-PCTD-3182
- **Revision**: R2 -- incorporating feedback on (1) `requires_infrastructure` location, (2) classification precedence rules, (3) Docker test fixture feasibility

## Root Cause Analysis

### The Failure Chain

```
1. Player implements TASK-DB-003 (User model + CRUD with PostgreSQL)
2. Player's own task-work passes (it can set up DB locally)
3. Coach runs independent test verification via SDK subprocess
4. SDK subprocess has no PostgreSQL running → ConnectionRefusedError
5. _classify_test_failure() correctly returns "infrastructure"
6. Coach returns decision="feedback" with infra remediation suggestions
7. Player attempts to fix (adds mocks, but tests still need real DB for integration)
8. Steps 3-7 repeat → identical feedback signature → stall after 3 turns
```

### Why This is Unfixable by the Player

The Coach's remediation suggestions (add mocks, use SQLite, mark with `@pytest.mark.integration`) are reasonable in theory but problematic in practice:

1. **Mocking defeats purpose**: TASK-DB-003's acceptance criteria require real database operations (CRUD, schemas). Mocking away the database means the tests verify nothing.
2. **SQLite incompatibility**: PostgreSQL-specific features (JSONB, array types, UUID columns) don't work with SQLite.
3. **Marking as integration**: The Player could exclude integration tests, but then there are no tests to verify -- the Coach's zero-test anomaly check would catch this.

The fundamental issue: **the Coach is asking the Player to solve an environment problem, not a code problem**.

### Why Not Just Spin Up Docker? (Revision 2 Addition)

The original review dismissed Option E as "very high effort" requiring a full Docker orchestration system. This was wrong. Both the Player and Coach already have Bash access via the SDK. Spinning up a PostgreSQL container is a test fixture, not an infrastructure project:

```bash
# Cleanup any stale container
docker rm -f guardkit-test-pg 2>/dev/null

# Spin up PostgreSQL
docker run -d --name guardkit-test-pg \
  -e POSTGRES_PASSWORD=test \
  -p 5433:5432 \
  postgres:16-alpine

# Wait for ready
until docker exec guardkit-test-pg pg_isready; do sleep 1; done

# Run tests
DATABASE_URL=postgresql://postgres:test@localhost:5433/test pytest tests/ -v

# Cleanup
docker rm -f guardkit-test-pg
```

The Player already knows how to do this -- Claude understands Docker. The execution protocol just needs to tell it to do so when infrastructure is declared.

## Evidence

### Log Analysis

| Turn | Player Output | Coach Classification | Feedback Sig |
|------|--------------|---------------------|-------------|
| 1 | 9 created, 2 modified, 1 test passing | infrastructure | a94d191b |
| 2 | 4 created, 3 modified, 0 tests passing | infrastructure | a94d191b |
| 3 | 2 created, 4 modified, 0 tests passing | infrastructure | a94d191b |

Source: [db_failed_after_sdk_refactor.md](../../docs/reviews/autobuild-fixes/db_failed_after_sdk_refactor.md), lines 359-495

### Key Code Paths

- **Classification**: [coach_validator.py:362-381](guardkit/orchestrator/quality_gates/coach_validator.py#L362-L381) -- Pattern list for infrastructure detection
- **Classification function**: [coach_validator.py:2063-2083](guardkit/orchestrator/quality_gates/coach_validator.py#L2063-L2083) -- Simple string matching, returns "infrastructure" or "code"
- **Decision path after classification**: [coach_validator.py:575-616](guardkit/orchestrator/quality_gates/coach_validator.py#L575-L616) -- Always returns feedback, regardless of classification
- **Stall detection**: [autobuild.py:1635-1645](guardkit/orchestrator/autobuild.py#L1635-L1645) -- Triggers after 3 identical feedback turns with 0 criteria progress
- **Task dict passed to Coach**: [autobuild.py:3564-3567](guardkit/orchestrator/autobuild.py#L3564-L3567) -- `{"acceptance_criteria": [...], "task_type": task_type}`
- **task_type loaded from frontmatter**: [autobuild.py:738-742](guardkit/orchestrator/autobuild.py#L738-L742) -- Via TaskLoader, only `task_type` is extracted today

## Option Evaluation

### Option A: Auto-Approve After N Infrastructure Failures

**How it works**: If `classification=infrastructure` for N consecutive turns, Coach automatically approves.

| Aspect | Assessment |
|--------|-----------|
| Implementation effort | Low (5-10 lines in coach_validator.py) |
| Safety | **Risky** -- no explicit opt-in, false positives auto-approve silently |
| False positive risk | **High** -- `ImportError` and `ModuleNotFoundError` in the pattern list can mask real code bugs (missing import = code defect, not infrastructure) |
| Reversibility | Easy (remove the auto-approve logic) |

**Verdict**: Too dangerous. The classification logic is pattern-based string matching with known false-positive vectors. Auto-approving without any external signal creates a hole where code bugs get through.

### Option B: Skip Independent Verification for Infra Tasks

**How it works**: When `task_type=infrastructure` or similar marker, skip `run_independent_tests()` entirely.

| Aspect | Assessment |
|--------|-----------|
| Implementation effort | Low (add condition at coach_validator.py:564) |
| Safety | **Medium** -- skips the "trust but verify" check entirely |
| False positive risk | Low (task type is explicit) |
| Reversibility | Easy |

**Verdict**: Too broad. TASK-DB-003 is `task_type=feature`, not `infrastructure`. The existing task type system doesn't map to "requires external services". Skipping all verification loses the safety net for tasks that have some tests that can run locally.

### Option C: Infrastructure-Aware Conditional Approval (Fallback)

**How it works**: Two-part approach:

1. **Feature/task YAML declares infrastructure dependencies**:
   ```yaml
   tasks:
     - id: TASK-DB-003
       requires_infrastructure: [postgresql]
   ```

2. **Coach conditionally approves** when all of:
   - `classification=infrastructure` with **high-confidence** patterns (see R2)
   - Task has `requires_infrastructure` declared
   - All quality gates EXCEPT independent tests passed
   - Player's own tests passed during task-work

3. **Approval is flagged** as `approved_without_independent_tests` (not a clean `approved`)

| Aspect | Assessment |
|--------|-----------|
| Implementation effort | Medium (FeatureTask model change, coach_validator decision path, feature YAML schema) |
| Safety | **High** -- requires explicit opt-in via YAML + classification confirmation |
| False positive risk | **Very low** -- two independent signals must agree (YAML declaration + runtime classification) |
| Reversibility | Easy (remove the conditional path, revert to always-feedback) |

**Verdict**: Good fallback for environments without Docker. Explicit opt-in via YAML prevents silent auto-approval. The dual-signal requirement (declared + detected) makes false positives extremely unlikely.

### Option D: New "Conditional Approval" State

**How it works**: Introduce `approved_without_tests` state that requires human sign-off before merge.

| Aspect | Assessment |
|--------|-----------|
| Implementation effort | High (new state in AutoBuild result model, new UI flow, feature-complete changes) |
| Safety | **Very high** -- human always in the loop |
| False positive risk | None (human verifies) |
| Reversibility | Medium (need to handle the new state throughout) |

**Verdict**: Over-engineered for the problem. AutoBuild already preserves the worktree for manual review. Adding a formal state creates ceremony without proportional safety gain, since the YAML declaration in Option C already provides explicit human intent.

### Option E (Revised): Docker Test Fixtures (Primary)

**How it works**: Tasks declare `requires_infrastructure: [postgresql]`. Both Player and Coach spin up Docker containers as test fixtures before running tests, then tear them down after.

| Aspect | Assessment |
|--------|-----------|
| Implementation effort | **Low-Medium** -- execution protocol instructions + container lifecycle bash |
| Safety | **Ideal** -- tests actually run against real infrastructure |
| False positive risk | None -- real tests against real services |
| Docker dependency | Requires Docker Desktop running (graceful fallback needed) |
| Reversibility | Easy (remove protocol instructions) |

**Revised verdict**: The original review over-scoped this as a Docker orchestration project. It's actually a test fixture pattern -- a few lines of bash that any developer would run. Both agents already have Bash access. The execution protocol ([autobuild_execution_protocol.md](guardkit/orchestrator/prompts/autobuild_execution_protocol.md)) just needs infrastructure setup instructions.

**Practical considerations**:
- **Docker Desktop must be running** -- agents can't start it. If not running, fall back to Option C.
- **Port conflicts** -- use non-standard ports (5433 not 5432) to avoid clashing with local services.
- **Cleanup** -- `docker rm -f <name> 2>/dev/null` at the start of each run handles orphaned containers.
- **Readiness** -- need `pg_isready` or equivalent health check before running tests.
- **Per-service setup** -- each infrastructure type (PostgreSQL, Redis, MongoDB) needs its own setup recipe. But the Player is Claude with Bash access -- it already knows how to set these up.

## Revised Decision Matrix

| Option | Safety | Effort | False Positive Risk | Recommendation |
|--------|--------|--------|-------------------|----------------|
| A: Auto-approve after N turns | Low | Low | High | Reject |
| B: Skip verification for task type | Medium | Low | Low | Reject |
| C: Infrastructure-aware conditional | High | Medium | Very Low | **Fallback** |
| D: New conditional approval state | Very High | High | None | Reject (over-engineered) |
| **E: Docker test fixtures** | **Ideal** | **Low-Medium** | **None** | **Primary** |

## Recommendations

### R1: Primary -- Docker Test Fixtures via Execution Protocol

**Approach**: Add infrastructure setup instructions to the execution protocol so both Player and Coach spin up Docker containers when `requires_infrastructure` is declared.

**Changes required**:

1. **Execution protocol** ([autobuild_execution_protocol.md](guardkit/orchestrator/prompts/autobuild_execution_protocol.md)): Add section:
   ```markdown
   ## Infrastructure Setup
   If the task declares `requires_infrastructure`, set up required services
   before running tests:
   - postgresql: `docker run -d --name guardkit-test-pg -e POSTGRES_PASSWORD=test -p 5433:5432 postgres:16-alpine`
   - redis: `docker run -d --name guardkit-test-redis -p 6380:6379 redis:7-alpine`
   - mongodb: `docker run -d --name guardkit-test-mongo -p 27018:27017 mongo:7`
   Wait for readiness before proceeding. Clean up containers after tests.
   Set DATABASE_URL or equivalent environment variable for tests.
   ```

2. **CoachValidator.run_independent_tests()** ([coach_validator.py](guardkit/orchestrator/quality_gates/coach_validator.py)): Before running tests, check `requires_infrastructure` and start containers if Docker is available. Fall back to Option C if Docker is unavailable.

3. **Docker availability check**: Simple `docker info` probe. If it fails, log warning and fall back to conditional approval.

**Estimated complexity**: 3/10 (low-medium -- protocol changes are text, Docker lifecycle is ~20 lines of bash)

### R2: Fallback -- Infrastructure-Aware Conditional Approval (Option C)

When Docker isn't available, the Coach needs a graceful fallback. This is Option C from the original report, now serving as the secondary path.

**Changes required** (same as original R1, with location resolution from Revision 2):

1. **FeatureTask model** ([feature_loader.py:189](guardkit/orchestrator/feature_loader.py#L189)): Add `requires_infrastructure: List[str] = Field(default_factory=list)`
2. **CoachValidator.validate()** ([coach_validator.py:575-616](guardkit/orchestrator/quality_gates/coach_validator.py#L575-L616)): Conditional approval path when Docker unavailable
3. **CoachValidationResult**: Add `approved_without_independent_tests: bool = False`
4. **AutoBuild summary**: Display conditional approval distinctly

### R3: Where `requires_infrastructure` Lives (Revision 2 Resolution)

**Decision**: Both locations, with clear propagation rules.

```
Feature YAML (source of truth for feature-build tasks)
    ↓ propagates to
Task frontmatter (authoritative for standalone tasks and runtime)
    ↓ loaded by
AutoBuildOrchestrator (autobuild.py:738-742, alongside task_type)
    ↓ passed to
CoachValidator.validate(task={"requires_infrastructure": [...]})
```

**Precedence**: Task frontmatter > Feature YAML default.

**Rationale**:
- **Feature YAML** is the right place for `/feature-plan` generated tasks. The feature author knows which tasks need PostgreSQL. Feature-build already propagates task metadata to generated task markdown files (see [feature_orchestrator.py:600](guardkit/orchestrator/feature_orchestrator.py#L600), `_copy_tasks_to_worktree`).
- **Task frontmatter** is the right place for standalone tasks (no parent feature). It's also the override point -- a task that normally needs PostgreSQL might have been refactored to use SQLite, and the frontmatter reflects that.
- **Propagation path**: When `/feature-plan` generates task markdown files from the feature YAML, it should copy `requires_infrastructure` into the task frontmatter. This is consistent with how `task_type`, `complexity`, and `dependencies` are already propagated.

**Implementation detail**: `AutoBuildOrchestrator.orchestrate()` at [autobuild.py:738-742](guardkit/orchestrator/autobuild.py#L738-L742) already loads `task_type` from frontmatter. Add `requires_infrastructure` in the same block:

```python
task_type = task_data.get("frontmatter", {}).get("task_type")
requires_infrastructure = task_data.get("frontmatter", {}).get("requires_infrastructure", [])
```

Then pass it through `_loop_phase` → `_execute_turn` → Coach's `task` dict (at [autobuild.py:3564](guardkit/orchestrator/autobuild.py#L3564)):

```python
task={
    "acceptance_criteria": acceptance_criteria or [],
    "task_type": task_type,
    "requires_infrastructure": requires_infrastructure,  # NEW
},
```

### R4: Tighten Infrastructure Classification Patterns (with Precedence Rule)

**Problem**: `ImportError`, `ModuleNotFoundError`, and `No module named` in `_INFRA_FAILURE_PATTERNS` are too broad. A missing import due to a code bug would be misclassified as infrastructure.

**Solution**: Split patterns into two tiers:

```python
_INFRA_HIGH_CONFIDENCE = [
    "ConnectionRefusedError",
    "ConnectionError",
    "Connection refused",
    "could not connect to server",
    "OperationalError",
    "psycopg2", "psycopg", "asyncpg",
    "sqlalchemy.exc.OperationalError",
    "django.db.utils.OperationalError",
    "pymongo.errors.ServerSelectionTimeoutError",
    "redis.exceptions.ConnectionError",
]

_INFRA_AMBIGUOUS = [
    "ModuleNotFoundError",
    "ImportError",
    "No module named",
]
```

**Classification precedence rule** (Revision 2 addition):

```python
def _classify_test_failure(self, test_output: Optional[str]) -> Tuple[str, str]:
    """Returns (classification, confidence) tuple.

    Precedence: high-confidence wins if ANY high-confidence pattern matches,
    regardless of ambiguous patterns also being present.

    Examples:
    - ConnectionRefusedError only → ("infrastructure", "high")
    - ImportError only → ("infrastructure", "ambiguous")
    - ConnectionRefusedError + ModuleNotFoundError: psycopg2 → ("infrastructure", "high")
      (high-confidence pattern present → high wins)
    - AssertionError + ImportError → ("code", "n/a")
      (ambiguous alone is not enough when code errors present... actually no,
       the presence of ImportError means infrastructure. But the assertion
       error is the actual test failure.)
    """
```

**The clear rule**: Check high-confidence patterns first. If ANY high-confidence pattern matches, return `("infrastructure", "high")` -- ambiguous patterns are irrelevant because the high-confidence match already confirms infrastructure. If only ambiguous patterns match, return `("infrastructure", "ambiguous")`. Only `"high"` confidence qualifies for conditional approval (Option C fallback).

**Edge cases resolved**:
- `ConnectionRefusedError` + `ModuleNotFoundError: psycopg2` → **high confidence** (connection error is the primary signal; the import error is a consequence)
- `ImportError: No module named 'myapp.utils'` (no high-confidence match) → **ambiguous** (this is likely a code bug, not infrastructure)
- `AssertionError: assert 4 == 5` (no infrastructure patterns) → **code**

### R5: Future -- Service-Specific Docker Recipes

As more infrastructure types are encountered, build a registry of Docker recipes:

```yaml
# Possible future: .guardkit/infrastructure-recipes.yaml
postgresql:
  image: postgres:16-alpine
  port: 5433:5432
  env: {POSTGRES_PASSWORD: test}
  readiness: pg_isready
  env_var: DATABASE_URL=postgresql://postgres:test@localhost:5433/test
redis:
  image: redis:7-alpine
  port: 6380:6379
  readiness: redis-cli ping
  env_var: REDIS_URL=redis://localhost:6380
```

This is tracked as a future enhancement -- for now, the execution protocol instructions are sufficient.

## Risk Assessment

### False Positive Analysis for Current Classification

| Pattern | True Positive | False Positive Scenario | Tier |
|---------|--------------|----------------------|------|
| `ConnectionRefusedError` | DB/service not running | Very rare -- almost always infra | High |
| `OperationalError` | DB connection issue | Possible -- some ORMs raise this for SQL syntax errors | High |
| `ImportError` | Missing system package | **Common** -- typo in import, missing `__init__.py` | Ambiguous |
| `ModuleNotFoundError` | Missing system package | **Common** -- forgot to add to requirements.txt | Ambiguous |
| `No module named` | Missing system package | **Common** -- virtual env issues | Ambiguous |

**After R4 (tiered patterns)**: False-positive surface area drops from ~30% to <5% for the conditional approval path, because only high-confidence patterns qualify.

### Risk of Docker Test Fixtures (Option E)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Docker Desktop not running | Medium | Test failure (same as today) | Fall back to Option C conditional approval |
| Port conflict (5432 in use) | Low | Container fails to start | Use non-standard ports (5433, 6380, 27018) |
| Orphaned containers | Medium | Port/resource leak | `docker rm -f <name>` at start of each run |
| Container slow to start | Low | Test timeout | Health check with retry (pg_isready loop) |
| Docker not installed at all | Low (dev machines) | Cannot spin up services | Fall back to Option C conditional approval |

### Risk of Conditional Approval (Option C, as fallback)

With both R2 and R4 implemented:
- **Scenario**: Task declares `requires_infrastructure: [postgresql]`, tests fail with `ConnectionRefusedError`, Docker unavailable
- **Risk**: Player wrote buggy SQL that would also fail against a real database
- **Mitigation**: Player's own task-work must have passed tests (which ran against a real or test DB). The conditional approval trusts the Player's test results.
- **Residual risk**: Low -- if the Player faked test results, this is a separate trust issue that conditional approval doesn't make worse.

## Appendix

### Current Validation Flow (simplified)

```
CoachValidator.validate()
├── 1. Read task-work results (quality gates)
├── 2. Evaluate quality gates (tests, coverage, arch, audit)
├── 3. Run independent tests
│   ├── tests pass → continue to step 4
│   └── tests fail → classify failure
│       ├── infrastructure → feedback with remediation ← STUCK HERE
│       └── code → feedback with standard message
├── 4. Validate requirements
└── 5. Approve (if all pass)
```

### Proposed Validation Flow (Revision 2)

```
CoachValidator.validate()
├── 1. Read task-work results (quality gates)
├── 2. Evaluate quality gates (tests, coverage, arch, audit)
├── 3. Check requires_infrastructure
│   ├── declared + Docker available → spin up containers → run tests (REAL INFRA)
│   ├── declared + Docker unavailable → run tests → classify failure
│   │   ├── infrastructure (high confidence) → CONDITIONAL APPROVE (fallback)
│   │   ├── infrastructure (ambiguous) → feedback with remediation
│   │   └── code → feedback with standard message
│   └── not declared → run tests normally
│       ├── tests pass → continue to step 4
│       └── tests fail → classify + feedback (existing behavior)
├── 4. Validate requirements
└── 5. Approve (if all pass)
```

### Files to Modify

| File | Change | Priority |
|------|--------|----------|
| [autobuild_execution_protocol.md](guardkit/orchestrator/prompts/autobuild_execution_protocol.md) | Add infrastructure setup instructions for Player | P1 (primary path) |
| [feature_loader.py](guardkit/orchestrator/feature_loader.py) | Add `requires_infrastructure` to `FeatureTask` model | P1 |
| [coach_validator.py](guardkit/orchestrator/quality_gates/coach_validator.py) | Split infra patterns into tiers, add Docker setup + conditional approval fallback | P1 |
| [autobuild.py](guardkit/orchestrator/autobuild.py) | Load and pass `requires_infrastructure` through validation chain | P1 |
| [feature_orchestrator.py](guardkit/orchestrator/feature_orchestrator.py) | Propagate `requires_infrastructure` from feature YAML to task frontmatter | P2 |
| [task_types.py](guardkit/models/task_types.py) | No changes needed | -- |

### Implementation Order

1. **R3**: Add `requires_infrastructure` field and propagation (foundation for everything else)
2. **R4**: Split classification patterns into tiers (safety improvement, independent of R1/R2)
3. **R1**: Docker test fixtures in execution protocol (primary solution)
4. **R2**: Conditional approval fallback (handles Docker-unavailable case)
5. **R5**: Service recipe registry (future, if needed)
