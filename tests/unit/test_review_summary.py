"""Unit tests for ReviewSummaryGenerator.

TASK-ABE-003: Tests for structured review summary generation from autobuild
execution data.

Coverage Target: >=85%
Test Count: 20+ tests
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrationResult,
    TaskExecutionResult,
    WaveExecutionResult,
)
from guardkit.orchestrator.review_summary import (
    ReviewSummaryGenerator,
    ReviewSummaryResult,
    TaskSummaryRow,
)


# ============================================================================
# Fixtures
# ============================================================================


def _make_task_result(
    task_id: str = "TASK-001",
    success: bool = True,
    total_turns: int = 1,
    final_decision: str = "approved",
    error: str | None = None,
    recovery_count: int = 0,
    sdk_ceiling_hits: int = 0,
    sdk_total_invocations: int = 1,
    sdk_turns_per_invocation: list[int] | None = None,
) -> TaskExecutionResult:
    return TaskExecutionResult(
        task_id=task_id,
        success=success,
        total_turns=total_turns,
        final_decision=final_decision,
        error=error,
        recovery_count=recovery_count,
        sdk_ceiling_hits=sdk_ceiling_hits,
        sdk_total_invocations=sdk_total_invocations,
        sdk_turns_per_invocation=sdk_turns_per_invocation or [total_turns],
    )


def _make_wave(
    wave_number: int,
    results: list[TaskExecutionResult],
) -> WaveExecutionResult:
    return WaveExecutionResult(
        wave_number=wave_number,
        task_ids=[r.task_id for r in results],
        results=results,
        all_succeeded=all(r.success for r in results),
    )


def _make_feature_result(
    feature_id: str = "FEAT-TEST",
    wave_results: list[WaveExecutionResult] | None = None,
    success: bool = True,
    status: str = "completed",
) -> FeatureOrchestrationResult:
    if wave_results is None:
        task = _make_task_result()
        wave_results = [_make_wave(1, [task])]
    total_tasks = sum(len(w.results) for w in wave_results)
    completed = sum(1 for w in wave_results for r in w.results if r.success)
    failed = total_tasks - completed
    return FeatureOrchestrationResult(
        feature_id=feature_id,
        success=success,
        status=status,
        total_tasks=total_tasks,
        tasks_completed=completed,
        tasks_failed=failed,
        wave_results=wave_results,
        worktree=MagicMock(),
    )


@pytest.fixture
def generator(tmp_path: Path) -> ReviewSummaryGenerator:
    return ReviewSummaryGenerator(output_dir=tmp_path)


@pytest.fixture
def single_task_result() -> FeatureOrchestrationResult:
    return _make_feature_result()


@pytest.fixture
def multi_wave_result() -> FeatureOrchestrationResult:
    t1 = _make_task_result("TASK-001", success=True, total_turns=1)
    t2 = _make_task_result("TASK-002", success=True, total_turns=3)
    t3 = _make_task_result(
        "TASK-003",
        success=False,
        total_turns=5,
        final_decision="max_turns_exceeded",
        error="Tests still failing",
    )
    w1 = _make_wave(1, [t1, t2])
    w2 = _make_wave(2, [t3])
    return _make_feature_result(
        wave_results=[w1, w2],
        success=False,
        status="failed",
    )


# ============================================================================
# Test: generate()
# ============================================================================


class TestGenerate:
    """Tests for the generate() method."""

    def test_generate_writes_file(
        self, generator: ReviewSummaryGenerator, single_task_result: FeatureOrchestrationResult
    ) -> None:
        result = generator.generate(single_task_result)
        assert result.success is True
        assert result.output_path is not None
        assert result.output_path.exists()

    def test_generate_returns_correct_path(
        self, generator: ReviewSummaryGenerator, single_task_result: FeatureOrchestrationResult
    ) -> None:
        result = generator.generate(single_task_result)
        assert result.output_path is not None
        assert result.output_path.name == "review-summary.md"

    def test_generate_creates_output_dir(
        self, tmp_path: Path, single_task_result: FeatureOrchestrationResult
    ) -> None:
        nested = tmp_path / "deep" / "nested" / "dir"
        gen = ReviewSummaryGenerator(output_dir=nested)
        result = gen.generate(single_task_result)
        assert result.success is True
        assert nested.exists()

    def test_generate_on_unwritable_dir(
        self, single_task_result: FeatureOrchestrationResult
    ) -> None:
        gen = ReviewSummaryGenerator(output_dir=Path("/proc/nonexistent/path"))
        result = gen.generate(single_task_result)
        assert result.success is False
        assert result.error is not None

    def test_generate_on_empty_waves(
        self, generator: ReviewSummaryGenerator
    ) -> None:
        result_data = _make_feature_result(wave_results=[])
        result = generator.generate(result_data)
        assert result.success is True
        content = result.output_path.read_text()
        assert "No task data available" in content


# ============================================================================
# Test: Header rendering
# ============================================================================


class TestRenderHeader:
    """Tests for the header section."""

    def test_header_contains_feature_id(
        self, generator: ReviewSummaryGenerator, single_task_result: FeatureOrchestrationResult
    ) -> None:
        result = generator.generate(single_task_result)
        content = result.output_path.read_text()
        assert "FEAT-TEST" in content

    def test_header_shows_completed_on_success(
        self, generator: ReviewSummaryGenerator
    ) -> None:
        data = _make_feature_result(success=True, status="completed")
        result = generator.generate(data)
        content = result.output_path.read_text()
        assert "**Status:** COMPLETED" in content

    def test_header_shows_failed_on_failure(
        self, generator: ReviewSummaryGenerator
    ) -> None:
        t = _make_task_result(success=False, final_decision="error", error="boom")
        w = _make_wave(1, [t])
        data = _make_feature_result(wave_results=[w], success=False, status="failed")
        result = generator.generate(data)
        content = result.output_path.read_text()
        assert "**Status:** FAILED" in content

    def test_header_shows_paused_on_paused(
        self, generator: ReviewSummaryGenerator
    ) -> None:
        data = _make_feature_result(success=False, status="paused")
        result = generator.generate(data)
        content = result.output_path.read_text()
        assert "**Status:** PAUSED" in content


# ============================================================================
# Test: Feature Metrics
# ============================================================================


class TestRenderFeatureMetrics:
    """Tests for the metrics table."""

    def test_metrics_table_correct_counts(
        self, generator: ReviewSummaryGenerator, multi_wave_result: FeatureOrchestrationResult
    ) -> None:
        result = generator.generate(multi_wave_result)
        content = result.output_path.read_text()
        assert "| Total tasks | 3 |" in content
        # total turns = 1 + 3 + 5 = 9
        assert "| Total turns | 9 |" in content
        assert "| Waves executed | 2 |" in content

    def test_avg_turns_per_task(
        self, generator: ReviewSummaryGenerator, multi_wave_result: FeatureOrchestrationResult
    ) -> None:
        result = generator.generate(multi_wave_result)
        content = result.output_path.read_text()
        # 9 / 3 = 3.00
        assert "| Avg turns/task | 3.00 |" in content

    def test_first_attempt_pass_rate(
        self, generator: ReviewSummaryGenerator, multi_wave_result: FeatureOrchestrationResult
    ) -> None:
        result = generator.generate(multi_wave_result)
        content = result.output_path.read_text()
        # Only TASK-001 passed on first turn: 1/3 = 33%
        assert "| First-attempt pass rate | 33% |" in content


# ============================================================================
# Test: Per-Task Outcome Table
# ============================================================================


class TestRenderTaskTable:
    """Tests for the per-task outcome table."""

    def test_task_table_one_row_per_task(
        self, generator: ReviewSummaryGenerator, multi_wave_result: FeatureOrchestrationResult
    ) -> None:
        result = generator.generate(multi_wave_result)
        content = result.output_path.read_text()
        assert "TASK-001" in content
        assert "TASK-002" in content
        assert "TASK-003" in content

    def test_task_table_shows_wave_number(
        self, generator: ReviewSummaryGenerator, multi_wave_result: FeatureOrchestrationResult
    ) -> None:
        result = generator.generate(multi_wave_result)
        content = result.output_path.read_text()
        # TASK-001 and TASK-002 in wave 1, TASK-003 in wave 2
        lines = content.split("\n")
        task1_line = [l for l in lines if "TASK-001" in l][0]
        task3_line = [l for l in lines if "TASK-003" in l][0]
        assert "| 1 |" in task1_line
        assert "| 2 |" in task3_line

    def test_task_table_shows_outcome(
        self, generator: ReviewSummaryGenerator, multi_wave_result: FeatureOrchestrationResult
    ) -> None:
        result = generator.generate(multi_wave_result)
        content = result.output_path.read_text()
        lines = content.split("\n")
        task1_line = [l for l in lines if "TASK-001" in l][0]
        task3_line = [l for l in lines if "TASK-003" in l][0]
        assert "PASSED" in task1_line
        assert "FAILED" in task3_line


# ============================================================================
# Test: Quality Metrics
# ============================================================================


class TestRenderQualityMetrics:
    """Tests for quality metrics section."""

    def test_success_rate_100_percent(
        self, generator: ReviewSummaryGenerator, single_task_result: FeatureOrchestrationResult
    ) -> None:
        result = generator.generate(single_task_result)
        content = result.output_path.read_text()
        assert "Task success rate: 100%" in content

    def test_success_rate_partial(
        self, generator: ReviewSummaryGenerator, multi_wave_result: FeatureOrchestrationResult
    ) -> None:
        result = generator.generate(multi_wave_result)
        content = result.output_path.read_text()
        # 2/3 = 67%
        assert "Task success rate: 67%" in content

    def test_first_turn_approvals(
        self, generator: ReviewSummaryGenerator, multi_wave_result: FeatureOrchestrationResult
    ) -> None:
        result = generator.generate(multi_wave_result)
        content = result.output_path.read_text()
        assert "First-turn approvals: 1/3" in content


# ============================================================================
# Test: Turn Efficiency
# ============================================================================


class TestRenderTurnEfficiency:
    """Tests for turn efficiency analysis."""

    def test_avg_turns_calculation(
        self, generator: ReviewSummaryGenerator, multi_wave_result: FeatureOrchestrationResult
    ) -> None:
        result = generator.generate(multi_wave_result)
        content = result.output_path.read_text()
        assert "| Avg turns/task | 3.0 |" in content

    def test_single_vs_multi_turn_breakdown(
        self, generator: ReviewSummaryGenerator, multi_wave_result: FeatureOrchestrationResult
    ) -> None:
        result = generator.generate(multi_wave_result)
        content = result.output_path.read_text()
        # 1 single-turn (TASK-001), 2 multi-turn (TASK-002, TASK-003)
        assert "| Single-turn tasks | 1 |" in content
        assert "| Multi-turn tasks | 2 |" in content

    def test_empty_task_results(
        self, generator: ReviewSummaryGenerator
    ) -> None:
        data = _make_feature_result(wave_results=[])
        result = generator.generate(data)
        content = result.output_path.read_text()
        assert "No task data available" in content

    def test_avg_sdk_turns(self, generator: ReviewSummaryGenerator) -> None:
        t1 = _make_task_result(
            "TASK-001", total_turns=4, sdk_turns_per_invocation=[2, 2]
        )
        t2 = _make_task_result(
            "TASK-002", total_turns=6, sdk_turns_per_invocation=[3, 3]
        )
        w = _make_wave(1, [t1, t2])
        data = _make_feature_result(wave_results=[w])
        result = generator.generate(data)
        content = result.output_path.read_text()
        # avg of [2, 2, 3, 3] = 2.5
        assert "| Avg SDK turns/invocation | 2.5 |" in content


# ============================================================================
# Test: Key Findings
# ============================================================================


class TestRenderKeyFindings:
    """Tests for auto-generated key findings."""

    def test_ceiling_hit_finding(self, generator: ReviewSummaryGenerator) -> None:
        t = _make_task_result("TASK-001", sdk_ceiling_hits=3)
        w = _make_wave(1, [t])
        data = _make_feature_result(wave_results=[w])
        result = generator.generate(data)
        content = result.output_path.read_text()
        assert "3 SDK ceiling hit(s) detected" in content

    def test_clean_run_finding(
        self, generator: ReviewSummaryGenerator, single_task_result: FeatureOrchestrationResult
    ) -> None:
        result = generator.generate(single_task_result)
        content = result.output_path.read_text()
        assert "All tasks completed cleanly" in content

    def test_multi_turn_failure_finding(
        self, generator: ReviewSummaryGenerator
    ) -> None:
        t = _make_task_result(
            "TASK-BAD", success=False, total_turns=3, final_decision="error", error="boom"
        )
        w = _make_wave(1, [t])
        data = _make_feature_result(wave_results=[w], success=False, status="failed")
        result = generator.generate(data)
        content = result.output_path.read_text()
        assert "TASK-BAD" in content
        assert "multiple turns before failing" in content

    def test_single_turn_failure_finding(
        self, generator: ReviewSummaryGenerator
    ) -> None:
        t = _make_task_result(
            "TASK-QUICK", success=False, total_turns=1, final_decision="error", error="instant fail"
        )
        w = _make_wave(1, [t])
        data = _make_feature_result(wave_results=[w], success=False, status="failed")
        result = generator.generate(data)
        content = result.output_path.read_text()
        assert "failed on first turn" in content
        assert "TASK-QUICK" in content

    def test_recovery_finding(self, generator: ReviewSummaryGenerator) -> None:
        t = _make_task_result("TASK-REC", recovery_count=2)
        w = _make_wave(1, [t])
        data = _make_feature_result(wave_results=[w])
        result = generator.generate(data)
        content = result.output_path.read_text()
        assert "State recovery used" in content
        assert "TASK-REC (2x)" in content

    def test_no_findings_fallback(self, generator: ReviewSummaryGenerator) -> None:
        # A failed run with no ceiling, no recovery, single-turn failure
        # should still have some finding
        t = _make_task_result(
            "TASK-X", success=False, total_turns=1, final_decision="error", error="err"
        )
        w = _make_wave(1, [t])
        data = _make_feature_result(wave_results=[w], success=False, status="failed")
        result = generator.generate(data)
        content = result.output_path.read_text()
        assert "## Key Findings" in content


# ============================================================================
# Test: TaskSummaryRow
# ============================================================================


class TestTaskSummaryRow:
    """Tests for the TaskSummaryRow dataclass."""

    def test_row_creation(self) -> None:
        row = TaskSummaryRow(
            task_id="TASK-001",
            wave=1,
            outcome="passed",
            turns=2,
            final_decision="approved",
            sdk_invocations=1,
            sdk_ceiling_hits=0,
        )
        assert row.task_id == "TASK-001"
        assert row.error is None

    def test_row_with_error(self) -> None:
        row = TaskSummaryRow(
            task_id="TASK-002",
            wave=2,
            outcome="failed",
            turns=5,
            final_decision="max_turns_exceeded",
            sdk_invocations=3,
            sdk_ceiling_hits=1,
            error="Tests failing",
        )
        assert row.error == "Tests failing"


# ============================================================================
# Test: ReviewSummaryResult
# ============================================================================


class TestReviewSummaryResult:
    """Tests for the ReviewSummaryResult dataclass."""

    def test_success_result(self, tmp_path: Path) -> None:
        r = ReviewSummaryResult(success=True, output_path=tmp_path / "test.md")
        assert r.success is True
        assert r.error is None

    def test_failure_result(self) -> None:
        r = ReviewSummaryResult(success=False, error="Permission denied")
        assert r.success is False
        assert r.output_path is None


# ============================================================================
# Test: Markdown structure
# ============================================================================


class TestMarkdownStructure:
    """Tests for overall markdown structure and required sections."""

    def test_all_required_sections_present(
        self, generator: ReviewSummaryGenerator, single_task_result: FeatureOrchestrationResult
    ) -> None:
        result = generator.generate(single_task_result)
        content = result.output_path.read_text()
        assert "# Autobuild Review Summary:" in content
        assert "## Metrics" in content
        assert "## Per-Task Outcomes" in content
        assert "## Quality Metrics" in content
        assert "## Turn Efficiency" in content
        assert "## Key Findings" in content

    def test_markdown_ends_with_newline(
        self, generator: ReviewSummaryGenerator, single_task_result: FeatureOrchestrationResult
    ) -> None:
        result = generator.generate(single_task_result)
        content = result.output_path.read_text()
        assert content.endswith("\n")

    def test_ceiling_hits_in_notes_column(
        self, generator: ReviewSummaryGenerator
    ) -> None:
        t = _make_task_result("TASK-CEIL", sdk_ceiling_hits=2)
        w = _make_wave(1, [t])
        data = _make_feature_result(wave_results=[w])
        result = generator.generate(data)
        content = result.output_path.read_text()
        lines = [l for l in content.split("\n") if "TASK-CEIL" in l]
        assert len(lines) >= 1
        assert "ceiling hits: 2" in lines[0]
