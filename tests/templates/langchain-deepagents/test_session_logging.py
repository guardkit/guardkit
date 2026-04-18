"""Tests for the session_logging lib module (TASK-LCL-008).

Validates the two orchestrator-level logging primitives extracted from
weighted-evaluation's inline scaffold helpers:

- ``configure_logging(debug, verbose)`` — bootstrap root logger with force=True.
- ``write_session_log(target_id, result, log_dir)`` — unconditional per-run
  JSON diagnostic dump. Duck-typed over the result shape so any pipeline
  result with ``success``/``attempts``/``error``/optional ``verdict`` works.

Coverage Target: >=85%
Test Count: 20+ tests
"""

from __future__ import annotations

import importlib.util
import json
import logging
import sys
from dataclasses import dataclass, field
from importlib.machinery import SourceFileLoader
from pathlib import Path
from typing import Any

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
    / "session_logging.py"
)

_loader = SourceFileLoader("_test_session_logging", str(_MODULE_PATH))
_spec = importlib.util.spec_from_loader("_test_session_logging", _loader)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["_test_session_logging"] = _mod
_loader.exec_module(_mod)

configure_logging = _mod.configure_logging
write_session_log = _mod.write_session_log
_serialize_verdict = _mod._serialize_verdict


# ---------------------------------------------------------------------------
# Minimal result / verdict stand-ins for the duck-typed contract
# ---------------------------------------------------------------------------

@dataclass
class _MinimalResult:
    """Minimal result exposing only the required attrs."""

    success: bool = False
    attempts: int = 0
    error: str | None = None
    verdict: Any = None


@dataclass
class _CoachVerdictLike:
    """Stand-in for base-template CoachVerdict."""

    decision: str = "reject"
    score: int = 1
    issues: list[str] = field(default_factory=list)
    criteria_met: bool = False
    quality_assessment: str = "needs_revision"


@dataclass
class _CriterionScoreLike:
    name: str = ""
    score: float = 0.0
    feedback: str = ""


@dataclass
class _WeightedVerdictLike:
    """Stand-in for weighted-eval WeightedVerdict."""

    decision: str = "reject"
    composite_score: float = 0.0
    issues: list[str] = field(default_factory=list)
    quality_assessment: str = "needs_revision"
    criterion_scores: list[_CriterionScoreLike] = field(default_factory=list)


# ===========================================================================
# configure_logging
# ===========================================================================


class TestConfigureLogging:
    """Configure_logging bootstrap behaviour.

    The existing test pattern cleans up by resetting root logger level after
    each test because configure_logging uses force=True and mutates global state.
    """

    @pytest.fixture(autouse=True)
    def _reset_root_level(self):
        original_level = logging.getLogger().level
        yield
        logging.getLogger().setLevel(original_level)

    def test_debug_flag_sets_debug_level(self):
        configure_logging(debug=True)
        assert logging.getLogger().level == logging.DEBUG

    def test_verbose_flag_sets_info_level(self):
        configure_logging(verbose=True)
        assert logging.getLogger().level == logging.INFO

    def test_no_flags_does_not_raise(self):
        # Neither flag configures logging — just exits quietly.
        configure_logging()

    def test_debug_takes_precedence_over_verbose(self):
        configure_logging(debug=True, verbose=True)
        assert logging.getLogger().level == logging.DEBUG

    def test_force_true_overrides_existing_handlers(self):
        # Pre-install a handler that would otherwise block basicConfig.
        root = logging.getLogger()
        root.addHandler(logging.NullHandler())
        configure_logging(verbose=True)
        assert root.level == logging.INFO


# ===========================================================================
# _serialize_verdict (duck-typed)
# ===========================================================================


class TestSerializeVerdict:
    """Duck-typed verdict serialization covers Coach and Weighted shapes."""

    def test_returns_none_for_none_verdict(self):
        assert _serialize_verdict(None) is None

    def test_serializes_coach_verdict_like(self):
        verdict = _CoachVerdictLike(
            decision="accept", score=5, issues=[], criteria_met=True,
            quality_assessment="excellent",
        )
        out = _serialize_verdict(verdict)
        assert out["decision"] == "accept"
        assert out["score"] == 5
        assert out["criteria_met"] is True
        assert out["quality_assessment"] == "excellent"
        # No composite_score / criterion_scores for the base shape
        assert "composite_score" not in out
        assert "criterion_scores" not in out

    def test_serializes_weighted_verdict_like(self):
        verdict = _WeightedVerdictLike(
            decision="accept",
            composite_score=0.82,
            issues=["minor nits"],
            criterion_scores=[
                _CriterionScoreLike(name="accuracy", score=0.9, feedback="Good"),
                _CriterionScoreLike(name="clarity", score=0.75, feedback="OK"),
            ],
        )
        out = _serialize_verdict(verdict)
        assert out["decision"] == "accept"
        assert out["composite_score"] == pytest.approx(0.82)
        assert out["issues"] == ["minor nits"]
        assert out["criterion_scores"] == [
            {"name": "accuracy", "score": 0.9, "feedback": "Good"},
            {"name": "clarity", "score": 0.75, "feedback": "OK"},
        ]

    def test_skips_missing_attrs(self):
        class BareVerdict:
            decision = "reject"

        out = _serialize_verdict(BareVerdict())
        assert out == {"decision": "reject"}


