# Feature Input: AutoBuild GB10 Benchmark Task Suite

## Feature Name

`autobuild-benchmark-suite`

## One-liner

A suite of self-contained, infrastructure-free benchmark tasks built on the FastAPI base project, designed to generate comparable `llm.call` instrumentation data across different AutoBuild prompt profiles (`digest_only`, `digest+graphiti`, `digest+rules_bundle`) on the GB10 / vLLM / Qwen3-Coder stack.

---

## Background & Motivation

With AutoBuild instrumentation live (FEAT-CF57) and the role-specific digest system built, the next step is generating real performance data from the GB10. To do this, we need a repeatable benchmark suite: a fixed set of tasks that can be run multiple times under different `prompt_profile` configurations and compared via the structured JSONL event output.

The tasks are deliberately chosen to be:

**Self-contained** — no Postgres, Redis, or external APIs required. `pytest` passes from a clean clone with only `pip install -e ".[dev]"`.

**Complexity 3–5** — the range where the GB10 should handle a task in a single AutoBuild turn. This isolates model performance (prefill latency, generation speed, token efficiency) rather than confounding it with multi-turn orchestration overhead.

**Domain-flavoured** — tasks are written in terms of a financial services API domain (loosely inspired by document processing and client management workflows), so the model has to handle realistic naming, validation rules, and business logic — not toy problems.

**Independently runnable** — each task adds to the base project without depending on any other benchmark task. They can be run in any order and in parallel within a wave.

---

## Structure

Each benchmark task is a self-contained feature addition to the `fastapi-base` project. The tasks are grouped into two tiers:

**Tier A (complexity 3–4) — Primary tuning suite.** Expected to complete in one AutoBuild turn on GB10. Run these with all three prompt profiles to generate the A/B instrumentation data.

**Tier B (complexity 5) — Validation suite.** Run after tuning to confirm quality holds at higher complexity. One turn expected with a well-tuned profile; two turns may occur.

---

## Tier A Tasks

### BENCH-001: Reference Data Validator

**Complexity:** 3

Add a `ReferenceDataValidator` class to `app/validators/reference.py` that validates whether a given string value belongs to a controlled vocabulary.

Requirements:
- `ReferenceDataValidator(allowed_values: frozenset[str], case_sensitive: bool = True)`
- `.validate(value: str) -> ValidationResult`
- `ValidationResult` is a dataclass with `is_valid: bool`, `value: str`, `normalised: str | None` (lowercased if `case_sensitive=False` and valid), `error: str | None`
- Raise `ValueError` on construction if `allowed_values` is empty
- Thread-safe (no mutable state after construction)

Controlled vocabularies to implement as module-level constants:
- `DOCUMENT_TYPES = frozenset({"passport", "driving_licence", "national_id", "birth_certificate"})`
- `CLIENT_STATUSES = frozenset({"active", "suspended", "pending_review", "closed"})`
- `JURISDICTION_CODES = frozenset({"ENG", "WAL", "SCO", "NIR"})`

Tests must cover: valid values, invalid values, case-insensitive mode, empty allowed_values construction error, all three named vocabulary constants.

Add `GET /v1/reference/{vocabulary_name}` endpoint that returns the full allowed values list for a named vocabulary.

---

### BENCH-002: Fee Calculator

**Complexity:** 3

Implement a fee calculation module at `app/calculators/fees.py`.

Domain: a document registration service charges fees based on document type, applicant category, and whether the application is standard or expedited.

Fee schedule (encode as a dataclass or typed dict, not magic numbers inline):

| Document Type | Applicant Category | Standard | Expedited |
|---|---|---|---|
| `standard` | `individual` | £82 | £164 |
| `standard` | `organisation` | £82 | £164 |
| `complex` | `individual` | £167 | £334 |
| `complex` | `organisation` | £167 | £334 |

Additional rules:
- `applicant_category = "exempt"` → fee is always £0 regardless of type or mode
- `expedited = True` → double the base fee
- Unknown `document_type` or `applicant_category` raises `FeeCalculationError` with message listing valid values

`FeeCalculationError` is a custom exception in the same module.

`calculate_fee(document_type: str, applicant_category: str, expedited: bool = False) -> FeeResult`

`FeeResult` dataclass: `amount_pence: int`, `amount_pounds: Decimal`, `currency: str = "GBP"`, `is_exempt: bool`, `is_expedited: bool`

Add `POST /v1/fees/calculate` endpoint that accepts a JSON body and returns the fee result. Pydantic request/response models.

Tests must cover: all combinations in the schedule, exempt applicants, expedited doubling, unknown type/category error, endpoint integration.

