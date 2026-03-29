"""Tests for the observability logging scaffold.

Validates TokenTracker, PipelineStageLogger, log_error_context, StageTimer,
and configure_logging.

Coverage Target: >=85%
Test Count: 30+ tests
"""

from __future__ import annotations

import importlib.util
import logging
import sys
import time
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load module directly — directory name contains hyphens, not importable.
# ---------------------------------------------------------------------------
_MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / "installer"
    / "core"
    / "templates"
    / "langchain-deepagents"
    / "lib"
    / "observability.py"
)

_loader = SourceFileLoader("observability", str(_MODULE_PATH))
_spec = importlib.util.spec_from_loader("observability", _loader)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["observability"] = _mod
_loader.exec_module(_mod)

TokenUsage = _mod.TokenUsage
TokenTracker = _mod.TokenTracker
PipelineStageLogger = _mod.PipelineStageLogger
log_error_context = _mod.log_error_context
StageTimer = _mod.StageTimer
StageTimingRecord = _mod.StageTimingRecord
configure_logging = _mod.configure_logging
PIPELINE_STAGES = _mod.PIPELINE_STAGES


# ===========================================================================
# TokenUsage dataclass
# ===========================================================================


class TestTokenUsage:
    """Tests for the TokenUsage dataclass."""

    def test_default_values(self):
        usage = TokenUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_custom_values(self):
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150


# ===========================================================================
# TokenTracker
# ===========================================================================


class TestTokenTracker:
    """Tests for token usage tracking with cumulative totals and alerts."""

    def test_initial_state(self):
        tracker = TokenTracker()
        assert tracker.total.prompt_tokens == 0
        assert tracker.total.completion_tokens == 0
        assert tracker.total.total_tokens == 0

    def test_record_single_call(self, caplog):
        tracker = TokenTracker()
        with caplog.at_level(logging.INFO, logger="deepagents.observability"):
            tracker.record(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                target="doc1",
            )
        assert tracker.total.prompt_tokens == 100
        assert tracker.total.completion_tokens == 50
        assert tracker.total.total_tokens == 150
        assert "prompt=100 completion=50 total=150" in caplog.text

    def test_cumulative_totals_across_calls(self):
        tracker = TokenTracker()
        tracker.record(100, 50, 150, target="doc1")
        tracker.record(200, 100, 300, target="doc1")
        assert tracker.total.prompt_tokens == 300
        assert tracker.total.completion_tokens == 150
        assert tracker.total.total_tokens == 450

    def test_per_target_tracking(self):
        tracker = TokenTracker()
        tracker.record(100, 50, 150, target="doc1")
        tracker.record(200, 100, 300, target="doc2")

        doc1 = tracker.per_target("doc1")
        assert doc1.prompt_tokens == 100
        assert doc1.total_tokens == 150

        doc2 = tracker.per_target("doc2")
        assert doc2.prompt_tokens == 200
        assert doc2.total_tokens == 300

    def test_per_target_unknown_returns_empty(self):
        tracker = TokenTracker()
        usage = tracker.per_target("nonexistent")
        assert usage.prompt_tokens == 0

    def test_default_target(self):
        tracker = TokenTracker()
        tracker.record(100, 50, 150)
        assert tracker.per_target("default").total_tokens == 150

    def test_context_utilisation_alert(self, caplog):
        tracker = TokenTracker(context_limit=1000, alert_threshold=0.80)
        with caplog.at_level(logging.WARNING, logger="deepagents.observability"):
            tracker.record(prompt_tokens=850, completion_tokens=50, total_tokens=900)
        assert "Context utilisation alert" in caplog.text
        assert "85.0%" in caplog.text

    def test_no_alert_below_threshold(self, caplog):
        tracker = TokenTracker(context_limit=1000, alert_threshold=0.80)
        with caplog.at_level(logging.WARNING, logger="deepagents.observability"):
            tracker.record(prompt_tokens=500, completion_tokens=50, total_tokens=550)
        assert "Context utilisation alert" not in caplog.text

    def test_alert_at_exact_threshold(self, caplog):
        tracker = TokenTracker(context_limit=1000, alert_threshold=0.80)
        with caplog.at_level(logging.WARNING, logger="deepagents.observability"):
            tracker.record(prompt_tokens=800, completion_tokens=50, total_tokens=850)
        assert "Context utilisation alert" in caplog.text

    def test_invalid_threshold_raises(self):
        with pytest.raises(ValueError, match="alert_threshold"):
            TokenTracker(alert_threshold=0.0)
        with pytest.raises(ValueError, match="alert_threshold"):
            TokenTracker(alert_threshold=1.5)

    def test_log_summary(self, caplog):
        tracker = TokenTracker()
        tracker.record(100, 50, 150, target="a")
        tracker.record(200, 100, 300, target="b")
        with caplog.at_level(logging.INFO, logger="deepagents.observability"):
            tracker.log_summary()
        assert "Token summary [a]" in caplog.text
        assert "Token summary [b]" in caplog.text
        assert "Token summary [pipeline]" in caplog.text

    def test_zero_context_limit_no_crash(self):
        tracker = TokenTracker(context_limit=0)
        # Should not raise — division by zero guarded
        tracker.record(100, 50, 150)


