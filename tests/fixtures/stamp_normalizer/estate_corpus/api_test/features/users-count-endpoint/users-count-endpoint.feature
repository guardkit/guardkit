# Proposed by the factory coordinator; APPROVED by Rich 2026-07-27 ("spec-approved")
# Feature: Users Count Endpoint
# Stack: python
# Assumptions: 4 (see users-count-endpoint_assumptions.yaml — all confirmed 2026-07-27)
# Generated: 2026-07-26
# Purpose: the SECOND forge e2e run's demo feature — FEAT-UPT1-class (single task,
#   read-only) but data-bearing: it touches the real DB layer, so the mandatory
#   dependency_down_degradation negative path is meaningful, not vacuous.

@users-count-endpoint
Feature: Users Count Endpoint
  As an operator of the api_test service
  I want to query how many users are stored
  So that I can observe data growth without listing every record

  Background:
    Given the api_test service is running with its database available

  # Why: Core path — the count reflects the stored data (a seeded-data round-trip,
  # the shape the runtime-smoke layer verifies; a hardcoded response cannot fake it)
  @key-example @smoke
  Scenario: The count reflects the number of stored users
    Given 3 users exist in the store
    When I request the users count
    Then the request should succeed
    And the response should report a count of 3

  # Why: Just-inside boundary — an empty store is a real state, not an error
  @boundary
  Scenario: The count of an empty store is zero
    Given no users exist in the store
    When I request the users count
    Then the request should succeed
    And the response should report a count of 0

  # Why: The count must track writes — the data round-trip in motion
  @key-example
  Scenario: Creating a user increments the count
    Given 1 user exists in the store
    When I create a new user
    And I request the users count
    Then the response should report a count of 2

  # Why: Route coexistence — the count route must not shadow, or be shadowed by,
  # the user-by-id route (the /users/{user_id} pattern would otherwise capture
  # the literal path segment "count" and fail UUID parsing)
  # [ASSUMPTION: confidence=high] Declaring the count route before the by-id route resolves both correctly
  @edge-case
  Scenario: Requesting a user by id still works alongside the count route
    Given 1 user exists in the store
    When I request that user by their id
    Then the request should succeed
    And the response should be that user's record

  # Why: The endpoint is read-only — modification verbs are not part of its contract
  @negative
  Scenario: Attempting to modify the users count is rejected
    When I attempt to submit data to the users count endpoint
    Then the request should be rejected as unsupported

  # Why: The count is data-bearing, so a missing database cannot be papered over —
  # the honest degradation is a clear service-unavailable response, never a raw
  # server error or an invented number
  # [ASSUMPTION: confidence=medium] 503 with a clear cause is the right degradation for data-bearing reads (contrast /health, which reports 200-degraded about its OWN status)
  @edge-case
  Scenario: The count degrades honestly when the database is unavailable
    Given the database is unavailable
    When I request the users count
    Then the request should fail with a service-unavailable response
    And the response should name the database as the cause
