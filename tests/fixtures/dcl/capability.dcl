language dcl 1.0

// DCL capability spec for api_test's GET /stats endpoint.
// Task: TASK-STAT-001 (feature FEAT-AE43). SPIKE ARTIFACT — not a frozen suite.
//
// Grounded in the SAME inputs the Gherkin had:
//   - feature_spec_inputs/2dfb4ef5-b769-4a89-91b6-f25498af0090.md, "Request" field
//     (the drone-fleet "Product Documentation" in that file is PO-seat template bleed
//      and is excluded — same low-confidence assumption the .feature file records).
//   - qa/pass-bar-TASK-STAT-001.yaml (the five machine criteria + two negative paths).
//   - features/stats-endpoint/stats-endpoint.feature (the 8 @task:TASK-STAT-001 scenarios).
//
// The Request, verbatim in substance: "add a GET /stats endpoint returning JSON with three
// fields: service (configured app name), requests_served (process-lifetime count of HTTP
// requests handled, integer) and first_request_at (UTC ISO-8601 of the first request handled,
// null until one has been). Keep the counter in-process (no database)."

actor Operator is human

// GET /stats carries no request body — the operator simply asks for the current statistics.
shape StatisticsQuery {
}

// The statistics payload — the three fields the Request names, as a first-class,
// compiler-checked shape. firstRequestAt is always PRESENT in the body but its VALUE is
// null until the service has handled its first request; DCL v1.0 has no optional/nullable
// field qualifier (fields are `required`-only), so the null-until-first-request nuance
// cannot be expressed here and is carried by the pass-bar / scenarios instead.
event StatisticsProduced is {
  service: Text required
  requestsServed: Number required
  firstRequestAt: Text required
}

// The endpoint touches no database, so it stays available when the database is down
// (pass-bar negative path dependency_down_degradation = NO degradation; feature edge-case
// "Statistics remain available when the database is unavailable").
policy StatisticsAvailability {
  availability {
    dependency_tolerance allowed
  }
}

capability ReportServiceStatistics {
  intent StatisticsQuery from Operator

  outcome StatisticsReported

  events {
    emits StatisticsProduced
  }

  policies {
    StatisticsAvailability governs capability
  }

  observe {
    capability duration as stats_report_duration
    event StatisticsProduced count as statistics_reports
    outcome StatisticsReported count as statistics_reported_total
  }

  when {
    always StatisticsReported
  }

  // Process-lifetime state: first_request_at is null on a fresh process (Fresh) and, once a
  // request has been handled, is set and thereafter stable (Serving). A restart is a new
  // process that begins again at Fresh.
  lifecycle {
    begin Fresh
    step Fresh
    end Serving
    move Fresh to Serving on outcome StatisticsReported
  }
}
