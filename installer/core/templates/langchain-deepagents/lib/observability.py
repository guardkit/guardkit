"""Observability logging scaffold for LangChain DeepAgents pipelines.

Provides four logging capabilities that prevent common observability gaps:
1. Token usage tracking per API call with cumulative totals and context alerts.
2. Pipeline stage content-length logging to detect truncation or data loss.
3. Error context logging with head/tail snippets for rapid diagnosis.
4. Stage timing with per-target and pipeline-wide summaries.

Dependencies: stdlib only (logging, time).

Fixes prevented: TRF-010, TRF-017, TRF-018, TRF-023.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("deepagents.observability")


# ---------------------------------------------------------------------------
# Token usage tracking
# ---------------------------------------------------------------------------

@dataclass
class TokenUsage:
    """Token counts for a single LLM API call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class TokenTracker:
    """Track token usage per API call with cumulative totals and context alerts.

    Args:
        context_limit: Maximum context window size for utilisation alerts.
        alert_threshold: Fraction (0-1) of context_limit that triggers an alert.
            Defaults to 0.8 (80%).
    """

    def __init__(
        self,
        context_limit: int = 128_000,
        alert_threshold: float = 0.80,
    ) -> None:
        if not 0.0 < alert_threshold <= 1.0:
            raise ValueError(
                f"alert_threshold must be in (0, 1], got {alert_threshold}"
            )
        self._context_limit = context_limit
        self._alert_threshold = alert_threshold
        # Per-target cumulative usage: target_name -> TokenUsage
        self._per_target: dict[str, TokenUsage] = {}
        # Pipeline-wide totals
        self._total = TokenUsage()

    @property
    def total(self) -> TokenUsage:
        """Pipeline-wide cumulative token usage."""
        return self._total

    def per_target(self, target: str) -> TokenUsage:
        """Cumulative token usage for a specific target."""
        return self._per_target.get(target, TokenUsage())

    def record(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        target: str = "default",
    ) -> None:
        """Record token usage from a single LLM API call.

        Logs the per-call counts, updates cumulative totals, and emits a
        warning if context utilisation exceeds the configured threshold.

        Args:
            prompt_tokens: Tokens in the prompt.
            completion_tokens: Tokens in the completion.
            total_tokens: Total tokens (prompt + completion).
            target: Logical target name for per-target tracking.
        """
        logger.info(
            "Token usage [%s]: prompt=%d completion=%d total=%d",
            target,
            prompt_tokens,
            completion_tokens,
            total_tokens,
        )

        # Update per-target cumulative
        if target not in self._per_target:
            self._per_target[target] = TokenUsage()
        tgt = self._per_target[target]
        tgt.prompt_tokens += prompt_tokens
        tgt.completion_tokens += completion_tokens
        tgt.total_tokens += total_tokens

        # Update pipeline-wide cumulative
        self._total.prompt_tokens += prompt_tokens
        self._total.completion_tokens += completion_tokens
        self._total.total_tokens += total_tokens

        # Context utilisation alert
        utilisation = prompt_tokens / self._context_limit if self._context_limit else 0
        if utilisation >= self._alert_threshold:
            logger.warning(
                "Context utilisation alert [%s]: %.1f%% of %d token limit "
                "(prompt_tokens=%d, threshold=%.0f%%)",
                target,
                utilisation * 100,
                self._context_limit,
                prompt_tokens,
                self._alert_threshold * 100,
            )

    def log_summary(self) -> None:
        """Log cumulative token usage summary for all targets and pipeline total."""
        for target, usage in sorted(self._per_target.items()):
            logger.info(
                "Token summary [%s]: prompt=%d completion=%d total=%d",
                target,
                usage.prompt_tokens,
                usage.completion_tokens,
                usage.total_tokens,
            )
        logger.info(
            "Token summary [pipeline]: prompt=%d completion=%d total=%d",
            self._total.prompt_tokens,
            self._total.completion_tokens,
            self._total.total_tokens,
        )


# ---------------------------------------------------------------------------
# Pipeline stage content-length logging
# ---------------------------------------------------------------------------

PIPELINE_STAGES = (
    "raw_response",
    "normalized",
    "extracted",
    "validated",
    "written",
)


class PipelineStageLogger:
    """Log content length at each pipeline stage to detect truncation or data loss.

    Tracks content lengths per target across the pipeline stages:
    raw_response → normalized → extracted → validated → written.
    """

    def __init__(self) -> None:
        # target -> stage -> length
        self._lengths: dict[str, dict[str, int]] = {}

    def log_stage(self, stage: str, content: str, target: str = "default") -> None:
        """Record and log content length at a pipeline stage.

        Args:
            stage: Pipeline stage name (e.g. "raw_response", "extracted").
            content: The content at this stage.
            target: Logical target name for per-target tracking.
        """
        length = len(content)
        if target not in self._lengths:
            self._lengths[target] = {}
        self._lengths[target][stage] = length

        logger.info(
            "Pipeline stage [%s][%s]: content_length=%d",
            target,
            stage,
            length,
        )

    def log_summary(self, target: str = "default") -> None:
        """Log a summary of content lengths across all recorded stages for a target.

        Args:
            target: Target to summarise. Defaults to "default".
        """
        stages = self._lengths.get(target, {})
        if not stages:
            logger.info("Pipeline summary [%s]: no stages recorded", target)
            return

        parts = [f"{stage}={length}" for stage, length in stages.items()]
        logger.info(
            "Pipeline summary [%s]: %s",
            target,
            " → ".join(parts),
        )

    def get_lengths(self, target: str = "default") -> dict[str, int]:
        """Return recorded stage lengths for a target.

        Args:
            target: Target name.

        Returns:
            Dict mapping stage name to content length.
        """
        return dict(self._lengths.get(target, {}))


