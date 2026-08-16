# APPROVED AS PROPOSED by Rich 2026-07-28 (interactive sit; all 4 assumptions confirmed, ASSUM-003 = 404 honest absence)
# Feature: Delete User By Email
# Stack: python
# Assumptions: 4 (see users-delete-by-email_assumptions.yaml — ALL CONFIRMED 2026-07-28)
# Generated: 2026-07-28
# Purpose: the next routine-sit feature — deliberately thin (pure reuse of two
#   proven seams: crud.get_user_by_email + crud.delete_user). The realism rung it
#   adds: a DESTRUCTIVE operation whose pass-bar demands a real round-trip (delete
#   then look up ⇒ 404 — a hardcoded response cannot fake actual deletion).
#   Conventions inherited: EmailStr 422-before-DB, 404 detail shape, the
#   /users/count 503 DB-down convention, and DELETE-group route order (literal
#   /by-email declared BEFORE /{user_id} — the FEAT-UCNT/UBEM precedent, now in
#   the DELETE method group). THIS TASK ALSO CARRIES THE FACTORY'S FIRST
#   `conformance:` BLOCK (FEAT-SCG machinery, live proof-of-life).

@users-delete-by-email
Feature: Delete User By Email
  As an operator of the api_test service
  I want to delete a user by their email address
  So that I can remove an account without first looking up its id

  Background:
    Given the api_test service is running with its database available

  # Why: Core path — the deletion actually removes the record (the round-trip:
  # a subsequent lookup by the same email must honestly miss)
  @key-example @smoke
  Scenario: An existing user is deleted by their email
    Given a user exists with email "ada@example.com"
    When I delete the user by email "ada@example.com"
    Then the request should succeed with no content
    And looking up the user by email "ada@example.com" should find nothing

  # Why: Precision — with several users stored, only the matching user is removed
  @boundary
  Scenario: Deleting by email removes exactly the matching user
    Given 3 users exist with distinct emails
    When I delete the user by the second user's email
    Then looking up the second user's email should find nothing
    And the other two users should still exist

  # Why: An unknown email is a 404, mirroring the by-email lookup's contract
  @key-example
  Scenario: Deleting an unknown email reports not found
    Given no user exists with email "ghost@example.com"
    When I delete the user by email "ghost@example.com"
    Then the request should fail with a not-found response

  # Why: A second delete of the same email finds nothing — the absence is
  # reported honestly, never a fabricated success
  @edge-case
  Scenario: Deleting the same email twice reports not found the second time
    Given a user exists with email "once@example.com"
    When I delete the user by email "once@example.com"
    And I delete the user by email "once@example.com" again
    Then the second request should fail with a not-found response

  # Why: Malformed input is rejected before the database is touched
  @negative
  Scenario: A malformed email address is rejected as invalid
    When I delete the user by email "not-an-email"
    Then the request should fail as invalid input

  # Why: The by-id delete route must keep working — the literal by-email route
  # must not shadow it (the route-order regression guard, DELETE group)
  @boundary
  Scenario: Deleting by id still works alongside the by-email route
    Given a user exists with email "keep-id@example.com"
    When I delete that user by their id
    Then the request should succeed with no content

  # Why: Honest degradation — the database being down is named as the cause,
  # never a raw 500 (the /users/count convention)
  @negative
  Scenario: Deletion degrades honestly when the database is down
    Given the database is unavailable
    When I delete the user by email "ada@example.com"
    Then the request should fail naming the database as the cause