---

### BENCH-003: Pagination Helper

**Complexity:** 3

Implement a reusable pagination utility at `app/pagination.py`.

`PaginationParams` — a Pydantic model usable as FastAPI query parameter dependency:
- `page: int` — 1-indexed, default 1, minimum 1
- `page_size: int` — default 20, minimum 1, maximum 100
- `.offset -> int` property (returns `(page - 1) * page_size`)
- `.limit -> int` property (alias for `page_size`)

`paginate(items: Sequence[T], params: PaginationParams) -> PaginatedResponse[T]`

`PaginatedResponse[T]` — generic Pydantic model:
- `items: list[T]`
- `total: int`
- `page: int`
- `page_size: int`
- `total_pages: int`
- `has_next: bool`
- `has_previous: bool`

Add `GET /v1/reference/document-types` endpoint that returns a paginated list of document type strings using this utility, accepting `page` and `page_size` query params.

Tests must cover: first page, last page, middle page, single-item result, empty result, page_size=1, page beyond total_pages returns empty items (not error), invalid params (page=0, page_size=0, page_size=101) return 422.

---

### BENCH-004: Structured Error Responses

**Complexity:** 4

Replace FastAPI's default error handling with a consistent structured error response format across the entire application.

`ErrorCode` — a `str` enum in `app/errors.py`:
- `VALIDATION_ERROR = "VALIDATION_ERROR"`
- `NOT_FOUND = "NOT_FOUND"`
- `CONFLICT = "CONFLICT"`
- `INTERNAL_ERROR = "INTERNAL_ERROR"`
- `RATE_LIMITED = "RATE_LIMITED"`

`ErrorResponse` — Pydantic model:
- `error_code: ErrorCode`
- `message: str`
- `detail: dict[str, Any] | None` — optional structured context
- `correlation_id: str | None` — pulled from request context
- `request_id: str` — always present (same as correlation_id if available, else generated)

Register exception handlers on the app:
- `RequestValidationError` → 422 with `error_code=VALIDATION_ERROR`, `detail` contains field-level errors restructured from Pydantic's format
- `HTTPException` → pass-through status code, wrap body in `ErrorResponse`
- Unhandled `Exception` → 500 with `error_code=INTERNAL_ERROR`, message `"An unexpected error occurred"`, no detail (avoid leaking internals)

All existing endpoints (health, reference, fees) must return errors in this format.

Tests must cover: 404 on unknown route returns `ErrorResponse`, validation error on fee calculator with invalid body returns structured field errors, 500 handler does not leak exception message, correlation_id appears in error response when header was provided.

---

### BENCH-005: Request/Response Logging Middleware

**Complexity:** 4

Extend the existing correlation middleware to also emit structured log entries for every request and response.

Log on request receipt:
- `event: "request.received"`
- `method: str`
- `path: str`
- `correlation_id: str`
- `user_agent: str | None`
- `content_length: int | None`

Log on response sent:
- `event: "request.completed"`
- `method: str`
- `path: str`
- `status_code: int`
- `correlation_id: str`
- `duration_ms: float` (wall clock from request receipt to response sent)
- `response_size_bytes: int | None`

Health check paths (`/v1/health/live`, `/v1/health/ready`) should be suppressed from logging by default to avoid noise in production (configurable via `Settings.LOG_HEALTH_CHECKS: bool = False`).

Tests must cover: request log emitted with correct fields, response log includes duration_ms > 0, correlation_id matches across request and response logs, health probe paths suppressed when setting is False, health probe paths logged when setting is True, log output is valid JSON when `LOG_FORMAT=json`.

For test assertions on log output, capture log records via pytest's `caplog` fixture or by injecting a test log handler — do not parse stdout.

---

## Tier B Tasks

### BENCH-006: Client Record API (Complexity 5)

Implement an in-memory client record store and CRUD API — no database, uses a module-level dict as the store, reset between tests via a fixture.

`ClientRecord` Pydantic model:
- `id: str` (UUID, generated on creation)
- `reference: str` (human-readable, format `CLT-{6 digits}`, auto-generated)
- `full_name: str` (1–200 chars)
- `email: str` (valid email format)
- `status: ClientStatus` (enum: `active`, `suspended`, `pending_review`, `closed`)
- `jurisdiction: str` (must be in `JURISDICTION_CODES`)
- `created_at: datetime`
- `updated_at: datetime`

`ClientStore` class in `app/stores/clients.py` with:
- `create(data: ClientCreateRequest) -> ClientRecord`
- `get(client_id: str) -> ClientRecord | None`
- `update(client_id: str, data: ClientUpdateRequest) -> ClientRecord | None`
- `list(status: ClientStatus | None, page: int, page_size: int) -> PaginatedResponse[ClientRecord]`
- `delete(client_id: str) -> bool`

