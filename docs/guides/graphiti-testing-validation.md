# Graphiti Testing and Validation Guide

> **What is this guide?**
>
> This guide documents how to test and validate Graphiti integration in GuardKit. It covers running the E2E integration tests, manual validation procedures, and troubleshooting common issues.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Validation (5 Minutes)](#quick-validation-5-minutes)
- [Running E2E Integration Tests](#running-e2e-integration-tests)
- [Manual Validation Procedures](#manual-validation-procedures)
- [Test Categories](#test-categories)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Prerequisites

### Required Services

```bash
# Start Graphiti services (Neo4j + Graphiti)
cd path/to/guardkit
docker compose -f docker/docker-compose.graphiti.yml up -d

# Verify containers are running
docker ps --filter "name=neo4j"
```

**Expected containers:**
- `neo4j` - Graph database (port 7687 for Bolt, 7474 for HTTP)

### Required Environment Variables

```bash
# Option 1: Source from .env file
source .env

# Option 2: Set directly
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=password123
export GRAPHITI_ENABLED=true
export OPENAI_API_KEY=sk-your-key-here  # Required for embeddings
```

### Required Python Packages

```bash
# Core Graphiti package
pip install graphiti-core

# Test dependencies
pip install pytest pytest-asyncio
```

---

## Quick Validation (5 Minutes)

### Step 1: Check Status

```bash
guardkit graphiti status
```

**Expected output:**
```
Enabled: Yes
Neo4j URI: bolt://localhost:7687
Connection: OK
Health: OK
Seeded: No (or Yes if already seeded)
```

### Step 2: Seed Knowledge

```bash
# First time or to refresh
guardkit graphiti seed --force
```

**Expected output:**
```
Seeding Graphiti with GuardKit knowledge...
  ✓ product_knowledge (5 episodes)
  ✓ command_workflows (8 episodes)
  ✓ quality_gate_phases (6 episodes)
  ... (13 categories total)
Seeding complete: 67 episodes across 13 categories
```

### Step 3: Verify Queries

```bash
guardkit graphiti verify --verbose
```

**Expected output:**
```
Verifying Graphiti knowledge...

✓ Query: "What is GuardKit?"
  → Found: GuardKit is a lightweight task workflow system...

✓ Query: "How to invoke task-work?"
  → Found: Use /task-work TASK-XXX to execute phases 2-5.5...

✓ Query: "What are the quality phases?"
  → Found: Phase 2 (Planning), Phase 2.5 (Architectural Review)...

✓ Query: "What is the Player-Coach pattern?"
  → Found: Player implements, Coach validates, max 5 turns...

✓ Query: "How to use SDK vs subprocess?"
  → Found: Use SDK query() method, not subprocess to CLI...

Results: 5 passed, 0 failed
Verification complete!
```

---

## Running E2E Integration Tests

### Test File Location

```
tests/integration/graphiti/test_workflow_integration.py
```

### Running Mock Tests (No Infrastructure)

These tests use mocked Graphiti client and don't require Neo4j or OpenAI:

```bash
cd path/to/guardkit
source .env  # Ensure environment is set

# Run mock-based tests only
pytest tests/integration/graphiti/test_workflow_integration.py -v --no-cov -m "integration and not live"
```

**Expected output:**
```
tests/integration/graphiti/test_workflow_integration.py::TestSeedingWorkflow::test_seed_creates_metadata_episodes PASSED
tests/integration/graphiti/test_workflow_integration.py::TestSeedingWorkflow::test_seed_creates_marker_with_version PASSED
tests/integration/graphiti/test_workflow_integration.py::TestContextLoadingWorkflow::test_load_critical_context_structure PASSED
tests/integration/graphiti/test_workflow_integration.py::TestContextLoadingWorkflow::test_context_loading_graceful_degradation PASSED
tests/integration/graphiti/test_workflow_integration.py::TestContextLoadingWorkflow::test_context_loading_disabled_client PASSED
tests/integration/graphiti/test_workflow_integration.py::TestContextLoadingWorkflow::test_context_categories_comprehensive PASSED
tests/integration/graphiti/test_workflow_integration.py::TestCLICommandIntegration::test_status_command_fields PASSED
tests/integration/graphiti/test_workflow_integration.py::TestCLICommandIntegration::test_verify_command_queries PASSED
tests/integration/graphiti/test_workflow_integration.py::TestGracefulDegradation::test_empty_results_on_connection_error PASSED
tests/integration/graphiti/test_workflow_integration.py::TestGracefulDegradation::test_client_returns_disabled_when_not_enabled PASSED
tests/integration/graphiti/test_workflow_integration.py::TestGracefulDegradation::test_health_check_returns_false_on_error PASSED
tests/integration/graphiti/test_workflow_integration.py::TestWorkflowSequence::test_seed_then_verify_mock PASSED
tests/integration/graphiti/test_workflow_integration.py::TestClearAndReseed::test_clear_removes_marker PASSED

========== 13 passed in 2.34s ==========
```

### Running Live Tests (Requires Infrastructure)

These tests require Neo4j running and OPENAI_API_KEY set:

```bash
cd path/to/guardkit
source .env  # Must include OPENAI_API_KEY

# Run live tests
pytest tests/integration/graphiti/test_workflow_integration.py -v --no-cov -m "integration and live"
```

**Prerequisites checklist:**
- [ ] Neo4j running: `docker ps --filter "name=neo4j"`
- [ ] OPENAI_API_KEY set: `echo $OPENAI_API_KEY | head -c 10`
- [ ] graphiti-core installed: `pip show graphiti-core`

### Running All Integration Tests

```bash
cd path/to/guardkit
source .env

# All tests (mock + live)
pytest tests/integration/graphiti/test_workflow_integration.py -v --no-cov
```

---

## Manual Validation Procedures

### Phase 1: Infrastructure Verification

**Purpose:** Confirm Neo4j and Graphiti services are operational.

```bash
# 1. Check Docker containers
docker ps --filter "name=neo4j"

# 2. Check Graphiti status
guardkit graphiti status

# 3. Test Neo4j connection directly
docker exec -it neo4j cypher-shell -u neo4j -p password123 "RETURN 1"
```

### Phase 2: Seeding Verification

**Purpose:** Confirm knowledge is correctly seeded.

```bash
# 1. Clear existing data (optional, for clean start)
guardkit graphiti clear --force

# 2. Seed knowledge
guardkit graphiti seed --force

# 3. Verify seeded data
guardkit graphiti verify --verbose
```

### Phase 3: Workflow Integration Verification

**Purpose:** Confirm Graphiti context is loaded during command execution.

```bash
# Enable debug logging
export GUARDKIT_LOG_LEVEL=DEBUG

# Create a test task
guardkit task-create "Test Graphiti integration" --tags=testing

# Run task-work with verbose logging
guardkit task-work TASK-XXX --verbose 2>&1 | tee validation.log

# Check for Graphiti activity
grep -i "graphiti\|context\|knowledge" validation.log
```

**Look for:**
- "Loading context from Graphiti"
- Architecture decision references
- Quality gate information
- Pattern recommendations

### Phase 4: Graceful Degradation Verification

**Purpose:** Confirm GuardKit works when Graphiti is unavailable.

```bash
# 1. Stop Neo4j
docker compose -f docker/docker-compose.graphiti.yml stop neo4j

# 2. Run command (should work with warnings)
guardkit task-work TASK-XXX --verbose

# 3. Check for graceful degradation
# Should see warnings but command should complete

# 4. Restart Neo4j
docker compose -f docker/docker-compose.graphiti.yml start neo4j
```

---

## Test Categories

### TestSeedingWorkflow

Tests the complete seeding process:

| Test | Description | Requirements |
|------|-------------|--------------|
| `test_seed_creates_metadata_episodes` | Verifies episode metadata structure | Mock |
| `test_seed_creates_marker_with_version` | Verifies seeding marker creation | Mock |
| `test_live_seeding_and_verify` | Full seeding with real infrastructure | Live |

### TestContextLoadingWorkflow

Tests context loading for workflow commands:

| Test | Description | Requirements |
|------|-------------|--------------|
| `test_load_critical_context_structure` | Verifies context dictionary structure | Mock |
| `test_context_loading_graceful_degradation` | Tests fallback on connection errors | Mock |
| `test_context_loading_disabled_client` | Tests behavior when Graphiti disabled | Mock |
| `test_context_categories_comprehensive` | Verifies all knowledge categories loaded | Mock |
| `test_live_context_loading` | Real context loading from Neo4j | Live |

### TestCLICommandIntegration

Tests CLI commands:

| Test | Description | Requirements |
|------|-------------|--------------|
| `test_status_command_fields` | Verifies status output fields | Mock |
| `test_verify_command_queries` | Verifies verification queries | Mock |
| `test_live_cli_status_and_verify` | Real CLI execution | Live |

### TestGracefulDegradation

Tests fallback behavior:

| Test | Description | Requirements |
|------|-------------|--------------|
| `test_empty_results_on_connection_error` | Search returns empty on error | Mock |
| `test_client_returns_disabled_when_not_enabled` | Client reports disabled state | Mock |
| `test_health_check_returns_false_on_error` | Health check fails gracefully | Mock |

### TestWorkflowSequence

Tests end-to-end workflows:

| Test | Description | Requirements |
|------|-------------|--------------|
| `test_seed_then_verify_mock` | Mock seed → verify sequence | Mock |
| `test_live_seed_verify_query` | Real seed → verify → query | Live |

### TestClearAndReseed

Tests data management:

| Test | Description | Requirements |
|------|-------------|--------------|
| `test_clear_removes_marker` | Verifies clear removes seeding marker | Mock |
| `test_live_clear_and_reseed` | Real clear → reseed cycle | Live |

---

## Troubleshooting

### Tests Skipped Due to Missing OPENAI_API_KEY

**Symptom:**
```
SKIPPED [1] tests/integration/graphiti/test_workflow_integration.py:123:
  OPENAI_API_KEY not set - live tests require embedding API
```

**Solution:**
```bash
# Ensure .env file contains OPENAI_API_KEY
cat .env | grep OPENAI_API_KEY

# Source the environment
source .env

# Verify it's set
echo $OPENAI_API_KEY | head -c 10
# Should show: sk-xxxxxx...
```

### Neo4j Connection Refused

**Symptom:**
```
ConnectionRefusedError: [Errno 111] Connection refused
```

**Solution:**
```bash
# Check if container is running
docker ps --filter "name=neo4j"

# If not running, start it
docker compose -f docker/docker-compose.graphiti.yml up -d

# Wait for Neo4j to be ready (takes ~30 seconds)
sleep 30

# Verify connection
docker exec -it neo4j cypher-shell -u neo4j -p password123 "RETURN 1"
```

### graphiti-core Not Installed

**Symptom:**
```
ModuleNotFoundError: No module named 'graphiti_core'
```

**Solution:**
```bash
pip install graphiti-core
```

### Unknown Pytest Marker Warning

**Symptom:**
```
PytestUnknownMarkWarning: Unknown pytest.mark.live
```

**Solution:** Verify `pytest.ini` contains the marker:
```ini
markers =
    live: Live tests requiring real infrastructure (Neo4j, OPENAI_API_KEY)
```

### Seeding Fails with Embedding Error

**Symptom:**
```
openai.AuthenticationError: Incorrect API key provided
```

**Solution:**
```bash
# Verify API key is valid
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  | head -c 100

# If error, check the key in .env
cat .env | grep OPENAI_API_KEY

# Re-source environment
source .env
```

### Tests Pass But Commands Don't Show Context

**Symptom:** Tests pass but `guardkit task-work` doesn't show Graphiti context.

**Diagnosis:**
```bash
# Check if Graphiti is enabled
guardkit graphiti status

# Check if data is seeded
guardkit graphiti verify --verbose

# Enable debug logging
export GUARDKIT_LOG_LEVEL=DEBUG
guardkit task-work TASK-XXX --verbose 2>&1 | grep -i graphiti
```

---

## See Also

- **[Graphiti Integration Guide](graphiti-integration-guide.md)** - Setup and usage overview
- **[Graphiti Project Namespaces](graphiti-project-namespaces.md)** - Multi-project isolation
- **[GuardKit Workflow](guardkit-workflow.md)** - How Graphiti integrates with commands
- **[Troubleshooting Guide](troubleshooting.md)** - General GuardKit troubleshooting

---

## Summary

**Quick Validation:**
```bash
source .env
guardkit graphiti status
guardkit graphiti seed --force
guardkit graphiti verify --verbose
```

**Running Tests:**
```bash
# Mock tests (no infrastructure)
pytest tests/integration/graphiti/test_workflow_integration.py -v --no-cov -m "integration and not live"

# Live tests (requires Neo4j + OPENAI_API_KEY)
source .env
pytest tests/integration/graphiti/test_workflow_integration.py -v --no-cov -m "integration and live"

# All tests
source .env
pytest tests/integration/graphiti/test_workflow_integration.py -v --no-cov
```

**Test Coverage:**
- 18 total tests (13 mock, 5 live)
- 6 test classes covering seeding, context loading, CLI, degradation, workflows, and data management
- Mock tests run without infrastructure for CI/CD
- Live tests validate real integration with Neo4j and OpenAI
