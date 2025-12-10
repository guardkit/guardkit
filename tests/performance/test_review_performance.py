"""
Performance tests for task-review command.

Tests validate that review operations complete within expected time limits
for different depth levels and modes.

NOTE: These tests are marked with @pytest.mark.slow and should be run separately
from regular unit tests. They may take significant time to complete.
"""

import pytest
import time
from pathlib import Path
import tempfile
import shutil
import sys

# Add installer lib to path
installer_lib_path = Path(__file__).parent.parent.parent / "installer" / "core" / "commands" / "lib"
if installer_lib_path.exists():
    sys.path.insert(0, str(installer_lib_path))

from task_review_orchestrator import (
    execute_task_review,
    generate_review_report,
    execute_review_analysis,
    synthesize_recommendations
)
from task_utils import create_task_frontmatter, write_task_frontmatter


class TestReviewPerformance:
    """Performance tests for task-review operations."""

    def setup_method(self):
        """Set up temporary task directory structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.tasks_dir = Path(self.temp_dir) / "tasks"
        self.tasks_dir.mkdir()

        # Create all task state directories
        for state in ["backlog", "in_progress", "in_review", "blocked", "completed", "review_complete"]:
            (self.tasks_dir / state).mkdir()

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def _create_test_task(self, task_id: str, title: str) -> Path:
        """Helper to create a test task file."""
        frontmatter = create_task_frontmatter(
            task_id=task_id,
            title=title,
            priority="medium",
            tags=["performance-test"],
            task_type="review",
            review_mode="architectural"
        )

        body = """
## Description
Performance test task for measuring review execution time.

## Review Scope
- Complete codebase analysis
- Architecture patterns
- Code quality metrics

