# Focused per-task feature file for TASK-NATS-PH1-006.
#
# Why this file exists (TASK-NATS-FIX-001):
#   The Coach's `independent_tests` path runs pytest over the master glue
#   `features/nats-fleet-integration/test_nats_fleet_integration.py`, which collects
#   every scenario in `nats-fleet-integration.feature` (30+ scenarios across nine
#   tasks). pytest-bdd v8 emits unbound peer-task scenarios as FAILED — making
#   the Coach gate `bdd_results.scenarios_failed == 0` deterministically
#   unsatisfiable for any single-task run. This focused file scopes pytest-bdd's
#   collection to exactly the one scenario this task owns.
#
# Source of truth: features/nats-fleet-integration/nats-fleet-integration.feature
#   - Background: lines 16-21
#   - Scenario:   lines 246-256 (@task:TASK-NATS-PH1-006)
#
# This file is a hand-maintained subset copy. If the master scenario evolves,
# update this copy in the same review.
#
# Removal: when GuardKit task TASK-FIX-CC-BDD lands an upstream fix, this
# file (and its sibling test_TASK-NATS-PH1-006.py) can be deleted.

@phase-1 @nats-fleet @feat-nats-001
Feature: study-tutor NATS Fleet Integration — TASK-NATS-PH1-006 focused subset
  As the study-tutor agent
  I want to participate in the NATS fleet alongside specialist-agent and forge
  So that jarvis (and any future fleet caller) can dispatch tutoring commands
  through the same canonical request/reply contract used by every other agent

  Background:
    Given the NATS server is reachable with valid APPMILLA credentials
    And the agent-registry KV bucket exists
    And the AGENTS and FLEET JetStream streams are provisioned
    And the study-tutor adapter is configured with agent_id "gcse-tutor"
    And the tutor business logic is wired through MCPAdapter

  # Why: SIGTERM mid-turn must not orphan an in-flight tutor session
  # [ASSUMPTION: confidence=high] Drain window is 30 seconds (specialist-agent _shutdown_timeout)
  @task:TASK-NATS-PH1-006
  @edge-case @phase-1 @lifecycle
  Scenario: SIGTERM during an in-flight tutor turn drains the request before deregistration
    Given the adapter is running and ready
    And a tutor_turn command is currently being processed
    When the adapter receives SIGTERM
    Then the in-flight tutor turn should be allowed to complete within 30 seconds
    And the result for that turn should reach the caller before the adapter exits
    And the registry entry should then be removed