# ===========================================================================
# write_session_log
# ===========================================================================


class TestWriteSessionLog:
    """write_session_log fires unconditionally and never raises."""

    def test_writes_log_on_success(self, tmp_path):
        result = _MinimalResult(success=True, attempts=1)
        log_file = write_session_log("target-1", result, log_dir=tmp_path)

        assert log_file is not None
        assert log_file.exists()
        data = json.loads(log_file.read_text())
        assert data["success"] is True
        assert data["attempts"] == 1
        assert data["target_id"] == "target-1"
        assert data["error"] is None
        assert data["verdict"] is None

    def test_writes_log_on_failure(self, tmp_path):
        """The critical case — failures must still produce a log."""
        result = _MinimalResult(
            success=False, attempts=3, error="Exhausted 3 retries",
        )
        log_file = write_session_log("target-fail", result, log_dir=tmp_path)

        assert log_file is not None
        data = json.loads(log_file.read_text())
        assert data["success"] is False
        assert data["error"] == "Exhausted 3 retries"
        assert data["attempts"] == 3

    def test_filename_includes_target_id_and_timestamp(self, tmp_path):
        result = _MinimalResult(success=True, attempts=1)
        log_file = write_session_log("tgt-abc", result, log_dir=tmp_path)
        assert log_file.name.startswith("tgt-abc_")
        assert log_file.suffix == ".json"

    def test_creates_log_dir_if_missing(self, tmp_path):
        nested = tmp_path / "deeply" / "nested"
        assert not nested.exists()
        result = _MinimalResult(success=True, attempts=1)
        log_file = write_session_log("t", result, log_dir=nested)
        assert nested.exists()
        assert log_file.parent == nested

    def test_accepts_string_log_dir(self, tmp_path):
        result = _MinimalResult(success=True, attempts=1)
        log_file = write_session_log("t", result, log_dir=str(tmp_path))
        assert log_file is not None
        assert log_file.exists()

    def test_serializes_weighted_verdict(self, tmp_path):
        result = _MinimalResult(
            success=True, attempts=2,
            verdict=_WeightedVerdictLike(
                decision="accept",
                composite_score=0.91,
                criterion_scores=[
                    _CriterionScoreLike(
                        name="accuracy", score=0.95, feedback="solid",
                    ),
                ],
            ),
        )
        log_file = write_session_log("tgt", result, log_dir=tmp_path)
        data = json.loads(log_file.read_text())
        verdict = data["verdict"]
        assert verdict["decision"] == "accept"
        assert verdict["composite_score"] == pytest.approx(0.91)
        assert verdict["criterion_scores"][0]["name"] == "accuracy"

    def test_serializes_coach_verdict(self, tmp_path):
        result = _MinimalResult(
            success=True, attempts=1,
            verdict=_CoachVerdictLike(decision="accept", score=4),
        )
        log_file = write_session_log("tgt", result, log_dir=tmp_path)
        data = json.loads(log_file.read_text())
        verdict = data["verdict"]
        assert verdict["decision"] == "accept"
        assert verdict["score"] == 4
        # Weighted-specific fields absent for base-shape verdict
        assert "composite_score" not in verdict

    def test_returns_none_when_write_fails(self, tmp_path, monkeypatch):
        """Diagnostic path must not crash the pipeline."""
        result = _MinimalResult(success=True, attempts=1)

        def _boom(self, *_a, **_kw):
            raise OSError("disk full")

        monkeypatch.setattr(Path, "write_text", _boom)
        log_file = write_session_log("t", result, log_dir=tmp_path)
        assert log_file is None

    def test_reads_verdict_via_getattr(self, tmp_path):
        """Result may omit .verdict entirely (getattr default is None)."""

        class NoVerdict:
            success = True
            attempts = 1
            error = None

        log_file = write_session_log("t", NoVerdict(), log_dir=tmp_path)
        data = json.loads(log_file.read_text())
        assert data["verdict"] is None

    def test_handles_missing_attrs_gracefully(self, tmp_path):
        """Even required attrs can be absent — result becomes None in log."""

        class Sparse:
            pass

        log_file = write_session_log("sparse", Sparse(), log_dir=tmp_path)
        assert log_file is not None
        data = json.loads(log_file.read_text())
        assert data["success"] is None
        assert data["attempts"] is None