# ===========================================================================
# PipelineStageLogger
# ===========================================================================


class TestPipelineStageLogger:
    """Tests for pipeline stage content-length logging."""

    def test_log_single_stage(self, caplog):
        psl = PipelineStageLogger()
        with caplog.at_level(logging.INFO, logger="deepagents.observability"):
            psl.log_stage("raw_response", "hello world", target="doc1")
        assert "content_length=11" in caplog.text
        assert psl.get_lengths("doc1") == {"raw_response": 11}

    def test_log_multiple_stages(self):
        psl = PipelineStageLogger()
        psl.log_stage("raw_response", "a" * 1000, target="doc1")
        psl.log_stage("normalized", "b" * 950, target="doc1")
        psl.log_stage("extracted", "c" * 500, target="doc1")
        lengths = psl.get_lengths("doc1")
        assert lengths == {
            "raw_response": 1000,
            "normalized": 950,
            "extracted": 500,
        }

    def test_default_target(self):
        psl = PipelineStageLogger()
        psl.log_stage("raw_response", "content")
        assert psl.get_lengths("default") == {"raw_response": 7}

    def test_multiple_targets(self):
        psl = PipelineStageLogger()
        psl.log_stage("raw_response", "aaa", target="doc1")
        psl.log_stage("raw_response", "bbbbb", target="doc2")
        assert psl.get_lengths("doc1") == {"raw_response": 3}
        assert psl.get_lengths("doc2") == {"raw_response": 5}

    def test_get_lengths_unknown_target(self):
        psl = PipelineStageLogger()
        assert psl.get_lengths("nonexistent") == {}

    def test_log_summary(self, caplog):
        psl = PipelineStageLogger()
        psl.log_stage("raw_response", "aaa", target="doc1")
        psl.log_stage("extracted", "bb", target="doc1")
        with caplog.at_level(logging.INFO, logger="deepagents.observability"):
            psl.log_summary("doc1")
        assert "Pipeline summary [doc1]" in caplog.text
        assert "raw_response=3" in caplog.text

    def test_log_summary_no_stages(self, caplog):
        psl = PipelineStageLogger()
        with caplog.at_level(logging.INFO, logger="deepagents.observability"):
            psl.log_summary("empty")
        assert "no stages recorded" in caplog.text

    def test_empty_content(self):
        psl = PipelineStageLogger()
        psl.log_stage("raw_response", "", target="doc1")
        assert psl.get_lengths("doc1") == {"raw_response": 0}


# ===========================================================================
# Pipeline stages constant
# ===========================================================================


class TestPipelineStages:
    """Tests for the PIPELINE_STAGES constant."""

    def test_stages_defined(self):
        assert PIPELINE_STAGES == (
            "raw_response",
            "normalized",
            "extracted",
            "validated",
            "written",
        )


# ===========================================================================
# Error context logging
# ===========================================================================