## Acceptance Criteria
- [ ] Review completed within time limit
- [ ] All findings documented
"""

        task_file = self.tasks_dir / "backlog" / f"{task_id}-{title.replace(' ', '-').lower()}.md"
        content = write_task_frontmatter(frontmatter, body)
        task_file.write_text(content, encoding='utf-8')

        return task_file

    @pytest.mark.slow
    @pytest.mark.timeout(1900)  # 31 minutes max (with buffer)
    def test_quick_review_completes_in_time(self):
        """Test that quick review completes within 30 minutes."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            task_id = "TASK-PERF-001"
            self._create_test_task(task_id, "Quick review performance test")

            start = time.time()
            result = execute_task_review(task_id, mode="architectural", depth="quick")
            duration = time.time() - start

            # Verify completion
            assert result["status"] == "success"

            # Verify time limit (30 minutes = 1800 seconds)
            assert duration < 1800, f"Quick review took {duration:.2f}s, expected < 1800s"

            # Log actual duration for analysis
            print(f"\nQuick review completed in {duration:.2f} seconds")

        finally:
            os.chdir(original_dir)

    @pytest.mark.slow
    @pytest.mark.timeout(7300)  # 2 hours + buffer
    def test_standard_review_completes_in_time(self):
        """Test that standard review completes within 2 hours."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            task_id = "TASK-PERF-002"
            self._create_test_task(task_id, "Standard review performance test")

            start = time.time()
            result = execute_task_review(task_id, mode="architectural", depth="standard")
            duration = time.time() - start

            # Verify completion
            assert result["status"] == "success"

            # Verify time limit (2 hours = 7200 seconds)
            assert duration < 7200, f"Standard review took {duration:.2f}s, expected < 7200s"

            # Log actual duration
            print(f"\nStandard review completed in {duration:.2f} seconds")

        finally:
            os.chdir(original_dir)

    @pytest.mark.slow
    @pytest.mark.timeout(21700)  # 6 hours + buffer
    def test_comprehensive_review_completes_in_time(self):
        """Test that comprehensive review completes within 6 hours."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            task_id = "TASK-PERF-003"
            self._create_test_task(task_id, "Comprehensive review performance test")

            start = time.time()
            result = execute_task_review(task_id, mode="architectural", depth="comprehensive")
            duration = time.time() - start

            # Verify completion
            assert result["status"] == "success"

            # Verify time limit (6 hours = 21600 seconds)
            assert duration < 21600, f"Comprehensive review took {duration:.2f}s, expected < 21600s"

            # Log actual duration
            print(f"\nComprehensive review completed in {duration:.2f} seconds")

        finally:
            os.chdir(original_dir)

    def test_report_generation_is_fast(self):
        """Test that report generation completes within 5 seconds."""
        # Create realistic test data
        review_results = {
            "mode": "architectural",
            "depth": "standard",
            "overall_score": 85,
            "findings": [
                {
                    "severity": "high",
                    "category": "SOLID",
                    "description": "Test finding 1",
                    "file": "test.py",
                    "line": 42
                },
                {
                    "severity": "medium",
                    "category": "DRY",
                    "description": "Test finding 2",
                    "file": "utils.py",
                    "line": 100
                }
            ] * 10,  # 20 findings total
            "principles": {
                "solid": {"score": 80, "findings": []},
                "dry": {"score": 85, "findings": []},
                "yagni": {"score": 90, "findings": []}
            }
        }

        recommendations = {
            "recommendations": [
                {
                    "priority": "high",
                    "category": "Architecture",
                    "description": "Test recommendation 1",
                    "effort": "medium"
                },
                {
                    "priority": "medium",
                    "category": "Code Quality",
                    "description": "Test recommendation 2",
                    "effort": "low"
                }
            ] * 5,  # 10 recommendations total
            "confidence": 0.85,
            "decision_options": ["accept", "revise", "implement"]
        }

        # Test report generation time
        start = time.time()
        report = generate_review_report(review_results, recommendations, "detailed")
        duration = time.time() - start

        # Verify report generated
        assert isinstance(report, str)
        assert len(report) > 0
        assert "# Review Report" in report

        # Verify time limit (5 seconds max)
        assert duration < 5.0, f"Report generation took {duration:.4f}s, expected < 5.0s"

        # Log actual duration
        print(f"\nReport generation completed in {duration:.4f} seconds")

    def test_multiple_report_formats_performance(self):
        """Test that all report formats generate quickly."""
        review_results = {
            "mode": "code-quality",
            "depth": "standard",
            "overall_score": 75,
            "findings": [{"severity": "low", "description": f"Finding {i}"} for i in range(15)]
        }

        recommendations = {
            "recommendations": [{"priority": "medium", "description": f"Rec {i}"} for i in range(8)],
            "confidence": 0.78
        }

        formats = ["summary", "detailed", "presentation"]
        results = {}

        for output_format in formats:
            start = time.time()
            report = generate_review_report(review_results, recommendations, output_format)
            duration = time.time() - start

            # Verify report generated
            assert isinstance(report, str)
            assert len(report) > 0

            # Store result
            results[output_format] = duration

            # Verify time limit (3 seconds max per format)
            assert duration < 3.0, f"{output_format} format took {duration:.4f}s, expected < 3.0s"

        # Log all durations
        print(f"\nReport format generation times:")
        for fmt, dur in results.items():
            print(f"  {fmt}: {dur:.4f}s")

        # Verify total time for all formats (8 seconds max)
        total_duration = sum(results.values())
        assert total_duration < 8.0, f"Total time {total_duration:.4f}s, expected < 8.0s"

    @pytest.mark.parametrize("review_mode", [
        "architectural",
        "code-quality",
        "decision",
        "technical-debt",
        "security"
    ])
    def test_all_review_modes_performance(self, review_mode):
        """Test that all review modes complete in reasonable time (quick depth)."""
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            task_id = f"TASK-MODE-{review_mode.upper()}"
            self._create_test_task(task_id, f"{review_mode} performance test")

            start = time.time()
            result = execute_task_review(task_id, mode=review_mode, depth="quick")
            duration = time.time() - start

            # Verify completion
            assert result["status"] == "success"
            assert result["review_mode"] == review_mode

            # Verify reasonable time (quick mode should be under 30 minutes)
            assert duration < 1800, f"{review_mode} review took {duration:.2f}s, expected < 1800s"

            # Log duration
            print(f"\n{review_mode} review completed in {duration:.2f} seconds")

        finally:
            os.chdir(original_dir)

    def test_analysis_phase_performance(self):
        """Test Phase 2 (analysis) performance in isolation."""
        context = {
            "task_id": "TASK-ANALYSIS",
            "title": "Analysis performance test",
            "description": "Test description",
            "review_scope": ["src/", "tests/"],
            "metadata": {
                "task_type": "review",
                "review_mode": "architectural"
            }
        }

        start = time.time()
        results = execute_review_analysis(context, "architectural", "quick")
        duration = time.time() - start

        # Verify results structure
        assert "findings" in results
        assert "mode" in results

        # Verify reasonable time (Phase 2 should be quick)
        assert duration < 60, f"Analysis took {duration:.2f}s, expected < 60s"

        print(f"\nAnalysis phase completed in {duration:.2f} seconds")

    def test_synthesis_phase_performance(self):
        """Test Phase 3 (synthesis) performance in isolation."""
        review_results = {
            "mode": "architectural",
            "findings": [
                {"severity": "high", "description": f"Finding {i}"}
                for i in range(20)
            ],
            "overall_score": 72
        }

        start = time.time()
        recommendations = synthesize_recommendations(review_results)
        duration = time.time() - start

        # Verify recommendations structure
        assert "recommendations" in recommendations
        assert "confidence" in recommendations

        # Verify reasonable time (Phase 3 should be very quick)
        assert duration < 30, f"Synthesis took {duration:.2f}s, expected < 30s"

        print(f"\nSynthesis phase completed in {duration:.2f} seconds")


