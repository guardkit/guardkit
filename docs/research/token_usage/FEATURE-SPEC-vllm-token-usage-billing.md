# Feature Specification: vLLM Token Usage Tracking & Client Billing

**Date:** 2026-03-01  
**Author:** Rich  
**Status:** Ready for Implementation  
**Research Method:** Claude Desktop conversation → manual spec  
**Target Repo:** `appmilla/dev-pipeline`  
**Target Branch:** `feature/vllm-token-billing`  
**Feature ID:** FEAT-XXX *(assigned by `/feature-plan`)*

---

## 1. Problem Statement

When running AutoBuild on the DGX Spark using vLLM with local models (Qwen3-Next-Coder), there is currently no mechanism to track token consumption per feature build or per project. This has two consequences:

1. **Internal visibility gap**: Rich cannot see how much inference each AutoBuild run consumes, making it hard to understand cost and capacity.
2. **Client billing gap**: When working on client projects (e.g. FinProxy LPA Platform) on a time-and-materials basis, there is no way to report or charge for local AI inference — despite it having a real cost and real value.

The dev-pipeline architecture already has `tokens_used` in the result message schema and "Cost tracking: Token usage per build, aggregated per project, for client billing" listed as a future extension. This feature implements that extension.

vLLM exposes a Prometheus metrics endpoint at `/metrics` that includes `vllm:prompt_tokens_total` and `vllm:generation_tokens_total`. The solution reads these before and after each AutoBuild run, computes the delta, and records usage against the feature/project in a persistent store. A reporting command then aggregates usage for invoicing.

Billing rate is configurable per project — defaulting to 60% of current Anthropic Claude Sonnet API pricing (input: $3/M tokens, output: $15/M tokens), giving a default of $1.80/M input and $9.00/M output. Projects can be configured at 100% (matching cloud API pricing) or any other multiplier, reflecting the value of local inference (no rate limits, data privacy, lower latency) versus the cost.

---

## 2. Decision Log