Endpoints under `/v1/clients/`:
- `POST /v1/clients/` → 201 with `ClientRecord`
- `GET /v1/clients/{client_id}` → 200 or 404
- `PATCH /v1/clients/{client_id}` → 200 or 404 (partial update, only provided fields)
- `GET /v1/clients/` → 200 with `PaginatedResponse[ClientRecord]`, optional `?status=` filter
- `DELETE /v1/clients/{client_id}` → 204 or 404

Use the `ErrorResponse` format from BENCH-004 for all errors. Use `PaginatedResponse` from BENCH-003 for the list endpoint. The store is injected as a FastAPI dependency to enable test isolation.

---

### BENCH-007: Document Submission State Machine (Complexity 5)

Implement a document submission lifecycle as a state machine at `app/statemachine/submission.py`.

States: `draft → submitted → under_review → approved | rejected`

Transitions:
- `draft → submitted`: requires `submitted_by: str` (non-empty)
- `submitted → under_review`: requires `assigned_to: str` (non-empty)
- `under_review → approved`: requires `decision_notes: str` (10+ chars)
- `under_review → rejected`: requires `rejection_reason: str` (10+ chars), `rejection_code: str` (from a controlled set)
- Any state → `draft` (recall): only allowed from `submitted` or `under_review`, sets all assignment fields to None

`SubmissionStateMachine`:
- `current_state: SubmissionState`
- `.transition(event: TransitionEvent) -> TransitionResult`
- `TransitionResult`: `success: bool`, `previous_state`, `new_state`, `error: str | None`
- Invalid transitions return `TransitionResult(success=False, ...)` — do not raise

`TransitionEvent` dataclass with `action: str` and optional context fields.

In-memory `SubmissionStore` (same pattern as BENCH-006) storing `SubmissionRecord`:
- `id`, `client_id`, `document_type`, `state`, `history: list[StateTransition]`, `created_at`, `updated_at`

`StateTransition` records: `from_state`, `to_state`, `action`, `actor`, `timestamp`, `notes`

Endpoints under `/v1/submissions/`:
- `POST /v1/submissions/` → create in `draft` state
- `GET /v1/submissions/{id}` → full record including history
- `POST /v1/submissions/{id}/transitions` → apply a transition, return updated record or 409 on invalid transition
- `GET /v1/submissions/` → paginated list, filterable by `state` and `client_id`

---

## How to Use This Suite for GB10 Tuning

### Benchmark Run Procedure

1. Ensure FEAT-CF57 instrumentation is active (events writing to `.guardkit/autobuild/{task_id}/events.jsonl`)
2. Create a feature YAML with Tier A tasks (BENCH-001 through BENCH-005) in a single parallel wave
3. Set `prompt_profile` in AutoBuild config to the profile under test
4. Run the wave and collect JSONL output
5. Repeat for each profile: `digest_only`, `digest+graphiti`, `digest+rules_bundle`
6. Compare across profiles: `llm.call.latency_ms` p50/p95, `input_tokens` average, first-attempt success rate

### What to Measure

From the JSONL events, the primary signals are:
- `llm.call.input_tokens` — does digest-only significantly reduce input token count?
- `llm.call.latency_ms` — does reduced context improve prefill time on GB10?
- `llm.call.ttft_ms` — time to first token (most sensitive to prefill cost)
- `task.lifecycle.turn_count` — does simpler context cause more turns (quality regression)?
- `task.lifecycle.verification_status` — does quality hold across profiles?

### Expected Outcome

Tier A tasks (complexity 3–4) should all complete in one turn under all profiles. If `digest_only` reduces `input_tokens` by 30%+ with no increase in `turn_count` or `verification_status` degradation, that validates the context reduction approach. If turn counts increase, the rules bundle is doing meaningful work and targeted retrieval via Graphiti needs to be tuned before removing it.

---

## Notes for Spec Generation

- Stack is Python, building on the `fastapi-base-project` described in the companion feature spec
- All tasks must be independently runnable — BENCH-006 uses BENCH-003's `PaginatedResponse` and BENCH-004's `ErrorResponse`, but should either import them or define local equivalents if those tasks haven't run
- Tests use `TestClient` (sync) — no async fixtures needed
- Each task's test file must be independently runnable with `pytest tests/test_bench_XXX.py` and pass without running other benchmark tasks first
- The in-memory stores in BENCH-006 and BENCH-007 are the only shared state — reset via pytest fixtures, not module-level teardown
