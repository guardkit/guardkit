# Proposed by the factory coordinator (propose-review; AWAITING Rich's Gherkin review)
# Feature: User Lookup By Email
# Stack: python
# Assumptions: 4 (see users-by-email-endpoint_assumptions.yaml — all pending review)
# Generated: 2026-07-27
# Purpose: the THIRD forge e2e run's demo feature — the clean-routine-datum candidate.
#   Deliberately thin (the chain is under test, not the Player): expose the EXISTING
#   crud.get_user_by_email query as a route. The realism rung it adds over /users/count:
#   a parameterized read with validation (422), found/not-found (404) semantics.
#   DB-down degradation follows the convention /users/count established: 503 naming
#   the database — inherited precedent, not a new assumption.

@users-by-email-endpoint
Feature: User Lookup By Email
  As an operator of the api_test service
  I want to look up a user by their email address
  So that I can find a specific account without listing every record

  Background:
    Given the api_test service is running with its database available

  # Why: Core path — the lookup returns the stored record (seeded-data round-trip;
  # email is unique+indexed in the model, so exactly one match is possible)
  @key-example @smoke
  Scenario: An existing user is found by their email
    Given a user exists with email "ada@example.com"
    When I request the user by email "ada@example.com"
    Then the request should succeed
    And the response should be that user's public record

  # Why: Precision — with several users stored, the lookup returns exactly the match
  @boundary
  Scenario: The lookup returns exactly the matching user among several
    Given 3 users exist with distinct emails
    When I request the user by the second user's email
    Then the response should be the second user's public record

  # Why: A specific-resource lookup that finds nothing is a 404, mirroring the
  # by-id route's contract — not an empty 200
  @key-example
  Scenario: An unknown email returns not-found
    Given no user exists with email "ghost@example.com"
    When I request the user by email "ghost@example.com"
    Then the request should fail with a not-found response

  # Why: Input validation is the route's job — a malformed address never reaches the query
  @negative
  Scenario: A malformed email is rejected as invalid input
    When I request the user by email "not-an-email"
    Then the request should be rejected as invalid input

  # Why: Route coexistence — the literal segment "by-email" must be declared before
  # the /users/{user_id} pattern or it is captured as a user id and fails UUID parsing
  # [ASSUMPTION: confidence=high] Declaring by-email before by-id resolves both correctly
  @edge-case
  Scenario: Requesting a user by id still works alongside the by-email route
    Given 1 user exists in the store
    When I request that user by their id
    Then the request should succeed
    And the response should be that user's record

  # Why: Data-bearing read, DB down — the inherited /users/count convention applies
  @edge-case
  Scenario: The lookup degrades honestly when the database is unavailable
    Given the database is unavailable
    When I request the user by email "ada@example.com"
    Then the request should fail with a service-unavailable response
    And the response should name the database as the cause