| # | Decision | Rationale | Alternatives Rejected | ADR Status |
|---|----------|-----------|----------------------|------------|
| D1 | Read vLLM Prometheus metrics endpoint for token counts | Already exposed by vLLM at `/metrics` with no additional instrumentation. `vllm:prompt_tokens_total` and `vllm:generation_tokens_total` are cumulative counters — delta between before/after a build gives per-build usage | vLLM request logging (requires patching GuardKit to intercept every request), OpenTelemetry (overkill, adds infrastructure), manual token counting in GuardKit (fragile, duplicates vLLM's own counting) | Accepted |
| D2 | Store usage records in SQLite on the Spark, not in NATS JetStream or FalkorDB | Billing data is append-only structured records — SQLite is the right tool. Survives NATS restarts. Simple to query for reports. No additional infrastructure | NATS KV store (designed for config not append-only billing records), FalkorDB/Graphiti (knowledge graph, not relational billing store), PostgreSQL (overkill for this use case), flat JSON files (hard to query for aggregated reports) | Accepted |
| D3 | Capture usage at the Build Agent level, not inside GuardKit | The Build Agent already wraps each GuardKit AutoBuild subprocess invocation. Reading vLLM metrics before and after the subprocess gives accurate per-build token delta without modifying GuardKit internals. Clean separation of concerns | Modify GuardKit to emit token events (couples billing to the build tool), read metrics inside GuardKit (wrong layer — GuardKit is a build tool not a billing system) | Accepted |
| D4 | Configurable billing rate per project as a multiplier against Anthropic Sonnet pricing | Anthropic API pricing is a well-understood reference point. Charging 60% of that rate reflects real value of local inference. 100% is also valid when selling the "same capability, better reliability" story. Multiplier config means rates can be updated when Anthropic changes pricing without changing code | Fixed price per token (brittle when reference prices change), manual rate entry (error-prone), no billing rate (would require post-processing before invoicing) | Accepted |
| D5 | Publish `pipeline.usage-recorded` NATS event after each build | Keeps the event-driven architecture consistent. Allows future consumers (dashboard, PM adapter, invoice generator) to react to usage events. Current implementation just persists to SQLite — the event is fire-and-forget | Skip NATS event (loses integration opportunity), use NATS as primary store (wrong tool) | Accepted |
| D6 | CLI reporting command `dev-pipeline usage report` for invoice generation | Simple tabular output (per-feature, per-project, date range) is sufficient for time-and-materials invoicing. Export to CSV for import into accounting tools | Web dashboard (nice, but not blocking invoicing), automatic invoice generation (out of scope), Linear integration for billing (different concern from development tracking) | Accepted |
| D7 | Separate input and output token tracking with separate rates | Anthropic charges different rates for input vs output tokens (5:1 ratio for Sonnet). Collapsing to a single token count would either over- or under-charge depending on the workload mix. AutoBuild is output-heavy (generates code), so this matters in practice | Single blended token rate (loses accuracy), token count only without rate split (forces manual calculation at invoice time) | Accepted |

**Warnings & Constraints:**
- vLLM metrics endpoint must be reachable from the Build Agent at build time — if vLLM is down or the endpoint is unreachable, the build should still proceed but usage should be recorded as `null` with a warning, not fail the build
- Prometheus counters are cumulative and reset on vLLM restart — the delta calculation must handle counter resets gracefully (delta < 0 means a reset occurred; log a warning and record `null`)
- The `tokens_used` field already exists in the NATS result message schema (`distributed_agent_orchestration_architecture.md`) — this feature populates it
- Billing rates are for invoicing guidance only — this system does not integrate with payment processing

---

## 3. Behaviour Specification (Gherkin)

```gherkin
Feature: vLLM Token Usage Tracking
  As Rich running AutoBuild on the DGX Spark
  I want token usage captured per feature build
  So that I can report and charge for local AI inference on client projects

  Background:
    Given the vLLM server is running on the DGX Spark
    And the vLLM metrics endpoint is available at "http://localhost:8000/metrics"
    And the dev-pipeline Build Agent is running
    And a usage database exists at "/var/dev-pipeline/usage.db"

  # ── Happy Path ──────────────────────────────────────────────────────────

  Scenario: Token usage is captured for a completed build
    Given a feature build for project "finproxy" and feature "FEAT-042" is triggered
    And the vLLM metrics show 12,500 prompt tokens and 8,300 generation tokens at build start
    When the AutoBuild subprocess completes successfully
    And the vLLM metrics show 24,100 prompt tokens and 19,700 generation tokens at build end
    Then a usage record is written to the database with:
      | field            | value       |
      | project_id       | finproxy    |
      | feature_id       | FEAT-042    |
      | prompt_tokens    | 11,600      |
      | generation_tokens| 11,400      |
      | build_status     | success     |
    And a "pipeline.usage-recorded" event is published to NATS

  Scenario: Usage report shows per-feature breakdown for a project
    Given usage records exist for project "finproxy" across 3 features in March 2026
    When I run "dev-pipeline usage report --project finproxy --month 2026-03"
    Then the output shows a table with one row per feature containing:
      | Feature ID | Prompt Tokens | Generation Tokens | Input Cost | Output Cost | Total Cost |
    And a totals row at the bottom
    And the costs use the configured billing rate for project "finproxy"

  Scenario: Usage report for all projects in a date range
    Given usage records exist for multiple projects between 2026-02-01 and 2026-03-31
    When I run "dev-pipeline usage report --from 2026-02-01 --to 2026-03-31"
    Then the output shows usage grouped by project
    And each project section shows per-feature detail and a project subtotal
    And a grand total is shown at the end

  Scenario: CSV export for invoicing
    Given usage records exist for project "finproxy" in March 2026
    When I run "dev-pipeline usage report --project finproxy --month 2026-03 --csv"
    Then a CSV file is written to the current directory named "finproxy-usage-2026-03.csv"
    And the CSV contains one row per feature with all usage fields and calculated costs

  # ── Billing Rate Configuration ──────────────────────────────────────────

  Scenario: Default billing rate is 60% of Anthropic Sonnet pricing
    Given project "acme-client" has no explicit billing rate configured
    When I run "dev-pipeline usage report --project acme-client --month 2026-03"
    Then costs are calculated at $1.80 per million prompt tokens
    And costs are calculated at $9.00 per million generation tokens

  Scenario: Project configured at 100% of Anthropic Sonnet pricing
    Given project "finproxy" has billing_rate_multiplier set to 1.0 in its config
    When I run "dev-pipeline usage report --project finproxy --month 2026-03"
    Then costs are calculated at $3.00 per million prompt tokens
    And costs are calculated at $15.00 per million generation tokens

  Scenario: Custom billing rate multiplier
    Given project "internal-tools" has billing_rate_multiplier set to 0.0 in its config
    When I run "dev-pipeline usage report --project internal-tools --month 2026-03"
    Then all cost columns show $0.00
    And token counts are still shown

  # ── Error Handling ──────────────────────────────────────────────────────

  Scenario: vLLM metrics endpoint unreachable at build start
    Given the vLLM metrics endpoint is not responding
    When a feature build for "FEAT-043" is triggered
    Then the build proceeds normally without waiting for metrics
    And a usage record is written with prompt_tokens = null and generation_tokens = null
    And a warning is logged: "vLLM metrics unavailable at build start for FEAT-043 — token usage will not be recorded"
    And the build result is not affected

  Scenario: vLLM metrics endpoint unreachable at build end
    Given the vLLM metrics endpoint was readable at build start
    And the vLLM metrics endpoint becomes unreachable during the build
    When the AutoBuild subprocess completes
    Then a usage record is written with prompt_tokens = null and generation_tokens = null
    And a warning is logged: "vLLM metrics unavailable at build end for FEAT-043 — token usage will not be recorded"

  Scenario: Prometheus counter reset detected during build
    Given the vLLM metrics show 950,000 prompt tokens at build start
    And vLLM was restarted during the build
    And the vLLM metrics show 5,200 prompt tokens at build end
    Then the Build Agent detects the counter has reset (end < start)
    And a usage record is written with prompt_tokens = null and generation_tokens = null
    And a warning is logged: "vLLM counter reset detected during FEAT-044 build — token usage not recorded"

  Scenario: Build fails — usage is still recorded
    Given a feature build for "FEAT-045" is triggered
    And vLLM metrics are readable at start and end
    When the AutoBuild subprocess exits with a non-zero status
    Then a usage record is written with build_status = "failed"
    And token deltas are recorded normally
    And the usage record is included in reports

  # ── Data Retention ──────────────────────────────────────────────────────

  Scenario: Usage records are queryable after 90 days
    Given a usage record was written 91 days ago for project "finproxy"
    When I run "dev-pipeline usage report --project finproxy --from 2025-11-01"
    Then the 91-day-old record appears in the report

  Scenario Outline: Report handles empty result sets gracefully
    Given no usage records exist matching the filter criteria
    When I run "dev-pipeline usage report <flags>"
    Then the output shows "No usage records found for the specified criteria"
    And the exit code is 0

    Examples:
      | flags                                          |
      | --project nonexistent-project --month 2026-03  |
      | --from 2020-01-01 --to 2020-01-31              |
      | --project finproxy --month 2025-01             |
```

---

## 4. Assumptions Manifest

```yaml
# vllm-token-billing_assumptions.yaml
feature_id: FEAT-XXX
generated: 2026-03-01

assumptions:
  - id: A1
    description: "vLLM metrics endpoint is at http://localhost:8000/metrics on the DGX Spark"
    confidence: high
    basis: "Default vLLM configuration. Already confirmed in use for AutoBuild."
    impact_if_wrong: "MetricsReader will fail to connect — change base URL in config"

  - id: A2
    description: "Prometheus counter names are vllm:prompt_tokens_total and vllm:generation_tokens_total"
    confidence: high
    basis: "Standard vLLM Prometheus metric names as of vLLM 0.4.x"
    impact_if_wrong: "MetricsReader parses wrong fields — returns zero deltas silently"
    verification: "Run: curl http://localhost:8000/metrics | grep vllm.*tokens"

  - id: A3
    description: "Anthropic Sonnet reference pricing: $3.00/M input tokens, $15.00/M output tokens"
    confidence: medium
    basis: "Current Anthropic API pricing as of March 2026"
    impact_if_wrong: "Billing calculations will be off — update base_input_rate and base_output_rate in config"
    note: "Pricing changes over time — these are stored in config not hardcoded"

  - id: A4
    description: "SQLite at /var/dev-pipeline/usage.db is writable by the Build Agent process"
    confidence: medium
    basis: "Assumed Docker volume mount or appropriate file permissions"
    impact_if_wrong: "Database writes fail — usage not recorded"
    verification: "Confirm Docker Compose volume configuration for dev-pipeline service"

  - id: A5
    description: "Build Agent runs as a single instance — no concurrent builds initially"
    confidence: high
    basis: "dev-pipeline-system-spec.md: 'Single build at a time initially'"
    impact_if_wrong: "Concurrent builds would cause token delta attribution errors — metrics snapshot approach is not safe under concurrency"
    note: "If parallelism is added later, switch to per-request token tracking in vLLM"

  - id: A6
    description: "The NATS pipeline.usage-recorded event is fire-and-forget — no consumer guaranteed"
    confidence: high
    basis: "No current consumer planned for this event — published for future extensibility"
    impact_if_wrong: "No impact on billing functionality — SQLite is the source of truth"
```

---

## 5. Component Design

### New Components

**`UsageTracker`** (`dev-pipeline/billing/usage_tracker.py`)
- `snapshot_before(feature_id, project_id)` — reads vLLM metrics, stores snapshot in memory
- `snapshot_after(feature_id, project_id, build_status)` — reads vLLM metrics, computes delta, writes to SQLite, publishes NATS event
- Handles unreachable endpoint and counter reset gracefully (records null, logs warning)

**`MetricsReader`** (`dev-pipeline/billing/metrics_reader.py`)
- `read_token_counts()` → `TokenSnapshot | None`
- Fetches `/metrics`, parses Prometheus text format, extracts prompt and generation token counters
- Returns None on any error (connection refused, parse failure, timeout)

**`UsageDatabase`** (`dev-pipeline/billing/usage_database.py`)
- SQLite wrapper with schema migration
- `write_record(UsageRecord)` — insert
- `query_records(project_id, date_from, date_to)` → `list[UsageRecord]`
- Schema: `usage_records(id, project_id, feature_id, build_id, started_at, completed_at, prompt_tokens, generation_tokens, build_status, billing_rate_multiplier)`

**`BillingConfig`** (`dev-pipeline/billing/billing_config.py`)
- Loads per-project billing rate multiplier from project config YAML
- Falls back to global default (0.6) if not configured
- Exposes `base_input_rate` and `base_output_rate` (updatable when Anthropic changes pricing)

**`UsageReportCommand`** (`dev-pipeline/cli/usage_report.py`)
- CLI: `dev-pipeline usage report [--project X] [--month YYYY-MM] [--from DATE] [--to DATE] [--csv]`
- Queries UsageDatabase, applies BillingConfig rates, formats as table or CSV
- Tabular output uses `rich` (already used elsewhere in GuardKit ecosystem)

### Modified Components

**`BuildAgent`** (`dev-pipeline/build_agent/agent.py`)
- Add `UsageTracker` injection
- Call `usage_tracker.snapshot_before()` immediately before subprocess launch
- Call `usage_tracker.snapshot_after()` immediately after subprocess completes
- Pass `build_status` (success/failed) to `snapshot_after`

**`nats_core` message schema** — `pipeline.usage-recorded` event added:
```json
{
  "event_type": "usage-recorded",
  "project_id": "finproxy",
  "feature_id": "FEAT-042",
  "build_id": "uuid",
  "prompt_tokens": 11600,
  "generation_tokens": 11400,
  "build_status": "success",
  "input_cost_usd": 0.02088,
  "output_cost_usd": 0.1026,
  "total_cost_usd": 0.12348
}
```

---

## 6. File Layout

```
dev-pipeline/
├── billing/
│   ├── __init__.py
│   ├── usage_tracker.py       # Orchestrates snapshot/delta/persist/publish
│   ├── metrics_reader.py      # vLLM Prometheus endpoint client
│   ├── usage_database.py      # SQLite persistence layer
│   └── billing_config.py      # Per-project billing rate configuration
├── cli/
│   └── usage_report.py        # `dev-pipeline usage report` command
└── tests/
    ├── test_usage_tracker.py
    ├── test_metrics_reader.py
    ├── test_usage_database.py
    ├── test_billing_config.py
    ├── test_usage_report.py
    └── integration/
        └── test_billing_e2e.py  # Requires vLLM running (mark with @pytest.mark.integration)
```

---

## 7. Configuration

```yaml
# dev-pipeline config (addition to existing config)
vllm:
  metrics_url: "http://localhost:8000/metrics"
  metrics_timeout_seconds: 5

billing:
  base_input_rate_per_million: 3.00      # USD — Anthropic Sonnet input pricing
  base_output_rate_per_million: 15.00    # USD — Anthropic Sonnet output pricing
  default_rate_multiplier: 0.6           # 60% of reference pricing
  database_path: "/var/dev-pipeline/usage.db"

projects:
  finproxy:
    billing_rate_multiplier: 1.0          # Charge at full Anthropic API rate
  internal-tools:
    billing_rate_multiplier: 0.0          # Internal — no charge
  # Projects not listed use default_rate_multiplier (0.6)
```

---

## 8. Quality Gates

```yaml
# .guardkit/quality-gates/FEAT-XXX.yaml
feature_id: FEAT-XXX
quality_gates:
  lint:
    command: "ruff check dev-pipeline/billing/ dev-pipeline/cli/usage_report.py"
    required: true
  type_check:
    command: "mypy dev-pipeline/billing/ dev-pipeline/cli/usage_report.py"
    required: true
  unit_tests:
    command: "pytest tests/test_usage_tracker.py tests/test_metrics_reader.py tests/test_usage_database.py tests/test_billing_config.py tests/test_usage_report.py -v --tb=short"
    required: true
  integration_tests:
    command: "pytest tests/integration/test_billing_e2e.py -v -m integration"
    required: false
  import_check:
    command: "python -c \"from dev_pipeline.billing.usage_tracker import UsageTracker; from dev_pipeline.billing.metrics_reader import MetricsReader; from dev_pipeline.billing.usage_database import UsageDatabase; print('All imports OK')\""
    required: true
```

---

## 9. Graphiti Seeding Commands

```bash
guardkit graphiti add-context docs/adr/ADR-BILL-001-vllm-prometheus-metrics.md
guardkit graphiti add-context docs/adr/ADR-BILL-002-sqlite-usage-store.md
guardkit graphiti add-context docs/features/FEATURE-SPEC-vllm-token-billing.md
guardkit graphiti verify --verbose
```

---

## 10. Phase 2 Execution Workflow

```bash
# On DGX Spark — AutoBuild via GuardKit

guardkit feature-build FEAT-XXX
# → Player adds UsageTracker to BuildAgent
# → Player implements MetricsReader (Prometheus text format parsing)
# → Player implements UsageDatabase (SQLite schema + queries)
# → Player implements BillingConfig (YAML config loading)
# → Player implements UsageReportCommand (rich table + CSV)
# → Coach validates against Gherkin scenarios above
# → Up to 5 turns per task before escalation

cd .guardkit/worktrees/FEAT-XXX && git diff main
guardkit feature-complete FEAT-XXX
```