@pytest.mark.slow
class TestScalabilityPerformance:
    """Test performance with varying task complexity."""

    def setup_method(self):
        """Set up temporary task directory structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.tasks_dir = Path(self.temp_dir) / "tasks"
        self.tasks_dir.mkdir()

        for state in ["backlog", "review_complete"]:
            (self.tasks_dir / state).mkdir()

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    @pytest.mark.parametrize("scope_size", [
        ("small", ["src/models.py"]),
        ("medium", ["src/models.py", "src/services.py", "src/controllers.py"]),
        ("large", [f"src/module{i}.py" for i in range(10)])
    ])
    def test_performance_scales_with_scope(self, scope_size):
        """Test that performance scales reasonably with review scope size."""
        scope_label, scope_files = scope_size

        # Create task with varying scope
        task_id = f"TASK-SCALE-{scope_label.upper()}"
        frontmatter = create_task_frontmatter(
            task_id=task_id,
            title=f"Scalability test - {scope_label}",
            priority="medium",
            tags=["performance", "scalability"],
            task_type="review",
            review_mode="code-quality"
        )

        scope_str = "\n".join(f"- {f}" for f in scope_files)
        body = f"""
## Description
Scalability test with {scope_label} scope.

## Review Scope
{scope_str}

## Acceptance Criteria
- [ ] Review completed
"""

        task_file = self.tasks_dir / "backlog" / f"{task_id}.md"
        content = write_task_frontmatter(frontmatter, body)
        task_file.write_text(content, encoding='utf-8')

        # Execute review
        import os
        original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        try:
            start = time.time()
            result = execute_task_review(task_id, mode="code-quality", depth="quick")
            duration = time.time() - start

            # Verify success
            assert result["status"] == "success"

            # Log performance
            print(f"\n{scope_label} scope review: {duration:.2f}s for {len(scope_files)} files")

            # Verify reasonable scaling (shouldn't grow exponentially)
            # Small: < 5 min, Medium: < 15 min, Large: < 30 min
            time_limits = {"small": 300, "medium": 900, "large": 1800}
            expected_limit = time_limits[scope_label]

            assert duration < expected_limit, \
                f"{scope_label} scope took {duration:.2f}s, expected < {expected_limit}s"

        finally:
            os.chdir(original_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "slow"])
