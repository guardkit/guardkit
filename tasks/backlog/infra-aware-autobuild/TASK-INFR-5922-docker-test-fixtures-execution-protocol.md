---
id: TASK-INFR-5922
title: Docker test fixtures in execution protocol for Player and Coach
status: backlog
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:00:00Z
priority: high
tags: [autobuild, docker, execution-protocol, infrastructure, player, coach]
task_type: feature
complexity: 4
parent_review: TASK-REV-BA4B
feature_id: FEAT-INFRA
wave: 2
implementation_mode: task-work
dependencies: [TASK-INFR-6D4F]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Docker test fixtures in execution protocol for Player and Coach

## Description

This is the **primary solution** for infrastructure-dependent tasks in AutoBuild. When a task declares `requires_infrastructure: [postgresql]`, both the Player and Coach should spin up Docker containers as test fixtures before running tests, then tear them down after.

Both agents already have Bash access via the SDK. Docker is a test fixture pattern, not an infrastructure project -- a few lines of bash that any developer would run.

### Player Side

Add infrastructure setup instructions to the execution protocol (`autobuild_execution_protocol.md`). The Player reads this protocol and follows its instructions, so it will automatically set up Docker containers when infrastructure is declared.

### Coach Side

Modify `CoachValidator.run_independent_tests()` to check `requires_infrastructure` and start Docker containers before executing tests. Requires a Docker availability check (`docker info`) with graceful fallback to TASK-INFR-24DB conditional approval when Docker is unavailable.

## Acceptance Criteria

- [ ] Execution protocol (`autobuild_execution_protocol.md`) includes infrastructure setup section
- [ ] Protocol specifies Docker recipes for common services: postgresql, redis, mongodb
- [ ] Protocol uses non-standard ports to avoid conflicts (5433, 6380, 27018)
- [ ] Protocol includes cleanup instructions (docker rm -f at start and end)
- [ ] Protocol includes readiness checks (pg_isready, redis-cli ping, etc.)
- [ ] Protocol instructs Player to set DATABASE_URL or equivalent env vars for tests
- [ ] `CoachValidator` checks Docker availability before attempting container setup
- [ ] `CoachValidator` starts declared infrastructure containers before `run_independent_tests()`
- [ ] `CoachValidator` tears down containers after test execution (including on failure)
- [ ] When Docker is unavailable, `CoachValidator` logs warning and allows fallback to TASK-INFR-24DB
- [ ] `requires_infrastructure` field from task dict is used to determine which containers to start
- [ ] Unit tests for Docker availability check and container lifecycle methods
- [ ] Integration test: Coach starts PostgreSQL container, runs test, tears down

## Key Files

- `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` - Player execution protocol
- `guardkit/orchestrator/quality_gates/coach_validator.py` - Independent test execution
- `guardkit/orchestrator/agent_invoker.py` - Player invocation (protocol injection)

## Implementation Notes

### Docker recipes (embed in protocol and Coach)

```bash
# PostgreSQL
docker rm -f guardkit-test-pg 2>/dev/null
docker run -d --name guardkit-test-pg -e POSTGRES_PASSWORD=test -p 5433:5432 postgres:16-alpine
until docker exec guardkit-test-pg pg_isready; do sleep 1; done
export DATABASE_URL=postgresql://postgres:test@localhost:5433/test

# Redis
docker rm -f guardkit-test-redis 2>/dev/null
docker run -d --name guardkit-test-redis -p 6380:6379 redis:7-alpine
sleep 1

# MongoDB
docker rm -f guardkit-test-mongo 2>/dev/null
docker run -d --name guardkit-test-mongo -p 27018:27017 mongo:7
sleep 2
```

### Docker availability check

```python
def _is_docker_available(self) -> bool:
    """Check if Docker is available and running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
```

### Coach validation flow change

```
run_independent_tests():
  if requires_infrastructure and docker_available:
    start_containers(requires_infrastructure)
    try:
      run_tests()
    finally:
      stop_containers(requires_infrastructure)
  elif requires_infrastructure and not docker_available:
    run_tests()  # will fail → classification → fallback to TASK-INFR-24DB
  else:
    run_tests()  # existing behavior
```
