language dcl 1.0

// KNOWN-BAD FIXTURE — the false-green guard for the dcl-authoring grader.
// This file is DELIBERATELY broken and MUST fail the grader. It mirrors the
// /stats capability's shape but with two planted semantic defects:
//   1. actor Operator is referenced by `intent ... from Operator` but never declared
//      (and shape StatisticsQuery is likewise never declared).
//   2. the `when` block names UndeclaredOutcome, which the capability's outcomes do
//      not list.
// If the grader ever passes this file, the grader is a false-green and must be fixed.

capability ReportServiceStatistics {
  intent StatisticsQuery from Operator

  outcome StatisticsReported

  when {
    always UndeclaredOutcome
  }

  lifecycle {
    begin Fresh
    step Fresh
    end Serving
    move Fresh to Serving on outcome StatisticsReported
  }
}
