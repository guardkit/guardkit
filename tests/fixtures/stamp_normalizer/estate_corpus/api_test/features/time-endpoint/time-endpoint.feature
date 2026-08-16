# APPROVED AS PROPOSED by Rich 2026-07-31 (interactive sit; all 3 assumptions confirmed)
# Feature: Server Time Endpoint
# Stack: python
# Assumptions: 3 (see time-endpoint_assumptions.yaml — ALL CONFIRMED 2026-07-31)
# Generated: 2026-07-31
# Purpose: the routine-sit feature for 2026-07-31 — deliberately thin (a pure
#   read-only GET with no database dependency, the /version weight class). The
#   morning's revival runs proved this exact endpoint through the machine chain
#   on throwaway branches that were never merged; this staging ships it FOR REAL
#   through the routine path. The sit's two extra payloads: the first
#   `conformance:` block whose receipt SURVIVES (receipts export is live since
#   FEAT-DRC — the UDBE block's receipt was destroyed with its worktree), and
#   the first real `--profile unattended` build (1800s / 2 review cycles).
#   Conventions inherited: module-per-route (src/<module>/router.py + schemas),
#   the /version no-database shape, 405 on write methods via FastAPI's default
#   method handling.

@time-endpoint
Feature: Server Time Endpoint
  As a consumer of the api_test service
  I want to read the server's current time
  So that I can timestamp client-side operations against the server's clock

  Background:
    Given the api_test service is running

  # Why: Core path — two exact fields, server-truth time in a machine-parseable
  # shape (ISO-8601 UTC, second precision, trailing Z)
  @key-example @smoke
  Scenario: Reading the current server time
    When I send a GET request to "/time"
    Then the response status code should be 200
    And the response content type should be "application/json"
    And the response body should contain exactly two fields: "time" and "service"
    And the "time" field should be the current UTC time in ISO-8601 format with second precision and a trailing "Z"
    And the "service" field should be "api_test"

  # Why: Boundary — the value is computed per request, never cached or frozen
  # at process start (an uptime-style constant cannot fake a clock)
  @boundary
  Scenario: The time is fresh on every request
    When I send two GET requests to "/time" at least one second apart
    Then each response's "time" field should parse as a valid ISO-8601 UTC timestamp
    And the second timestamp should be strictly later than the first

  # Why: Negative — a read-only surface rejects every write method
  @negative
  Scenario: Write methods are rejected
    When I send a POST request to "/time"
    Then the response status code should be 405
    When I send a PUT request to "/time"
    Then the response status code should be 405
    When I send a DELETE request to "/time"
    Then the response status code should be 405

  # Why: Negative — the endpoint has NO database dependency, and stays honest
  # about it: it must keep answering 200 while the database is down (the
  # dependency-down class expressed as proven unaffectedness)
  @negative
  Scenario: The endpoint is unaffected by database unavailability
    Given the database is unavailable
    When I send a GET request to "/time"
    Then the response status code should be 200
    And the "time" field should parse as a valid ISO-8601 UTC timestamp