# ---------------------------------------------------------------------------
# Error context logging
# ---------------------------------------------------------------------------

def log_error_context(
    content: str,
    error: Exception,
    stage: str = "unknown",
    target: str = "default",
    snippet_size: int = 200,
) -> None:
    """Log error context with head/tail snippets for rapid diagnosis.

    On extraction or validation failure, logs the first and last
    ``snippet_size`` characters of the content alongside the total length
    and the error message.

    Args:
        content: The content that caused the error.
        error: The exception that occurred.
        stage: Pipeline stage where the error occurred.
        target: Logical target name.
        snippet_size: Number of characters to include in head/tail snippets.
            Defaults to 200.
    """
    total_length = len(content)
    head = content[:snippet_size]
    tail = content[-snippet_size:] if total_length > snippet_size else content

    logger.error(
        "Error context [%s][%s]: error=%s total_length=%d "
        "head=%.200r tail=%.200r",
        target,
        stage,
        error,
        total_length,
        head,
        tail,
    )


# ---------------------------------------------------------------------------
# Stage timing
# ---------------------------------------------------------------------------

@dataclass
class StageTimingRecord:
    """Timing record for a single pipeline stage execution."""

    stage: str
    target: str
    elapsed_seconds: float


class StageTimer:
    """Track wall-clock time per pipeline stage with per-target and pipeline summaries.

    Usage::

        timer = StageTimer()
        with timer.time("extraction", target="doc1"):
            result = extract(content)
        timer.log_summary()
    """

    def __init__(self) -> None:
        self._records: list[StageTimingRecord] = []

    def time(self, stage: str, target: str = "default") -> "_TimingContext":
        """Context manager that times a pipeline stage.

        Args:
            stage: Stage name (e.g. "extraction", "validation").
            target: Logical target name.

        Returns:
            Context manager that records elapsed time on exit.
        """
        return _TimingContext(stage=stage, target=target, timer=self)

    def _add_record(self, record: StageTimingRecord) -> None:
        """Add a timing record (called by _TimingContext on exit)."""
        self._records.append(record)
        logger.info(
            "Stage timing [%s][%s]: %.3fs",
            record.target,
            record.stage,
            record.elapsed_seconds,
        )

    def per_target_summary(self, target: str) -> float:
        """Total elapsed time for a specific target.

        Args:
            target: Target name to summarise.

        Returns:
            Total elapsed seconds for the target.
        """
        return sum(
            r.elapsed_seconds for r in self._records if r.target == target
        )

    def pipeline_summary(self) -> float:
        """Total elapsed time across all targets and stages.

        Returns:
            Total elapsed seconds for the entire pipeline.
        """
        return sum(r.elapsed_seconds for r in self._records)

    @property
    def records(self) -> list[StageTimingRecord]:
        """All timing records in order of recording."""
        return list(self._records)

    def log_summary(self) -> None:
        """Log timing summaries per target and pipeline-wide."""
        targets = sorted({r.target for r in self._records})
        for target in targets:
            total = self.per_target_summary(target)
            logger.info(
                "Timing summary [%s]: %.3fs total",
                target,
                total,
            )
        pipeline_total = self.pipeline_summary()
        logger.info(
            "Timing summary [pipeline]: %.3fs total",
            pipeline_total,
        )


class _TimingContext:
    """Context manager for stage timing."""

    def __init__(self, stage: str, target: str, timer: StageTimer) -> None:
        self._stage = stage
        self._target = target
        self._timer = timer
        self._start: Optional[float] = None

    def __enter__(self) -> "_TimingContext":
        self._start = time.monotonic()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        elapsed = time.monotonic() - self._start
        self._timer._add_record(
            StageTimingRecord(
                stage=self._stage,
                target=self._target,
                elapsed_seconds=elapsed,
            )
        )
        return None  # Do not suppress exceptions


# ---------------------------------------------------------------------------
# Convenience: configure logging
# ---------------------------------------------------------------------------

def configure_logging(
    level: int = logging.INFO,
    fmt: str = "%(asctime)s %(name)s %(levelname)s %(message)s",
) -> None:
    """Configure the observability logger with a given level and format.

    This is a convenience function for quick setup. For production use,
    configure the ``deepagents.observability`` logger via your application's
    logging configuration.

    Args:
        level: Logging level (e.g. logging.DEBUG, logging.INFO).
        fmt: Log format string.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt))
    obs_logger = logging.getLogger("deepagents.observability")
    obs_logger.setLevel(level)
    # Avoid duplicate handlers if called multiple times
    if not obs_logger.handlers:
        obs_logger.addHandler(handler)
