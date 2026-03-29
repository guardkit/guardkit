"""LangChain DeepAgents template utility library.

Exports:
    DomainValidator: Type-aware metadata validator with coercion and range support.
    MetadataField: Schema definition for a single metadata field.
    FieldType: Enum of supported field types.
    ValidationResult: Aggregated validation outcome.
    ValidationError: A single validation failure.
    coerce_value: Type coercion at model-output boundary.
    parse_range: Parse range notation (e.g. "1+", "1-10").
    validate_config: Validate required config fields (max_tokens etc.).
    validate_field: Validate a single field value against its schema.
    JsonExtractor: 5-strategy cascade JSON extractor for LLM outputs.
    JsonExtractionError: Raised when all extraction strategies fail.
    normalise_think_closing_tags: Stand-alone helper (also available via JsonExtractor).
    ToolLeakageError: Raised when agent tool inventory doesn't match expected set.
    assert_tool_inventory: Post-factory assertion for tool allowlisting.
    create_restricted_agent: Agent factory that bypasses FilesystemMiddleware.
    assert_no_system_messages: Guard against dual system messages in ainvoke().
    TokenTracker: Track token usage per API call with cumulative totals.
    TokenUsage: Token counts dataclass for a single API call.
    PipelineStageLogger: Log content length at each pipeline stage.
    StageTimer: Wall-clock timing per pipeline stage.
    StageTimingRecord: Timing record dataclass.
    log_error_context: Log error snippets for rapid diagnosis.
    configure_logging: Convenience function for observability logger setup.
    CheckResult: Outcome of a single preflight check.
    PreflightReport: Aggregated preflight validation report.
    run_preflight: Run all preflight checks against a project directory.
    format_report: Format a PreflightReport for terminal display.
"""

from .domain_validator import (
    DomainValidator,
    FieldType,
    MetadataField,
    ValidationError,
    ValidationResult,
    coerce_value,
    parse_range,
    validate_config,
    validate_field,
)
from .factory_guards import (
    ToolLeakageError,
    assert_no_system_messages,
    assert_tool_inventory,
    create_restricted_agent,
)
from .json_extractor import JsonExtractionError, JsonExtractor
from .observability import (
    PipelineStageLogger,
    StageTimer,
    StageTimingRecord,
    TokenTracker,
    TokenUsage,
    configure_logging,
    log_error_context,
)
from .preflight import (
    CheckResult,
    PreflightReport,
    format_report,
    run_preflight,
)

normalise_think_closing_tags = JsonExtractor.normalise_think_closing_tags

__all__ = [
    "DomainValidator",
    "FieldType",
    "JsonExtractor",
    "JsonExtractionError",
    "MetadataField",
    "PipelineStageLogger",
    "StageTimer",
    "StageTimingRecord",
    "TokenTracker",
    "TokenUsage",
    "ValidationError",
    "ValidationResult",
    "ToolLeakageError",
    "assert_no_system_messages",
    "assert_tool_inventory",
    "configure_logging",
    "create_restricted_agent",
    "log_error_context",
    "coerce_value",
    "normalise_think_closing_tags",
    "parse_range",
    "validate_config",
    "validate_field",
    "CheckResult",
    "PreflightReport",
    "format_report",
    "run_preflight",
]