class TestLogErrorContext:
    """Tests for error context logging with head/tail snippets."""

    def test_short_content(self, caplog):
        content = "short"
        error = ValueError("parse failed")
        with caplog.at_level(logging.ERROR, logger="deepagents.observability"):
            log_error_context(content, error, stage="extraction", target="doc1")
        assert "total_length=5" in caplog.text
        assert "parse failed" in caplog.text

    def test_long_content_head_tail(self, caplog):
        content = "H" * 200 + "M" * 600 + "T" * 200
        error = ValueError("extraction failed")
        with caplog.at_level(logging.ERROR, logger="deepagents.observability"):
            log_error_context(content, error, stage="extraction", target="doc1")
        assert "total_length=1000" in caplog.text
        assert "extraction failed" in caplog.text

    def test_default_stage_and_target(self, caplog):
        with caplog.at_level(logging.ERROR, logger="deepagents.observability"):
            log_error_context("x", RuntimeError("fail"))
        assert "[default][unknown]" in caplog.text

    def test_custom_snippet_size(self, caplog):
        content = "A" * 50 + "B" * 50
        with caplog.at_level(logging.ERROR, logger="deepagents.observability"):
            log_error_context(content, ValueError("err"), snippet_size=10)
        assert "total_length=100" in caplog.text


# ===========================================================================
# StageTimer
# ===========================================================================


class TestStageTimer:
    """Tests for stage timing with context manager."""

    def test_time_context_manager(self):
        timer = StageTimer()
        with timer.time("extraction", target="doc1"):
            time.sleep(0.01)
        records = timer.records
        assert len(records) == 1
        assert records[0].stage == "extraction"
        assert records[0].target == "doc1"
        assert records[0].elapsed_seconds >= 0.005

    def test_multiple_stages(self):
        timer = StageTimer()
        with timer.time("stage1"):
            pass
        with timer.time("stage2"):
            pass
        assert len(timer.records) == 2

    def test_per_target_summary(self):
        timer = StageTimer()
        with timer.time("s1", target="a"):
            time.sleep(0.01)
        with timer.time("s2", target="a"):
            time.sleep(0.01)
        with timer.time("s1", target="b"):
            time.sleep(0.01)
        total_a = timer.per_target_summary("a")
        total_b = timer.per_target_summary("b")
        assert total_a >= 0.01
        assert total_b >= 0.005

    def test_pipeline_summary(self):
        timer = StageTimer()
        with timer.time("s1"):
            time.sleep(0.01)
        with timer.time("s2"):
            time.sleep(0.01)
        total = timer.pipeline_summary()
        assert total >= 0.01

    def test_log_summary(self, caplog):
        timer = StageTimer()
        with timer.time("s1", target="doc1"):
            pass
        with caplog.at_level(logging.INFO, logger="deepagents.observability"):
            timer.log_summary()
        assert "Timing summary [doc1]" in caplog.text
        assert "Timing summary [pipeline]" in caplog.text

    def test_default_target(self):
        timer = StageTimer()
        with timer.time("extraction"):
            pass
        assert timer.records[0].target == "default"

    def test_exception_still_records_timing(self):
        timer = StageTimer()
        with pytest.raises(ValueError):
            with timer.time("failing_stage"):
                raise ValueError("boom")
        assert len(timer.records) == 1
        assert timer.records[0].stage == "failing_stage"

    def test_per_target_summary_empty(self):
        timer = StageTimer()
        assert timer.per_target_summary("nonexistent") == 0.0


# ===========================================================================
# StageTimingRecord dataclass
# ===========================================================================


class TestStageTimingRecord:
    """Tests for the StageTimingRecord dataclass."""

    def test_fields(self):
        record = StageTimingRecord(
            stage="extraction", target="doc1", elapsed_seconds=1.234
        )
        assert record.stage == "extraction"
        assert record.target == "doc1"
        assert record.elapsed_seconds == 1.234


# ===========================================================================
# configure_logging
# ===========================================================================


class TestConfigureLogging:
    """Tests for the configure_logging convenience function."""

    def test_sets_level(self):
        configure_logging(level=logging.DEBUG)
        obs_logger = logging.getLogger("deepagents.observability")
        assert obs_logger.level == logging.DEBUG

    def test_adds_handler(self):
        # Reset handlers
        obs_logger = logging.getLogger("deepagents.observability")
        obs_logger.handlers.clear()
        configure_logging()
        assert len(obs_logger.handlers) >= 1

    def test_no_duplicate_handlers(self):
        obs_logger = logging.getLogger("deepagents.observability")
        obs_logger.handlers.clear()
        configure_logging()
        handler_count = len(obs_logger.handlers)
        configure_logging()  # Call again
        assert len(obs_logger.handlers) == handler_count

    def test_custom_format(self):
        obs_logger = logging.getLogger("deepagents.observability")
        obs_logger.handlers.clear()
        configure_logging(fmt="%(message)s")
        assert obs_logger.handlers[0].formatter._fmt == "%(message)s"
