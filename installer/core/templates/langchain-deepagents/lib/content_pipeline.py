"""Canonical content processing pipeline for LangChain DeepAgents templates.

Enforces the correct stage order: normalize -> extract -> validate -> write.
This prevents pipeline ordering bugs (TRF-020) and ensures all processing
steps are applied consistently.

Each stage logs input/output length via the observability scaffold and
provides error context (head + tail + length) on failure.

Dependencies: json_extractor, domain_validator, observability (all in this lib).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Sequence

from .json_extractor import JsonExtractionError, JsonExtractor
from .domain_validator import DomainValidator, ValidationResult
from .observability import PipelineStageLogger, StageTimer, log_error_context

logger = logging.getLogger("deepagents.pipeline")


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class StageResult:
    """Outcome of a single pipeline stage execution."""

    stage: str
    success: bool
    input_length: int
    output_length: int
    error: Optional[str] = None


@dataclass
class PipelineResult:
    """Outcome of the full pipeline execution."""

    success: bool
    content: Any = None
    stages: list[StageResult] = field(default_factory=list)
    error: Optional[str] = None
    validation_result: Optional[ValidationResult] = None


# ---------------------------------------------------------------------------
# Stage descriptor
# ---------------------------------------------------------------------------


@dataclass
class _StageDescriptor:
    """Internal descriptor for a registered pipeline stage."""

    name: str
    fn: Callable[[Any], Any]
    position: int  # Determines execution order


# ---------------------------------------------------------------------------
# Canonical stage positions (fixed, cannot be reordered)
# ---------------------------------------------------------------------------

_CANONICAL_POSITIONS = {
    "normalize": 100,
    "extract": 200,
    "validate": 300,
    "write": 400,
}

_CUSTOM_STAGE_GAP = 10  # Custom stages inserted between canonical stages


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class ContentPipeline:
    """Canonical content processing pipeline.

    Enforces the correct order: normalize -> extract -> validate -> write.
    Custom stages can be inserted between canonical stages but cannot
    reorder or replace the canonical four.

    Args:
        extractor: JsonExtractor instance (or class — uses static methods).
        validator: DomainValidator instance for output validation.
        stage_logger: PipelineStageLogger for content-length tracking.
        timer: StageTimer for wall-clock timing (optional).
        write_fn: Optional write function for the write stage.
            Signature: ``write_fn(validated_data: dict) -> Any``.
            If None, the write stage is a no-op passthrough.
        config: Optional config dict passed to DomainValidator.validate().

    Usage::

        pipeline = ContentPipeline(
            extractor=JsonExtractor,
            validator=DomainValidator(schema),
            stage_logger=PipelineStageLogger(),
        )
        result = pipeline.process("raw LLM output")
        assert result.success
    """

    def __init__(
        self,
        extractor: type[JsonExtractor] | JsonExtractor,
        validator: DomainValidator,
        stage_logger: PipelineStageLogger,
        timer: Optional[StageTimer] = None,
        write_fn: Optional[Callable[[dict], Any]] = None,
        config: Optional[dict] = None,
    ) -> None:
        self._extractor = extractor
        self._validator = validator
        self._stage_logger = stage_logger
        self._timer = timer
        self._write_fn = write_fn
        self._config = config

        # Register canonical stages
        self._stages: list[_StageDescriptor] = [
            _StageDescriptor("normalize", self._normalize, _CANONICAL_POSITIONS["normalize"]),
            _StageDescriptor("extract", self._extract, _CANONICAL_POSITIONS["extract"]),
            _StageDescriptor("validate", self._validate, _CANONICAL_POSITIONS["validate"]),
            _StageDescriptor("write", self._write, _CANONICAL_POSITIONS["write"]),
        ]

        # Hooks
        self._on_stage_complete: Optional[Callable[[str, int, int], None]] = None
        self._on_stage_failure: Optional[Callable[[str, Exception, str], None]] = None

    # ------------------------------------------------------------------
    # Hook registration
    # ------------------------------------------------------------------

    def on_stage_complete(self, callback: Callable[[str, int, int], None]) -> None:
        """Register a hook called after each stage completes successfully.

        Args:
            callback: ``fn(stage_name, input_length, output_length)``
        """
        self._on_stage_complete = callback

    def on_stage_failure(self, callback: Callable[[str, Exception, str], None]) -> None:
        """Register a hook called when a stage fails.

        Args:
            callback: ``fn(stage_name, error, content_preview)``
        """
        self._on_stage_failure = callback

    # ------------------------------------------------------------------
    # Custom stage insertion
    # ------------------------------------------------------------------

    def add_stage(
        self,
        name: str,
        fn: Callable[[Any], Any],
        after: str,
    ) -> None:
        """Insert a custom stage after a named canonical or custom stage.

        Args:
            name: Name for the new stage (must be unique).
            fn: Stage function ``fn(input) -> output``.
            after: Name of the stage to insert after.

        Raises:
            ValueError: If ``after`` stage not found or ``name`` already exists.
        """
        if any(s.name == name for s in self._stages):
            raise ValueError(f"Stage {name!r} already exists")

        after_stage = next((s for s in self._stages if s.name == after), None)
        if after_stage is None:
            raise ValueError(f"Stage {after!r} not found")

        # Find the next stage position after the target
        sorted_stages = sorted(self._stages, key=lambda s: s.position)
        after_idx = next(i for i, s in enumerate(sorted_stages) if s.name == after)

        if after_idx + 1 < len(sorted_stages):
            next_pos = sorted_stages[after_idx + 1].position
            new_pos = after_stage.position + (next_pos - after_stage.position) // 2
        else:
            new_pos = after_stage.position + _CUSTOM_STAGE_GAP

        self._stages.append(_StageDescriptor(name, fn, new_pos))

    @property
    def stage_names(self) -> list[str]:
        """Return stage names in execution order."""
        return [s.name for s in sorted(self._stages, key=lambda s: s.position)]

    # ------------------------------------------------------------------
    # Pipeline execution
    # ------------------------------------------------------------------

    def process(
        self,
        raw_content: str | list,
        target: str = "default",
        additional_kwargs: dict | None = None,
    ) -> PipelineResult:
        """Execute the full pipeline on raw content.

        Args:
            raw_content: Raw LLM output (string or block-list).
            target: Logical target name for observability tracking.
            additional_kwargs: Optional metadata dict passed to JsonExtractor
                (may contain ``reasoning_content`` for vLLM).

        Returns:
            PipelineResult with processed content and stage log.
        """
        stage_log: list[StageResult] = []
        current = raw_content

        # Store additional_kwargs for the extract stage
        self._current_additional_kwargs = additional_kwargs

        sorted_stages = sorted(self._stages, key=lambda s: s.position)

        for descriptor in sorted_stages:
            stage_name = descriptor.name
            input_repr = self._content_repr(current)
            input_len = len(input_repr)

            try:
                if self._timer:
                    with self._timer.time(stage_name, target=target):
                        current = descriptor.fn(current)
                else:
                    current = descriptor.fn(current)

                output_repr = self._content_repr(current)
                output_len = len(output_repr)

                # Log stage via observability scaffold
                self._stage_logger.log_stage(stage_name, output_repr, target=target)

                stage_log.append(StageResult(
                    stage=stage_name,
                    success=True,
                    input_length=input_len,
                    output_length=output_len,
                ))

                if self._on_stage_complete:
                    self._on_stage_complete(stage_name, input_len, output_len)

            except Exception as exc:
                content_preview = input_repr[:200] if len(input_repr) > 200 else input_repr
                log_error_context(
                    content=input_repr,
                    error=exc,
                    stage=stage_name,
                    target=target,
                )

                stage_log.append(StageResult(
                    stage=stage_name,
                    success=False,
                    input_length=input_len,
                    output_length=0,
                    error=str(exc),
                ))

                if self._on_stage_failure:
                    self._on_stage_failure(stage_name, exc, content_preview)

                return PipelineResult(
                    success=False,
                    content=None,
                    stages=stage_log,
                    error=f"Stage {stage_name!r} failed: {exc}",
                )

        # Extract validation result if validate stage ran
        validation_result = getattr(self, "_last_validation_result", None)

        return PipelineResult(
            success=True,
            content=current,
            stages=stage_log,
            validation_result=validation_result,
        )

    # ------------------------------------------------------------------
    # Canonical stage implementations
    # ------------------------------------------------------------------

    def _normalize(self, content: str | list) -> str:
        """Stage 1: Normalize content format and think block tags.

        Handles:
        - Block-list to string conversion (joins list elements)
        - Think block tag normalization via JsonExtractor
        """
        if isinstance(content, list):
            content = "\n".join(str(item) for item in content)
        if not isinstance(content, str):
            content = str(content)

        return JsonExtractor.normalise_think_closing_tags(content)

    def _extract(self, content: str) -> dict:
        """Stage 2: Extract JSON using the 5-strategy cascade."""
        return self._extractor.extract(
            content,
            additional_kwargs=self._current_additional_kwargs,
        )

    def _validate(self, data: dict) -> dict:
        """Stage 3: Validate extracted data against domain schema."""
        result = self._validator.validate(data, config=self._config)
        self._last_validation_result = result

        if not result.is_valid:
            error_msgs = [str(e) for e in result.errors]
            raise ValueError(
                f"Validation failed with {len(result.errors)} error(s): "
                + "; ".join(error_msgs)
            )
        return data

    def _write(self, data: dict) -> dict:
        """Stage 4: Orchestrator-gated write (or passthrough if no write_fn)."""
        if self._write_fn is not None:
            return self._write_fn(data)
        return data

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _content_repr(content: Any) -> str:
        """Convert content to string for length measurement."""
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            import json
            return json.dumps(content, default=str)
        if isinstance(content, list):
            return "\n".join(str(item) for item in content)
        return str(content)
